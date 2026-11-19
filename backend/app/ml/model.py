"""Transformer model loading and inference.

Loads a locally fine-tuned checkpoint when available (MODEL_PATH), otherwise a
pretrained Hugging Face sequence-classification model (MODEL_HF_ID). The model
is loaded lazily once per process and reused for all requests.

Explainability uses gradient-based token attribution: we backpropagate the
predicted-class logit with respect to the input embeddings and aggregate the
gradients at token level. This is a legitimate, fast attribution method
(similar in spirit to integrated gradients / gradient*input saliency). It is
NOT a measure of factual correctness.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import torch
from transformers import AutoConfig, AutoModelForSequenceClassification, AutoTokenizer

from ..core.config import get_settings
from ..core.logging import logger
from .text_utils import clean_text


@dataclass
class Attribution:
    token: str
    score: float
    start: int | None = None
    end: int | None = None


@dataclass
class SentenceScore:
    text: str
    score: float


@dataclass
class PredictionResult:
    text: str
    prediction: str
    confidence: float
    probabilities: dict[str, float]
    label_order: list[str]
    model_name: str
    inference_ms: float
    top_tokens: list[Attribution] = field(default_factory=list)
    bottom_tokens: list[Attribution] = field(default_factory=list)
    sentence_scores: list[SentenceScore] = field(default_factory=list)
    truncated: bool = False
    attribution_method: str = "gradient_token_attribution"


class ModelUnavailableError(RuntimeError):
    pass


class FakeNewsModel:
    """Thread-safe lazy singleton wrapper around a HF sequence classifier."""

    _instance: "FakeNewsModel | None" = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._model = None
        self._tokenizer = None
        self._id2label: dict[int, str] = {}
        self._model_name: str = ""
        self._max_length: int = 512
        self._device = "cpu"
        self._load_lock = threading.Lock()
        self._loaded = False
        self._load_error: str | None = None

    @classmethod
    def get(cls) -> "FakeNewsModel":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------ load
    def load(self) -> None:
        if self._loaded:
            return
        with self._load_lock:
            if self._loaded:
                return
            settings = get_settings()
            model_dir = settings.model_path.strip()
            source = model_dir if model_dir else settings.model_hf_id
            self._model_name = source
            self._max_length = settings.model_max_length

            try:
                if settings.force_cpu:
                    torch.set_num_threads(max(1, torch.get_num_threads()))
                self._device = "cuda" if (torch.cuda.is_available() and not settings.force_cpu) else "cpu"

                logger.info("Loading tokenizer/model from %s", source)
                self._tokenizer = AutoTokenizer.from_pretrained(source)
                self._model = AutoModelForSequenceClassification.from_pretrained(source)
                self._model.to(self._device)
                self._model.eval()

                cfg = AutoConfig.from_pretrained(source)
                if getattr(cfg, "id2label", None):
                    self._id2label = {int(k): str(v) for k, v in cfg.id2label.items()}
                elif getattr(cfg, "label2id", None):
                    self._id2label = {v: k for k, v in cfg.label2id.items()}

                # Fall back to configured label order when config lacks names.
                labels = settings.label_list
                num_labels = getattr(self._model.config, "num_labels", len(labels))
                if len(self._id2label) < num_labels:
                    for i in range(num_labels):
                        self._id2label.setdefault(i, labels[i] if i < len(labels) else f"class_{i}")

                # Normalise common label spellings to canonical Fake/Real.
                norm = {}
                for k, v in self._id2label.items():
                    lv = v.strip().lower()
                    if "fake" in lv or "false" in lv or lv in ("0", "fake"):
                        norm[k] = "Fake"
                    elif "real" in lv or "true" in lv or lv in ("1", "real"):
                        norm[k] = "Real"
                    else:
                        norm[k] = v
                self._id2label = norm

                self._loaded = True
                logger.info("Model ready on %s with labels %s", self._device, self._id2label)
            except Exception as exc:  # noqa: BLE001
                self._load_error = str(exc)
                logger.exception("Failed to load model from %s", source)
                raise ModelUnavailableError(
                    f"Model could not be loaded from '{source}': {exc}"
                ) from exc

    @property
    def loaded(self) -> bool:
        return self._loaded

    @property
    def load_error(self) -> str | None:
        return self._load_error

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def id2label(self) -> dict[int, str]:
        return dict(self._id2label)

    # --------------------------------------------------------------- inference
    def predict(self, text: str, max_length: int | None = None) -> PredictionResult:
        self.load()
        settings = get_settings()
        max_len = max_length or settings.model_max_length

        cleaned = clean_text(text)
        if not cleaned:
            raise ValueError("Text is empty after cleaning")

        # Headline emphasis: prepend the first line if input has multiple lines.
        model_input = cleaned

        start = time.perf_counter()
        enc = self._tokenizer(
            model_input,
            return_tensors="pt",
            truncation=True,
            max_length=max_len,
            padding=True,
            return_offsets_mapping=True,
        )
        offset_mapping = enc.pop("offset_mapping")[0].tolist()
        enc = {k: v.to(self._device) for k, v in enc.items()}
        truncated = len(self._tokenizer(model_input)["input_ids"]) > max_len

        with torch.no_grad():
            logits = self._model(**enc).logits[0]
            probs = torch.softmax(logits, dim=-1)

        prob_list = probs.detach().cpu().tolist()
        label_ids = sorted(range(len(prob_list)), key=lambda i: -prob_list[i])
        label_names = [self._id2label.get(i, f"class_{i}") for i in label_ids]
        label_probs = {name: round(prob_list[i], 4) for i, name in zip(label_ids, label_names)}

        best_idx_local = 0
        best_label_id = label_ids[best_idx_local]
        confidence = prob_list[best_label_id]
        prediction = label_names[best_idx_local]

        inference_ms = (time.perf_counter() - start) * 1000

        result = PredictionResult(
            text=cleaned,
            prediction=prediction,
            confidence=round(confidence, 4),
            probabilities=label_probs,
            label_order=[self._id2label.get(i, f"class_{i}") for i in sorted(self._id2label)],
            model_name=self._model_name,
            inference_ms=round(inference_ms, 2),
            truncated=truncated,
        )

        # Attribution only on reasonably sized inputs to bound latency.
        if len(model_input) <= 20000:
            try:
                self._add_attribution(result, enc, offset_mapping, best_label_id, model_input)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Attribution failed: %s", exc)
        return result

    # ------------------------------------------------------------ attribution
    def _add_attribution(
        self,
        result: PredictionResult,
        enc: dict,
        offset_mapping: list,
        target_label_id: int,
        text: str,
    ) -> None:
        """Gradient-based token attribution aggregated to words/sentences."""
        self._model.zero_grad(set_to_none=True)
        # Re-embed so gradients flow to input embeddings.
        inputs_embeds = self._model.get_input_embeddings()(enc["input_ids"])
        inputs_embeds.requires_grad_(True)
        inputs_embeds.retain_grad()

        outputs = self._model(
            inputs_embeds=inputs_embeds,
            attention_mask=enc["attention_mask"],
        )
        logit = outputs.logits[0, target_label_id]
        logit.backward()

        grads = inputs_embeds.grad[0].detach().cpu()  # [seq, hidden]
        # signed saliency: sum of absolute gradient components per token
        token_scores = grads.abs().sum(dim=-1).tolist()

        tokens = self._tokenizer.convert_ids_to_tokens(enc["input_ids"][0].tolist())
        special = set(self._tokenizer.all_special_tokens)

        attributions: list[Attribution] = []
        word_scores: dict[str, float] = {}
        word_positions: dict[str, tuple[int, int]] = {}

        for i, tok in enumerate(tokens):
            if tok in special:
                continue
            start, end = offset_mapping[i]
            if start is None or end is None or end <= start:
                continue
            score = token_scores[i] if i < len(token_scores) else 0.0
            surface = text[start:end]
            piece = tok.lstrip("Ġ▁")
            attributions.append(Attribution(token=surface or piece, score=score, start=start, end=end))
            key = surface.lower().strip(".,!?;:\"'()[]{}")
            if key:
                word_scores[key] = word_scores.get(key, 0.0) + score
                if key not in word_positions:
                    word_positions[key] = (start, end)

        ranked = sorted(attributions, key=lambda a: -a.score)
        result.top_tokens = ranked[:12]
        result.bottom_tokens = ranked[-6:][::-1] if len(ranked) > 6 else []

        # Sentence-level aggregation via character offsets
        sentences = _split_sentences(text)
        sent_scores: list[SentenceScore] = []
        cursor = 0
        for sent in sentences:
            idx = text.find(sent, cursor)
            if idx == -1:
                idx = cursor
            s_start, s_end = idx, idx + len(sent)
            cursor = s_end
            sc = sum(a.score for a in attributions if a.start is not None and s_start <= a.start < s_end)
            sent_scores.append(SentenceScore(text=sent, score=round(sc, 6)))
        result.sentence_scores = sorted(sent_scores, key=lambda s: -s.score)[:8]

        # stash word-level scores on result for explanation building
        result._word_scores = word_scores  # type: ignore[attr-defined]
        result._word_positions = word_positions  # type: ignore[attr-defined]


def _split_sentences(text: str) -> list[str]:
    import re

    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if p and p.strip()]


def get_model() -> FakeNewsModel:
    return FakeNewsModel.get()
