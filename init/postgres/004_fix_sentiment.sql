-- Drop and recreate the sentiment_scores table
DROP TABLE IF EXISTS sentiment_scores;

CREATE TABLE sentiment_scores (
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
