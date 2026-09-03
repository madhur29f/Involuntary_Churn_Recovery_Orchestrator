# Involuntary Churn Recovery Orchestrator

An event-driven, decline-aware subscription recovery layer for Razorpay-shaped payment failures. It applies a non-negotiable rules floor before a scoped timing model, writes every outcome to an append-only audit log, and compares its policy against a naive retry baseline.

## Run

```bash
docker compose up --build
```

Open the API docs at `http://localhost:8000/docs`. For a deterministic demo, seed a batch, run `naive` and `orchestrator`, then request its metrics:

```bash
curl -X POST localhost:8000/simulation/seed -H "content-type: application/json" -d '{"seed":42,"population_size":60}'
curl -X POST localhost:8000/simulation/run -H "content-type: application/json" -d '{"batch_id":"batch_42_60","policy":"naive"}'
curl -X POST localhost:8000/simulation/run -H "content-type: application/json" -d '{"batch_id":"batch_42_60","policy":"orchestrator"}'
curl localhost:8000/batches/batch_42_60/metrics
```

The local API uses SQLite for frictionless development; the compose stack also provisions Postgres, Redis Streams infrastructure, and Temporal for production workflow deployment. The initial Postgres schema is in `db/migrations`.
