CREATE TABLE subscriptions (id TEXT PRIMARY KEY, customer_id TEXT, plan_amount INTEGER, currency TEXT, billing_cycle TEXT, card_bin TEXT, card_type TEXT, subscription_age_days INTEGER, customer_segment TEXT, comms_opt_in JSONB, status TEXT, created_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE webhook_events (id TEXT PRIMARY KEY, event_type TEXT, subscription_id TEXT, payment_id TEXT, decline_code TEXT, source TEXT, timestamp TIMESTAMPTZ, raw_payload JSONB);
CREATE TABLE decisions (id BIGSERIAL PRIMARY KEY, subscription_id TEXT, decline_code TEXT, category TEXT, action TEXT, scheduled_at TIMESTAMPTZ, channel TEXT, decided_by TEXT, model_confidence REAL, reason TEXT);
CREATE TABLE workflow_state (subscription_id TEXT PRIMARY KEY, current_state TEXT, attempt_count INT, next_action_at TIMESTAMPTZ, terminal_reason TEXT);
CREATE TABLE audit_log (id BIGSERIAL PRIMARY KEY, subscription_id TEXT, event TEXT, decision_id BIGINT, reason TEXT, actor TEXT, timestamp TIMESTAMPTZ DEFAULT now());
CREATE INDEX audit_subscription_timestamp ON audit_log(subscription_id, timestamp);
