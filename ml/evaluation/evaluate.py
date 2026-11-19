"""Evaluate a trained checkpoint or HF model on the test split.

Usage:
  python -m ml.evaluation.evaluate --model ml/checkpoints/<name> [--max-length 256]
Writes ml/reports/evaluation_metrics.json (same schema as train_transformer).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import (accuracy_score, classification_report,
                             confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score)
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
SPLITS = ROOT / "data" / "processed" / "splits"
REPORTS = ROOT / "reports"
LABELS = ["Fake", "Real"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--max-length", type=int, default=256)
    args = ap.parse_args()

    test_df = pd.read_csv(SPLITS / "test.csv")
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = AutoModelForSequenceClassification.from_pretrained(args.model).to(device)
    model.eval()

    texts = test_df["model_text"].tolist()
    y = np.array([LABELS.index(l) for l in test_df["label"].tolist()])
    probs_all = []
    bs = 16
    with torch.no_grad():
        for i in range(0, len(texts), bs):
            enc = tokenizer(texts[i:i+bs], truncation=True, max_length=args.max_length,
                            padding=True, return_tensors="pt").to(device)
            logits = model(**enc).logits
            probs_all.append(torch.softmax(logits, dim=-1).cpu().numpy())
    probs = np.vstack(probs_all)
    preds = probs.argmax(axis=-1)

    metrics = {
        "accuracy": round(float(accuracy_score(y, preds)), 4),
        "precision_macro": round(float(precision_score(y, preds, average="macro", zero_division=0)), 4),
        "recall_macro": round(float(recall_score(y, preds, average="macro", zero_division=0)), 4),
        "f1_macro": round(float(f1_score(y, preds, average="macro", zero_division=0)), 4),
        "f1_weighted": round(float(f1_score(y, preds, average="weighted", zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y == 0, probs[:, 0])), 4) if len(set(y)) > 1 else None,
        "confusion_matrix": confusion_matrix(y, preds, labels=[0, 1]).tolist(),
        "labels": LABELS,
        "classification_report": classification_report(
            y, preds, labels=[0, 1], target_names=LABELS, output_dict=True, zero_division=0),
        "per_class": {
            name: {
                "precision": round(float(precision_score(y, preds, labels=[i], average=None, zero_division=0)[0]), 4),
                "recall": round(float(recall_score(y, preds, labels=[i], average=None, zero_division=0)[0]), 4),
                "f1": round(float(f1_score(y, preds, labels=[i], average=None, zero_division=0)[0]), 4),
                "support": int((y == i).sum()),
            }
            for i, name in enumerate(LABELS)
        },
        "model": args.model,
        "test_rows": len(test_df),
    }
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "evaluation_metrics.json").write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
