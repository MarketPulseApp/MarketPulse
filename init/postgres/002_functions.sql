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
    time   TIMESTAMPTZ, symbol TEXT,
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
    time   TIMESTAMPTZ, symbol TEXT,
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
    time                   TIMESTAMPTZ, symbol          TEXT,
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
    time                   TIMESTAMPTZ, symbol          TEXT,
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
    p_source        TEXT,
    p_score         NUMERIC,
    p_article_count INT DEFAULT 0,
    p_post_count    INT DEFAULT 0
) RETURNS VOID AS $$
BEGIN
    INSERT INTO sentiment_scores (time, symbol, source, score, article_count, post_count)
    VALUES (p_time, p_symbol, p_source, p_score, p_article_count, p_post_count)
    ON CONFLICT (time, symbol, source) DO UPDATE
        SET score         = EXCLUDED.score,
            article_count = EXCLUDED.article_count,
            post_count    = EXCLUDED.post_count;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_get_sentiment_trend(
    p_symbol TEXT,
    p_days   INT
) RETURNS TABLE (
    time TEXT, symbol TEXT, source TEXT,
    score NUMERIC, article_count INT, post_count INT
) AS $$
BEGIN
    RETURN QUERY
    SELECT s.time::TEXT, s.symbol, s.source, s.score, s.article_count, s.post_count
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
    id UUID, user_id UUID, symbol TEXT, alert_type TEXT,
    min_confidence NUMERIC, horizons TEXT[], channels TEXT[],
    is_active BOOLEAN, created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT a.id, a.user_id, a.symbol, a.alert_type, a.min_confidence,
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
