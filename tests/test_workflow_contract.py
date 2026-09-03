from services.worker.workflows import RecoveryWorkflow

def test_workflow_has_stable_initial_state():
    workflow = RecoveryWorkflow()
    assert workflow.state() == {"current_state": "failed", "attempt_count": 0}
