"""Temporal dispatch adapter. The API deliberately owns persistence; Temporal owns transitions."""
import os
from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from services.worker.workflows import RecoveryWorkflow

import temporalio.exceptions

async def execute_recovery(event: dict, policy: str) -> dict:
    client = await Client.connect(os.getenv("TEMPORAL_ADDRESS", "temporal:7233"))
    workflow_id = f"recovery-{event['subscription_id']}-{policy}"
    try:
        return await client.execute_workflow(
            RecoveryWorkflow.run,
            args=[event, policy, int(os.getenv("VIRTUAL_CLOCK_SECONDS", "0"))],
            id=workflow_id,
            task_queue=os.getenv("TEMPORAL_TASK_QUEUE", "recovery-orchestrator"),
            id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE,
        )
    except temporalio.exceptions.WorkflowAlreadyStartedError:
        handle = client.get_workflow_handle(workflow_id)
        try:
            await handle.terminate(reason="Restarted by simulation run")
        except Exception:
            pass
        return await client.execute_workflow(
            RecoveryWorkflow.run,
            args=[event, policy, int(os.getenv("VIRTUAL_CLOCK_SECONDS", "0"))],
            id=f"{workflow_id}-{os.urandom(4).hex()}",
            task_queue=os.getenv("TEMPORAL_TASK_QUEUE", "recovery-orchestrator"),
            id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE,
        )
