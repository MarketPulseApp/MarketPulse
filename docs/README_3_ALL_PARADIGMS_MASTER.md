# MarketPulse — All Paradigms Master Reference

> This document lists every sub-paradigm across all 25 categories and maps each one to a
> specific MarketPulse feature. Use this as the authoritative checklist: every item on this list
> must be observable in the running system. The admin paradigm demo console (README_4) provides
> the live demonstration panel for each category.

**Total count: 216 sub-paradigms across 25 categories.**

---

## Category 1 — Versioning (9 sub-paradigms)

| # | Sub-Paradigm | What It Is | How MarketPulse Demonstrates It |
|---|-------------|-----------|--------------------------------|
| 1.1 | **Semantic versioning** | Major.Minor.Patch version numbering scheme | The FastAPI backend exposes `GET /version` returning `{"version": "1.0.0", "schema_version": "3"}`. The version is read from `pyproject.toml`. |
| 1.2 | **Database schema migration** | Incremental, versioned changes to database schema applied in order | Alembic manages all PostgreSQL schema changes. Each migration is a numbered Python file. Running `alembic upgrade head` applies all pending migrations in sequence. |
| 1.3 | **API versioning** | Versioning the HTTP API contract so old clients continue to work | FastAPI routes are prefixed with `/api/v1/`. When breaking changes are needed, `/api/v2/` routes are added alongside, not replacing, the v1 routes. |
| 1.4 | **Feature flag versioning** | Tracking which version of a feature is live | The `feature_flags` table includes an `updated_at` column. The admin console shows the last-changed timestamp for each flag, making flag state auditable. |
| 1.5 | **Model versioning** | Tracking which trained model version produced each prediction | Each LSTM/XGBoost/LightGBM model is saved to MinIO with a version key: `models/AAPL/lstm/v3/model.pt`. The `predictions` table stores `model_version` (e.g., `"ensemble-v3"`) so every prediction is traceable to the exact model that produced it. |
| 1.6 | **Configuration versioning** | Versioning application configuration to track changes | OPA policy files are versioned in Git. The `policies/` directory includes a `CHANGELOG.md` updated with every policy change. |
| 1.7 | **Protocol versioning** | Versioning the gRPC protobuf contract | The `.proto` file includes a `feature_schema_version` field in `PredictionRequest`. The ML sidecar validates that the version matches what it was trained on, rejecting mismatched feature vectors. |
| 1.8 | **Data format versioning** | Versioning serialized data to handle format evolution | Parquet files archived in MinIO include a `schema_version` metadata attribute. The DuckDB reader checks this version before querying and applies a migration function if the schema has changed since the file was written. |
| 1.9 | **Audit trail versioning** | Every state change has an immutable record with version | The SQLite audit ledger's SHA-256 hash chain creates an implicit version sequence — each row's `row_hash` covers the `prev_hash`, making the ledger's version history tamper-evident. |

---

## Category 2 — Configuration Management (7 sub-paradigms)

| # | Sub-Paradigm | What It Is | How MarketPulse Demonstrates It |
|---|-------------|-----------|--------------------------------|
| 2.1 | **Environment-based configuration** | Config values come from environment variables, not hardcoded | All secrets, connection strings, and tunable parameters come from `.env` files or environment variables, read by `pydantic-settings`. The `Settings` class validates and types every variable at startup. |
| 2.2 | **Configuration schema validation** | Config is validated against a schema at startup, not at use time | The `Settings` class uses Pydantic validators. If `POSTGRES_PASSWORD` is empty or `JWT_SECRET_KEY` is fewer than 32 characters, the application exits at startup with a descriptive error rather than failing later. |
| 2.3 | **Runtime feature flags** | Application behavior changes at runtime without restart | Feature flags stored in Valkey are read on every request. Flipping `flag:alert.sms` to `false` stops all SMS alerts within seconds — no restart, no deployment. |
| 2.4 | **Secrets management** | Sensitive credentials stored and accessed securely | HashiCorp Vault stores all production secrets. The FastAPI backend calls the Vault API at startup to fetch database passwords, API keys, and JWT secrets. In development, `.env` files are used as a Vault substitute. |
| 2.5 | **Hierarchical configuration** | Configuration has a precedence hierarchy (env > file > defaults) | `pydantic-settings` reads in order: environment variables first, then `.env.local`, then `.env`, then compiled-in defaults. This allows production to override dev values without touching files. |
| 2.6 | **Per-ticker configuration** | Fine-grained configuration at the entity level, not just globally | Each ticker has a per-ticker config object stored in the ZODB registry: which subreddits to monitor, FLAT band threshold, alert thresholds, which data sources to enable. Changing AAPL's config does not affect TSLA's. |
| 2.7 | **GitOps configuration** | Infrastructure configuration managed as code in a Git repository | Argo CD watches the `deploy/` directory in the Git repository. Changes to Kubernetes manifests or Helm values are applied automatically when merged to `main`. OPA policy changes are also in Git and applied by Argo CD. |

---

## Category 3 — Data Serialization (8 sub-paradigms)

| # | Sub-Paradigm | What It Is | How MarketPulse Demonstrates It |
|---|-------------|-----------|--------------------------------|
| 3.1 | **JSON** | Human-readable text serialization format | FastAPI serializes all REST API responses as JSON. Alert payloads stored in `notification_log.message` are JSON strings. Feature flag values in Valkey are JSON-encoded booleans. |
| 3.2 | **Protocol Buffers** | Binary serialization for gRPC | The ML sidecar uses `.proto` definitions for `PredictionRequest` and `PredictionResponse`. The binary encoding is 3–10× smaller than JSON equivalents and ~100× faster to serialize/deserialize. |
| 3.3 | **Parquet (columnar)** | Columnar binary format optimized for analytical queries | OHLCV data is archived nightly to MinIO as Parquet files. DuckDB reads these files directly — columnar format allows "SELECT close FROM ohlcv WHERE symbol='AAPL'" to read only the close column, skipping all other columns. |
| 3.4 | **CSV** | Flat-file tabular format | Data export module produces CSV for OHLCV, predictions, and sentiment data. CSV is the most universally importable format for Excel, Google Sheets, and trading platforms. |
| 3.5 | **XML** | Structured text format with schema validation | The RSS publisher produces valid RSS 2.0 XML. Data export produces XML with XSD schema for machine-readable consumption. The SEC EDGAR XBRL API returns financial data as XML/XBRL — the ingestion pipeline parses it. |
| 3.6 | **MessagePack** | Compact binary replacement for JSON | Valkey pub/sub messages (price updates, prediction changes) are serialized with MessagePack for compact binary transmission to WebSocket clients. The web dashboard deserializes them with the `msgpack` JS library. |
| 3.7 | **Pickle (with version control)** | Python object serialization | ZODB persists `StockTicker` and `CryptoTicker` Python objects using the `zodbpickle` library. The `feature_schema_version` in the gRPC proto guards against model/feature schema mismatches that Pickle cannot detect on its own. |
| 3.8 | **NDJSON (newline-delimited JSON)** | Streaming JSON format, one JSON object per line | The bulk JSON export produces NDJSON rather than a JSON array, allowing streaming download of large datasets without buffering the entire response in memory. The ingestion pipeline also accepts NDJSON for bulk data ingest. |

---

## Category 4 — Authorization / Access Control (7 sub-paradigms)

