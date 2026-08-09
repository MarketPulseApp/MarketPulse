# MarketPulse — Expanded Outline

> This document covers three subjects: (1) the module-by-module description of how to build each
> of the 25 admin-console paradigm demonstration panels, (2) the complete modularity architecture
> (plugin pattern, event bus, feature flags), and (3) the simplicity design contract and
> financial-specific technical module architectures (OHLCV pipeline, sentiment aggregation
> pipeline, feature engineering pipeline).

---

## Part 1 — Admin Paradigm Demo Console

The admin paradigm demo console is an admin-only section of the web dashboard at `/admin/paradigms`.
It has 25 tabs, one per paradigm category. Each tab is a **live demonstration panel** — it shows
real data from the running system, executes real operations, and returns real results. It is not
a documentation page; it is an interactive exhibit.

**Access:** Only users with the `admin` role (set in OPA policy, stored in JWT `roles` claim) can
access the `/admin` section. The entire admin console is a single React component tree that only
renders for admin users.

**Panel anatomy:** Every panel has three sections:

1. **Concept summary** (2–3 sentences): What this paradigm is and why it exists.
2. **Live demonstration**: An interactive UI element showing the paradigm in action with real data.
3. **Code excerpt**: The actual production code that implements the paradigm, shown with syntax
   highlighting. This is the code running right now, not pseudocode.

---

### Panel 1 — Versioning

**Concept:** Versioning assigns unambiguous identifiers to things that change over time —
software, schemas, APIs, models, and data — so that any future state can be reproduced,
compared, or rolled back to a prior state.

**Live demonstration:**
- A version info card showing: `App version: 1.0.0` (from `GET /version`), `API version: v1`,
  `Schema version: 3 (Alembic head)`, `ML model version: ensemble-v3`.
- An Alembic migration log table: each migration ID, its description, when it was applied.
- A "Run pending migrations" button (admin-only, shows a diff of what would change, requires
  confirmation before executing).

**Implementation steps:**
1. Create `GET /api/v1/version` endpoint returning app version, schema version, and model
   version from environment variables and the Alembic revision.
2. Create `GET /api/v1/admin/migrations` endpoint returning `alembic history` output parsed
   to JSON.
3. Build `VersionPanel.tsx` with `useGetVersionQuery()` RTK Query hook and the migrations table.
4. Add the "Apply Migrations" mutation endpoint — wrap `alembic upgrade head` in a subprocess
   call from FastAPI, stream the output to the client via SSE.

---

### Panel 2 — Configuration Management

**Concept:** Configuration management separates the values that change between environments
(database URLs, API keys, feature flags) from the code that uses them, enabling the same code
to behave differently in development, staging, and production.

**Live demonstration:**
- A settings table showing all `pydantic-settings` configuration keys (names only, not values for
  secrets — `POSTGRES_PASSWORD` is shown as `[SET]` or `[NOT SET]`).
- A feature flags table (all `feature_flags` rows from PostgreSQL) with toggle switches.
  Toggling a flag calls `PATCH /api/v1/admin/flags/{flag_name}` and writes to both PostgreSQL
  and Valkey simultaneously. The change is reflected live — all workers pick it up within 5
  seconds.
- A "Configuration validation report" showing whether all required env vars are set, which are
  using default values, and whether the Vault connection is healthy.

**Implementation steps:**
1. Create `GET /api/v1/admin/config/summary` returning a redacted settings summary.
2. Create `GET/PATCH /api/v1/admin/flags` endpoints for listing and toggling flags.
3. Ensure the flag toggle writes to both PostgreSQL and Valkey in a single transaction using
   Valkey's MULTI/EXEC to make the write atomic.
4. Build `ConfigPanel.tsx` with the settings summary, flag toggles (React Switch components),
   and real-time flag state from the WebSocket connection.

---

### Panel 3 — Data Serialization

**Concept:** Serialization converts an in-memory data structure to a byte representation that
can be stored, transmitted, or reconstructed. Different formats make different trade-offs between
human readability, size, speed, and type fidelity.

**Live demonstration:**
- A serialization comparison table for a sample `Prediction` object:
  | Format | Size | Serialize time | Deserialize time |
  |--------|------|---------------|-----------------|
  | JSON | 312 bytes | 0.04ms | 0.06ms |
  | MessagePack | 187 bytes | 0.01ms | 0.02ms |
  | Protobuf | 89 bytes | 0.008ms | 0.009ms |
  | Parquet (batch of 1000) | 4.2 KB | 12ms | 8ms |
- An "Export as..." button set: clicking any format runs the serialization benchmark live and
  updates the table with measured times from the current request.
- An RSS feed preview showing the raw XML output of `GET /rss/predictions`.

**Implementation steps:**
1. Create `POST /api/v1/admin/serialize-benchmark` that accepts a prediction object and returns
   timing data for all four formats.
2. Use Python's `time.perf_counter_ns()` for nanosecond-precision timing.
3. Build `SerializationPanel.tsx` with the benchmark table, a "Run Benchmark" button, and the
   RSS preview using a `<pre>` block fetched from `GET /rss/predictions`.

---

### Panel 4 — Authorization / Access Control

**Concept:** Authorization determines what an authenticated identity is allowed to do. It is
separate from authentication (which determines who you are). Authorization policy expressed as
code (OPA/Rego) can be versioned, tested, and changed independently of the application code.

**Live demonstration:**
- A policy viewer showing the content of each `.rego` file in `policies/`, syntax-highlighted.
- An authorization query tester: input a JSON `input` object (e.g., `{"user": {"roles":
  ["user"]}, "method": "DELETE", "resource": "admin_flags"}`) and click "Evaluate Policy." The
  panel calls `POST /api/v1/admin/opa/evaluate` which calls OPA's `/v1/data/marketpulse/allow`
  endpoint and shows `{"result": true}` or `{"result": false}` with the rule that matched.
- A JWT decoder: paste any MarketPulse JWT and see the decoded header, payload, and verification
  status (valid/expired/blocklisted).

**Implementation steps:**
1. Create `GET /api/v1/admin/policies` returning the content of all `.rego` files.
2. Create `POST /api/v1/admin/opa/evaluate` that accepts an OPA input JSON and calls the OPA
   server's data API, returning the result.
3. Create `POST /api/v1/admin/jwt/decode` that verifies and decodes a JWT without revealing
   the secret.
4. Build `AuthPanel.tsx` with the Rego viewer (use `react-syntax-highlighter`), query tester,
   and JWT decoder.

---

### Panel 5 — Observability

**Concept:** Observability is the ability to understand what is happening inside a system from
its external outputs: metrics (numbers over time), logs (events with context), and traces
(correlated spans across multiple services). Without observability, debugging production issues
requires guessing.

