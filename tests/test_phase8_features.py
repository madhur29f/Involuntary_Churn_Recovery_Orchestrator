import pytest
from fastapi.testclient import TestClient
from services.api.main import app
from services.api.store import set_system_state, get_system_state
from services.worker.workflows import RecoveryWorkflow
import asyncio

client = TestClient(app)

def test_chaos_worker_endpoints():
    res_kill = client.post("/chaos/worker/kill")
    assert res_kill.status_code == 200
    assert res_kill.json()["status"] == "killed"
    assert get_system_state("worker_chaos_paused") == "1"

    res_stat = client.get("/chaos/worker/status")
    assert res_stat.status_code == 200
    assert res_stat.json()["status"] == "killed"

    res_restart = client.post("/chaos/worker/restart")
    assert res_restart.status_code == 200
    assert res_restart.json()["status"] == "running"
    assert get_system_state("worker_chaos_paused") == "0"

def test_multi_seed_statistical_evaluation():
    res = client.post("/simulation/multi-seed", json={"seeds": 5, "population_size": 20, "start_seed": 100})
    assert res.status_code == 200
    data = res.json()
    assert data["seeds_evaluated"] == 5
    assert data["population_per_seed"] == 20
    assert "mean_naive_rate" in data
    assert "mean_orchestrator_rate" in data
    assert "mean_lift_delta" in data
    assert "confidence_interval_95" in data
    assert len(data["ci_range"]) == 2
    assert "cfo_metrics" in data
    assert data["cfo_metrics"]["network_fees_saved_inr"] >= 0
    assert data["cfo_metrics"]["fraud_retries_prevented_pct"] == 100.0
    assert len(data["distribution"]) == 5

def test_card_network_30d_cap():
    wf = RecoveryWorkflow()
    event = {
        "id": "evt_test_capped",
        "subscription_id": "sub_capped",
        "decline_code": "insufficient_funds",
        "prior_attempts_30d": 15
    }
    result = asyncio.run(wf.run(event, "orchestrator"))
    assert result["state"] == "stopped"
    assert result["terminal_reason"] == "capped_by_network_policy"
    assert result["decision"]["action"] == "stop"

def test_razorpay_launcher_ingestion():
    payload = {
        "entity": "event",
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_launcher_test",
                    "amount": 99900,
                    "currency": "INR",
                    "status": "failed",
                    "subscription_id": "sub_launcher_test",
                    "error_reason": "insufficient_funds"
                }
            }
        }
    }
    res = client.post("/webhooks/razorpay", json=payload)
    assert res.status_code == 200
    assert res.json()["accepted"] is True
