"""Initial schema

Revision ID: fbf81257f834
Revises: 
Create Date: 2026-09-15 14:57:32.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fbf81257f834"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    sql_statements = """-- MarketPulse PostgreSQL + TimescaleDB Schema
-- Save to: C:\marketpulse\init\postgres\001_schema.sql

-- Enable TimescaleDB
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ── Users ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'user',   -- 'user' | 'admin'
    totp_secret TEXT,
    totp_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    discord_id  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Tickers ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tickers (
    symbol      TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    asset_type  TEXT NOT NULL,   -- 'stock' | 'crypto' | 'index'
    sector      TEXT,
    exchange    TEXT,
    currency    TEXT NOT NULL DEFAULT 'USD',
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Watchlists ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS watchlists (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS watchlist_entries (
    watchlist_id UUID NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
    symbol       TEXT NOT NULL REFERENCES tickers(symbol),
    added_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (watchlist_id, symbol)
);

-- ── OHLCV (TimescaleDB hypertable) ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ohlcv (
    time        TIMESTAMPTZ NOT NULL,
    symbol      TEXT NOT NULL REFERENCES tickers(symbol),
    open        NUMERIC(18,6) NOT NULL,
    high        NUMERIC(18,6) NOT NULL,
    low         NUMERIC(18,6) NOT NULL,
    close       NUMERIC(18,6) NOT NULL,
    volume      BIGINT NOT NULL,
    source      TEXT NOT NULL DEFAULT 'yfinance',
    PRIMARY KEY (time, symbol)
);
SELECT create_hypertable('ohlcv', 'time', chunk_time_interval => INTERVAL '1 month', if_not_exists => TRUE);
ALTER TABLE ohlcv SET (timescaledb.compress, timescaledb.compress_segmentby = 'symbol');
SELECT add_compression_policy('ohlcv', INTERVAL '7 days', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_time ON ohlcv (symbol, time DESC);

-- ── Technical Indicators (hypertable) ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS technical_indicators (
    time        TIMESTAMPTZ NOT NULL,
    symbol      TEXT NOT NULL REFERENCES tickers(symbol),
    rsi_14      NUMERIC(8,4),
    macd_line   NUMERIC(12,6),
    macd_signal NUMERIC(12,6),
    macd_hist   NUMERIC(12,6),
    bb_upper    NUMERIC(18,6),
    bb_middle   NUMERIC(18,6),
    bb_lower    NUMERIC(18,6),
    bb_pct      NUMERIC(8,4),
    sma_20      NUMERIC(18,6),
    sma_50      NUMERIC(18,6),
    sma_200     NUMERIC(18,6),
    ema_12      NUMERIC(18,6),
    ema_26      NUMERIC(18,6),
    atr_14      NUMERIC(12,6),
    adx_14      NUMERIC(8,4),
    obv         BIGINT,
    volume_sma_20 BIGINT,
    PRIMARY KEY (time, symbol)
);
SELECT create_hypertable('technical_indicators', 'time', chunk_time_interval => INTERVAL '1 month', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_indicators_symbol_time ON technical_indicators (symbol, time DESC);

-- ── Predictions (hypertable) ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS predictions (
    time            TIMESTAMPTZ NOT NULL,
    symbol          TEXT NOT NULL REFERENCES tickers(symbol),
    horizon         TEXT NOT NULL,   -- '1d' | '3d' | '7d' | '30d'
    direction       TEXT NOT NULL,   -- 'UP' | 'DOWN' | 'FLAT'
    confidence      NUMERIC(5,2) NOT NULL,
    lstm_prob_up    NUMERIC(5,4),
    lstm_prob_down  NUMERIC(5,4),
    lstm_prob_flat  NUMERIC(5,4),
    xgb_prob_up     NUMERIC(5,4),
    xgb_prob_down   NUMERIC(5,4),
    xgb_prob_flat   NUMERIC(5,4),
    lgbm_prob_up    NUMERIC(5,4),
    lgbm_prob_down  NUMERIC(5,4),
    lgbm_prob_flat  NUMERIC(5,4),
    model_version   TEXT NOT NULL DEFAULT 'v0',
    feature_schema_version INT NOT NULL DEFAULT 1,
    resolved        BOOLEAN NOT NULL DEFAULT FALSE,
    actual_direction TEXT,           -- filled in by outcome resolver
    was_correct     BOOLEAN,
    resolved_at     TIMESTAMPTZ,
    PRIMARY KEY (time, symbol, horizon)
);
SELECT create_hypertable('predictions', 'time', chunk_time_interval => INTERVAL '1 month', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_predictions_symbol_horizon ON predictions (symbol, horizon, time DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_unresolved ON predictions (symbol, horizon) WHERE resolved = FALSE;

-- ── Sentiment Scores (hypertable) ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sentiment_scores (
    time            TIMESTAMPTZ NOT NULL,
    symbol          TEXT NOT NULL REFERENCES tickers(symbol),
    source_type     TEXT NOT NULL,
    source_name     TEXT,
    score           NUMERIC(5,4) NOT NULL,
    article_count   INT NOT NULL DEFAULT 0,
    post_count      INT NOT NULL DEFAULT 0,
    PRIMARY KEY (time, symbol, source_type)
);

SELECT create_hypertable('sentiment_scores', 'time', chunk_time_interval => INTERVAL '1 month', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_sentiment_symbol_time ON sentiment_scores (symbol, time DESC);


-- ── Alert Configs ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS alert_configs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol          TEXT REFERENCES tickers(symbol),   -- NULL = all tickers
    alert_type      TEXT NOT NULL,
    min_confidence  NUMERIC(5,2) NOT NULL DEFAULT 75.0,
    horizons        TEXT[] NOT NULL DEFAULT '{1d,3d,7d,30d}',
    channels        TEXT[] NOT NULL DEFAULT '{browser_push}',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── API Quotas ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS api_quotas (
    source          TEXT PRIMARY KEY,
    daily_limit     INT NULL,
    monthly_limit   INT,
    notes           TEXT
);

INSERT INTO api_quotas (source, daily_limit, monthly_limit, notes) VALUES
    ('yfinance',    1000,  NULL,   'No official limit; be conservative'),
    ('polygon',     NULL,  NULL,   '5 calls/min on free tier'),
    ('newsapi',     100,   NULL,   'Free tier: 100 req/day'),
    ('gnews',       100,   NULL,   'Free tier: 100 req/day'),
    ('finnhub',     NULL,  NULL,   '60 calls/min free tier'),
    ('coingecko',   NULL,  10000,  'Free tier: 10K calls/month'),
    ('reddit',      NULL,  NULL,   '100 req/min per OAuth client'),
    ('fred',        NULL,  NULL,   'Unlimited free'),
    ('sec_edgar',   NULL,  NULL,   '10 req/sec limit')
ON CONFLICT (source) DO NOTHING;

-- ── Feature Flags ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS feature_flags (
    flag            TEXT PRIMARY KEY,
    enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    description     TEXT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO feature_flags (flag, enabled, description) VALUES
    -- Data sources
    ('datasource.yfinance',         true,  'yfinance OHLCV ingestion'),
    ('datasource.polygon',          true,  'Polygon.io real-time data'),
    ('datasource.coingecko',        true,  'CoinGecko crypto OHLCV'),
    ('datasource.newsapi',          true,  'NewsAPI news ingestion'),
    ('datasource.gnews',            true,  'GNews ingestion'),
    ('datasource.finnhub',          true,  'Finnhub news + data'),
    ('datasource.reddit',           true,  'Reddit / PRAW ingestion'),
    ('datasource.rss',              true,  'RSS feed ingestion'),
    ('datasource.sec_edgar',        true,  'SEC EDGAR insider filings'),
    ('datasource.fred',             true,  'FRED macro indicators'),
    -- ML models
    ('ml.lstm',                     true,  'LSTM model in ensemble'),
    ('ml.xgboost',                  true,  'XGBoost model in ensemble'),
    ('ml.lightgbm',                 true,  'LightGBM model in ensemble'),
    ('ml.finbert',                  true,  'FinBERT deep sentiment scoring'),
    -- Alerts
    ('alert.browser_push',          true,  'Browser push via OneSignal'),
    ('alert.mobile_push',           true,  'Mobile push via OneSignal'),
    ('alert.email',                 true,  'Email notifications'),
    ('alert.sms',                   false, 'SMS via Twilio (costs money)'),
    ('alert.discord',               true,  'Discord message delivery'),
    ('alert.voice',                 false, 'Voice alert delivery'),
    -- Features
    ('feature.earnings_calendar',   true,  'Earnings calendar module'),
    ('feature.insider_tracking',    true,  'Insider trading tracker'),
    ('feature.macro_indicators',    true,  'Macro indicator module'),
    ('feature.correlation_graph',   true,  'Correlation graph explorer')
ON CONFLICT (flag) DO NOTHING;

-- ── Notification Log ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notification_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id),
    symbol      TEXT,
    alert_type  TEXT NOT NULL,
    channel     TEXT NOT NULL,
    status      TEXT NOT NULL,   -- 'sent' | 'failed' | 'skipped'
    error_msg   TEXT,
    sent_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_notif_log_user ON notification_log (user_id, sent_at DESC);

-- ── OHLCVRepository ───────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION fn_insert_ohlcv(
    p_time   TIMESTAMPTZ,
    p_symbol TEXT,
    p_open   NUMERIC,
    p_high   NUMERIC,
    p_low    NUMERIC,
    p_close  NUMERIC,
    p_volume BIGINT,
    p_source TEXT DEFAULT 'yfinance'
) RETURNS VOID AS $$
BEGIN
    INSERT INTO ohlcv (time, symbol, open, high, low, close, volume, source)
    VALUES (p_time, p_symbol, p_open, p_high, p_low, p_close, p_volume, p_source)
    ON CONFLICT (time, symbol) DO NOTHING;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_get_ohlcv_recent(
    p_symbol TEXT,
    p_days   INT
) RETURNS TABLE (
    "time" TIMESTAMPTZ, symbol TEXT,
    open   NUMERIC,     high   NUMERIC,
    low    NUMERIC,     close  NUMERIC,
    volume BIGINT,      source TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT o.time, o.symbol, o.open, o.high, o.low, o.close, o.volume, o.source
    FROM ohlcv o
    WHERE o.symbol = p_symbol
      AND o.time >= NOW() - (p_days || ' days')::INTERVAL
    ORDER BY o.time DESC;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_get_ohlcv_range(
    p_symbol TEXT,
    p_start  TIMESTAMPTZ,
    p_end    TIMESTAMPTZ
) RETURNS TABLE (
    "time" TIMESTAMPTZ, symbol TEXT,
    open   NUMERIC,     high   NUMERIC,
    low    NUMERIC,     close  NUMERIC,
    volume BIGINT,      source TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT o.time, o.symbol, o.open, o.high, o.low, o.close, o.volume, o.source
    FROM ohlcv o
    WHERE o.symbol = p_symbol
      AND o.time BETWEEN p_start AND p_end
    ORDER BY o.time ASC;
END;
$$ LANGUAGE plpgsql;


-- ── PredictionRepository ──────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION fn_insert_prediction(
    p_time                   TIMESTAMPTZ,
    p_symbol                 TEXT,
    p_horizon                TEXT,
    p_direction              TEXT,
    p_confidence             NUMERIC,
    p_lstm_prob_up           NUMERIC DEFAULT NULL,
    p_lstm_prob_down         NUMERIC DEFAULT NULL,
    p_lstm_prob_flat         NUMERIC DEFAULT NULL,
    p_xgb_prob_up            NUMERIC DEFAULT NULL,
    p_xgb_prob_down          NUMERIC DEFAULT NULL,
    p_xgb_prob_flat          NUMERIC DEFAULT NULL,
    p_lgbm_prob_up           NUMERIC DEFAULT NULL,
    p_lgbm_prob_down         NUMERIC DEFAULT NULL,
    p_lgbm_prob_flat         NUMERIC DEFAULT NULL,
    p_model_version          TEXT DEFAULT 'v0',
    p_feature_schema_version INT DEFAULT 1
) RETURNS VOID AS $$
BEGIN
    INSERT INTO predictions (
        time, symbol, horizon, direction, confidence,
        lstm_prob_up, lstm_prob_down, lstm_prob_flat,
        xgb_prob_up, xgb_prob_down, xgb_prob_flat,
        lgbm_prob_up, lgbm_prob_down, lgbm_prob_flat,
        model_version, feature_schema_version
    ) VALUES (
        p_time, p_symbol, p_horizon, p_direction, p_confidence,
        p_lstm_prob_up, p_lstm_prob_down, p_lstm_prob_flat,
        p_xgb_prob_up, p_xgb_prob_down, p_xgb_prob_flat,
        p_lgbm_prob_up, p_lgbm_prob_down, p_lgbm_prob_flat,
        p_model_version, p_feature_schema_version
    )
    ON CONFLICT (time, symbol, horizon) DO NOTHING;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_get_latest_prediction(
    p_symbol  TEXT,
    p_horizon TEXT
) RETURNS TABLE (
    "time" TIMESTAMPTZ, symbol          TEXT,
    horizon                TEXT,        direction       TEXT,
    confidence             NUMERIC,     lstm_prob_up    NUMERIC,
    lstm_prob_down         NUMERIC,     lstm_prob_flat  NUMERIC,
    xgb_prob_up            NUMERIC,     xgb_prob_down   NUMERIC,
    xgb_prob_flat          NUMERIC,     lgbm_prob_up    NUMERIC,
    lgbm_prob_down         NUMERIC,     lgbm_prob_flat  NUMERIC,
    model_version          TEXT,        feature_schema_version INT,
    resolved               BOOLEAN,     actual_direction TEXT,
    was_correct            BOOLEAN,     resolved_at     TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT p.time, p.symbol, p.horizon, p.direction, p.confidence,
           p.lstm_prob_up, p.lstm_prob_down, p.lstm_prob_flat,
           p.xgb_prob_up, p.xgb_prob_down, p.xgb_prob_flat,
           p.lgbm_prob_up, p.lgbm_prob_down, p.lgbm_prob_flat,
           p.model_version, p.feature_schema_version,
           p.resolved, p.actual_direction, p.was_correct, p.resolved_at
    FROM predictions p
    WHERE p.symbol = p_symbol AND p.horizon = p_horizon
    ORDER BY p.time DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_get_unresolved_predictions()
RETURNS TABLE (
    "time" TIMESTAMPTZ, symbol          TEXT,
    horizon                TEXT,        direction       TEXT,
    confidence             NUMERIC,     lstm_prob_up    NUMERIC,
    lstm_prob_down         NUMERIC,     lstm_prob_flat  NUMERIC,
    xgb_prob_up            NUMERIC,     xgb_prob_down   NUMERIC,
    xgb_prob_flat          NUMERIC,     lgbm_prob_up    NUMERIC,
    lgbm_prob_down         NUMERIC,     lgbm_prob_flat  NUMERIC,
    model_version          TEXT,        feature_schema_version INT,
    resolved               BOOLEAN,     actual_direction TEXT,
    was_correct            BOOLEAN,     resolved_at     TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT p.time, p.symbol, p.horizon, p.direction, p.confidence,
           p.lstm_prob_up, p.lstm_prob_down, p.lstm_prob_flat,
           p.xgb_prob_up, p.xgb_prob_down, p.xgb_prob_flat,
           p.lgbm_prob_up, p.lgbm_prob_down, p.lgbm_prob_flat,
           p.model_version, p.feature_schema_version,
           p.resolved, p.actual_direction, p.was_correct, p.resolved_at
    FROM predictions p
    WHERE p.resolved = FALSE
    ORDER BY p.time ASC;
END;
$$ LANGUAGE plpgsql;


-- ── TickerRepository ──────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION fn_get_all_active_tickers()
RETURNS TABLE (
    symbol TEXT, name TEXT, asset_type TEXT,
    sector TEXT, exchange TEXT, currency TEXT,
    is_active BOOLEAN, created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT t.symbol, t.name, t.asset_type, t.sector, t.exchange,
           t.currency, t.is_active, t.created_at
    FROM tickers t
    WHERE t.is_active = TRUE
    ORDER BY t.symbol;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_insert_ticker(
    p_symbol     TEXT,
    p_name       TEXT,
    p_asset_type TEXT,
    p_sector     TEXT DEFAULT NULL,
    p_exchange   TEXT DEFAULT NULL,
    p_currency   TEXT DEFAULT 'USD',
    p_is_active  BOOLEAN DEFAULT TRUE
) RETURNS VOID AS $$
BEGIN
    INSERT INTO tickers (symbol, name, asset_type, sector, exchange, currency, is_active)
    VALUES (p_symbol, p_name, p_asset_type, p_sector, p_exchange, p_currency, p_is_active)
    ON CONFLICT (symbol) DO NOTHING;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_deactivate_ticker(p_symbol TEXT) RETURNS VOID AS $$
BEGIN
    UPDATE tickers SET is_active = FALSE WHERE symbol = p_symbol;
END;
$$ LANGUAGE plpgsql;


-- ── SentimentRepository ───────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION fn_insert_sentiment(
    p_time          TIMESTAMPTZ,
    p_symbol        TEXT,
    p_source_type   TEXT,
    p_source_name   TEXT,
    p_score         NUMERIC,
    p_article_count INT DEFAULT 0,
    p_post_count    INT DEFAULT 0
) RETURNS VOID AS $$
BEGIN
    INSERT INTO sentiment_scores (time, symbol, source_type, source_name, score, article_count, post_count)
    VALUES (p_time, p_symbol, p_source_type, p_source_name, p_score, p_article_count, p_post_count)
    ON CONFLICT (time, symbol, source_type) DO UPDATE
        SET score         = EXCLUDED.score,
            source_name   = EXCLUDED.source_name,
            article_count = EXCLUDED.article_count,
            post_count    = EXCLUDED.post_count;
END;
$$ LANGUAGE plpgsql;

DROP FUNCTION IF EXISTS fn_get_sentiment_trend(text, integer) CASCADE;
CREATE OR REPLACE FUNCTION fn_get_sentiment_trend(
    p_symbol TEXT,
    p_days   INT
) RETURNS TABLE (
    "time"        TIMESTAMPTZ,
    symbol        TEXT,
    source_type   TEXT,
    source_name   TEXT,
    score         NUMERIC,
    article_count INT,
    post_count    INT
) AS $$
BEGIN
    RETURN QUERY
    SELECT s.time, s.symbol, s.source_type, s.source_name, s.score, s.article_count, s.post_count
    FROM sentiment_scores s
    WHERE s.symbol = p_symbol
      AND s.time >= NOW() - (p_days || ' days')::INTERVAL
    ORDER BY s.time DESC;
END;
$$ LANGUAGE plpgsql;


-- ── AlertConfigRepository ─────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION fn_get_alert_configs_for_user(
    p_user_id UUID
) RETURNS TABLE (
    id UUID, 
    user_id UUID, 
    symbol TEXT, 
    alert_type TEXT,
    min_confidence NUMERIC, 
    horizons TEXT[], 
    channels TEXT[],
    is_active BOOLEAN, 
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        a.id, a.user_id, a.symbol, a.alert_type, a.min_confidence,
           a.horizons, a.channels, a.is_active, a.created_at
    FROM alert_configs a
    WHERE a.user_id = p_user_id AND a.is_active = TRUE
    ORDER BY a.created_at DESC;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_get_matching_alert_configs(
    p_alert_type TEXT,
    p_symbol     TEXT DEFAULT NULL
) RETURNS TABLE (
    id UUID, user_id UUID, symbol TEXT, alert_type TEXT,
    min_confidence NUMERIC, horizons TEXT[], channels TEXT[],
    is_active BOOLEAN, created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT a.id, a.user_id, a.symbol, a.alert_type, a.min_confidence,
           a.horizons, a.channels, a.is_active, a.created_at
    FROM alert_configs a
    WHERE a.alert_type = p_alert_type
      AND a.is_active = TRUE
      AND (a.symbol IS NULL OR a.symbol = p_symbol)
    ORDER BY a.created_at DESC;
END;
$$ LANGUAGE plpgsql;


-- ── QuotaRepository ───────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION fn_get_all_quotas()
RETURNS TABLE (
    source TEXT, daily_limit INT, monthly_limit INT, notes TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT q.source, q.daily_limit, q.monthly_limit, q.notes
    FROM api_quotas q
    ORDER BY q.source;
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION fn_get_ohlcv_recent(
    p_symbol TEXT,
    p_days   INT
) RETURNS TABLE (
    "time"  TIMESTAMPTZ, symbol TEXT,
    open    NUMERIC,     high   NUMERIC,
    low     NUMERIC,     close  NUMERIC,
    volume  BIGINT,      source TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT o.time, o.symbol, o.open, o.high, o.low, o.close, o.volume, o.source
    FROM ohlcv o
    WHERE o.symbol = p_symbol
      AND o.time >= NOW() - (p_days || ' days')::INTERVAL
    ORDER BY o.time DESC;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_get_ohlcv_range(
    p_symbol TEXT,
    p_start  TIMESTAMPTZ,
    p_end    TIMESTAMPTZ
) RETURNS TABLE (
    "time"  TIMESTAMPTZ, symbol TEXT,
    open    NUMERIC,     high   NUMERIC,
    low     NUMERIC,     close  NUMERIC,
    volume  BIGINT,      source TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT o.time, o.symbol, o.open, o.high, o.low, o.close, o.volume, o.source
    FROM ohlcv o
    WHERE o.symbol = p_symbol
      AND o.time BETWEEN p_start AND p_end
    ORDER BY o.time ASC;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_get_latest_prediction(
    p_symbol  TEXT,
    p_horizon TEXT
) RETURNS TABLE (
    "time"                 TIMESTAMPTZ, symbol          TEXT,
    horizon                TEXT,        direction       TEXT,
    confidence             NUMERIC,     lstm_prob_up    NUMERIC,
    lstm_prob_down         NUMERIC,     lstm_prob_flat  NUMERIC,
    xgb_prob_up            NUMERIC,     xgb_prob_down   NUMERIC,
    xgb_prob_flat          NUMERIC,     lgbm_prob_up    NUMERIC,
    lgbm_prob_down         NUMERIC,     lgbm_prob_flat  NUMERIC,
    model_version          TEXT,        feature_schema_version INT,
    resolved               BOOLEAN,     actual_direction TEXT,
    was_correct            BOOLEAN,     resolved_at     TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT p.time, p.symbol, p.horizon, p.direction, p.confidence,
           p.lstm_prob_up, p.lstm_prob_down, p.lstm_prob_flat,
           p.xgb_prob_up, p.xgb_prob_down, p.xgb_prob_flat,
           p.lgbm_prob_up, p.lgbm_prob_down, p.lgbm_prob_flat,
           p.model_version, p.feature_schema_version,
           p.resolved, p.actual_direction, p.was_correct, p.resolved_at
    FROM predictions p
    WHERE p.symbol = p_symbol AND p.horizon = p_horizon
    ORDER BY p.time DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_get_unresolved_predictions()
RETURNS TABLE (
    "time"                 TIMESTAMPTZ, symbol          TEXT,
    horizon                TEXT,        direction       TEXT,
    confidence             NUMERIC,     lstm_prob_up    NUMERIC,
    lstm_prob_down         NUMERIC,     lstm_prob_flat  NUMERIC,
    xgb_prob_up            NUMERIC,     xgb_prob_down   NUMERIC,
    xgb_prob_flat          NUMERIC,     lgbm_prob_up    NUMERIC,
    lgbm_prob_down         NUMERIC,     lgbm_prob_flat  NUMERIC,
    model_version          TEXT,        feature_schema_version INT,
    resolved               BOOLEAN,     actual_direction TEXT,
    was_correct            BOOLEAN,     resolved_at     TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT p.time, p.symbol, p.horizon, p.direction, p.confidence,
           p.lstm_prob_up, p.lstm_prob_down, p.lstm_prob_flat,
           p.xgb_prob_up, p.xgb_prob_down, p.xgb_prob_flat,
           p.lgbm_prob_up, p.lgbm_prob_down, p.lgbm_prob_flat,
           p.model_version, p.feature_schema_version,
           p.resolved, p.actual_direction, p.was_correct, p.resolved_at
    FROM predictions p
    WHERE p.resolved = FALSE
    ORDER BY p.time ASC;
END;
$$ LANGUAGE plpgsql;

DROP FUNCTION IF EXISTS fn_get_sentiment_trend(text, integer) CASCADE;
CREATE OR REPLACE FUNCTION fn_get_sentiment_trend(
    p_symbol TEXT,
    p_days   INT
) RETURNS TABLE (
    "time"        TIMESTAMPTZ, symbol TEXT,
    source        TEXT,        score  NUMERIC,
    article_count INT,         post_count INT
) AS $$
BEGIN
    RETURN QUERY
    SELECT s.time, s.symbol, s.source, s.score, s.article_count, s.post_count
    FROM sentiment_scores s
    WHERE s.symbol = p_symbol
      AND s.time >= NOW() - (p_days || ' days')::INTERVAL
    ORDER BY s.time DESC;
END;
$$ LANGUAGE plpgsql;


-- Drop and recreate the sentiment_scores table
DROP TABLE IF EXISTS sentiment_scores;

CREATE TABLE IF NOT EXISTS sentiment_scores (
    time            TIMESTAMPTZ NOT NULL,
    symbol          TEXT NOT NULL REFERENCES tickers(symbol),
    source_type     TEXT NOT NULL,
    source_name     TEXT,
    score           NUMERIC(5,4) NOT NULL,
    article_count   INT NOT NULL DEFAULT 0,
    post_count      INT NOT NULL DEFAULT 0,
    PRIMARY KEY (time, symbol, source_type)
);

SELECT create_hypertable('sentiment_scores', 'time', chunk_time_interval => INTERVAL '1 month', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_sentiment_symbol_time ON sentiment_scores (symbol, time DESC);

-- Replace the two sentiment functions
CREATE OR REPLACE FUNCTION fn_insert_sentiment(
    p_time          TIMESTAMPTZ,
    p_symbol        TEXT,
    p_source_type   TEXT,
    p_source_name   TEXT,
    p_score         NUMERIC,
    p_article_count INT DEFAULT 0,
    p_post_count    INT DEFAULT 0
) RETURNS VOID AS $$
BEGIN
    INSERT INTO sentiment_scores (time, symbol, source_type, source_name, score, article_count, post_count)
    VALUES (p_time, p_symbol, p_source_type, p_source_name, p_score, p_article_count, p_post_count)
    ON CONFLICT (time, symbol, source_type) DO UPDATE
        SET score         = EXCLUDED.score,
            source_name   = EXCLUDED.source_name,
            article_count = EXCLUDED.article_count,
            post_count    = EXCLUDED.post_count;
END;
$$ LANGUAGE plpgsql;

DROP FUNCTION IF EXISTS fn_get_sentiment_trend(text, integer) CASCADE;
CREATE OR REPLACE FUNCTION fn_get_sentiment_trend(
    p_symbol TEXT,
    p_days   INT
) RETURNS TABLE (
    "time"        TIMESTAMPTZ,
    symbol        TEXT,
    source_type   TEXT,
    source_name   TEXT,
    score         NUMERIC,
    article_count INT,
    post_count    INT
) AS $$
BEGIN
    RETURN QUERY
    SELECT s.time, s.symbol, s.source_type, s.source_name, s.score, s.article_count, s.post_count
    FROM sentiment_scores s
    WHERE s.symbol = p_symbol
      AND s.time >= NOW() - (p_days || ' days')::INTERVAL
    ORDER BY s.time DESC;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_insert_sentiment(
    p_time          TIMESTAMPTZ,
    p_symbol        TEXT,
    p_source_type   TEXT,
    p_source_name   TEXT,
    p_score         NUMERIC,
    p_article_count INT DEFAULT 0,
    p_post_count    INT DEFAULT 0
) RETURNS VOID AS $$
BEGIN
    INSERT INTO sentiment_scores (time, symbol, source_type, source_name, score, article_count, post_count)
    VALUES (p_time, p_symbol, p_source_type, p_source_name, p_score, p_article_count, p_post_count)
    ON CONFLICT (time, symbol, source_type) DO UPDATE
        SET score         = EXCLUDED.score,
            source_name   = EXCLUDED.source_name,
            article_count = EXCLUDED.article_count,
            post_count    = EXCLUDED.post_count;
END;
$$ LANGUAGE plpgsql;

DROP FUNCTION IF EXISTS fn_get_sentiment_trend(text, integer) CASCADE;
CREATE OR REPLACE FUNCTION fn_get_sentiment_trend(
    p_symbol TEXT,
    p_days   INT
) RETURNS TABLE (
    "time"        TIMESTAMPTZ,
    symbol        TEXT,
    source_type   TEXT,
    source_name   TEXT,
    score         NUMERIC,
    article_count INT,
    post_count    INT
) AS $$
BEGIN
    RETURN QUERY
    SELECT s.time, s.symbol, s.source_type, s.source_name, s.score, s.article_count, s.post_count
    FROM sentiment_scores s
    WHERE s.symbol = p_symbol
      AND s.time >= NOW() - (p_days || ' days')::INTERVAL
    ORDER BY s.time DESC;
END;
$$ LANGUAGE plpgsql;

ALTER TABLE alert_configs 
ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

DROP FUNCTION fn_get_alert_configs_for_user(uuid);
DROP FUNCTION fn_get_matching_alert_configs(text, text);

CREATE OR REPLACE FUNCTION fn_get_alert_configs_for_user(
    p_user_id UUID
) RETURNS TABLE (
    id             UUID,
    user_id        UUID,
    symbol         TEXT,
    alert_type     TEXT,
    min_confidence NUMERIC,
    horizons       TEXT[],
    channels       TEXT[],
    is_active      BOOLEAN,
    created_at     TIMESTAMPTZ,
    updated_at     TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT a.id, a.user_id, a.symbol, a.alert_type, a.min_confidence,
           a.horizons, a.channels, a.is_active, a.created_at, a.updated_at
    FROM alert_configs a
    WHERE a.user_id = p_user_id AND a.is_active = TRUE
    ORDER BY a.created_at DESC;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_get_matching_alert_configs(
    p_alert_type TEXT,
    p_symbol     TEXT DEFAULT NULL
) RETURNS TABLE (
    id             UUID,
    user_id        UUID,
    symbol         TEXT,
    alert_type     TEXT,
    min_confidence NUMERIC,
    horizons       TEXT[],
    channels       TEXT[],
    is_active      BOOLEAN,
    created_at     TIMESTAMPTZ,
    updated_at     TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT a.id, a.user_id, a.symbol, a.alert_type, a.min_confidence,
           a.horizons, a.channels, a.is_active, a.created_at, a.updated_at
    FROM alert_configs a
    WHERE a.alert_type = p_alert_type
      AND a.is_active = TRUE
      AND (a.symbol IS NULL OR a.symbol = p_symbol)
    ORDER BY a.created_at DESC;
END;
$$ LANGUAGE plpgsql;

-- Add missing columns to api_quotas
ALTER TABLE api_quotas
    ADD COLUMN IF NOT EXISTS daily_used      INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS monthly_used    INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS is_unlimited    BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS low_threshold   INT DEFAULT 10,
    ADD COLUMN IF NOT EXISTS last_reset_daily   TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS last_reset_monthly TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- Replace fn_get_all_quotas to return all fields
DROP FUNCTION fn_get_all_quotas();

CREATE OR REPLACE FUNCTION fn_get_all_quotas()
RETURNS TABLE (
    source              TEXT,
    daily_limit         INT,
    monthly_limit       INT,
    daily_used          INT,
    monthly_used        INT,
    is_unlimited        BOOLEAN,
    low_threshold       INT,
    last_reset_daily    TIMESTAMPTZ,
    last_reset_monthly  TIMESTAMPTZ,
    updated_at          TIMESTAMPTZ,
    notes               TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT q.source, q.daily_limit, q.monthly_limit,
           q.daily_used, q.monthly_used, q.is_unlimited,
           q.low_threshold, q.last_reset_daily, q.last_reset_monthly,
           q.updated_at, q.notes
    FROM api_quotas q
    ORDER BY q.source;
END;
$$ LANGUAGE plpgsql;

-- Increment daily or monthly used counter (skips if is_unlimited is true)
CREATE OR REPLACE FUNCTION fn_increment_quota(
    p_source TEXT,
    p_daily  BOOLEAN
) RETURNS VOID AS $$
BEGIN
    IF (SELECT is_unlimited FROM api_quotas WHERE source = p_source) THEN
        RETURN;
    END IF;

    IF p_daily THEN
        UPDATE api_quotas
        SET daily_used = daily_used + 1,
            updated_at = NOW()
        WHERE source = p_source;
    ELSE
        UPDATE api_quotas
        SET monthly_used = monthly_used + 1,
            updated_at = NOW()
        WHERE source = p_source;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Reset counters for a source
CREATE OR REPLACE FUNCTION fn_reset_quota(
    p_source TEXT,
    p_daily  BOOLEAN
) RETURNS VOID AS $$
BEGIN
    IF p_daily THEN
        UPDATE api_quotas
        SET daily_used = 0,
            last_reset_daily = NOW(),
            updated_at = NOW()
        WHERE source = p_source;
    ELSE
        UPDATE api_quotas
        SET monthly_used = 0,
            last_reset_monthly = NOW(),
            updated_at = NOW()
        WHERE source = p_source;
    END IF;
END;
$$ LANGUAGE plpgsql;

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


-- Real-time intraday sentiment stream (replaces InfluxDB SentimentStreamRepository)
CREATE TABLE IF NOT EXISTS sentiment_stream (
    time        TIMESTAMPTZ     NOT NULL,
    symbol      TEXT            NOT NULL,
    source      TEXT            NOT NULL,   -- "news", "reddit", "finbert", "vader"
    score       DOUBLE PRECISION NOT NULL   -- -1.0 to +1.0
);

SELECT create_hypertable('sentiment_stream', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_sentiment_stream_symbol_time
    ON sentiment_stream (symbol, time DESC);

SELECT add_retention_policy('sentiment_stream', INTERVAL '30 days', if_not_exists => TRUE);


"""
    # Use exec_driver_sql to avoid SQLAlchemy parsing colons as bind parameters
    connection.exec_driver_sql(sql_statements)


def downgrade() -> None:
    pass