| # | Sub-Paradigm | What It Is | How MarketPulse Demonstrates It |
|---|-------------|-----------|--------------------------------|
| 4.1 | **Role-Based Access Control (RBAC)** | Permissions tied to roles (user, admin), not individuals | JWT payload includes a `roles` claim. OPA policies check `input.user.roles` — admin-only endpoints (quota reset, flag toggle, paradigm console) require the `admin` role. Regular users have `user` role. |
| 4.2 | **Attribute-Based Access Control (ABAC)** | Permissions based on attributes of the subject and resource | OPA policy for watchlist access: a user can only read or modify a watchlist if `input.resource.user_id == input.user.id`. This is attribute-based (the resource attribute must match the subject attribute), not purely role-based. |
| 4.3 | **Policy as code (OPA/Rego)** | Authorization rules expressed as code, versioned in Git | All policies live in `policies/*.rego`. Example: `allow if { input.method == "GET"; data.feature_flags[input.resource] == true }`. Policies are tested with `opa test`. |
| 4.4 | **JWT authentication** | Stateless bearer token authentication | Access tokens are signed JWTs verified by FastAPI middleware on every protected request. The `jose` library signs with HS256. Token expiry and blocklist check happen in the auth middleware. |
| 4.5 | **Scope-based API authorization** | Specific API endpoints require specific scopes | The OPA policy for admin operations requires `"admin" in input.user.roles`. The policy for the Discord bot's internal API (called by the bot process) requires `"bot_client"` in the roles claim. |
| 4.6 | **2FA enforcement** | Multi-factor authentication as an authorization gate | The `/auth/verify-2fa` endpoint is the second authorization gate after password verification. The 2FA code is a time-bounded credential: TOTP codes are valid for 30 seconds (with 1-step tolerance), SMS codes for 5 minutes. |
| 4.7 | **API key authentication** | Service-to-service authentication with static keys | The ML sidecar's gRPC server validates an `Authorization` metadata header on every RPC call. The FastAPI backend passes this key when calling the sidecar. This prevents any unauthorized process from calling the prediction service. |

---

## Category 5 — Observability (7 sub-paradigms)

| # | Sub-Paradigm | What It Is | How MarketPulse Demonstrates It |
|---|-------------|-----------|--------------------------------|
| 5.1 | **Metrics (Prometheus)** | Numeric time-series measurements of system behavior | Every FastAPI endpoint exports request count, latency histogram, and error rate via `prometheus-client`. ARQ workers export task queue depth and task processing time. All metrics scraped by Prometheus at `GET /metrics`. |
| 5.2 | **Dashboards (Grafana)** | Visual display of metrics over time | Grafana dashboards pre-provisioned: (1) API request latency by endpoint, (2) ARQ worker queue depth over time, (3) ML prediction latency histogram, (4) database connection pool usage, (5) API quota gauges per source. |
| 5.3 | **Distributed tracing (Jaeger)** | Correlating spans across multiple services | Every FastAPI request starts a trace span. When it calls the ML sidecar via gRPC, the trace context is propagated via gRPC metadata. Jaeger shows the full trace: FastAPI → feature assembly → gRPC call → prediction response → database write. |
| 5.4 | **Structured logging (Loki)** | JSON-formatted logs aggregated into a searchable store | All application logs use `structlog` with JSON output: `{"event": "ohlcv_ingested", "symbol": "AAPL", "rows": 1, "latency_ms": 43, "timestamp": "..."}`. Loki aggregates these; Grafana queries them with LogQL. |
| 5.5 | **Health checks** | Standardized endpoints that report service readiness | FastAPI exposes `GET /health` (liveness) and `GET /ready` (readiness — checks all database connections). Docker Compose `healthcheck` entries call these. The ML sidecar exposes `gRPC HealthCheck` per the standard gRPC health protocol. |
| 5.6 | **Alerting (alert rules in Prometheus)** | Automated alerts based on metric thresholds | Prometheus alert rules fire when: API request error rate > 5%, ML prediction latency p99 > 2s, disk usage > 80%, any database connection pool exhausted. Alerts route through Alertmanager → Discord channel. |
| 5.7 | **SLO tracking** | Service Level Objective measurement | The admin console displays computed SLOs: "Prediction latency < 2s: 99.2% of the last 1000 requests" and "OHLCV ingestion success rate: 98.7% over the last 7 days." SLO data is stored in PostgreSQL and queried by the dashboard. |

---

## Category 6 — State Management (8 sub-paradigms)

| # | Sub-Paradigm | What It Is | How MarketPulse Demonstrates It |
|---|-------------|-----------|--------------------------------|
| 6.1 | **Redux Toolkit** | Centralized, predictable state management for React | Web dashboard uses Redux Toolkit with RTK Query for all server state. Each ticker's prediction, price, and sentiment are stored in typed Redux slices. DevTools show every state change. |
| 6.2 | **Optimistic updates** | UI updates immediately before server confirms success | When a user adds a ticker to a watchlist in the dashboard, the ticker card appears immediately in the UI (optimistic), then the POST request is sent. If the server returns an error, the card is removed (rollback). |
| 6.3 | **Server-sent events / WebSocket** | Pushing state changes from server to client in real-time | FastAPI WebSocket endpoint pushes price and prediction updates to the web dashboard. Mobile app receives push notifications (a different state update channel — see 6.4). |
| 6.4 | **Push state (OneSignal)** | State delivered proactively to mobile/browser without polling | OneSignal delivers prediction change notifications to the mobile app and browser. This replaces the need for the mobile app to poll for changes — the server pushes when state changes. |
| 6.5 | **Pub/sub state propagation** | State changes broadcast to multiple consumers via pub/sub | Valkey pub/sub propagates new predictions: the WebSocket handler, the alert evaluator, the Discord bot, and the voice integration all subscribe to `pubsub:price_updates`. A single state change fans out to all four consumers. |
| 6.6 | **Materialized view / cache** | Pre-computed results stored for fast reads | The dashboard "current summary" view reads from DuckDB in-memory materialized aggregations, not from raw TimescaleDB queries. The materialized view is refreshed on every prediction update, keeping reads instant. |
| 6.7 | **Event sourcing** | State reconstructed from an append-only event log | The SQLite event journal is a partial event-sourcing implementation: every prediction, alert, and training run is appended. The total accuracy of a ticker's predictions can be recomputed from the event journal alone, independent of the `predictions` table. |
| 6.8 | **React Native state** | Mobile app state management with React hooks | Mobile app uses `useState` and `useReducer` for local component state, and `@tanstack/react-query` for server cache state (prediction cards, news feed). No Redux in the mobile app — lighter, more appropriate for the read-only use case. |

---

## Category 7 — Compilation / Execution (7 sub-paradigms)

