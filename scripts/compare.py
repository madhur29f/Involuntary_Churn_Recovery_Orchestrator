"""
CLI Comparison Runner for Triage (Involuntary Churn Recovery Orchestrator).
Runs reproducible simulations across naive baseline vs decline-aware orchestrator.
Computes recovered revenue, recovery lift, and false-positive retries avoided.
"""
import argparse
import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.simulation.engine import population, event as sim_event, oracle
from services.api.decision import decide
from services.api.store import conn, audit

def run_comparison(seed: int = 42, size: int = 60, quiet: bool = False):
    batch_id = f"batch_{seed}_{size}"
    c = conn()
    c.execute("INSERT OR REPLACE INTO batches VALUES(?,?,?,datetime('now'))", (batch_id, seed, size))

    subs = population(seed, size)
    total_at_risk_paise = sum(s["plan_amount"] for s in subs)

    # Ingest synthetic population and events
    for sub in subs:
        c.execute(
            "INSERT OR REPLACE INTO subscriptions VALUES(?,?,?,?,?,?)",
            (sub["id"], batch_id, sub["customer_id"], sub["plan_amount"], json.dumps(sub), "failed")
        )
        e = sim_event(sub, batch_id)
        c.execute(
            "INSERT OR IGNORE INTO webhook_events VALUES(?,?,?,?,?,?,?,?)",
            (e["id"], e["subscription_id"], batch_id, e["event_type"], e["decline_code"], e["source"], e["timestamp"], json.dumps(e["raw_payload"]))
        )

    results = {}
    categories_breakdown = {}

    for policy in ("naive", "orchestrator"):
        c.execute("DELETE FROM decisions WHERE batch_id=? AND policy=?", (batch_id, policy))
        c.execute(
            "DELETE FROM workflow_state WHERE policy=? AND subscription_id IN (SELECT id FROM subscriptions WHERE batch_id=?)",
            (policy, batch_id)
        )

        recovered_count = 0
        recovered_revenue = 0
        total_retries = 0
        terminal_stops = 0

        for sub in subs:
            e = sim_event(sub, batch_id)
            code = e["decline_code"]

            if code not in categories_breakdown:
                categories_breakdown[code] = {"count": 0, "naive_recovered": 0, "orch_recovered": 0}
            if policy == "naive":
                categories_breakdown[code]["count"] += 1

            if policy == "naive":
                # Blind 2-day retry without taxonomy awareness
                d = decide({**e, "decline_code": "card_declined", "opted_out": False}, model_available=False)
                d.reason = "Naive fixed two-day retry; decline category ignored."
                d.decided_by = "rule"
            else:
                d = decide(e, model_available=True)

            success = oracle(e, policy)
            state = "recovered" if success else ("stopped" if d.action in {"stop", "escalate_ops"} else "exhausted")
            terminal = "payment_recovered" if success else d.reason

            if d.action == "retry_scheduled":
                total_retries += 1
            elif d.action in {"stop", "escalate_ops"}:
                terminal_stops += 1

            if success:
                recovered_count += 1
                recovered_revenue += sub["plan_amount"]
                if policy == "naive":
                    categories_breakdown[code]["naive_recovered"] += 1
                else:
                    categories_breakdown[code]["orch_recovered"] += 1

            cur = c.execute(
                "INSERT INTO decisions(subscription_id,batch_id,policy,decline_code,category,action,scheduled_at,channel,decided_by,model_confidence,reason) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (sub["id"], batch_id, policy, code, d.category, d.action, d.scheduled_at, d.channel, d.decided_by, d.model_confidence, d.reason)
            )
            c.execute(
                "INSERT INTO workflow_state VALUES(?,?,?,?,?,?)",
                (sub["id"], policy, state, 1, d.scheduled_at, terminal)
            )

        recovery_rate = (recovered_count / size) * 100
        false_positive_retries = max(0, total_retries - recovered_count)

        results[policy] = {
            "recovered_count": recovered_count,
            "recovered_revenue_paise": recovered_revenue,
            "recovered_revenue_inr": recovered_revenue / 100,
            "recovery_rate": round(recovery_rate, 2),
            "total_retries": total_retries,
            "false_positive_retries": false_positive_retries,
            "terminal_stops": terminal_stops,
        }

    c.commit()
    c.close()

    naive = results["naive"]
    orch = results["orchestrator"]
    lift_rate = round(orch["recovery_rate"] - naive["recovery_rate"], 2)
    lift_revenue_inr = round(orch["recovered_revenue_inr"] - naive["recovered_revenue_inr"], 2)
    wasted_retries_prevented = max(0, naive["false_positive_retries"] - orch["false_positive_retries"])

    output = {
        "batch_id": batch_id,
        "seed": seed,
        "population_size": size,
        "at_risk_revenue_inr": total_at_risk_paise / 100,
        "naive": naive,
        "orchestrator": orch,
        "lift": {
            "recovery_rate_lift_pct_pts": lift_rate,
            "recovered_revenue_lift_inr": lift_revenue_inr,
            "wasted_retries_prevented": wasted_retries_prevented,
        },
        "taxonomy_breakdown": categories_breakdown,
    }

    if not quiet:
        print("=" * 72)
        print("   TRIAGE: INVOLUNTARY CHURN RECOVERY ORCHESTRATOR - POLICY COMPARISON")
        print("=" * 72)
        print(f" Cohort: {size} failed subscriptions (Seed: {seed})")
        print(f" Total At-Risk Revenue: INR {total_at_risk_paise / 100:,.2f}")
        print("-" * 72)
        print(f" {'Metric':<32} | {'Naive Policy':<16} | {'Orchestrator':<16}")
        print("-" * 72)
        print(f" {'Recovery Rate':<32} | {naive['recovery_rate']:>13.1f}% | {orch['recovery_rate']:>13.1f}%")
        print(f" {'Subscriptions Recovered':<32} | {naive['recovered_count']:>11} / {size:<2} | {orch['recovered_count']:>11} / {size:<2}")
        print(f" {'Revenue Recovered (INR)':<32} | INR {naive['recovered_revenue_inr']:>12,.2f} | INR {orch['recovered_revenue_inr']:>12,.2f}")
        print(f" {'Wasted / Doomed Retries':<32} | {naive['false_positive_retries']:>16} | {orch['false_positive_retries']:>16}")
        print(f" {'Compliant Immediate Stops':<32} | {naive['terminal_stops']:>16} | {orch['terminal_stops']:>16}")
        print("-" * 72)
        print(f" >>> RECOVERY LIFT: +{lift_rate:.1f}% (+INR {lift_revenue_inr:,.2f})")
        print(f" >>> WASTED RETRIES ELIMINATED: {wasted_retries_prevented} retries")
        print("=" * 72)

    return output

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run comparison between Naive and Orchestrator policies.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic cohort")
    parser.add_argument("--size", type=int, default=60, help="Population size")
    parser.add_argument("--json", action="store_true", help="Output JSON result")
    args = parser.parse_args()

    res = run_comparison(seed=args.seed, size=args.size, quiet=args.json)
    if args.json:
        print(json.dumps(res, indent=2))
