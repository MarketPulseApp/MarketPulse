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
