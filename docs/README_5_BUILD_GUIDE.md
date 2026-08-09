# MarketPulse — Build Guide

> This is your daily driver. Open it every morning. Find your current phase. Work top to bottom.
> Do not skip steps. Do not move to the next phase until the current phase's VALIDATE gate passes.
> Every checkbox is a real deliverable, not documentation padding.

---

## How to Use This Guide

- `[ ]` — Not started
- `[x]` — Complete
- `[!]` — In progress
- `[VALIDATE]` — A gate. Do not proceed until this check passes.

When you complete a step, mark it `[x]`. When you finish a phase, run the VALIDATE check and
mark it too. If the VALIDATE fails, fix the issue before moving on — a later phase may depend on
something this phase should have established.

---

## Phase 0 — Developer Environment

**Goal:** A clean, reproducible development environment on the main rig. All tools at correct
versions. Git configured. VS Code configured. Python virtual environment working.

- [x] 0.1 Install Git if not present: `winget install Git.Git` (Windows) or `brew install git` (Mac)
- [x] 0.2 Configure Git identity:
      ```bash
      git config --global user.name "Your Name"
      git config --global user.email "your@email.com"
      ```
- [x] 0.3 Create the project repository on GitHub: name it `marketpulse`, private, with a README.
- [x] 0.4 Clone the repository locally: `git clone git@github.com:<you>/marketpulse.git`
- [x] 0.5 Install Python 3.11.x (not 3.12+ — some ML libraries have not fully validated on 3.12):
      - Windows: https://python.org/downloads/ or `pyenv install 3.11.9`
      - Mac: `brew install python@3.11`
      - Linux: `sudo apt-get install python3.11 python3.11-venv`
- [x] 0.6 Create a virtual environment inside the project: `cd marketpulse && python3.11 -m venv .venv`
- [x] 0.7 Activate it: `source .venv/bin/activate` (Linux/Mac) or `.venv\Scripts\activate` (Windows)
- [x] 0.8 Upgrade pip: `pip install --upgrade pip`
- [x] 0.9 Install all packages from the complete pip command in README_1.
- [x] 0.10 Install Node.js 20 LTS: https://nodejs.org/ or `nvm install 20 && nvm use 20`
- [x] 0.11 Install Docker Desktop (Windows/Mac) or Docker Engine (Linux).
      - Verify: `docker --version` and `docker compose version`
