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
