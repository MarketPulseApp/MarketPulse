-- Migration 009: mention_counts hypertable + api_call_log table
-- Replaces InfluxDB (mention counts) and DataStax Astra (API call log).

-- ── mention_counts ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS mention_counts (
    time        TIMESTAMPTZ      NOT NULL,
    symbol      TEXT             NOT NULL,
    subreddit   TEXT,
    count       INTEGER          NOT NULL DEFAULT 0,
    avg_score   DOUBLE PRECISION NOT NULL DEFAULT 0.0
);

SELECT create_hypertable('mention_counts', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_mention_counts_symbol_time
    ON mention_counts (symbol, time DESC);

-- ── api_call_log ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS api_call_log (
    id          BIGSERIAL        PRIMARY KEY,
    source      TEXT             NOT NULL,
    logged_at   TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
    endpoint    TEXT             NOT NULL,
    status_code INTEGER          NOT NULL,
    latency_ms  INTEGER          NOT NULL,
    error_msg   TEXT
);

CREATE INDEX IF NOT EXISTS idx_api_call_log_source_time
    ON api_call_log (source, logged_at DESC);

-- Retain log rows for 90 days (requires TimescaleDB)
SELECT add_retention_policy('mention_counts', INTERVAL '90 days', if_not_exists => TRUE);