**Live demonstration:**
- Embedded Grafana dashboard iframe showing the last 1 hour of API request latency.
- A live Prometheus metrics table: current request count, error rate, p50/p95/p99 latency,
  fetched from `GET /metrics` and parsed.
- A Jaeger trace search: enter a trace ID and show the full distributed trace for that request.
- A Loki log viewer: show the last 10 structured log lines, formatted as JSON with timestamp
  and event field highlighted.
- SLO status cards: "Prediction latency < 2s: 99.2% · Error rate < 1%: 99.8%."

**Implementation steps:**
1. Create `GET /api/v1/admin/metrics` that fetches and parses the Prometheus metrics endpoint.
2. Create `GET /api/v1/admin/traces/{trace_id}` that queries Jaeger's HTTP API.
3. Create `GET /api/v1/admin/logs/recent` that queries Loki's API for recent structured logs.
4. Build `ObservabilityPanel.tsx` with a `<iframe>` for Grafana and custom React components
   for the metrics, traces, and log display.

---

### Panel 6 — State Management

**Concept:** State management governs how data flows through an application — from the server to
the client, within a UI, and between services. The key challenge is keeping state consistent
when multiple components, processes, and users are modifying the same data.

**Live demonstration:**
- A live Redux DevTools-style action log showing the last 10 Redux actions dispatched in the
  current browser session (populated via `window.__REDUX_DEVTOOLS_EXTENSION__`).
- A pub/sub message counter: shows how many messages have been published to
  `pubsub:price_updates` in the last 5 minutes (Valkey `XLEN` on the stream or `SUBSCRIBE`
  message counter).
- An optimistic update demo: a form that simulates adding a ticker to a watchlist, shows the
  optimistic state update (ticker appears immediately), then artificially delays the server
  response to show what rollback looks like on failure.
- A state rehydration demo: shows the SQLite event journal's last 5 entries and a button to
  "recompute accuracy from event journal" — demonstrating that state can be recomputed from
  the immutable event log.

**Implementation steps:**
1. Expose the Redux DevTools API from the app's root store.
2. Create `GET /api/v1/admin/state/pubsub-stats` returning recent pub/sub message counts.
3. Create `GET /api/v1/admin/state/event-journal/recent` for the last N event journal entries.
4. Build `StatePanel.tsx` with the action log viewer, pub/sub counter, and event journal table.

---

### Panel 7 — Compilation / Execution

**Concept:** Modern applications go through multiple compilation and transformation steps before
executing: TypeScript compiles to JavaScript, Python compiles to bytecode, ML models compile to
ONNX or TorchScript, and gRPC stubs are generated from .proto files. Each step makes a trade-off
between developer convenience, performance, and portability.

**Live demonstration:**
- A model format comparison: for the AAPL LSTM model, show file size as PyTorch `.pt`,
  TorchScript `.jit.pt`, and ONNX `.onnx`. Show inference latency for each format.
- A protobuf schema viewer: show the `prediction.proto` file content and a "decode bytes" tool
  where you can paste a hex-encoded protobuf message and see it decoded to JSON.
- A "run code generation" button: clicking it runs `python -m grpc_tools.protoc prediction.proto`
  in a subprocess and shows the generated code output.
- The Vite build stats: bundle sizes, chunk count, and build time from the last production build.

**Implementation steps:**
1. Create `GET /api/v1/admin/models/format-comparison/{symbol}` returning model size and
   benchmark inference times for each format.
2. Create `POST /api/v1/admin/protobuf/decode` accepting hex bytes and returning decoded JSON.
3. Create `GET /api/v1/admin/proto-schema` returning the `prediction.proto` file content.
4. Build `CompilationPanel.tsx` with the model comparison table, protobuf tools, and Vite stats.

---

### Panel 8 — Type System

**Concept:** Type systems catch entire classes of bugs before the code runs. In a financial
application, a type mismatch between `float` and `Decimal`, or between "price" and "return"
(which have different statistical properties), can produce subtly wrong predictions that are
harder to find than a crash.

**Live demonstration:**
- A schema explorer: shows all Pydantic models defined in the application, their fields, and
  their types — rendered as a searchable table.
- A TypeScript interface viewer: shows all interfaces in `src/types/`, browsable by name.
- A runtime type validation demo: a form where you can submit a `PredictionSchema` JSON with
  intentional type errors (e.g., `"confidence": "high"` instead of a float) and see the Pydantic
  422 validation error response in real-time.
- The discriminated union demo: submit either a `StockTicker` JSON or a `CryptoTicker` JSON and
  see which Pydantic model it parsed to.

**Implementation steps:**
1. Create `GET /api/v1/admin/schemas` returning a serialized representation of all Pydantic
   models (use `model.model_json_schema()` for each model class).
2. Create `POST /api/v1/admin/schemas/validate` accepting arbitrary JSON and validating it
   against a named schema.
3. Build `TypeSystemPanel.tsx` with the schema explorer (searchable table), type validation
   tester, and discriminated union demo.

---

### Panel 9 — Memory Management

**Concept:** In a long-running server process, memory must be actively managed. Unbounded caches
fill RAM. Forgotten connections exhaust connection pools. Large data frames processed all at once
cause spikes that starve other requests. Knowing where your memory is going is the first step.

**Live demonstration:**
- A live memory gauge: current Python process RSS (resident set size) from `/proc/{pid}/status`,
  updated every 5 seconds via SSE.
- A connection pool gauge: current active and idle connections for each database pool
  (asyncpg, motor).
- A memory by component breakdown: estimated memory used by the Valkey connection, ChromaDB
  client, DuckDB in-memory, and loaded ML models (estimated from `sys.getsizeof()` on key
  objects).
- A "Force GC" button: calls `gc.collect()` on the FastAPI process and shows the before/after
  RSS delta.
- A streaming demo: trigger an export of 10,000 OHLCV rows and show memory usage during the
  stream (should stay flat, not spike to 10,000× row size).

**Implementation steps:**
1. Create `GET /api/v1/admin/memory/status` returning RSS, connection pool stats, and estimated
   component memory using `psutil` and `sys.getsizeof`.
2. Create `POST /api/v1/admin/memory/gc` calling `gc.collect()` and returning before/after RSS.
3. Build `MemoryPanel.tsx` with live gauges (update via polling every 5s) and the streaming demo.

---

### Panel 10 — AI / ML

**Concept:** The ML prediction pipeline combines five model types — LSTM for time-series patterns,
XGBoost and LightGBM for tabular features, FinBERT for NLP sentiment, and VADER for fast scoring
— into an ensemble. Anomaly detection runs in parallel. Each component contributes to the final
prediction.

