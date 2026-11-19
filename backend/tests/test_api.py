"""Tests that do NOT require the transformer model to be loaded."""
import pytest


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("ok", "degraded")
    assert "model_available" in body


def test_linguistic_signals_unit():
    from app.ml import linguistic
    sig = linguistic.analyze_linguistic_signals(
        "SHOCKING!!! You won't believe this!!! Act NOW! " * 5
    )
    assert sig["available"] is True
    assert sig["metrics"]["exclamation_marks"] > 0
    assert "sensationalism_score" in sig


def test_text_cleaning():
    from app.ml import text_utils
    dirty = "<p>Hello   world</p>\n\n\nVisit https://example.com now!!!"
    clean = text_utils.clean_text(dirty)
    assert "<p>" not in clean
    assert "https://" not in clean
    assert "  " not in clean


def test_text_analysis_validation(client):
    # empty text should 422
    r = client.post("/api/v1/analyze/text", json={"text": ""})
    assert r.status_code == 422


def test_url_validation_rejects_bad(client):
    r = client.post("/api/v1/analyze/url", json={"url": "ftp://example.com/x"})
    assert r.status_code == 422


def test_url_validation_rejects_localhost(client):
    r = client.post("/api/v1/analyze/url", json={"url": "http://localhost:8000/admin"})
    assert r.status_code == 422


def test_analyses_empty_list(client):
    r = client.get("/api/v1/analyses")
    assert r.status_code == 200
    body = r.json()
    assert "items" in body and "total" in body


def test_dashboard_stats(client):
    r = client.get("/api/v1/dashboard/stats")
    assert r.status_code == 200
    body = r.json()
    assert "total_analyses" in body
    assert "classification_distribution" in body
    assert body["data_source"] == "live"


def test_model_info(client):
    r = client.get("/api/v1/model/info")
    assert r.status_code == 200
    body = r.json()
    assert "available" in body
    assert "labels" in body


def test_model_metrics(client):
    r = client.get("/api/v1/model/metrics")
    assert r.status_code == 200
    assert "available" in r.json()
