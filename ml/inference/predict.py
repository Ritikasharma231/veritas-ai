"""CLI demo of the inference pipeline (mirrors backend logic without DB)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.ml import predictor  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("text", nargs="?", help="Text to analyze")
    ap.add_argument("--file", help="Read text from file")
    args = ap.parse_args()

    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        text = args.text
    else:
        text = (
            "SHOCKING: Doctors hate this one weird trick! "
            "You won't believe what happens next. Act now before it's too late!"
        )

    out = predictor.analyze_text(text)
    print(json.dumps({
        "prediction": out.prediction,
        "confidence": out.confidence,
        "probabilities": out.probabilities,
        "model": out.model_name,
        "inference_ms": out.inference_ms,
        "top_tokens": dict(list(out.explanation["top_contributing_tokens"].items())[:8]),
        "sensationalism_score": out.linguistic_signals.get("sensationalism_score"),
    }, indent=2))


if __name__ == "__main__":
    main()
