import pytest
from services.model.predictor import predict_timing
from services.api.decision import decide

def test_model_predictor_inference():
    event = {
        "decline_code": "insufficient_funds",
        "timestamp": "2026-01-28T10:00:00Z",
        "subscription_age_days": 45,
        "amount": 99900,
    }
    pred = predict_timing(event, attempts=0)
    assert pred["delay_days"] in [1, 2, 3, 4, 5]
    assert 0.0 < pred["confidence"] <= 1.0
    assert "pay-cycle" in pred["explanation"]

def test_decision_uses_model_for_ambiguous_declines():
    event = {"decline_code": "insufficient_funds", "timestamp": "2026-01-15T00:00:00Z"}
    d = decide(event, model_available=True)
    assert d.decided_by == "model"
    assert d.action == "retry_scheduled"
    assert d.model_confidence is not None
    assert d.scheduled_at is not None

def test_decision_falls_back_to_rule_when_model_disabled():
    event = {"decline_code": "insufficient_funds"}
    d = decide(event, model_available=False)
    assert d.decided_by == "rule"
    assert d.action == "retry_scheduled"
    assert d.model_confidence is None
    assert "conservative two-day" in d.reason.lower()
