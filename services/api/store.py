import os
import sqlite3
from pathlib import Path

DB_FILE = os.getenv("RECOVERY_DB_PATH")
if DB_FILE:
    DB = Path(DB_FILE)
else:
    DB = Path(__file__).resolve().parents[2] / "recovery_orchestrator.db"

SCHEMA = '''
CREATE TABLE IF NOT EXISTS batches (id TEXT PRIMARY KEY, seed INTEGER, population_size INTEGER, created_at TEXT);
CREATE TABLE IF NOT EXISTS subscriptions (id TEXT PRIMARY KEY, batch_id TEXT, customer_id TEXT, plan_amount INTEGER, data TEXT, status TEXT);
CREATE TABLE IF NOT EXISTS webhook_events (id TEXT PRIMARY KEY, subscription_id TEXT, batch_id TEXT, event_type TEXT, decline_code TEXT, source TEXT, timestamp TEXT, raw_payload TEXT);
CREATE TABLE IF NOT EXISTS decisions (id INTEGER PRIMARY KEY AUTOINCREMENT, subscription_id TEXT, batch_id TEXT, policy TEXT, decline_code TEXT, category TEXT, action TEXT, scheduled_at TEXT, channel TEXT, decided_by TEXT, model_confidence REAL, reason TEXT);
CREATE TABLE IF NOT EXISTS workflow_state (subscription_id TEXT, policy TEXT, current_state TEXT, attempt_count INTEGER, next_action_at TEXT, terminal_reason TEXT, PRIMARY KEY(subscription_id, policy));
CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, subscription_id TEXT, batch_id TEXT, event TEXT, decision_id INTEGER, reason TEXT, actor TEXT, timestamp TEXT);
CREATE TABLE IF NOT EXISTS system_state (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT);
'''

_INITIALIZED = set()

def init_db(db_path: Path):
    if str(db_path) in _INITIALIZED:
        return
    with sqlite3.connect(db_path, timeout=30.0) as connection:
        try:
            connection.execute("PRAGMA journal_mode=WAL;")
        except Exception:
            pass
        try:
            connection.execute("PRAGMA busy_timeout=5000;")
        except Exception:
            pass
        connection.executescript(SCHEMA)
    _INITIALIZED.add(str(db_path))

def conn(db_path: Path | None = None):
    target = db_path or (Path(os.getenv("RECOVERY_DB_PATH")) if os.getenv("RECOVERY_DB_PATH") else DB)
    init_db(target)
    connection = sqlite3.connect(target, timeout=60.0)
    try:
        connection.execute("PRAGMA busy_timeout=60000;")
    except Exception:
        pass
    connection.row_factory = sqlite3.Row
    return connection

def set_system_state(key: str, value: str):
    c = conn()
    try:
        c.execute("INSERT OR REPLACE INTO system_state(key, value, updated_at) VALUES(?,?,datetime('now'))", (key, value))
        c.commit()
    finally:
        c.close()

def get_system_state(key: str, default: str = "") -> str:
    c = conn()
    try:
        row = c.execute("SELECT value FROM system_state WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default
    finally:
        c.close()

def audit(connection, subscription_id, batch_id, event, reason, actor="system", decision_id=None):
    connection.execute(
        "INSERT INTO audit_log(subscription_id,batch_id,event,decision_id,reason,actor,timestamp) VALUES(?,?,?,?,?,?,datetime('now'))",
        (subscription_id, batch_id, event, decision_id, reason, actor)
    )