| # | Sub-Paradigm | What It Is | How MarketPulse Demonstrates It |
|---|-------------|-----------|--------------------------------|
| 7.1 | **TypeScript compilation** | Static type-checking and transpilation to JavaScript | Web dashboard is written in TypeScript, compiled by Vite's esbuild pipeline. `tsc --noEmit` runs in CI to catch type errors before the build step. |
| 7.2 | **Python bytecode compilation** | Python source compiled to .pyc bytecode by CPython | Standard Python behavior. The FastAPI backend is packaged as a Docker image with `python -O` optimization flag (removes assert statements, optimizes bytecode) in production builds. |
| 7.3 | **ONNX runtime inference** | Models compiled to a portable inference format and run without the training framework | XGBoost and LightGBM models are exported to ONNX format after training. On the ML sidecar, `onnxruntime` runs these models — no XGBoost or LightGBM installation needed in the inference container. This reduces the inference container image size by ~500MB. |
| 7.4 | **PyTorch JIT (TorchScript)** | PyTorch model traced/scripted to a portable executable format | The LSTM model is exported with `torch.jit.trace()` after training, producing a TorchScript model that can be loaded with `torch.jit.load()` without the training code. Enables deployment to environments without the full PyTorch training stack. |
| 7.5 | **esbuild (via Vite)** | Ultra-fast JavaScript/TypeScript bundler | Vite uses esbuild for development mode (instant hot reload) and Rollup for production builds. The production build produces a single optimized JS bundle + CSS, serving the entire web dashboard from three files. |
| 7.6 | **gRPC code generation** | RPC stubs generated from .proto definitions | Running `python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. prediction.proto` generates `prediction_pb2.py` and `prediction_pb2_grpc.py`. These generated files are the client and server stubs — never edited manually. |
| 7.7 | **React Native Metro bundler** | JavaScript bundler for React Native | Metro bundles the React Native mobile app's JavaScript into a single bundle loaded by the native runtime. In development, Metro serves the bundle live with fast refresh. In production, the bundle is embedded in the app binary. |

---

## Category 8 — Type System (8 sub-paradigms)

| # | Sub-Paradigm | What It Is | How MarketPulse Demonstrates It |
|---|-------------|-----------|--------------------------------|
| 8.1 | **Pydantic models (runtime type validation)** | Python data validation at runtime with type annotations | Every FastAPI request and response body is a Pydantic `BaseModel`. Invalid types (e.g., sending a string where a float is expected for `confidence`) return a 422 error with the field path and expected type. |
| 8.2 | **TypeScript interfaces** | Static type contracts in the frontend codebase | Every API response type is defined as a TypeScript interface in `src/types/`. RTK Query endpoints are generic over these interfaces. The compiler catches mismatches between API response shapes and UI component props. |
| 8.3 | **Python dataclasses** | Lightweight typed data containers | Internal data transfer objects (e.g., `FeatureVector`, `NewsArticle`, `IngestRecord`) use Python `@dataclass` for structured, typed containers without the full Pydantic overhead. |
| 8.4 | **Generic types** | Type-parameterized containers and functions | The FastAPI `PaginatedResponse[T]` response model is a generic: `class PaginatedResponse(BaseModel, Generic[T]): items: list[T]; total: int; page: int`. The same wrapper works for `PaginatedResponse[PredictionSchema]` and `PaginatedResponse[NewsArticleSchema]`. |
| 8.5 | **Discriminated unions** | Tagged unions that select type based on a discriminator field | Pydantic `ticker_type` discriminator: `Annotated[Union[StockTickerSchema, CryptoTickerSchema], Field(discriminator="asset_type")]`. Tickers with `asset_type="stock"` parse as `StockTickerSchema`; `asset_type="crypto"` as `CryptoTickerSchema`. |
| 8.6 | **Literal types** | Types constrained to specific string or numeric values | `direction: Literal["UP", "FLAT", "DOWN"]` in the prediction schema. `horizon: Literal["1d", "3d", "7d", "30d"]`. TypeScript: `type AlertChannel = "browser" | "mobile" | "email" | "sms" | "discord" | "voice"`. |
| 8.7 | **Protocol Buffers typed schema** | Binary serialization with enforced field types | `.proto` file defines field types: `string symbol = 1`, `repeated float feature_vector = 2`, `float confidence = 3`. The gRPC framework enforces these types — a client cannot send a string where a float is expected without explicit conversion. |
| 8.8 | **OPA Rego typed rules** | Policy language with implicit type checking | OPA's Rego is type-inferred. `input.user.roles` must be a set for `"admin" in input.user.roles` to evaluate correctly. The `opa check` command statically validates types in policy files. |

---

## Category 9 — Memory Management (8 sub-paradigms)

| # | Sub-Paradigm | What It Is | How MarketPulse Demonstrates It |
|---|-------------|-----------|--------------------------------|
| 9.1 | **Python garbage collection** | Automatic memory reclamation by CPython's reference counter + cyclic collector | Standard Python GC manages all FastAPI and ingestion worker objects. `gc.collect()` is called explicitly after large batch operations (e.g., processing 1000 news articles at once) to reclaim memory immediately. |
| 9.2 | **Connection pooling** | Reusing database connections rather than creating new ones per request | `asyncpg` connection pool: min 5, max 20 connections. `motor` (MongoDB) connection pool: max 10. Elasticsearch `AsyncElasticsearch` maintains its own pool. Connection reuse is the single biggest performance optimization for database-heavy code. |
| 9.3 | **In-process caching with LRU eviction** | Bounded in-memory cache that evicts least-recently-used items | `functools.lru_cache` caches the company-name-to-ticker lookup table (built from the ticker registry at startup) with `maxsize=10000`. The Valkey client's connection pool inherits Python's `allkeys-lru` eviction. |
| 9.4 | **Streaming large responses** | Processing large data sets without loading them into memory** | The NDJSON export endpoint uses FastAPI's `StreamingResponse` with a Python generator: each row is serialized and yielded one at a time. A 1M-row OHLCV export never loads more than one row into memory. |
| 9.5 | **Chunked batch processing** | Processing large datasets in fixed-size chunks | The nightly model retraining processes OHLCV history in 1000-row chunks using pandas `chunksize`. The news FinBERT scoring job processes articles in batches of 16 (the maximum GPU batch size that fits in 8GB VRAM locally). |
| 9.6 | **Valkey memory limit with eviction** | Redis-compatible key-value store with a memory cap and eviction policy | Valkey is configured with `--maxmemory 512mb --maxmemory-policy allkeys-lru`. When the 512MB cap is reached, Valkey evicts the least recently used key. This prevents Valkey from consuming unbounded memory as the price cache grows. |
| 9.7 | **NumPy memory layout** | Efficient contiguous memory arrays for numerical computation | The `ta` library and the ML feature engineering pipeline operate on NumPy arrays. All feature vectors are `float32` (not float64) to halve memory usage. The LSTM input tensor uses contiguous C-order memory layout for CUDA efficiency. |
| 9.8 | **DuckDB in-memory lifecycle** | In-memory database reclaimed when the process restarts | The DuckDB in-memory instance is intentionally ephemeral — it is populated from Valkey caches and Parquet files at startup. Restarting the FastAPI process re-populates it. This means the in-memory state is always consistent with persistent storage, not a separate source of truth. |

---

## Category 10 — AI / ML (10 sub-paradigms)