- [x] 0.12 Install VS Code (https://code.visualstudio.com/) with extensions:
      - Python (Microsoft)
      - Pylance
      - ESLint
      - Prettier
      - Docker
      - GitLens
      - REST Client (for `.http` file API testing)
      - Thunder Client (in-IDE HTTP client)
- [x] 0.13 Install `ruff`: `pip install ruff`
- [x] 0.14 Install `black`: `pip install black`
- [x] 0.15 Install `mypy`: `pip install mypy`
- [x] 0.16 Configure `pyproject.toml` at project root:
      ```toml
      [tool.black]
      line-length = 100
      target-version = ["py311"]

      [tool.ruff]
      line-length = 100
      select = ["E", "F", "W", "I", "N", "UP", "S", "B", "A", "C4", "DTZ"]
      ignore = ["S101"]  # allow assert in tests

      [tool.mypy]
      python_version = "3.11"
      strict = true
      ignore_missing_imports = true
      ```
- [x] 0.17 Create `.gitignore` with entries for: `.venv`, `__pycache__`, `.env`, `.env.local`,
      `*.pyc`, `data/`, `secrets/`, `*.db`, `*.fs`, `.DS_Store`, `node_modules/`, `dist/`,
      `build/`, `.coverage`, `htmlcov/`
- [x] 0.18 Create `.env` from the template in README_1. Fill in strong passwords for all DB fields.
      **Do not fill in API keys yet** — those come in later phases.
- [x] 0.19 Create the project directory structure:
      ```
      marketpulse/
      ├── app/                  ← FastAPI backend
      │   ├── api/              ← Route handlers
      │   ├── core/             ← Config, security, middleware
      │   ├── db/               ← Database adapters (repositories)
      │   ├── domain/           ← Domain model classes
      │   ├── events/           ← Event types and publisher
      │   ├── plugins/          ← Plugin system
      │   └── workers/          ← ARQ background tasks
      ├── ml_sidecar/           ← ML gRPC sidecar
      │   ├── proto/            ← .proto files
      │   ├── models/           ← PyTorch, XGBoost, LightGBM model classes
      │   ├── training/         ← Training scripts
      │   └── server.py         ← gRPC server entry point
      ├── discord_bot/          ← discord.py bot
      ├── web_dashboard/        ← React + Vite frontend
      │   ├── src/
      │   │   ├── components/
      │   │   ├── pages/
      │   │   ├── store/        ← Redux Toolkit slices
      │   │   ├── types/        ← TypeScript interfaces
      │   │   └── api/          ← RTK Query endpoints
      │   └── package.json
      ├── mobile_app/           ← React Native
      ├── voice/                ← Alexa skill + Google Home action
      ├── policies/             ← OPA Rego policies
      ├── deploy/               ← Kubernetes manifests (Argo CD)
      ├── ansible/              ← Ansible playbooks
      ├── observability/        ← Prometheus, Grafana, Loki configs
      ├── init/                 ← Database init scripts
      ├── tests/                ← pytest test suite
      │   ├── unit/
      │   ├── integration/
      │   └── api/
      ├── data/                 ← Embedded database files (gitignored)
      ├── secrets/              ← Astra SCB zip, certs (gitignored)
      ├── docs/                 ← The nine README files
      ├── docker-compose.yml
      ├── .env
      ├── .gitignore
      └── pyproject.toml
      ```
- [x] 0.20 Make the initial commit: `git add . && git commit -m "chore: initial project structure"`

### [VALIDATE] Phase 0
```bash
python --version          # Should print Python 3.11.x
pip show fastapi          # Should show FastAPI installed
docker --version          # Should show Docker version
docker compose version    # Should show Docker Compose version
node --version            # Should show v20.x.x
ruff --version            # Should show ruff version
mypy --version            # Should show mypy version
git log --oneline -1      # Should show initial commit
```
All six commands must succeed before proceeding to Phase 1.

---

## Phase 1 — All Databases Running

**Goal:** Every one of the 17 databases running locally via Docker Compose, with the health
check script returning 100% PASS.

**Prerequisite:** Phase 0 VALIDATE passed.

- [x] 1.1 Copy the complete `docker-compose.yml` from README_1 into the project root.
- [x] 1.2 Create `init/postgres/001_schema.sql` with the complete schema from README_1.
- [x] 1.3 Create `init/mongo/init.js` with the index setup from README_1.
- [x] 1.4 Create `observability/prometheus.yml`:
      ```yaml
      global:
        scrape_interval: 15s
      scrape_configs:
        - job_name: "marketpulse-api"
          static_configs:
            - targets: ["host.docker.internal:8080"]
        - job_name: "postgres"
          static_configs:
            - targets: ["postgres:9187"]  # postgres_exporter
      ```
- [x] 1.5 Create `observability/loki.yml` (basic single-process Loki config).
- [x] 1.6 Start the full stack: `docker compose up -d`
- [x] 1.7 Wait 60 seconds for all services to initialize.
- [x] 1.8 Run the health check script from README_1: `python marketpulse_healthcheck.py`

**For cloud databases (parallel with 1.1–1.8):**
- [x] 1.9 Create DataStax Astra account and database (instructions in README_1).
      Download the Secure Connect Bundle to `secrets/astra-secure-connect-bundle.zip`.
- [x] 1.10 Run the Astra CQL schema from README_1 in the Astra CQL console.
- [x] 1.11 Create Neo4j AuraDB Free account and instance (instructions in README_1).
      Save the credentials to `.env`.
- [x] 1.12 Run the Neo4j constraint creation Cypher queries from README_1.

**For embedded databases:**
- [x] 1.13 Create `data/` directory (gitignored).
- [x] 1.14 Run `python -c "from app.db.embedded import init_all; init_all()"` to initialize
      all five embedded databases (event journal, audit ledger, SpatiaLite, ZODB, DuckDB).
- [x] 1.15 Install SpatiaLite: `sudo apt-get install spatialite-bin` (Linux) or
      `brew install spatialite-tools` (Mac).

**Documentation links:**
- README_1 for all database-specific setup steps
- Docker Compose reference: https://docs.docker.com/compose/compose-file/

### [VALIDATE] Phase 1
```bash
python marketpulse_healthcheck.py
# Expected: all 17 databases PASS (or N/A for cloud databases if network is unavailable)

docker compose ps
# Expected: all containers "healthy" or "running"

# Spot-check TimescaleDB hypertables
docker exec marketpulse-postgres psql -U marketpulse -d marketpulse \
    -c "SELECT hypertable_name FROM timescaledb_information.hypertables;"
# Expected: 4 hypertables listed

# Spot-check Valkey
docker exec marketpulse-valkey valkey-cli -a $VALKEY_PASSWORD ping
# Expected: PONG
```

---

## Phase 2 — CI/CD and Code Quality

**Goal:** GitHub Actions pipelines running. Linting and type checking passing on empty project.
Pre-commit hooks installed.

- [x] 2.1 Create `.github/workflows/test.yml`:
      ```yaml
      name: Test
      on: [push, pull_request]
      jobs:
        test:
          runs-on: ubuntu-latest
          steps:
            - uses: actions/checkout@v4
            - uses: actions/setup-python@v5
              with: {python-version: "3.11"}
            - run: pip install -r requirements.txt
            - run: ruff check .
            - run: black --check .
            - run: mypy app/ --ignore-missing-imports
            - run: pytest tests/ --cov=app --cov-report=xml
      ```
- [x] 2.2 Create `requirements.txt` by running `pip freeze > requirements.txt` from the venv.
- [x] 2.3 Create the initial empty test file: `tests/__init__.py` and `tests/unit/__init__.py`
- [x] 2.4 Install `pre-commit`: `pip install pre-commit`
- [x] 2.5 Create `.pre-commit-config.yaml`:
      ```yaml
      repos:
        - repo: https://github.com/astral-sh/ruff-pre-commit
          rev: v0.3.0
          hooks:
            - id: ruff
              args: [--fix]
        - repo: https://github.com/psf/black
          rev: 24.3.0
          hooks:
            - id: black
        - repo: https://github.com/pre-commit/mirrors-mypy
          rev: v1.9.0
          hooks:
            - id: mypy
              args: [--ignore-missing-imports]
      ```
- [x] 2.6 Install the hooks: `pre-commit install`
- [x] 2.7 Push to GitHub. Verify the Actions pipeline runs and passes.
- [x] 2.8 Set up GitHub branch protection on `main`: require PR, require CI pass, no force push.x

### [VALIDATE] Phase 2
```bash
ruff check .          # 0 errors (empty project)
black --check .       # All reformatted or already clean
mypy app/             # 0 errors
pytest tests/         # 0 tests (empty), but pytest exits 0
git push && # check GitHub Actions
```

---

## Phase 2.5 — Modularity Architecture

**Goal:** The plugin system, event bus, and feature flag infrastructure are implemented and
tested before any data source is written. This ensures all future modules use the same pattern.

- [x] 2.5.1 Implement `app/plugins/datasources/base.py` — `DataSourcePlugin` ABC with
      `fetch()`, `get_quota_info()`, and `health_check()` methods (from README_4).
- [x] 2.5.2 Implement `app/plugins/delivery/base.py` — `AlertDeliveryPlugin` ABC.
- [x] 2.5.3 Implement `app/plugins/__init__.py` — plugin registry with `load_all_plugins()`,
      `register_datasource()`, `register_delivery()`, and `get_enabled_datasources()`.
- [x] 2.5.4 Implement `app/events/types.py` — all 12 event type dataclasses.
- [x] 2.5.5 Implement `app/events/publisher.py` — `publish_event()` using MessagePack + Valkey.
- [x] 2.5.6 Implement `app/events/consumer.py` — `run_alert_consumer()` subscribing to events.
- [x] 2.5.7 Implement `app/core/feature_flags.py` — `sync_flags_to_cache()` and `is_enabled()`.
- [x] 2.5.8 Write unit tests for the plugin registry: test `load_all_plugins()` discovers
      plugins, `get_enabled_datasources()` filters by flags, and `register_datasource()` avoids
      duplicate registration.
- [x] 2.5.9 Write unit tests for the event publisher: test that events serialize correctly with
      MessagePack and that the correct channel name is used.
- [x] 2.5.10 Write unit tests for `is_enabled()`: test that disabled flags return False even
       when the database says enabled (if the Valkey cache contradicts PostgreSQL, Valkey wins
       until the next sync).

**Documentation links:**
- ABC module: https://docs.python.org/3/library/abc.html
- MessagePack Python: https://msgpack-python.readthedocs.io/

### [VALIDATE] Phase 2.5
```bash
pytest tests/unit/test_plugins.py -v      # All tests pass
pytest tests/unit/test_events.py -v       # All tests pass
pytest tests/unit/test_feature_flags.py -v # All tests pass

# Demonstrate the plugin pattern works:
python -c "
from app.plugins import load_all_plugins, get_enabled_datasources
load_all_plugins()
plugins = get_enabled_datasources({'datasource.test': True})
print(f'Plugins registered: {len(plugins)}')
"
```

---

## Phase 3 — Domain Model

**Goal:** All core business entity classes defined and tested. These are the objects the
entire application will work with.

- [ ] 3.1 Implement `app/domain/ticker.py` — `Ticker`, `StockTicker`, `CryptoTicker`, `IndexTicker`
      (Python dataclasses; ZODB-persistent versions come in Phase 4).
- [ ] 3.2 Implement `app/domain/prediction.py` — `Prediction`, `HorizonPrediction`,
      `PredictionOutcome`. Include `is_actionable()` method (returns True if confidence ≥ 75%).
- [ ] 3.3 Implement `app/domain/sentiment.py` — `SentimentScore`, `NewsArticle`, `RedditPost`.
- [ ] 3.4 Implement `app/domain/alert.py` — `Alert`, `AlertConfig`, `NotificationPreference`,
      `DeliveryResult`.
- [ ] 3.5 Implement `app/domain/watchlist.py` — `WatchList`, `WatchListEntry`.
- [ ] 3.6 Implement `app/domain/quota.py` — `APIQuota`, `QuotaStatus`.
- [ ] 3.7 Implement `app/domain/feature_vector.py` — `FeatureVector` with validation that
      all values are finite floats and the schema version matches the expected constant.
- [ ] 3.8 Write unit tests for all domain objects. Focus on edge cases:
      - `Prediction.is_actionable()` returns False for confidence = 74.9, True for 75.0.
      - `FeatureVector` raises `ValueError` for NaN values.
      - `AlertConfig` with no channels raises `ValueError` on construction.
      - `SentimentScore` normalizes scores to [-1.0, 1.0].

**Documentation links:**
- Python dataclasses: https://docs.python.org/3/library/dataclasses.html

### [VALIDATE] Phase 3
```bash
pytest tests/unit/test_domain.py -v   # All domain model tests pass
mypy app/domain/                       # 0 type errors
```

---

## Phase 4 — All 17 Database Adapters

**Goal:** A repository class for every database. Application code never touches raw SQL,
pymongo, or any driver directly — only repository methods.

- [ ] 4.1 **PostgreSQL / TimescaleDB** — `app/db/postgres/`:
      - `OHLCVRepository.insert_batch(records)`, `get_recent(symbol, days)`, `get_range(symbol, start, end)`
      - `PredictionRepository.insert(prediction)`, `get_latest(symbol, horizon)`, `get_unresolved()`
      - `TickerRepository.get_all_active()`, `insert(ticker)`, `deactivate(symbol)`
      - `SentimentRepository.insert_daily(score)`, `get_trend(symbol, days)`
      - `AlertConfigRepository.get_for_user(user_id)`, `get_matching_type(alert_type, symbol)`
      - `QuotaRepository.increment(source, daily)`, `get_all()`, `reset(source)`
- [ ] 4.2 **Valkey** — `app/db/valkey/`:
      - `PriceCacheRepository.set(symbol, price_data)`, `get(symbol)` → JSON
      - `QuotaCounterRepository.increment(source, daily)`, `get_count(source, daily)` → int
      - `FeatureFlagRepository.get_all()` → dict, `set(flag, value)`
      - `SessionRepository.create(user_id, token)`, `invalidate(jti)`
      - `PubSubRepository.publish(channel, event)`, `subscribe(channel)` → async generator
- [ ] 4.3 **ChromaDB** — `app/db/chroma/`:
      - `NewsDeduplicationRepository.is_duplicate(embedding, threshold)` → bool, `add(id, embedding, metadata)`
      - `RedditClusterRepository.add(post_id, embedding)`, `find_similar(embedding, n)`
      - `FeatureAnomalyRepository.fit(vectors)`, `score(vector)` → float
- [ ] 4.4 **SurrealDB** — `app/db/surreal/`:
      - `CrossDomainRepository.get_sector_news(symbol, days, sentiment_threshold)`
      - `SectorRepository.get_peers(symbol)` → list of symbols
- [ ] 4.5 **MinIO** — `app/db/minio/`:
      - `ChartRepository.upload(symbol, chart_bytes)` → presigned_url, `get_url(symbol, key)`
      - `ModelRepository.upload(symbol, model_name, version, file_bytes)`, `download(symbol, model_name, version)`
      - `ReportRepository.upload(symbol, format, file_bytes)` → download_url
      - `ParquetRepository.write_ohlcv(symbol, date, df)`, `read_ohlcv(symbol, start_date, end_date)`
- [ ] 4.6 **MongoDB** — `app/db/mongo/`:
      - `NewsArticleRepository.insert(article)`, `get_recent(symbol, hours)`, `get_unscored(limit)`
      - `RedditPostRepository.insert(post)`, `get_recent_by_subreddit(symbol, subreddit, hours)`
      - `SECFilingRepository.insert(filing)`, `get_recent(symbol, days)`
      - `PredictionExplanationRepository.insert(explanation)`, `get_for_prediction(symbol, time)`
- [ ] 4.7 **Elasticsearch** — `app/db/elastic/`:
      - `NewsSearchRepository.index(article)`, `search(query, symbol, days)`
      - `RedditSearchRepository.index(post)`, `search(query, symbol, days)`
- [ ] 4.8 **InfluxDB** — `app/db/influx/`:
      - `MentionCountRepository.write(symbol, subreddit, count)`, `get_recent(symbol, hours)`
      - `SentimentStreamRepository.write(symbol, source, score)`, `get_realtime(symbol, minutes)`
- [ ] 4.9 **SQLite event journal** — `app/db/embedded/event_journal.py`:
      - `EventJournalRepository.append(event_type, payload)`, `get_recent(event_type, n)`
- [ ] 4.10 **SQLite audit ledger** — `app/db/embedded/audit_ledger.py`:
      - `AuditLedgerRepository.append(action, actor_id, target_type, target_id, old, new)`
      - `AuditLedgerRepository.verify_chain()` → bool
- [ ] 4.11 **SpatiaLite** — `app/db/embedded/spatial.py`:
      - `CompanyGeoRepository.insert(symbol, lat, lon, city, country)`, `get_by_sector(sector)`
- [ ] 4.12 **ZODB** — `app/db/embedded/zodb_registry.py`:
      - `TickerRegistryRepository.add(ticker)`, `get(symbol)`, `get_all()`, `deactivate(symbol)`
- [ ] 4.13 **DuckDB in-memory** — `app/db/embedded/duckdb_live.py`:
      - `LiveAggregationRepository.get_daily_summary()`, `get_sector_breakdown()`
      - Refresh methods that re-read from Parquet/Valkey after each prediction update
- [ ] 4.14 **DuckDB persistent** — `app/db/embedded/duckdb_analytics.py`:
      - `AccuracyAnalyticsRepository.get_rolling_accuracy(symbol, horizon, window)`
      - `SentimentCorrelationRepository.compute(symbol, lag_days)`
- [ ] 4.15 **NetworkX/SQLite** — `app/db/embedded/correlation_graph.py`:
      - `CorrelationGraphRepository.update_edge(sym_a, sym_b, correlation)`, `get_neighbors(symbol, min_correlation)`, `get_graph()` → nx.Graph
- [ ] 4.16 **DataStax Astra** — `app/db/astra/`:
      - `APICallLogRepository.log(source, endpoint, status_code, latency_ms)`
      - `IngestionEventRepository.log(event_type, symbol, source, record_count, duration_ms)`
- [ ] 4.17 **Neo4j AuraDB** — `app/db/neo4j/`:
      - `TickerGraphRepository.create_ticker(ticker)`, `add_sector_membership(symbol, sector)`
      - `TickerGraphRepository.add_correlation(sym_a, sym_b, r)`, `get_peers(symbol)`
      - `InsiderGraphRepository.add_transaction(person, symbol, transaction_type)`
- [ ] 4.18 Write integration tests for each repository using test containers where applicable.
       Each test must verify: insert works, get returns the inserted data, error cases raise
       the correct domain exceptions.

**Documentation links:**
- asyncpg: https://magicstack.github.io/asyncpg/current/
- motor (async MongoDB): https://motor.readthedocs.io/
- elasticsearch-py: https://elasticsearch-py.readthedocs.io/
- neo4j Python driver: https://neo4j.com/docs/python-manual/current/

### [VALIDATE] Phase 4
```bash
pytest tests/integration/ -v -k "repository"
# All repository integration tests pass

# Verify each paradigm is represented:
python -c "
from app.db.postgres.ohlcv import OHLCVRepository
from app.db.valkey.price_cache import PriceCacheRepository
from app.db.chroma.news_dedup import NewsDeduplicationRepository
from app.db.mongo.news import NewsArticleRepository
from app.db.elastic.news_search import NewsSearchRepository
from app.db.embedded.zodb_registry import TickerRegistryRepository
print('All 17 adapters importable')
"
```

---

## Phase 5 — FastAPI Backend

**Goal:** The FastAPI application skeleton running with auth, OPA middleware, health endpoints,
and all route groups registered.

- [ ] 5.1 Create `app/main.py` — FastAPI application factory with: lifespan context manager
      (startup: load plugins, sync flags, init embedded DBs; shutdown: close all connections),
      CORS middleware, Prometheus middleware, structured logging middleware.
- [ ] 5.2 Create `app/core/config.py` — `Settings` class with pydantic-settings, reading all
      variables from the `.env` template in README_1.
- [ ] 5.3 Create `app/core/security.py` — JWT encode/decode, bcrypt hash/verify, TOTP
      generate/verify, `get_current_user` FastAPI dependency.
- [ ] 5.4 Create `app/core/opa_middleware.py` — FastAPI middleware that calls OPA before
      each protected route.
- [ ] 5.5 Create `policies/marketpulse.rego` — initial OPA policies for user vs. admin roles.
- [ ] 5.6 Create `app/api/v1/auth.py` — `POST /auth/login`, `POST /auth/verify-2fa`,
      `POST /auth/logout`, `POST /auth/refresh`.
- [ ] 5.7 Create `app/api/v1/tickers.py` — `GET /tickers`, `POST /tickers`, `GET /tickers/{symbol}`,
      `DELETE /tickers/{symbol}`.
- [ ] 5.8 Create `app/api/v1/predictions.py` — `GET /tickers/{symbol}/predictions`,
      `GET /tickers/{symbol}/predictions/history`.
- [ ] 5.9 Create `app/api/v1/sentiment.py` — `GET /tickers/{symbol}/sentiment`.
- [ ] 5.10 Create `app/api/v1/watchlists.py` — CRUD endpoints for watchlists and ticker membership.
- [ ] 5.11 Create `app/api/v1/alerts.py` — CRUD endpoints for alert configurations.
- [ ] 5.12 Create `app/api/v1/news.py` — `GET /tickers/{symbol}/news`.
- [ ] 5.13 Create `app/api/v1/admin.py` — all `/admin/*` endpoints for the paradigm console.
- [ ] 5.14 Create `app/api/v1/websocket.py` — WebSocket endpoint for real-time price updates.
- [ ] 5.15 Create `app/api/rss.py` — `GET /rss/predictions` RSS 2.0 feed.
- [ ] 5.16 Create `app/api/webhooks.py` — webhook receivers for OneSignal and Twilio callbacks.
- [ ] 5.17 Run the FastAPI app locally: `uvicorn app.main:app --reload --port 8080`
- [ ] 5.18 Open http://localhost:8080/docs — verify the Swagger UI loads with all routes.
- [ ] 5.19 Write API tests for auth flow: register user, login, get JWT, use JWT, logout, verify
      blocked.
- [ ] 5.20 Write API tests for ticker CRUD: create, read, update (deactivate), verify ZODB
      registry is updated when PostgreSQL is.

**Documentation links:**
- FastAPI: https://fastapi.tiangolo.com/
- FastAPI lifespan: https://fastapi.tiangolo.com/advanced/events/
- FastAPI WebSocket: https://fastapi.tiangolo.com/advanced/websockets/

### [VALIDATE] Phase 5
```bash
uvicorn app.main:app --port 8080 &
curl http://localhost:8080/health         # {"status": "ok"}
curl http://localhost:8080/api/v1/version # {"version": "0.1.0", ...}
curl http://localhost:8080/docs           # HTML page loads

pytest tests/api/ -v                      # All API tests pass
```

---

## Phase 6 — OHLCV Data Ingestion Pipeline

**Goal:** yfinance can fetch historical OHLCV for all 25 seed tickers. Daily ingestion ARQ task
runs and populates the TimescaleDB hypertable. Price cache in Valkey is updated.

- [ ] 6.1 Register yfinance API keys in `.env` (none needed — yfinance requires no key).
- [ ] 6.2 Get free Polygon.io API key at https://polygon.io and add to `.env`.
- [ ] 6.3 Get free CoinGecko API key at https://coingecko.com/api and add to `.env`.
- [ ] 6.4 Implement `app/plugins/datasources/yfinance_plugin.py` — fetches daily OHLCV,
      converts to `IngestRecord`, handles ticker not found gracefully.
- [ ] 6.5 Implement `app/plugins/datasources/polygon_plugin.py` — fetches real-time bars,
      implements the 5-calls/min async semaphore rate limiter.
- [ ] 6.6 Implement `app/plugins/datasources/coingecko_plugin.py` — fetches crypto OHLCV.
- [ ] 6.7 Implement `app/workers/ohlcv_ingest.py` — ARQ task that: selects all active tickers,
      determines the correct plugin per ticker type, calls `plugin.fetch()`, passes each record
      to `OHLCVRepository.insert_batch()`, updates Valkey price cache, enqueues chained tasks.
- [ ] 6.8 Implement the QuotaMiddleware wrapper in `app/workers/quota_middleware.py`.
- [ ] 6.9 Implement `app/workers/scheduler.py` — ARQ CronJob definitions:
      - `ohlcv_ingest`: daily at 4:00 AM UTC
      - `ohlcv_ingest_realtime`: every 60 seconds during market hours (09:30–16:00 ET, Mon–Fri)
- [ ] 6.10 Start the ARQ worker: `python -m arq app.workers.scheduler.WorkerSettings`
- [ ] 6.11 Trigger a manual ingestion run for AAPL only: `arq app.workers.ohlcv_ingest enqueue AAPL`
- [ ] 6.12 Verify OHLCV data in TimescaleDB:
       ```sql
       SELECT count(*) FROM ohlcv WHERE symbol='AAPL';
       -- Expected: ~500 rows (2 years of daily data)
       ```
- [ ] 6.13 Verify Valkey price cache: `GET price:cache:AAPL` should return JSON with current price.

**Documentation links:**
- yfinance: https://pypi.org/project/yfinance/
- ARQ: https://arq-docs.helpmanual.io/
- Polygon.io aggregates: https://polygon.io/docs/stocks/get_v2_aggs_ticker__stocksticker__range__multiplier___timespan___from___to_

### [VALIDATE] Phase 6
```bash
# 2 years of OHLCV data for AAPL
docker exec marketpulse-postgres psql -U marketpulse -d marketpulse \
    -c "SELECT count(*) FROM ohlcv WHERE symbol='AAPL';"
# Expected: count > 400

# Price cache populated
docker exec marketpulse-valkey valkey-cli -a $VALKEY_PASSWORD GET price:cache:AAPL
# Expected: JSON string with price data

# Time-bucket aggregation works
docker exec marketpulse-postgres psql -U marketpulse -d marketpulse \
    -c "SELECT time_bucket('1 week', time) AS week, avg(close) FROM ohlcv WHERE symbol='AAPL' GROUP BY week ORDER BY week DESC LIMIT 5;"
# Expected: 5 rows with weekly average close prices
```

---

## Phase 7 — News and RSS Ingestion Pipeline

**Goal:** All news sources and RSS feeds ingesting. Articles stored in MongoDB, indexed in
Elasticsearch, deduplicated by ChromaDB. VADER scoring on every article.

- [ ] 7.1 Get free NewsAPI key at https://newsapi.org/register and add to `.env`.
- [ ] 7.2 Get free GNews key at https://gnews.io and add to `.env`.
- [ ] 7.3 Get free Finnhub key at https://finnhub.io and add to `.env`.
- [ ] 7.4 Implement `app/plugins/datasources/newsapi_plugin.py`.
- [ ] 7.5 Implement `app/plugins/datasources/gnews_plugin.py`.
- [ ] 7.6 Implement `app/plugins/datasources/finnhub_plugin.py` (news endpoint only for now).
- [ ] 7.7 Implement `app/plugins/datasources/rss_plugin.py` — generic feedparser-based plugin
      that accepts a list of feed URLs and a ticker-to-feed-URL mapping. Each configured RSS feed
      creates one plugin instance.
- [ ] 7.8 Create `app/config/rss_feeds.py` — list of all 14+ default RSS feeds with ticker tags.
- [ ] 7.9 Implement `app/services/news_ingestion.py` — processes an `IngestRecord` of type
      "news": embedds the headline with sentence-transformers, checks ChromaDB deduplication,
      VADER-scores the text, stores in MongoDB, indexes in Elasticsearch.
- [ ] 7.10 Implement `app/workers/news_ingest.py` — ARQ task polling all news plugins on a
       15-minute cron schedule.
- [ ] 7.11 Run a manual news ingest for AAPL. Verify:
       - At least one article appears in MongoDB: `db.news_articles.find({symbol:"AAPL"}).count()`
       - Article indexed in Elasticsearch: `GET /news_index/_search?q=AAPL`
       - Duplicate article rejected by ChromaDB (test by running the same ingest twice)

**Documentation links:**
- feedparser: https://feedparser.readthedocs.io/
- sentence-transformers: https://www.sbert.net/docs/quickstart.html
- VADER: https://pypi.org/project/vaderSentiment/

### [VALIDATE] Phase 7
```bash
# Articles in MongoDB
python -c "
from pymongo import MongoClient
import os
client = MongoClient(os.environ['MONGO_URL'])
db = client['marketpulse']
count = db.news_articles.count_documents({'ticker_symbols': 'AAPL'})
print(f'AAPL articles: {count}')
assert count > 0, 'No AAPL articles found — news ingest failed'
"

# Articles in Elasticsearch
curl -u elastic:$ELASTIC_PASSWORD \
    'http://localhost:9200/news_index/_count?q=symbol:AAPL'
# Expected: {"count": >0}

# Deduplication working (same article fetched twice = still only one in MongoDB)
# Check that news_articles count doesn't grow when the same ingest runs again
```

---

## Phase 8 — Reddit Ingestion and PRAW Integration

**Goal:** PRAW authenticated. All 8 default subreddits polling. Posts stored in MongoDB.
Mention counts in InfluxDB. VADER scores on all posts.

- [ ] 8.1 Create a Reddit developer account at https://www.reddit.com/prefs/apps/
      Create an app type "script." Copy client_id, client_secret to `.env`.
      Set REDDIT_USER_AGENT to `MarketPulse/1.0 by <your-reddit-username>`.
- [ ] 8.2 Implement `app/plugins/datasources/reddit_plugin.py` — PRAW-based plugin that polls
      configured subreddits, extracts ticker mentions, VADER-scores each post.
- [ ] 8.3 Implement `app/workers/reddit_ingest.py` — ARQ task on a 30-minute cron schedule.
- [ ] 8.4 Trigger a manual Reddit ingest for `r/wallstreetbets` for tickers `["AAPL", "TSLA"]`.
- [ ] 8.5 Verify posts in MongoDB and mention counts in InfluxDB.

### [VALIDATE] Phase 8
```bash
python -c "
import praw, os
reddit = praw.Reddit(
    client_id=os.environ['REDDIT_CLIENT_ID'],
    client_secret=os.environ['REDDIT_CLIENT_SECRET'],
    user_agent=os.environ['REDDIT_USER_AGENT']
)
posts = list(reddit.subreddit('wallstreetbets').hot(limit=5))
print(f'PRAW working — fetched {len(posts)} posts')
assert len(posts) == 5
"
```

---

## Phase 9 — Technical Indicator Computation Pipeline

**Goal:** All technical indicators computed from OHLCV data and stored in the
`technical_indicators` hypertable. Valkey cache populated for ML feature reads.

- [ ] 9.1 Implement `app/services/indicators.py` — `compute_all_indicators(symbol, ohlcv_df)`
      using the `ta` library, returning a `TechnicalIndicatorSnapshot` domain object.
- [ ] 9.2 Implement `app/workers/indicator_compute.py` — ARQ task triggered by OHLCV ingest.
- [ ] 9.3 Write unit tests for indicator computation with a known OHLCV input and expected RSI,
      MACD, and Bollinger Band output values (use a fixed 14-day series with a known RSI result).
- [ ] 9.4 Verify the `technical_indicators` table is populated after running the OHLCV + indicator
      pipeline for AAPL.

**Documentation links:**
- ta: https://github.com/bukosabino/ta
- ta docs: https://technical-analysis-library-in-python.readthedocs.io/

### [VALIDATE] Phase 9
```bash
docker exec marketpulse-postgres psql -U marketpulse -d marketpulse \
    -c "SELECT time, rsi_14, macd_line, bb_upper FROM technical_indicators WHERE symbol='AAPL' ORDER BY time DESC LIMIT 1;"
# Expected: 1 row with all indicator values populated (not NULL)
```

---

## Phase 10 — Sentiment Analysis Pipeline (VADER + FinBERT)

**Goal:** VADER scores on all news and Reddit content. FinBERT deep-scoring running on the ML
sidecar for news articles. Daily sentiment aggregates in TimescaleDB.

- [ ] 10.1 Implement `app/services/sentiment_vader.py` — `score_text(text: str) -> float` using
       VADER, returns compound score in [-1.0, 1.0].
- [ ] 10.2 Implement the FinBERT scoring client — gRPC call to `SentimentService.ScoreText` on
       the ML sidecar (Phase 11 will implement the server; for now, mock it).
- [ ] 10.3 Implement `app/workers/finbert_scoring.py` — ARQ task that runs post-market, fetches
       unscored news articles from MongoDB in batches of 16, calls FinBERT via gRPC, updates
       MongoDB `finbert_score` field.
- [ ] 10.4 Implement `app/workers/sentiment_aggregate.py` — hourly ARQ task that computes
       per-ticker per-source sentiment aggregates and writes to TimescaleDB `sentiment_scores`.
- [ ] 10.5 Write unit tests for VADER scoring: verify "This stock is going to the moon! 🚀🚀🚀"
       scores > 0.5 and "This company is going bankrupt" scores < -0.5.

### [VALIDATE] Phase 10
```bash
python -c "
from app.services.sentiment_vader import score_text
bull = score_text('This stock is going to the moon! Amazing earnings!')
bear = score_text('This company is going bankrupt. Terrible results.')
print(f'Bullish: {bull:.3f}  Bearish: {bear:.3f}')
assert bull > 0.3 and bear < -0.3, 'VADER scoring not working correctly'
"
```

---

## Phase 11 — ML Prediction Sidecar

**Goal:** gRPC server running with LSTM, XGBoost, LightGBM, FinBERT, VADER, ensemble, and
Isolation Forest. Initial models trained on seed data. First prediction generated.

- [ ] 11.1 Create the protobuf definition: `ml_sidecar/proto/prediction.proto` (from README_2).
- [ ] 11.2 Generate gRPC stubs: `python -m grpc_tools.protoc -I./ml_sidecar/proto
       --python_out=./ml_sidecar --grpc_python_out=./ml_sidecar prediction.proto`
- [ ] 11.3 Implement `ml_sidecar/models/lstm_model.py` — PyTorch LSTM for price direction prediction.
       Input: (batch_size, sequence_length=30, features). Output: probability over 3 classes.
- [ ] 11.4 Implement `ml_sidecar/models/xgboost_model.py` — XGBoost classifier for tabular features.
- [ ] 11.5 Implement `ml_sidecar/models/lightgbm_model.py` — LightGBM classifier for tabular features.
- [ ] 11.6 Implement `ml_sidecar/models/ensemble.py` — combines all component outputs with
       learned per-ticker weights. Exposes `predict(feature_vector)` → `PredictionResponse`.
- [ ] 11.7 Implement `ml_sidecar/models/isolation_forest.py` — Isolation Forest for anomaly detection.
- [ ] 11.8 Implement `ml_sidecar/training/train.py` — training pipeline:
       1. Load 2 years of OHLCV from TimescaleDB
       2. Compute features with the feature engineering pipeline
       3. Create temporally-correct train/test split (no look-ahead)
       4. Train LSTM, XGBoost, LightGBM, Isolation Forest
       5. Calibrate XGBoost and LightGBM
       6. Train ensemble meta-learner on validation set
       7. Evaluate on test set, log accuracy metrics
       8. Save models to MinIO if test accuracy ≥ baseline
- [ ] 11.9 Implement `ml_sidecar/server.py` — gRPC server implementing `PredictionService.Predict`,
       `PredictionService.PredictStream`, `SentimentService.ScoreText`, and `SentimentService.ScoreBatch`.
- [ ] 11.10 Run training for AAPL: `python ml_sidecar/training/train.py --symbol AAPL`
        Verify model files uploaded to MinIO.
- [ ] 11.11 Start the gRPC server: `python ml_sidecar/server.py`
- [ ] 11.12 Implement `app/services/prediction_client.py` — gRPC client with circuit breaker.
- [ ] 11.13 Implement `app/workers/prediction_run.py` — ARQ task that assembles features and
        calls the gRPC client for each active ticker.
- [ ] 11.14 Run first end-to-end prediction for AAPL. Verify in TimescaleDB `predictions` table.
- [ ] 11.15 Implement `app/workers/outcome_resolver.py` — ARQ task that runs daily to resolve
        prediction outcomes and compute accuracy metrics.

**Documentation links:**
- PyTorch LSTM: https://pytorch.org/docs/stable/generated/torch.nn.LSTM.html
- XGBoost Python: https://xgboost.readthedocs.io/en/stable/python/
- LightGBM Python: https://lightgbm.readthedocs.io/en/stable/Python-Intro.html
- grpcio: https://grpc.io/docs/languages/python/quickstart/
- SHAP: https://shap.readthedocs.io/

### [VALIDATE] Phase 11
```bash
# gRPC server responding
python -c "
import grpc
from ml_sidecar import prediction_pb2_grpc, prediction_pb2
channel = grpc.insecure_channel('localhost:50051')
stub = prediction_pb2_grpc.PredictionServiceStub(channel)
resp = stub.Status(prediction_pb2.StatusRequest())
print(f'ML sidecar status: {resp.status}')
"

# Prediction in database
docker exec marketpulse-postgres psql -U marketpulse -d marketpulse \
    -c "SELECT symbol, horizon, direction, confidence FROM predictions ORDER BY time DESC LIMIT 4;"
# Expected: 4 rows for AAPL (1d, 3d, 7d, 30d)
```

---

## Phase 12 — Alert and Notification System

**Goal:** All six delivery channels implemented. Alert evaluation consuming events from the
event bus. Notifications delivered when test events are published.

- [ ] 12.1 Implement `app/plugins/delivery/browser_push.py` — OneSignal web push.
       Get OneSignal App ID and REST API key at https://onesignal.com, add to `.env`.
- [ ] 12.2 Implement `app/plugins/delivery/mobile_push.py` — OneSignal mobile push (same App ID).
- [ ] 12.3 Implement `app/plugins/delivery/email_plugin.py` — aiosmtplib SMTP delivery with
       Jinja2 HTML template. Add SMTP config to `.env`.
- [ ] 12.4 Implement `app/plugins/delivery/sms_plugin.py` — Twilio (feature-flagged off).
       Verify it is disabled by default (flag `alert.sms = false`).
- [ ] 12.5 Implement `app/plugins/delivery/discord_plugin.py` — discord.py message delivery.
- [ ] 12.6 Implement `app/plugins/delivery/voice_plugin.py` — Alexa announcement + Google Home
       broadcast (can stub the actual voice call for now).
- [ ] 12.7 Implement `app/events/consumer.py` — the alert evaluator subscribing to all event types.
- [ ] 12.8 Test end-to-end: manually publish a `PredictionChangedEvent` to Valkey pub/sub.
       Verify the alert evaluator fires and a notification appears in `notification_log`.
- [ ] 12.9 Write unit tests for each delivery plugin: test that `deliver()` calls the correct
       external API (mock the API call), and that a delivery failure returns a `DeliveryResult`
       with `success=False` rather than raising an exception.

### [VALIDATE] Phase 12
```bash
# Publish a test event and verify notification log entry
python -c "
import asyncio
from app.events.publisher import publish_event
from app.events.types import PredictionChangedEvent
from datetime import datetime
event = PredictionChangedEvent(
    symbol='AAPL', old_direction='FLAT', new_direction='UP',
    confidence=85.0, horizon='1d', timestamp=datetime.utcnow()
)
asyncio.run(publish_event(event))
print('Event published — check notification_log table')
"
docker exec marketpulse-postgres psql -U marketpulse -d marketpulse \
    -c "SELECT alert_type, channel, status FROM notification_log ORDER BY sent_at DESC LIMIT 5;"
```

---

## Phase 13 — Discord Bot

**Goal:** Discord bot running with all slash commands implemented. Chart images generating.
Paginated embeds working.

- [ ] 13.1 Create a Discord Application at https://discord.com/developers/applications.
       Create a Bot, copy the token to `.env`. Generate invite URL with `applications.commands`
       and `bot` scopes + `Send Messages`, `Embed Links`, `Attach Files` permissions.
       Invite the bot to a test Discord server.
- [ ] 13.2 Add Guild ID to `.env`: `DISCORD_GUILD_ID=<your-server-id>`
- [ ] 13.3 Implement `discord_bot/bot.py` — discord.py `commands.Bot` with slash commands.
       All commands call the FastAPI internal API (HTTP to `app`), never touching databases directly.
- [ ] 13.4 Implement all 15 slash commands (from README_2 Module 9 command table).
- [ ] 13.5 Implement the chart image generator (from README_2 Module 9 code snippet).
- [ ] 13.6 Implement pagination for `/watchlist`, `/news`, `/reddit` using `discord.ui.View`
       with `discord.ui.Button` for Next/Previous.
- [ ] 13.7 Run the bot: `python discord_bot/bot.py`
- [ ] 13.8 Test each slash command in the test Discord server. Verify chart image is sent as
       an attachment for `/chart AAPL 1m`.

**Documentation links:**
- discord.py: https://discordpy.readthedocs.io/en/stable/
- discord.py slash commands: https://discordpy.readthedocs.io/en/stable/interactions/api.html
- mplfinance: https://github.com/matplotlib/mplfinance

### [VALIDATE] Phase 13
In the Discord test server:
- `/predict AAPL` → embed with 4 horizon prediction cards
- `/price AAPL` → embed with current price and stats
- `/chart AAPL 1m` → candlestick chart image attached
- `/quota` → table of API quota status
- `/accuracy AAPL` → accuracy grid embed

---

## Phase 14 — Web Dashboard

**Goal:** React + Vite SPA running. Home page shows prediction cards. Ticker detail view with
candlestick chart and tabs. Real-time WebSocket updates working.

- [ ] 14.1 Initialize the web dashboard: `cd web_dashboard && npm create vite@latest . -- --template react-ts`
- [ ] 14.2 Install dependencies: `npm install @reduxjs/toolkit react-redux recharts @tanstack/react-query
       react-router-dom axios dayjs`
- [ ] 14.3 Configure TypeScript strict mode in `tsconfig.json`.
- [ ] 14.4 Set up Redux store: `src/store/index.ts` with RTK Query API slice.
- [ ] 14.5 Define all TypeScript interfaces in `src/types/` (Prediction, Ticker, SentimentScore,
       NewsArticle, Alert, WatchList, FeatureFlag, etc.).
- [ ] 14.6 Implement RTK Query endpoints in `src/api/` for all FastAPI endpoints.
- [ ] 14.7 Implement the Home page with the `WatchlistGrid` and `TickerCard` components.
- [ ] 14.8 Implement the `TickerDetailDrawer` with `CandlestickChart` (Recharts `ComposedChart`).
- [ ] 14.9 Implement all analysis tabs: Why, Sentiment, News, Reddit, Indicators, History.
- [ ] 14.10 Implement the `ConfigSlideout` for ticker configuration.
- [ ] 14.11 Implement the `Settings` page with alert config table, flag toggles, and quota gauges.
- [ ] 14.12 Implement the `Admin` section with all 25 paradigm demo panels.
- [ ] 14.13 Implement WebSocket connection in `src/store/websocket.ts` and update Redux state
        on price/prediction push messages.
- [ ] 14.14 Build for production: `npm run build` — verify bundle sizes are reasonable.
- [ ] 14.15 Serve the production build from FastAPI: `StaticFiles(directory="web_dashboard/dist")`.

**Documentation links:**
- Recharts: https://recharts.org/en-US/
- RTK Query: https://redux-toolkit.js.org/rtk-query/overview
- react-router-dom v6: https://reactrouter.com/en/main

### [VALIDATE] Phase 14
```bash
cd web_dashboard && npm run build
# Expected: build succeeds, no TypeScript errors

# Start FastAPI with static file serving
uvicorn app.main:app --port 8080
# Open http://localhost:8080 in browser
# Expected: web dashboard loads, prediction cards visible, ticker detail chart opens on click
```

---

## Phase 15 — Mobile App

**Goal:** React Native CLI bare workflow app running on iOS simulator or Android emulator.
Portfolio screen shows predictions. Push notifications receiving via OneSignal.

- [ ] 15.1 Set up React Native CLI environment:
       - Install JDK 17 and Android Studio (for Android)
       - Install Xcode 15+ (for iOS, Mac only)
       - Install `react-native-cli`: `npm install -g react-native@latest`
- [ ] 15.2 Initialize the project: `cd mobile_app && npx react-native init MarketPulseMobile --template react-native-template-typescript`
- [ ] 15.3 Install dependencies: `npm install @react-navigation/native @react-navigation/bottom-tabs
       react-native-screens react-native-safe-area-context react-native-vector-icons
       react-native-onesignal @tanstack/react-query axios dayjs`
- [ ] 15.4 Implement the Portfolio screen: fetches watchlist tickers with predictions from the
       FastAPI API and renders a `FlatList` of `PredictionCard` components.
- [ ] 15.5 Implement the Ticker Detail screen.
- [ ] 15.6 Configure OneSignal: follow the React Native SDK setup guide. iOS requires APNs
       certificate configuration.
- [ ] 15.7 Test push notification delivery: trigger a high-confidence prediction alert, verify
       the notification appears on the device.

**Documentation links:**
- React Native CLI setup: https://reactnative.dev/docs/environment-setup
- OneSignal React Native SDK: https://documentation.onesignal.com/docs/react-native-sdk

### [VALIDATE] Phase 15
- App builds and runs on simulator/emulator without errors.
- Portfolio screen shows at least one ticker with prediction data.
- OneSignal push notification received when manually triggered.

---

## Phase 16 — Voice Integrations

**Goal:** Local Alexa skill and local Google Home action both responding to test utterances.

- [ ] 16.1 **Alexa:**
       - Create an Alexa Developer account at https://developer.amazon.com/alexa/console/ask
       - Create a Custom Skill with the intents from README_2 Module 12.
       - Set the endpoint to your Cloudflare Tunnel URL + `/voice/alexa`.
       - Implement `voice/alexa_skill.py` using `ask-sdk-core`.
       - Set up Cloudflare Tunnel to expose the voice endpoint.
       - Test with the Alexa Developer Console simulator.
- [ ] 16.2 **Google Home:**
       - Create a Google Actions project at https://console.actions.google.com/
       - Implement `voice/google_action.py` using Flask as the fulfillment endpoint.
       - Set the fulfillment URL to your Cloudflare Tunnel URL + `/voice/google`.
       - Test with the Actions on Google simulator.

**Documentation links:**
- Alexa Skills Kit: https://developer.amazon.com/en-US/docs/alexa/alexa-skills-kit-sdk-for-python/overview.html
- Google Actions SDK: https://developers.google.com/assistant/actions/sdk

### [VALIDATE] Phase 16
- Alexa Developer Console: "What is the prediction for Apple?" → correct response
- Google Actions simulator: "What are today's alerts?" → correct response

---

## Phase 17 — RSS Bidirectional

**Goal:** RSS ingestion pipeline running. RSS publisher endpoint responding with valid RSS 2.0.

- [ ] 17.1 Verify RSS feed ingestion is already working from Phase 7 (RSS plugin was included).
- [ ] 17.2 Implement `app/api/rss.py` — the `GET /rss/predictions` endpoint that generates
       valid RSS 2.0 XML for all predictions with confidence ≥ 75% in the last 24 hours.
- [ ] 17.3 Validate the RSS output with https://validator.w3.org/feed/.

### [VALIDATE] Phase 17
```bash
curl http://localhost:8080/rss/predictions
# Expected: valid RSS 2.0 XML with at least one <item> for a recent high-confidence prediction
```

---

## Phase 18 — Data Export

**Goal:** All five export formats (CSV, PDF, JSON, NDJSON, XML) working from the web dashboard.

- [ ] 18.1 Implement `app/api/v1/export.py` — `GET /tickers/{symbol}/export?format=csv|pdf|json|xml|ndjson`
- [ ] 18.2 Implement CSV export using Python's `csv` module.
- [ ] 18.3 Implement PDF export using `reportlab` (header, prediction summary, candlestick chart image).
- [ ] 18.4 Implement JSON and NDJSON export using `StreamingResponse`.
- [ ] 18.5 Implement XML export.
- [ ] 18.6 Store all export files in MinIO `reports` bucket, return presigned URL.
- [ ] 18.7 Add "Export" button to the ticker detail page in the web dashboard.

---

## Phase 19 — Authentication and 2FA

**Goal:** Login flow complete. TOTP 2FA enrollment and verification working. SMS 2FA working
(optional — requires Twilio). Discord account linking working.

- [ ] 19.1 Implement user registration: `POST /auth/register` — hash password with bcrypt,
       create user in PostgreSQL, append to audit ledger.
- [ ] 19.2 Implement login: `POST /auth/login` — verify password, check 2FA enrollment,
       return either JWT (no 2FA) or `{requires_2fa: true}`.
- [ ] 19.3 Implement TOTP enrollment: `POST /auth/2fa/totp/enroll` — generate secret,
       return QR code image. `POST /auth/2fa/totp/verify` — verify first code, enable TOTP.
- [ ] 19.4 Implement `POST /auth/verify-2fa` — verify TOTP or SMS/email code, return JWT.
- [ ] 19.5 Implement JWT blocklist: `POST /auth/logout` — write `jti` to Valkey with TTL.
- [ ] 19.6 Implement Discord linking: OAuth2 flow linking a Discord account to a user record.
- [ ] 19.7 Verify the full auth flow with API tests.

---

## Phase 20 — Admin Paradigm Demo Panels

**Goal:** All 25 paradigm demo panels in the web dashboard are functional with live data.

- [ ] 20.1 Build each panel described in README_4 Part 1, panels 1–25.
- [ ] 20.2 Create backend endpoints for each panel as specified in README_4.
- [ ] 20.3 Verify each panel shows real data from the running system, not mock data.
- [ ] 20.4 Verify that the code excerpts shown in each panel are the actual production code
       (not pseudocode — pull from the live source files).

---

## Phase 21 — Security Hardening

**Goal:** All security controls from Category 18 of README_3 are implemented and tested.

- [ ] 21.1 Verify bcrypt work factor is 12 in the `passlib` configuration.
- [ ] 21.2 Verify JWT blocklist is checked on every protected endpoint.
- [ ] 21.3 Implement rate limiting middleware (100 req/min authenticated, 10 req/min anonymous).
- [ ] 21.4 Audit all database queries for parameterization (no string interpolation in SQL).
- [ ] 21.5 Run `bandit -r app/` (Python security linter) and fix any high-severity findings.
- [ ] 21.6 Verify the audit ledger hash chain is intact: `python -c "from app.db.embedded.audit_ledger import AuditLedgerRepository; r = AuditLedgerRepository(); print(r.verify_chain())"`
- [ ] 21.7 Set up HashiCorp Vault: install Vault locally, init and unseal, migrate all secrets
       from `.env` to Vault, update the application to read from Vault at startup.

---

## Phase 22 — Test Suite

**Goal:** Full test pyramid in place. Coverage ≥ 80% overall, ≥ 90% for ML and auth modules.

- [ ] 22.1 Verify all unit tests from previous phases are present and passing.
- [ ] 22.2 Add integration tests for each database repository (from Phase 4).
- [ ] 22.3 Add API tests for every FastAPI endpoint (from Phase 5).
- [ ] 22.4 Add ML backtesting (from Phase 11).
- [ ] 22.5 Add Hypothesis property-based tests for feature engineering.
- [ ] 22.6 Add Locust load test: simulate 50 concurrent users on `/tickers` and `/predictions`.
- [ ] 22.7 Add OPA policy tests (`opa test policies/`).
- [ ] 22.8 Run `mutmut run` on core modules and fix any surviving mutants.
- [ ] 22.9 Run `pytest --cov=app --cov-report=term-missing`. Identify any module below 80%
       and add tests until it passes.

### [VALIDATE] Phase 22
```bash
pytest tests/ --cov=app --cov-fail-under=80 -q
# Expected: all tests pass, coverage ≥ 80%
opa test policies/
# Expected: all policy tests pass
```

---

## Phase 23 — Seed Data

**Goal:** The system has 2 years of OHLCV history, seeded news, seeded Reddit posts, and
seeded predictions for 20 stock tickers and 5 crypto tickers. The seed data enables the
admin paradigm console to show real charts and real numbers.

**20 seed stock tickers:** AAPL, MSFT, GOOGL, AMZN, META, TSLA, NVDA, JPM, JNJ, WMT,
NFLX, BRKB, V, MA, DIS, PYPL, AMD, INTC, CRM, SPY

**5 seed crypto tickers:** BTC-USD, ETH-USD, SOL-USD, BNB-USD, ADA-USD

- [ ] 23.1 Create `scripts/seed_tickers.py` — insert all 25 tickers into PostgreSQL and ZODB.
- [ ] 23.2 Run the OHLCV ingestion pipeline for all 25 tickers with a 2-year lookback.
       `python -m arq app.workers.ohlcv_ingest --symbol ALL --since 2022-01-01`
- [ ] 23.3 Run indicator computation for all tickers.
- [ ] 23.4 Run 3 days of news and Reddit ingestion to seed documents.
- [ ] 23.5 Run the training pipeline for all 25 tickers. This will take significant time —
       run overnight.
- [ ] 23.6 Run the first full prediction run for all 25 tickers.
- [ ] 23.7 Create `scripts/seed_predictions.py` — insert 90 days of historical predictions
       with known accuracy stats (to enable accuracy panel to show meaningful data from day 1).
- [ ] 23.8 Add all 25 tickers to 3 default watchlists: "US Stocks", "Crypto", "Tech".

### [VALIDATE] Phase 23
```bash
# OHLCV rows for all 25 tickers
docker exec marketpulse-postgres psql -U marketpulse -d marketpulse \
    -c "SELECT symbol, count(*) as rows FROM ohlcv GROUP BY symbol ORDER BY symbol;"
# Expected: 25 rows, each with count > 400

# Predictions for all 25 tickers, all 4 horizons
docker exec marketpulse-postgres psql -U marketpulse -d marketpulse \
    -c "SELECT count(distinct symbol) as tickers, count(*) as predictions FROM predictions WHERE time > NOW() - INTERVAL '1 day';"
# Expected: tickers=25, predictions=100 (25 × 4 horizons)
```

---

## Phase 24 — Deployment to Proxmox

**Goal:** All three Proxmox nodes provisioned. Services migrated from local Docker Compose
to Proxmox. Argo CD managing deployments. Cloudflare Tunnel live.

- [ ] 24.1 Provision the three Proxmox VMs (manual step — set up Proxmox, create VMs).
- [ ] 24.2 Run Ansible playbooks to configure each node:
       `ansible-playbook ansible/playbooks/node1.yml`
- [ ] 24.3 Deploy databases to nodes using per-node Docker Compose files.
- [ ] 24.4 Push Docker images to a container registry (GitHub Container Registry: `ghcr.io/<you>/marketpulse`).
- [ ] 24.5 Create Kubernetes-style manifests in `deploy/` (or Docker Compose files per node).
- [ ] 24.6 Set up Argo CD on Node 1. Connect it to the Git repository.
- [ ] 24.7 Set up Cloudflare Tunnel on Node 1: `cloudflared tunnel create marketpulse`
- [ ] 24.8 Configure blue/green deployment for the FastAPI backend.
- [ ] 24.9 Configure canary deployment for the ML model (5% → 25% → 100% traffic ramp).
- [ ] 24.10 Migrate secrets from `.env` to HashiCorp Vault production instance.

---

## Phase 25 — Final Verification

**Goal:** Full smoke test on the production Proxmox deployment. All 216 paradigms observable
in the admin paradigm demo console. Performance benchmarks met.

- [ ] 25.1 **Smoke test:** For each of the 25 seed tickers:
       - Verify latest prediction exists and is not stale (within 24 hours)
       - Verify OHLCV data is current (latest row within 1 trading day)
       - Verify at least one sentiment score exists
       - Verify Discord `/predict {ticker}` returns a prediction
- [ ] 25.2 **All 216 paradigms:** Open the admin paradigm demo console. Work through all 25 panels.
       Each panel must show live data (not mock data) and produce a result without errors.
       Check off each paradigm in README_3 as verified.
- [ ] 25.3 **Performance:**
       - `GET /tickers/{symbol}/predictions` p99 < 200ms (warm, with Valkey cache)
       - ML prediction latency (gRPC call) p99 < 2s
       - OHLCV ingestion for 25 tickers completes < 5 minutes
       - Web dashboard loads (LCP) < 2s on first load
- [ ] 25.4 **Security:**
       - Verify Cloudflare Tunnel is the only external access point (no open ports on router)
       - Verify JWT blocklist works: login, get token, logout, verify 401 with same token
       - Verify OPA blocks admin panel access for non-admin user
       - Run `bandit -r app/ ml_sidecar/` — 0 high-severity findings
- [ ] 25.5 **Storage check:**
       - `df -h` on all three Proxmox nodes — all < 85% used
       - Verify MarketPulse's total storage across all nodes < 75GB total (well within budget)
- [ ] 25.6 Make a GitHub Release: `git tag v1.0.0 && git push --tags`

---

## Definition of Done

MarketPulse is done when all of the following are true:

1. All 25 phases complete with all VALIDATE gates passed.
2. All 25 admin paradigm demo panels show live data without errors.
3. All 216 sub-paradigms from README_3 are checked off as demonstrated.
4. The prediction system has generated at least 25 predictions (one per seed ticker) with
   confidence scores, and at least some outcomes have been resolved with accuracy computed.
5. All six alert delivery channels have each delivered at least one test notification.
6. The web dashboard, Discord bot, mobile app, and at least one voice integration are all
   reachable and returning correct data simultaneously.
7. The test suite runs with ≥ 80% coverage and 0 failures.
8. Storage on all nodes is < 85% used.
9. There are no known high-severity security issues (`bandit` clean, `opa test` passes).
10. The system runs for 24 hours unattended without any fatal errors.

When all ten conditions are true, MarketPulse is production-ready.