**Live demonstration:**
- A ticker selector. Choose any active ticker and click "Run Full Prediction Pipeline."
- The panel shows each step executing in sequence:
  1. Feature assembly (shows the actual feature vector as a labeled list of values)
  2. LSTM inference (shows raw probability output: [UP: 0.62, FLAT: 0.21, DOWN: 0.17])
  3. XGBoost inference (shows raw probability output)
  4. LightGBM inference (shows raw probability output)
  5. FinBERT scoring (shows the latest news headline scored in real-time)
  6. Ensemble combination (shows the weighted average computation)
  7. Isolation Forest score (anomaly flag: yes/no)
  8. Calibrated confidence score (final output)
- SHAP waterfall chart: shows which features pushed the prediction toward UP vs. DOWN.
- Model accuracy cards: rolling accuracy for this ticker per horizon.

**Implementation steps:**
1. Create `POST /api/v1/admin/ml/debug-predict/{symbol}` that runs the full pipeline in verbose
   mode, returning intermediate outputs from each component.
2. Create `GET /api/v1/admin/ml/shap/{symbol}` returning the SHAP values for the latest
   prediction.
3. Build `MLPanel.tsx` with the step-by-step pipeline display (each step is a collapsible card
   that reveals when the step completes), a SHAP waterfall chart using Recharts, and accuracy cards.

---

### Panel 11 — Storage

**Concept:** Different storage systems make different trade-offs. A relational database enforces
consistency. A document database accepts flexible schemas. A time-series database stores
sequences efficiently. A vector database enables similarity search. Understanding when to use
each is as important as knowing how to use it.

**Live demonstration:**
- A storage topology diagram: all 17 databases shown as colored nodes with their type, host,
  and current status (green/red).
- A query comparison: for a query like "latest 30 days of AAPL closing prices", show:
  - TimescaleDB: `SELECT time, close FROM ohlcv WHERE symbol='AAPL' AND time > NOW() - '30d'::interval ORDER BY time` → execution time
  - PostgreSQL (no TimescaleDB): same query on a plain table → execution time
  - DuckDB on Parquet: `SELECT time, close FROM read_parquet('s3://...')` → execution time
- A storage size breakdown table: current data size in each database (from their respective
  management APIs).
- A "test deduplication" demo: paste two similar news headlines, click "Check Similarity," and
  see the ChromaDB cosine similarity score.

**Implementation steps:**
1. Create `GET /api/v1/admin/storage/topology` returning status and size for all 17 databases.
2. Create `POST /api/v1/admin/storage/query-benchmark` running the same query on TimescaleDB
   vs. plain PostgreSQL and returning timing.
3. Create `POST /api/v1/admin/storage/similarity` accepting two texts and returning ChromaDB
   cosine similarity.
4. Build `StoragePanel.tsx` with a custom force-directed graph layout using D3 for the topology,
   the benchmark table, and the similarity tester.

---

### Panel 12 — Modeling

**Concept:** Data modeling is the practice of deciding what entities exist, what attributes they
have, and how they relate to each other. The model choice — relational, document, graph,
object-oriented — determines what queries are easy, what constraints are enforced, and what
future changes will be difficult.

**Live demonstration:**
- An entity relationship diagram (ERD) for the PostgreSQL schema — rendered as a SVG diagram
  using `mermaid-js` from the actual schema introspection.
- A ZODB object browser: shows the ticker registry as a tree — `Ticker` at the root, with
  `StockTicker` (AAPL, TSLA, ...) and `CryptoTicker` (BTC-USD, ETH-USD) as children, with
  their inheritance-specific fields visible.
- A Neo4j graph snippet: show a Cypher query and its result as an interactive node-link diagram
  (use `neo4j-nvl` or `@neo4j-nvl/react` for in-browser graph rendering).
- A SurrealDB cross-model query demo: a pre-built query that joins tickers, sectors, and news
  articles, showing results that would require three separate queries in a traditional system.

**Implementation steps:**
1. Create `GET /api/v1/admin/modeling/erd` returning a Mermaid ER diagram string generated
   from `asyncpg.fetch("SELECT * FROM information_schema.table_constraints")`.
2. Create `GET /api/v1/admin/modeling/zodb/ticker-tree` returning the ZODB ticker registry
   as a nested JSON tree.
3. Create `POST /api/v1/admin/modeling/neo4j/query` accepting a Cypher query and returning
   results.
4. Build `ModelingPanel.tsx` with Mermaid rendering, the ZODB tree, and Neo4j graph display.

---

### Panel 13 — Concurrency

**Concept:** Concurrency allows multiple tasks to make progress without waiting for each other.
In an async system, many requests are in flight simultaneously. Understanding how concurrency
is achieved (event loop, threads, processes) and what the limits are (GIL, connection pool
size, API rate limits) is essential for building a system that scales.

**Live demonstration:**
- A live event loop utilization gauge: shows the asyncio event loop's current task count and
  estimated CPU utilization (from `asyncio.all_tasks()`).
- A concurrent feature assembly demo: click "Assemble features for all tickers concurrently."
  Watch the panel show the start times and end times for each ticker's feature assembly running
  in parallel (asyncio.gather). Compare to a "sequential" option.
- A rate limiter visualization: shows the Polygon.io sliding window semaphore — the current
  token count, the refill rate, and a "send burst of 10 requests" button that demonstrates
  how the semaphore throttles to 5/min.
- An ARQ worker queue depth graph: live chart of the ARQ task queue depth over the last hour.

**Implementation steps:**
1. Create `GET /api/v1/admin/concurrency/event-loop` returning task count from `asyncio.all_tasks()`.
2. Create `POST /api/v1/admin/concurrency/feature-assembly-race` that runs feature assembly for
   all tickers with `asyncio.gather` and returns per-ticker timing.
3. Create `POST /api/v1/admin/concurrency/burst-test` that attempts 10 rapid API quota increments
   and shows which ones were rate-limited.
4. Build `ConcurrencyPanel.tsx` with gauges, the side-by-side timing comparison, and the
   rate limiter visualization.

---

### Panel 14 — Networking

**Concept:** Modern distributed systems communicate over many protocols — REST, gRPC, WebSocket,
webhooks, and platform-specific APIs. Each protocol is optimized for a different use case:
REST for general API calls, gRPC for low-latency service-to-service calls, WebSocket for
real-time push, and webhooks for event callbacks.

**Live demonstration:**
- A network topology diagram: FastAPI → ML sidecar (gRPC), FastAPI → Valkey (TCP), FastAPI →
  PostgreSQL (TCP), FastAPI → MongoDB (TCP), Discord bot → FastAPI (HTTP). Shows current
  connection status for each.