| # | Sub-Paradigm | What It Is | How MarketPulse Demonstrates It |
|---|-------------|-----------|--------------------------------|
| 10.1 | **LSTM (sequence modeling)** | Recurrent neural network for sequential data patterns | LSTM model takes a 30-day sliding window of OHLCV returns and technical indicator values as a sequence, outputs a probability distribution over [UP, FLAT, DOWN] for each prediction horizon. Implemented in PyTorch. |
| 10.2 | **Gradient boosting (XGBoost + LightGBM)** | Ensemble of decision trees trained sequentially to correct previous trees' errors | XGBoost and LightGBM both take the full feature vector (not a sequence) as input and output class probabilities. Having both provides ensemble diversity since they use different boosting strategies. |
| 10.3 | **Transfer learning (FinBERT)** | Using a pre-trained model and fine-tuning on domain-specific data | FinBERT is BERT pre-trained on general text by Google, then fine-tuned on financial news by Prosus. MarketPulse uses the HuggingFace `ProsusAI/finbert` checkpoint without further fine-tuning — it is used as a zero-shot financial sentiment classifier. |
| 10.4 | **Rule-based NLP (VADER)** | Sentiment analysis using a dictionary of sentiment words and rules | VADER applies a lexicon of ~7500 words with pre-assigned sentiment scores plus rules for capitalization, punctuation (!!!), and negation. Runs at ~10,000 texts/second — suitable for real-time Reddit scoring as posts arrive. |
| 10.5 | **Ensemble model** | Combining multiple model outputs into a single prediction | The ensemble model takes the output probabilities from LSTM, XGBoost, LightGBM, and FinBERT and computes a weighted average. Weights are learned per ticker per horizon using a meta-learner (logistic regression on the validation set). |
| 10.6 | **Anomaly detection (Isolation Forest)** | Detecting observations that are statistically anomalous | `IsolationForest` from scikit-learn is fit on the historical feature vectors for each ticker. At inference time, a new feature vector is scored — if it falls in the anomaly region (isolation score < threshold), the prediction is flagged as "anomaly — unusual input." |
| 10.7 | **Feature engineering** | Transforming raw data into model-ready numeric features | The feature engineering pipeline converts raw OHLCV values → log returns, raw sentiment scores → z-score normalized sentiment, days-until-earnings → bucket encoding, correlation coefficients → binned buckets. Raw prices are never fed to models directly. |
| 10.8 | **Incremental learning** | Updating a trained model with new data without full retraining | XGBoost and LightGBM support `xgb_model=existing_model` for incremental boosting rounds. The LSTM uses an online update with a small learning rate on the new day's data only. This keeps models current without nightly full-retraining (which would take hours at full history size). |
| 10.9 | **Model calibration** | Aligning model output probabilities with actual empirical frequencies | Raw XGBoost/LightGBM probabilities are uncalibrated. The pipeline applies `sklearn.calibration.CalibratedClassifierCV` using isotonic regression, so a model output of 0.8 (80% confidence) actually corresponds to ~80% observed accuracy. |
| 10.10 | **SHAP explainability** | Computing the marginal contribution of each feature to a prediction | After each ensemble prediction, SHAP (SHapley Additive Explanations) computes the contribution of each feature to the final direction. The `prediction_explanations` MongoDB document stores the top 10 most influential features and their SHAP values. The dashboard "why" panel displays these. |

---

## Category 11 — Storage (8 sub-paradigms)

| # | Sub-Paradigm | What It Is | How MarketPulse Demonstrates It |
|---|-------------|-----------|--------------------------------|
| 11.1 | **Relational (PostgreSQL)** | ACID-compliant row-oriented relational database | Users, tickers, watchlists, alert configs, quota tracking, and notification log stored in PostgreSQL with foreign keys, constraints, and JOIN queries. |
| 11.2 | **Time-series (TimescaleDB)** | Database optimized for time-ordered data with automatic partitioning | OHLCV, predictions, sentiment scores, and technical indicators stored in TimescaleDB hypertables. `time_bucket` aggregations power the dashboard charts. |
| 11.3 | **Document (MongoDB)** | Schema-flexible document storage | News articles (varying fields per source), Reddit posts (nested comments), SEC filings, and prediction explanations stored in MongoDB collections. |
| 11.4 | **Key-value (Valkey)** | Fast in-memory key-value store with TTL | Sessions, feature flags, API quota counters, price caches, and pub/sub messaging. |
| 11.5 | **Vector (ChromaDB)** | Database for high-dimensional embeddings with similarity search | News deduplication, Reddit post clustering, and prediction feature anomaly proximity. |
| 11.6 | **Object storage (MinIO)** | S3-compatible blob storage for arbitrary binary objects | Chart images, exported reports, ML model binaries, OHLCV Parquet archives. |
| 11.7 | **Columnar (DuckDB + Parquet)** | Column-oriented format for analytical query efficiency | DuckDB queries Parquet archives for long-term accuracy trend analysis, reading only the relevant columns. |
| 11.8 | **Full-text search (Elasticsearch)** | Inverted-index search over text content | Full-text search across all news articles and Reddit posts by keyword, ticker, date range, and sentiment band. |

---

## Category 12 — Modeling (7 sub-paradigms)

| # | Sub-Paradigm | What It Is | How MarketPulse Demonstrates It |
|---|-------------|-----------|--------------------------------|
| 12.1 | **Object-oriented inheritance (ZODB)** | Class hierarchies with inherited behavior | `StockTicker` and `CryptoTicker` inherit from `Ticker`. The `Ticker` base class has common fields (symbol, name, subreddits, alert_configs). Each subclass adds type-specific fields (StockTicker: exchange, sector; CryptoTicker: chain, coingecko_id). |
| 12.2 | **Graph modeling (Neo4j)** | Representing entities and their relationships as nodes and edges | Ticker nodes connected by `MEMBER_OF` (sector/index), `SUPPLIER_OF`, `CUSTOMER_OF`, `CORRELATED_WITH`, `INSIDER_BOUGHT`/`SOLD`, and `ETF_HOLDS` relationships. |
| 12.3 | **Multi-model (SurrealDB)** | Single database expressing relational, document, and graph structures simultaneously | SurrealDB stores ticker records (table), news articles (document), and sector membership (graph edges) in one query engine, enabling cross-model JOINs that would require three separate databases otherwise. |
| 12.4 | **Entity-relationship modeling** | Formal specification of entity types and their relationships | The PostgreSQL schema explicitly models the ER diagram: `users` → `watchlists` → `watchlist_tickers` → `tickers`. Foreign keys enforce referential integrity. The ER diagram is in the `docs/` directory. |
| 12.5 | **Wide-column modeling (Cassandra)** | Data modeled around query patterns, not entity normalization | Cassandra `api_call_log` is modeled around its query pattern: "give me all calls to source X on date Y, sorted by time." The primary key `(source_name, call_date)` + clustering key `call_time` enables this query in O(log N). |
| 12.6 | **Object-document mapping (ODM)** | Mapping Python objects to MongoDB documents | `motor` with `beanie` ODM maps Python dataclasses to MongoDB documents. `@Document` annotated classes handle serialization/deserialization, type coercion, and index management. |
| 12.7 | **Domain model** | Rich Python objects representing business concepts | The domain model (Phase 3 of the build guide) defines `Ticker`, `Prediction`, `Alert`, `WatchList`, `SentimentScore`, `NewsArticle`, `RedditPost`, `APIQuota`, `NotificationPreference` as Python dataclasses with behavior methods (e.g., `Prediction.is_actionable()`, `Alert.should_fire()`). |

---

## Category 13 — Concurrency (8 sub-paradigms)

