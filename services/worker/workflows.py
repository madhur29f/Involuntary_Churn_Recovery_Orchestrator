"""A bounded, signalable Temporal state machine per subscription and policy."""
from datetime import timedelta
from temporalio import workflow
with workflow.unsafe.imports_passed_through():
    from .activities import classify_recovery, evaluate_simulated_payment

@workflow.defn
class RecoveryWorkflow:
    def __init__(self):
        self.current_state = "failed"
        self.attempt_count = 0
        self.payment_succeeded: bool | None = None

    @workflow.query
    def state(self) -> dict:
        return {"current_state": self.current_state, "attempt_count": self.attempt_count}

    @workflow.signal
    def record_payment_result(self, succeeded: bool) -> None:
        self.payment_succeeded = succeeded

    @workflow.run
    async def run(self, event: dict, policy: str, virtual_delay_seconds: int = 0) -> dict:
        decision = None
        # This loop, including the maximum-attempts stopping rule, is workflow-owned.
        while self.attempt_count < 3:
            # Card-network compliance floor: Visa/Mastercard mandate <= 15 retries in rolling 30 days
            prior_30d = event.get("prior_attempts_30d", 0)
            if prior_30d + self.attempt_count >= 15:
                self.current_state = "stopped"
                if not decision:
                    decision = {"action": "stop", "category": "hard_decline", "reason": "capped_by_network_policy"}
                decision["reason"] = "Visa/Mastercard 15-retry rolling limit reached. Capped by network policy."
                return {"state": self.current_state, "attempt_count": self.attempt_count, "decision": decision,
                        "terminal_reason": "capped_by_network_policy"}

            decision_event = event if policy != "naive" else {**event, "decline_code": "card_declined", "opted_out": False}
            decision = await workflow.execute_activity(
                classify_recovery,
                args=[decision_event, self.attempt_count, policy != "naive"],
                start_to_close_timeout=timedelta(seconds=30)
            )
            if policy == "naive":
                decision["reason"] = "Naive fixed two-day retry; decline category ignored."
            action = decision["action"]
            if action in {"stop", "escalate_ops", "card_update_prompt"}:
                self.current_state = "stopped" if action == "stop" else "awaiting_customer_or_ops"
                return {"state": self.current_state, "attempt_count": self.attempt_count, "decision": decision,
                        "terminal_reason": decision["reason"]}
            self.current_state = "retry_scheduled"
            self.attempt_count += 1
            if virtual_delay_seconds:
                await workflow.sleep(timedelta(seconds=virtual_delay_seconds))
            self.current_state = "retry_attempted"
            if self.payment_succeeded is None:
                self.payment_succeeded = await workflow.execute_activity(
                    evaluate_simulated_payment,
                    args=[event, policy],
                    start_to_close_timeout=timedelta(seconds=30)
                )
            if self.payment_succeeded:
                self.current_state = "recovered"
                return {"state": self.current_state, "attempt_count": self.attempt_count, "decision": decision,
                        "terminal_reason": "payment_recovered"}
        self.current_state = "exhausted"
        return {"state": self.current_state, "attempt_count": self.attempt_count, "decision": decision,
                "terminal_reason": "Maximum of three recovery attempts reached."}
