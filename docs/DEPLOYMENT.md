# Deployment Guide

## Local development (recommended first step)

```bash
cp .env.example .env

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

The model checkpoint is downloaded from Hugging Face on first inference
(~500 MB for the default RoBERTa). Subsequent starts load from the HF cache.

## Database

- **SQLite (default):** zero config — `DATABASE_URL=sqlite:///./veritas.db`.
  Tables auto-create on startup.
- **PostgreSQL:**
  ```
  DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/veritas
  ```
  Run migrations: `cd backend && alembic upgrade head`.

## Docker Compose

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- API + Swagger: http://localhost:8000/docs

The compose file mounts a `veritas-data` volume for SQLite/Postgres data.
To use Postgres in compose, add a `db` service and point `DATABASE_URL` at it.

## Production checklist

- Set `APP_ENV=production`, strong `CORS_ORIGINS`, and `API_KEYS` if the API is
  exposed beyond the frontend.
- Put the app behind TLS (reverse proxy: nginx/Caddy/Traefik).
- Run uvicorn with multiple workers **only if** each worker can hold the model
  in memory; otherwise a single worker is safer on CPU.
- Bake the model into the image or a shared volume to avoid first-request
  download latency: set `MODEL_PATH=/models/<checkpoint>` and copy
  `ml/checkpoints/<name>` into the image.
- Set `HF_TOKEN` if using gated HF models.
- Structured logs go to stdout — ship via your platform's log collector.

## GPU training

Fine-tuning is CPU-capable but slow. For real training:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu121
python -m ml.training.train_transformer --model roberta-base \
    --epochs 3 --batch-size 32 --fp16 --max-length 256
```

Then point `MODEL_PATH` at `ml/checkpoints/<output-name>`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Model could not be loaded` | Check network/HF reachability; verify `MODEL_HF_ID`; check disk space for cache |
| Analysis returns 503 | Model failed to load — see backend logs; `/api/v1/model/info` shows the error |
| URL analysis 422 | URL blocked (private host, bad scheme) or extraction failed — expected behavior |
| Frontend shows no data | Confirm `NEXT_PUBLIC_API_URL` matches backend and CORS origins include the frontend origin |
| Slow first analysis | Model loads lazily on first request — expected (~10–30 s for RoBERTa on CPU) |
| `transformers`/`huggingface_hub` conflict | Keep `huggingface-hub==1.33.0` per requirements.txt |