| # | Sub-Paradigm | What It Is | How MarketPulse Demonstrates It |
|---|-------------|-----------|--------------------------------|
| 13.1 | **Python asyncio** | Native asynchronous I/O for concurrent coroutines | The FastAPI backend is entirely async. Database queries, HTTP calls to external APIs, and Valkey operations all use `await`. A single worker process handles hundreds of concurrent requests without threads. |
| 13.2 | **ARQ task queue** | Background task execution with worker processes | All ingestion, training, and notification tasks run as ARQ background jobs. Multiple ARQ worker processes run concurrently, pulling tasks from Valkey queues. |
| 13.3 | **gRPC streaming** | Bidirectional streaming RPC for continuous data flow | The ML sidecar exposes a `PredictStream` RPC that accepts a stream of `PredictionRequest`s and returns a stream of `PredictionResponse`s. Used during batch prediction runs (nightly rerun of all active tickers) to pipeline requests. |
| 13.4 | **Asyncio task groups** | Structured concurrency for parallel async operations | Feature assembly for multiple tickers runs with `asyncio.gather()`: `results = await asyncio.gather(*[assemble_features(sym) for sym in symbols])`. Assembles features for all 25 tickers concurrently instead of sequentially. |
| 13.5 | **Rate limiting (async)** | Throttling concurrent operations to respect API rate limits | The Polygon.io plugin implements an async semaphore-based rate limiter: `async with polygon_semaphore: result = await polygon_client.get(...)`. The semaphore allows at most 5 concurrent calls, matching the 5-calls/min free tier limit. |
| 13.6 | **WebSocket concurrency** | Managing multiple simultaneous WebSocket connections | The FastAPI WebSocket endpoint uses an `asyncio.Queue` per connected client. A background coroutine reads from Valkey pub/sub and puts messages into all connected clients' queues. Each WebSocket send is awaited independently, so slow clients do not block fast ones. |
| 13.7 | **Thread pool for CPU-bound tasks** | Offloading CPU-bound work from the async event loop | TA-Lib indicator computation and pandas DataFrame operations are CPU-bound. They are offloaded to a thread pool with `asyncio.to_thread()`, freeing the event loop to handle requests while indicators are computed. |
| 13.8 | **Process-based isolation (gRPC sidecar)** | Isolating heavy computation in a separate process | The ML sidecar runs as a completely separate Python process. This means a memory leak or crash in the ML process does not take down the FastAPI backend. The process boundary is the strongest isolation available in Python (separate GIL). |

---

## Category 14 — Networking (9 sub-paradigms)

| # | Sub-Paradigm | What It Is | How MarketPulse Demonstrates It |
|---|-------------|-----------|--------------------------------|
| 14.1 | **REST API (FastAPI)** | Resource-oriented HTTP API with standard verbs | The FastAPI backend exposes a complete REST API: `GET /tickers`, `POST /tickers`, `GET /tickers/{symbol}/predictions`, `GET /tickers/{symbol}/sentiment`, etc. |
| 14.2 | **gRPC** | Binary RPC protocol with code-generated stubs | FastAPI → ML sidecar communication uses gRPC. The prediction call is a standard unary RPC; batch prediction uses client-streaming RPC. |
| 14.3 | **WebSocket** | Full-duplex persistent connection for real-time updates | The web dashboard connects to `ws://api/ws/price-updates` for real-time prediction and price push. |
| 14.4 | **Cloudflare Tunnel** | Exposing local services to the internet without port forwarding | `cloudflared tunnel run` exposes the FastAPI backend and Alexa/Google Home fulfillment endpoints on a `*.trycloudflare.com` or custom domain URL, with zero router configuration. |
| 14.5 | **Cloudflare Workers** | Serverless edge functions handling webhooks | OneSignal delivery receipts, Reddit push notifications, and Twilio SMS callbacks are received at Cloudflare Workers, which validate the signature and forward to the FastAPI internal webhook endpoint. |
| 14.6 | **mTLS (Astra Cassandra)** | Mutual TLS for service authentication | The DataStax Astra Secure Connect Bundle includes client certificates. The Cassandra driver presents these certificates when connecting — both client and server authenticate each other, not just the server authenticating to the client. |
| 14.7 | **SMTP** | Email delivery protocol | Email alerts use `aiosmtplib` to connect to a configured SMTP server (e.g., Gmail SMTP, Mailgun SMTP). Supports STARTTLS. |
| 14.8 | **Discord Gateway WebSocket** | Discord bot's persistent event stream | `discord.py` maintains a persistent WebSocket connection to the Discord gateway. Slash command interactions are delivered over this connection. |
| 14.9 | **Bolt protocol (Neo4j)** | Neo4j's binary graph query protocol | The Neo4j Python driver communicates with AuraDB over the Bolt protocol (binary, encrypted with TLS). This is the native protocol for the Neo4j driver — not HTTP. |

---

## Category 15 — Testing (10 sub-paradigms)

| # | Sub-Paradigm | What It Is | How MarketPulse Demonstrates It |
|---|-------------|-----------|--------------------------------|
| 15.1 | **Unit tests (pytest)** | Isolated tests of individual functions with mocked dependencies | All pure functions (feature engineering, technical indicator computation, sentiment score aggregation, hash-chain computation) have unit tests with `pytest`. No database or network calls in unit tests — all dependencies are mocked. |
| 15.2 | **Integration tests** | Tests verifying that multiple components work together | Integration tests for the OHLCV ingestion pipeline use a real PostgreSQL container (via `testcontainers-python`) and verify that a full ingest → indicator → cache cycle completes correctly. |
| 15.3 | **API tests (pytest + httpx)** | Testing FastAPI endpoints end-to-end | The full FastAPI app is tested with `httpx.AsyncClient` in pytest. Tests verify response schemas, error codes, and auth enforcement. Uses an in-memory SQLite database instead of PostgreSQL for speed. |
| 15.4 | **ML backtesting** | Evaluating ML model performance on held-out historical data | The `backtest.py` script trains a model on OHLCV data from 2020-2022, then evaluates it on 2023 data (never seen during training). Reports accuracy, F1 per class, and calibration metrics. This is the gate for model promotion to production. |
| 15.5 | **Property-based testing (Hypothesis)** | Generating random inputs to find edge cases automatically | `hypothesis` generates random `FeatureVector` inputs to `assemble_features()` to verify it never crashes, always returns a valid vector, and always produces values within expected ranges. |
| 15.6 | **Mutation testing** | Verifying that tests fail when code is subtly broken | `mutmut` mutates the business logic in `prediction.py` (e.g., changing `>=` to `>`, swapping `UP` and `DOWN`) and verifies that at least one test fails for each mutation. If a mutation survives, the test suite is incomplete. |
| 15.7 | **Load testing (Locust)** | Simulating many concurrent users to find performance bottlenecks | `locust` scripts simulate 100 concurrent users hitting `/tickers/{symbol}/predictions`. The test verifies that p99 latency stays below 500ms and that no database connection pool exhaustion occurs. |
| 15.8 | **Contract testing** | Verifying that the API client and server agree on the interface | The gRPC `.proto` file is the contract. `buf lint` and `buf breaking` (in CI) verify that no breaking changes are made to the proto without a version bump. |
| 15.9 | **Snapshot testing** | Comparing output against a known-good saved snapshot | Discord embed output is snapshot-tested: the rendered embed JSON for `/predict AAPL` is compared against a saved snapshot. If the embed format changes, the snapshot test fails and must be explicitly updated. |
| 15.10 | **OPA policy testing** | Testing authorization policies in isolation | `opa test policies/` runs all `.rego` test files. Tests verify: admin can access admin panel, non-admin cannot, anonymous user cannot access any protected endpoint, bot_client role can call internal endpoints. |

---

## Category 16 — Deployment / Infrastructure (9 sub-paradigms)

