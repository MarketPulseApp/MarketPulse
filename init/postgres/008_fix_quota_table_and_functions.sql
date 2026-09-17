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
