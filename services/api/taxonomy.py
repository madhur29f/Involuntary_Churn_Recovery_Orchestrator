"""Razorpay-shaped decline taxonomy. Rules in this module are the safety floor."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Taxon:
    category: str
    default_action: str
    reason: str

TAXONOMY = {
    "payment_risk_check_failed": Taxon("hard", "stop", "Risk/fraud signal: blind retries are prohibited."),
    "international_transaction_not_allowed": Taxon("hard", "card_update_prompt", "Customer must enable international transactions before retry."),
    "card_expired": Taxon("hard", "card_update_prompt", "Expired payment method needs replacement, not a retry."),
    "card_lost": Taxon("hard", "stop", "Lost/stolen card: no further collection attempts."),
    "card_stolen": Taxon("hard", "stop", "Lost/stolen card: no further collection attempts."),
    "bank_technical_error": Taxon("soft", "retry_scheduled", "Transient bank technical error; retry shortly."),
    "gateway_technical_error": Taxon("soft", "retry_scheduled", "Transient gateway technical error; retry shortly."),
    "bank_not_available": Taxon("soft", "retry_scheduled", "Bank unavailable; retry shortly."),
    "authentication_failed": Taxon("soft", "card_update_prompt", "Authentication failed; ask customer to complete authentication."),
    "insufficient_funds": Taxon("ambiguous", "retry_scheduled", "Funds may clear around a pay-cycle window."),
    "card_declined": Taxon("ambiguous", "retry_scheduled", "Issuer decline is ambiguous; select a conservative retry window."),
    "payment_cancelled": Taxon("not_a_decline", "card_update_prompt", "Customer cancelled checkout; send a single opt-in-respecting nudge."),
    "payment_method_not_enabled": Taxon("business_error", "escalate_ops", "Merchant payment method configuration requires operations review."),
}

def lookup(code: str) -> Taxon:
    return TAXONOMY.get(code, Taxon("ambiguous", "retry_scheduled", "Unknown decline: conservative retry with audit review."))
