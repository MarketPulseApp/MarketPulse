-- MarketPulse PostgreSQL + TimescaleDB Schema
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
    source          TEXT NOT NULL,   -- 'news' | 'reddit' | 'combined'
    score           NUMERIC(5,4) NOT NULL,
    article_count   INT NOT NULL DEFAULT 0,
    post_count      INT NOT NULL DEFAULT 0,
    PRIMARY KEY (time, symbol, source)
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
    daily_limit     INT NOT NULL,
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