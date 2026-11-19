import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..core.logging import logger
from ..database import Analysis, AnalysisStatus, get_db
from ..ml import predictor
from ..ml.model import ModelUnavailableError
from ..schemas.schemas import (
    AnalysisListItem,
    AnalysisListResponse,
    AnalysisResponse,
    DashboardStatsResponse,
    HealthResponse,
    ModelInfoResponse,
    TextAnalyzeRequest,
    UrlAnalyzeRequest,
    UrlFetchResponse,
)
from ..services import stats as stats_service
from ..services.url_fetcher import UrlFetchError, fetch_article, validate_url

router = APIRouter()
settings = get_settings()


def _to_response(a: Analysis) -> AnalysisResponse:
    return AnalysisResponse(
        id=a.id,
        input_type=a.input_type,
        source_url=a.source_url,
        title=a.title,
        prediction=a.prediction,
        confidence=a.confidence,
        probabilities=a.probabilities,
        explanation=a.explanation,
        linguistic_signals=a.linguistic_signals,
        metadata=a.metadata_,
        model_name=a.model_name,
        inference_ms=a.inference_ms,
        status=a.status.value if hasattr(a.status, "value") else str(a.status),
        error=a.error,
        created_at=a.created_at.isoformat() if a.created_at else None,
    )


def _persist(db: Session, out: predictor.AnalysisOutput, *, input_type: str,
             source_url: str | None, text: str, metadata: dict | None,
             status_: AnalysisStatus = AnalysisStatus.COMPLETED,
             error: str | None = None) -> Analysis:
    record = Analysis(
        input_type=input_type,
        source_url=source_url,
        title=out.title,
        text=text[:50000],
        text_length=len(text),
        prediction=out.prediction,
        confidence=out.confidence,
        probabilities=out.probabilities,
        explanation=out.explanation,
        linguistic_signals=out.linguistic_signals,
        metadata_=metadata,
        model_name=out.model_name,
        inference_ms=out.inference_ms,
        status=status_,
        error=error,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.post("/analyze/text", response_model=AnalysisResponse)
def analyze_text(req: TextAnalyzeRequest, db: Session = Depends(get_db)):
    try:
        out = predictor.analyze_text(req.text, title=req.title, input_type="text")
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail="Analysis failed. Please try again.")

    if req.save_history:
        record = _persist(db, out, input_type="text", source_url=None,
                          text=req.text, metadata=None)
        resp = _to_response(record)
    else:
        resp = AnalysisResponse(
            prediction=out.prediction, confidence=out.confidence,
            probabilities=out.probabilities, explanation=out.explanation,
            linguistic_signals=out.linguistic_signals, model_name=out.model_name,
            inference_ms=out.inference_ms, status=out.status, title=out.title,
        )
    logger.info("text analysis -> %s (%.1f%%, %.0fms)", out.prediction, out.confidence * 100, out.inference_ms)
    return resp


@router.post("/analyze/url/preview", response_model=UrlFetchResponse)
def preview_url(req: UrlAnalyzeRequest):
    """Fetch + extract article text without running inference."""
    try:
        art = fetch_article(req.url)
    except UrlFetchError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return UrlFetchResponse(
        url=art.url,
        final_url=art.final_url,
        title=art.title,
        author=art.author,
        publish_date=art.publish_date,
        site_name=art.site_name,
        extractor=art.extractor,
        text_preview=art.text[:1500],
        text_length=len(art.text),
    )


@router.post("/analyze/url", response_model=AnalysisResponse)
def analyze_url(req: UrlAnalyzeRequest, db: Session = Depends(get_db)):
    try:
        art = fetch_article(req.url)
    except UrlFetchError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("URL fetch failed")
        raise HTTPException(status_code=502, detail="Could not retrieve the article. Check the URL and try again.")

    meta = {
        "source_url": art.final_url,
        "author": art.author,
        "publish_date": art.publish_date,
        "site_name": art.site_name,
        "extractor": art.extractor,
        "fetch_note": "Article content extracted from the page; metadata is as reported by the publisher and is not independently verified.",
    }
    try:
        out = predictor.analyze_text(
            art.text, title=art.title, source_url=art.final_url,
            input_type="url", metadata=meta,
        )
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=500, detail="Analysis failed after fetching the article.")

    if req.save_history:
        record = _persist(db, out, input_type="url", source_url=art.final_url,
                          text=art.text, metadata=meta)
        resp = _to_response(record)
    else:
        resp = AnalysisResponse(
            prediction=out.prediction, confidence=out.confidence,
            probabilities=out.probabilities, explanation=out.explanation,
            linguistic_signals=out.linguistic_signals, model_name=out.model_name,
            inference_ms=out.inference_ms, status=out.status,
            title=out.title, source_url=art.final_url, metadata=meta,
        )
    return resp


