# MarketPulse — Database Setup Guide

> **17 databases, two deployment contexts (local Docker and Proxmox), two cloud free tiers, and
> five embedded databases.** This document is the authoritative reference for getting every
> database running, connected, and verified. Do not start writing application code until every
> database listed in Phase 1 of README_5 has a passing health check.

---

## Quick Reference — All 17 Databases

| # | Database | Type | Host | Port | Container Name |
|---|---------|------|------|------|----------------|
| 1 | PostgreSQL + TimescaleDB | Relational + time-series | Node 1 | 5432 | `marketpulse-postgres` |
| 2 | Valkey | Key-value + pub/sub | Node 1 | 6379 | `marketpulse-valkey` |
| 3 | ChromaDB | Vector | Node 1 | 8000 | `marketpulse-chroma` |
| 4 | SurrealDB (primary) | Multi-model | Node 1 | 8001 | `marketpulse-surreal` |
| 5 | MinIO | Object storage | Node 1 | 9000/9001 | `marketpulse-minio` |
| 6 | MongoDB | Document | Node 2 | 27017 | `marketpulse-mongo` |
| 7 | Elasticsearch | Full-text search | Node 2 | 9200 | `marketpulse-elastic` |
| 8 | InfluxDB | Time-series (secondary) | Node 2 | 8086 | `marketpulse-influx` |
| 9 | SQLite event journal | Embedded append-only | App process | — | (file) |
| 10 | SQLite audit ledger | Embedded hash-chain | App process | — | (file) |
| 11 | SpatiaLite | Embedded geospatial | App process | — | (file) |
| 12 | ZODB | Embedded object-oriented | App process | — | (file) |
| 13 | DuckDB in-memory | Embedded OLAP live | App process | — | (in-memory) |
| 14 | DuckDB persistent | Embedded OLAP analytics | App process | — | (file) |
| 15 | NetworkX → SQLite | Embedded graph | App process | — | (file) |
| 16 | DataStax Astra (Cassandra) | Cloud — free tier | Cloud | 9042 (TLS) | (cloud) |
| 17 | Neo4j AuraDB Free | Cloud — free tier | Cloud | 7687 (Bolt) | (cloud) |

---

## Python Package Install — Complete Command

Run this once after creating your virtual environment. This covers every database driver,
every API client library, and every ML dependency used across the entire project.

```bash
pip install \
  # --- Database drivers ---
  asyncpg psycopg2-binary sqlalchemy[asyncio] alembic \
  timescaledb \
  valkey hiredis \
  chromadb \
  sursql \
  minio \
  motor pymongo \
  elasticsearch[async] \
  influxdb-client \
  zodb zodbpickle \
  duckdb \
  spatialite \
  networkx \
  cassandra-driver \
  neo4j \
  # --- FastAPI and async ---
  fastapi uvicorn[standard] httpx aiohttp \
  pydantic pydantic-settings \
  # --- Auth ---
  python-jose[cryptography] passlib[bcrypt] pyotp qrcode \
  # --- Task queue ---
  arq \
  # --- Market data ---
  yfinance alpha-vantage polygon-api-client \
  # --- Crypto data ---
  pycoingecko \
  web3 \
  # --- News and RSS ---
  feedparser newsapi-python \
  # --- Reddit ---
  praw \
  # --- Technical indicators ---
  ta pandas numpy \
  # --- ML / AI ---
  torch torchvision \
  xgboost lightgbm scikit-learn \
  transformers[torch] tokenizers \
  vaderSentiment \
  onnx onnxruntime \
  grpcio grpcio-tools protobuf \
  # --- Notifications ---
  onesignal-sdk twilio \
  # --- Discord bot ---
  discord.py \
  pillow mplfinance \
  # --- Policy ---
  opa-client \
  # --- Observability ---
  prometheus-client opentelemetry-sdk opentelemetry-exporter-otlp \
  python-json-logger \
  # --- Charts and export ---
  reportlab \
  openpyxl \
  # --- Voice ---
  flask ask-sdk-core \
  # --- Scraping ---
  playwright \
  # --- Utilities ---
  python-dotenv \
  pydantic \
  arrow \
  tenacity \
  structlog \
  rich
```

> **Note on TA-Lib:** If you prefer TA-Lib over `ta`, install the C library first
> (`apt-get install libta-lib-dev` or `brew install ta-lib`), then `pip install TA-Lib`.
> The `ta` package requires no C dependencies and is the default choice for this project.

---

## Storage Budget — Main Rig (95.5GB Free)

The constraint is real. Every service below has an explicit allocation. The total must stay below
85GB, leaving ≥10GB as operational headroom.

| Service | Allocated Storage | Notes |
|---------|------------------|-------|
| PostgreSQL + TimescaleDB data | 8 GB | 2 years OHLCV × 25 tickers + all hypertables |
| TimescaleDB compressed chunks | 3 GB | Timescale compression reduces historical data ~10× |
| MongoDB documents | 6 GB | News articles (~100KB average) + Reddit posts |
| Elasticsearch index | 4 GB | Inverted index over all news + Reddit text |
| ChromaDB embeddings | 3 GB | ~1M vectors at 384 dimensions (float32) |
| SurrealDB | 1 GB | Cross-domain query graph data |
| MinIO objects | 10 GB | Chart images + exported reports + Parquet archives |
| InfluxDB | 2 GB | High-frequency mention counts + sentiment stream |
| SQLite files (all four) | 0.5 GB | Event journal + audit ledger + SpatiaLite + NetworkX |
| ZODB | 0.2 GB | Ticker registry — small, bounded by ticker count |
| DuckDB persistent | 1 GB | OLAP analytics over Parquet |
| ML model files | 8 GB | FinBERT (~440MB), LSTM per-ticker, XGBoost, LightGBM |
| Docker images | 12 GB | All container images pulled and cached |
| Build cache | 3 GB | pip cache, npm cache, Docker build layers |
| Application code | 0.5 GB | Python source + React build artifacts |
| Log files (Loki storage) | 4 GB | Rotated logs, capped by Loki retention policy |
| **Subtotal** | **66.2 GB** | |
| **Operational headroom** | **≥10 GB** | Hard floor — alert if free space drops below this |
| **Buffer** | **~19.3 GB** | Room for data growth before storage management kicks in |

**Storage growth rate (once running):**
- OHLCV data: ~50MB/month per 25 tickers at daily granularity
- News documents: ~300MB/month (100 articles/day × 30 days × average document size)
- Reddit posts: ~150MB/month
- Chart images: ~500MB/month (if chart generation is heavy)
- Log files: capped by Loki retention (default: 14-day rolling window)

**At 12-month run time:** estimated 84GB total. Still within budget, but begin planning MinIO
archival to cold storage (a spare drive or NAS) at the 9-month mark.

---

## Complete Local docker-compose.yml

This is the full compose file for local development on the main rig. All services that will
eventually migrate to Proxmox nodes are here together for local-first development.

