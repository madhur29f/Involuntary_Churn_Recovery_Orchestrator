import pytest
from services.api.decision import decide
from services.api.taxonomy import TAXONOMY

def test_all_taxonomy_codes_have_deterministic_routes():
    """Ensure every Razorpay decline code resolves cleanly without unhandled exceptions."""
    for code, taxon in TAXONOMY.items():
        event = {"decline_code": code}
        decision = decide(event)
        assert decision.category == taxon.category
        if taxon.category in {"hard", "business_error", "not_a_decline"}:
            assert decision.decided_by == "rule"
            assert decision.action == taxon.default_action

def test_hard_risk_declines_stop_immediately():
    for code in ["payment_risk_check_failed", "card_lost", "card_stolen"]:
        d = decide({"decline_code": code})
        assert d.action == "stop"
        assert d.decided_by == "rule"

def test_card_expired_prompts_update_not_retry():
    d = decide({"decline_code": "card_expired"})
    assert d.action == "card_update_prompt"
    assert d.channel == "email"
    assert d.decided_by == "rule"

def test_business_error_escalates_to_ops_never_dunning():
    d = decide({"decline_code": "payment_method_not_enabled"})
    assert d.action == "escalate_ops"
    assert d.decided_by == "rule"

def test_opted_out_customer_stopping_rule():
    d = decide({"decline_code": "insufficient_funds", "opted_out": True})
    assert d.action == "stop"
    assert d.decided_by == "rule"
    assert "opted out" in d.reason.lower()

def test_max_attempts_stopping_rule():
    for attempts in [3, 4, 10]:
        d = decide({"decline_code": "insufficient_funds"}, attempts=attempts)
        assert d.action == "stop"
        assert d.decided_by == "rule"
        assert "maximum" in d.reason.lower()
