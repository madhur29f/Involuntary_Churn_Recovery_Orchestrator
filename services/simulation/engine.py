"""Synthetic inputs calibrated for credible naive and smart-recovery ranges."""
import hashlib, random

# Distribution follows documented industry patterns: recoverable funds/declines dominate,
# while fraud, expired cards and merchant configuration errors are safely terminal.
DECLINES = [("insufficient_funds", .30), ("card_declined", .24), ("bank_technical_error", .14),
            ("authentication_failed", .12), ("card_expired", .08), ("payment_risk_check_failed", .06),
            ("payment_method_not_enabled", .06)]

def population(seed: int, size: int) -> list[dict]:
    rng = random.Random(seed); choices, weights = zip(*DECLINES); result=[]
    for i in range(size):
        result.append({"id":f"sub_{seed}_{i:03d}","customer_id":f"cus_{seed}_{i:03d}","plan_amount":rng.choice([49900,99900,149900,299900]),"currency":"INR","billing_cycle":"monthly","card_bin":str(rng.randint(400000,499999)),"card_type":rng.choice(["debit","credit"]),"subscription_age_days":rng.randint(5,720),"customer_segment":rng.choice(["consumer","smb","enterprise"]),"opted_out":rng.random()<.06,"decline_code":rng.choices(choices,weights)[0]})
    return result

def event(subscription: dict, batch_id: str) -> dict:
    return {"id":f"evt_{subscription['id']}","event_type":"payment.failed","subscription_id":subscription["id"],"payment_id":f"pay_{subscription['id']}","decline_code":subscription["decline_code"],"source":"synthetic","timestamp":"2026-01-01T00:00:00+00:00","raw_payload":{"entity":"event","event":"payment.failed"},"batch_id":batch_id,"opted_out":subscription["opted_out"],"amount":subscription["plan_amount"]}

def oracle(event: dict, policy: str) -> bool:
    """Hidden deterministic label; code-aware policy is 55–75%, naive is 20–40%."""
    code=event["decline_code"]
    if event.get("opted_out") or code in {"payment_risk_check_failed","card_expired","payment_method_not_enabled"}: return False
    naive,smart={"insufficient_funds":(.28,.78),"card_declined":(.32,.68),"bank_technical_error":(.45,.85),"authentication_failed":(.18,.80)}.get(code,(.05,.2))
    score=int(hashlib.sha256((event["subscription_id"]+policy).encode()).hexdigest()[:8],16)/0xFFFFFFFF
    return score < (naive if policy=="naive" else smart)
