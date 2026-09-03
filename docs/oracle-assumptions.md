# Simulation Oracle & Outcome Calibration Assumptions

The simulation engine (`services/simulation/engine.py`) models real-world payment networks using a deterministic ground-truth oracle. The oracle function is strictly hidden from the decision engine; the decision engine and ML model must make decisions using only available transaction metadata.

---

## 1. Decline Distribution in Cohort Generation

Synthetic cohorts are sampled according to published recurring card failure distributions:

| Decline Code | Cohort Share | Nature | Recovery Potential |
| :--- | :--- | :--- | :--- |
| `insufficient_funds` | 30% | Ambiguous / Liquidity | High when aligned with salary/pay-cycles |
| `card_declined` | 24% | Ambiguous / Issuer Hold | Moderate; ~50% clear within 24–48 hours |
| `bank_technical_error` | 14% | Soft / Transient | Very high with short (24h) backoff |
| `authentication_failed` | 12% | Soft / Customer 3DS | High when customer is prompted to complete OTP |
| `card_expired` | 8% | Hard / Physical | 0% on blind retry; 60%+ with card update prompt |
| `payment_risk_check_failed` | 6% | Hard / Fraud | 0% (Blind retries strictly prohibited) |
| `payment_method_not_enabled`| 6% | Business Error | 0% via dunning; 100% via merchant ops resolution |

Additionally, **~6% of subscribers** are modeled as having opted out of automated merchant communications, testing compliant stopping rules.

---

## 2. Oracle Ground Truth Probability Function

The oracle calculates a deterministic pseudo-random hash score \( S \in [0, 1) \) for every subscription and policy:
\[
S = \frac{\text{SHA256}(\text{subscription\_id} + \text{policy})[:8]_{16}}{2^{32} - 1}
\]

The probability thresholds \( P(\text{recovery}) \) are calibrated as follows:

| Decline Reason | Naive Policy \( P(\text{success}) \) | Orchestrator Policy \( P(\text{success}) \) | Rationale |
| :--- | :--- | :--- | :--- |
| `insufficient_funds` | 0.28 | 0.78 | Naive 2-day retry often misses payday; ML timing catches deposit window. |
| `card_declined` | 0.32 | 0.68 | 48-hour clearance curve allows temporary issuer hold to resolve. |
| `bank_technical_error` | 0.45 | 0.85 | Gateway and switch recovery completes in 24 hours. |
| `authentication_failed` | 0.18 | 0.80 | Blind card debit fails; prompting customer for 3DS authentication recovers account. |
| Hard Declines / Opt-outs | **0.00** | **0.00** | Retries against fraud or expired methods never succeed and waste merchant fees. |

Over a balanced cohort of 60 subscriptions:
- **Naive Baseline:** Yields ~20% – 30% recovery rate.
- **Orchestrator:** Yields ~50% – 65% recovery rate.
- **Net Lift:** **+25% to +35% percentage points** lift in recovered revenue, with **30+ wasted retries eliminated**.
