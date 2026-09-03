# Industry Benchmark Grounding & Empirical Calibration

Every metric, baseline recovery rate, and failure distribution in this project is grounded in published payment industry data and network research from Recurly, Stripe, and Razorpay.

---

## 1. Involuntary Churn Scale

- **Proportion of Total Churn:** Involuntary churn (payment failures, rather than active subscriber cancellations) represents roughly **20–40% of total subscription churn** across SaaS and DTC businesses.
- **Network Annual Churn Rates:** Analysis across tens of millions of active subscriptions (Recurly State of Subscriptions) indicates typical baseline subscription churn around **3–4% monthly** (30–45% annualized), with payment failure as the single largest addressable leakage point.
- **Card Payment Failure Rates:** Card-not-present recurring transaction failure rates consistently range between **10% and 15%** across major card networks. The majority of these failures are mechanical (insufficient funds, temporary issuer holds, expired payment methods) rather than fraudulent, proving that intelligent recovery is highly viable.

---

## 2. Industry Recovery Bands

| Strategy / Tier | Typical Industry Recovery Rate | Our Calibration | Justification & Sources |
| :--- | :--- | :--- | :--- |
| **Zero Retries** | 0% – 10% | < 5% | Organic customer recovery without automated intervention is minimal. |
| **Naive Fixed-Interval Retries** | 20% – 40% | **~23% – 32%** | Industry standard fixed 24h/48h blind retries (Recurly/Stripe baseline comparisons). |
| **Industry Average (Mixed Retries + Dunning)** | 45% – 48% | ~45% | Mixed basic dunning emails and fixed retries without decline awareness. |
| **Smart / ML-Timed Retries** | 50% – 65% | **~50% – 65%** | Scoped timing optimization aligning with pay cycles and transient clearance curves. |
| **Best-in-Class (Smart Retries + Card Updater + Ops)** | 70% – 85% | Up to 75% | Full multi-channel intervention, card replacement, and dynamic routing. |

> [!NOTE]
> **Why we reject 95%+ recovery claims:**  
> A system claiming 95%+ recovery on involuntary churn is unrealistic because hard fraud, lost/stolen cards, and customer account closures represent a permanent 15–25% ceiling of irrecoverable transactions. Our demo targets a conservative, defensible lift from **~23% (naive) to 55–65% (orchestrator)**.

---

## 3. The Pay-Cycle Effect on `insufficient_funds`

- The single most common recoverable decline reason is `insufficient_funds` (~30% of failures).
- Bank account deposit research demonstrates that consumer and small business accounts experience predictable liquidity surges around:
  - **Beginning of Month:** 1st – 5th (salary and monthly retainer deposits)
  - **Mid-Month:** 14th – 16th (bi-weekly paydays)
  - **End of Month:** 28th – 31st (month-end disbursements)
- Blind 2-day retries fail when a subscription bills on the 22nd; waiting 5 days to hit the 27th–28th yields an empirical recovery lift of up to 40 percentage points.