- A gRPC benchmark: click "Send 100 prediction requests via gRPC" and see total time, per-request
  latency, and throughput vs. a hypothetical REST equivalent.
- A WebSocket connection counter: current number of active WebSocket connections to the FastAPI
  backend.
- A webhook history table: the last 10 webhooks received (OneSignal, Twilio, or test) with
  timestamp, source, and payload.

**Implementation steps:**
1. Create `GET /api/v1/admin/network/topology` returning connection status for all service pairs.
2. Create `POST /api/v1/admin/network/grpc-benchmark` that sends N requests to the ML sidecar
   and measures aggregate throughput.
3. Create `GET /api/v1/admin/network/websocket-count` returning the current active WebSocket
   connection count.
4. Build `NetworkPanel.tsx` with a custom SVG topology diagram, benchmark results, and the
   webhook log table.

---

### Panel 15 — Testing

**Concept:** A test suite is a specification of expected behavior. Without tests, every change
is a risk. The different types of tests form a pyramid: many cheap unit tests at the bottom,
fewer but more realistic integration tests in the middle, and a small number of expensive
end-to-end tests at the top.

**Live demonstration:**
- A live test runner: click "Run Unit Tests" to trigger `pytest tests/unit/` in a subprocess.
  The panel streams test output (pass/fail/error per test) in real-time via SSE.
- A coverage badge: current coverage percentage and a heat map of which modules have high vs.
  low coverage.
- A backtesting results table: accuracy, F1 score, and calibration error for each ticker's
  model on the holdout test period.
- A mutation testing report: the last `mutmut` run's mutation survival rate, with examples of
  mutants that survived (indicating test gaps).
- A load test summary: results from the last Locust run (p50, p95, p99 latency, max RPS).

**Implementation steps:**
1. Create `POST /api/v1/admin/testing/run-unit` that spawns `pytest tests/unit/` and streams
   output to the client via SSE.
2. Create `GET /api/v1/admin/testing/coverage` returning the latest coverage report JSON.
3. Create `GET /api/v1/admin/testing/backtest-results` returning stored backtest metrics.
4. Build `TestingPanel.tsx` with the live test output stream (SSE consumer), coverage heat map,
   and the results tables.

---

### Panel 16 — Deployment / Infrastructure

**Concept:** Modern deployment is infrastructure-as-code. The state of every server, every
container, and every configuration is defined in version-controlled files and applied
automatically. Manual server configuration is a source of undocumented state — a future outage
waiting to happen.

**Live demonstration:**
- An Argo CD application status view: the current sync status of each Argo CD application
  (MarketPulse-backend, MarketPulse-ml-sidecar, MarketPulse-databases), last sync time, and
  last deployed commit hash.
- A deployment history table: last 10 deployments with commit hash, deployed at, deployer, and
  outcome (success/rollback).
- A blue/green status card: current traffic distribution (Blue: 100% → Green: 0% before deploy,
  Blue: 0% → Green: 100% after healthy deploy). A "Simulate Deploy" button walks through the
  blue/green flow with fake data.
- A Vault health card: Vault seal status, current token TTL remaining, and which secrets were
  last rotated and when.

**Implementation steps:**
1. Create `GET /api/v1/admin/deployment/argo-status` that calls the Argo CD API and returns
   application health.
2. Create `GET /api/v1/admin/deployment/history` returning the last 10 deployments from a
   `deployments` PostgreSQL table (written to by the CI/CD pipeline).
3. Create `GET /api/v1/admin/deployment/vault-health` checking Vault's `/v1/sys/health` endpoint.
4. Build `DeploymentPanel.tsx` with the Argo CD status cards, deployment history table, and
   blue/green visualization.

---

### Panel 17 — UI / Frontend

**Concept:** The user interface is the only part of the system the user sees. A well-designed
UI makes complex data accessible through progressive disclosure — showing the most important
information first, with detail available on demand. A poorly designed UI buries insights in
menus and tabs.

**Live demonstration:**
- A component gallery: shows every reusable UI component from `src/components/` — PredictionCard,
  SentimentBadge, ConfidenceMeter, QuotaGauge — as a live interactive component with all
  variants (UP/FLAT/DOWN states, all confidence levels, all alert types).
- A chart type gallery: shows the same AAPL data rendered as five chart types — candlestick,
  line, area, volume bar, and a combined chart — to demonstrate Recharts versatility.
- A real-time update demo: shows a ticker price updating live from the WebSocket with a pulse
  animation on each update.
- A Discord embed preview: shows what the `/predict AAPL` Discord response would look like,
  rendered as an HTML mockup of a Discord embed.

**Implementation steps:**
1. Create a `ComponentGallery.tsx` that renders every shared component in isolation with all
   prop variants.
2. Create a `ChartGallery.tsx` that fetches AAPL OHLCV data and renders it in 5 chart formats.
3. Create a `DiscordEmbedPreview.tsx` that mimics Discord's embed rendering using CSS.
4. Build `UIPanel.tsx` with tabs for the component gallery, chart gallery, live update demo,
   and Discord preview.

---

### Panel 18 — Security

**Concept:** Security is not a single feature — it is a layered posture. Password hashing makes
database breaches survivable. JWT blocklists enable immediate logout. 2FA makes stolen passwords
insufficient. Rate limiting prevents brute-force attacks. Audit logs create accountability.
Each layer is independently valuable, and together they compound.

**Live demonstration:**
- A bcrypt benchmark: show how long it takes to hash a password at work factor 12 vs. 10 vs. 14.
  Show how many attempts/second an attacker could make at each factor.
- A JWT lifecycle demo: issue a test JWT, show it decoded, then call "Blocklist this token" and
  show the subsequent 401 response when the same token is used.
- A 2FA setup walkthrough: generate a test TOTP secret, show the QR code it produces (using a
  disposable test secret), and let the admin type a TOTP code to verify it validates correctly.
- An audit log hash chain verifier: show the last 10 audit ledger entries with their hashes,
  and a "Verify Chain Integrity" button that recomputes all hashes and reports whether the chain
  is intact.
- A rate limit tester: click "Send 120 requests in 60 seconds" and show which ones were blocked
  by the rate limiter.

**Implementation steps:**
1. Create `POST /api/v1/admin/security/bcrypt-benchmark` testing hash time at work factors
   10, 12, 14.
2. Create `POST /api/v1/admin/security/totp/generate-test` returning a test secret + QR image.
3. Create `POST /api/v1/admin/security/audit/verify` running the hash chain verification
   algorithm and returning integrity status.
