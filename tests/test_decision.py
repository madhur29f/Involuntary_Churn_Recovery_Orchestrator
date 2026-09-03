from services.api.decision import decide

def test_hard_decline_stops():
    assert decide({"decline_code":"payment_risk_check_failed"}).action == "stop"

def test_opt_out_stops():
    assert decide({"decline_code":"insufficient_funds","opted_out":True}).action == "stop"

def test_model_fallback_is_conservative_rule():
    result=decide({"decline_code":"card_declined"},model_available=False)
    assert (result.action,result.decided_by)==("retry_scheduled","rule")
