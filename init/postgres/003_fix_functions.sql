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
