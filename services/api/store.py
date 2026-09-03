import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[2] / "recovery.db"
SCHEMA = '''
CREATE TABLE IF NOT EXISTS batches (id TEXT PRIMARY KEY, seed INTEGER, population_size INTEGER, created_at TEXT);
CREATE TABLE IF NOT EXISTS subscriptions (id TEXT PRIMARY KEY, batch_id TEXT, customer_id TEXT, plan_amount INTEGER, data TEXT, status TEXT);
CREATE TABLE IF NOT EXISTS webhook_events (id TEXT PRIMARY KEY, subscription_id TEXT, batch_id TEXT, event_type TEXT, decline_code TEXT, source TEXT, timestamp TEXT, raw_payload TEXT);
CREATE TABLE IF NOT EXISTS decisions (id INTEGER PRIMARY KEY AUTOINCREMENT, subscription_id TEXT, batch_id TEXT, policy TEXT, decline_code TEXT, category TEXT, action TEXT, scheduled_at TEXT, channel TEXT, decided_by TEXT, model_confidence REAL, reason TEXT);
CREATE TABLE IF NOT EXISTS workflow_state (subscription_id TEXT, policy TEXT, current_state TEXT, attempt_count INTEGER, next_action_at TEXT, terminal_reason TEXT, PRIMARY KEY(subscription_id, policy));
CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, subscription_id TEXT, batch_id TEXT, event TEXT, decision_id INTEGER, reason TEXT, actor TEXT, timestamp TEXT);
'''

def conn():
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA)
    return connection

def audit(connection, subscription_id, batch_id, event, reason, actor="system", decision_id=None):
    connection.execute("INSERT INTO audit_log(subscription_id,batch_id,event,decision_id,reason,actor,timestamp) VALUES(?,?,?,?,?,?,datetime('now'))", (subscription_id, batch_id, event, decision_id, reason, actor))