4. Build `SecurityPanel.tsx` with bcrypt benchmark chart, JWT lifecycle demo, 2FA walkthrough,
   and audit chain verifier.

---

### Panel 19 — Data Processing

**Concept:** Data pipelines transform raw source data into structured, analyzed, model-ready
information. The design of a pipeline — whether to process in real-time or in batches, how to
handle errors and retries, how to deduplicate — determines the freshness and reliability of the
system's predictions.

**Live demonstration:**
- A pipeline health table: shows the last run time, status (success/failure), and record count
  for each of the major pipelines (OHLCV ingest, news ingest, Reddit ingest, indicator compute,
  sentiment aggregate, model retrain).
- A "trigger manual ingest" button for any pipeline: clicking it enqueues the ARQ task and shows
  live progress as the task runs.
- A deduplication stats card: "In the last 24 hours, 847 news articles were fetched. 312 were
  flagged as duplicates by ChromaDB and skipped. 535 were stored."
- A Lambda architecture diagram: shows the batch layer (OHLCV to TimescaleDB nightly) and speed
  layer (Polygon.io real-time to Valkey) side by side, with current data freshness for each.

**Implementation steps:**
1. Create `GET /api/v1/admin/pipelines/status` returning last run metadata for each pipeline.
2. Create `POST /api/v1/admin/pipelines/trigger/{pipeline_name}` enqueuing the named ARQ task.
3. Create `GET /api/v1/admin/pipelines/dedup-stats` querying MongoDB for today's deduplication
   metrics.
4. Build `DataProcessingPanel.tsx` with the pipeline health table, trigger buttons, dedup stats,
   and the Lambda architecture diagram (custom SVG or a Mermaid flowchart).

---

### Panel 20 — Database

**Concept:** MarketPulse uses 17 databases. This is not database-of-the-week syndrome — each
serves a specific purpose that no other database type handles as well. This panel lets you
explore and interact with each database type directly.

**Live demonstration:**
- 17 database cards, each with: type, current health, data size, and a live query tool.
- Clicking any card opens a query panel for that database type:
  - PostgreSQL: SQL editor with auto-complete
  - MongoDB: mongosh-style query editor (`db.news_articles.find({symbol:"AAPL"}).limit(5)`)
  - Valkey: Redis CLI style (`GET price:cache:AAPL`, `KEYS quota:*`)
  - Elasticsearch: JSON query body editor
  - Neo4j: Cypher query editor
  - DuckDB: SQL editor (runs directly in-process)
  - Cassandra: CQL editor (via DataStax Astra REST API)
- Results are returned as formatted JSON. Non-admin queries are read-only (prevented by OPA
  policy that rejects mutations in the admin query tool during non-maintenance windows).

**Implementation steps:**
1. Create query proxy endpoints for each database type: `POST /api/v1/admin/db/postgres/query`,
   `/mongo/query`, `/valkey/command`, `/elastic/search`, `/neo4j/cypher`, `/duckdb/query`,
   `/cassandra/query`. Each validates the query for safety (no DROP, DELETE, TRUNCATE).
2. Build `DatabasePanel.tsx` with the 17 cards in a responsive grid and a modal query panel
   for each database with syntax-highlighted input and formatted JSON output.

---

### Panel 21 — Programming Paradigms

**Concept:** Programming paradigms are fundamental styles of computation. The same problem can
be solved with an object-oriented approach (encapsulate state in objects), a functional approach
(transform data through pure functions), a declarative approach (describe the desired result),
or an event-driven approach (react to stimuli). Most real systems combine paradigms.

**Live demonstration:**
- A paradigm comparison: show four implementations of the same operation — "compute the average
  sentiment score for all active tickers" — in OOP style, functional style, declarative SQL
  style, and using the event log (event-sourcing style).
- A decorator demo: show the `@register_plugin("datasource")` decorator and what it adds to the
  function at registration time.
- A reactive chain visualization: trace a price update from Valkey pub/sub message → WebSocket
  message → Redux action → React re-render, showing each step in the chain.

**Implementation steps:**
1. Pre-write the four "same operation, four paradigms" implementations in the backend.
2. Create `GET /api/v1/admin/paradigms/demo/{paradigm_name}` that returns the code excerpt
   and runs the implementation, returning timing.
3. Build `ProgrammingPanel.tsx` with a paradigm selector, code display, execution output,
   and the reactive chain animation (use Framer Motion for the flow visualization).

---

### Panel 22 — Software Architecture

**Concept:** Software architecture is the set of decisions that are hard to change later — the
major components, how they communicate, and which components depend on which others. The goal
is to isolate changes: adding a new data source should not require changing the prediction
pipeline; changing the alert delivery system should not require touching the ingestion workers.

**Live demonstration:**
- A component dependency graph: shows the dependency graph of all major MarketPulse components
  as a directed acyclic graph. Nodes are components; edges are "calls/depends on" relationships.
  Color-coded by layer (data layer: blue, API layer: green, client layer: orange).
- A plugin registry browser: shows all registered `DataSourcePlugin` and `AlertDeliveryPlugin`
  instances — their class name, source_name, and enabled status.
- A circuit breaker status card: shows the ML sidecar circuit breaker's current state (closed /
  open / half-open), failure count, and last trip time.
- A CQRS write/read path trace: shows a complete write path (Polygon.io poll → Valkey update →
  pub/sub → WebSocket → Redux) side by side with a read path (dashboard load → DuckDB query →
  RTK Query cache → React component).

**Implementation steps:**
1. Create `GET /api/v1/admin/architecture/component-graph` returning the dependency graph as
   a node/edge JSON structure.
2. Create `GET /api/v1/admin/architecture/plugin-registry` returning all registered plugin
   instances.
3. Create `GET /api/v1/admin/architecture/circuit-breaker/status` returning the circuit breaker
   state.
4. Build `ArchitecturePanel.tsx` with a D3 force-directed graph for the dependency diagram,
   the plugin registry table, and the circuit breaker status card.

---

### Panel 23 — API / Communication

**Concept:** Different communication protocols are suited to different use cases. REST is
stateless and human-readable, ideal for public APIs. gRPC is binary and fast, ideal for
internal service calls. WebSocket maintains a persistent connection for push updates. Webhooks
enable event-driven callbacks from external services. Understanding the trade-offs helps you
choose the right protocol for each interface.

**Live demonstration:**
- An API explorer: a simplified Swagger UI for the MarketPulse REST API, generated from
  FastAPI's OpenAPI spec. Allows live API calls from the browser.
- A protocol comparison benchmark: send the same prediction request via REST (simulated, since
  the real prediction endpoint calls gRPC internally) vs. direct gRPC, and compare latency.
