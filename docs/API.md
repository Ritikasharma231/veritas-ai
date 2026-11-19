# API Reference

Base URL: `http://localhost:8000/api/v1` — Swagger UI at `/docs`.

All endpoints return JSON. Errors follow `{"detail": ...}`; validation errors
add an `errors` array. Stack traces and internals are never exposed.

## POST /analyze/text

Analyze raw text (article, headline, or claim).

```json
// request
{ "text": "Article text…", "title": "optional", "save_history": true }
```

```json
// 200 response (abridged)
{
  "id": "uuid", "input_type": "text", "title": "…",
  "prediction": "Real", "confidence": 0.97,
  "probabilities": {"Real": 0.97, "Fake": 0.03},
  "explanation": { "top_contributing_tokens": {...}, "limitations": [...], "disclaimer": "…" },
  "linguistic_signals": { "sensationalism_score": 0.0, "interpretation": [...] },
  "model_name": "…", "inference_ms": 1234.5, "status": "completed",
  "created_at": "…"
}
```

Errors: `400` empty text · `422` validation · `503` model unavailable · `500` inference failure.

## POST /analyze/url

Fetch (SSRF-safe) → extract readable text → analyze. Same response shape plus
`metadata` (author, publish_date, site_name, extractor, fetch_note) and
`source_url`.

```json
{ "url": "https://example.com/article", "save_history": true }
```

Errors: `422` invalid URL / blocked host / extraction failure · `502` upstream fetch failure.

## POST /analyze/url/preview

Fetch + extract only (no inference). Returns `{url, final_url, title, author,
publish_date, site_name, extractor, text_preview, text_length}`.

## GET /analyses

Query params: `page` (≥1), `page_size` (1–100), `prediction`, `q` (search),
`date_from`, `date_to` (ISO-8601), `sort` (`asc|desc`).

```json
{ "items": [...], "total": 0, "page": 1, "page_size": 20, "pages": 1 }
```

## GET /analyses/{id} · DELETE /analyses/{id}

Full stored analysis / `204` on delete. `404` when missing.

## GET /dashboard/stats

```json
{
  "total_analyses": 12,
  "classification_distribution": {"Real": 8, "Fake": 4},
  "avg_confidence": 0.91,
  "daily_trend": [{"date": "…", "total": 0, "Fake": 0, "Real": 0}],
  "confidence_histogram": [{"range": "0-20%", "count": 0}],
  "recent_activity": [...],
  "avg_inference_ms": 1450.2,
  "data_source": "live", "generated_at": "…"
}
```

All values are computed from the `analyses` table — no sample data.

## GET /model/info

```json
{
  "available": true, "model_name": "…", "labels": ["Fake","Real"],
  "device": "cpu", "locally_finetuned": false,
  "model_path": null, "hf_id": "…",
  "metrics": {…}|null, "metrics_source": "evaluation_metrics.json"|null,
  "error": null
}
```

## GET /model/metrics

`{ "available": true, "source": "evaluation_metrics.json", "metrics": {…} }`
or `{ "available": false, "detail": "No evaluation report found…" }`.

## GET /health

`{ "status": "ok|degraded", "version": "1.0.0", "model_available": bool, "database": "ok|error", "timestamp": "…" }`

## Security notes

- Rate limit: `RATE_LIMIT_PER_MINUTE` per IP (default 30) → `429`.
- Optional API keys: set `API_KEYS=k1,k2`; mutating endpoints then require `X-API-Key`.
- URL fetch: http(s) only, private/reserved IPs rejected (incl. redirect hops),
  `MAX_FETCH_BYTES` cap, `FETCH_TIMEOUT_SECONDS` timeout.
