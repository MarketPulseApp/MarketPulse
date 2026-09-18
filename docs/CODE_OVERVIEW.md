# MarketPulse Codebase Overview

## 1. Core Architecture
- **Backend**: FastAPI (Python) serving a REST API and WebSockets.
- **Frontend**: React + Vite + TypeScript web dashboard (using React Router, Tailwind, etc.).
- **Workers**: ARQ (Redis-backed) for background data ingestion and cron jobs (`app/workers/ingestion.py`).
- **Dynamic Plugin System**: Ingestion sources can be dynamically registered (`app/plugins/datasources/registry.py`).

## 2. Persistence Layer (Polyglot)
The system employs a heavily distributed polyglot persistence architecture. Some of it is operational, while others are partially mocked out or stubbed:
- **PostgreSQL (`asyncpg`)**: Primary relational database. Stores Users, Quotas, System Settings, OHLCV (price data), Macro indicators, and Sector data. Connection pool is initialized properly.
- **Valkey/Redis**: Used for ARQ task queuing, caching, and Pub/Sub functionality.
- **MongoDB**: Intended for unstructured document storage (News articles, Reddit posts, SEC filings, predictions). The `ingestion.py` worker partially mocks out insider trading storage.
- **Neo4j**: Intended for graph relationships (e.g., Insider Trading bought/sold edges, Ticker correlations). Currently **MOCKED** out in `ingestion.py` (it catches an ImportError if Neo4j isn't installed and simply logs mock statements).
- **ChromaDB**: Intended for vector storage (News deduplication, Reddit clusters). Currently, deduplication logic is **STUBBED** out in `ingestion.py`.
- **MinIO**: Used for object storage (Charts, Parquet dumps, Models). 
- **SQLite / DuckDB (Embedded)**: Used in the backend lifespan for Audit Ledgers, Geo queries, and Accuracy Analytics.

## 3. Features
### Operational/Implemented
- **Authentication**: JWT-based auth via `/auth/login` and `/auth/register`.
- **API Quotas**: Full CRUD with encrypted API keys (`/api/v1/quotas`).
- **Data Ingestion**: ARQ cron worker polls plugins and dumps data into Valkey.
- **Data Stream**: `/api/v1/data-stream/raw` reads the ingestion firehose from Valkey.
- **Market Data**: OHLCV querying via `/market/ohlcv/{symbol}`.
- **Paper Trading**: Retrieve portfolios and trades via `/paper-trading/portfolio` and `/paper-trading/trades`.

### Frontend Pages
The dashboard has components and routes established for:
- Dashboard, PaperTrading, Settings, AdminConsole, Analytics, CorrelationGraph, SentimentDashboard, MacroIndicators, InsiderTrading, EarningsCalendar, RawData, Training, Quotas.

## 4. Broken, Incomplete, or Disconnected Code (Issues)

1. **Neo4j Integration is Mocked**: 
   - *Issue*: In `app/workers/ingestion.py`, Neo4j graph relationships for Insider Trading are heavily mocked. It falls back to printing log statements (`logger.info("Mock: Creating INSIDER_BOUGHT/INSIDER_SOLD relationships in Neo4j")`).
   - *Fix*: The Neo4j driver needs to actually execute graph creation statements.

2. **ChromaDB Deduplication & FinBERT are Stubbed**:
   - *Issue*: In `app/workers/ingestion.py`, `deduplicate_and_store_news` lacks actual Chroma similarity search logic. `finbert_score_news` is an empty stub that only prints a log.
   - *Fix*: Implement vector search for semantic deduplication and link a real NLP model for scoring.

3. **`/predictions` and `/sentiment` API endpoints**:
   - *Issue*: Both routers (`app/routers/predictions.py`, `app/routers/sentiment.py`) are largely unimplemented. They return hardcoded dummy JSON strings like `"not yet implemented"` or empty arrays/null values.
   - *Fix*: Connect these endpoints to the respective PostgreSQL/MongoDB/TimescaleDB collections.

4. **Websocket Streams (`/ws`) are Hardcoded & Fake**:
   - *Issue*: 
     - `/ws/market` hardcodes `symbol = "AAPL"` and endlessly streams Apple data, ignoring client requests.
     - `/ws/training` streams completely randomized fake training loops (e.g. `loss = loss * random.uniform(0.95, 0.99)`).
   - *Fix*: Allow the client to subscribe to specific symbols for the market WS. Replace training dummy data with an actual hook into ML worker progress.

5. **TimescaleDB / Earnings / Insider Aggregation Mocked**:
   - *Issue*: In `ingestion.py`, saving aggregated earnings surprise data or insider ratios to PostgreSQL/TimescaleDB is commented out or mocked.
   - *Fix*: Uncomment and wire up the TimescaleDB insertion routines.
