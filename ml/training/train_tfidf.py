"""TF-IDF + Logistic Regression baseline.

This is the traditional-ML baseline required by the project spec. It is also
the graceful-degradation path: if no transformer checkpoint exists, the
backend can optionally fall back to this model (MODEL_BASELINE=tflr).
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, classification_report, f1_score,
                             precision_score, recall_score, roc_auc_score,
                             confusion_matrix)
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]
SPLITS = ROOT / "data" / "processed" / "splits"
CKPT = ROOT / "checkpoints"
REPORTS = ROOT / "reports"


def load(name: str) -> pd.DataFrame:
    return pd.read_csv(SPLITS / f"{name}.csv")


def evaluate(model, X_test, y_test, label_names) -> dict:
    probs = model.predict_proba(X_test)
    pred = model.predict(X_test)
    # align columns to label_names order
    classes = list(model.named_steps["clf"].classes_)
    out = {
        "accuracy": round(accuracy_score(y_test, pred), 4),
        "precision_macro": round(precision_score(y_test, pred, average="macro", zero_division=0), 4),
        "recall_macro": round(recall_score(y_test, pred, average="macro", zero_division=0), 4),
        "f1_macro": round(f1_score(y_test, pred, average="macro", zero_division=0), 4),
        "f1_weighted": round(f1_score(y_test, pred, average="weighted", zero_division=0), 4),
        "confusion_matrix": confusion_matrix(y_test, pred, labels=label_names).tolist(),
        "labels": label_names,
        "classification_report": classification_report(
            y_test, pred, labels=label_names, output_dict=True, zero_division=0
        ),
    }
    try:
        # binary roc-auc on the positive (Fake) class if present
        if len(classes) == 2:
            idx = classes.index("Fake") if "Fake" in classes else 1
            out["roc_auc"] = round(roc_auc_score((y_test == "Fake").astype(int), probs[:, idx]), 4)
    except Exception:
        pass
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-features", type=int, default=100000)
    ap.add_argument("--ngram", default="1,2")
    ap.add_argument("--C", type=float, default=2.0)
    args = ap.parse_args()

    CKPT.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)

    train, val, test = load("train"), load("val"), load("test")
    Xtr, ytr = train["model_text"].tolist(), train["label"].tolist()
    Xva, yva = val["model_text"].tolist(), val["label"].tolist()
    Xte, yte = test["model_text"].tolist(), test["label"].tolist()
    label_names = sorted(set(ytr) | set(yva) | set(yte))

    ngram_min, ngram_max = (int(x) for x in args.ngram.split(","))
    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(
            lowercase=True, ngram_range=(ngram_min, ngram_max),
            max_features=args.max_features, sublinear_tf=True,
            strip_accents="unicode", min_df=2,
        )),
        ("clf", LogisticRegression(C=args.C, max_iter=1000, class_weight="balanced", n_jobs=-1)),
    ])

    t0 = time.time()
    pipe.fit(Xtr, ytr)
    fit_s = time.time() - t0
    val_metrics = evaluate(pipe, Xva, yva, label_names)
    test_metrics = evaluate(pipe, Xte, yte, label_names)

    out_path = CKPT / "tfidf_logreg.joblib"
    joblib.dump({"pipeline": pipe, "labels": label_names}, out_path)

    report = {
        "model": "tfidf-logreg",
        "hyperparams": vars(args),
        "fit_seconds": round(fit_s, 2),
        "train_rows": len(train),
        "validation": val_metrics,
        "test": test_metrics,
        "trained_at": pd.Timestamp.utcnow().isoformat(),
    }
    (REPORTS / "baseline_tfidf_metrics.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({"model": "tfidf-logreg", "test": test_metrics}, indent=2))
    print(f"Saved {out_path}")


if __name__ == "__main__":
    main()