- A WebSocket connection tester: connect to the price update WebSocket, show incoming messages
  in real-time, and show the raw message bytes for a MessagePack-encoded update.
- An RSS feed live view: shows the current output of `GET /rss/predictions` with auto-refresh
  every 60 seconds.

**Implementation steps:**
1. FastAPI auto-generates OpenAPI spec — embed a Swagger UI iframe pointing to `/docs`.
2. Create `POST /api/v1/admin/api/protocol-benchmark` running the REST vs. gRPC latency test.
3. Create a WebSocket test endpoint at `ws://api/ws/admin/protocol-test` that sends raw
   MessagePack bytes the admin panel can display.
4. Build `APIPanel.tsx` with the Swagger iframe, benchmark results, WebSocket tester, and
   RSS live view.

---

### Panel 24 — Development Process

**Concept:** A disciplined development process makes a complex codebase maintainable by teams
(or by a solo developer returning to the code six months later). Version control, automated
testing, code review, and documentation are not bureaucracy — they are the engineering equivalent
of a pilot's pre-flight checklist.

**Live demonstration:**
- A CI/CD pipeline status view: the last 10 GitHub Actions pipeline runs with status, commit
  message, and duration (queried from the GitHub API).
- A code quality dashboard: current linting errors (from `ruff check .`), type errors (from
  `mypy --strict`), test coverage, and mutation score.
- A "Documentation coverage" check: shows which modules in README_2 have corresponding entries
  in README_5 and README_3, and which are missing.
- A commit history analysis: show the last 30 commits grouped by semantic prefix
  (feat/fix/docs/test/refactor/chore) as a bar chart.

**Implementation steps:**
1. Create `GET /api/v1/admin/dev/ci-status` calling the GitHub API to get recent Actions runs.
2. Create `GET /api/v1/admin/dev/code-quality` running ruff and mypy in subprocesses and
   returning counts.
3. Create `GET /api/v1/admin/dev/doc-coverage` parsing README_2 module list vs. README_5
   phase list and flagging mismatches.
4. Build `DevProcessPanel.tsx` with the CI status table, quality metric cards, doc coverage
   table, and commit history chart.

---

### Panel 25 — Financial Domain

**Concept:** Financial ML has unique constraints that general ML does not. Time-series data is
non-stationary and must be transformed before modeling. Models trained on the past must be
evaluated on data the model never saw. Look-ahead bias — using future information to predict the
past — is the most common mistake and produces optimistically wrong results. Confidence scores
must be calibrated to have meaning.

**Live demonstration:**
- A normalization demo: pick a ticker and date range. Show the raw close price series vs. the
  log return series vs. the z-score normalized series. Explain why raw prices are non-stationary
  and cannot be fed directly to an LSTM.
- A walk-forward backtest runner: choose a ticker and click "Run Walk-Forward Backtest (last
  2 years)." The panel shows the train/test split advancing month by month, and the cumulative
  accuracy chart updating as each period's evaluation completes.
- A look-ahead bias detector: runs a validation check on the feature engineering pipeline.
  For each feature used in the last prediction, it verifies that the feature's timestamp is
  strictly earlier than the prediction's timestamp. Shows "ALL FEATURES VALID" or flags any
  feature that violated the temporal boundary.
- A calibration curve: shows a reliability diagram for each ticker's ensemble model — X axis
  is predicted confidence bucket (0-10%, 10-20%, ..., 90-100%), Y axis is actual observed
  accuracy in that bucket. A perfectly calibrated model lies on the diagonal.

**Implementation steps:**
1. Create `POST /api/v1/admin/financial/normalization-demo` returning raw prices, log returns,
   and z-scores for a given ticker and date range.
2. Create `POST /api/v1/admin/financial/walk-forward-backtest` running the walk-forward
   evaluation and streaming results.
3. Create `GET /api/v1/admin/financial/lookahead-check/{symbol}` running the temporal boundary
   validation on the latest prediction's features.
4. Create `GET /api/v1/admin/financial/calibration/{symbol}` returning the reliability diagram
   data for a given ticker's model.
5. Build `FinancialPanel.tsx` with the normalization chart (Recharts LineChart with 3 series),
   walk-forward backtest progress view, look-ahead checker, and calibration chart.

---

## Part 2 — Modularity Architecture

### Plugin System Design

The plugin system is implemented in `app/plugins/`. The directory structure is:

```
app/
├── plugins/
│   ├── __init__.py               ← Registry definition
│   ├── datasources/
│   │   ├── base.py               ← DataSourcePlugin abstract base
│   │   ├── newsapi_plugin.py     ← NewsAPI implementation
│   │   ├── gnews_plugin.py
│   │   ├── rss_plugin.py
│   │   ├── polygon_plugin.py
│   │   ├── coingecko_plugin.py
│   │   ├── glassnode_plugin.py
│   │   ├── reddit_plugin.py
│   │   ├── sec_edgar_plugin.py
│   │   ├── fred_plugin.py
│   │   └── yfinance_plugin.py
│   └── delivery/
│       ├── base.py               ← AlertDeliveryPlugin abstract base
│       ├── browser_push.py       ← OneSignal web push
│       ├── mobile_push.py        ← OneSignal mobile push
│       ├── email_plugin.py
│       ├── sms_plugin.py         ← Twilio (feature-flagged)
│       ├── discord_plugin.py
│       └── voice_plugin.py
```

#### DataSourcePlugin Interface (Complete)

```python
# app/plugins/datasources/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any

@dataclass
class IngestRecord:
    """Normalized output from any data source."""
    source_name: str
    record_type: str        # "news", "price", "sentiment", "onchain", "economic"
    ticker_symbols: list[str]
    timestamp: datetime
    payload: dict[str, Any]
    raw_id: str             # Source-specific unique ID for deduplication

@dataclass
class QuotaInfo:
    source_name: str
    daily_limit: int | None
    monthly_limit: int | None
    resets_at_midnight_utc: bool

class DataSourcePlugin(ABC):
    source_name: str
    source_type: str
    feature_flag: str

    @abstractmethod
    async def fetch(
        self,
        symbols: list[str],
        since: datetime,
    ) -> list[IngestRecord]:
        """Fetch new data for the given symbols since the given timestamp."""
        ...

    def get_quota_info(self) -> QuotaInfo | None:
        """Return quota metadata. Return None if no quota tracking needed."""
        return None

    async def health_check(self) -> bool:
        """Return True if the source is reachable. Default: try a minimal fetch."""
        try:
            await self.fetch(["AAPL"], datetime.utcnow())
            return True
        except Exception:
            return False
```

#### Plugin Registry

