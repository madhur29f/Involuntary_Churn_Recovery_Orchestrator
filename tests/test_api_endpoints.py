import hashlib
import hmac
import json
import pytest
from fastapi.testclient import TestClient
from services.api.main import app

import os

@pytest.fixture(autouse=True)
def isolated_db(tmp_path):
    test_db = tmp_path / "test_recovery.db"
    os.environ["RECOVERY_DB_PATH"] = str(test_db)
    yield
    os.environ.pop("RECOVERY_DB_PATH", None)

client = TestClient(app)

def test_simulation_seed_and_run_flow():
    seed_resp = client.post("/simulation/seed", json={"seed": 42, "population_size": 10})
    assert seed_resp.status_code == 200
    batch_data = seed_resp.json()
    batch_id = batch_data["batch_id"]
    assert batch_id == "batch_42_10"

    # Run naive policy
    run_naive = client.post("/simulation/run", json={"batch_id": batch_id, "policy": "naive"})
    assert run_naive.status_code == 200
    assert run_naive.json()["processed"] == 10

    # Run orchestrator policy
    run_orch = client.post("/simulation/run", json={"batch_id": batch_id, "policy": "orchestrator"})
    assert run_orch.status_code == 200
    assert run_orch.json()["processed"] == 10

    # Get metrics
    metrics_resp = client.get(f"/batches/{batch_id}/metrics")
    assert metrics_resp.status_code == 200
    metrics = metrics_resp.json()
    assert metrics["batch_id"] == batch_id
    assert "naive" in metrics["policies"]
    assert "orchestrator" in metrics["policies"]
    assert metrics["policies"]["orchestrator"]["recovery_rate"] >= metrics["policies"]["naive"]["recovery_rate"]

def test_subscription_audit_endpoint():
    # Seed single item
    client.post("/simulation/seed", json={"seed": 777, "population_size": 1})
    sub_id = "sub_777_000"

    client.post("/simulation/run", json={"batch_id": "batch_777_1", "policy": "orchestrator"})
    audit_resp = client.get(f"/subscriptions/{sub_id}/audit")
    assert audit_resp.status_code == 200
    trail = audit_resp.json()["trail"]
    assert len(trail) >= 2
    events = [entry["event"] for entry in trail]
    assert "event_ingested" in events
    assert "state_transition" in events

def test_webhook_signature_verification():
    import os
    os.environ["RAZORPAY_WEBHOOK_SECRET"] = "test_secret_123"
    payload = json.dumps({
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_001",
                    "subscription_id": "sub_test_001",
                    "error_reason": "card_declined"
                }
            }
        }
    }).encode()

    # Valid signature
    valid_sig = hmac.new(b"test_secret_123", payload, hashlib.sha256).hexdigest()
    resp = client.post(
        "/webhooks/razorpay",
        content=payload,
        headers={"X-Razorpay-Signature": valid_sig, "Content-Type": "application/json"}
    )
    assert resp.status_code == 200
    assert resp.json()["accepted"] is True

    # Invalid signature
    resp_bad = client.post(
        "/webhooks/razorpay",
        content=payload,
        headers={"X-Razorpay-Signature": "invalid_sig", "Content-Type": "application/json"}
    )
    assert resp_bad.status_code == 401
    os.environ.pop("RAZORPAY_WEBHOOK_SECRET", None)

def test_dashboard_endpoint():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Involuntary Churn Recovery Orchestrator" in resp.text
    assert "text/html" in resp.headers["content-type"]

def test_batch_subscriptions_endpoint():
    client.post("/simulation/seed", json={"seed": 99, "population_size": 5})
    resp = client.get("/batches/batch_99_5/subscriptions")
    assert resp.status_code == 200
    subs = resp.json()["subscriptions"]
    assert len(subs) == 5
    assert "decline_code" in subs[0]
    assert "category" in subs[0]
