# VERITAS AI — Intelligence Beyond Headlines

A production-oriented platform for analyzing news articles, headlines, and claims
with transformer-based NLP. It estimates how content resembles labeled
real/fake news patterns and explains *why* — through class probabilities,
gradient-based token attribution, and transparent rule-based linguistic signals.

> **Honesty note:** predictions are statistical estimates of stylistic similarity
> to training data. They are **not** verdicts of factual truth, and the platform
> never claims independent fact verification.

---

## Table of contents

- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- ( [Quick start](#quick-start-local) · [ML pipeline](#machine-learning-pipeline) · [API](#api) · [Docker](#docker-deployment) · [Docs](#documentation) · [Limitations](#limitations--ethics) )

## Architecture

```
┌────────────┐   REST/JSON   ┌──────────────────────────┐   ┌────────────────────┐
│  Next.js   │──────────────▶│  FastAPI backend          │──▶│  Transformer model │
│  frontend  │               │  /api/v1                  │   │  (HF checkpoint)   │
│  (React+TS)│◀──────────────│  analyze · history ·      │   └────────────────────┘
└────────────┘               │  dashboard · model info   │
                             └───────┬──────────┬───────┘
                                     │          │
                              ┌──────▼───┐  ┌───▼──────┐
                              │ SQLite / │  │ trafilatura │
                              │ Postgres │  │ URL fetch  │
                              │ (SQLA)   │  │ (SSRF-safe)│
                              └──────────┘  └──────────┘
```

- `frontend/` — Next.js 15 (App Router), TypeScript, Tailwind CSS, Framer Motion, Recharts, Lucide.
- `backend/` — FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic, pytest.
- `ml/` — dataset acquisition, preprocessing, training, evaluation, inference utilities.
- `scripts/` — end-to-end training pipeline scripts.
- `docs/` — detailed documentation.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS 3, Framer Motion, Recharts, Lucide |
| Backend | Python 3.12+, FastAPI, Uvicorn, Pydantic v2, SQLAlchemy 2, Alembic |
| ML/NLP | PyTorch, Hugging Face Transformers, scikit-learn, pandas, NumPy, SHAP (available), trafilatura |
| Database | PostgreSQL (preferred) / SQLite (dev fallback) |
| Infra | Docker, Docker Compose, env-based config, structured logging |

## Quick start (local)

### Prerequisites
- Python 3.12+ and Node.js 20+
- ~2 GB disk for the default model download on first run

### 1. Configure
```bash
cp .env.example .env
```
Defaults work out of the box: SQLite DB, pretrained `hamzab/roberta-fake-news-classification`
checkpoint auto-downloaded from Hugging Face on first request.

### 2. Backend
```bash
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --reload --port 8000
```
API docs: http://localhost:8000/docs

### 3. Frontend
```bash
cd frontend
npm install
npm run dev        # http://localhost:3000
```

### 4. Verify
```bash
curl http://localhost:8000/api/v1/health
curl -X POST http://localhost:8000/api/v1/analyze/text \
  -H "Content-Type: application/json" \
  -d '{"text": "Your news text here…"}'
```

## Machine learning pipeline

```bash
# 1. Acquire + normalize data (WELFake by default)
python -m ml.data.download_data --source welfake      # or: fake_news | csv | all

# 2. Leakage-controlled stratified splits (train/val/test)
python -m ml.preprocessing.make_splits --seed 42

# 3. Traditional baseline: TF-IDF + Logistic Regression
python -m ml.training.train_tfidf

# 4. Transformer fine-tuning (configurable architecture)
python -m ml.training.train_transformer \
    --model distilbert-base-uncased --max-length 256 --epochs 2
# candidates: roberta-base, facebook/bart-base, microsoft/deberta-v3-base

# 5. Evaluate any checkpoint on the untouched test split
python -m ml.evaluation.evaluate --model ml/checkpoints/<name>
```

Or run everything: `./scripts/train_pipeline.sh` (see `scripts/train_pipeline.ps1` for Windows).

Training writes `ml/reports/evaluation_metrics.json` and
`ml/reports/comparison_report.json`; the `/api/v1/model/info` and
`/api/v1/model/metrics` endpoints surface them in the UI.

To use your own checkpoint in the API, set in `.env`:
```
MODEL_PATH=../ml/checkpoints/<your-checkpoint>
```

### Model selection rationale
- The default inference checkpoint (`hamzab/roberta-fake-news-classification`)
  is a RoBERTa sequence classifier with explicit FAKE/TRUE labels — chosen for
  its explicit label mapping and reasonable CPU inference cost.
- For local fine-tuning, DistilBERT is the CPU-friendly default; RoBERTa-base
  and DeBERTa-v3-base are supported via `--model` when GPU resources permit.
- The TF-IDF + Logistic Regression baseline provides a documented comparison
  point and a degradation path.

## API

Base URL: `/api/v1` — interactive docs at `/docs`.

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/analyze/text` | Analyze raw text/headline/claim |
| POST | `/analyze/url` | Fetch (SSRF-safe) + extract + analyze an article URL |
| POST | `/analyze/url/preview` | Fetch + extract article text without inference |
| GET | `/analyses` | List history (search, filter, sort, paginate) |
| GET | `/analyses/{id}` | Full stored analysis |
| DELETE | `/analyses/{id}` | Delete an analysis |
| GET | `/dashboard/stats` | Live aggregate statistics |
| GET | `/model/info` | Model availability, provenance, metrics |
| GET | `/model/metrics` | Evaluation report JSON |
| GET | `/health` | Liveness + model/DB status |

Security: Pydantic validation, rate limiting (per-IP, configurable), optional
`X-API-Key` auth via `API_KEYS`, CORS allowlist, SSRF protection on URL fetch
(scheme allowlist, DNS private-IP rejection, redirect re-validation, size cap,
timeout), generic error responses (no stack traces).

## Database

SQLAlchemy models in `backend/app/database/models.py`; Alembic migrations in
`backend/alembic/`. Tables are auto-created on startup for convenience;
for managed deployments run:

```bash
cd backend
alembic upgrade head
```

PostgreSQL: set `DATABASE_URL=postgresql+psycopg2://user:pass@host/db` and
install `psycopg2-binary` (already in requirements).

## Docker deployment

```bash
cp .env.example .env
docker compose up --build
```
- Frontend → http://localhost:3000, API → http://localhost:8000/docs
- The model checkpoint is downloaded from Hugging Face on first inference.
  To bake it into the image, set `MODEL_PATH` to a mounted/copy checkpoint.

## Testing

```bash
cd backend
pytest tests -q          # API, validation, URL security, inference, ML utils
cd ../frontend && npm run build   # type-checks + production build
```

## Documentation

- `docs/ARCHITECTURE.md` — system design, data flow, component details
- `docs/MODEL.md` — datasets, preprocessing, training, evaluation methodology
- `docs/API.md` — endpoint reference with examples
- `docs/DEPLOYMENT.md` — production deployment guide

## Limitations & ethics

- The model classifies *style*, not truth. Confidence ≠ correctness.
- Trained/evaluated on English news datasets (WELFake and/or `mrm8488/fake_news`);
  satire, opinion, non-English content, and rapidly evolving events reduce reliability.
- URL extraction depends on the publisher's page; paywalls/JS-heavy pages may fail
  and the API reports that honestly rather than guessing.
- No claim-verification against live external sources is performed; the platform
  surfaces linguistic and model signals for human judgment.
- Always verify important information against primary sources.