| # | Sub-Paradigm | What It Is | How MarketPulse Demonstrates It |
|---|-------------|-----------|--------------------------------|
| 16.1 | **Docker containerization** | Packaging services and their dependencies as portable containers | Every service (FastAPI, ML sidecar, Discord bot, ARQ workers) runs in a Docker container. `docker-compose.yml` defines the complete local stack. |
| 16.2 | **Docker Compose** | Multi-container local development orchestration | The `docker-compose.yml` in README_1 defines all 17 databases + application services. One `docker compose up -d` starts everything. |
| 16.3 | **GitOps (Argo CD)** | Infrastructure state managed via Git; Argo CD syncs cluster to Git state | Argo CD watches the `deploy/` directory. Merging to `main` triggers automatic deployment to the Proxmox nodes. Manual `kubectl apply` is never used in production. |
| 16.4 | **CI/CD (GitHub Actions)** | Automated test → build → deploy pipeline on every push | Pushing to any branch runs unit tests. Merging to `main` runs the full test suite, builds Docker images, pushes to the container registry, and triggers Argo CD sync. |
| 16.5 | **Blue/green deployment** | Running two production environments and switching traffic between them | FastAPI backend deploys to a Blue environment; traffic switches to Green only after health checks pass. If Green fails, traffic reverts to Blue with zero downtime. Managed by Argo CD Rollouts. |
| 16.6 | **Canary deployment for ML models** | Gradually routing prediction traffic to a new model version | New ML model versions receive 5% of prediction traffic first. If accuracy on the canary slice is at least as good as the main model, traffic increases to 25%, then 100%. Managed by a custom canary controller in the ML sidecar. |
| 16.7 | **Ansible provisioning** | Automated server configuration management | `ansible/playbooks/` contains playbooks for provisioning each Proxmox node: installing Docker, creating directories, setting up systemd services for Argo CD agents, and configuring firewall rules. |
| 16.8 | **HashiCorp Vault** | Secrets management and dynamic secret generation | Production secrets are stored in Vault. The FastAPI backend uses the Vault Agent Sidecar to authenticate (via Kubernetes service account) and receive rotated database credentials without restarting. |
| 16.9 | **Proxmox virtualization** | Self-hosted bare-metal hypervisor for virtual machines | The three Proxmox nodes run as VMs on Proxmox, each with allocated RAM and storage. Proxmox provides live migration, snapshots, and resource monitoring for the production MarketPulse environment. |

---

## Category 17 — UI / Frontend (9 sub-paradigms)

| # | Sub-Paradigm | What It Is | How MarketPulse Demonstrates It |
|---|-------------|-----------|--------------------------------|
| 17.1 | **React SPA** | Single-page application with client-side routing | The web dashboard is a React SPA using `react-router-dom` v6. Navigation between ticker detail, watchlists, settings, and the admin console never reloads the page. |
| 17.2 | **React Native** | Cross-platform mobile app with native rendering | The mobile app renders real native iOS and Android components (not WebView). The bare workflow gives direct access to native modules for OneSignal push. |
| 17.3 | **Recharts** | Declarative SVG chart library for React | Candlestick charts: `ComposedChart` with `Bar` (OHLC encoded as bar geometry), `Line` (SMA/EMA overlays), and `ReferenceLine` (support/resistance). Sentiment charts: `LineChart`. Accuracy charts: `RadarChart`. |
| 17.4 | **Progressive disclosure** | Showing information in layers, from summary to detail | Dashboard home: prediction direction only. Clicking a card: candlestick + prediction row. Expanding tabs: full indicator list. Clicking gear icon: full configuration panel. No information is hidden — it is progressively revealed. |
| 17.5 | **Responsive design** | UI adapts to different screen sizes | The web dashboard uses CSS Grid with responsive breakpoints. At mobile viewport width, the watchlist switches from a 3-column card grid to a single-column vertical list. |
| 17.6 | **Discord embeds** | Rich formatted message blocks in Discord | The Discord bot builds `discord.Embed` objects with color-coded titles (green for UP, red for DOWN), inline fields for each prediction horizon, thumbnail for the ticker logo, and a footer with the prediction timestamp. |
| 17.7 | **mplfinance chart generation** | Server-side financial chart image generation | The `/chart` Discord command generates a PNG candlestick chart on the server and attaches it to the Discord message. Pillow adds text overlays (confidence badge, prediction direction label). |
| 17.8 | **WebSocket live updates** | Real-time DOM updates without polling | Ticker card prices and confidence scores on the web dashboard update in real-time as Valkey pub/sub pushes changes through the WebSocket connection. The Redux store is updated, causing React to re-render only the changed ticker cards. |
| 17.9 | **Voice UI** | Natural language interaction through smart speakers | The Alexa skill and Google Home action provide a voice UI with intent recognition. The `GetPrediction` intent handler formats a spoken response optimized for audio (not text) — short, unambiguous, using stock ticker spoken names ("Apple" not "AAPL"). |

---

## Category 18 — Security (7 sub-paradigms)

| # | Sub-Paradigm | What It Is | How MarketPulse Demonstrates It |
|---|-------------|-----------|--------------------------------|
| 18.1 | **bcrypt password hashing** | Slow, salted hash algorithm that resists brute-force attacks | User passwords are hashed with `passlib.hash.bcrypt` using work factor 12. The plain-text password is never stored or logged. |
| 18.2 | **JWT blocklist** | Revoking tokens before their natural expiry | On logout, the token's `jti` (JWT ID) is written to Valkey with TTL equal to the token's remaining lifetime. The auth middleware checks this blocklist on every request. |
| 18.3 | **TOTP 2FA** | Time-based one-time passwords using a shared secret | `pyotp.TOTP` generates codes from a shared secret, current time, and 30-second window. The secret is stored encrypted in PostgreSQL; only the QR code setup is shown once. |
| 18.4 | **Rate limiting (API)** | Limiting request frequency per client to prevent abuse | FastAPI middleware applies rate limits per IP: 100 requests/minute for authenticated users, 10 requests/minute for anonymous. Implemented with a Valkey sliding window counter. |
| 18.5 | **Input validation and sanitization** | Rejecting malformed inputs before they reach business logic | Pydantic validates all request inputs. Ticker symbols are validated against a whitelist regex `[A-Z]{1,10}(-[A-Z]+)?`. SQL injection is impossible because `asyncpg` always uses parameterized queries. |
| 18.6 | **Audit log (hash chain)** | Tamper-evident record of all privileged operations | The SQLite audit ledger's SHA-256 hash chain ensures that if any row is modified after the fact, all subsequent row hashes become invalid. An integrity check script is run nightly. |
| 18.7 | **TLS termination at edge** | Encrypting all external traffic at the Cloudflare edge | All traffic from the internet passes through Cloudflare Tunnel, which provides TLS termination. Internal traffic between services (within the same Proxmox node or LAN) uses HTTP; only the external edge uses TLS. |

---

## Category 19 — Data Processing (8 sub-paradigms)

| # | Sub-Paradigm | What It Is | How MarketPulse Demonstrates It |
|---|-------------|-----------|--------------------------------|
| 19.1 | **ETL pipeline** | Extract, Transform, Load — batch data movement | The nightly OHLCV ingestion is a classic ETL: Extract (fetch from yfinance), Transform (compute indicators, normalize), Load (write to TimescaleDB + Parquet). Each phase is a separate ARQ task. |
| 19.2 | **Stream processing** | Processing data records as they arrive | Reddit posts are processed in a streaming fashion: as PRAW yields posts, each is VADER-scored, checked for duplication, written to MongoDB, and written to InfluxDB — no buffering. |
| 19.3 | **Batch processing** | Processing a set of records together for efficiency | FinBERT deep scoring runs in batches of 16 articles at a time (the GPU batch size). Processing 16 together is the same GPU cost as processing 1, so batching gives 16× throughput. |
| 19.4 | **Fan-out aggregation** | Collecting data from many sources and combining into one output | The sentiment aggregation pipeline reads from Reddit (multiple subreddits), news (multiple sources), and on-chain data, then computes a single weighted combined sentiment score per ticker. |
| 19.5 | **Lambda architecture** | Combining a batch layer (historical) and a speed layer (real-time) | OHLCV history is the batch layer (written to TimescaleDB + Parquet, queried by DuckDB). Real-time price updates during market hours are the speed layer (Valkey cache, updated every 60 seconds by Polygon.io polling). |
| 19.6 | **Data deduplication** | Preventing duplicate records from entering the store | ChromaDB vector similarity deduplication prevents the same news story from three different sources from being stored three times. Reddit post deduplication uses the `post_id` unique index in MongoDB. |
| 19.7 | **Schema normalization** | Reducing data to a canonical form before storage | Each `DataSourcePlugin` must return `list[IngestRecord]` where `IngestRecord` is the canonical schema. Source-specific field names (e.g., `article_title`, `heading`, `title`) are all mapped to `headline` in the normalized schema. |
| 19.8 | **Data retention and TTL** | Automatically expiring data that is no longer useful | MongoDB `news_articles` has a 90-day TTL index. Valkey keys have TTLs (price cache: 60s, quota counters: until reset). Loki log retention is 14 days. Cassandra tables have `default_time_to_live`. |

