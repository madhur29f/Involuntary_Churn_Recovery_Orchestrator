# Razorpay-Calibrated Decline Taxonomy & Routing Policy

Every decline reason ingested by the orchestrator matches official Razorpay payment error documentation (`razorpay.com/docs/errors/payments/list`). This taxonomy establishes the **safety floor**: blind retries against terminal or customer-actionable errors are forbidden by deterministic rules before any ML inference occurs.

---

## Complete Taxonomy Mapping

| Razorpay Error Reason | Category | Safety Action | Channel | Deterministic Rationale |
| :--- | :--- | :--- | :--- | :--- |
| `payment_risk_check_failed` | **Hard** | `stop` | None | Bank/Razorpay fraud flag: blind retries are prohibited to prevent network penalties. |
| `card_lost` | **Hard** | `stop` | None | Card permanently lost: collection attempts immediately ceased. |
| `card_stolen` | **Hard** | `stop` | None | Card reported stolen: collection attempts immediately ceased. |
| `card_expired` | **Hard** | `card_update_prompt` | `email` | Card requires replacement; automatic retry cannot succeed. |
| `international_transaction_not_allowed` | **Hard** | `card_update_prompt` | `email` | Customer must enable cross-border permissions with issuing bank. |
| `bank_technical_error` | **Soft** | `retry_scheduled` | None | Transient bank switch error; fast 1-day recovery window. |
| `gateway_technical_error` | **Soft** | `retry_scheduled` | None | Transient gateway timeout; fast 1-day recovery window. |
| `bank_not_available` | **Soft** | `retry_scheduled` | None | Core banking downtime; fast 1-day recovery window. |
| `authentication_failed` | **Soft** | `card_update_prompt` | `email` | 3DS / OTP verification failed; ask customer to re-authenticate. |
| `insufficient_funds` | **Ambiguous** | `retry_scheduled` | None | Evaluated by ML timing model to align with 1st/15th/30th pay-cycle windows. |
| `card_declined` | **Ambiguous** | `retry_scheduled` | None | Issuer generic decline; evaluated by ML model for 24–48h clearance. |
| `payment_cancelled` | **Not a Decline** | `card_update_prompt` | `email` | Checkout abandoned; single respectful opt-in nudge sent. |
| `payment_method_not_enabled` | **Business Error** | `escalate_ops` | `ops_webhook` | Merchant account misconfiguration; routed to internal ops queue, never customer. |

---

## Why Deterministic Stopping Rules are a Core Feature

1. **Card Network Compliance:** Visa and Mastercard rules levy fines and increased interchange fees on merchants who repeatedly retry fraud-flagged (`payment_risk_check_failed`) or permanently dead cards.
2. **Customer Relationship Protection:** Bombarding an expired card or an opted-out customer with failed recurring debits accelerates voluntary churn.
3. **Internal Ops Isolation:** If a merchant forgets to enable a payment method (`payment_method_not_enabled`), dunning the subscriber creates customer confusion and support tickets. Routing to internal ops fixes the root cause immediately.