# ------------------------------------------------------------- analyses CRUD
@router.get("/analyses", response_model=AnalysisListResponse)
def list_analyses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    prediction: str | None = Query(None),
    q: str | None = Query(None, max_length=200),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    sort: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    stmt = select(Analysis)
    count_stmt = select(func.count(Analysis.id))
    if prediction:
        stmt = stmt.where(Analysis.prediction == prediction)
        count_stmt = count_stmt.where(Analysis.prediction == prediction)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(Analysis.title.ilike(like) | Analysis.text.ilike(like))
        count_stmt = count_stmt.where(Analysis.title.ilike(like) | Analysis.text.ilike(like))
    if date_from:
        try:
            d = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
            stmt = stmt.where(Analysis.created_at >= d)
            count_stmt = count_stmt.where(Analysis.created_at >= d)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid date_from format; use ISO 8601")
    if date_to:
        try:
            d = datetime.fromisoformat(date_to).replace(tzinfo=timezone.utc)
            stmt = stmt.where(Analysis.created_at <= d)
            count_stmt = count_stmt.where(Analysis.created_at <= d)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid date_to format; use ISO 8601")

    total = db.scalar(count_stmt) or 0
    order = Analysis.created_at.asc() if sort == "asc" else Analysis.created_at.desc()
    rows = db.execute(
        stmt.order_by(order).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()

    items = [
        AnalysisListItem(
            id=r.id, input_type=r.input_type, title=(r.title or "")[:140] or None,
            prediction=r.prediction,
            confidence=round(float(r.confidence), 4) if r.confidence is not None else None,
            source_url=r.source_url,
            created_at=r.created_at.isoformat() if r.created_at else "",
            status=r.status.value if hasattr(r.status, "value") else str(r.status),
        )
        for r in rows
    ]
    return AnalysisListResponse(
        items=items, total=int(total), page=page, page_size=page_size,
        pages=max(1, (int(total) + page_size - 1) // page_size),
    )


@router.get("/analyses/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(analysis_id: str, db: Session = Depends(get_db)):
    row = db.get(Analysis, analysis_id)
    if not row:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return _to_response(row)


@router.delete("/analyses/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_analysis(analysis_id: str, db: Session = Depends(get_db)):
    row = db.get(Analysis, analysis_id)
    if not row:
        raise HTTPException(status_code=404, detail="Analysis not found")
    db.delete(row)
    db.commit()
    return None


# ------------------------------------------------------------------ dashboard
@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
def dashboard_stats(db: Session = Depends(get_db)):
    return DashboardStatsResponse(**stats_service.get_dashboard_stats(db))


# ------------------------------------------------------------------ model info
@router.get("/model/info", response_model=ModelInfoResponse)
def model_info():
    status_info = predictor.model_status()
    metrics, metrics_source = _load_metrics()
    s = settings
    return ModelInfoResponse(
        available=status_info["available"],
        model_name=status_info["model_name"],
        labels=status_info["labels"],
        device=status_info["device"],
        error=status_info["error"],
        model_path=s.model_path or None,
        hf_id=None if s.model_path else s.model_hf_id,
        locally_finetuned=bool(s.model_path),
        metrics=metrics,
        metrics_source=metrics_source,
    )


def _load_metrics() -> tuple[dict | None, str | None]:
    """Load evaluation metrics produced by the ML pipeline, if present."""
    reports = settings.reports_dir
    candidates = [
        reports / "evaluation_metrics.json",
        reports / "comparison_report.json",
    ]
    for path in candidates:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return data, path.name
            except Exception:  # noqa: BLE001
                continue
    return None, None


@router.get("/model/metrics")
def model_metrics():
    metrics, source = _load_metrics()
    if metrics is None:
        return {"available": False, "detail": "No evaluation report found. Run the ML evaluation pipeline first.", "metrics": None}
    return {"available": True, "source": source, "metrics": metrics}


# ---------------------------------------------------------------------- health
@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)):
    db_ok = "ok"
    try:
        db.execute(select(func.count(Analysis.id))).scalar()
    except Exception:  # noqa: BLE001
        db_ok = "error"
    model_ok = False
    try:
        predictor.get_model().load()
        model_ok = True
    except Exception:  # noqa: BLE001
        model_ok = False
    return HealthResponse(
        status="ok" if db_ok == "ok" else "degraded",
        version="1.0.0",
        model_available=model_ok,
        database=db_ok,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