```yaml
# docker-compose.yml
# MarketPulse — Local Development Stack
# Run: docker compose up -d
# Stop: docker compose down
# Full teardown: docker compose down -v  (DESTROYS ALL DATA)

version: "3.9"

networks:
  marketpulse:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16

volumes:
  postgres_data:
  valkey_data:
  chroma_data:
  surreal_data:
  minio_data:
  mongo_data:
  elastic_data:
  influx_data:
  influx_config:
  loki_data:
  grafana_data:
  prometheus_data:

services:

  # ─────────────────────────────────────────────────
  # NODE 1 SERVICES
  # ─────────────────────────────────────────────────

  postgres:
    image: timescale/timescaledb:latest-pg15
    container_name: marketpulse-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-marketpulse}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB:-marketpulse}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init/postgres:/docker-entrypoint-initdb.d
    networks:
      - marketpulse
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-marketpulse}"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          memory: 2G

  valkey:
    image: valkey/valkey:7.2-alpine
    container_name: marketpulse-valkey
    restart: unless-stopped
    command: >
      valkey-server
      --requirepass ${VALKEY_PASSWORD}
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
      --save 60 1000
      --appendonly yes
    ports:
      - "6379:6379"
    volumes:
      - valkey_data:/data
    networks:
      - marketpulse
    healthcheck:
      test: ["CMD", "valkey-cli", "-a", "${VALKEY_PASSWORD}", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  chromadb:
    image: chromadb/chroma:latest
    container_name: marketpulse-chroma
    restart: unless-stopped
    environment:
      CHROMA_SERVER_AUTH_CREDENTIALS: ${CHROMA_TOKEN}
      CHROMA_SERVER_AUTH_CREDENTIALS_PROVIDER: chromadb.auth.token.TokenConfigServerAuthCredentialsProvider
      CHROMA_SERVER_AUTH_PROVIDER: chromadb.auth.token.TokenAuthServerProvider
    ports:
      - "8000:8000"
    volumes:
      - chroma_data:/chroma/.chroma/index
    networks:
      - marketpulse
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/heartbeat"]
      interval: 15s
      timeout: 5s
      retries: 5

  surrealdb:
    image: surrealdb/surrealdb:latest
    container_name: marketpulse-surreal
    restart: unless-stopped
    command: start --log trace --user ${SURREAL_USER:-root} --pass ${SURREAL_PASSWORD} file:/var/lib/surrealdb/data
    ports:
      - "8001:8000"
    volumes:
      - surreal_data:/var/lib/surrealdb
    networks:
      - marketpulse
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 15s
      timeout: 5s
      retries: 5

  minio:
    image: minio/minio:latest
    container_name: marketpulse-minio
    restart: unless-stopped
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-marketpulse}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    ports:
      - "9000:9000"   # S3 API
      - "9001:9001"   # Console
    volumes:
      - minio_data:/data
    networks:
      - marketpulse
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 15s
      timeout: 5s
      retries: 5

  opa:
    image: openpolicyagent/opa:latest-rootless
    container_name: marketpulse-opa
    restart: unless-stopped
    command: run --server --addr :8181 --log-level info /policies
    ports:
      - "8181:8181"
    volumes:
      - ./policies:/policies:ro
    networks:
      - marketpulse
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8181/health"]
      interval: 10s
      timeout: 3s
      retries: 5

  # ─────────────────────────────────────────────────
  # NODE 2 SERVICES
  # ─────────────────────────────────────────────────

  mongodb:
    image: mongo:7.0
    container_name: marketpulse-mongo
    restart: unless-stopped
    environment:
      MONGO_INITDB_ROOT_USERNAME: ${MONGO_USER:-marketpulse}
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASSWORD}
      MONGO_INITDB_DATABASE: marketpulse
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db
      - ./init/mongo:/docker-entrypoint-initdb.d
    networks:
      - marketpulse
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 15s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          memory: 2G

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.12.0
    container_name: marketpulse-elastic
    restart: unless-stopped
    environment:
      - discovery.type=single-node
      - ES_JAVA_OPTS=-Xms1g -Xmx1g
      - xpack.security.enabled=true
      - ELASTIC_PASSWORD=${ELASTIC_PASSWORD}
      - xpack.security.http.ssl.enabled=false
    ports:
      - "9200:9200"
    volumes:
      - elastic_data:/usr/share/elasticsearch/data
    networks:
      - marketpulse
    ulimits:
      memlock:
        soft: -1
        hard: -1
    healthcheck:
      test: ["CMD-SHELL", "curl -s -u elastic:${ELASTIC_PASSWORD} http://localhost:9200/_cluster/health | grep -v '\"status\":\"red\"'"]
      interval: 20s
      timeout: 10s
      retries: 5

  influxdb:
    image: influxdb:2.7-alpine
    container_name: marketpulse-influx
    restart: unless-stopped
    environment:
      DOCKER_INFLUXDB_INIT_MODE: setup
      DOCKER_INFLUXDB_INIT_USERNAME: ${INFLUX_USER:-marketpulse}
      DOCKER_INFLUXDB_INIT_PASSWORD: ${INFLUX_PASSWORD}
      DOCKER_INFLUXDB_INIT_ORG: marketpulse
      DOCKER_INFLUXDB_INIT_BUCKET: sentiment_stream
      DOCKER_INFLUXDB_INIT_ADMIN_TOKEN: ${INFLUX_TOKEN}
    ports:
      - "8086:8086"
    volumes:
      - influx_data:/var/lib/influxdb2
      - influx_config:/etc/influxdb2
    networks:
      - marketpulse
    healthcheck:
      test: ["CMD", "influx", "ping"]
      interval: 15s
      timeout: 5s
      retries: 5

  # ─────────────────────────────────────────────────
  # OBSERVABILITY STACK (Node 1 in production)
  # ─────────────────────────────────────────────────

  prometheus:
    image: prom/prometheus:latest
    container_name: marketpulse-prometheus
    restart: unless-stopped
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.retention.time=30d'
      - '--web.enable-lifecycle'
    ports:
      - "9090:9090"
    volumes:
      - ./observability/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    networks:
      - marketpulse

  grafana:
    image: grafana/grafana:latest
    container_name: marketpulse-grafana
    restart: unless-stopped
    environment:
      GF_SECURITY_ADMIN_USER: ${GRAFANA_USER:-admin}
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
      GF_INSTALL_PLUGINS: grafana-clock-panel,grafana-simple-json-datasource
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./observability/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./observability/grafana/datasources:/etc/grafana/provisioning/datasources
    networks:
      - marketpulse

  loki:
    image: grafana/loki:latest
    container_name: marketpulse-loki
    restart: unless-stopped
    command: -config.file=/etc/loki/loki.yml
    ports:
      - "3100:3100"
    volumes:
      - loki_data:/loki
      - ./observability/loki.yml:/etc/loki/loki.yml:ro
    networks:
      - marketpulse

  jaeger:
    image: jaegertracing/all-in-one:latest
    container_name: marketpulse-jaeger
    restart: unless-stopped
    environment:
      COLLECTOR_OTLP_ENABLED: "true"
    ports:
      - "16686:16686"   # Jaeger UI
      - "4317:4317"     # OTLP gRPC
      - "4318:4318"     # OTLP HTTP
    networks:
      - marketpulse
```

---

## Database 1 — PostgreSQL + TimescaleDB

**Role:** Primary relational store (users, tickers, watchlists, alert configs, quota tracking) and
time-series hypertables (OHLCV price history, prediction history, sentiment scores over time,
technical indicator snapshots).

