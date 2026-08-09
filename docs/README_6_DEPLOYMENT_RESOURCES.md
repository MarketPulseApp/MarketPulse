# MarketPulse — Deployment Resources

> This document answers one question: "What runs where, and how much does it cost?"
> Use it when provisioning nodes, debugging resource exhaustion, or planning storage growth.

---

## Contents

1. [Hardware Inventory](#1-hardware-inventory)
2. [Storage Budget](#2-storage-budget)
3. [Local Development Allocation (Main Rig)](#3-local-development-allocation-main-rig)
4. [Node 1 — Infrastructure and Data Layer](#4-node-1--infrastructure-and-data-layer)
5. [Node 2 — Application Layer](#5-node-2--application-layer)
6. [Node 3 — ML and Analytics](#6-node-3--ml-and-analytics)
7. [Cloud Services](#7-cloud-services)
8. [Network Architecture](#8-network-architecture)
9. [Storage Growth Projections](#9-storage-growth-projections)
10. [Migration Thresholds](#10-migration-thresholds)
11. [Environment Variable Reference](#11-environment-variable-reference)
12. [One-Command Startup per Node](#12-one-command-startup-per-node)
13. [Shutdown Sequence](#13-shutdown-sequence)
14. [Port Reference](#14-port-reference)

---

## 1. Hardware Inventory

| Node | Role | CPU | RAM | Storage Free | OS |
|------|------|-----|-----|-------------|-----|
| **Main rig** | Dev workstation + self-hosting | i7-9700K (8c/8t @ 3.6 GHz) | 32 GB DDR4 | 95.5 GB | Windows 11 / WSL2 |
| **Proxmox Node 1** | Infrastructure + data layer | To be specified per VM | ~14 GB total | ~120 GB | Proxmox VE 8 |
| **Proxmox Node 2** | Application layer | To be specified per VM | ~14 GB total | ~120 GB | Proxmox VE 8 |
| **Proxmox Node 3** | ML sidecar + analytics | To be specified per VM | ~14 GB total | ~120 GB | Proxmox VE 8 |

**GPU:** RTX 3070 (8 GB VRAM) on the main rig — available for local LSTM training if needed.
The Proxmox nodes do not have GPUs; ML inference uses CPU-based ONNX Runtime on Node 3.

---

## 2. Storage Budget

Total storage constraint: **95.5 GB free** on the main rig.
In production (Proxmox), each node has ~120 GB free; total cluster ~360 GB free.

### Main Rig Storage (Development)

| Component | Allocated GB | Notes |
|-----------|-------------|-------|
| Python venv + packages | 2.5 GB | ML libraries are large |
| Node modules (web + mobile) | 1.5 GB | node_modules are notorious |
| Docker images (all services) | 18 GB | Most ML images are 2–4 GB each |
| Docker volumes (DB data) | 22 GB | See per-database breakdown below |
| MinIO object storage | 8 GB | Charts, model files, Parquet archives |
| Embedded databases (data/) | 2 GB | SQLite, ZODB, DuckDB |
| ML model files (local copy) | 3 GB | ~120 MB per ticker × 25 tickers |
| Test data and fixtures | 1 GB | |
| **Total allocated** | **58 GB** | |
| **Buffer remaining** | **37.5 GB** | Above safety margin |

### Per-Database Storage (Development Docker Volumes)

| Database | Volume Name | Allocated | Growth Rate |
|----------|------------|-----------|-------------|
| PostgreSQL + TimescaleDB | pg_data | 5 GB | ~200 MB/month |
| Valkey | valkey_data | 0.5 GB | Bounded (TTL eviction) |
| ChromaDB | chroma_data | 2 GB | ~100 MB/month (news embeddings) |
| SurrealDB | surreal_data | 0.5 GB | ~20 MB/month |
| MinIO | minio_data | 8 GB | ~500 MB/month |
| MongoDB | mongo_data | 3 GB | ~300 MB/month (news articles) |
| Elasticsearch | elastic_data | 4 GB | ~200 MB/month (news index) |
| InfluxDB | influx_data | 1 GB | ~100 MB/month |
| Prometheus | prometheus_data | 2 GB | ~50 MB/month (15-day retention) |
| Grafana | grafana_data | 0.2 GB | Nearly flat |
| Loki | loki_data | 1 GB | ~100 MB/month (7-day retention) |
| **Total** | | **27.2 GB** | **~1.77 GB/month** |

---

## 3. Local Development Allocation (Main Rig)

This is the layout for running MarketPulse locally during development.
All services run in Docker Compose. The main rig has 32 GB RAM.

| Service | Container | RAM Limit | RAM Typical | RAM Peak | Port(s) |
|---------|-----------|-----------|-------------|----------|---------|
| PostgreSQL + TimescaleDB | marketpulse-postgres | 1.5 GB | 400 MB | 1.2 GB | 5432 |
| Valkey | marketpulse-valkey | 512 MB | 150 MB | 400 MB | 6379 |
| ChromaDB | marketpulse-chroma | 1 GB | 300 MB | 800 MB | 8000 |
| SurrealDB | marketpulse-surreal | 512 MB | 200 MB | 400 MB | 8001 |
| MinIO | marketpulse-minio | 512 MB | 200 MB | 400 MB | 9000, 9001 |
| MongoDB | marketpulse-mongo | 1 GB | 400 MB | 800 MB | 27017 |
| Elasticsearch | marketpulse-elastic | 2 GB | 1.2 GB | 2 GB | 9200, 9300 |
| InfluxDB | marketpulse-influx | 512 MB | 200 MB | 400 MB | 8086 |
| OPA | marketpulse-opa | 256 MB | 80 MB | 200 MB | 8181 |
| Prometheus | marketpulse-prometheus | 512 MB | 300 MB | 500 MB | 9090 |
| Grafana | marketpulse-grafana | 256 MB | 120 MB | 250 MB | 3000 |
| Loki | marketpulse-loki | 512 MB | 200 MB | 400 MB | 3100 |
| Jaeger | marketpulse-jaeger | 512 MB | 150 MB | 400 MB | 16686, 14268 |
| FastAPI backend (uvicorn) | (native, not Docker) | — | 300 MB | 600 MB | 8080 |
| ARQ worker | (native, not Docker) | — | 200 MB | 500 MB | — |
| ML sidecar (gRPC) | (native, not Docker) | — | 1.5 GB | 3 GB | 50051 |
| Discord bot | (native, not Docker) | — | 150 MB | 300 MB | — |
| React + Vite dev server | (native, not Docker) | — | 400 MB | 800 MB | 5173 |
| **Total (all services)** | | | **~6.5 GB** | **~13 GB** | |

**Remaining headroom:** 32 GB - 13 GB peak = **19 GB** for OS + browser + IDE.
The ML sidecar is the biggest single consumer. For development, you may run it only when testing
predictions; all other phases do not require it.

---

## 4. Node 1 — Infrastructure and Data Layer

**Role:** Databases that require high reliability and persistence. This node is the most
important — it holds all time-series data, the event bus, the object store, and the document store.

**Proxmox VM spec (recommended):** 6 vCPU, 12 GB RAM, 110 GB storage (LVM thin-pool).
Keep 2 GB RAM and 10 GB storage as headroom.

| Service | Container Name | RAM Allocated | RAM at Peak | Storage | Port(s) | Restart Policy |
|---------|---------------|---------------|-------------|---------|---------|----------------|
| PostgreSQL + TimescaleDB | mp-pg | 3 GB | 2.5 GB | 30 GB (volume) | 5432 | always |
| Valkey | mp-valkey | 1 GB | 800 MB | 2 GB (RDB snapshots) | 6379 | always |
| MinIO | mp-minio | 1 GB | 800 MB | 40 GB (object data) | 9000, 9001 | always |
| MongoDB | mp-mongo | 2 GB | 1.5 GB | 15 GB (oplog + data) | 27017 | always |
| InfluxDB | mp-influx | 1 GB | 800 MB | 8 GB (time-series) | 8086 | always |
| Prometheus | mp-prometheus | 512 MB | 400 MB | 5 GB (15-day retention) | 9090 | always |
| Loki | mp-loki | 512 MB | 400 MB | 5 GB (7-day retention) | 3100 | always |
| **Total allocated** | | **9 GB** | **7.2 GB** | **105 GB** | | |
| **Headroom** | | **3 GB** | | **5 GB** | | |

**Valkey persistence config (production):**
```
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec
maxmemory 800mb
maxmemory-policy allkeys-lru
```

**PostgreSQL production tuning (`postgresql.conf`):**
```
shared_buffers = 768MB          # 25% of 3 GB allocated
effective_cache_size = 2GB
work_mem = 32MB
maintenance_work_mem = 256MB
wal_buffers = 16MB
checkpoint_completion_target = 0.9
max_connections = 100
```

**Backup schedule (Node 1):**
- PostgreSQL: `pg_dump` nightly at 02:00 UTC, stored in MinIO `backups` bucket
- MongoDB: `mongodump` nightly at 02:30 UTC, stored in MinIO `backups` bucket
- MinIO: data is the source of truth; replicated to S3 via `mc mirror` weekly
- Valkey: RDB snapshots every 5 minutes; AOF fsync every second

---

## 5. Node 2 — Application Layer

**Role:** The FastAPI backend, ARQ workers, Discord bot, OPA, and observability dashboards.
This node is the "brain" — it processes all requests and coordinates between the data layer
and the ML layer.

**Proxmox VM spec (recommended):** 6 vCPU, 10 GB RAM, 40 GB storage.

| Service | Container Name | RAM Allocated | RAM at Peak | Storage | Port(s) | Restart Policy |
|---------|---------------|---------------|-------------|---------|---------|----------------|
| FastAPI backend (uvicorn, 4 workers) | mp-api | 1.5 GB | 1.2 GB | 2 GB (app code) | 8080 | always |
| ARQ worker (ingestion) | mp-arq-ingest | 1 GB | 800 MB | — | — | always |
| ARQ worker (predictions) | mp-arq-predict | 512 MB | 400 MB | — | — | always |
| ARQ worker (notifications) | mp-arq-notify | 512 MB | 400 MB | — | — | always |
| Discord bot | mp-discord | 512 MB | 400 MB | — | — | always |
| OPA | mp-opa | 256 MB | 200 MB | 1 GB (policy bundle) | 8181 | always |
| Grafana | mp-grafana | 512 MB | 400 MB | 2 GB (dashboards) | 3000 | always |
| Jaeger | mp-jaeger | 512 MB | 400 MB | 5 GB (14-day traces) | 16686 | always |
| Cloudflare Tunnel (cloudflared) | mp-tunnel | 128 MB | 100 MB | — | — | always |
| Nginx reverse proxy | mp-nginx | 128 MB | 100 MB | — | 80, 443 | always |
| Voice fulfillment server | mp-voice | 256 MB | 200 MB | — | 8082 | always |
| **Total allocated** | | **5.8 GB** | **4.6 GB** | **~10 GB** | | |
| **Headroom** | | **4.2 GB** | | **30 GB** | | |

**FastAPI production command:**
```bash
uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8080 \
    --workers 4 \
    --loop uvloop \
    --log-level warning
```

**Nginx config (Node 2 — /etc/nginx/conf.d/marketpulse.conf):**
```nginx
upstream fastapi {
    server 127.0.0.1:8080;
    keepalive 32;
}

server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://fastapi;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;
    }

    location /ws {
        proxy_pass http://fastapi;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
    }
}
```

**ARQ worker startup (one command per worker type):**
```bash
# Ingestion worker
arq app.workers.ingestion.WorkerSettings

# Prediction orchestration worker
arq app.workers.predictions.WorkerSettings

# Notification delivery worker
arq app.workers.notifications.WorkerSettings
```

---

## 6. Node 3 — ML and Analytics

**Role:** The ML gRPC sidecar (inference), the analytics query engine (DuckDB), ChromaDB,
SurrealDB, and Elasticsearch. This node handles the heaviest CPU workloads.

**Proxmox VM spec (recommended):** 6 vCPU, 12 GB RAM, 60 GB storage.
All ML inference is CPU-based (ONNX Runtime). No GPU required on this node.

| Service | Container Name | RAM Allocated | RAM at Peak | Storage | Port(s) | Restart Policy |
|---------|---------------|---------------|-------------|---------|---------|----------------|
| ML sidecar (gRPC server) | mp-ml | 4 GB | 3.5 GB | 15 GB (model files) | 50051 | always |
| ChromaDB | mp-chroma | 2 GB | 1.5 GB | 10 GB (embeddings) | 8000 | always |
| SurrealDB | mp-surreal | 1 GB | 800 MB | 5 GB | 8001 | always |
| Elasticsearch | mp-elastic | 4 GB | 3.5 GB | 20 GB (inverted index) | 9200 | always |
| DuckDB analytics (sidecar) | mp-duckdb | 512 MB | 400 MB | 5 GB (persistent DB) | — | always |
| **Total allocated** | | **11.5 GB** | **9.7 GB** | **55 GB** | | |
| **Headroom** | | **0.5 GB** | | **5 GB** | | |

> **Node 3 is RAM-tight.** The 4 GB ML sidecar + 4 GB Elasticsearch together consume 8 GB.
> If you observe OOM kills, reduce Elasticsearch heap to 3 GB: set `ES_JAVA_OPTS="-Xms1g -Xmx3g"`.
> The ML sidecar loads all 25 ticker models into RAM at startup; if this exceeds 4 GB, switch
> to lazy loading (load model on first request, LRU cache of 5 models).

**ML sidecar startup:**
```bash
python ml_sidecar/server.py \
    --port 50051 \
    --model-dir /data/models \
    --lazy-load \
    --model-cache-size 10
```

**Elasticsearch production settings (`/etc/elasticsearch/jvm.options.d/heap.options`):**
```
-Xms2g
-Xmx4g
```

**DuckDB analytics — querying Parquet from MinIO:**
```python
import duckdb
conn = duckdb.connect("/data/analytics.duckdb")
conn.execute("""
    INSTALL httpfs;
    LOAD httpfs;
    SET s3_endpoint='node1.local:9000';
    SET s3_access_key_id='minioadmin';
    SET s3_secret_access_key='minioadmin';
    SET s3_use_ssl=false;
    SET s3_url_style='path';
""")
# Now you can query Parquet files stored in MinIO
result = conn.execute("""
    SELECT symbol, DATE_TRUNC('month', time) as month,
           AVG(close) as avg_close, SUM(volume) as total_volume
    FROM read_parquet('s3://ohlcv-archive/AAPL/*.parquet')
    WHERE time >= CURRENT_DATE - INTERVAL '1 year'
    GROUP BY symbol, month
    ORDER BY month DESC
""").fetchdf()
```

---

## 7. Cloud Services

These are the free-tier cloud databases and services MarketPulse depends on.
All require keep-alive pings to avoid free-tier shutdown.

| Service | Purpose | Free Tier Limits | Keep-Alive Requirement | Keep-Alive Schedule |
|---------|---------|-----------------|----------------------|---------------------|
| DataStax Astra (Cassandra) | API call logs, ingestion event log | 5 GB storage, 40M ops/month | Activity within 30 days or DB paused | Nightly `ALLOW FILTERING` read at 03:00 UTC |
| Neo4j AuraDB Free | Ticker relationship graph, insider transaction graph | 200K nodes, 400K relationships, 200MB | Activity within 30 days or DB paused | Nightly relationship count query at 03:05 UTC |
| OneSignal | Web push + mobile push | 10K subscribers, unlimited notifications | No keep-alive needed | — |
| Twilio (optional) | SMS alerts | $15.50 trial credit | Replenish credit manually | — |
| NewsAPI | News headlines | 100 req/day free tier | No keep-alive needed | — |
| GNews | News articles | 100 req/day free tier | No keep-alive needed | — |
| Finnhub | News + company data | 60 calls/min free tier | No keep-alive needed | — |
| CoinGecko | Crypto OHLCV | 10K calls/month free tier | No keep-alive needed | — |
| Polygon.io | Real-time stock quotes | 5 calls/min, EOD data free tier | No keep-alive needed | — |
| FRED (St. Louis Fed) | Macro economic indicators | Unlimited free | No keep-alive needed | — |
| SEC EDGAR | Insider trading filings | Unlimited free (10 req/sec limit) | No keep-alive needed | — |

**Keep-alive ARQ task (runs nightly at 03:00 UTC):**
```python
# app/workers/keepalive.py
from arq import cron
from app.db.astra.api_call_log import APICallLogRepository
from app.db.neo4j.ticker_graph import TickerGraphRepository

async def keep_astra_alive(ctx):
    repo = APICallLogRepository()
    count = await repo.get_count_today()
    logger.info("astra_keepalive", count=count)

async def keep_neo4j_alive(ctx):
    repo = TickerGraphRepository()
    count = await repo.get_ticker_count()
    logger.info("neo4j_keepalive", ticker_count=count)

class WorkerSettings:
    cron_jobs = [
        cron(keep_astra_alive, hour=3, minute=0),
        cron(keep_neo4j_alive, hour=3, minute=5),
    ]
```

---

## 8. Network Architecture

```
╔══════════════════════════════════════════════════════════════════════════╗
║                        INTERNET / EXTERNAL                               ║
║                                                                          ║
║   Browser         Mobile App         Discord         Alexa / Google      ║
║   (HTTPS)         (HTTPS)            (webhooks)      (webhook)           ║
╚═══════════════════════════╦══════════════════════════════════════════════╝
                             │  All external traffic
                             ▼
╔════════════════════════════════════════════════════════════════════════╗
║                    CLOUDFLARE EDGE (cloudflare.com)                     ║
║                                                                         ║
║   DDoS protection + CDN + TLS termination + WAF rules                  ║
║   Domain: marketpulse.yourdomain.com → Tunnel                          ║
╚══════════════════════════╦═════════════════════════════════════════════╝
                            │  Tunnel (TCP, encrypted)
                            ▼
╔════════════════════════════════════════════════════════════════════════╗
║                         NODE 2 (Application)                            ║
║                                                                         ║
║   cloudflared ──→ Nginx ──→ FastAPI (port 8080)                        ║
║                                │                                        ║
║                    ┌───────────┼───────────────┐                        ║
║                    ▼           ▼               ▼                        ║
║               WebSocket   REST API        Voice (8082)                  ║
║                                │                                        ║
║   Discord Bot ←───────────────  ←── OPA (8181)                         ║
║   ARQ Workers ─────────────────────────────────                         ║
╚═══════════════╦══════════════════╦═════════════╦══════════════════════╝
                │                  │              │
      ┌─────────▼──────┐  ┌────────▼──────┐ ┌───▼───────────┐
      │   NODE 1       │  │   NODE 3      │ │  CLOUD TIER   │
      │  (Data Layer)  │  │  (ML + Search)│ │               │
      │                │  │               │ │ DataStax Astra│
      │ PostgreSQL 5432│  │ ML sidecar    │ │ (Cassandra)   │
      │ Valkey     6379│  │ gRPC  50051   │ │               │
      │ MinIO      9000│  │               │ │ Neo4j AuraDB  │
      │ MongoDB   27017│  │ ChromaDB 8000 │ │ (graph DB)    │
      │ InfluxDB  8086 │  │ SurrealDB8001 │ │               │
      │ Prometheus9090 │  │ Elastic  9200 │ └───────────────┘
      │ Loki       3100│  │ DuckDB  (IPC) │
      └────────────────┘  └───────────────┘
                │                  │
                └────────┬─────────┘
                         │  Internal network (Proxmox VLAN)
                         │  All inter-node traffic on 10.0.0.0/24
                         │  Node 1: 10.0.0.11
                         │  Node 2: 10.0.0.12
                         │  Node 3: 10.0.0.13

╔════════════════════════════════════════════════════════════════════════╗
║                  MAIN RIG (Development Only)                            ║
║                                                                         ║
║  All services in Docker Compose (local only, not in production path)   ║
║  Vite dev server: localhost:5173                                        ║
║  FastAPI dev: localhost:8080                                            ║
║  ML sidecar dev: localhost:50051                                        ║
╚════════════════════════════════════════════════════════════════════════╝
```

**Network security rules:**
- Node 1 accepts inbound connections only from Node 2 (10.0.0.12) and Node 3 (10.0.0.13)
- Node 3 accepts inbound connections only from Node 2 (gRPC 50051)
- Node 2 accepts inbound only from cloudflared tunnel (loopback → Nginx)
- No direct port exposure from any node to the internet
- Proxmox management interface on a separate VLAN (192.168.1.0/24)

---

## 9. Storage Growth Projections

Based on 25 active tickers (20 stocks + 5 crypto), daily ingestion, and 90-day retention
for news/social data.

| Database | Month 1 | Month 3 | Month 6 | Month 12 | Notes |
|----------|---------|---------|---------|----------|-------|
| PostgreSQL (OHLCV) | 3 GB | 3.5 GB | 4 GB | 5 GB | TimescaleDB compression ~10:1 |
| PostgreSQL (predictions) | 0.5 GB | 1 GB | 1.5 GB | 3 GB | 4 horizons × 25 tickers × daily |
| PostgreSQL (sentiment) | 0.2 GB | 0.5 GB | 1 GB | 2 GB | Aggregated per ticker per day |
| Valkey | 0.1 GB | 0.1 GB | 0.1 GB | 0.1 GB | TTL-bounded; nearly flat |
| ChromaDB | 1 GB | 2 GB | 3.5 GB | 6 GB | News embeddings (768-dim float32) |
| MinIO (charts) | 0.5 GB | 1 GB | 1.5 GB | 2.5 GB | ~50 KB/chart × 25 tickers × daily |
| MinIO (models) | 3 GB | 4 GB | 5 GB | 6 GB | 3 model types × 25 tickers |
| MinIO (Parquet archive) | 0.5 GB | 1.5 GB | 3 GB | 6 GB | Nightly OHLCV export |
| MongoDB (news) | 1 GB | 2 GB | 3 GB | 3 GB | 90-day TTL index; steady-state ~3 GB |
| MongoDB (reddit) | 0.5 GB | 1 GB | 1.5 GB | 1.5 GB | 90-day TTL index; steady-state |
| Elasticsearch | 2 GB | 4 GB | 5 GB | 5 GB | 90-day ILM rollover; steady-state |
| InfluxDB | 0.5 GB | 1 GB | 1.5 GB | 2 GB | Real-time mention counts |
| Neo4j AuraDB | < 50 MB | < 100 MB | < 200 MB | < 200 MB | Bounded by free tier (200 MB) |
| **Total** | **~14 GB** | **~22 GB** | **~31 GB** | **~43 GB** | Well within 360 GB cluster budget |

**TimescaleDB compression detail:**
The `ohlcv` hypertable compresses chunks older than 7 days. For 25 tickers with 2 years of daily
OHLCV (5 columns × NUMERIC), uncompressed = ~18 MB; compressed ≈ 1.8 MB. Run this query to
monitor compression ratio:
```sql
SELECT
    hypertable_name,
    pg_size_pretty(before_compression_total_bytes) AS before,
    pg_size_pretty(after_compression_total_bytes) AS after,
    ROUND(before_compression_total_bytes::numeric /
          NULLIF(after_compression_total_bytes, 0), 1) AS ratio
FROM timescaledb_information.chunk_compression_stats;
```

---

## 10. Migration Thresholds

When these thresholds are hit, take the listed action before the service degrades.

| Database | Metric | Warning Threshold | Action |
|----------|--------|-------------------|--------|
| PostgreSQL | Table size | 30 GB total | Extend TimescaleDB compression window to 3 days; add more tickers to the compression job |
| PostgreSQL | Connection count | > 80 / 100 | Enable `pgBouncer` connection pooling |
| Valkey | Memory used | > 700 MB | Review TTL policies; consider moving cold cache entries to PostgreSQL |
| MongoDB | Collection size | news_articles > 3 GB | Verify 90-day TTL index is running; check for non-expiring documents |
| Elasticsearch | Disk watermark | > 85% used | Run ILM force-rollover; delete indices older than 90 days |
| ChromaDB | Collection size | > 8 GB | Prune embeddings for deleted articles; consider downgrading to 384-dim model |
| MinIO | Bucket `ohlcv-archive` | > 20 GB | Enable Parquet partitioning by year-month; verify old monthly files are compressed |
| MinIO | Bucket `models` | > 8 GB | Delete model versions more than 3 versions old per ticker |
| Node 1 disk | Overall | > 90 GB / 120 GB | Archive MongoDB snapshots to external storage; verify compression is running |
| Node 3 disk | Overall | > 50 GB / 60 GB | Delete stale ChromaDB embeddings; compress old Elasticsearch indices |

---

## 11. Environment Variable Reference

All variables read from `.env` at startup via `pydantic-settings`. Group them into `.env` exactly
as shown below — the application expects these names.

### Core Application
```ini
# Application
APP_ENV=development              # development | production
APP_SECRET_KEY=                  # 64-char random hex: openssl rand -hex 32
APP_HOST=0.0.0.0
APP_PORT=8080
LOG_LEVEL=INFO                   # DEBUG | INFO | WARNING | ERROR

# JWT
JWT_SECRET=                      # 64-char random hex
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
JWT_REFRESH_EXPIRE_DAYS=7
```

### PostgreSQL / TimescaleDB
```ini
POSTGRES_HOST=localhost           # Node 1 IP in production: 10.0.0.11
POSTGRES_PORT=5432
POSTGRES_DB=marketpulse
POSTGRES_USER=marketpulse
POSTGRES_PASSWORD=               # Strong password
DATABASE_URL=postgresql+asyncpg://marketpulse:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:5432/marketpulse
```

### Valkey
```ini
VALKEY_HOST=localhost             # Node 1 IP in production: 10.0.0.11
VALKEY_PORT=6379
VALKEY_PASSWORD=                 # Strong password
VALKEY_URL=redis://:${VALKEY_PASSWORD}@${VALKEY_HOST}:6379/0
```

### ChromaDB
```ini
CHROMA_HOST=localhost             # Node 3 IP in production: 10.0.0.13
CHROMA_PORT=8000
CHROMA_AUTH_TOKEN=               # Set in chromadb config
```

### SurrealDB
```ini
SURREAL_HOST=localhost            # Node 3 IP in production: 10.0.0.13
SURREAL_PORT=8001
SURREAL_USER=root
SURREAL_PASSWORD=                # Strong password
SURREAL_NAMESPACE=marketpulse
SURREAL_DATABASE=main
```

### MinIO
```ini
MINIO_HOST=localhost              # Node 1 IP in production: 10.0.0.11
MINIO_PORT=9000
MINIO_ACCESS_KEY=                # Generate: 20-char alphanumeric
MINIO_SECRET_KEY=                # Generate: 40-char alphanumeric
MINIO_SECURE=false               # true in production (configure TLS on MinIO)
```

### MongoDB
```ini
MONGO_HOST=localhost              # Node 1 IP in production: 10.0.0.11
MONGO_PORT=27017
MONGO_USER=marketpulse
MONGO_PASSWORD=                  # Strong password
MONGO_DB=marketpulse
MONGO_URL=mongodb://${MONGO_USER}:${MONGO_PASSWORD}@${MONGO_HOST}:27017/${MONGO_DB}
```

### Elasticsearch
```ini
ELASTIC_HOST=localhost            # Node 3 IP in production: 10.0.0.13
ELASTIC_PORT=9200
ELASTIC_USER=elastic
ELASTIC_PASSWORD=                # Strong password (set during first start)
ELASTIC_URL=http://${ELASTIC_HOST}:${ELASTIC_PORT}
```

### InfluxDB
```ini
INFLUX_HOST=localhost             # Node 1 IP in production: 10.0.0.11
INFLUX_PORT=8086
INFLUX_ORG=marketpulse
INFLUX_BUCKET=marketpulse
INFLUX_TOKEN=                    # Generate from InfluxDB UI after first start
INFLUX_URL=http://${INFLUX_HOST}:${INFLUX_PORT}
```

### Embedded Databases (paths only)
```ini
SQLITE_JOURNAL_PATH=data/event_journal.db
SQLITE_AUDIT_PATH=data/audit_ledger.db
SPATIALITE_PATH=data/spatial.db
ZODB_PATH=data/ticker_registry.fs
DUCKDB_LIVE_PATH=:memory:
DUCKDB_ANALYTICS_PATH=data/analytics.duckdb
NETWORKX_SQLITE_PATH=data/correlation_graph.db
```

### DataStax Astra (Cassandra)
```ini
ASTRA_DB_ID=                     # From Astra console
ASTRA_DB_REGION=                 # e.g., us-east-2
ASTRA_DB_KEYSPACE=marketpulse
ASTRA_TOKEN=AstraCS:...          # Application token from Astra console
ASTRA_SECURE_CONNECT_BUNDLE=secrets/astra-secure-connect-bundle.zip
```

### Neo4j AuraDB
```ini
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=                  # From AuraDB console
```

### ML Sidecar
```ini
ML_SIDECAR_HOST=localhost         # Node 3 IP in production: 10.0.0.13
ML_SIDECAR_PORT=50051
ML_SIDECAR_TIMEOUT_SECONDS=10
ML_CIRCUIT_BREAKER_THRESHOLD=3   # Failures before circuit opens
ML_CIRCUIT_BREAKER_TIMEOUT=60    # Seconds before retry
```

### OPA
```ini
OPA_HOST=localhost                # Node 2 IP in production: 10.0.0.12
OPA_PORT=8181
OPA_POLICY_PATH=v1/data/marketpulse/authz
```

### Data Sources — Stock Market
```ini
POLYGON_API_KEY=                 # polygon.io free tier
YFINANCE_REQUESTS_CACHE=true     # Enable requests-cache for yfinance
FINNHUB_API_KEY=                 # finnhub.io free tier
```

### Data Sources — Crypto
```ini
COINGECKO_API_KEY=               # coingecko.com free tier (optional)
```

### Data Sources — News
```ini
NEWSAPI_KEY=                     # newsapi.org free tier
GNEWS_API_KEY=                   # gnews.io free tier
```

### Data Sources — Social
```ini
REDDIT_CLIENT_ID=                # reddit.com/prefs/apps
REDDIT_CLIENT_SECRET=            # reddit.com/prefs/apps
REDDIT_USER_AGENT=MarketPulse/1.0 by YourRedditUsername
```

### Data Sources — Macro
```ini
FRED_API_KEY=                    # fred.stlouisfed.org/api
```

### Notifications — Push
```ini
ONESIGNAL_APP_ID=                # onesignal.com dashboard
ONESIGNAL_REST_API_KEY=          # onesignal.com dashboard
```

### Notifications — Email
```ini
SMTP_HOST=smtp.gmail.com         # Or your SMTP provider
SMTP_PORT=587
SMTP_USER=                       # Email address
SMTP_PASSWORD=                   # App password (not account password)
SMTP_FROM=MarketPulse <noreply@yourdomain.com>
```

### Notifications — SMS (optional, feature-flagged off by default)
```ini
TWILIO_ACCOUNT_SID=              # twilio.com console
TWILIO_AUTH_TOKEN=               # twilio.com console
TWILIO_FROM_NUMBER=+1...         # Your Twilio number
```

### Discord
```ini
DISCORD_BOT_TOKEN=               # discord.com/developers/applications
DISCORD_GUILD_ID=                # Right-click server → Copy Server ID
DISCORD_ALERT_CHANNEL_ID=        # Right-click channel → Copy Channel ID
```

### Voice
```ini
ALEXA_SKILL_ID=amzn1.ask.skill...  # From Alexa Developer Console
GOOGLE_ACTION_PROJECT_ID=           # From Actions on Google console
```

### Cloudflare
```ini
CLOUDFLARE_TUNNEL_TOKEN=         # cloudflared tunnel token
CLOUDFLARE_ACCOUNT_ID=           # Cloudflare dashboard
```

### Observability
```ini
PROMETHEUS_PUSH_GATEWAY=http://localhost:9091  # If using push gateway
JAEGER_HOST=localhost            # Node 2 IP in production: 10.0.0.12
JAEGER_PORT=14268
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:14268/api/traces
```

### HashiCorp Vault (Production Only)
```ini
VAULT_ADDR=http://10.0.0.11:8200
VAULT_TOKEN=                     # Or use AppRole auth
VAULT_MOUNT_PATH=secret/marketpulse
```

---

## 12. One-Command Startup per Node

These commands start all services on each node. Run them after `git pull` and any config updates.

### Node 1 (Data Layer)
```bash
# SSH to Node 1
ssh deploy@10.0.0.11

# Pull latest config
cd ~/marketpulse && git pull origin main

# Start all Node 1 services
docker compose -f docker-compose.node1.yml up -d

# Verify all healthy
docker compose -f docker-compose.node1.yml ps

# Watch logs
docker compose -f docker-compose.node1.yml logs -f --tail=100
```

**`docker-compose.node1.yml` (abbreviated — full file in the repo):**
```yaml
services:
  mp-pg:
    image: timescale/timescaledb:2.14.2-pg16
    env_file: .env
    ports: ["5432:5432"]
    volumes:
      - pg_data:/var/lib/postgresql/data
      - ./init/postgres:/docker-entrypoint-initdb.d:ro
    deploy:
      resources:
        limits: {memory: 3g}
    restart: always

  mp-valkey:
    image: valkey/valkey:7.2
    env_file: .env
    command: valkey-server /etc/valkey/valkey.conf
    volumes:
      - valkey_data:/data
      - ./config/valkey.conf:/etc/valkey/valkey.conf:ro
    deploy:
      resources:
        limits: {memory: 1g}
    restart: always

  mp-minio:
    image: minio/minio:latest
    env_file: .env
    command: server /data --console-address ":9001"
    ports: ["9000:9000", "9001:9001"]
    volumes:
      - minio_data:/data
    deploy:
      resources:
        limits: {memory: 1g}
    restart: always

  mp-mongo:
    image: mongo:7.0
    env_file: .env
    ports: ["27017:27017"]
    volumes:
      - mongo_data:/data/db
      - ./init/mongo:/docker-entrypoint-initdb.d:ro
    deploy:
      resources:
        limits: {memory: 2g}
    restart: always

  mp-influx:
    image: influxdb:2.7
    env_file: .env
    ports: ["8086:8086"]
    volumes:
      - influx_data:/var/lib/influxdb2
    deploy:
      resources:
        limits: {memory: 1g}
    restart: always

volumes:
  pg_data:
  valkey_data:
  minio_data:
  mongo_data:
  influx_data:
```

### Node 2 (Application Layer)
```bash
ssh deploy@10.0.0.12
cd ~/marketpulse && git pull origin main

# Deploy API (blue/green — new version starts on port 8081, nginx cuts over)
docker build -t ghcr.io/you/marketpulse-api:$(git rev-parse --short HEAD) .
docker run -d --name mp-api-green \
    --env-file .env \
    -p 8081:8080 \
    --restart always \
    ghcr.io/you/marketpulse-api:$(git rev-parse --short HEAD)

# Run smoke test against green
curl http://localhost:8081/health

# If healthy, cut nginx to green
sed -i 's/8080/8081/' /etc/nginx/conf.d/marketpulse.conf && nginx -s reload

# Stop old blue
docker stop mp-api-blue && docker rm mp-api-blue
docker rename mp-api-green mp-api-blue

# Start ARQ workers
docker compose -f docker-compose.node2.yml up -d mp-arq-ingest mp-arq-predict mp-arq-notify

# Start Discord bot
docker compose -f docker-compose.node2.yml up -d mp-discord

# Start OPA with latest policies
docker compose -f docker-compose.node2.yml up -d mp-opa
```

### Node 3 (ML and Analytics)
```bash
ssh deploy@10.0.0.13
cd ~/marketpulse && git pull origin main

# Start supporting services
docker compose -f docker-compose.node3.yml up -d mp-chroma mp-surreal mp-elastic

# Deploy ML sidecar (canary — new version on port 50052)
docker build -t ghcr.io/you/marketpulse-ml:$(git rev-parse --short HEAD) ./ml_sidecar
docker run -d --name mp-ml-canary \
    --env-file .env \
    -p 50052:50051 \
    -v /data/models:/data/models \
    --restart always \
    ghcr.io/you/marketpulse-ml:$(git rev-parse --short HEAD)

# Update FastAPI config to send 5% of traffic to canary
# (set ML_SIDECAR_CANARY_HOST and ML_SIDECAR_CANARY_WEIGHT=0.05 in .env on Node 2)

# Monitor canary accuracy for 24h before promoting to 100%
```

---

## 13. Shutdown Sequence

Always shut down in this order to avoid data loss. A reverse of the startup order.

### Graceful Shutdown (maintenance or upgrade)
```bash
# Step 1: Drain incoming traffic (Node 2)
# Update Cloudflare to return maintenance page, or
# Set cloudflared tunnel to reject new connections:
cloudflared tunnel cleanup marketpulse

# Step 2: Stop ARQ workers and Discord bot (let in-progress tasks finish)
docker compose -f docker-compose.node2.yml stop mp-arq-ingest mp-arq-predict mp-arq-notify mp-discord
# Wait 30 seconds for graceful task completion

# Step 3: Stop FastAPI backend
docker compose -f docker-compose.node2.yml stop mp-api

# Step 4: Stop ML sidecar (Node 3)
docker compose -f docker-compose.node3.yml stop mp-ml

# Step 5: Stop analytics databases (Node 3)
docker compose -f docker-compose.node3.yml stop mp-chroma mp-surreal mp-elastic

# Step 6: Stop data layer (Node 1) — databases last
# Postgres: gracefully shut down accepting connections, then flush WAL
docker exec mp-pg pg_ctl stop -m fast
# MongoDB: clean shutdown
docker exec mp-mongo mongod --shutdown
# InfluxDB: flush before stop
docker compose -f docker-compose.node1.yml stop mp-influx
# Valkey: trigger BGSAVE before stop
docker exec mp-valkey valkey-cli BGSAVE
sleep 5
docker compose -f docker-compose.node1.yml stop mp-valkey
# MinIO last
docker compose -f docker-compose.node1.yml stop mp-minio

# Step 7: Verify all containers stopped
docker ps -a | grep mp-
```

### Emergency Shutdown (power loss or critical failure)
If you must shut down immediately without the graceful sequence, the only database at risk of
data loss is Valkey (in-memory). PostgreSQL, MongoDB, and InfluxDB use write-ahead logging and
will recover on restart. After emergency shutdown, always run:
```bash
# On Node 1 restart:
docker start mp-pg
docker exec mp-pg psql -U marketpulse -c "CHECKPOINT;"  # Force WAL flush

docker start mp-mongo
# MongoDB auto-recovers from journal on startup

docker start mp-valkey
# Valkey replays AOF log — may take a few minutes if log is large
```

---

## 14. Port Reference

All ports used by MarketPulse across all nodes.

| Port | Service | Node | Protocol | Exposed to |
|------|---------|------|----------|-----------|
| 5432 | PostgreSQL | Node 1 | TCP | Node 2, Node 3, main rig (dev) |
| 6379 | Valkey | Node 1 | TCP | Node 2, Node 3, main rig (dev) |
| 8000 | ChromaDB | Node 3 | HTTP | Node 2, Node 3 |
| 8001 | SurrealDB | Node 3 | HTTP/WS | Node 2 |
| 8080 | FastAPI backend | Node 2 | HTTP | Nginx (loopback) |
| 8082 | Voice fulfillment | Node 2 | HTTP | Nginx (loopback) |
| 8086 | InfluxDB | Node 1 | HTTP | Node 2, Node 3 |
| 8181 | OPA | Node 2 | HTTP | Node 2 (loopback) |
| 9000 | MinIO API | Node 1 | HTTP | Node 2, Node 3 |
| 9001 | MinIO Console | Node 1 | HTTP | Admin only (VPN) |
| 9090 | Prometheus | Node 1 | HTTP | Node 2 (Grafana) |
| 9200 | Elasticsearch API | Node 3 | HTTP | Node 2 |
| 9300 | Elasticsearch cluster | Node 3 | TCP | Internal only |
| 3000 | Grafana | Node 2 | HTTP | Admin only (VPN) |
| 3100 | Loki | Node 1 | HTTP | Node 2 (Grafana) |
| 16686 | Jaeger UI | Node 2 | HTTP | Admin only (VPN) |
| 14268 | Jaeger collector | Node 2 | HTTP | Node 2 (loopback) |
| 27017 | MongoDB | Node 1 | TCP | Node 2, Node 3 |
| 50051 | ML sidecar gRPC | Node 3 | gRPC | Node 2 |
| 80/443 | Nginx | Node 2 | HTTP/HTTPS | cloudflared (loopback) |

**No port in this table is directly exposed to the internet.**
All external access goes through the Cloudflare Tunnel on Node 2.
Admin-only services (Grafana, MinIO Console, Jaeger UI) require VPN access to the Proxmox LAN.
