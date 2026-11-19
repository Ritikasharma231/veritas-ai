"""Transformer fine-tuning for fake-news classification.

Fine-tunes a pretrained sequence classifier (default: distilbert-base-uncased;
roberta-base / deberta-v3-base supported via --model) on the processed splits.

Features: AdamW, linear warmup+decay schedule, gradient clipping, early
stopping on validation macro-F1, best-checkpoint selection, full metrics on
the untouched test set, and a comparison/evaluation JSON report consumed by
the backend /model/info endpoint.

CPU-friendly defaults: small max_length, modest epochs. On CPU, prefer
--model distilbert-base-uncased or a smaller variant.
"""
from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset
from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                          EarlyStoppingCallback, Trainer, TrainingArguments,
                          get_linear_schedule_with_warmup)
from sklearn.metrics import (accuracy_score, classification_report,
                             confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score)

ROOT = Path(__file__).resolve().parents[1]
SPLITS = ROOT / "data" / "processed" / "splits"
CKPT_ROOT = ROOT / "checkpoints"
REPORTS = ROOT / "reports"

LABELS = ["Fake", "Real"]  # canonical order; dataset only contains these


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


class NewsDataset(Dataset):
    def __init__(self, df: pd.DataFrame, tokenizer, max_length: int):
        self.texts = df["model_text"].tolist()
        self.labels = [LABELS.index(l) for l in df["label"].tolist()]
        self.tok = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, i):
        enc = self.tok(
            self.texts[i], truncation=True, max_length=self.max_length,
            padding="max_length", return_tensors="pt",
        )
        return {
            "input_ids": enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "labels": torch.tensor(self.labels[i], dtype=torch.long),
        }


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    probs = torch.softmax(torch.tensor(logits), dim=-1).numpy()
    out = {
        "accuracy": float(accuracy_score(labels, preds)),
        "f1_macro": float(f1_score(labels, preds, average="macro", zero_division=0)),
        "precision_macro": float(precision_score(labels, preds, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(labels, preds, average="macro", zero_division=0)),
    }
    try:
        # positive class = Fake -> index 0 in LABELS
        out["roc_auc"] = float(roc_auc_score(labels == 0, probs[:, 0]))
    except Exception:
        pass
    return out


def full_test_report(model, tokenizer, test_df: pd.DataFrame, max_length: int,
                     device: str) -> dict:
    model.eval()
    texts = test_df["model_text"].tolist()
    y = np.array([LABELS.index(l) for l in test_df["label"].tolist()])
    all_probs = []
    bs = 16
    with torch.no_grad():
        for i in range(0, len(texts), bs):
            batch = texts[i:i + bs]
            enc = tokenizer(batch, truncation=True, max_length=max_length,
                            padding=True, return_tensors="pt").to(device)
            logits = model(**enc).logits
            probs = torch.softmax(logits, dim=-1).cpu().numpy()
            all_probs.append(probs)
    probs = np.vstack(all_probs)
    preds = probs.argmax(axis=-1)
    return {
        "accuracy": round(float(accuracy_score(y, preds)), 4),
        "precision_macro": round(float(precision_score(y, preds, average="macro", zero_division=0)), 4),
        "recall_macro": round(float(recall_score(y, preds, average="macro", zero_division=0)), 4),
        "f1_macro": round(float(f1_score(y, preds, average="macro", zero_division=0)), 4),
        "f1_weighted": round(float(f1_score(y, preds, average="weighted", zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y == 0, probs[:, 0])), 4) if len(set(y)) > 1 else None,
        "confusion_matrix": confusion_matrix(y, preds, labels=[0, 1]).tolist(),
        "labels": LABELS,
        "classification_report": classification_report(
            y, preds, labels=[0, 1], target_names=LABELS,
            output_dict=True, zero_division=0,
        ),
        "per_class": {
            name: {
                "precision": round(float(precision_score(y, preds, labels=[i], average=None, zero_division=0)[0]), 4),
                "recall": round(float(recall_score(y, preds, labels=[i], average=None, zero_division=0)[0]), 4),
                "f1": round(float(f1_score(y, preds, labels=[i], average=None, zero_division=0)[0]), 4),
                "support": int((y == i).sum()),
            }
            for i, name in enumerate(LABELS)
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="distilbert-base-uncased",
                    help="HF model id or local path")
    ap.add_argument("--max-length", type=int, default=256)
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--eval-batch-size", type=int, default=32)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--warmup-ratio", type=float, default=0.06)
    ap.add_argument("--weight-decay", type=float, default=0.01)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-train-rows", type=int, default=0, help="0 = all")
    ap.add_argument("--output-name", default=None)
    ap.add_argument("--fp16", action="store_true")
    args = ap.parse_args()

    seed_everything(args.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    train_df = pd.read_csv(SPLITS / "train.csv")
    val_df = pd.read_csv(SPLITS / "val.csv")
    test_df = pd.read_csv(SPLITS / "test.csv")
    if args.max_train_rows:
        train_df = train_df.sample(n=min(args.max_train_rows, len(train_df)), random_state=args.seed)

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model, num_labels=len(LABELS), id2label={i: l for i, l in enumerate(LABELS)},
        label2id={l: i for i, l in enumerate(LABELS)},
    )
    model.to(device)

    train_ds = NewsDataset(train_df, tokenizer, args.max_length)
    val_ds = NewsDataset(val_df, tokenizer, args.max_length)

    CKPT_ROOT.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out_name = args.output_name or f"{Path(args.model).name}-{stamp}"
    out_dir = CKPT_ROOT / out_name

    training_args = TrainingArguments(
        output_dir=str(out_dir / "trainer"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.eval_batch_size,
        learning_rate=args.lr,
        weight_decay=args.weight_decay,
        warmup_ratio=args.warmup_ratio,
        lr_scheduler_type="linear",
        optim="adamw_torch",
        max_grad_norm=1.0,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="f1_macro",
        greater_is_better=True,
        logging_steps=50,
        report_to=[],
        fp16=args.fp16 and device == "cuda",
        seed=args.seed,
        dataloader_num_workers=0,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=1)],
    )

    t0 = time.time()
    trainer.train()
    train_seconds = time.time() - t0

    # save final model + tokenizer
    model.save_pretrained(out_dir)
    tokenizer.save_pretrained(out_dir)

    val_metrics = trainer.evaluate()
    test_metrics = full_test_report(model, tokenizer, test_df, args.max_length, device)

    report = {
        "model": args.model,
        "checkpoint": str(out_dir),
        "hyperparams": vars(args),
        "labels": LABELS,
        "train_rows": len(train_df),
        "val_rows": len(val_df),
        "test_rows": len(test_df),
        "train_seconds": round(train_seconds, 1),
        "validation": val_metrics,
        "test": test_metrics,
        "trained_at": pd.Timestamp.utcnow().isoformat(),
        "device": device,
    }
    (REPORTS / "evaluation_metrics.json").write_text(json.dumps(report, indent=2))
    # comparison report merges with baseline if present
    comp_path = REPORTS / "comparison_report.json"
    comparison = {"transformer": report}
    base_path = REPORTS / "baseline_tfidf_metrics.json"
    if base_path.exists():
        comparison["tfidf_logreg"] = json.loads(base_path.read_text())
    comp_path.write_text(json.dumps(comparison, indent=2))

    print(json.dumps({"test": test_metrics}, indent=2))
    print(f"Saved checkpoint -> {out_dir}")
    print(f"Reports -> {REPORTS}")


if __name__ == "__main__":
    main()
