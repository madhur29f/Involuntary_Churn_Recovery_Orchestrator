# Architecture

`payment.failed` webhook or synthetic event flows through an idempotent event store, the shared `decide(event)` engine, a persisted decision/audit record, and a workflow-state transition. The dashboard reads metrics and receives state transitions through SSE.

Hard fraud/card-loss declines, opt-outs, and merchant configuration errors are handled by deterministic rules before model inference. The model is constrained to recovery timing for soft or ambiguous declines and falls back to a conservative two-day rule when unavailable.

The local runner persists data in SQLite. Docker provisions PostgreSQL, Redis, and Temporal as the durable production infrastructure boundary.
