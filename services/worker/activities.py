"""Activities are replay-safe: all non-deterministic work is outside workflow code."""
from temporalio import activity
from services.api.decision import decide, as_payload
from services.simulation.engine import oracle

@activity.defn
async def classify_recovery(event: dict, attempts: int, model_available: bool = True) -> dict:
    return as_payload(decide(event, attempts=attempts, model_available=model_available))

@activity.defn
async def evaluate_simulated_payment(event: dict, policy: str) -> bool:
    return oracle(event, policy)
