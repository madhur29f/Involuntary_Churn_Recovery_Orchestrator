import hashlib, hmac, json, os
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from .decision import decide
from .store import conn, audit
from services.simulation.engine import population, event as sim_event, oracle

app = FastAPI(title="Involuntary Churn Recovery Orchestrator", version="0.1.0")
STREAM = []

class SeedRequest(BaseModel):
    seed: int = 42
    population_size: int = Field(default=60, ge=1, le=2000)

class RunRequest(BaseModel):
    batch_id: str
    policy: str

@app.post('/simulation/seed')
def seed(request: SeedRequest):
    batch_id = f"batch_{request.seed}_{request.population_size}"
    c = conn(); c.execute("INSERT OR REPLACE INTO batches VALUES(?,?,?,datetime('now'))", (batch_id,request.seed,request.population_size))
    for sub in population(request.seed, request.population_size):
        c.execute("INSERT OR REPLACE INTO subscriptions VALUES(?,?,?,?,?,?)", (sub['id'],batch_id,sub['customer_id'],sub['plan_amount'],json.dumps(sub),"failed"))
        e = sim_event(sub,batch_id)
        c.execute("INSERT OR IGNORE INTO webhook_events VALUES(?,?,?,?,?,?,?,?,?)", (e['id'],e['subscription_id'],batch_id,e['event_type'],e['decline_code'],e['source'],e['timestamp'],json.dumps(e['raw_payload'])))
        audit(c,sub['id'],batch_id,"event_ingested",f"Synthetic {e['event_type']} accepted.","simulation")
    c.commit(); c.close()
    return {"batch_id":batch_id,"population_size":request.population_size,"deterministic":True}

@app.post('/simulation/run')
def run(request: RunRequest):
    if request.policy not in {'naive','orchestrator'}: raise HTTPException(422,"policy must be naive or orchestrator")
    c=conn(); rows=c.execute("SELECT s.data FROM subscriptions s WHERE s.batch_id=?", (request.batch_id,)).fetchall()
    if not rows: raise HTTPException(404,"Batch not found")
    c.execute("DELETE FROM decisions WHERE batch_id=? AND policy=?",(request.batch_id,request.policy))
    c.execute("DELETE FROM workflow_state WHERE policy=? AND subscription_id IN (SELECT id FROM subscriptions WHERE batch_id=?)",(request.policy,request.batch_id))
    recovered=0
    for row in rows:
        sub=json.loads(row['data']); e=sim_event(sub,request.batch_id)
        if request.policy == 'naive':
            d=decide({**e,'decline_code':'card_declined','opted_out':False}, model_available=False)
            d.reason="Naive fixed two-day retry; decline category ignored."; d.decided_by="rule"
        else: d=decide(e)
        success=oracle(e,request.policy)
        state='recovered' if success else ('stopped' if d.action in {'stop','escalate_ops'} else 'exhausted')
        terminal='payment_recovered' if success else d.reason
        cur=c.execute("INSERT INTO decisions(subscription_id,batch_id,policy,decline_code,category,action,scheduled_at,channel,decided_by,model_confidence,reason) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (sub['id'],request.batch_id,request.policy,e['decline_code'],d.category,d.action,d.scheduled_at,d.channel,d.decided_by,d.model_confidence,d.reason))
        c.execute("INSERT INTO workflow_state VALUES(?,?,?,?,?,?)",(sub['id'],request.policy,state,1,d.scheduled_at,terminal))
        audit(c,sub['id'],request.batch_id,"state_transition",f"{request.policy}: failed → {state}. {terminal}","orchestrator",cur.lastrowid)
        STREAM.append({"subscription_id":sub['id'],"policy":request.policy,"state":state,"amount":sub['plan_amount'] if success else 0})
        recovered += success
    c.commit(); c.close()
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
    subscription_id=payment.get('subscription_id') or payload.get('subscription_id')
    if not subscription_id: raise HTTPException(422,"subscription_id is required")
    event_id=payload.get('id') or hashlib.sha256(raw).hexdigest(); code=payment.get('error_reason','card_declined'); c=conn()
    c.execute("INSERT OR IGNORE INTO webhook_events VALUES(?,?,?,?,?,?,?,?,?)",(event_id,subscription_id,None,payload.get('event','payment.failed'),code,'real',datetime.now(timezone.utc).isoformat(),raw.decode()))
    audit(c,subscription_id,None,"event_ingested",f"Real Razorpay event received: {code}.","webhook"); c.commit(); c.close()
    return {"accepted":True,"event_id":event_id}

@app.get('/events/stream')
def stream():
    def generate():
        while STREAM: yield f"data: {json.dumps(STREAM.pop(0))}\\n\\n"
        yield "event: complete\\ndata: {}\\n\\n"
    return StreamingResponse(generate(),media_type='text/event-stream')
