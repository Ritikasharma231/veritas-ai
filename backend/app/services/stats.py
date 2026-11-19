"""Dashboard statistics computed from stored analyses."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database.models import Analysis, AnalysisStatus


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def get_dashboard_stats(db: Session) -> dict:
    total = db.scalar(select(func.count(Analysis.id))) or 0

    # classification distribution
    rows = db.execute(
        select(Analysis.prediction, func.count(Analysis.id))
        .where(Analysis.status == AnalysisStatus.COMPLETED, Analysis.prediction.isnot(None))
        .group_by(Analysis.prediction)
    ).all()
    distribution = {pred: int(cnt) for pred, cnt in rows}

    # confidence stats
    avg_conf = db.scalar(
        select(func.avg(Analysis.confidence)).where(Analysis.confidence.isnot(None))
    )
    avg_conf = round(float(avg_conf), 4) if avg_conf is not None else None

    # daily counts for last 14 days
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=13)
    daily_rows = db.execute(
        select(Analysis.created_at, Analysis.prediction)
        .where(Analysis.created_at >= since, Analysis.status == AnalysisStatus.COMPLETED)
        .order_by(Analysis.created_at)
    ).all()
    daily: dict[str, dict] = {}
    for created, pred in daily_rows:
        day = _aware(created).strftime("%Y-%m-%d")
        bucket = daily.setdefault(day, {"date": day, "total": 0, "Fake": 0, "Real": 0})
        bucket["total"] += 1
        if pred in ("Fake", "Real"):
            bucket[pred] += 1
    # fill missing days
    trend = []
    for i in range(14):
        d = (since + timedelta(days=i)).strftime("%Y-%m-%d")
        trend.append(daily.get(d, {"date": d, "total": 0, "Fake": 0, "Real": 0}))

    # confidence histogram (5 buckets)
    conf_rows = db.execute(
        select(Analysis.confidence).where(Analysis.confidence.isnot(None))
    ).all()
    buckets = [0] * 5
    for (c,) in conf_rows:
        if c is None:
            continue
        idx = min(int(float(c) * 5), 4)
        buckets[idx] += 1
    confidence_hist = [
        {"range": f"{i*20}-{(i+1)*20}%", "count": buckets[i]} for i in range(5)
    ]

    # recent activity
    recent = db.execute(
        select(Analysis.id, Analysis.title, Analysis.prediction, Analysis.confidence, Analysis.created_at)
        .order_by(Analysis.created_at.desc())
        .limit(8)
    ).all()
    recent_activity = [
        {
            "id": r.id,
            "title": (r.title or "Untitled")[:120],
            "prediction": r.prediction,
            "confidence": round(float(r.confidence), 4) if r.confidence is not None else None,
            "created_at": _aware(r.created_at).isoformat(),
        }
        for r in recent
    ]

    # avg inference latency
    avg_ms = db.scalar(select(func.avg(Analysis.inference_ms)).where(Analysis.inference_ms.isnot(None)))

    return {
        "total_analyses": int(total),
        "completed_analyses": int(total),
        "classification_distribution": distribution,
        "avg_confidence": avg_conf,
        "daily_trend": trend,
        "confidence_histogram": confidence_hist,
        "recent_activity": recent_activity,
        "avg_inference_ms": round(float(avg_ms), 1) if avg_ms is not None else None,
        "data_source": "live",
        "generated_at": now.isoformat(),
    }
