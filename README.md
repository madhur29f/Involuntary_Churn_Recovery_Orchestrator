# Involuntary Churn Recovery Orchestrator

[![Tests](https://img.shields.io/badge/pytest-21%20passed-success)](tests/)
[![Temporal](https://img.shields.io/badge/Temporal-Orchestrated-blue)](https://temporal.io)
[![Track](https://img.shields.io/badge/Razorpay%20Buildathon-Track%2003-blueviolet)](https://razorpay.com)

An event-driven, decline-aware subscription recovery orchestration layer designed for Razorpay payment failures. Instead of firing blind, fixed-interval retries that trigger issuer fraud flags and churn subscribers, the system:
1. Applies a **deterministic rules safety floor** before any model inference (fraud, lost cards, expired methods, customer opt-outs, and merchant configuration errors never enter retry loops).
2. Uses an **interpretable ML timing model** scoped exclusively to ambiguous soft declines (`insufficient_funds`, `card_declined`) to align retries with customer pay-cycles and issuer clearance windows.
3. Orchestrates every recovery as a **bounded, durable state machine powered by Temporal**, with queryable state, signal handling, and hard stopping rules.
4. Writes every ingest, decision, reason, and transition to an **append-only audit log**.
5. Delivers a **measurable +25% to +35% recovery lift** against naive retry baselines while **eliminating 30+ wasted retries per cohort**.

---

## Quickstart

### Option A: One-Command Docker Compose (Full Stack with Temporal & UI)

Brings up FastAPI API, Temporal Worker, Temporal Server, Temporal Web UI, PostgreSQL, and Redis:

```bash
docker compose up --build
```

- **Interactive Recovery Dashboard:** [`http://localhost:8000`](http://localhost:8000)
- **Temporal Official Web UI:** [`http://localhost:8088`](http://localhost:8088)
- **Interactive Swagger API Docs:** [`http://localhost:8000/docs`](http://localhost:8000/docs)

---

### Option B: Local Python Execution (Zero Docker / Zero Node Required)

The system runs completely standalone with pure Python using SQLite:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the deterministic comparison CLI benchmark (60-subscriber cohort)
python scripts/compare.py --seed 42 --size 60

# 3. (Optional) Run the local FastAPI server with interactive web dashboard
uvicorn services.api.main:app --host 127.0.0.1 --port 8000
```

Open [`http://localhost:8000`](http://localhost:8000) in your browser to view the interactive live dashboard, run benchmarks, and inspect subscription audit trails!

---

## Live Benchmark Results (Seed: 42, N=60)

```
========================================================================
   INVOLUNTARY CHURN RECOVERY ORCHESTRATOR - POLICY COMPARISON
========================================================================
 Cohort: 60 failed subscriptions (Seed: 42)
 Total At-Risk Revenue: INR 77,440.00
------------------------------------------------------------------------
 Metric                           | Naive Policy     | Orchestrator    
------------------------------------------------------------------------
 Recovery Rate                    |          23.3% |          50.0%
 Subscriptions Recovered          |          14 / 60 |          30 / 60
 Revenue Recovered (INR)          | INR    19,986.00 | INR    36,970.00
 Wasted / Doomed Retries          |               46 |               16
 Compliant Immediate Stops        |                0 |                6
------------------------------------------------------------------------
 >>> RECOVERY LIFT: +26.7% (+INR 16,984.00)
 >>> WASTED RETRIES ELIMINATED: 30 retries
========================================================================
```

---

## Key Architecture & Features

### 1. Deterministic Rules Safety Floor
Before calling any model, the system evaluates Razorpay decline codes against non-negotiable rules:
- **`payment_risk_check_failed`**, **`card_lost`**, **`card_stolen`**: Immediate `stop` (prevents card network fines).
- **`card_expired`**, **`authentication_failed`**: Routed to customer `card_update_prompt` / 3DS prompt via email, not automated card debit.
- **`payment_method_not_enabled`**: Routed to merchant operations queue (`escalate_ops`), strictly excluding customer dunning.
- **Customer Opt-Out**: Immediate compliant `stop` blocking all outreach and retries.

### 2. Interpretable ML Timing Model (`services/model/`)
- Scoped strictly to ambiguous soft declines (`insufficient_funds`, `card_declined`).
- Trained on pay-cycle deposit timing (1st, 15th, 30th of the month) and issuer clearance curves.
- Logs exact natural language reasons into the audit trail (e.g. *"Model selected retry in 5 day(s) from pay-cycle proximity window (day 28); confidence 0.78; attempt 1 of 3"*).
- Graceful fallback: automatically degrades to a safe 2-day rule if the model is unreachable.

### 3. Durable Temporal Workflows (`services/worker/`)
- Each subscription/policy combination is managed by a `RecoveryWorkflow`.
- Idempotent workflow ID `recovery-{subscription_id}-{policy}` prevents duplicate executions.
- Enforces strict stopping rules (maximum 3 attempts).
- State is live queryable via `@workflow.query def state()`.
- Dynamic signal handling via `@workflow.signal def record_payment_result(...)`.
- Resilient to worker crashes and server restarts; replays directly from Temporal event history.

### 4. Append-Only Audit Trail
Every single lifecycle event is recorded with reason, actor, decision ID, and timestamp:
- Query full history for any subscriber: `GET /subscriptions/{id}/audit`.

---

## Running the Automated Test Suite

```bash
python -m pytest
```

Output:
```
tests/test_api_endpoints.py .....                                        [ 22%]
tests/test_decision.py ...                                               [ 36%]
tests/test_model_inference.py ...                                        [ 50%]
tests/test_reproducibility.py ...                                        [ 63%]
tests/test_taxonomy_and_rules.py ......                                  [ 90%]
tests/test_temporal_workflow.py ..                                       [100%]

======================== 21 passed, 1 skipped in 3.90s ========================
```

---

## Repository Structure

```
├── docker-compose.yml              # Multi-container stack (API, Worker, Postgres, Redis, Temporal, Temporal UI)
├── requirements.txt                # Python dependencies
├── recovery_orchestrator.db        # SQLite local store
├── scripts/
│   └── compare.py                  # Single reproducible CLI comparison runner
├── services/
│   ├── api/
│   │   ├── main.py                 # FastAPI webhook receiver, simulation, and metrics endpoints
│   │   ├── dashboard.py            # Real-time interactive dashboard UI (served directly at /)
│   │   ├── decision.py             # Decision engine routing & model fallback
│   │   ├── taxonomy.py             # Razorpay decline taxonomy mapping
│   │   ├── orchestration.py        # Temporal client dispatch adapter
│   │   └── store.py                # Database connection & append-only audit logging
│   ├── model/
│   │   ├── train.py                # Model training script
│   │   ├── predictor.py            # Model inference wrapper with explainability
│   │   └── model.joblib            # Serialized ML pipeline artifact
│   ├── simulation/
│   │   └── engine.py               # Synthetic cohort generator & calibrated outcome oracle
│   └── worker/
│       ├── main.py                 # Temporal worker process
│       ├── workflows.py            # Temporal state machine workflow
│       └── activities.py           # Replay-safe Temporal activities
├── tests/                          # 22 automated tests covering taxonomy, rules, ML, and Temporal
└── docs/
    ├── architecture.md             # System architecture & sequence diagrams
    ├── decline-taxonomy.md         # Razorpay error taxonomy reference
    ├── benchmarks.md               # Sourced industry data (Recurly, Stripe, Razorpay)
    ├── oracle-assumptions.md       # Ground-truth simulation mathematical calibrations
    └── pitch_video_script.md       # 5-minute hackathon pitch video script
```