---

## Category 20 — Database (17 sub-paradigms)

| # | Sub-Paradigm | What It Is | How MarketPulse Demonstrates It |
|---|-------------|-----------|--------------------------------|
| 20.1 | **Relational (PostgreSQL)** | ACID, row-oriented, normalized | Users, tickers, watchlists, alert configs |
| 20.2 | **Time-series (TimescaleDB)** | Hypertables, time_bucket, compression | OHLCV, predictions, sentiment, indicators |
| 20.3 | **Key-value (Valkey)** | O(1) get/set, TTL, pub/sub, INCR | Sessions, flags, quota counters, price cache |
| 20.4 | **Vector (ChromaDB)** | Embedding store with similarity search | News dedup, Reddit clustering |
| 20.5 | **Multi-model (SurrealDB)** | Graph + document + relational in one engine | Cross-domain sector sentiment queries |
| 20.6 | **Object storage (MinIO)** | S3-compatible blob storage | Charts, reports, models, Parquet archives |
| 20.7 | **Document (MongoDB)** | Schema-flexible JSON document store | News articles, Reddit posts, SEC filings |
| 20.8 | **Full-text search (Elasticsearch)** | Inverted index for keyword search | News and Reddit search |
| 20.9 | **Secondary time-series (InfluxDB)** | High-frequency write optimized | Mention counts, sentiment stream |
| 20.10 | **Embedded append-only (SQLite event journal)** | Immutable event log | All predictions, alerts, training runs |
| 20.11 | **Embedded hash-chain (SQLite audit ledger)** | Tamper-evident audit log | Account changes, flag changes |
| 20.12 | **Embedded geospatial (SpatiaLite)** | Geographic features and queries | Company HQ locations, exchange locations |
| 20.13 | **Embedded object-oriented (ZODB)** | Python object persistence with OOP hierarchy | Ticker registry: StockTicker, CryptoTicker |
| 20.14 | **Embedded OLAP in-memory (DuckDB)** | Analytical queries on in-process data | Live dashboard aggregations |
| 20.15 | **Embedded OLAP persistent (DuckDB)** | Analytical queries over Parquet archives | Long-term accuracy trends, correlation |
| 20.16 | **Wide-column (Cassandra / Astra)** | Query-pattern-optimized column families | API call logs, ingestion event records |
| 20.17 | **Graph (Neo4j AuraDB)** | Node-edge graph with Cypher query language | Ticker relationships, supply chains, ETF holdings |

---

## Category 21 — Programming Paradigms (9 sub-paradigms)

| # | Sub-Paradigm | What It Is | How MarketPulse Demonstrates It |
|---|-------------|-----------|--------------------------------|
| 21.1 | **Object-oriented programming** | Encapsulation, inheritance, polymorphism | `DataSourcePlugin` base class with `NewsAPIPlugin`, `GNewsPlugin`, `RSSPlugin` subclasses. All are interchangeable through the `DataSourcePlugin` interface. |
| 21.2 | **Functional programming** | Pure functions, immutability, higher-order functions | Feature engineering pipeline: each transformation is a pure function (`normalize_rsi(value: float) -> float`). Transformations are composed with `functools.reduce`. No side effects in the transformation layer. |
| 21.3 | **Asynchronous programming** | Non-blocking I/O with async/await | The entire FastAPI backend uses `async def` endpoints and `await` for all I/O. Python's `asyncio` event loop handles all concurrency. |
| 21.4 | **Declarative programming** | Describing what you want, not how to compute it | SQL queries, OPA Rego policies, Pydantic models, and React JSX are all declarative — they describe the desired outcome, and the runtime figures out how to achieve it. |
| 21.5 | **Reactive programming** | Propagating changes through a data dependency graph | Valkey pub/sub → WebSocket → React Redux store → React component re-render is a reactive chain: a price change flows automatically through all layers without any imperative orchestration code. |
| 21.6 | **Event-driven programming** | Program flow controlled by events rather than a sequential call stack | The alert system is entirely event-driven: no component polls for alerts. Instead, events are published to the bus and consumed by subscribers. |
| 21.7 | **Procedural programming** | Step-by-step imperative scripts | The `backtest.py` script, the `healthcheck.py` script, and the Ansible playbooks are written procedurally — step 1, step 2, step 3, with clear control flow and no abstraction. |
| 21.8 | **Metaprogramming (Python decorators)** | Code that generates or modifies other code at runtime | FastAPI route decorators (`@router.get()`), Pydantic validators (`@validator`), ARQ task decorators (`@cron`), and the plugin registration decorator (`@register_plugin("datasource")`) are all metaprogramming: they wrap functions with generated behavior at import time. |
| 21.9 | **Policy-oriented programming (OPA)** | Separating policy decisions from policy enforcement code | OPA Rego policies express authorization rules. The FastAPI middleware calls OPA's REST API to evaluate policies, without knowing what the rules are. Adding a new policy rule requires only a `.rego` file change, not a code change. |

---

## Category 22 — Software Architecture (8 sub-paradigms)

| # | Sub-Paradigm | What It Is | How MarketPulse Demonstrates It |
|---|-------------|-----------|--------------------------------|
| 22.1 | **Microservices** | Application decomposed into independent, separately deployable services | FastAPI backend, ML sidecar, Discord bot, ARQ workers, and the web/mobile frontends are separate processes that communicate over defined interfaces (REST, gRPC, Valkey pub/sub). |
| 22.2 | **Plugin architecture** | Extending behavior by adding new implementations of a defined interface | `DataSourcePlugin` and `AlertDeliveryPlugin` are the plugin interfaces. New sources and channels are added by creating new plugin files, with zero changes to existing code. |
| 22.3 | **Event bus** | Decoupled communication between components via events | Valkey pub/sub is the event bus. Producers publish typed events; consumers subscribe and act. Producers and consumers do not know about each other. |
| 22.4 | **Sidecar pattern** | Auxiliary process augmenting a main process | The ML sidecar is a separate Python process providing prediction service to the FastAPI backend. It has its own lifecycle, can be deployed independently, and fails independently. |
| 22.5 | **Repository pattern** | Abstracting data access behind a consistent interface | Every database has a repository class: `PredictionRepository`, `NewsArticleRepository`, `TickerRepository`. Application code calls repository methods, never raw SQL or MongoDB queries directly. This makes swapping databases possible without changing business logic. |
| 22.6 | **CQRS (Command Query Responsibility Segregation)** | Separate write paths (commands) and read paths (queries) | The ingestion pipeline is the write path (command): it pushes data into all databases through the API. The dashboard reads (queries) use DuckDB materialized views and Valkey caches, not the primary write databases. Commands and queries hit completely different code paths. |
| 22.7 | **Circuit breaker** | Stopping calls to a failing service to prevent cascade failures | The gRPC client wrapping the ML sidecar implements a circuit breaker: after 3 consecutive connection failures, it opens the circuit for 60 seconds (returning cached predictions instead of failing live). |
| 22.8 | **Gateway pattern** | Single entry point for all client requests | The FastAPI backend is the sole API gateway. All four surfaces (web, mobile, Discord bot, voice) communicate exclusively through the FastAPI backend. No surface touches a database directly. |

