import hashlib, hmac, json, os
from types import SimpleNamespace
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from .decision import decide
from .taxonomy import lookup
from .store import conn, audit
from .dashboard import DASHBOARD_HTML
from services.simulation.engine import population, event as sim_event, oracle
from .orchestration import execute_recovery

app = FastAPI(title="Involuntary Churn Recovery Orchestrator", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STREAM = []

class SeedRequest(BaseModel):
    seed: int = 42
    population_size: int = Field(default=60, ge=1, le=2000)

class RunRequest(BaseModel):
    batch_id: str
    policy: str

@app.get('/', response_class=HTMLResponse)
def index():
    """Serves the complete interactive real-time dashboard UI."""
    return DASHBOARD_HTML

@app.post('/simulation/seed')
def seed(request: SeedRequest):
    batch_id = f"batch_{request.seed}_{request.population_size}"
    c = conn(); c.execute("INSERT OR REPLACE INTO batches VALUES(?,?,?,datetime('now'))", (batch_id,request.seed,request.population_size))
    for sub in population(request.seed, request.population_size):
        c.execute("INSERT OR REPLACE INTO subscriptions VALUES(?,?,?,?,?,?)", (sub['id'],batch_id,sub['customer_id'],sub['plan_amount'],json.dumps(sub),"failed"))
        e = sim_event(sub,batch_id)
        c.execute("INSERT OR IGNORE INTO webhook_events VALUES(?,?,?,?,?,?,?,?)", (e['id'],e['subscription_id'],batch_id,e['event_type'],e['decline_code'],e['source'],e['timestamp'],json.dumps(e['raw_payload'])))
        audit(c,sub['id'],batch_id,"event_ingested",f"Synthetic {e['event_type']} accepted.","simulation")
    c.commit(); c.close()
    return {"batch_id":batch_id,"population_size":request.population_size,"deterministic":True}

@app.post('/simulation/run')
async def run(request: RunRequest):
    if request.policy not in {'naive','orchestrator'}: raise HTTPException(422,"policy must be naive or orchestrator")
    c=conn()
    try:
        rows=c.execute("SELECT s.data FROM subscriptions s WHERE s.batch_id=?", (request.batch_id,)).fetchall()
        if not rows: raise HTTPException(404,"Batch not found")
        c.execute("DELETE FROM decisions WHERE batch_id=? AND policy=?",(request.batch_id,request.policy))
        c.execute("DELETE FROM workflow_state WHERE policy=? AND subscription_id IN (SELECT id FROM subscriptions WHERE batch_id=?)",(request.policy,request.batch_id))
        c.commit()
    finally:
        c.close()

    recovered=0
    for row in rows:
        sub=json.loads(row['data']); e=sim_event(sub,request.batch_id)
        if os.getenv("ORCHESTRATION_MODE", "local") == "temporal":
            outcome = await execute_recovery(e, request.policy)
            d = SimpleNamespace(**outcome["decision"])
            state, terminal = outcome["state"], outcome["terminal_reason"]
            success = state == "recovered"
        elif request.policy == 'naive':
            d=decide({**e,'decline_code':'card_declined','opted_out':False}, model_available=False)
            d.reason="Naive fixed two-day retry; decline category ignored."; d.decided_by="rule"
            success=oracle(e,request.policy)
            state='recovered' if success else ('stopped' if d.action in {'stop','escalate_ops'} else 'exhausted')
            terminal='payment_recovered' if success else d.reason
        else:
            d=decide(e, model_available=True)
            success=oracle(e,request.policy)
            state='recovered' if success else ('stopped' if d.action in {'stop','escalate_ops'} else 'exhausted')
            terminal='payment_recovered' if success else d.reason

        c_item = conn()
        try:
            cur=c_item.execute("INSERT INTO decisions(subscription_id,batch_id,policy,decline_code,category,action,scheduled_at,channel,decided_by,model_confidence,reason) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (sub['id'],request.batch_id,request.policy,e['decline_code'],d.category,d.action,d.scheduled_at,d.channel,d.decided_by,d.model_confidence,d.reason))
            c_item.execute("INSERT INTO workflow_state VALUES(?,?,?,?,?,?)",(sub['id'],request.policy,state,1,d.scheduled_at,terminal))
            audit(c_item,sub['id'],request.batch_id,"state_transition",f"{request.policy}: failed → {state}. {terminal}","orchestrator",cur.lastrowid)
            c_item.commit()
        finally:
            c_item.close()

        STREAM.append({"subscription_id":sub['id'],"policy":request.policy,"state":state,"amount":sub['plan_amount'] if success else 0})
        recovered += success

    return {"batch_id":request.batch_id,"policy":request.policy,"processed":len(rows),"recovered":recovered}

@app.get('/batches/{batch_id}/metrics')
def metrics(batch_id: str):
    c=conn(); total=c.execute("SELECT COUNT(*) n, COALESCE(SUM(plan_amount),0) amount FROM subscriptions WHERE batch_id=?",(batch_id,)).fetchone()
    if not total['n']: raise HTTPException(404,"Batch not found")
    policies={}
    for policy in ('naive','orchestrator'):
        r=c.execute("SELECT COUNT(*) n, COALESCE(SUM(s.plan_amount),0) amount FROM workflow_state w JOIN subscriptions s ON s.id=w.subscription_id WHERE s.batch_id=? AND w.policy=? AND w.current_state='recovered'",(batch_id,policy)).fetchone()
        retries=c.execute("SELECT COUNT(*) n FROM decisions WHERE batch_id=? AND policy=? AND action='retry_scheduled'",(batch_id,policy)).fetchone()['n']
        policies[policy]={"recovered_count":r['n'],"recovered_revenue_paise":r['amount'],"recovery_rate":round(r['n']/total['n']*100,2),"false_positive_retries":max(0,retries-r['n'])}
    c.close(); return {"batch_id":batch_id,"population_size":total['n'],"at_risk_revenue_paise":total['amount'],"policies":policies}

@app.get('/batches/{batch_id}/subscriptions')
def batch_subscriptions(batch_id: str):
    c = conn()
    rows = c.execute("SELECT id, plan_amount, data FROM subscriptions WHERE batch_id=? ORDER BY id", (batch_id,)).fetchall()
    if not rows:
        c.close()
        raise HTTPException(404, "Batch not found")
    result = []
    for r in rows:
        sub_data = json.loads(r["data"])
        sub_id = r["id"]
        naive_row = c.execute("SELECT current_state FROM workflow_state WHERE subscription_id=? AND policy='naive'", (sub_id,)).fetchone()
        orch_row = c.execute("SELECT current_state FROM workflow_state WHERE subscription_id=? AND policy='orchestrator'", (sub_id,)).fetchone()
        taxon = lookup(sub_data.get("decline_code", ""))
        result.append({
            "id": sub_id,
            "decline_code": sub_data.get("decline_code"),
            "category": taxon.category,
            "plan_amount": r["plan_amount"],
            "naive_state": naive_row["current_state"] if naive_row else None,
            "orch_state": orch_row["current_state"] if orch_row else None,
            "opted_out": sub_data.get("opted_out", False),
        })
    c.close()
    return {"batch_id": batch_id, "subscriptions": result}

@app.get('/audit/recent')
def recent_audit():
    c = conn()
    rows = c.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 15").fetchall()
    c.close()
    return {"recent_events": [dict(x) for x in rows]}

@app.get('/subscriptions/{subscription_id}/audit')
def subscription_audit(subscription_id: str):
    c=conn(); rows=c.execute("SELECT * FROM audit_log WHERE subscription_id=? ORDER BY id",(subscription_id,)).fetchall(); c.close()
    if not rows: raise HTTPException(404,"Subscription not found")
    return {"subscription_id":subscription_id,"trail":[dict(x) for x in rows]}

@app.post('/webhooks/razorpay')
async def webhook(request: Request):
    """Stores the raw signed webhook; duplicate event ids are idempotently ignored."""
    raw=await request.body(); signature=request.headers.get('X-Razorpay-Signature',''); secret=os.getenv('RAZORPAY_WEBHOOK_SECRET')
    if secret and not hmac.compare_digest(hmac.new(secret.encode(),raw,hashlib.sha256).hexdigest(),signature):
        raise HTTPException(401,"Invalid Razorpay webhook signature")
    payload=json.loads(raw); payment=payload.get('payload',{}).get('payment',{}).get('entity',{})
    subscription_id = (
        payment.get('subscription_id')
        or payload.get('subscription_id')
        or payload.get('payload',{}).get('subscription',{}).get('entity',{}).get('id')
        or payment.get('order_id')
        or payment.get('id')
        or f"sub_live_{hashlib.sha256(raw).hexdigest()[:8]}"
    )
    event_id=payload.get('id') or hashlib.sha256(raw).hexdigest(); code=payment.get('error_reason','card_declined'); c=conn()
    try:
        c.execute("INSERT OR IGNORE INTO webhook_events VALUES(?,?,?,?,?,?,?,?)",(event_id,subscription_id,None,payload.get('event','payment.failed'),code,'real',datetime.now(timezone.utc).isoformat(),raw.decode()))
        audit(c,subscription_id,None,"event_ingested",f"Real Razorpay event received: {code}.","webhook")
        c.commit()
    finally:
        c.close()

    outcome = None
    if 'failed' in payload.get('event', 'payment.failed'):
        e = {
            "id": event_id,
            "event_type": payload.get('event', 'payment.failed'),
            "subscription_id": subscription_id,
            "payment_id": payment.get('id', f"pay_{subscription_id}"),
            "decline_code": code,
            "source": "real",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "raw_payload": payload,
            "opted_out": False,
            "amount": payment.get('amount', 99900)
        }
        if os.getenv("ORCHESTRATION_MODE", "local") == "temporal":
            outcome = await execute_recovery(e, "orchestrator")
        else:
            d = decide(e, model_available=True)
            outcome = {"state": "retry_scheduled", "decision": as_payload(d), "terminal_reason": d.reason}

    return {"accepted": True, "event_id": event_id, "recovery": outcome}

@app.get('/events/stream')
def stream():
    def generate():
        while STREAM: yield f"data: {json.dumps(STREAM.pop(0))}\n\n"
        yield "event: complete\ndata: {}\n\n"
    return StreamingResponse(generate(),media_type='text/event-stream')