```python
# app/plugins/__init__.py
import importlib
import pkgutil
from pathlib import Path

_datasource_registry: dict[str, DataSourcePlugin] = {}
_delivery_registry: dict[str, AlertDeliveryPlugin] = {}

def register_datasource(plugin: DataSourcePlugin) -> None:
    _datasource_registry[plugin.source_name] = plugin

def register_delivery(plugin: AlertDeliveryPlugin) -> None:
    _delivery_registry[plugin.channel_name] = plugin

def load_all_plugins() -> None:
    """Auto-discover and load all plugins in the datasources/ and delivery/ dirs."""
    for pkg, module_name, _ in pkgutil.walk_packages(
        [str(Path(__file__).parent / "datasources")],
        prefix="app.plugins.datasources."
    ):
        module = importlib.import_module(module_name)
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, DataSourcePlugin)
                and attr is not DataSourcePlugin
            ):
                instance = attr()
                register_datasource(instance)

    # Repeat for delivery plugins
    ...

def get_enabled_datasources(flags: dict[str, bool]) -> list[DataSourcePlugin]:
    return [
        p for p in _datasource_registry.values()
        if flags.get(p.feature_flag, True)  # default enabled if no flag
    ]
```

#### Adding a New Data Source (Complete Walkthrough)

To add Benzinga as a news source (hypothetical example):

1. Create `app/plugins/datasources/benzinga_plugin.py`:
```python
from app.plugins.datasources.base import DataSourcePlugin, IngestRecord, QuotaInfo

class BenzingaPlugin(DataSourcePlugin):
    source_name = "benzinga"
    source_type = "news"
    feature_flag = "datasource.benzinga"

    async def fetch(self, symbols: list[str], since: datetime) -> list[IngestRecord]:
        # Fetch from Benzinga API
        articles = await benzinga_client.get_news(symbols=symbols, since=since)
        return [
            IngestRecord(
                source_name=self.source_name,
                record_type="news",
                ticker_symbols=[a.ticker],
                timestamp=a.published_at,
                payload={"headline": a.title, "summary": a.summary, "url": a.url},
                raw_id=a.id,
            )
            for a in articles
        ]

    def get_quota_info(self) -> QuotaInfo:
        return QuotaInfo(
            source_name="benzinga",
            daily_limit=500,
            monthly_limit=None,
            resets_at_midnight_utc=True,
        )
```

2. Add feature flag to the database:
```sql
INSERT INTO feature_flags (flag_name, is_enabled, description)
VALUES ('datasource.benzinga', TRUE, 'Benzinga news API');
```

3. Add API key to `.env`:
```
BENZINGA_API_KEY=your_key
```

**No other file changes required.** The plugin is auto-discovered at startup, automatically
quota-tracked, automatically disabled when `flag:datasource.benzinga` is set to `false`, and
automatically health-checked.

---

### Event Bus Architecture

The event bus is Valkey pub/sub with typed event schemas.

#### Event Types

```python
# app/events/types.py
from dataclasses import dataclass
from datetime import datetime

@dataclass
class PredictionChangedEvent:
    event_type: str = "prediction_changed"
    symbol: str = ""
    old_direction: str = ""
    new_direction: str = ""
    confidence: float = 0.0
    horizon: str = ""
    timestamp: datetime = None

@dataclass
class UnusualVolumeEvent:
    event_type: str = "unusual_volume"
    symbol: str = ""
    volume: int = 0
    avg_volume: int = 0
    multiplier: float = 0.0
    timestamp: datetime = None

@dataclass
class BreakingNewsEvent:
    event_type: str = "breaking_news"
    symbol: str = ""
    headline: str = ""
    source: str = ""
    finbert_score: float = 0.0
    url: str = ""
    timestamp: datetime = None

# ... 9 more event types (one per alert type)
```

#### Publishing

```python
# app/events/publisher.py
import msgpack
from app.infrastructure.valkey import redis

async def publish_event(event) -> None:
    payload = msgpack.packb({
        "event_type": event.event_type,
        **event.__dict__
    }, use_bin_type=True)
    await redis.publish("marketpulse:events", payload)
```

#### Subscribing (Alert Evaluator)

```python
# app/events/consumer.py
import asyncio, msgpack
from app.infrastructure.valkey import redis
from app.plugins import get_enabled_delivery_plugins
from app.db.alert_configs import get_matching_configs

async def run_alert_consumer():
    async with redis.pubsub() as pubsub:
        await pubsub.subscribe("marketpulse:events")
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            event = msgpack.unpackb(message["data"], raw=False)
            await evaluate_and_dispatch(event)

async def evaluate_and_dispatch(event: dict) -> None:
    configs = await get_matching_configs(event["event_type"], event.get("symbol"))
    plugins = get_enabled_delivery_plugins()
    for config in configs:
        for channel in config.channels:
            plugin = plugins.get(channel)
            if plugin:
                await plugin.deliver(Alert.from_event(event, config), config.user)
```

---

### Feature Flag Runtime Contract

Feature flags are checked in three places:

1. **Plugin layer:** `get_enabled_datasources(flags)` filters the plugin list before ingestion.
2. **Delivery layer:** `get_enabled_delivery_plugins(flags)` filters before dispatch.
3. **FastAPI middleware:** For experimental UI features, the `FeatureFlagMiddleware` checks
   `flags.get("feature.{feature_name}")` before the request reaches the route handler.

Flags are synced from PostgreSQL to Valkey at startup and every 60 seconds:

```python
async def sync_flags_to_cache():
    flags = await postgres.fetch("SELECT flag_name, is_enabled FROM feature_flags")
    pipe = redis.pipeline()
    for row in flags:
        pipe.set(f"flag:{row['flag_name']}", "true" if row["is_enabled"] else "false")
    await pipe.execute()
```

---

## Part 3 — Simplicity Design Contract

### The Three Laws of MarketPulse UX

1. **The prediction is always visible first.** Every view that shows a ticker shows its
   direction and confidence before anything else. No scrolling required to see the prediction.

2. **Configuration is always one level deeper.** You can always get to the prediction from the
   home page in zero clicks. You can always get to the configuration in exactly one click (the
   gear icon). Advanced configuration (per-source weights, custom subreddits) is one more click
   inside the configuration panel. No configuration is more than two clicks from the home page.

3. **The system explains itself.** Every prediction shows "why" — the top 3 features that drove
   it (from SHAP). Every alert shows what triggered it. Every sentiment score links to the
   source posts. The user is never left wondering "why did it say that?"

### Minimum Clicks to Key Actions

