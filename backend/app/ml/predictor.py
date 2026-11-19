"""High-level prediction orchestration: model inference + explanations."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..core.config import get_settings
from ..core.logging import logger
from . import linguistic, text_utils
from .model import Attribution, FakeNewsModel, ModelUnavailableError, PredictionResult, get_model

DISCLAIMER = (
    "This analysis reflects patterns learned by a machine-learning model from "
    "training data. It is an estimate of how the content resembles labeled "
    "examples — it is NOT a determination of factual truth, and it should not "
    "be used as the sole basis for any decision."
)

LABEL_GUIDANCE = {
    "Fake": "The text exhibits linguistic and stylistic patterns commonly associated with fabricated or misleading news in the training data.",
    "Real": "The text does not strongly exhibit patterns associated with fabricated news in the training data.",
}


@dataclass
class AnalysisOutput:
    prediction: str
    confidence: float
    probabilities: dict[str, float]
    explanation: dict
    linguistic_signals: dict
    model_name: str
    inference_ms: float
    truncated: bool
    title: str | None = None
    status: str = "completed"


def _class_tone(label: str) -> str:
    l = label.lower()
    if "fake" in l or "false" in l or "misleading" in l:
        return "error"
    if "real" in l or "true" in l or "authentic" in l or "credible" in l:
        return "success"
    return "warning"


def build_explanation(result: PredictionResult) -> dict:
    label = result.prediction
    tone = _class_tone(label)
    top = [a for a in result.top_tokens if len(a.token) > 2][:10]
    contrib = {a.token: round(a.score, 6) for a in top}

    # Positive vs negative contributors: tokens whose removal most changed the
    # predicted-class score get high saliency. We approximate direction by
    # whether the token appears in 'fake-associated' vs neutral contexts is not
    # available from gradient magnitude alone — so we report saliency only.
    strongest = top[0].token if top else None
    sentences = result.sentence_scores
    top_sentence = sentences[0].text[:240] + ("…" if len(sentences[0].text) > 240 else "") if sentences else None

    limitations = [
        "Model confidence is not a probability of truth; it reflects similarity to training examples.",
        "Attribution shows which words influenced the model, not whether those claims are factually correct.",
        "Short texts, satire, opinion, and non-English content are handled less reliably.",
        "The model can be fooled by adversarial phrasing and does not access external facts.",
    ]
    if result.truncated:
        limitations.append("Input exceeded the model's maximum sequence length and was truncated; the tail of the article was not analyzed.")

    return {
        "predicted_label": label,
        "tone": tone,
        "guidance": LABEL_GUIDANCE.get(label, "See class probabilities for detail."),
        "confidence_note": "Confidence is the model's softmax probability for the top class.",
        "top_contributing_tokens": contrib,
        "strongest_signal": strongest,
        "most_influential_sentence": top_sentence,
        "attribution_method": result.attribution_method,
        "attribution_note": (
            "Token scores come from gradient-based saliency (sensitivity of the "
            "predicted-class logit to each input token). Higher scores mean the "
            "model relied more heavily on that token."
        ),
        "probability_breakdown": result.probabilities,
        "limitations": limitations,
        "disclaimer": DISCLAIMER,
    }


def analyze_text(
    raw_text: str,
    *,
    title: str | None = None,
    source_url: str | None = None,
    input_type: str = "text",
    metadata: dict | None = None,
    model: FakeNewsModel | None = None,
) -> AnalysisOutput:
    """Run the full analysis pipeline on raw text."""
    model = model or get_model()

    cleaned = text_utils.clean_text(raw_text)
    if not cleaned:
        raise ValueError("No analyzable text content was provided.")

    cleaned = text_utils.truncate(cleaned, get_max_chars())

    headline, _body = text_utils.headline_and_body(cleaned)
    resolved_title = title or (headline[:300] if headline else None)

    try:
        pred: PredictionResult = model.predict(cleaned)
    except ModelUnavailableError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Inference failed")
        raise RuntimeError(f"Model inference failed: {exc}") from exc

    linguistic_signals = linguistic.analyze_linguistic_signals(cleaned)
    explanation = build_explanation(pred)
    explanation["title"] = resolved_title
    explanation["input_length_chars"] = len(cleaned)

    return AnalysisOutput(
        prediction=pred.prediction,
        confidence=pred.confidence,
        probabilities=pred.probabilities,
        explanation=explanation,
        linguistic_signals=linguistic_signals,
        model_name=pred.model_name,
        inference_ms=pred.inference_ms,
        truncated=pred.truncated,
        title=resolved_title,
        status="completed",
    )


def get_max_chars() -> int:
    from ..core.config import get_settings

    return get_settings().max_text_length


def model_status() -> dict:
    """Report whether the model is available without raising."""
    model = get_model()
    try:
        model.load()
        return {
            "available": True,
            "model_name": model.model_name,
            "labels": sorted(set(model.id2label.values())),
            "device": "cuda" if not get_settings().force_cpu and _cuda() else "cpu",
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "available": False,
            "model_name": model.model_name or get_settings().model_hf_id,
            "labels": get_settings().label_list,
            "device": "unknown",
            "error": str(exc),
        }


def _cuda() -> bool:
    try:
        import torch

        return torch.cuda.is_available()
    except Exception:  # noqa: BLE001
        return False
