"""Deterministic, explainable decision engine with a narrowly scoped timing model."""
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from .taxonomy import lookup

@dataclass
class Decision:
    category: str
    action: str
    scheduled_at: str | None
    channel: str | None
    decided_by: str
    model_confidence: float | None
    reason: str

def decide(event: dict, attempts: int = 0, model_available: bool = True, now: datetime | None = None) -> Decision:
    now = now or datetime.now(timezone.utc)
    taxon = lookup(event.get("decline_code", ""))
    if event.get("opted_out"):
        return Decision("hard", "stop", None, None, "rule", None, "Customer opted out; compliant stopping rule blocks all outreach and retries.")
    if taxon.category in {"hard", "business_error", "not_a_decline"}:
        channel = "email" if taxon.default_action == "card_update_prompt" else None
        return Decision(taxon.category, taxon.default_action, None, channel, "rule", None, taxon.reason)
    if attempts >= 3:
        return Decision(taxon.category, "stop", None, None, "rule", None, "Maximum of three recovery attempts reached.")
    if not model_available:
        when = now + timedelta(days=2)
        return Decision(taxon.category, "retry_scheduled", when.isoformat(), None, "rule", None, "Model unavailable; conservative two-day fallback retry.")
    code = event.get("decline_code")
    # Deliberately interpretable model proxy. Replaceable by services/model inference artifact.
    if code == "insufficient_funds":
        days, confidence, detail = 5, .74, "pay-cycle proximity"
    elif code == "card_declined":
        days, confidence, detail = 2, .61, "issuer declines often clear within 24–48 hours"
    else:
        days, confidence, detail = 1, .82, "transient technical-decline pattern"
    when = now + timedelta(days=days)
    return Decision(taxon.category, "retry_scheduled", when.isoformat(), None, "model", confidence,
                    f"Model selected retry in {days} day(s) from {detail}; attempt {attempts + 1} of 3.")

def as_payload(decision: Decision) -> dict:
    return asdict(decision)