**Why TimescaleDB:** Time-series queries on financial data (e.g., "give me AAPL's close price
every day for the last 6 months, ordered by time") are extremely common. TimescaleDB's hypertables
partition data by time automatically, making these queries 10–100× faster than a plain PostgreSQL
table of the same size. The `time_bucket` function is used throughout the application for OHLCV
aggregations.

### Environment Variables

```bash
POSTGRES_USER=marketpulse
POSTGRES_PASSWORD=<strong-password>
POSTGRES_DB=marketpulse
POSTGRES_HOST=localhost          # or Node 1 IP on Proxmox
POSTGRES_PORT=5432
DATABASE_URL=postgresql+asyncpg://marketpulse:<password>@localhost:5432/marketpulse
```

### Initial Schema — init/postgres/001_schema.sql

```sql
-- Enable TimescaleDB
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- for fuzzy search on ticker symbols

-- ─── Users ──────────────────────────────────────────────────────────────────
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email       TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    totp_secret TEXT,                  -- NULL if TOTP not enrolled
    totp_enabled BOOLEAN DEFAULT FALSE,
    sms_2fa_enabled BOOLEAN DEFAULT FALSE,
    discord_id  TEXT,                  -- NULL if Discord not linked
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Tickers ────────────────────────────────────────────────────────────────
CREATE TABLE tickers (
    symbol      TEXT PRIMARY KEY,      -- 'AAPL', 'BTC-USD', 'SPY'
    name        TEXT NOT NULL,         -- 'Apple Inc.', 'Bitcoin'
    asset_type  TEXT NOT NULL CHECK (asset_type IN ('stock','crypto','etf','index')),
    sector      TEXT,
    industry    TEXT,
    market_cap  BIGINT,
    logo_url    TEXT,
    is_active   BOOLEAN DEFAULT TRUE,
    added_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Watchlists ─────────────────────────────────────────────────────────────
CREATE TABLE watchlists (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE watchlist_tickers (
    watchlist_id UUID NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
    symbol       TEXT NOT NULL REFERENCES tickers(symbol) ON DELETE CASCADE,
    added_at     TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (watchlist_id, symbol)
);

-- ─── OHLCV Price History (Hypertable) ───────────────────────────────────────
CREATE TABLE ohlcv (
    time        TIMESTAMPTZ NOT NULL,
    symbol      TEXT NOT NULL REFERENCES tickers(symbol),
    open        NUMERIC(18,6) NOT NULL,
    high        NUMERIC(18,6) NOT NULL,
    low         NUMERIC(18,6) NOT NULL,
    close       NUMERIC(18,6) NOT NULL,
    volume      BIGINT NOT NULL,
    interval    TEXT NOT NULL DEFAULT '1d',  -- '1d', '1h', '15m'
    PRIMARY KEY (time, symbol, interval)
);

SELECT create_hypertable('ohlcv', 'time',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);

-- Enable compression on ohlcv (data older than 7 days)
ALTER TABLE ohlcv SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol,interval',
    timescaledb.compress_orderby = 'time DESC'
);
SELECT add_compression_policy('ohlcv', INTERVAL '7 days');

-- ─── Predictions (Hypertable) ───────────────────────────────────────────────
CREATE TABLE predictions (
    time            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol          TEXT NOT NULL REFERENCES tickers(symbol),
    horizon         TEXT NOT NULL CHECK (horizon IN ('1d','3d','7d','30d')),
    direction       TEXT NOT NULL CHECK (direction IN ('UP','FLAT','DOWN')),
    confidence      NUMERIC(5,2) NOT NULL CHECK (confidence BETWEEN 0 AND 100),
    -- Component scores
    lstm_direction  TEXT,
    lstm_confidence NUMERIC(5,2),
    xgb_direction   TEXT,
    xgb_confidence  NUMERIC(5,2),
    lgbm_direction  TEXT,
    lgbm_confidence NUMERIC(5,2),
    sentiment_score NUMERIC(8,4),
    anomaly_flag    BOOLEAN DEFAULT FALSE,
    -- Outcome tracking
    outcome_time    TIMESTAMPTZ,   -- populated when horizon elapses
    actual_direction TEXT,          -- actual UP/FLAT/DOWN after horizon
    was_correct     BOOLEAN,        -- NULL until outcome known
    PRIMARY KEY (time, symbol, horizon)
);

SELECT create_hypertable('predictions', 'time',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);

-- ─── Sentiment Scores (Hypertable) ──────────────────────────────────────────
CREATE TABLE sentiment_scores (
    time        TIMESTAMPTZ NOT NULL,
    symbol      TEXT NOT NULL REFERENCES tickers(symbol),
    source_type TEXT NOT NULL,   -- 'reddit', 'news', 'combined'
    source_name TEXT,            -- 'r/wallstreetbets', 'NewsAPI', etc.
    score       NUMERIC(8,4) NOT NULL,  -- range -1.0 to +1.0
    article_count INT DEFAULT 0,
    post_count    INT DEFAULT 0,
    PRIMARY KEY (time, symbol, source_type, source_name)
);

SELECT create_hypertable('sentiment_scores', 'time',
    chunk_time_interval => INTERVAL '1 week',
    if_not_exists => TRUE
);

-- ─── Alert Configurations ───────────────────────────────────────────────────
CREATE TABLE alert_configs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol          TEXT REFERENCES tickers(symbol),  -- NULL = global alert
    alert_type      TEXT NOT NULL,
    is_enabled      BOOLEAN DEFAULT TRUE,
    threshold_value NUMERIC,
    channels        JSONB NOT NULL DEFAULT '[]',  -- ["browser","discord","email"]
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ─── API Quota Tracking ─────────────────────────────────────────────────────
CREATE TABLE api_quotas (
    source_name     TEXT PRIMARY KEY,
    daily_limit     INT,
    monthly_limit   INT,
    daily_used      INT DEFAULT 0,
    monthly_used    INT DEFAULT 0,
    is_unlimited    BOOLEAN DEFAULT FALSE,
    low_threshold   INT DEFAULT 10,
    last_reset_daily   TIMESTAMPTZ DEFAULT NOW(),
    last_reset_monthly TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Seed initial quota records
INSERT INTO api_quotas (source_name, daily_limit, monthly_limit) VALUES
    ('alpha_vantage',   25,    NULL),
    ('polygon_realtime', NULL, NULL),  -- 5/min, tracked differently
    ('coingecko',        NULL, NULL),  -- rate-limited but no hard daily cap
    ('coinmarketcap',    333,  10000),
    ('newsapi',          100,  NULL),
    ('gnews',            100,  NULL),
    ('finnhub',          NULL, NULL),  -- 60/min
    ('glassnode',        NULL, NULL),
    ('intothebox',       NULL, NULL),
    ('etherscan',        NULL, NULL)
ON CONFLICT DO NOTHING;

-- ─── Feature Flags ──────────────────────────────────────────────────────────
CREATE TABLE feature_flags (
    flag_name   TEXT PRIMARY KEY,
    is_enabled  BOOLEAN DEFAULT TRUE,
    description TEXT,
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO feature_flags (flag_name, is_enabled, description) VALUES
    ('datasource.alpha_vantage',    TRUE,  'Alpha Vantage fundamental data'),
    ('datasource.polygon',          TRUE,  'Polygon.io real-time data'),
    ('datasource.coingecko',        TRUE,  'CoinGecko crypto data'),
    ('datasource.coinmarketcap',    TRUE,  'CoinMarketCap crypto data'),
    ('datasource.newsapi',          TRUE,  'NewsAPI news aggregation'),
    ('datasource.gnews',            TRUE,  'GNews news aggregation'),
    ('datasource.finnhub',          TRUE,  'Finnhub market data and news'),
    ('datasource.glassnode',        TRUE,  'Glassnode on-chain data'),
    ('datasource.etherscan',        TRUE,  'Etherscan Ethereum data'),
    ('datasource.reddit',           TRUE,  'Reddit PRAW sentiment'),
    ('datasource.sec_edgar',        TRUE,  'SEC EDGAR insider filings'),
    ('datasource.fred',             TRUE,  'FRED economic indicators'),
    ('ml.lstm',                     TRUE,  'LSTM time-series model'),
    ('ml.xgboost',                  TRUE,  'XGBoost tabular model'),
    ('ml.lightgbm',                 TRUE,  'LightGBM tabular model'),
    ('ml.finbert',                  TRUE,  'FinBERT deep NLP sentiment'),
    ('ml.vader',                    TRUE,  'VADER fast sentiment scoring'),
    ('ml.isolation_forest',         TRUE,  'Isolation Forest anomaly detection'),
    ('alert.browser_push',          TRUE,  'Browser push via OneSignal'),
    ('alert.mobile_push',           TRUE,  'Mobile push via OneSignal'),
    ('alert.email',                 TRUE,  'Email alerts via SMTP'),
    ('alert.sms',                   FALSE, 'SMS alerts via Twilio (disabled by default)'),
    ('alert.discord',               TRUE,  'Discord DM/channel alerts'),
    ('alert.voice',                 TRUE,  'Voice announcements (Alexa/Google Home)')
ON CONFLICT DO NOTHING;

-- ─── Technical Indicator Snapshots (Hypertable) ─────────────────────────────
CREATE TABLE technical_indicators (
    time        TIMESTAMPTZ NOT NULL,
    symbol      TEXT NOT NULL REFERENCES tickers(symbol),
    -- Trend
    sma_20      NUMERIC(18,6),
    sma_50      NUMERIC(18,6),
    sma_200     NUMERIC(18,6),
    ema_12      NUMERIC(18,6),
    ema_26      NUMERIC(18,6),
    -- Momentum
    rsi_14      NUMERIC(8,4),
    macd_line   NUMERIC(18,6),
    macd_signal NUMERIC(18,6),
    macd_hist   NUMERIC(18,6),
    stoch_k     NUMERIC(8,4),
    stoch_d     NUMERIC(8,4),
    williams_r  NUMERIC(8,4),
    -- Volatility
    bb_upper    NUMERIC(18,6),
    bb_middle   NUMERIC(18,6),
    bb_lower    NUMERIC(18,6),
    atr_14      NUMERIC(18,6),
    -- Volume
    obv         BIGINT,
    vwap        NUMERIC(18,6),
    -- Trend strength
    adx_14      NUMERIC(8,4),
    PRIMARY KEY (time, symbol)
);

SELECT create_hypertable('technical_indicators', 'time',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);

-- ─── Notification Log ───────────────────────────────────────────────────────
CREATE TABLE notification_log (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID REFERENCES users(id),
    alert_type  TEXT NOT NULL,
    channel     TEXT NOT NULL,
    symbol      TEXT,
    message     TEXT NOT NULL,
    status      TEXT DEFAULT 'sent',  -- 'sent', 'failed', 'delivered'
    sent_at     TIMESTAMPTZ DEFAULT NOW(),
    delivered_at TIMESTAMPTZ
);

-- ─── Indexes ─────────────────────────────────────────────────────────────────
CREATE INDEX idx_ohlcv_symbol ON ohlcv (symbol, time DESC);
CREATE INDEX idx_predictions_symbol_horizon ON predictions (symbol, horizon, time DESC);
CREATE INDEX idx_predictions_unresolved ON predictions (time, symbol, horizon)
    WHERE was_correct IS NULL AND outcome_time IS NULL;
CREATE INDEX idx_sentiment_symbol ON sentiment_scores (symbol, time DESC);
CREATE INDEX idx_tickers_symbol_trgm ON tickers USING GIN (symbol gin_trgm_ops);
CREATE INDEX idx_alert_configs_user ON alert_configs (user_id, alert_type);
```

### Alembic Setup

```bash
# In the project root
alembic init alembic
# Edit alembic/env.py to use DATABASE_URL from environment
# Generate first migration from the schema above
alembic revision --autogenerate -m "initial_schema"
alembic upgrade head
```

### Verification Commands

```bash
# Container running
docker exec marketpulse-postgres pg_isready -U marketpulse

# TimescaleDB extension loaded
docker exec marketpulse-postgres psql -U marketpulse -c "\dx timescaledb"

# Hypertables exist
docker exec marketpulse-postgres psql -U marketpulse -d marketpulse \
    -c "SELECT hypertable_name FROM timescaledb_information.hypertables;"

# Expected output:
#   hypertable_name
#   ─────────────────────
#   ohlcv
#   predictions
#   sentiment_scores
#   technical_indicators

# Insert test OHLCV row and query it
docker exec marketpulse-postgres psql -U marketpulse -d marketpulse \
    -c "INSERT INTO tickers (symbol, name, asset_type) VALUES ('TEST', 'Test Ticker', 'stock') ON CONFLICT DO NOTHING;"
docker exec marketpulse-postgres psql -U marketpulse -d marketpulse \
    -c "INSERT INTO ohlcv VALUES (NOW(), 'TEST', 100.0, 101.0, 99.0, 100.5, 1000000, '1d');"
docker exec marketpulse-postgres psql -U marketpulse -d marketpulse \
    -c "SELECT time_bucket('1 day', time) AS day, symbol, avg(close) FROM ohlcv WHERE symbol='TEST' GROUP BY day, symbol;"
```

### Error Reference

| Error | Cause | Fix |
|-------|-------|-----|
| `FATAL: password authentication failed` | Wrong `POSTGRES_PASSWORD` in env | Check `.env` file; password must match what was set when volume was first created. If volume already exists with old password, run `docker compose down -v` to destroy and re-init (loses data). |
| `timescaledb extension not found` | Wrong image — used `postgres:15` instead of `timescale/timescaledb` | Change image to `timescale/timescaledb:latest-pg15` and recreate container. |
| `create_hypertable already a hypertable` | Running the schema init script twice | Safe to ignore if wrapped in `IF NOT EXISTS`. Otherwise add `if_not_exists => TRUE` to the `create_hypertable` call. |
| `pg_isready: could not connect to server` | Container still starting or port conflict on 5432 | Wait 10–15 seconds after `docker compose up`. If persistent, check if another PostgreSQL instance is using port 5432 with `lsof -i :5432`. |
| `out of shared memory` | Too many connections or parallel workers | Add `max_connections=200 shared_buffers=256MB` to the Docker command or a `postgresql.conf` override. |
| `disk full` during ingestion | Exceeded the 8GB allocation | Run TimescaleDB compression manually: `SELECT compress_chunk(c) FROM show_chunks('ohlcv', older_than => INTERVAL '30 days') c;` |

---

## Database 2 — Valkey

**Role:** Session cache (JWT blocklist), feature flags mirror (fast read path), API quota counters
(`INCR` with daily TTL), real-time price cache for dashboard, pub/sub channel for live WebSocket
updates to the web dashboard.

**Why Valkey:** Valkey is a Redis-compatible fork maintained under a BSD license (Redis relicensed
to SSPL in 2024). It is a drop-in replacement for Redis. All Redis client libraries work with
Valkey without modification. The project uses the `valkey` Python package.

### Environment Variables

```bash
VALKEY_HOST=localhost
VALKEY_PORT=6379
VALKEY_PASSWORD=<strong-password>
VALKEY_URL=valkey://:${VALKEY_PASSWORD}@localhost:6379/0
```

### Key Naming Convention

```
sessions:{user_id}:{session_token}         → session data (TTL: 24h)
blocklist:{jti}                            → blocked JWT ID (TTL: token remaining lifetime)
quota:{source_name}:daily                  → INCR counter (TTL: seconds until midnight UTC)
quota:{source_name}:monthly               → INCR counter (TTL: seconds until month end)
price:cache:{symbol}                       → latest price JSON (TTL: 60s)
flag:{flag_name}                           → feature flag value, synced from PostgreSQL
predict:latest:{symbol}:{horizon}          → latest prediction JSON (TTL: 4h)
pubsub:price_updates                       → pub/sub channel for live price feed
pubsub:alert_triggered                     → pub/sub channel for real-time alert delivery
```

### Python Connection

```python
import valkey.asyncio as aioredis

pool = aioredis.ConnectionPool.from_url(
    settings.VALKEY_URL,
    max_connections=20,
    decode_responses=True,
)
redis = aioredis.Valkey(connection_pool=pool)

# Quota increment with TTL (API call tracking)
async def increment_quota(source: str) -> int:
    key = f"quota:{source}:daily"
    pipe = redis.pipeline()
    pipe.incr(key)
    pipe.expire(key, seconds_until_midnight())
    count, _ = await pipe.execute()
    return count
```

### Verification Commands

```bash
# Health check
docker exec marketpulse-valkey valkey-cli -a $VALKEY_PASSWORD ping
# Expected: PONG

# Test INCR with TTL
docker exec marketpulse-valkey valkey-cli -a $VALKEY_PASSWORD \
    SET quota:newsapi:daily 0 EX 86400
docker exec marketpulse-valkey valkey-cli -a $VALKEY_PASSWORD INCR quota:newsapi:daily
# Expected: 1

# Test pub/sub (open two terminals)
# Terminal 1: docker exec -it marketpulse-valkey valkey-cli -a $VALKEY_PASSWORD SUBSCRIBE pubsub:price_updates
# Terminal 2: docker exec -it marketpulse-valkey valkey-cli -a $VALKEY_PASSWORD PUBLISH pubsub:price_updates '{"symbol":"AAPL","price":195.42}'
```

### Error Reference

| Error | Cause | Fix |
|-------|-------|-----|
| `WRONGPASS invalid username-password pair` | Password mismatch | Check VALKEY_PASSWORD in .env matches container startup password |
| `OOM command not allowed` | Memory limit (512MB) hit with `allkeys-lru` eviction not configured | Verify `--maxmemory-policy allkeys-lru` is in the compose command. If already set, increase `--maxmemory` if RAM budget allows. |
| `Connection refused` on port 6379 | Container not running or port conflict | `docker compose ps marketpulse-valkey` to check status; `lsof -i :6379` for conflicts |
| `NOAUTH Authentication required` | Connecting without password in code | Pass `password=` in the connection URL or client constructor |

---

## Database 3 — ChromaDB

**Role:** Vector database for semantic deduplication of news articles (so the same story from
three sources is not processed three times), Reddit post clustering by topic, and prediction
feature embeddings for anomaly detection proximity searches.

**Collections:**
- `news_articles` — embeddings of news headline + summary (384-dim, all-MiniLM-L6-v2 or FinBERT CLS)
- `reddit_posts` — embeddings of post title + body (384-dim)
- `prediction_features` — embeddings of per-ticker feature vectors for anomaly proximity

### Environment Variables

```bash
CHROMA_HOST=localhost
CHROMA_PORT=8000
CHROMA_TOKEN=<token>
CHROMA_URL=http://localhost:8000
```

### Python Setup

```python
import chromadb
from chromadb.config import Settings

client = chromadb.HttpClient(
    host=settings.CHROMA_HOST,
    port=settings.CHROMA_PORT,
    settings=Settings(
        chroma_client_auth_provider="chromadb.auth.token.TokenAuthClientProvider",
        chroma_client_auth_credentials=settings.CHROMA_TOKEN,
    )
)

# Create collections at startup
news_collection = client.get_or_create_collection(
    name="news_articles",
    metadata={"hnsw:space": "cosine"}
)

reddit_collection = client.get_or_create_collection(
    name="reddit_posts",
    metadata={"hnsw:space": "cosine"}
)

feature_collection = client.get_or_create_collection(
    name="prediction_features",
    metadata={"hnsw:space": "euclidean"}
)

# Semantic dedup: is this article already in the collection?
async def is_duplicate_article(embedding: list[float], threshold: float = 0.95) -> bool:
    results = news_collection.query(
        query_embeddings=[embedding],
        n_results=1,
        include=["distances"]
    )
    if results["distances"] and results["distances"][0]:
        similarity = 1 - results["distances"][0][0]  # cosine distance → similarity
        return similarity >= threshold
    return False
```

### Verification Commands

```bash
# Health check
curl http://localhost:8000/api/v1/heartbeat
# Expected: {"nanosecond heartbeat": <timestamp>}

# List collections (after app startup creates them)
curl -H "Authorization: Bearer $CHROMA_TOKEN" \
    http://localhost:8000/api/v1/collections
```

### Error Reference

| Error | Cause | Fix |
|-------|-------|-----|
| `Unauthorized` | Missing or wrong token in request header | Ensure `Authorization: Bearer <token>` header is set; check CHROMA_TOKEN in env |
| `Collection not found` | App tried to query before startup created collections | Call `get_or_create_collection` at app startup (not lazily) |
| Slow query times | Collection is large and HNSW index needs tuning | Set `hnsw:construction_ef=200` and `hnsw:search_ef=100` on the collection metadata for better recall/speed balance |

---

## Database 4 — SurrealDB

**Role:** Multi-model cross-domain queries. Example query: "find all news articles from the last
7 days that are related to tickers in the same sector as AAPL and have a combined FinBERT
sentiment score below -0.5." This query spans the ticker table, the sector relationship, and the
news sentiment scores — a cross-domain join that is natural in SurrealDB's graph+document model
but cumbersome across separate databases.

### Environment Variables

```bash
SURREAL_URL=http://localhost:8001
SURREAL_USER=root
SURREAL_PASSWORD=<password>
SURREAL_NAMESPACE=marketpulse
SURREAL_DATABASE=main
```

### Schema (SurrealQL)

```sql
-- Run via: surreal sql --conn http://localhost:8001 --user root --pass <pass>
--           --ns marketpulse --db main

DEFINE TABLE ticker SCHEMAFULL;
DEFINE FIELD symbol ON ticker TYPE string;
DEFINE FIELD name ON ticker TYPE string;
DEFINE FIELD sector ON ticker TYPE option<string>;
DEFINE FIELD asset_type ON ticker TYPE string;

DEFINE TABLE news_article SCHEMAFULL;
DEFINE FIELD ticker_symbol ON news_article TYPE string;
DEFINE FIELD source ON news_article TYPE string;
DEFINE FIELD headline ON news_article TYPE string;
DEFINE FIELD published_at ON news_article TYPE datetime;
DEFINE FIELD finbert_score ON news_article TYPE float;

DEFINE TABLE in_sector SCHEMAFULL;
DEFINE FIELD in ON in_sector TYPE record<ticker>;
DEFINE FIELD out ON in_sector TYPE string;  -- sector name

-- Example cross-domain query:
-- SELECT * FROM news_article
--     WHERE ticker_symbol IN (
--         SELECT symbol FROM ticker WHERE sector = (
--             SELECT sector FROM ticker WHERE symbol = 'AAPL' LIMIT 1
--         )[0].sector
--     )
--     AND finbert_score < -0.5
--     AND published_at > time::now() - 7d;
```

### Verification Commands

```bash
curl http://localhost:8001/health
# Expected: {"status":"ok"}
```

---

## Database 5 — MinIO

**Role:** Object storage for generated chart images (candlestick charts sent as Discord
attachments), exported reports (PDF, CSV, JSON, XML), trained ML model files, and OHLCV data
archived as Parquet files.

**Buckets:**
- `charts` — Discord/web candlestick chart images (PNG)
- `reports` — user-exported data files
- `models` — trained ML model binaries (LSTM checkpoints, XGBoost/LightGBM models)
- `ohlcv-archive` — Parquet files partitioned by symbol/year/month

### Environment Variables

```bash
MINIO_ROOT_USER=marketpulse
MINIO_ROOT_PASSWORD=<password>
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=${MINIO_ROOT_USER}
MINIO_SECRET_KEY=${MINIO_ROOT_PASSWORD}
MINIO_BUCKET_CHARTS=charts
MINIO_BUCKET_REPORTS=reports
MINIO_BUCKET_MODELS=models
MINIO_BUCKET_OHLCV=ohlcv-archive
```

### Python Setup — Bucket Initialization

```python
from minio import Minio
from minio.error import S3Error

client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=False  # True in production with TLS
)

BUCKETS = ["charts", "reports", "models", "ohlcv-archive"]

async def init_buckets():
    for bucket in BUCKETS:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)

# Upload a chart image
def upload_chart(symbol: str, chart_bytes: bytes) -> str:
    import io, time
    key = f"{symbol}/{int(time.time())}.png"
    client.put_object(
        "charts", key,
        io.BytesIO(chart_bytes), len(chart_bytes),
        content_type="image/png"
    )
    return client.presigned_get_object("charts", key, expires=timedelta(hours=1))
```

### Verification Commands

```bash
# Console UI: http://localhost:9001 (login: MINIO_ROOT_USER / MINIO_ROOT_PASSWORD)

# CLI check
docker exec marketpulse-minio mc alias set local http://localhost:9000 \
    $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD
docker exec marketpulse-minio mc ls local/
```

### Error Reference

| Error | Cause | Fix |
|-------|-------|-----|
| `S3Error: Access Denied` | Wrong credentials or bucket policy | Verify MINIO_ACCESS_KEY/MINIO_SECRET_KEY match the container's MINIO_ROOT_USER/PASSWORD |
| `SignatureDoesNotMatch` | Clock skew between client and MinIO container | Sync system clock: `sudo ntpdate pool.ntp.org` |
| Console not loading at :9001 | Missing `--console-address ":9001"` in command | Ensure the compose `command:` line includes `--console-address ":9001"` |

---

## Database 6 — MongoDB

**Role:** Document store with flexible schema per source. Stores news articles (each source has
different fields), Reddit posts and comment threads (nested document structure), SEC filing
documents (XBRL data has varying structure), earnings call transcripts, and prediction explanation
documents (feature importance breakdowns).

**Collections:**
- `news_articles` — one document per article, schema varies by source
- `reddit_posts` — post document with embedded comment array
- `sec_filings` — Form 4 and 13D/G filings
- `earnings_transcripts` — raw text of earnings call transcripts
- `prediction_explanations` — SHAP values and feature importances per prediction

### Environment Variables

```bash
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_USER=marketpulse
MONGO_PASSWORD=<password>
MONGO_DB=marketpulse
MONGO_URL=mongodb://marketpulse:<password>@localhost:27017/marketpulse?authSource=admin
```

### Index Setup (init/mongo/init.js)

```javascript
// Runs automatically via /docker-entrypoint-initdb.d
db = db.getSiblingDB('marketpulse');

db.news_articles.createIndex({ "symbol": 1, "published_at": -1 });
db.news_articles.createIndex({ "source": 1, "published_at": -1 });
db.news_articles.createIndex({ "published_at": -1 }, { expireAfterSeconds: 7776000 }); // 90 days TTL
db.news_articles.createIndex({ "url": 1 }, { unique: true });

db.reddit_posts.createIndex({ "symbol": 1, "created_utc": -1 });
db.reddit_posts.createIndex({ "subreddit": 1, "created_utc": -1 });
db.reddit_posts.createIndex({ "post_id": 1 }, { unique: true });

db.sec_filings.createIndex({ "symbol": 1, "filed_at": -1 });
db.sec_filings.createIndex({ "filing_type": 1, "symbol": 1 });

db.prediction_explanations.createIndex({ "symbol": 1, "prediction_time": -1 });
```

### Verification Commands

```bash
docker exec marketpulse-mongo mongosh -u marketpulse -p $MONGO_PASSWORD \
    --authenticationDatabase admin marketpulse \
    --eval "db.stats()"

# Expected: shows db name, collections count, storage size
```

### Error Reference

| Error | Cause | Fix |
|-------|-------|-----|
| `Authentication failed` | Wrong credentials or auth database | Use `?authSource=admin` in connection string; root user authenticates against `admin` database |
| `Collection has no documents` after restart | Volume not mounted | Check `- mongo_data:/data/db` is in volumes section |
| Slow queries on news_articles | Missing index on symbol + published_at | Run `db.news_articles.createIndex({"symbol":1,"published_at":-1})` in mongosh |

---

## Database 7 — Elasticsearch

**Role:** Full-text search across all news articles and Reddit posts by ticker, keyword, date
range, or sentiment band. Powers the web dashboard search bar ("find all articles mentioning
'interest rate' for AAPL in the last 30 days") and the Discord `/news` command.

### Environment Variables

```bash
ELASTIC_HOST=localhost
ELASTIC_PORT=9200
ELASTIC_USER=elastic
ELASTIC_PASSWORD=<password>
ELASTIC_URL=http://elastic:<password>@localhost:9200
```

### Index Mapping Setup

```python
import httpx

MAPPINGS = {
    "news_index": {
        "mappings": {
            "properties": {
                "symbol":        {"type": "keyword"},
                "headline":      {"type": "text", "analyzer": "english"},
                "summary":       {"type": "text", "analyzer": "english"},
                "source":        {"type": "keyword"},
                "published_at":  {"type": "date"},
                "finbert_score": {"type": "float"},
                "url":           {"type": "keyword", "index": False}
            }
        },
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,  # Single-node; increase on multi-node
            "index.max_result_window": 50000
        }
    },
    "reddit_index": {
        "mappings": {
            "properties": {
                "symbol":      {"type": "keyword"},
                "subreddit":   {"type": "keyword"},
                "title":       {"type": "text", "analyzer": "english"},
                "body":        {"type": "text", "analyzer": "english"},
                "score":       {"type": "integer"},
                "vader_score": {"type": "float"},
                "created_utc": {"type": "date"},
                "post_id":     {"type": "keyword"}
            }
        },
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0
        }
    }
}

async def init_elasticsearch():
    async with httpx.AsyncClient() as client:
        for index_name, config in MAPPINGS.items():
            resp = await client.put(
                f"{settings.ELASTIC_URL}/{index_name}",
                json=config,
                auth=(settings.ELASTIC_USER, settings.ELASTIC_PASSWORD)
            )
            if resp.status_code not in (200, 400):  # 400 = already exists
                resp.raise_for_status()
```

### Verification Commands

```bash
# Cluster health
curl -u elastic:$ELASTIC_PASSWORD http://localhost:9200/_cluster/health?pretty
# Expected: "status": "green" or "yellow" (yellow is fine on single-node)

# List indices
curl -u elastic:$ELASTIC_PASSWORD http://localhost:9200/_cat/indices?v
```

### Error Reference

| Error | Cause | Fix |
|-------|-------|-----|
| `status: red` | Shard allocation failed | On single-node, expected green/yellow. If red: `GET /_cluster/allocation/explain` |
| `max virtual memory areas vm.max_map_count [65530] too low` | Linux kernel limit | Run `sysctl -w vm.max_map_count=262144` on the host, and add to `/etc/sysctl.conf` for persistence |
| `circuit_breaking_exception` | JVM heap exhausted | Increase `ES_JAVA_OPTS=-Xms1g -Xmx1g` if RAM budget allows; or reduce document size |

---

## Database 8 — InfluxDB

**Role:** Secondary time-series database for high-frequency streaming data where millisecond
write throughput matters: Reddit mention counts per ticker per minute, news publication rate per
ticker per hour, and real-time sentiment stream (VADER scores as posts arrive).

**Buckets:**
- `sentiment_stream` — VADER scores as Reddit posts arrive (TTL: 30 days)
- `mention_counts` — Reddit mention counts per ticker per minute (TTL: 90 days)
- `news_rate` — news publication rate per ticker per hour (TTL: 90 days)

### Environment Variables

```bash
INFLUX_URL=http://localhost:8086
INFLUX_TOKEN=<admin-token>
INFLUX_ORG=marketpulse
INFLUX_BUCKET_SENTIMENT=sentiment_stream
INFLUX_BUCKET_MENTIONS=mention_counts
```

### Python Write Example

```python
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from influxdb_client import Point

async def write_mention_count(symbol: str, subreddit: str, count: int):
    async with InfluxDBClientAsync(
        url=settings.INFLUX_URL,
        token=settings.INFLUX_TOKEN,
        org=settings.INFLUX_ORG
    ) as client:
        write_api = client.write_api()
        point = (
            Point("reddit_mentions")
            .tag("symbol", symbol)
            .tag("subreddit", subreddit)
            .field("count", count)
        )
        await write_api.write(bucket=settings.INFLUX_BUCKET_MENTIONS, record=point)
```

### Verification Commands

```bash
# Ping
curl http://localhost:8086/ping
# Expected: HTTP 204

# List buckets
influx bucket list --token $INFLUX_TOKEN --org marketpulse
```

---

## Databases 9–15 — Embedded Databases

These databases are embedded within the application process. They do not run in containers. They
are accessed directly through Python libraries. Their files are stored in the application's data
directory (`./data/` in development, `/var/lib/marketpulse/` in production).

### Database 9 — SQLite Event Journal

**Role:** Immutable append-only record of every prediction generated, every alert triggered, and
every model training run. Never updated, never deleted. Grows monotonically.

```python
import sqlite3

def init_event_journal(path: str = "data/event_journal.db"):
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type  TEXT NOT NULL,  -- 'prediction', 'alert', 'training_run'
            payload     TEXT NOT NULL,  -- JSON
            created_at  TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type, created_at)")
    conn.commit()
    return conn

# Append-only — never UPDATE or DELETE from this table
def log_event(conn, event_type: str, payload: dict):
    import json
    conn.execute(
        "INSERT INTO events (event_type, payload) VALUES (?, ?)",
        (event_type, json.dumps(payload))
    )
    conn.commit()
```

### Database 10 — SQLite Audit Ledger

**Role:** SHA-256 hash chain for user account changes, quota limit changes, and feature flag
changes. Each row includes the hash of the previous row, making the ledger tamper-evident: if any
row is modified, all subsequent hashes break.

```python
import sqlite3, hashlib, json

def init_audit_ledger(path: str = "data/audit_ledger.db"):
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            action          TEXT NOT NULL,
            actor_id        TEXT,
            target_type     TEXT NOT NULL,
            target_id       TEXT NOT NULL,
            old_value       TEXT,
            new_value       TEXT,
            prev_hash       TEXT NOT NULL,
            row_hash        TEXT NOT NULL,
            created_at      TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    return conn

def append_audit(conn, action: str, actor_id: str, target_type: str,
                 target_id: str, old_value, new_value):
    # Get hash of last row
    cursor = conn.execute("SELECT row_hash FROM audit_log ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    prev_hash = row[0] if row else "genesis"

    payload = json.dumps({
        "action": action, "actor_id": actor_id,
        "target_type": target_type, "target_id": target_id,
        "old_value": old_value, "new_value": new_value,
        "prev_hash": prev_hash
    }, sort_keys=True)
    row_hash = hashlib.sha256(payload.encode()).hexdigest()

    conn.execute("""
        INSERT INTO audit_log
            (action, actor_id, target_type, target_id, old_value, new_value, prev_hash, row_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (action, actor_id, target_type, target_id,
          json.dumps(old_value), json.dumps(new_value), prev_hash, row_hash))
    conn.commit()
```

### Database 11 — SpatiaLite

**Role:** Geographic data for macro-geographic analysis — stock exchange locations, company
headquarters for geographic clustering, and sector geographic concentration analysis.

```python
import sqlite3

def init_spatialite(path: str = "data/spatial.db"):
    conn = sqlite3.connect(path)
    conn.enable_load_extension(True)
    conn.load_extension("mod_spatialite")  # requires: apt-get install spatialite-bin
    conn.execute("SELECT InitSpatialMetaData(1)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS company_hq (
            symbol TEXT PRIMARY KEY,
            name   TEXT,
            city   TEXT,
            country TEXT
        )
    """)
    conn.execute("""
        SELECT AddGeometryColumn('company_hq', 'location', 4326, 'POINT', 'XY')
    """)
    conn.commit()
    return conn
```

### Database 12 — ZODB

**Role:** Object-oriented store for the ticker registry. `StockTicker` and `CryptoTicker` inherit
from `Ticker` with proper Python class hierarchies. Demonstrates OOP persistence without an ORM.

```python
import ZODB, ZODB.FileStorage, transaction
from persistent import Persistent
from persistent.mapping import PersistentMapping

class Ticker(Persistent):
    def __init__(self, symbol: str, name: str):
        self.symbol = symbol
        self.name = name
        self.is_active = True
        self.subreddits: list = []
        self.alert_configs: dict = {}

class StockTicker(Ticker):
    def __init__(self, symbol: str, name: str, exchange: str, sector: str):
        super().__init__(symbol, name)
        self.exchange = exchange
        self.sector = sector
        self.asset_type = "stock"

class CryptoTicker(Ticker):
    def __init__(self, symbol: str, name: str, chain: str):
        super().__init__(symbol, name)
        self.chain = chain  # 'ethereum', 'bitcoin', etc.
        self.asset_type = "crypto"
        self.coingecko_id = None

def open_registry(path: str = "data/ticker_registry.fs"):
    storage = ZODB.FileStorage.FileStorage(path)
    db = ZODB.DB(storage)
    conn = db.open()
    root = conn.root()
    if "tickers" not in root:
        root["tickers"] = PersistentMapping()
        transaction.commit()
    return db, conn, root

def add_ticker(root, ticker: Ticker):
    root["tickers"][ticker.symbol] = ticker
    transaction.commit()
```

### Database 13 — DuckDB In-Memory

**Role:** Live dashboard aggregations. Runs as an in-memory database inside the FastAPI process.
Queries Parquet files from MinIO and data materialized from PostgreSQL for ad-hoc aggregation
without touching the primary databases. Supports the dashboard's "current summary" panel.

```python
import duckdb

# In-memory connection — dies with the process, which is intentional
conn = duckdb.connect(database=":memory:")

def get_daily_prediction_summary():
    return conn.execute("""
        SELECT
            direction,
            COUNT(*) as count,
            AVG(confidence) as avg_confidence
        FROM read_parquet('s3://ohlcv-archive/predictions/*.parquet')
        WHERE DATE(prediction_time) = CURRENT_DATE
        GROUP BY direction
        ORDER BY count DESC
    """).fetchdf()
```

### Database 14 — DuckDB Persistent

**Role:** OLAP analytics over Parquet archives stored in MinIO. Long-term prediction accuracy
trends, historical sentiment vs. price correlation, sector rotation analysis. Persists between
restarts, updated nightly when new Parquet files are written.

```python
conn = duckdb.connect(database="data/analytics.duckdb")

# Register MinIO as an S3 source
conn.execute("""
    INSTALL httpfs;
    LOAD httpfs;
    SET s3_endpoint='localhost:9000';
    SET s3_access_key_id='marketpulse';
    SET s3_secret_access_key='<password>';
    SET s3_use_ssl=false;
    SET s3_url_style='path';
""")
```

### Database 15 — NetworkX → SQLite

**Role:** Correlation graph between tickers. Edges represent a historical correlation coefficient
above a threshold (e.g., |r| > 0.7 over 90 days). Edges are weighted by correlation strength.
Graph is persisted to SQLite for restart persistence and re-loaded into memory as a NetworkX
object at startup.

```python
import networkx as nx
import sqlite3, json

def save_graph(G: nx.Graph, path: str = "data/correlation_graph.db"):
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS edges (
            symbol_a TEXT, symbol_b TEXT, correlation REAL,
            window_days INT, updated_at TEXT,
            PRIMARY KEY (symbol_a, symbol_b)
        )
    """)
    for u, v, data in G.edges(data=True):
        conn.execute("""
            INSERT OR REPLACE INTO edges VALUES (?, ?, ?, ?, datetime('now'))
        """, (u, v, data.get("correlation", 0.0), data.get("window_days", 90)))
    conn.commit()

def load_graph(path: str = "data/correlation_graph.db") -> nx.Graph:
    G = nx.Graph()
    conn = sqlite3.connect(path)
    for row in conn.execute("SELECT symbol_a, symbol_b, correlation FROM edges"):
        G.add_edge(row[0], row[1], correlation=row[2])
    return G
```

---

## Database 16 — DataStax Astra (Cassandra)

**Role:** High-throughput write stream for API call logs and ingestion event records. Every call
to every external API is logged here with timestamp, source, endpoint, response code, latency,
and quota impact. Cassandra's wide-column model excels at append-heavy, time-ordered writes.

### Cloud Setup Steps

1. Go to [astra.datastax.com](https://astra.datastax.com) and create a free account.
2. Create a new database: name `marketpulse`, keyspace `ingestion`, cloud provider AWS/GCP/Azure
   (pick the closest region to your node).
3. Download the Secure Connect Bundle (SCB zip file) — this is the mTLS certificate bundle for
   your cluster.
4. Create an Application Token with "Database Administrator" role.
5. Store the SCB zip in `./secrets/astra-secure-connect-bundle.zip`.

### Environment Variables

```bash
ASTRA_DB_CLIENT_ID=<from token>
ASTRA_DB_CLIENT_SECRET=<from token>
ASTRA_DB_TOKEN=AstraCS:<token>
ASTRA_SECURE_BUNDLE_PATH=./secrets/astra-secure-connect-bundle.zip
ASTRA_KEYSPACE=ingestion
```

### Schema (CQL)

```cql
-- Run in Astra CQL console
CREATE KEYSPACE IF NOT EXISTS ingestion
    WITH replication = {'class': 'NetworkTopologyStrategy', 'replication_factor': 1};

USE ingestion;

CREATE TABLE IF NOT EXISTS api_call_log (
    source_name  TEXT,
    call_date    DATE,
    call_time    TIMESTAMP,
    endpoint     TEXT,
    status_code  INT,
    latency_ms   INT,
    quota_impact INT,
    PRIMARY KEY ((source_name, call_date), call_time)
) WITH CLUSTERING ORDER BY (call_time DESC)
  AND default_time_to_live = 7776000;  -- 90 days TTL

CREATE TABLE IF NOT EXISTS ingestion_events (
    event_type   TEXT,
    event_date   DATE,
    event_time   TIMESTAMP,
    symbol       TEXT,
    source       TEXT,
    record_count INT,
    duration_ms  INT,
    PRIMARY KEY ((event_type, event_date), event_time)
) WITH CLUSTERING ORDER BY (event_time DESC)
  AND default_time_to_live = 2592000;  -- 30 days TTL
```

### Keep-Alive Requirement

DataStax Astra Free tier databases are hibernated after 23 hours of inactivity. The ingestion
pipeline's constant writes prevent hibernation during normal operation. If MarketPulse is paused
for more than 23 hours (e.g., during Proxmox maintenance), resume by hitting the Astra UI or
sending a keep-alive write before starting ingestion workers.

### Verification

```python
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra import OperationTimedOut

cloud_config = {'secure_connect_bundle': settings.ASTRA_SECURE_BUNDLE_PATH}
auth_provider = PlainTextAuthProvider(
    settings.ASTRA_DB_CLIENT_ID,
    settings.ASTRA_DB_CLIENT_SECRET
)
cluster = Cluster(cloud=cloud_config, auth_provider=auth_provider)
session = cluster.connect(settings.ASTRA_KEYSPACE)
rows = session.execute("SELECT release_version FROM system.local")
print(f"Cassandra version: {rows.one().release_version}")
```

---

## Database 17 — Neo4j AuraDB Free

**Role:** Ticker relationship graph. Nodes are tickers, companies, sectors, and indices. Edges
represent relationships: `SUPPLIER_OF`, `CUSTOMER_OF`, `MEMBER_OF` (sector/index/ETF),
`CORRELATED_WITH`. Powers the "correlation graph explorer" in the web dashboard and the
`/compare` command in the Discord bot.

### Cloud Setup Steps

1. Go to [console.neo4j.io](https://console.neo4j.io) and create a free account.
2. Create a new AuraDB Free instance. Save the connection credentials shown immediately — the
   password is shown only once.
3. The free tier gives you one instance: 200K nodes, 400K relationships, 1 database.

### Environment Variables

```bash
NEO4J_URI=neo4j+s://<your-instance>.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=<password-from-creation>
```

### Schema and Seed Queries

```cypher
// Create constraints
CREATE CONSTRAINT ticker_symbol IF NOT EXISTS
    FOR (t:Ticker) REQUIRE t.symbol IS UNIQUE;
CREATE CONSTRAINT sector_name IF NOT EXISTS
    FOR (s:Sector) REQUIRE s.name IS UNIQUE;

// Create sample nodes
MERGE (aapl:Ticker {symbol: "AAPL", name: "Apple Inc.", asset_type: "stock"})
MERGE (tech:Sector {name: "Technology"})
MERGE (spy:Ticker {symbol: "SPY", name: "SPDR S&P 500 ETF", asset_type: "etf"})

// Create relationships
MERGE (aapl)-[:MEMBER_OF]->(tech)
MERGE (aapl)-[:MEMBER_OF]->(spy)

// Query: find all tickers in the same sector as AAPL
MATCH (t:Ticker)-[:MEMBER_OF]->(s:Sector)<-[:MEMBER_OF]-(peer:Ticker)
WHERE t.symbol = 'AAPL'
RETURN peer.symbol, peer.name
```

### Keep-Alive Requirement

Neo4j AuraDB Free instances are paused after 3 days of inactivity. MarketPulse's daily graph
updates prevent this during normal operation. If paused, resume from the AuraDB console.

### Verification

```python
from neo4j import AsyncGraphDatabase

driver = AsyncGraphDatabase.driver(
    settings.NEO4J_URI,
    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
)
async with driver.session() as session:
    result = await session.run("RETURN 1 AS n")
    record = await result.single()
    assert record["n"] == 1
    print("Neo4j AuraDB: connected")
```

---

## Health Check Script

Run this script to verify all 17 databases are reachable before starting the application.

```python
#!/usr/bin/env python3
"""
marketpulse_healthcheck.py
Run: python marketpulse_healthcheck.py
Expected: all checks PASS
"""

import asyncio
import asyncpg
import valkey.asyncio as aioredis
import httpx
import pymongo
from influxdb_client import InfluxDBClient
from minio import Minio
import sqlite3
import duckdb
import ZODB, ZODB.FileStorage
import os

results = []

def check(name, fn):
    try:
        result = fn()
        results.append((name, "PASS", None))
    except Exception as e:
        results.append((name, "FAIL", str(e)))

async def async_check(name, coro):
    try:
        await coro
        results.append((name, "PASS", None))
    except Exception as e:
        results.append((name, "FAIL", str(e)))

async def main():
    # PostgreSQL + TimescaleDB
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    version = await conn.fetchval("SELECT extversion FROM pg_extension WHERE extname='timescaledb'")
    assert version, "TimescaleDB extension not found"
    await conn.close()
    results.append(("PostgreSQL + TimescaleDB", "PASS", None))

    # Valkey
    r = aioredis.from_url(os.environ["VALKEY_URL"])
    assert await r.ping()
    results.append(("Valkey", "PASS", None))

    # ChromaDB
    async with httpx.AsyncClient() as client:
        resp = await client.get("http://localhost:8000/api/v1/heartbeat")
        assert resp.status_code == 200
    results.append(("ChromaDB", "PASS", None))

    # SurrealDB
    async with httpx.AsyncClient() as client:
        resp = await client.get("http://localhost:8001/health")
        assert resp.status_code == 200
    results.append(("SurrealDB", "PASS", None))

    # MinIO
    minio_client = Minio("localhost:9000",
        access_key=os.environ["MINIO_ROOT_USER"],
        secret_key=os.environ["MINIO_ROOT_PASSWORD"],
        secure=False)
    minio_client.list_buckets()  # raises on auth failure
    results.append(("MinIO", "PASS", None))

    # MongoDB
    client = pymongo.MongoClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=3000)
    client.admin.command("ping")
    results.append(("MongoDB", "PASS", None))

    # Elasticsearch
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "http://localhost:9200/_cluster/health",
            auth=(os.environ["ELASTIC_USER"], os.environ["ELASTIC_PASSWORD"])
        )
        assert resp.json()["status"] in ("green", "yellow")
    results.append(("Elasticsearch", "PASS", None))

    # InfluxDB
    influx = InfluxDBClient(url="http://localhost:8086", token=os.environ["INFLUX_TOKEN"])
    influx.ping()
    results.append(("InfluxDB", "PASS", None))

    # Embedded: SQLite
    conn = sqlite3.connect("data/event_journal.db")
    conn.execute("SELECT 1")
    results.append(("SQLite Event Journal", "PASS", None))

    # Embedded: DuckDB
    duck = duckdb.connect(":memory:")
    duck.execute("SELECT 42").fetchone()
    results.append(("DuckDB", "PASS", None))

    # Embedded: ZODB
    storage = ZODB.FileStorage.FileStorage("data/ticker_registry.fs")
    db = ZODB.DB(storage)
    db.close()
    results.append(("ZODB", "PASS", None))

    # Print results
    print("\n" + "="*60)
    print("MarketPulse Database Health Check")
    print("="*60)
    for name, status, error in results:
        icon = "✓" if status == "PASS" else "✗"
        print(f"  {icon}  {name:<35} {status}")
        if error:
            print(f"         Error: {error}")
    print("="*60)
    fails = [r for r in results if r[1] == "FAIL"]
    print(f"\n  {len(results) - len(fails)}/{len(results)} checks passed")
    if fails:
        print(f"  {len(fails)} database(s) failed — fix before starting the application")
        raise SystemExit(1)

asyncio.run(main())
```

---

## Port Reference Table

| Port | Service | Protocol | Notes |
|------|---------|---------|-------|
| 5432 | PostgreSQL | TCP | Primary relational + time-series |
| 6379 | Valkey | TCP | Requires password auth |
| 8000 | ChromaDB | HTTP | Bearer token auth |
| 8001 | SurrealDB | HTTP/WS | Maps to internal 8000 |
| 8086 | InfluxDB | HTTP | Admin token auth |
| 8181 | OPA | HTTP | No auth in dev; add in prod |
| 9000 | MinIO S3 API | HTTP | S3-compatible |
| 9001 | MinIO Console | HTTP | Web UI |
| 9090 | Prometheus | HTTP | Metrics scrape target |
| 9200 | Elasticsearch | HTTP | Basic auth |
| 16686 | Jaeger UI | HTTP | Trace viewer |
| 3000 | Grafana | HTTP | Dashboard UI |
| 3100 | Loki | HTTP | Log aggregation |
| 4317 | Jaeger OTLP gRPC | gRPC | Trace ingest |
| 4318 | Jaeger OTLP HTTP | HTTP | Trace ingest |
| 27017 | MongoDB | TCP | Auth required |
| 50051 | ML gRPC sidecar | gRPC | Internal only — not exposed externally |
| 8080 | FastAPI backend | HTTP | Main application API |
| 5173 | Vite dev server | HTTP | Local dev only |

---

## .env Template

```bash
# .env — copy to .env.local for local dev, never commit this file

# PostgreSQL
POSTGRES_USER=marketpulse
POSTGRES_PASSWORD=CHANGE_ME_postgres
POSTGRES_DB=marketpulse
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
DATABASE_URL=postgresql+asyncpg://marketpulse:CHANGE_ME_postgres@localhost:5432/marketpulse

# Valkey
VALKEY_PASSWORD=CHANGE_ME_valkey
VALKEY_URL=valkey://:CHANGE_ME_valkey@localhost:6379/0

# ChromaDB
CHROMA_TOKEN=CHANGE_ME_chroma

# SurrealDB
SURREAL_USER=root
SURREAL_PASSWORD=CHANGE_ME_surreal

# MinIO
MINIO_ROOT_USER=marketpulse
MINIO_ROOT_PASSWORD=CHANGE_ME_minio
MINIO_ENDPOINT=localhost:9000

# MongoDB
MONGO_USER=marketpulse
MONGO_PASSWORD=CHANGE_ME_mongo
MONGO_URL=mongodb://marketpulse:CHANGE_ME_mongo@localhost:27017/marketpulse?authSource=admin

# Elasticsearch
ELASTIC_PASSWORD=CHANGE_ME_elastic
ELASTIC_USER=elastic

# InfluxDB
INFLUX_USER=marketpulse
INFLUX_PASSWORD=CHANGE_ME_influx
INFLUX_TOKEN=CHANGE_ME_influx_token
INFLUX_ORG=marketpulse

# Grafana
GRAFANA_USER=admin
GRAFANA_PASSWORD=CHANGE_ME_grafana

# DataStax Astra
ASTRA_DB_CLIENT_ID=
ASTRA_DB_CLIENT_SECRET=
ASTRA_DB_TOKEN=
ASTRA_SECURE_BUNDLE_PATH=./secrets/astra-secure-connect-bundle.zip
ASTRA_KEYSPACE=ingestion

# Neo4j AuraDB
NEO4J_URI=
NEO4J_USER=neo4j
NEO4J_PASSWORD=

# API Keys
ALPHA_VANTAGE_KEY=
POLYGON_API_KEY=
COINGECKO_API_KEY=
COINMARKETCAP_KEY=
NEWSAPI_KEY=
GNEWS_KEY=
FINNHUB_KEY=
GLASSNODE_KEY=
ETHERSCAN_KEY=
FRED_API_KEY=
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=MarketPulse/1.0 by <your-reddit-username>

# Notifications
ONESIGNAL_APP_ID=
ONESIGNAL_REST_API_KEY=
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=

# Email
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=

# Discord
DISCORD_BOT_TOKEN=
DISCORD_GUILD_ID=

# Secrets and security
JWT_SECRET_KEY=CHANGE_ME_jwt_secret_minimum_32_chars
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# HashiCorp Vault (Phase 21)
VAULT_ADDR=http://localhost:8200
VAULT_TOKEN=

# App settings
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8080
LOG_LEVEL=INFO
FLAT_BAND_PERCENT=1.0    # ±1% = FLAT threshold
```
