import os
import pytest
import asyncio
from services.worker.workflows import RecoveryWorkflow

def test_workflow_state_contract():
    wf = RecoveryWorkflow()
    assert wf.state() == {"current_state": "failed", "attempt_count": 0}
    wf.record_payment_result(True)
    assert wf.payment_succeeded is True

def test_workflow_deterministic_stops():
    wf = RecoveryWorkflow()
    assert wf.current_state == "failed"
    assert wf.attempt_count == 0

@pytest.mark.skipif(not os.getenv("TEMPORAL_ADDRESS"), reason="Live Temporal server not configured")
def test_temporal_live_connection():
    from temporalio.client import Client
    async def _test():
        client = await Client.connect(os.getenv("TEMPORAL_ADDRESS"))
        assert client is not None
    asyncio.run(_test())
