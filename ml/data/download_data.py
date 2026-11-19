"""Dataset acquisition for fake-news classification.

Supported sources:
  - welfake   : WELFake CSV mirrored on GitHub (real/fake news, ~72k items).
                https://github.com/ashleyou/WELFake  (CC-BY style research use;
                see repo README for exact terms)
  - fake_news : 'mrm8488/fake_news' on the Hugging Face hub (news.csv used by
                several public fake-news models). Columns: title, text, label.
  - csv       : any local CSV with text/title/label columns.

All sources are normalised to a common schema:
    text, title, label, source_id
Labels are kept as raw strings; the preprocessing stage maps them to
canonical classes (real/fake/other -> dropped or kept per config).
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

WELFAKE_URL = "https://raw.githubusercontent.com/ashleyou/WELFake/master/WELFake.csv"
HF_FAKE_NEWS = "mrm8488/fake_news"

CANONICAL = {"real": "Real", "fake": "Fake", "fake news": "Fake", "0": "Fake", "1": "Real"}


def _norm_label(v) -> str | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip().lower()
    return CANONICAL.get(s, s.title() if s not in ("true", "false") else ("Real" if s == "true" else "Fake"))


def download_welfare() -> pd.DataFrame:
    """WELFake: columns news_id, domain, title, date, label(0=fake,1=real), text."""
    out = RAW_DIR / "WELFake.csv"
    if not out.exists():
        print(f"Downloading WELFake from {WELFAKE_URL} ...")
        df = pd.read_csv(WELFAKE_URL, on_bad_lines="skip", low_memory=False)
        df.to_csv(out, index=False)
    else:
        print(f"Using cached {out}")
        df = pd.read_csv(out, on_bad_lines="skip", low_memory=False)
    df = df.rename(columns={"news_id": "source_id"})
    df["source"] = "WELFake"
    return df


def download_hf_fake_news() -> pd.DataFrame:
    """mrm8488/fake_news via the datasets library -> CSV cache."""
    from datasets import load_dataset

    out = RAW_DIR / "fake_news_hf.csv"
    if out.exists():
        print(f"Using cached {out}")
        return pd.read_csv(out)
    print(f"Loading HF dataset {HF_FAKE_NEWS} ...")
    ds = load_dataset(HF_FAKE_NEWS, split="train")
    df = ds.to_pandas()
    df["source_id"] = [hashlib.md5((t or "").encode()).hexdigest()[:12] for t in df.get("text", df.iloc[:, 0])]
    df["source"] = "fake_news_hf"
    df.to_csv(out, index=False)
    return df


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, on_bad_lines="skip", low_memory=False)
    if "source" not in df.columns:
        df["source"] = Path(path).stem
    if "source_id" not in df.columns:
        keycol = "title" if "title" in df.columns else df.columns[0]
        df["source_id"] = [hashlib.md5(str(v).encode()).hexdigest()[:12] for v in df[keycol]]
    return df


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Map heterogeneous schemas to text/title/label/source_id."""
    rename = {}
    for col in df.columns:
        c = col.strip().lower()
        if c in ("text", "content", "article", "body"):
            rename[col] = "text"
        elif c in ("title", "headline", "subject"):
            rename[col] = "title"
        elif c in ("label", "class", "y"):
            rename[col] = "label"
    df = df.rename(columns=rename)
    for need in ("text", "label"):
        if need not in df.columns:
            raise ValueError(f"Dataset missing required '{need}' column; found {list(df.columns)}")
    if "title" not in df.columns:
        df["title"] = ""
    df["text"] = df["text"].fillna("").astype(str)
    df["title"] = df["title"].fillna("").astype(str)
    df["label"] = df["label"].map(_norm_label)
    df = df[df["label"].isin(["Real", "Fake"])]
    df = df[(df["text"].str.len() > 30) & (df["text"].str.len() < 100000)]
    return df.reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["welfake", "fake_news", "csv", "all"], default="welfake")
    ap.add_argument("--csv", default=None, help="Path to CSV when --source csv")
    args = ap.parse_args()

    frames = []
    if args.source in ("welfake", "all"):
        frames.append(normalize(download_welfare()))
    if args.source in ("fake_news", "all"):
        frames.append(normalize(download_hf_fake_news()))
    if args.source == "csv":
        if not args.csv:
            sys.exit("--csv required with --source csv")
        frames.append(normalize(load_csv(args.csv)))

    df = pd.concat(frames, ignore_index=True)
    # combine title+text as model input; keep title separate for metadata
    df["model_text"] = (df["title"].str.strip() + "\n\n" + df["text"].str.strip()).str.strip()

    # dedupe on normalised model_text
    before = len(df)
    df["_key"] = df["model_text"].str.lower().str.replace(r"\s+", " ", regex=True)
    df = df.drop_duplicates(subset=["_key"]).drop(columns=["_key"])
    print(f"Dedup: {before} -> {len(df)} rows")
    print(df["label"].value_counts())
    print(df.groupby("source")["label"].value_counts().unstack(fill_value=0))

    proc_dir = ROOT / "data" / "processed"
    proc_dir.mkdir(parents=True, exist_ok=True)
    out = proc_dir / "dataset.csv"
    df.to_csv(out, index=False)
    print(f"Wrote {out} ({len(df)} rows)")


if __name__ == "__main__":
    main()
