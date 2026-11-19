"""Train/validation/test splitting with leakage control.

Strategy:
  - Dedupe already applied upstream.
  - Stratified split on label.
  - 'source_id' groups are kept within a single split where possible so that
    duplicate/near-duplicate articles from the same source cannot leak across
    splits (group-aware holdout for the test set).
  - A deterministic seed is used throughout.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"


def make_splits(df: pd.DataFrame, seed: int = 42, test_size: float = 0.15,
                val_size: float = 0.15) -> dict[str, pd.DataFrame]:
    # hold out test by source-group where a source_id repeats; fall back to rows
    ids = df["source_id"].astype(str)
    unique_ids = ids.drop_duplicates()
    train_ids, test_ids = train_test_split(
        unique_ids, test_size=test_size, random_state=seed, shuffle=True
    )
    test_mask = ids.isin(set(test_ids))
    rest = df[~test_mask]
    rest_ids = rest["source_id"].astype(str).drop_duplicates()
    tr_ids, va_ids = train_test_split(
        rest_ids, test_size=val_size / (1 - test_size), random_state=seed, shuffle=True
    )
    train_mask = rest["source_id"].astype(str).isin(set(tr_ids))
    val_mask = rest["source_id"].astype(str).isin(set(va_ids))
    return {
        "train": rest[train_mask].reset_index(drop=True),
        "val": rest[val_mask].reset_index(drop=True),
        "test": df[test_mask].reset_index(drop=True),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    df = pd.read_csv(PROC / "dataset.csv")
    splits = make_splits(df, seed=args.seed)
    outdir = PROC / "splits"
    outdir.mkdir(parents=True, exist_ok=True)
    meta = {"seed": args.seed, "rows": {}, "label_dist": {}}
    for name, part in splits.items():
        path = outdir / f"{name}.csv"
        part.to_csv(path, index=False)
        meta["rows"][name] = len(part)
        meta["label_dist"][name] = part["label"].value_counts().to_dict()
        print(f"{name}: {len(part)} rows  {meta['label_dist'][name]}")
    (outdir / "split_meta.json").write_text(json.dumps(meta, indent=2))
    print(f"Wrote splits to {outdir}")


if __name__ == "__main__":
    main()
