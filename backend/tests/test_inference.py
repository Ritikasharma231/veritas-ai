"""Inference tests — skipped automatically if the model cannot be downloaded."""
import pytest

from app.ml.model import ModelUnavailableError, get_model
from app.ml import predictor


@pytest.fixture(scope="module")
def model():
    m = get_model()
    try:
        m.load()
    except ModelUnavailableError:
        pytest.skip("Model unavailable (no network / no checkpoint)")
    return m


def test_model_loads(model):
    assert model.loaded
    assert model.id2label


def test_prediction_shape(model):
    res = model.predict(
        "The government announced new economic data on Tuesday, "
        "according to official statistics released this morning."
    )
    assert res.prediction in res.probabilities
    assert abs(sum(res.probabilities.values()) - 1.0) < 0.01
    assert res.confidence == max(res.probabilities.values())
    assert res.inference_ms > 0


def test_attribution_tokens(model):
    res = model.predict("Breaking news: major earthquake strikes capital city.")
    assert len(res.top_tokens) > 0
    assert all(t.score >= 0 for t in res.top_tokens)


def test_analyze_text_output(model):
    out = predictor.analyze_text(
        "Scientists confirmed the discovery of a new species in the Amazon rainforest."
    )
    assert out.status == "completed"
    assert out.prediction
    assert out.explanation["disclaimer"]
    assert out.linguistic_signals["available"] is True