---

## Category 23 — API / Communication (8 sub-paradigms)

| # | Sub-Paradigm | What It Is | How MarketPulse Demonstrates It |
|---|-------------|-----------|--------------------------------|
| 23.1 | **REST** | Resource-oriented HTTP API | FastAPI exposes a full REST API with standard HTTP verbs for all resources. |
| 23.2 | **gRPC (unary)** | Single request/response RPC | `PredictionService.Predict` — one feature vector in, one prediction response out. |
| 23.3 | **gRPC (streaming)** | Streaming RPC for bulk operations | `PredictionService.PredictStream` — a stream of feature vectors in, a stream of predictions out. Used for nightly batch prediction runs. |
| 23.4 | **WebSocket** | Persistent full-duplex TCP channel | Web dashboard live price/prediction updates. |
| 23.5 | **Webhook (receive)** | Receiving callbacks from external services | Cloudflare Workers receive OneSignal, Twilio, and Reddit push notification webhooks and forward to FastAPI. |
| 23.6 | **RSS (consume + produce)** | Syndication feed consumed for input and produced as output | MarketPulse consumes 14+ RSS feeds via feedparser and publishes its own RSS feed at `GET /rss/predictions`. |
| 23.7 | **Discord API** | Platform-specific API for building bot interactions | Discord slash commands, embed builders, paginated message components, and file attachments via `discord.py`. |
| 23.8 | **Alexa Skills API + Google Actions API** | Voice platform APIs for building voice interactions | Local Alexa skill receives Alexa requests, returns SSML speech responses. Local Google Home action receives Google Assistant requests via Flask webhook. |

---

## Category 24 — Development Process (10 sub-paradigms)

| # | Sub-Paradigm | What It Is | How MarketPulse Demonstrates It |
|---|-------------|-----------|--------------------------------|
| 24.1 | **Feature branching** | Each feature developed on its own Git branch | Branching strategy: `main` is always deployable. Feature work happens on `feature/*` branches. CI runs on every push. Merge to `main` via PR only — no direct pushes. |
| 24.2 | **Code review** | Human review of every change before merge | GitHub PR template requires: description of change, testing evidence, paradigm coverage update (if applicable), README update (if behavior changes). Minimum 1 approval required to merge. |
| 24.3 | **CI/CD pipeline** | Automated testing, building, and deployment | GitHub Actions: `test.yml` (pytest, tsc), `build.yml` (Docker image build + push), `deploy.yml` (trigger Argo CD sync). |
| 24.4 | **Linting and formatting** | Automated code style enforcement | Python: `ruff` for linting + `black` for formatting. TypeScript: `eslint` + `prettier`. Rego: `opa fmt`. All checked in CI. |
| 24.5 | **Type checking** | Static type analysis before runtime | Python: `mypy --strict` on all application code. TypeScript: `tsc --noEmit`. Both in CI. |
| 24.6 | **Test coverage** | Measuring how much code is exercised by tests | `pytest-cov` measures line and branch coverage. CI fails if overall coverage drops below 80%. Critical modules (feature engineering, prediction pipeline) require 90%+ coverage. |
| 24.7 | **Semantic commit messages** | Commit messages following a convention for automated changelog generation | `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:` prefixes enforced by `commitlint` in the CI pipeline. `semantic-release` auto-generates changelogs and bumps the version on merge to `main`. |
| 24.8 | **Documentation as code** | Documentation living in the repository, updated with every change | The nine README files in `docs/` are part of the repository. CI includes a check that verifies: if a new module is added to `README_2`, a corresponding build step exists in `README_5`. |
| 24.9 | **Environment parity** | Local development environment matches production as closely as possible | The local `docker-compose.yml` uses the same images and versions as the Proxmox production deployment. The only difference between local and production is the number of replicas and the resource limits. |
| 24.10 | **Reproducible builds** | Given the same inputs, the build produces the same output** | `requirements.txt` pins all Python package versions. `package-lock.json` pins all npm packages. Docker images are built from pinned base image digests (e.g., `timescale/timescaledb@sha256:...`), not floating tags. |

---

## Category 25 — Additional / Financial Domain (4 sub-paradigms)

*(These four complete the count to 216 by covering MarketPulse-specific financial engineering
paradigms that don't fit cleanly into the 24 standard categories above.)*

| # | Sub-Paradigm | What It Is | How MarketPulse Demonstrates It |
|---|-------------|-----------|--------------------------------|
| 25.1 | **Financial time-series normalization** | Converting raw prices to stationary returns for ML | Raw close prices are non-stationary (they trend over time). The ML pipeline converts them to log returns (`log(close_t / close_{t-1})`), which are approximately stationary and model-ready. |
| 25.2 | **Walk-forward backtesting** | Evaluating ML models with a time-respecting train/test split | The backtesting script uses walk-forward validation: train on months 1–24, evaluate on month 25, advance 1 month, repeat. This is the only valid way to evaluate a financial ML model — it mirrors the real use case of training on the past and predicting the future. |
| 25.3 | **Look-ahead bias prevention** | Ensuring no future information leaks into model training | The feature engineering pipeline's `assemble_features(symbol, timestamp)` only reads data with `time < timestamp`. The pipeline tests include a temporal boundary check that fails if any feature value has a timestamp ≥ the prediction timestamp. |
| 25.4 | **Prediction calibration and confidence communication** | Communicating model uncertainty to end users accurately | Confidence scores are calibrated (isotonic regression) so that 80% confidence corresponds to ~80% observed accuracy. The UI communicates uncertainty through color, badge weight, and explicit "uncertain" labeling for low-confidence predictions — never presenting uncertain predictions as actionable. |

---

## Paradigm Coverage Quick-Check Table

| Category | Count | All Mapped? |
|----------|-------|------------|
| Versioning | 9 | ✓ |
| Configuration Management | 7 | ✓ |
| Data Serialization | 8 | ✓ |
| Authorization/Access Control | 7 | ✓ |
| Observability | 7 | ✓ |
| State Management | 8 | ✓ |
| Compilation/Execution | 7 | ✓ |
| Type System | 8 | ✓ |
| Memory Management | 8 | ✓ |
| AI/ML | 10 | ✓ |
| Storage | 8 | ✓ |
| Modeling | 7 | ✓ |
| Concurrency | 8 | ✓ |
| Networking | 9 | ✓ |
| Testing | 10 | ✓ |
| Deployment/Infrastructure | 9 | ✓ |
| UI/Frontend | 9 | ✓ |
| Security | 7 | ✓ |
| Data Processing | 8 | ✓ |
| Database | 17 | ✓ |
| Programming Paradigms | 9 | ✓ |
| Software Architecture | 8 | ✓ |
| API/Communication | 8 | ✓ |
| Development Process | 10 | ✓ |
| Financial Domain | 4 | ✓ |
| **TOTAL** | **216** | **✓** |
