# Architecture

## Request flow — text analysis

```
POST /api/v1/analyze/text {text, title?, save_history}
  └─ routes.analyze_text
       ├─ predictor.analyze_text
       │    ├─ text_utils.clean_text        (unicode NFKC, HTML strip, URL strip, whitespace)
       │    ├─ text_utils.truncate           (max_text_length, boundary-aware)
       │    ├─ FakeNewsModel.predict        (lazy singleton, GPU/CPU)
       │    │    ├─ tokenizer(text, truncation, max_length, offsets)
       │    │    ├─ model(**enc) → softmax probabilities
       │    │    └─ _add_attribution        (grad × input saliency → tokens/sentences)
       │    ├─ linguistic.analyze_linguistic_signals  (rule-based features)
       │    └─ build_explanation            (tokens, limitations, disclaimer)
       └─ persist Analysis row (SQLAlchemy) → AnalysisResponse
```

## Request flow — URL analysis

```
POST /api/v1/analyze/url {url}
  ├─ url_fetcher.validate_url     scheme allowlist, DNS → reject private/loopback/reserved
  ├─ fetch_article                httpx, no auto-redirects; each hop re-validated (SSRF)
  │                               content-type check, byte cap, timeout
  ├─ trafilatura.extract (+ BeautifulSoup fallback)
  └─ same analysis pipeline as text, with source metadata attached
```

`POST /analyze/url/preview` runs only the fetch/extract stage so the UI can show
extracted content before committing to inference.

## Backend layout (`backend/app/`)

| Module | Responsibility |
|---|---|
| `api/routes.py` | REST endpoints, request/response mapping, persistence |
| `core/config.py` | Pydantic-settings env config (single source of truth) |
| `core/security.py` | Per-IP rate limit + optional API-key middleware |
| `core/exceptions.py` | Centralized error handlers (no internals leaked) |
| `database/` | SQLAlchemy engine/session, `Analysis` model |
| `schemas/` | Pydantic request/response contracts |
| `services/url_fetcher.py` | SSRF-safe fetching + readability extraction |
| `services/stats.py` | Dashboard aggregates from stored analyses |
| `ml/text_utils.py` | Conservative text cleaning (preserves signals) |
| `ml/linguistic.py` | Rule-based stylistic feature extraction |
| `ml/model.py` | Lazy HF model wrapper + gradient token attribution |
| `ml/predictor.py` | Orchestration + explanation builder |

## ML layout (`ml/`)

| Path | Purpose |
|---|---|
| `data/download_data.py` | WELFake / HF dataset / CSV → normalized `dataset.csv` |
| `preprocessing/make_splits.py` | Seeded, label-stratified, source-group-aware splits |
| `training/train_tfidf.py` | TF-IDF + LogisticRegression baseline |
| `training/train_transformer.py` | HF Trainer fine-tuning w/ early stopping, metrics, reports |
| `evaluation/evaluate.py` | Test-set evaluation for any checkpoint |
| `inference/predict.py` | CLI demo of the same pipeline the API uses |
| `checkpoints/`, `reports/` | Model artifacts and evaluation JSON |

## Frontend layout (`frontend/`)

- `app/` — routes: `/` landing, `/analyze`, `/dashboard`, `/history`, `/model`
- `components/` — `Navbar`, `Footer`, `ThemeProvider`, `AnalyzeWorkspace`,
  `ResultsPanel`, `DashboardView`, `HistoryView`, `ModelView`, `SamplePreview`, `LiveStatus`, `ui`
- `lib/api.ts` — typed fetch client; `lib/types.ts` — shared contracts
- Dark-first theme via CSS variables; light theme via `.dark` class toggle

## Data model (`analyses` table)

`id, input_type, source_url, title, text, text_length, prediction, confidence,
probabilities(JSON), explanation(JSON), linguistic_signals(JSON), metadata(JSON),
model_name, inference_ms, status, error, created_at`

## Design decisions

- **Lazy model loading** — the transformer loads on first inference, not at
  startup, keeping boot fast and avoiding OOM in idle workers.
- **Gradient attribution over SHAP** — SHAP on transformers is prohibitively
  slow on CPU; gradient×input saliency gives token/sentence importance in a
  single backward pass and is honestly labeled as such.
- **Conservative cleaning** — we strip HTML/URLs/control chars but preserve
  punctuation, casing, and repetition because those are legitimate signals.
- **Source-group splits** — `source_id` groups are held within one split to
  reduce near-duplicate leakage across train/val/test.
- **Honest degradation** — model unavailable → 503; URL extraction failure →
  422 with reason; no fabricated outputs anywhere.
