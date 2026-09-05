# 5-Minute Pitch Video Script

**Track:** Razorpay AI Buildathon — Track 03: AI Revenue Recovery  
**Product:** Triage (Involuntary Churn Recovery Orchestrator)  
**Format:** 5-Minute Video Pitch + Live Demo

---

## Part 1: The Problem (0:00 – 0:45)
- **Hook:** Every subscription company loses between 20% and 40% of their total churn to one silent leak: **involuntary churn**. The customer didn't want to cancel — their payment simply failed.
- **The Status Quo:** Most billing systems deploy "retry bots" that issue blind 24-hour or 48-hour retries. 
- **The Pain:** Blind retries hammer expired cards, trigger card network penalties on fraud-flagged accounts, miss the customer's actual payday window, and churn subscribers who simply needed an OTP prompt.

---

## Part 2: The Twist — Not a Bot, an Orchestration Layer (0:45 – 1:30)
- **The Core Thesis:** "We didn't build another retry bot. We built a **decline-aware recovery orchestration layer** designed as infrastructure that any billing engine can plug into via webhooks."
- **Precedence Hierarchy:**
  1. **Deterministic Safety Floor:** Immediate `stop` for hard fraud (`payment_risk_check_failed`) and opted-out subscribers. Expired cards get customer replacement links; merchant misconfigurations get escalated to ops, never customer dunning.
  2. **Scoped ML Timing Model:** We don't use ML for everything — only for the ambiguous middle (`insufficient_funds`, `card_declined`). It predicts optimal pay-cycle clearance windows and explains *why* in the audit log.
  3. **Durable Temporal State Machine:** Every recovery attempt is bounded, queryable, signalable, and durable against server restarts.

---

## Part 3: Architecture & Live Demo (1:30 – 3:45)
- **Walkthrough:**
  1. Open the interactive dashboard at `http://localhost:8000/`.
  2. Show the single-click benchmark run on a deterministic cohort of 60 subscriptions.
  3. Show the Temporal UI running alongside on `http://localhost:8088`.
  4. Point to the real-time breakdown:
     - **At-Risk Revenue:** ₹77,440.
     - **Naive Policy:** 23.3% recovery rate (₹19,986 recovered) with 46 wasted retries.
     - **Orchestrator Policy:** 50.0% recovery rate (₹36,970 recovered) with 30 wasted retries prevented!
  5. Drill down into individual subscriptions in the table:
     - Inspect an `insufficient_funds` case: show how the ML model waited 5 days to hit the month-end payday window.
     - Inspect a `payment_risk_check_failed` case: show how the deterministic rule halted all retries immediately with zero wasted attempts.
     - Inspect an `opted_out` subscriber: show compliance-grade stopping rules.

---

## Part 4: Technical Rigor & Durability (3:45 – 4:30)
- **Temporal Resilience:** Show how Temporal workflow IDs (`recovery-{subscription_id}-{policy}`) ensure deduplication and idempotent recovery even across network drops.
- **Graceful Fallback:** Show how if the ML model is unreachable, the orchestrator automatically degrades to a safe 2-day rule without dropping transactions.
- **Single-Command Evaluation:** Mention `docker compose up` brings up the entire ecosystem (FastAPI, Temporal Server, Temporal Web UI, Postgres, Redis, and Worker) with zero setup friction.

---

## Part 5: Closing & The Ask (4:30 – 5:00)
- **Summary:** Triage turns payment failures from a blunt hammer into an intelligent, compliant, and auditable revenue recovery engine.
- **Call to Action:** Thank the Razorpay team and invite them to explore the live Swagger docs and Temporal workflow executions!