| Action | Clicks From Home | Path |
|--------|-----------------|------|
| See all predictions | 0 | Home page shows them |
| See a specific ticker's chart | 1 | Click ticker card |
| See why a prediction was made | 2 | Click ticker card → "Why" tab |
| Add a ticker to tracking | 1 | Click "+" button on home → type ticker |
| Change an alert threshold | 2 | Click ticker card → gear icon |
| Add a subreddit to a ticker | 3 | Click ticker card → gear → Subreddits |
| Export ticker data | 2 | Click ticker card → Export button |
| Change a feature flag | 3 | Admin → Settings → Feature Flags |

### Progressive Disclosure Implementation

The web dashboard implements progressive disclosure through a layered component model:

```
HomeDashboard
├── WatchlistHeader (static, shows watchlist name and total ticker count)
├── TickerCardGrid
│   └── TickerCard (shows: direction badge, confidence meter, price, 24h change)
│       └── [on click] TickerDetailDrawer
│           ├── CandlestickChart (always visible first in the drawer)
│           ├── PredictionHorizonRow (4 cards for 1d/3d/7d/30d)
│           └── AnalysisTabs
│               ├── WhyTab (SHAP values, top features)
│               ├── SentimentTab (Reddit + news scores)
│               ├── NewsTab (latest articles with FinBERT scores)
│               ├── IndicatorsTab (RSI, MACD, Bollinger Bands)
│               └── HistoryTab (prediction accuracy over time)
│       └── [gear icon] ConfigSlideout
│           ├── AlertThresholdsSection
│           ├── SubredditsSection
│           └── DataSourceWeightsSection
└── QuickAddSearch (bottom of home, always visible)
```

The `TickerDetailDrawer` is a slide-over panel that overlays the home page without navigation.
This means the user can check a prediction, look at the chart, and return to the home page
watchlist grid without a page transition.

---

## Part 4 — Financial-Specific Technical Module Architectures

### OHLCV Data Pipeline Architecture

```
┌─────────────────────────────────────────────────────┐
│  OHLCV Ingestion Pipeline (ARQ task: ohlcv_ingest)  │
└─────────────────────────────────────────────────────┘

Step 1: Source Selection
  ├── For each ticker in active_tickers:
  │   ├── If crypto: use CoinGecko OHLCV endpoint
  │   └── If stock/ETF: use Polygon.io (real-time) or yfinance (daily batch)
  └── Apply quota check before each call (QuotaMiddleware)

Step 2: Normalization
  ├── Map source field names → internal schema (open, high, low, close, volume)
  ├── Convert timestamps to UTC
  └── Validate OHLCV consistency (high ≥ low, high ≥ open, high ≥ close, etc.)

Step 3: Storage
  ├── Write to TimescaleDB ohlcv hypertable (asyncpg executemany)
  ├── Update Valkey price cache (SET price:cache:{symbol} <JSON> EX 60)
  └── Archive to Parquet (nightly only: write to MinIO ohlcv-archive bucket)

Step 4: Trigger chained tasks
  ├── Enqueue: indicator_compute task (depends on ohlcv data)
  └── Enqueue: prediction_run task (depends on indicator_compute completion)
```

### Sentiment Aggregation Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Sentiment Aggregation Pipeline                                     │
└─────────────────────────────────────────────────────────────────────┘

Continuous (streaming):
  PRAW poll → for each post:
    1. VADER score the title (fast, <1ms)
    2. Write to InfluxDB sentiment_stream (source=reddit, subreddit=...)
    3. Write to MongoDB reddit_posts (with vader_score)
    4. Increment InfluxDB mention count per ticker

Batch (hourly):
  1. Pull all Reddit posts from the last hour from InfluxDB
  2. Compute weighted average VADER score per (symbol, subreddit):
     weight = upvotes / max_upvotes_in_window
  3. Pull all news articles from the last hour from MongoDB
  4. For any article with finbert_score=None: batch to FinBERT scoring queue
  5. Compute average FinBERT score per (symbol, source_name)
  6. Compute combined sentiment score:
     combined = (reddit_weight × reddit_score + news_weight × news_score)
                / (reddit_weight + news_weight)
     where weights are user-configurable per ticker (default: 0.4 reddit, 0.6 news)
  7. Write daily sentiment_scores to TimescaleDB hypertable

FinBERT batch scoring (ARQ task, runs after market close):
  1. Fetch all news articles with finbert_score=None from last 24 hours
  2. Group into batches of 16
  3. For each batch: call ML sidecar gRPC SentimentService.ScoreBatch()
  4. Update finbert_score in MongoDB for each article
  5. Re-aggregate daily sentiment scores with updated FinBERT data
```

### Feature Engineering Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Feature Engineering: assemble_features(symbol, timestamp)          │
└─────────────────────────────────────────────────────────────────────┘

All reads are strictly: time < timestamp (enforced by temporal guard)

Read from Valkey (fast path, <5ms):
  ├── indicators:latest:{symbol}       → technical indicator values
  ├── macro:latest:FEDFUNDS            → federal funds rate
  ├── macro:latest:DGS10               → 10Y yield
  ├── macro:latest:VIXCLS              → VIX
  ├── onchain:latest:{symbol}:*        → on-chain metrics (crypto only)
  └── price:cache:{symbol}             → current price and 24h change

Read from TimescaleDB (if Valkey miss):
  ├── SELECT close FROM ohlcv WHERE symbol=? AND time <= ? ORDER BY time DESC LIMIT 30
  ├── SELECT * FROM technical_indicators WHERE symbol=? AND time <= ? LIMIT 1
  └── SELECT score FROM sentiment_scores WHERE symbol=? AND time <= ? ORDER BY time DESC LIMIT 7

Read from MongoDB:
  └── aggregate pipeline: avg finbert_score for symbol in last 7 days

Compute derived features:
  ├── log returns: [log(close[i]/close[i-1]) for i in 1..30]
  ├── RSI z-score: (RSI - mean_RSI_90d) / std_RSI_90d
  ├── Sentiment 7-day trend: linear regression slope of daily sentiment scores
  ├── BB position: (close - bb_lower) / (bb_upper - bb_lower) → 0.0 to 1.0
  ├── Days until earnings: from earnings_calendar table
  ├── Insider net ratio: (buy_count - sell_count) / (buy_count + sell_count) over 90d
  └── Sector momentum: (sector_avg_return_5d - SPY_return_5d)

Validate temporal boundary:
  ├── For each feature value, assert its data_timestamp < prediction_timestamp
  └── Raise TemporalViolationError if any feature violates this

Normalize:
  ├── Continuous features: z-score normalization using mean/std from training period
  ├── Bounded features (RSI, BB position): pass through (already in [0,1])
  └── Categorical features: one-hot encode (asset_type, sector)

Return:
  └── FeatureVector(values: list[float], schema_version: str, assembled_at: datetime)
```
