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
# Logging Implementation Plan for ML Trading Config

## Overview
The goal is to trace the exact request path, headers, and payload of the ML Trading config save request from the React frontend to the FastAPI backend. This is necessary to diagnose why the request fails when routed through a Cloudflare tunnel.

## Frontend Modifications (React)

### 1. `Settings.tsx`
- Add `console.log` statements before the API call to save the ML Trading config.
- Log the exact URL being called.
- Log the payload being sent.
- Log any error responses received.

### 2. `apiClient.ts`
- Add an interceptor or `console.log` statements in the request and response flow.
- Log the outgoing request method, URL, headers, and body.
- Log the incoming response status, headers, and body.

## Backend Modifications (FastAPI)

### 1. `main.py`
- Implement a logging middleware to capture all incoming requests.
- Log the request method, URL path, and query parameters.
- Log all headers, paying special attention to `x-forwarded-for`, `x-forwarded-proto`, and `host`.
- Log the request body (if possible and safe).
- Log the response status code.

### 2. `app/routers/settings.py`
- Add `logger.info` statements in the specific route handler for saving the ML Trading config (`/api/v1/settings/trading`).
- Log the received payload.
- Log any exceptions or validation errors before returning a 4xx or 5xx response.

## Execution Steps
1. Update `Settings.tsx` and `apiClient.ts` with frontend logging.
2. Update `main.py` to add global request logging middleware.
3. Update `app/routers/settings.py` to add route-specific logging.
4. Deploy/Restart services.
5. Attempt to save the ML Trading config via the Cloudflare tunnel.
6. Analyze the frontend console and backend logs to identify the point of failure.
# Plan: Expose Swagger API Documentation

This document outlines the necessary steps to expose the FastAPI Swagger UI to Cloudflare and add a convenient link to it in the React frontend sidebar.

## 1. Backend Changes (`app/main.py`)

FastAPI's built-in Swagger UI requires the `root_path` to be explicitly set when running behind a reverse proxy (like Nginx/Cloudflare) under a specific path (e.g., `/api`). This ensures that the generated `openapi.json` correctly maps the endpoint URLs.

**Changes required in `app/main.py`:**
Locate the FastAPI app initialization (around line 75):
```python
app = FastAPI(title="MarketPulse API", version="0.1.0", lifespan=lifespan)
```
Modify it to include `root_path="/api"`:
```python
app = FastAPI(
    title="MarketPulse API",
    version="0.1.0",
    lifespan=lifespan,
    root_path="/api"
)
```
*(FastAPI enables `/docs` and `/redoc` by default, so no other changes are strictly necessary to enable Swagger).*

## 2. Frontend Changes (`web_dashboard/src/components/layout/Sidebar.tsx`)

To make the API documentation easily accessible, we will add a new link in the sidebar. Since the Swagger UI is served directly by the backend and isn't a React route, we should use a standard HTML `<a>` tag with `target="_blank"` rather than a React Router `<NavLink>`.

**Changes required in `web_dashboard/src/components/layout/Sidebar.tsx`:**
Import an appropriate icon (e.g., `BookOpen` or `Code`) from `lucide-react`:
```tsx
import { ..., BookOpen } from 'lucide-react';
```
Add the following block within the `<nav>` section (e.g., above the Settings or Admin Console links):
```tsx
<a
  href="/api/docs"
  target="_blank"
  rel="noopener noreferrer"
  className="flex items-center space-x-3 p-2 rounded-lg transition-colors text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
>
  <BookOpen size={20} />
  <span>API Documentation</span>
</a>
```

## 3. Deployment Steps

Once the code changes are committed, the following deployment steps should be taken:

1. **Deploy Backend:**
   - Pull the latest changes to the server.
   - Restart the FastAPI service (e.g., using `systemctl restart marketpulse-api` or restarting the relevant Docker container/pm2 process).
   - *Verification:* Navigate to `https://<your-domain>/api/docs` and confirm the Swagger UI loads and the endpoints can be tested successfully.

2. **Deploy Frontend:**
   - Build the updated React application (`npm run build` or `yarn build`).
   - Deploy the new build artifacts to your hosting provider (e.g., Cloudflare Pages, Vercel, Nginx static dir).
   - *Verification:* Open the dashboard, locate the new "API Documentation" link in the sidebar, click it, and ensure it opens the Swagger UI in a new tab.
# MarketPulse Project Status & Master Checklist

This document is a unified checklist and status report merging findings from the code overview, test sweep, and active plans. It outlines what needs to be done and fixed for the MarketPulse application to be complete.

## 1. Core Codebase Fixes (From Code Overview)
- [ ] **Implement Neo4j Integration**: Update `app/workers/ingestion.py` so the Neo4j driver executes actual graph creation statements for Insider Trading instead of mocking them.
- [ ] **Implement ChromaDB & NLP**: Implement vector search for semantic deduplication in `deduplicate_and_store_news` and link a real NLP model for `finbert_score_news` (they are currently stubbed).
- [ ] **Implement Predictions & Sentiment Endpoints**: Connect the routers (`app/routers/predictions.py`, `app/routers/sentiment.py`) to the respective PostgreSQL/MongoDB/TimescaleDB collections. Currently, they return hardcoded dummy JSON.
- [ ] **Fix Websocket Streams**: 
  - Allow clients to subscribe to specific symbols for the market WS (`/ws/market`) instead of endlessly streaming Apple data.
  - Replace training dummy data with an actual hook into ML worker progress in `/ws/training`.
- [ ] **Implement TimescaleDB Aggregation**: Uncomment and wire up the TimescaleDB insertion routines for earnings surprise data and insider ratios in `ingestion.py`.

## 2. Testing Fixes (From Test Sweep)
- [ ] **Fix `SURREAL_URL` in Settings**: Add `SURREAL_URL` to the Pydantic `Settings` model (likely `app/core/config.py`), or handle its absence gracefully in `tests/integration/conftest.py`.
- [ ] **Install Missing Packages**: Add and install `respx` and `prometheus-fastapi-instrumentator` in the virtual environment to fix `ModuleNotFoundError` during test collection.
- [ ] **Clean Up Ghost Database Tests**: Delete orphaned test files for unimplemented databases (Astra, Elastic, Influx, Surreal, and ZODB in `tests/unit/db/*`), or write their implementations if they are still planned.

## 3. Swagger UI Exposure (From PLAN.md)
- [ ] **Backend (`app/main.py`)**: Add `root_path="/api"` to the FastAPI app initialization.
- [ ] **Frontend (`web_dashboard/src/components/layout/Sidebar.tsx`)**: Add a new standard HTML `<a>` link (with `target="_blank"`) to `/api/docs` in the sidebar using the `BookOpen` icon.
- [ ] **Deploy & Verify**: Restart the FastAPI service and build/deploy the updated React frontend, verifying the Swagger UI loads successfully at `/api/docs`.

## 4. ML Trading Config Logging (From PLAN_LOGGING.md)
- [ ] **Frontend Logging**: Add `console.log` statements in `Settings.tsx` and `apiClient.ts` to log the outgoing request method, URL, headers, and body for the ML Trading config save.
- [ ] **Backend Middleware (`app/main.py`)**: Implement logging middleware to capture incoming requests, focusing on URL paths, query parameters, headers (especially `x-forwarded-for`, `x-forwarded-proto`, `host`), and body.
- [ ] **Backend Route Logging (`app/routers/settings.py`)**: Add `logger.info` in `/api/v1/settings/trading` to log received payloads and exceptions.
- [ ] **Test via Cloudflare**: Attempt to save the config via the Cloudflare tunnel and analyze logs to diagnose the routing failure.
# MarketPulse — Start Here

> **MarketPulse** is a self-hosted financial intelligence platform that ingests public market data,
> news, Reddit sentiment, on-chain data, and economic indicators, runs machine learning models
> across all of it, and outputs a three-class prediction (UP / FLAT / DOWN) with a confidence
> score for every tracked ticker across four prediction horizons. It is not a trading platform.
> It does not execute trades. It does not connect to any brokerage. It is purely an intelligence
> and alert system you run on your own hardware.

---

## Document Map

Read this file first, every time. It tells you which document to open next.

| # | File | What It Is | Open It When |
|---|------|-----------|--------------|
| 0 | `README_0_START_HERE.md` | This file. Navigation hub, project overview, key concepts at a glance. | Always first. |
| 1 | `README_1_DATABASE_SETUP.md` | Complete setup guide for all 17 databases — Docker config, schemas, env vars, verification commands, error reference, storage budget. | Phase 1 of the build. Every time you add a new Proxmox node. When a database crashes and you need the error table. |
| 2 | `README_2_APPLICATION_OUTLINE.md` | Feature specification for every module — what each must do, which database paradigm it demonstrates, and documentation references. | Before you write any code for a new module. When scoping a feature. |
| 3 | `README_3_ALL_PARADIGMS_MASTER.md` | The complete list of all 216 sub-paradigms across 25 categories, each mapped to a specific MarketPulse feature. | When you need to verify paradigm coverage. When a reviewer asks how a specific concept is demonstrated. |
| 4 | `README_4_EXPANDED_OUTLINE.md` | How to build each of the 25 admin-console paradigm panels, plus the plugin/modularity architecture and the simplicity design contract. | When implementing the admin console. When designing the plugin pattern for new data sources. When deciding how UI progressive disclosure should work. |
| 5 | `README_5_BUILD_GUIDE.md` | The authoritative build checklist. Phases 0–25, numbered steps, checkboxes, VALIDATE gates, documentation links, and a Definition of Done. | Your daily driver during active development. Open it, find your phase, work top to bottom. |
| 6 | `README_6_DEPLOYMENT_RESOURCES.md` | Infrastructure reference — per-node resource tables, network diagram, storage growth projections, migration thresholds, env var reference, startup/shutdown sequences. | When provisioning Proxmox nodes. When calculating whether a new service fits in RAM budget. When troubleshooting network routing. |
| 7 | `README_7_COURSE.md` | One plain-English lesson before each build phase. No assumed knowledge. Covers every concept in the build — OHLCV, RSI, FinBERT, LSTM, gRPC, PRAW, look-ahead bias, and more. | Before starting any phase you haven't built before. When you understand what to do but not why it works. |
| 8 | `README_8_EXERCISES.md` | One standalone programming exercise per lesson in README_7. Each completable in under two hours, with expected output shown. | When you want to prove you understand a concept before putting it in production code. When a specific technique feels fuzzy. |

---

## What MarketPulse Does, In One Paragraph

You configure a list of tickers — any mix of US stocks, ETFs, indices, and cryptocurrencies. Every
day (and throughout the day as data arrives) MarketPulse fetches price history, computes every
standard technical indicator, ingests news from a dozen free sources, reads Reddit sentiment from
eight subreddits, pulls on-chain data for crypto tickers, reads economic indicators from FRED, and
watches SEC filings for insider activity. A machine learning pipeline combines all of this into a
prediction: will this ticker be higher, lower, or roughly flat one day from now? Three days? Seven
days? Thirty days? Each prediction comes with a confidence score. When the model is confident and
the prediction changes, MarketPulse alerts you — through your browser, your phone, your Discord,
your email, your SMS, or your smart speaker. The web dashboard and Discord bot give you every data
point the model used, the chart, the sentiment breakdown, the news that drove it, and the model's
historical accuracy on that specific ticker. The mobile app gives you the same portfolio view on
your phone with push notifications. The voice integration lets you ask your Alexa or Google Home
what MarketPulse thinks about any ticker in your watchlist.

---

## The Four Surfaces

### 1. Web Dashboard
**Stack:** React + Vite SPA, TypeScript, Redux Toolkit, Recharts

The primary exploration and configuration surface. Everything the system knows about a ticker is
available here: interactive candlestick charts with prediction overlays, sentiment timelines, news
feed with FinBERT scores, Reddit post lists, technical indicator charts, prediction history with
actual outcome tracking, earnings calendar, insider activity log, API quota gauges, and full
configuration for every alert and data source. Data export (CSV, PDF, JSON, XML, HTML) is
available from every view. The web dashboard is the only surface where you configure the system —
adding tickers, adjusting subreddits, setting alert thresholds, managing API quotas, and operating
the admin paradigm-demo console.

### 2. Mobile App
**Stack:** React Native CLI bare workflow (no Expo), TypeScript, React Native Maps

The at-a-glance surface. Optimized for the use case "I pick up my phone and want to know what the
models think right now." Shows a portfolio card list sorted by confidence × direction, a news
ticker strip, a sentiment heat map across watchlists, and push notifications for high-confidence
prediction changes. You cannot configure the system from the mobile app — it reads; the web
dashboard writes. Push notifications use OneSignal (not Firebase) so there is no Google
dependency.

### 3. Discord Bot
**Stack:** discord.py, Pillow, mplfinance

A near-complete command-line mirror of the application delivered inside Discord. Every significant
feature is available via a slash command. Chart images are generated server-side with mplfinance
and sent as Discord attachments. Paginated embed menus handle long lists (watchlists, news, Reddit
posts). The bot can operate as a multi-channel delivery system: predictions to one channel, alerts
to another, quota warnings to a third. A full command reference is in README_2.

### 4. Voice
**Stack:** Local Alexa skill (Python), Local Google Home action (Python)

Read-only voice queries against the prediction system. Deployed as local skills that run on your
hardware — no cloud skill host required. Handles natural-language queries like "what is the
prediction for Apple today", "is the market bullish on Bitcoin", "what are today's alerts." Can
announce high-confidence predictions as proactive Alexa announcements or Google Home broadcasts
when triggered by the alert system. Not configurable by voice — voice is output only.

---

## Three-Node Deployment Architecture

All development happens on the main rig first (i7-9700K, 32GB RAM, RTX 3070, 95.5GB free).
Everything runs in Docker before migrating to Proxmox. Once stable, services migrate to one of
three Proxmox nodes.

```
┌─────────────────────────────────────────────────────────────────────┐
│  MAIN RIG (Development)                                             │
│  i7-9700K · 32GB RAM (18GB free) · RTX 3070 8GB · 95.5GB free     │
│  Docker Compose — full stack locally during active dev              │
└─────────────────────────────────────────────────────────────────────┘
                               │
               ┌───────────────┼───────────────┐
               ▼               ▼               ▼
 ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
 │  NODE 1         │  │  NODE 2         │  │  NODE 3         │
 │  Core App       │  │  Ingestion      │  │  ML Sidecar     │
 │  ~14GB RAM      │  │  ~14GB RAM      │  │  ~14GB RAM      │
 │  ~120GB storage │  │  ~120GB storage │  │  ~120GB storage │
 │                 │  │                 │  │                 │
 │ FastAPI backend │  │ MongoDB         │  │ gRPC server     │
 │ PostgreSQL +    │  │ Elasticsearch   │  │ LSTM (PyTorch)  │
 │   TimescaleDB   │  │ InfluxDB        │  │ XGBoost         │
 │ Valkey          │  │ ARQ workers     │  │ LightGBM        │
 │ ChromaDB        │  │ Ingestion pods  │  │ FinBERT         │
 │ SurrealDB       │  │ ETL pipeline    │  │ ONNX Runtime    │
 │ MinIO           │  │                 │  │ Isolation Forest│
 │ OPA             │  │                 │  │                 │
 │ Prometheus      │  │                 │  │ CPU-only on     │
 │ Grafana         │  │                 │  │ Proxmox; GPU    │
 │ Jaeger · Loki   │  │                 │  │ locally (3070)  │
 └─────────────────┘  └─────────────────┘  └─────────────────┘
```

All three nodes communicate over a private LAN. The FastAPI backend on Node 1 is the single entry
point for all four surfaces. The ML sidecar on Node 3 exposes a gRPC endpoint that the backend
calls when a prediction is needed. The ingestion workers on Node 2 push processed data into the
databases on Node 1 via the FastAPI internal API (not directly to the database — all writes go
through the API layer). This enforces a single write path and makes the data flow auditable.

Cloudflare Tunnel exposes the FastAPI backend and web dashboard to the internet without opening
any ports on the router. Cloudflare Workers handle incoming webhooks (Reddit push notifications,
OneSignal delivery receipts, Twilio SMS callbacks).

---

## Data Sources by Cost Tier

### Tier 0 — Completely Free, No Key Required

| Source | What It Provides |
|--------|-----------------|
| yfinance (Python library) | OHLCV price history for all US stocks, ETFs, indices, crypto pairs — no API key, no rate limit enforced (be polite) |
| FRED API | Federal Reserve economic data: CPI, interest rates, unemployment, VIX, yield curve — free, key required but free to obtain |
| SEC EDGAR XBRL API | All public company filings, earnings data, insider trading records — completely free, no key |
| US Treasury API | Treasury yield data, bond rates — free, no key |
| RSS feeds (14+) | Reuters, Bloomberg public RSS, CNBC, MarketWatch, Seeking Alpha public, The Motley Fool public, Benzinga, Yahoo Finance RSS, CoinDesk, CoinTelegraph, Decrypt — free, no key, self-ingested with feedparser |
| PRAW / Reddit API | Reddit posts and comments from configured subreddits — free developer account, rate-limited |
| Blockchain.com API | Bitcoin network stats — free, no key |
| ta (Technical Analysis) | Technical indicators computed locally from OHLCV data — no API, no cost |

### Tier 1 — Free with Key (Rate-Limited)

| Source | Free Tier Limit | What It Provides |
|--------|----------------|-----------------|
| Alpha Vantage | 25 calls/day | Fundamental data: P/E ratio, EPS, revenue, dividend history |
| Polygon.io | 5 calls/min real-time; unlimited previous-day | US stock data, options data, aggregates |
| CoinGecko | ~30 calls/min (no key), higher with key | Crypto prices, market cap, volume, 24h change, coin metadata |
| CoinMarketCap | 333 calls/day (free key) | Crypto rankings, market cap, volume, historical snapshots |
| NewsAPI.org | 100 requests/day | News from 150,000+ sources — good coverage of major financial news |
| GNews API | 100 requests/day | Supplementary news aggregation |
| Finnhub | 60 calls/min | News, basic market data, earnings calendars, insider sentiment |
| Glassnode | Basic tier (Bitcoin, Ethereum) | On-chain metrics: SOPR, MVRV, exchange flows, hash rate |
| IntoTheBlock | Free tier | Crypto intelligence signals: large transaction volume, ownership concentration |
| Etherscan | 5 calls/sec (free key) | Ethereum network data: gas prices, contract interactions, token transfers |

### Tier 2 — Free Cloud Database Tiers (Persistent)

| Service | Free Limit | What It Provides |
|---------|-----------|-----------------|
| DataStax Astra (Cassandra) | 40GB storage, unlimited reads/writes | High-throughput write stream for API call logs and ingestion events |
| Neo4j AuraDB Free | 200K nodes, 400K relationships, 1 instance | Ticker relationship graph: company supply chains, sector membership, ETF holdings |

### Cost to Run MarketPulse at Scale

Zero dollars per month at the free tiers listed above, assuming you already own the hardware. The
only optional paid services are Twilio (SMS alerts, feature-flagged off by default) and a domain
for Cloudflare (free on Cloudflare's free plan with a Tunnel).

---

## Alert Types

MarketPulse generates twelve categories of alerts. Each can be sent through any combination of
the six delivery channels. Each is independently togglable per ticker and globally.

| # | Alert Type | Trigger Condition |
|---|-----------|------------------|
| 1 | **Prediction change** | A ticker's UP/FLAT/DOWN prediction flips direction. Only fires when confidence ≥ user threshold. |
| 2 | **High confidence prediction** | Confidence score crosses a user-set threshold (default: 80%) for any prediction horizon. |
| 3 | **Significant price movement** | Intraday price moves more than N% from the previous close (user-configured per ticker, default 5%). |
| 4 | **Unusual volume** | Volume exceeds N× the 20-day average volume (default 3×). |
| 5 | **Sentiment spike** | Combined Reddit + news sentiment score changes by more than N points in 24 hours. |
| 6 | **Breaking news** | A news article mentioning the ticker is published with a sentiment score outside the normal band. |
| 7 | **Earnings approaching** | An earnings announcement is N days away (default 3 days). |
| 8 | **Insider trading filing** | A Form 4 or Schedule 13D/G is filed with the SEC for a tracked ticker. |
| 9 | **Short squeeze signal** | Short interest is high AND volume AND price are both spiking simultaneously. |
| 10 | **API quota warning** | Any tracked API source is within N calls of its daily/monthly limit. |
| 11 | **Model accuracy degraded** | A ticker's rolling prediction accuracy drops below threshold (default: 50% over the last 20 predictions). |
| 12 | **Application error** | Any unhandled exception in the ingestion pipeline, ML sidecar, or notification system that requires human attention. |

### The Six Delivery Channels

1. **Browser push notification** — via OneSignal web push (no Firebase)
2. **Mobile push notification** — via OneSignal mobile SDK in the React Native app
3. **Email** — SMTP, configured in settings
4. **SMS** — Twilio (feature-flagged off by default; no error if Twilio is not configured)
5. **Discord** — DM to a linked Discord account, or post to a configured channel
6. **Voice announcement** — Proactive Alexa announcement or Google Home broadcast

---

## ML Prediction Domains

### What Is Predicted

For each tracked ticker, MarketPulse predicts the **direction of price movement** over four
horizons:

| Horizon | Definition | Use Case |
|---------|-----------|---------|
| **1 day** | Will closing price tomorrow be ≥1% higher (UP), ≤1% lower (DOWN), or within ±1% (FLAT) vs. today? | Short-term swing signals |
| **3 day** | Same threshold, measured 3 trading days out | Short-term trend confirmation |
| **7 day** | Same threshold, 7 trading days out | Weekly trend planning |
| **30 day** | Same threshold, 30 calendar days out | Medium-term position sizing |

The ±1% FLAT threshold is the default. Users can configure this per ticker (e.g., for a volatile
crypto, ±5% might be more meaningful as the FLAT band).

### The Five Model Components

| Model | Role in Ensemble | Primary Input Features |
|-------|-----------------|----------------------|
| **LSTM** | Time-series pattern recognition — captures sequential dependencies in price history | OHLCV returns (not raw prices), technical indicator time series |
| **XGBoost** | Tabular feature classification — fast, accurate on structured feature vectors | All technical indicators, fundamental ratios, macro indicators, sentiment scores at a point in time |
| **LightGBM** | Fast ensemble member — second tabular model for diversity | Same features as XGBoost, different boosting approach for ensemble diversity |
| **FinBERT** | Deep NLP sentiment — BERT fine-tuned on financial text | News headlines and article summaries, earnings call excerpts |
| **VADER** | Fast rule-based sentiment — scores Reddit comment text before FinBERT deep pass | Reddit post titles and comment bodies |

The **ensemble model** combines all five component outputs using learned weights per ticker per
horizon. A ticker with weak news coverage but strong price pattern behavior weights LSTM higher. A
ticker where Reddit sentiment has historically predicted movement weights VADER/FinBERT higher.

The **Isolation Forest** runs parallel to the ensemble and flags anomalous feature vectors —
unusually extreme values in price, volume, or sentiment that fall outside the distribution the
model was trained on. When triggered, the prediction is marked "anomaly — interpret with caution."

### Confidence Score Interpretation

| Score | Displayed As | Alert Behavior |
|-------|-------------|---------------|
| 75–100% | Green badge, prediction shown prominently | Sends alerts through configured channels |
| 50–75% | Yellow badge, caution indicator visible | No alert notifications — shown in dashboard only |
| < 50% | Gray badge, labeled "uncertain" | No alerts; treated as no actionable prediction |

### Training Pipeline

- **Initial training:** On system setup, fetch 2 years of OHLCV history and use it to train an
  initial per-ticker model.
- **Daily incremental retraining:** Each night after market close, add the day's actual outcome
  to the training set and run an incremental update.
- **Per-ticker specialization:** AAPL's model is trained on AAPL's data. BTC's model is trained
  on BTC's data. Models are not shared across tickers — each ticker has its own parameter set.
- **Accuracy tracking:** Every prediction is stored with its confidence and horizon. When the
  outcome date arrives, the actual price change is recorded. The rolling accuracy (last 20
  predictions, last 100 predictions) is computed per ticker per horizon and displayed in the
  dashboard and via `/accuracy` in the Discord bot.

---

## Daily Building Flow

This is the pattern you follow every day during active development. It is also the pattern the
system follows every day in production once running.

### Developer Day (You Building MarketPulse)

```
Morning
  1. Open README_5_BUILD_GUIDE.md at your current phase.
  2. Find the next unchecked step.
  3. Read the corresponding lesson in README_7_COURSE.md if the concept is new.
  4. Do the exercise from README_8_EXERCISES.md to prove understanding before writing
     production code.
  5. Write the code, run it locally in Docker, check it against the VALIDATE gate.

Midday
  6. Commit working code (feature-branch → main via PR; CI runs automatically).
  7. Verify the paradigm covered by this step is recorded in README_3.
  8. Check storage budget against README_6 before adding any new persistent data.

End of Day
  9. Mark the build-guide checkboxes completed.
  10. If a new module is complete, update README_2 to reflect actual behavior vs. spec.
  11. Run the smoke test suite; do not stop for the night with a failing test.
```

### Production Day (MarketPulse Running)

```
Pre-Market (4:00 AM — automated)
  ├── OHLCV ingestion: fetch previous day's closing data for all tickers
  ├── Fundamental data refresh: Alpha Vantage calls for any ticker due for update
  ├── Economic indicator refresh: FRED, US Treasury, BLS
  ├── SEC EDGAR scan: new filings for tracked tickers since last run
  ├── Daily model retraining: add yesterday's outcome, run incremental update
  └── Prediction generation: run all models, compute ensemble, store predictions

Market Hours (9:30 AM – 4:00 PM ET — automated)
  ├── Polygon.io real-time polling (5 calls/min): price and volume updates
  ├── News ingestion: NewsAPI + GNews + Finnhub + RSS feeds — every 15 minutes
  ├── Reddit ingestion: PRAW polls configured subreddits — every 30 minutes
  ├── On-chain data (crypto): CoinGecko + Glassnode polls — every 15 minutes
  ├── Intraday prediction refresh: rerun ensemble when significant input changes
  └── Alert evaluation: after each data update, evaluate all alert conditions

Post-Market (4:05 PM ET — automated)
  ├── Earnings calendar check: fetch upcoming earnings from Yahoo Finance
  ├── Full news sweep: run FinBERT on all articles not yet deep-scored
  ├── Sentiment aggregation: compute daily sentiment scores for each ticker
  └── Daily summary: push summary embed to Discord if configured

Overnight (11:00 PM ET — automated)
  ├── OHLCV Parquet archive: write today's data to MinIO cold storage
  ├── Database maintenance: Timescale compression, ChromaDB index optimization
  ├── API quota reset tracking: reset counters that reset daily
  └── Health check report: push observability summary to Grafana + Discord admin
```

---

## Key Architectural Decisions

Know these before you write a single line of code.

**Single write path.** All data enters the system through the FastAPI backend. Ingestion workers
never write directly to databases — they call internal FastAPI endpoints. This makes every write
observable, rate-limitable, and auditable.

**Plugin pattern for data sources.** Adding a new news source or a new on-chain data feed
requires only creating a new Python class that implements the `DataSourcePlugin` interface and
registering it in the plugin registry. No existing code changes. See README_4 for the complete
plugin architecture.

**gRPC for ML.** The ML sidecar is a separate Python process exposing a gRPC server. The FastAPI
backend calls it with a feature vector and receives a prediction. The ML sidecar can run on
different hardware, can be restarted independently, and can be replaced without touching the
backend.

**No Firebase.** Push notifications use OneSignal. This removes the Google Play Services
dependency from the mobile app and makes the system fully self-hostable without any Google
dependency in the notification path.

**OPA for authorization.** All permission checks are evaluated against OPA policies written in
Rego. The FastAPI backend calls OPA's REST API before executing any operation that modifies
system state. Authorization rules can be updated without redeploying the backend.

**Feature flags on everything.** Every data source, every ML model component, every alert
channel, and every delivery method has a feature flag stored in Valkey. You can disable Twilio
without touching code. You can disable FinBERT and run VADER-only during development without
touching code. See README_2 for the flag naming convention.

**Look-ahead bias is forbidden.** The ML training pipeline enforces a strict temporal split:
features at time T can only include data known before time T. News published after a price move
cannot be used as a feature for predicting that price move. This is the single most important
rule in the entire ML pipeline. See README_7, Lesson 11 for a full explanation.

---

## Storage Budget Summary (Main Rig, 95.5GB Free)

Detailed breakdown is in README_6. The key constraint: **95.5GB is the hard ceiling**. After all
containers, databases, model files, and data are accounted for, at least 10GB must remain free as
operational headroom.

| Category | Allocation |
|----------|-----------|
| PostgreSQL + TimescaleDB (2 years OHLCV, 25 tickers) | 8 GB |
| MongoDB (news + Reddit documents) | 6 GB |
| Elasticsearch index | 4 GB |
| ChromaDB (embeddings) | 3 GB |
| MinIO (charts, reports, Parquet archives) | 10 GB |
| ML model files (LSTM, XGBoost, LightGBM, FinBERT) | 8 GB |
| InfluxDB | 2 GB |
| All other databases combined | 4 GB |
| Docker images and build cache | 12 GB |
| Application code and dependencies | 3 GB |
| Log files (Loki) | 4 GB |
| **Operational headroom** | **≥10 GB** |
| **Total allocated** | **~74 GB** |
| **Remaining buffer** | **~21.5 GB** |

---

## Glossary of Project-Specific Terms

| Term | Definition |
|------|-----------|
| **OHLCV** | Open, High, Low, Close, Volume — the five data points recorded for every asset in every time period. The foundation of all financial analysis. |
| **Ticker** | A symbol identifying a financial asset (AAPL, BTC-USD, SPY). In MarketPulse, a ticker is an object in the ZODB registry with inherited configuration. |
| **Prediction horizon** | The time period a prediction covers: 1-day, 3-day, 7-day, 30-day. All four are generated simultaneously for every ticker. |
| **Confidence score** | A value 0–100 representing how confident the ensemble model is in its direction prediction. Derived from the probability output of the models after calibration. |
| **Paradigm** | One of 25 software engineering categories (e.g., "Database", "AI/ML", "Concurrency") that MarketPulse demonstrates through its implementation. Each category contains sub-paradigms. |
| **Sub-paradigm** | A specific technique within a paradigm category (e.g., "time-series hypertable" within "Database"). There are 216 sub-paradigms in total. |
| **Sentiment score** | A numerical representation of whether text (news or Reddit) is bullish (+) or bearish (−) on a ticker. Produced by VADER (fast) and FinBERT (deep). |
| **Feature vector** | The set of numerical inputs fed to the ML models at prediction time: technical indicators + fundamental ratios + sentiment scores + macro indicators + all other engineered features. |
| **Ingestion worker** | An ARQ background task that fetches data from a source, normalizes it, and writes it through the FastAPI API layer into the appropriate databases. |
| **Plugin** | A Python class implementing a defined interface (`DataSourcePlugin`, `AlertDeliveryPlugin`) that registers itself at startup and requires no changes to existing code. |
| **Look-ahead bias** | Using information about the future to predict the past — the cardinal sin of financial ML. MarketPulse enforces a strict temporal boundary in all training pipelines. |
| **Backtesting** | Simulating how a model would have performed on historical data. Reliable only when performed on data the model was never trained on (out-of-sample). |
| **Paradigm demo console** | An admin-only section of the web dashboard with 25 dedicated panels, one per paradigm category, each showing a live demonstration of the specific sub-paradigms implemented in that category. |
| **Hypertable** | A TimescaleDB abstraction over a regular PostgreSQL table that automatically partitions time-series data by time interval for efficient range queries. |
| **Ensemble model** | A model whose predictions are computed as a weighted combination of several individual models. The ensemble is more accurate than any individual component on average. |
| **gRPC** | Google Remote Procedure Call — a high-performance RPC framework using Protocol Buffers for serialization. Used for the FastAPI → ML sidecar prediction call. |
| **ARQ** | Async Redis Queue — a Python task queue that uses Valkey (Redis-compatible) as a backend. Used for all background ingestion and processing jobs. |
| **Ingestion worker** | An ARQ background task that fetches data from one source, normalizes it to the internal schema, and writes it via the FastAPI internal API. |
| **ZODB** | Zope Object Database — an object-oriented Python database. Used for the ticker registry where StockTicker and CryptoTicker inherit from Ticker. |
| **Parquet** | A columnar file format optimized for analytics queries. OHLCV data is archived to Parquet files in MinIO for long-term storage and DuckDB analysis. |
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
# MarketPulse — Application Outline

> This document is the feature specification for every module. For each module it states what the
> module must do, which database paradigm(s) it demonstrates, and the key documentation
> references. **This is the contract.** What is written here is what gets built. If the
> implementation diverges, update this document first.

---

## Modularity Principles

These rules govern how every module is designed. Read them before reading any module spec.

### 1. The Plugin Pattern — New Sources Without Touching Existing Code

Every data source (news provider, Reddit subreddit, on-chain feed) is a Python class that
implements one of these base interfaces:

```python
class DataSourcePlugin(ABC):
    source_name: str           # e.g. "newsapi", "r/wallstreetbets"
    source_type: str           # "news", "reddit", "onchain", "market", "economic"
    feature_flag: str          # e.g. "datasource.newsapi"

    @abstractmethod
    async def fetch(self, symbols: list[str], since: datetime) -> list[IngestRecord]:
        """Fetch new data for the given symbols since the given timestamp."""
        ...

    @abstractmethod
    def get_quota_info(self) -> QuotaInfo | None:
        """Return quota metadata, or None if this source has no quota tracking."""
        ...
```

Every alert delivery method implements:

```python
class AlertDeliveryPlugin(ABC):
    channel_name: str          # "discord", "email", "sms", "browser_push", "mobile_push", "voice"
    feature_flag: str          # e.g. "alert.discord"

    @abstractmethod
    async def deliver(self, alert: Alert, recipient: User) -> DeliveryResult:
        ...
```

The plugin registry is a dict populated at startup by scanning a `plugins/` directory and calling
`register()` on each found class. **Adding a new data source means creating one new file in
`plugins/datasources/`. No existing file is modified.**

### 2. The Event Bus — Alert Propagation

Alerts are not dispatched directly from the code that detects a condition. Instead, conditions
publish to a typed event bus backed by Valkey pub/sub. Alert consumers subscribe and dispatch.
This decouples detection from delivery.

```
PriceMonitor detects unusual volume
    → publishes UnusualVolumeEvent to event bus
        → AlertEvaluator receives event, checks user alert configs
            → dispatches to enabled AlertDeliveryPlugin instances
```

This means disabling all SMS delivery is one Valkey key flip (`flag:alert.sms = false`), not a
code change.

### 3. Feature Flags on Everything

Every data source, every ML model component, every alert delivery channel, and every
experimental feature has a feature flag in the `feature_flags` PostgreSQL table, mirrored in
Valkey for fast reads. The naming convention is `category.name`:

- `datasource.<source_name>` — data source enabled/disabled
- `ml.<model_name>` — ML model component enabled/disabled
- `alert.<channel_name>` — alert delivery channel enabled/disabled
- `feature.<feature_name>` — experimental feature toggle

The FastAPI startup sequence syncs all flags from PostgreSQL to Valkey on boot. The admin console
can flip any flag at runtime.

### 4. Simplicity Principles — Minimum Clicks to a Prediction

The web dashboard's primary use case is: open it, see the prediction. This must require **zero
clicks** from the authenticated dashboard home page. The dashboard home page shows:

1. All tickers in the user's default watchlist, sorted by confidence × direction magnitude.
2. For each ticker: current direction (UP/FLAT/DOWN), confidence percentage, 24h price change,
   and a color-coded background (green gradient for UP, red gradient for DOWN, gray for FLAT).
3. Clicking any ticker card expands to the full analysis view.

Progressive disclosure: the full analysis view shows the candlestick chart first (most
information density, no interaction needed), with tabs for Sentiment, News, Reddit, Indicators,
and History below it. Advanced configuration (subreddit list, alert thresholds, per-source
weights) is behind a gear icon that opens a slide-out panel — not on the main view.

The Discord bot follows the same principle: `/predict AAPL` must respond with the UP/FLAT/DOWN
prediction in the first embed, with detailed breakdown in a secondary expandable embed.

---

## Module Specifications

---

### Module 1: OHLCV Data Ingestion

**What it must do:**

Fetch Open, High, Low, Close, Volume data for every active ticker across multiple time intervals
(daily `1d`, hourly `1h`, fifteen-minute `15m`). Store all data in the `ohlcv` TimescaleDB
hypertable. Enforce a 2-year lookback on initial ingestion. On incremental runs, only fetch data
since the last recorded timestamp for each ticker.

**Data sources used:**
- `yfinance` for initial historical backfill (unlimited, daily granularity, no key required)
- `Polygon.io` for intraday real-time polling during market hours (5 calls/min on free tier)
- `CoinGecko` for crypto OHLCV (rate-limited, no daily cap on basic tier)

**Databases used:**
- **PostgreSQL + TimescaleDB** — `ohlcv` hypertable (primary time-series write target)
- **Valkey** — `price:cache:{symbol}` key for latest price (60-second TTL for dashboard reads)
- **DataStax Astra** — `api_call_log` table for every Polygon.io and CoinGecko call
- **DuckDB in-memory** — live aggregations on recent OHLCV for dashboard summary panel
- **MinIO** — Parquet archive of daily OHLCV data (written every night at 11 PM)

**Paradigm demonstrated:** TimescaleDB hypertable (time-series), Parquet columnar archival,
INCR-based quota tracking in Valkey.

**Implementation requirements:**
- The ingestion worker must be an ARQ task — not a background thread. Tasks are enqueued by the
  scheduler (ARQ cron) and dequeued by workers.
- Rate limiting for Polygon.io: use a sliding window counter in Valkey that blocks if 5 calls
  have been made in the current second.
- On error from any source, retry with exponential backoff (tenacity library) up to 3 times,
  then mark the ingestion run as failed in the event journal and send an Application Error alert.
- All OHLCV values stored as `NUMERIC(18,6)` — never `FLOAT` for financial data (floating-point
  precision issues with financial calculations).

**Documentation links:**
- yfinance: https://pypi.org/project/yfinance/
- TimescaleDB hypertable: https://docs.timescale.com/use-timescale/latest/hypertables/
- Polygon.io REST API: https://polygon.io/docs/stocks/get_v2_aggs_ticker__stocksticker__range__multiplier___timespan___from___to_
- ARQ task queue: https://arq-docs.helpmanual.io/

---

### Module 2: News Ingestion (Per Source)

**What it must do:**

Fetch news articles from all configured sources, normalize each article to a common schema,
deduplicate against already-stored articles using ChromaDB semantic similarity, extract ticker
mentions, score each article with VADER (fast pass), enqueue for FinBERT deep scoring,
store in MongoDB, and index in Elasticsearch.

**Sources (each is a separate DataSourcePlugin):**
- NewsAPI.org (100 calls/day)
- GNews API (100 calls/day)
- Finnhub news endpoint (60 calls/min)
- RSS feeds: Reuters, Bloomberg public, CNBC, MarketWatch, Seeking Alpha, The Motley Fool,
  Benzinga, Yahoo Finance RSS, CoinDesk, CoinTelegraph, Decrypt
- User-custom RSS feeds (user-added via dashboard, tagged with tickers)

**Normalized article schema:**

```python
@dataclass
class NewsArticle:
    url: str                    # unique identifier
    source_name: str
    source_type: str            # "api" or "rss"
    headline: str
    summary: str | None
    published_at: datetime
    ticker_symbols: list[str]   # extracted from content
    vader_score: float | None   # populated immediately
    finbert_score: float | None # populated after deep scoring
    embedding: list[float] | None  # populated after vectorization
    is_duplicate: bool
```

**Databases used:**
- **MongoDB** — `news_articles` collection (flexible schema per source)
- **Elasticsearch** — `news_index` (full-text search)
- **ChromaDB** — `news_articles` collection (semantic dedup)
- **TimescaleDB** — `sentiment_scores` hypertable (aggregated daily score per ticker)
- **InfluxDB** — `news_rate` bucket (publication rate per ticker per hour)
- **DataStax Astra** — `api_call_log` for all API calls

**Paradigm demonstrated:** Document store with flexible schema (MongoDB), full-text search
(Elasticsearch), vector similarity for deduplication (ChromaDB), time-series for publication
rate (InfluxDB).

**Implementation requirements:**
- RSS feeds are polled with `feedparser` on a 15-minute ARQ cron schedule.
- Deduplication: embed the headline + summary with `sentence-transformers` (all-MiniLM-L6-v2),
  query ChromaDB for nearest neighbor. If cosine similarity ≥ 0.95, mark as duplicate and do
  not store in MongoDB or index in Elasticsearch.
- Ticker extraction: use a simple regex match against the known ticker list. For articles
  mentioning "Apple" without "AAPL", use a company name → ticker lookup table built at startup.
- VADER scoring: score immediately in the ingestion worker (fast, no GPU needed).
- FinBERT scoring: enqueue a separate ARQ task for each unscored article. FinBERT tasks run on
  the ML sidecar's gRPC endpoint (`SentimentService.ScoreText`).

**Documentation links:**
- feedparser: https://feedparser.readthedocs.io/
- sentence-transformers: https://www.sbert.net/
- NewsAPI: https://newsapi.org/docs/endpoints/everything

---

### Module 3: Reddit Ingestion and Sentiment

**What it must do:**

Use PRAW to authenticate with the Reddit API and poll configured subreddits for new posts
mentioning tracked tickers. Score each post with VADER immediately. Store posts in MongoDB.
Index in Elasticsearch. Write mention count time-series to InfluxDB. Compute hourly and daily
sentiment aggregates and write to the TimescaleDB `sentiment_scores` hypertable. Surface the
most bullish and most bearish posts per ticker in the dashboard sentiment panel.

**Default subreddits:**
r/investing, r/stocks, r/wallstreetbets, r/cryptocurrency, r/Bitcoin, r/ethtrader,
r/SecurityAnalysis, r/StockMarket

**Per-ticker configurable:** users can add any subreddit to any ticker's tracking list via the
ticker configuration panel in the dashboard.

**Databases used:**
- **MongoDB** — `reddit_posts` collection (nested comment structure)
- **Elasticsearch** — `reddit_index` (full-text search)
- **InfluxDB** — `mention_counts` and `sentiment_stream` buckets (high-frequency stream)
- **TimescaleDB** — `sentiment_scores` hypertable (daily aggregates)
- **DataStax Astra** — Reddit API call log

**Paradigm demonstrated:** Document store for nested structures (Reddit thread = post + comments
embedded), high-frequency time-series write path (InfluxDB), VADER fast sentiment scoring.

**Implementation requirements:**
- PRAW rate limit: Reddit allows 100 requests per minute per authenticated app. Use one PRAW
  instance per worker process. Track calls in Valkey.
- Post scoring: VADER on title only (fast), then VADER on body if body > 50 words.
- Comment scoring: score top 10 comments by upvotes, weighted by upvote count / max_upvotes.
- Mention detection: a ticker is mentioned if its symbol OR company name appears in the title
  or body. WSB-specific: map common meme references ("stonks", "$BB calls") to tickers.
- Historical pull: on initial subreddit tracking setup, use PRAW `submissions` sorted by "top"
  over "month" and "year" to build a sentiment history baseline.

**Documentation links:**
- PRAW: https://praw.readthedocs.io/
- PRAW rate limits: https://praw.readthedocs.io/en/stable/getting_started/ratelimits.html
- VADER: https://github.com/cjhutto/vaderSentiment

---

### Module 4: On-Chain Data Ingestion

**What it must do:**

Fetch on-chain metrics for crypto tickers from Glassnode, IntoTheBlock, Blockchain.com, and
Etherscan. Normalize metrics to a common schema. Store in MongoDB and TimescaleDB. Use as
features in the ML prediction pipeline for crypto tickers.

**Metrics by source:**
- **Glassnode** (free tier, BTC and ETH): SOPR, MVRV ratio, exchange inflow/outflow, hash rate,
  active addresses, NVT ratio
- **IntoTheBlock** (free tier): large transaction volume, concentration ratio (what % is held by
  top 10 addresses), in/out of the money above/below current price
- **Blockchain.com** (free, no key): Bitcoin transaction count, average fee, total hashrate,
  mempool size
- **Etherscan** (free key): gas price (gwei average), pending transactions, ETH burned per day

**Databases used:**
- **MongoDB** — `onchain_metrics` collection (metric name + value + timestamp per source)
- **TimescaleDB** — aggregated on-chain metrics as time-series for ML feature engineering
- **DataStax Astra** — API call log

**Paradigm demonstrated:** API fan-out aggregation, multi-source data normalization.

**Implementation requirements:**
- Glassnode free tier has specific available metrics — check `https://api.glassnode.com/v1/metrics/endpoints`
  at startup and cache the list of available metric paths.
- On-chain metrics are leading indicators for crypto prices — write them to a fast-access cache
  in Valkey (`onchain:latest:{symbol}:{metric}`) for the ML feature pipeline to read without
  database queries.
- Fetch frequency: every 15 minutes during market hours (24/7 for crypto).

**Documentation links:**
- Glassnode API: https://docs.glassnode.com/basic-api/api/
- Etherscan API: https://docs.etherscan.io/api-endpoints/stats
- Blockchain.com API: https://www.blockchain.com/explorer/api/blockchain_api

---

### Module 5: Technical Indicator Computation

**What it must do:**

After every OHLCV update, compute the full set of standard technical indicators for each ticker
and store the computed values as a snapshot in the `technical_indicators` TimescaleDB hypertable.
Expose computed indicators to the ML feature pipeline and to the web dashboard chart view.

**Indicators computed (ta):**

*Trend:* SMA(20), SMA(50), SMA(200), EMA(12), EMA(26)
*Momentum:* RSI(14), MACD line, MACD signal, MACD histogram, Stochastic %K(14,3), Stochastic
%D(14,3), Williams %R(14)
*Volatility:* Bollinger Bands upper/middle/lower(20,2), ATR(14)
*Volume:* OBV (On-Balance Volume), VWAP (Volume Weighted Average Price)
*Trend Strength:* ADX(14)
*Custom:* Support/resistance levels (local minima/maxima over 20-day window), Fibonacci
retracement levels from 52-week high/low

**Databases used:**
- **TimescaleDB** — `technical_indicators` hypertable (primary store, one row per ticker per day)
- **Valkey** — `indicators:latest:{symbol}` cache (TTL: 4h, for ML feature reads)
- **DuckDB in-memory** — live computation for dashboard "current indicators" panel

**Paradigm demonstrated:** Time-series snapshot storage, computed column cache pattern.

**Implementation requirements:**
- Use `ta` for all indicator computations — it is pure Python with no C dependencies.
- Minimum lookback period: 200 trading days (for SMA(200)). Tickers with less than 200 days of
  history will have NULL values for SMA(200) until sufficient data accumulates.
- Normalization: do NOT store normalized values in `technical_indicators`. Store raw values.
  Normalization happens in the ML feature engineering pipeline at training/inference time.
- After computing indicators, serialize the full indicator row to JSON and write to Valkey
  cache immediately, before the database write completes. The ML pipeline reads from Valkey.
- Run as an ARQ task triggered by the completion of each OHLCV ingestion task (chained tasks).

**Documentation links:**
- ta: https://github.com/bukosabino/ta
- ta docs: https://technical-analysis-library-in-python.readthedocs.io/
- ATR: https://school.stockcharts.com/doku.php?id=technical_indicators:average_true_range_atr
- VWAP: https://school.stockcharts.com/doku.php?id=technical_indicators:vwap_intraday

---

### Module 6: ML Prediction Pipeline

**What it must do:**

For each active ticker, assemble a complete feature vector from all available data sources, call
the ML sidecar's gRPC endpoint, receive the prediction response (direction + confidence for all
four horizons + component scores), store the prediction in the TimescaleDB `predictions`
hypertable, and publish the new prediction to the Valkey pub/sub channel.

**Feature vector composition (per ticker):**

```
OHLCV returns:        5-day, 10-day, 20-day returns; log returns
Technical indicators: RSI, MACD hist, BB position, ATR normalized, ADX,
                      Stochastic %K, Williams %R, OBV change, VWAP distance
Fundamental (stocks): P/E, P/B, EPS surprise (last 4 quarters), revenue growth
Sentiment scores:     Reddit combined score, news combined score, 7-day trend,
                      30-day trend, post count, article count
Macro indicators:     Federal funds rate, 10Y yield, VIX, CPI YoY, yield curve slope
Earnings:             Days until next earnings, last EPS surprise magnitude
Insider activity:     Net insider buy/sell ratio over last 90 days
Short interest:       Short interest ratio (if available)
On-chain (crypto):    SOPR, MVRV, exchange inflow/outflow, active addresses
Sector:               Sector vs SPY 5-day return, sector momentum
Correlation:          SPY correlation (90-day), QQQ correlation (90-day)
```

**ML sidecar gRPC interface:**

```protobuf
service PredictionService {
    rpc Predict (PredictionRequest) returns (PredictionResponse);
    rpc Train   (TrainingRequest)   returns (TrainingResponse);
    rpc Status  (StatusRequest)     returns (StatusResponse);
}

message PredictionRequest {
    string symbol = 1;
    repeated float feature_vector = 2;
    string feature_schema_version = 3;
}

message PredictionResponse {
    string symbol = 1;
    repeated HorizonPrediction horizons = 2;
    bool anomaly_flag = 3;
    float isolation_score = 4;
}

message HorizonPrediction {
    string horizon = 1;          // "1d", "3d", "7d", "30d"
    string direction = 2;        // "UP", "FLAT", "DOWN"
    float confidence = 3;        // 0.0 - 100.0
    float lstm_confidence = 4;
    float xgb_confidence = 5;
    float lgbm_confidence = 6;
    float sentiment_score = 7;
}
```

**Databases used:**
- **TimescaleDB** — `predictions` hypertable (store every prediction)
- **Valkey** — `predict:latest:{symbol}:{horizon}` (4-hour TTL for fast dashboard reads)
- **Valkey pub/sub** — `pubsub:price_updates` channel to push new predictions to connected
  WebSocket clients
- **MongoDB** — `prediction_explanations` (SHAP values and feature importances)
- **SQLite event journal** — every prediction appended as an immutable event
- **MinIO** — ML model binary files (LSTM checkpoints, XGBoost models)

**Paradigm demonstrated:** gRPC client-server (the most important architecture demonstration in
this module), ML ensemble, feature engineering pipeline, SHAP explainability.

**Implementation requirements:**
- Feature assembly is a pure function: `assemble_features(symbol, timestamp) -> FeatureVector`.
  It reads from Valkey caches first (fast path), falls back to database queries.
- The gRPC call is wrapped with a 5-second timeout. If the ML sidecar is unreachable, use the
  last stored prediction from Valkey and mark it as "stale" in the response.
- After storing a new prediction, compare it to the previous prediction. If direction changed,
  publish a `PredictionChangedEvent` to the event bus.
- The prediction stored in the database includes the full feature vector hash (SHA-256 of the
  serialized feature vector) for reproducibility auditing.

**Documentation links:**
- gRPC Python: https://grpc.io/docs/languages/python/quickstart/
- protobuf: https://protobuf.dev/programming-guides/proto3/
- SHAP: https://shap.readthedocs.io/

---

### Module 7: Alert and Notification System

**What it must do:**

Subscribe to the event bus for all alert-triggering events. For each event, evaluate whether any
user has a matching alert configuration. For each matching configuration, determine which delivery
channels are enabled. Dispatch the alert through all enabled channels. Log the delivery attempt
and outcome in the `notification_log` PostgreSQL table.

**Alert evaluation flow:**

```
Event published to Valkey pub/sub
  → AlertEvaluator receives event
  → Queries user alert configs from PostgreSQL (cached in Valkey for 5 min)
  → Checks feature flag for each channel (e.g., flag:alert.sms)
  → For each enabled channel, calls AlertDeliveryPlugin.deliver()
  → Writes delivery result to notification_log
  → If all channels failed, publishes ApplicationErrorEvent
```

**Alert delivery plugins (one per channel):**

1. **BrowserPushPlugin** — calls OneSignal REST API with notification payload
2. **MobilePushPlugin** — calls OneSignal REST API targeting mobile subscribers
3. **EmailPlugin** — sends via SMTP using `aiosmtplib`; renders Jinja2 HTML template
4. **SMSPlugin** — calls Twilio REST API; feature-flagged off by default
5. **DiscordPlugin** — posts to Discord channel or DMs linked user via `discord.py`
6. **VoicePlugin** — triggers proactive Alexa announcement or Google Home TTS broadcast

**Databases used:**
- **PostgreSQL** — `alert_configs` and `notification_log` tables
- **Valkey** — alert config cache, pub/sub event bus
- **DataStax Astra** — high-volume notification event logging

**Paradigm demonstrated:** Pub/sub event bus, plugin pattern for delivery channels, feature flags
as runtime circuit breakers.

**Documentation links:**
- OneSignal REST API: https://documentation.onesignal.com/reference/create-notification
- Twilio Python: https://www.twilio.com/docs/libraries/python
- aiosmtplib: https://aiosmtplib.readthedocs.io/

---

### Module 8: API Quota Tracker

**What it must do:**

Track API call counts for every external API source in both Valkey (live counters) and PostgreSQL
(persistent reference). Display current usage in the admin settings panel. Send quota warning
alerts when any source approaches its daily or monthly limit. Support manual counter reset for
development testing. Support toggling any source as "unlimited" (disables counting).

**Two-layer architecture:**
- **Hot path:** Valkey `INCR` counter with TTL set to seconds until the API's reset time.
  Called synchronously with every API call (adds ~1ms latency).
- **Cold path:** PostgreSQL `api_quotas` table updated every 5 minutes from Valkey counters.
  Used for persistence across container restarts.

**Tracking API sources:**
| Source | Reset Frequency | Counter Key |
|--------|----------------|-------------|
| Alpha Vantage | Daily (midnight UTC) | `quota:alpha_vantage:daily` |
| NewsAPI.org | Daily (midnight UTC) | `quota:newsapi:daily` |
| GNews | Daily (midnight UTC) | `quota:gnews:daily` |
| CoinMarketCap | Daily (midnight UTC) and monthly | `quota:coinmarketcap:daily`, `:monthly` |
| Polygon.io | Per-minute (not counted as daily) | `quota:polygon:per_minute` with 60s TTL |
| Finnhub | Per-minute | `quota:finnhub:per_minute` with 60s TTL |

**Databases used:**
- **Valkey** — live INCR counters with TTL (primary quota tracking)
- **PostgreSQL** — `api_quotas` table (persistent reference, low-frequency writes)

**Paradigm demonstrated:** Valkey INCR as an atomic rate-limiting counter; dual write-through
cache pattern.

**Implementation requirements:**
- `QuotaMiddleware` wraps every `DataSourcePlugin.fetch()` call. Before each external HTTP
  request, it increments the Valkey counter and checks if the result exceeds the configured
  limit. If over limit, raises `QuotaExceededException` instead of making the HTTP call.
- On `QuotaExceededException`, the ingestion worker logs the skip, waits until reset time, and
  does not retry.
- The Dashboard quota panel shows: source name, current count, limit, percentage used as a
  progress bar, and estimated reset time.

---

### Module 9: Discord Bot

**What it must do:**

Provide a complete slash-command interface to MarketPulse via Discord. All commands respond with
structured embeds. Chart commands generate chart images and attach them. Multi-item responses use
paginated embeds. The bot connects to the FastAPI backend via internal HTTP (not direct database
access).

**Complete Command List:**

| Command | Arguments | Response Format | Description |
|---------|-----------|----------------|-------------|
| `/predict` | `ticker` | Embed with 4 horizon cards | UP/FLAT/DOWN + confidence for 1d/3d/7d/30d |
| `/watchlist` | `name` | Paginated embed (10 tickers/page) | All tickers in a watchlist with current predictions |
| `/sentiment` | `ticker` | Embed + chart image attachment | Reddit and news sentiment breakdown with score chart |
| `/price` | `ticker` | Embed | Current price, 24h change %, 52-week high/low, volume |
| `/news` | `ticker` | Embed (5 headlines) | Latest 5 articles with FinBERT score and source |
| `/reddit` | `ticker`, `subreddit` (optional) | Paginated embed | Top Reddit posts today, sorted by score |
| `/chart` | `ticker`, `period` (1w/1m/3m/1y) | Chart image attachment | Candlestick chart with prediction overlay |
| `/quota` | — | Embed table | API quota status for all sources |
| `/alerts` | — | Embed list | Active alert configurations for linked user |
| `/add` | `ticker` | Confirmation embed | Add a ticker to tracking |
| `/accuracy` | `ticker` | Embed with accuracy grid | Historical prediction accuracy per horizon |
| `/macro` | — | Embed | Current macro indicators: fed rate, CPI, VIX, yield curve |
| `/earnings` | — | Paginated embed | Upcoming earnings for tracked tickers |
| `/insider` | `ticker` | Paginated embed | Recent SEC Form 4 filings |
| `/compare` | `ticker1`, `ticker2` | Side-by-side embed | Prediction + sentiment + price comparison |
| `/export` | `ticker`, `format` | Link embed | Link to web dashboard export endpoint |

**Chart generation (`/chart` and `/sentiment`):**

```python
import mplfinance as mpf
import matplotlib.pyplot as plt
import io

def generate_candlestick(df: pd.DataFrame, symbol: str, prediction: dict) -> bytes:
    # df has columns: Open, High, Low, Close, Volume with DatetimeIndex
    prediction_color = {"UP": "green", "FLAT": "gray", "DOWN": "red"}[prediction["direction"]]

    # Custom style matching MarketPulse dark theme
    mc = mpf.make_marketcolors(up='#26a69a', down='#ef5350', inherit=True)
    style = mpf.make_mpf_style(base_mpf_style='nightclouds', marketcolors=mc)

    # Add SMA overlays
    addplots = [
        mpf.make_addplot(df["SMA_20"], color="#f39c12", width=1.0, label="SMA20"),
        mpf.make_addplot(df["SMA_50"], color="#3498db", width=1.0, label="SMA50"),
    ]

    fig, axes = mpf.plot(
        df, type='candle', style=style, addplot=addplots,
        title=f"\n{symbol} — Prediction: {prediction['direction']} ({prediction['confidence']:.0f}%)",
        ylabel="Price (USD)", ylabel_lower="Volume",
        returnfig=True, volume=True, figratio=(16, 9), figscale=1.2
    )

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf.read()
```

**Databases used:**
- **No direct database access** — all data fetched from FastAPI internal endpoints
- **MinIO** — chart images stored and served via presigned URL (or sent directly as bytes)

**Paradigm demonstrated:** discord.py slash commands, image generation with mplfinance and
Pillow, paginated interaction patterns.

**Documentation links:**
- discord.py: https://discordpy.readthedocs.io/en/stable/
- mplfinance: https://github.com/matplotlib/mplfinance
- Discord interactions: https://discord.com/developers/docs/interactions/application-commands

---

### Module 10: Web Dashboard

**What it must do:**

Provide a React + Vite SPA that is the primary exploration and configuration surface. No page
reloads after initial load. Real-time price and prediction updates via WebSocket. All charts
rendered with Recharts.

**Pages and their primary components:**

**Home (/):** Default watchlist, ticker prediction cards sorted by confidence, quick search bar.

**Ticker Detail (/ticker/:symbol):**
- Candlestick chart with SMA/EMA overlays (Recharts ComposedChart)
- Prediction card row (four horizons, color-coded confidence)
- Tabs: Indicators | Sentiment | News | Reddit | Insider | Accuracy
- Gear icon → slide-out configuration panel (subreddits, alert thresholds, source weights)

**Watchlists (/watchlists):** Create, rename, delete watchlists. Drag-and-drop ticker reordering.

**Sentiment (/sentiment/:symbol):**
- Reddit sentiment line chart per subreddit over time (Recharts LineChart)
- News sentiment line chart per source over time
- Sentiment vs. price correlation chart
- Most bullish and bearish posts table with links

**Earnings (/earnings):** Calendar view of upcoming earnings for tracked tickers.

**Macro (/macro):** Federal funds rate chart (FRED data), 10Y yield, CPI YoY, VIX, yield curve.

**Settings (/settings):** Alert configuration table, notification channel toggles, API quota
gauges, 2FA enrollment, Discord linking.

**Admin (/admin):** Paradigm demo console (25 panels), feature flag toggles, API quota manual
reset, system health dashboard.

**Real-time updates (WebSocket):**
- On WebSocket connect, subscribe to all tickers in the user's active watchlists.
- Server publishes to `pubsub:price_updates` in Valkey.
- FastAPI WebSocket handler reads from Valkey pub/sub and pushes to connected clients.
- Client Redux store updates on message receipt, re-rendering only the changed ticker cards.

**Databases used:**
- **No direct database access** — all data fetched from FastAPI REST + WebSocket endpoints
- **Valkey** — WebSocket subscription management (server-side)

**State management:** Redux Toolkit with RTK Query for all API calls and cache management.

**Documentation links:**
- Recharts: https://recharts.org/en-US/api
- RTK Query: https://redux-toolkit.js.org/rtk-query/overview
- Vite: https://vitejs.dev/guide/

---

### Module 11: Mobile App

**What it must do:**

React Native CLI bare workflow app providing portfolio-at-a-glance view with push notifications.
Displays prediction cards, news ticker strip, and sentiment heat map. Receives push notifications
via OneSignal SDK. No configuration — read-only view of the same data as the web dashboard.

**Screens:**
- **Portfolio:** Vertical scroll list of prediction cards, sorted by confidence × magnitude
- **Ticker Detail:** Same analysis view as web, adapted for mobile (swipeable tabs)
- **Alerts:** History of received push notifications
- **Settings:** Notification preferences, OneSignal subscription management

**Push notification payload:**

```json
{
  "heading": "AAPL — High Confidence DOWN",
  "content": "87% confidence · 7-day horizon · Current: $189.42",
  "data": {
    "symbol": "AAPL",
    "direction": "DOWN",
    "confidence": 87,
    "horizon": "7d",
    "route": "/ticker/AAPL"
  }
}
```

**Paradigm demonstrated:** React Native bare workflow (no Expo), OneSignal mobile push
(no Firebase), deep linking from push notification to app screen.

**Documentation links:**
- React Native CLI: https://reactnative.dev/docs/environment-setup
- OneSignal React Native SDK: https://documentation.onesignal.com/docs/react-native-sdk

---

### Module 12: Voice Integration

**What it must do:**

Provide a read-only voice interface to MarketPulse predictions through Amazon Alexa (local skill)
and Google Home (local action). Handle natural-language intent parsing and respond with spoken
summaries of predictions, alerts, and macro indicators.

**Supported intents:**

| Intent | Example Utterance | Response |
|--------|------------------|---------|
| `GetPrediction` | "What is the prediction for Apple?" | "MarketPulse predicts Apple will go UP with 84% confidence over the next day." |
| `GetSentiment` | "Is the market bullish on Bitcoin?" | "Bitcoin's current sentiment score is 0.62, which is bullish. Reddit is positive at 0.71, news is moderate at 0.45." |
| `GetAlerts` | "What are today's alerts?" | "You have 2 alerts today. Apple crossed the high confidence threshold at 87%. Tesla had unusual volume detected at 9:45 AM." |
| `GetMacro` | "What is the current interest rate?" | "The federal funds rate is 5.25 to 5.50 percent as of July 2024." |
| `GetAccuracy` | "How accurate is the Apple prediction?" | "MarketPulse has been 72% accurate on Apple's 7-day predictions over the last 100 forecasts." |

**Alexa local skill:** Uses `ask-sdk-core` Python package. Deployed as a local HTTPS endpoint
(Cloudflare Tunnel exposes it). Alexa Developer Console configured to point to local endpoint.

**Google Home local action:** Uses Flask + Google Actions SDK (`google-auth`, `flask`). Local
endpoint exposed via same Cloudflare Tunnel. No Google Cloud required — local fulfillment only.

**Proactive announcements:** When the alert system generates a high-confidence prediction alert
and voice is in the enabled channels, the VoicePlugin sends a proactive Alexa announcement
to all registered Echo devices and a Google Home broadcast.

**Documentation links:**
- Alexa Skills Kit SDK for Python: https://developer.amazon.com/en-US/docs/alexa/alexa-skills-kit-sdk-for-python/overview.html
- Alexa local testing: https://developer.amazon.com/en-US/docs/alexa/custom-skills/test-a-custom-skill.html
- Google Actions SDK: https://developers.google.com/assistant/actions/sdk

---

### Module 13: RSS Bidirectional

**What it must do:**

**Ingest:** Consume RSS feeds from all configured sources using `feedparser` on a 15-minute
polling schedule. Each feed entry is processed by the news ingestion pipeline.

**Publish:** Expose a `GET /rss/predictions` endpoint from the FastAPI backend that generates a
valid RSS 2.0 XML feed of significant MarketPulse predictions and alerts. Subscribable by any
RSS reader. Items include: prediction direction, confidence, ticker, horizon, and a link to the
ticker detail page in the web dashboard.

**RSS 2.0 output format:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>MarketPulse Predictions</title>
    <link>https://your-domain/dashboard</link>
    <description>High-confidence stock and crypto predictions from MarketPulse</description>
    <item>
      <title>AAPL — UP (87% confidence, 7-day)</title>
      <link>https://your-domain/ticker/AAPL</link>
      <description>MarketPulse predicts AAPL will go UP over the next 7 trading days with 87% confidence.</description>
      <pubDate>Thu, 01 Aug 2024 14:32:00 +0000</pubDate>
      <guid>prediction:AAPL:7d:2024-08-01T14:32:00Z</guid>
    </item>
  </channel>
</rss>
```

Only predictions with confidence ≥ 75% are included in the published feed. Feed is regenerated
on each request (not cached) to ensure freshness.

**Documentation links:**
- feedparser: https://feedparser.readthedocs.io/
- RSS 2.0 specification: https://cyber.harvard.edu/rss/rss.html

---

### Module 14: Data Export

**What it must do:**

Allow users to export any data view from the web dashboard in five formats: CSV, PDF report,
raw JSON, raw HTML, and XML. Export is available from every data-bearing view via an export
button.

**Export formats by data type:**

| Data Type | CSV | PDF | JSON | HTML | XML |
|-----------|-----|-----|------|------|-----|
| OHLCV history | ✓ | ✓ | ✓ | ✓ | ✓ |
| Prediction history | ✓ | ✓ | ✓ | ✓ | ✓ |
| Sentiment scores | ✓ | ✓ | ✓ | ✓ | ✓ |
| News articles | ✓ | ✓ | ✓ | ✓ | ✓ |
| Technical indicators | ✓ | — | ✓ | ✓ | ✓ |
| Full ticker report | — | ✓ | ✓ | ✓ | — |

**PDF generation:** `reportlab` generates a structured PDF with the MarketPulse header, ticker
name and current prediction, summary table, and a static version of the candlestick chart
embedded as an image.

**Export files are written to MinIO** (`reports` bucket) and the user receives a presigned
download URL valid for 1 hour.

**Documentation links:**
- reportlab: https://www.reportlab.com/docs/reportlab-userguide.pdf
- MinIO presigned URLs: https://min.io/docs/minio/linux/developers/python/API.html#presigned_get_object

---

### Module 15: Authentication and 2FA

**What it must do:**

Implement email + password login with JWT access tokens. Support two independently enrollable
2FA methods: TOTP (Google Authenticator, Authy) and SMS/email code. Neither 2FA method is
required to complete account creation — both are optional. When both are enrolled, the user
chooses which to use at login. Discord account linking enables personalized Discord alerts.

**Auth flow:**

```
POST /auth/login
  → verify email + password (bcrypt)
  → if 2FA enrolled: return {requires_2fa: true, methods: ["totp", "sms"]}
  → client prompts user to choose method and submit code
  → POST /auth/verify-2fa
      → verify code (PyOTP for TOTP; check stored code + TTL for SMS/email)
      → return {access_token: <JWT>, refresh_token: <JWT>}
```

**JWT structure:**

```python
payload = {
    "sub": str(user.id),          # user ID
    "jti": str(uuid4()),          # unique token ID (for blocklist)
    "iat": now,                   # issued at
    "exp": now + timedelta(minutes=1440),  # 24-hour expiry
    "roles": ["user"],            # or ["user", "admin"]
}
```

**Token blocklist:** On logout, the JWT's `jti` is written to Valkey with TTL equal to the
token's remaining lifetime: `SET blocklist:{jti} 1 EX {remaining_seconds}`. The auth middleware
checks this on every request.

**TOTP enrollment flow:**

```python
import pyotp, qrcode, io

def generate_totp_setup(user: User) -> tuple[str, bytes]:
    secret = pyotp.random_base32()
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=user.email,
        issuer_name="MarketPulse"
    )
    qr = qrcode.QRCode()
    qr.add_data(totp_uri)
    qr.make(fit=True)
    img = qr.make_image()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return secret, buf.getvalue()
```

**Databases used:**
- **PostgreSQL** — `users` table (email, password_hash, totp_secret, discord_id)
- **Valkey** — JWT blocklist, SMS/email 2FA code store (5-minute TTL)
- **SQLite audit ledger** — every account change appended to hash chain

**Documentation links:**
- PyOTP: https://pyauth.github.io/pyotp/
- python-jose: https://python-jose.readthedocs.io/en/latest/
- passlib bcrypt: https://passlib.readthedocs.io/en/stable/lib/passlib.hash.bcrypt.html

---

### Module 16: Ticker Management

**What it must do:**

Allow users to add any stock ticker, ETF, index, or cryptocurrency to tracking. On addition, the
system auto-enriches the ticker (fetches name, sector, industry, market cap, logo). Tickers are
stored in PostgreSQL (relational metadata) and registered in ZODB (object-oriented registry with
`StockTicker` and `CryptoTicker` subclasses). Tickers can be deactivated (stops data ingestion)
but not deleted (preserves historical data integrity).

**Auto-enrichment on ticker add:**

```python
async def enrich_ticker(symbol: str) -> TickerMetadata:
    info = yf.Ticker(symbol).info
    return TickerMetadata(
        name=info.get("longName") or info.get("shortName"),
        sector=info.get("sector"),
        industry=info.get("industry"),
        market_cap=info.get("marketCap"),
        asset_type=detect_asset_type(info),
        logo_url=info.get("logo_url"),
    )
```

**Databases used:**
- **PostgreSQL** — `tickers` table
- **ZODB** — ticker object registry (`StockTicker` / `CryptoTicker`)
- **Neo4j** — ticker node creation + sector/index membership edges
- **SQLite audit ledger** — ticker addition/deactivation logged

---

### Module 17: Watchlist Management

**What it must do:**

Allow users to create named watchlists, add/remove tickers, set a default watchlist, and reorder
tickers within a watchlist. Support up to 20 watchlists per user, 100 tickers per watchlist.

**Databases used:**
- **PostgreSQL** — `watchlists` and `watchlist_tickers` tables

---

### Module 18: Earnings Calendar

**What it must do:**

Maintain a calendar of upcoming earnings announcements for all tracked tickers. Show the
calendar in the web dashboard and Discord `/earnings` command. Send earnings-approaching alerts
when configured.

**Data sources:**
- Yahoo Finance earnings calendar via `yfinance` (primary)
- Finnhub earnings calendar endpoint (secondary, for cross-verification)

**Databases used:**
- **PostgreSQL** — `earnings_calendar` table (symbol, report_date, estimate_eps, actual_eps,
  surprise_percent)
- **TimescaleDB** — earnings surprise history as a time-series for ML feature use

---

### Module 19: Insider Trading Tracker

**What it must do:**

Poll the SEC EDGAR API for Form 4 filings (insider transactions) and Schedule 13D/G filings
(ownership changes) for all tracked tickers. Extract insider name, role, transaction type
(buy/sell), shares, price, and filing date. Store in MongoDB. Surface in the dashboard ticker
detail view and Discord `/insider` command. Generate an insider trading alert when a new filing
is detected.

**EDGAR API endpoint:**
`https://data.sec.gov/submissions/CIK{cik_padded}.json` for filing history
`https://efts.sec.gov/LATEST/search-index?q=%22{symbol}%22&dateRange=custom&startdt={date}&forms=4`

**Databases used:**
- **MongoDB** — `sec_filings` collection
- **Neo4j** — `INSIDER_BOUGHT` / `INSIDER_SOLD` relationships between person nodes and ticker nodes
- **TimescaleDB** — aggregated insider buy/sell ratio as a time-series feature

---

### Module 20: Macro Indicators Dashboard

**What it must do:**

Fetch, store, and display macroeconomic indicators from FRED, US Treasury, and BLS. Show current
values and historical charts. Include these as features in the ML prediction pipeline for all
tickers.

**Indicators tracked:**
| Indicator | FRED Series ID | Update Frequency |
|-----------|---------------|-----------------|
| Federal Funds Rate | `FEDFUNDS` | Monthly |
| 10-Year Treasury Yield | `DGS10` | Daily |
| 2-Year Treasury Yield | `DGS2` | Daily |
| CPI (YoY inflation) | `CPIAUCSL` | Monthly |
| Unemployment Rate | `UNRATE` | Monthly |
| VIX | `VIXCLS` | Daily |
| GDP Growth Rate | `A191RL1Q225SBEA` | Quarterly |

**Yield curve slope** = DGS10 - DGS2 (computed). Inversion (negative) historically precedes
recessions and is significant for ML models predicting medium-term returns.

**Databases used:**
- **PostgreSQL** — `macro_indicators` table
- **TimescaleDB** — macro indicator time-series as ML features
- **Valkey** — `macro:latest:{series_id}` cache (24-hour TTL, daily update)

---

### Module 21: Sentiment Dashboard

**What it must do:**

Display a comprehensive sentiment analysis view for each ticker: Reddit sentiment per subreddit
over time (chart), news sentiment per source over time (chart), overall combined sentiment score
with configurable source weights, most bullish and most bearish Reddit posts (with links),
most bullish and most bearish news headlines (with source and link), and a sentiment vs. price
correlation chart (did sentiment precede price movement?).

**Sentiment vs. price correlation:** Compute Pearson correlation between sentiment score (lagged
by 1, 2, 3, and 7 days) and next-day return. Show the optimal lag in the dashboard. High
correlation with a 2-day lag means "when sentiment spikes, price tends to follow 2 days later."

**Databases used:**
- **TimescaleDB** — `sentiment_scores` hypertable (primary source for all sentiment charts)
- **MongoDB** — raw Reddit posts and news articles (for most bullish/bearish tables)
- **InfluxDB** — high-frequency sentiment stream (real-time chart updates during market hours)
- **DuckDB in-memory** — sentiment vs. price correlation computation

---

### Module 22: Prediction Accuracy Tracker

**What it must do:**

Track the accuracy of every prediction by recording the actual price outcome when the prediction
horizon elapses. Compute rolling accuracy metrics (last 20, last 100 predictions) per ticker per
horizon. Display accuracy in the dashboard and Discord `/accuracy` command. Send a model accuracy
degraded alert when rolling accuracy drops below threshold.

**Outcome resolution process (daily job):**
1. Query all predictions where `outcome_time IS NULL AND prediction_time + horizon <= NOW()`.
2. For each prediction, fetch the actual closing price at the outcome time from TimescaleDB.
3. Compute actual direction: if close[outcome] > close[prediction_time] × 1.01, direction = UP;
   if close[outcome] < close[prediction_time] × 0.99, direction = DOWN; else FLAT.
4. Set `actual_direction`, `was_correct`, and `outcome_time` on the prediction row.
5. Recompute rolling accuracy for the ticker/horizon combination.

**Databases used:**
- **TimescaleDB** — `predictions` hypertable (outcome_time, actual_direction, was_correct fields)
- **DuckDB persistent** — long-term accuracy trend analytics over Parquet archives

---

### Module 23: Correlation Graph Explorer

**What it must do:**

Display the ticker correlation graph in the web dashboard with interactive node-link visualization.
Allow users to explore which tickers move together, which are inversely correlated, and which
clusters represent sector behavior. The Discord `/compare` command queries the same graph to
explain why two tickers are or are not correlated.

**Graph computation:**
- Pearson correlation matrix computed over 90-day rolling returns for all tracked tickers.
- An edge is added between ticker A and ticker B if |correlation| > 0.7.
- Edge weight = |correlation coefficient|. Edge color = green (positive) or red (negative).
- Graph recomputed weekly by an ARQ cron job.
- NetworkX persists the graph to SQLite (Database 15) for restart persistence.
- Neo4j stores the graph as `CORRELATED_WITH` relationships for complex graph queries.

**Web dashboard visualization:** Recharts cannot render network graphs — use `react-force-graph`
or `vis-network` for the interactive force-directed layout.

**Databases used:**
- **NetworkX → SQLite** — in-process graph with SQLite persistence
- **Neo4j AuraDB** — `CORRELATED_WITH` relationships for graph queries
- **TimescaleDB** — OHLCV data source for correlation computation

---

### Module 24: Admin Paradigm Demo Console

**What it must do:**

Provide an admin-only section of the web dashboard with 25 dedicated panels, one per paradigm
category, each showing a live demonstration of the specific sub-paradigms implemented in that
category. Panels show real data, real database operations, and real output from the running
system. This is the central proof-of-implementation exhibit.

See README_4_EXPANDED_OUTLINE.md for the detailed description of each panel.

---

### Module 25: Feature Flag Management

**What it must do:**

Display all feature flags in the admin settings panel. Allow toggling any flag on or off at
runtime. Changes take effect immediately (written to Valkey, picked up by all workers within
their next polling cycle). Audit every flag change to the SQLite audit ledger.

**Flag categories:**
- `datasource.*` — Enable/disable any data source
- `ml.*` — Enable/disable any ML model component
- `alert.*` — Enable/disable any alert delivery channel
- `feature.*` — Experimental feature toggles

**Two-phase rollout:** Experimental features can be enabled for `["admin"]` role only by
combining feature flags with OPA authorization rules.

---

## Discord Bot Feature Flag Map

The bot's behavior changes automatically when flags are flipped:

```python
# Before executing any command
async def check_feature_flags(source_name: str):
    enabled = await redis.get(f"flag:datasource.{source_name}")
    if enabled == "false":
        raise FeatureDisabledException(f"{source_name} is currently disabled")
```

---

## Module Dependency Graph

The following modules must be complete before the listed modules can be implemented:

```
Database adapters (Module 4 in build guide)
  → OHLCV Ingestion (Module 1)
      → Technical Indicators (Module 5)
          → ML Prediction Pipeline (Module 6)
              → Alert System (Module 7)
                  → Discord Bot (Module 9)
                  → Web Dashboard (Module 10)
                  → Mobile App (Module 11)
                  → Voice Integration (Module 12)
  → News Ingestion (Module 2)
      → Sentiment Dashboard (Module 21)
  → Reddit Ingestion (Module 3)
      → Sentiment Dashboard (Module 21)
  → Technical Indicators (Module 5)
      → ML Prediction Pipeline (Module 6)
  → Prediction Accuracy Tracker (Module 22)
      → (depends on ML Prediction Pipeline having run for ≥ 1 horizon period)

Authentication (Module 15)
  → All user-facing modules (must be built before any module that has user-specific config)

Ticker Management (Module 16)
  → All ingestion modules (must exist before ingestion workers run)
```
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

- [x] 3.1 Implement `app/domain/ticker.py` — `Ticker`, `StockTicker`, `CryptoTicker`, `IndexTicker`
      (Python dataclasses; ZODB-persistent versions come in Phase 4).
- [x] 3.2 Implement `app/domain/prediction.py` — `Prediction`, `HorizonPrediction`,
      `PredictionOutcome`. Include `is_actionable()` method (returns True if confidence ≥ 75%).
- [x] 3.3 Implement `app/domain/sentiment.py` — `SentimentScore`, `NewsArticle`, `RedditPost`.
- [x] 3.4 Implement `app/domain/alert.py` — `Alert`, `AlertConfig`, `NotificationPreference`,
      `DeliveryResult`.
- [x] 3.5 Implement `app/domain/watchlist.py` — `WatchList`, `WatchListEntry`.
- [x] 3.6 Implement `app/domain/quota.py` — `APIQuota`, `QuotaStatus`.
- [x] 3.7 Implement `app/domain/feature_vector.py` — `FeatureVector` with validation that
      all values are finite floats and the schema version matches the expected constant.
- [x] 3.8 Write unit tests for all domain objects. Focus on edge cases:
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
# MarketPulse — The Course

> One plain-English lesson before each build phase. No assumed knowledge.
> Each lesson answers: what is this, why does it exist, and how does MarketPulse use it?
> Read the lesson, then build the phase. The exercise for each lesson is in README_8.

---

## Lesson 0 — Developer Environment: Why Every Tool in the Stack

**What this is about:** Before writing a single line of MarketPulse code, you need a consistent
environment. This lesson explains why each tool in the Phase 0 setup exists and what it protects
you from.

**Python version pinning.** Python 3.11 is specified — not 3.12 or 3.13. ML libraries like
PyTorch and XGBoost maintain independent release cycles. A new Python minor version can break
a C extension that hasn't been recompiled yet, and those breaks are hard to debug. Pinning to
a known-good version means your training code will run the same way on Tuesday as it did on Monday.
`pyenv` lets you install multiple Python versions side-by-side and switch between projects without
conflicts. The virtual environment (`.venv`) isolates MarketPulse's packages from every other
project on the machine.

**Ruff, Black, Mypy.** These three tools enforce three different kinds of code correctness:
- **Black** is a formatter. It reformats your code to a consistent style so every file looks the
  same, regardless of who wrote it. You stop arguing about spaces and focus on logic.
- **Ruff** is a linter. It catches code patterns that are likely bugs: undefined variables,
  unused imports, mutable default arguments, and about 500 other mistakes.
- **Mypy** is a type checker. Python is dynamically typed but allows optional type annotations.
  Mypy reads those annotations and catches type mismatches before runtime — for example, if a
  function that returns `str | None` has its return value passed to a function that expects `str`,
  Mypy catches it at development time instead of in production at 2 AM.

**Pre-commit hooks.** These run automatically before every `git commit`. If ruff finds a problem
or mypy has a type error, the commit is rejected until you fix it. The benefit: broken code
never enters version history.

**Why this matters for MarketPulse:** The system has 17 database adapters, 25+ background tasks,
and ML code that's easy to write incorrectly. Type annotations on function signatures (especially
around database repositories and the ML feature vector) catch whole categories of errors that
would otherwise only appear when running an ingestion pipeline overnight.

**Documentation links:**
- pyenv: https://github.com/pyenv/pyenv
- Black: https://black.readthedocs.io/
- Ruff: https://docs.astral.sh/ruff/
- Mypy: https://mypy.readthedocs.io/

---

## Lesson 1 — Databases: Why 17 and What Each One Is For

**What this is about:** Most applications use one database. MarketPulse uses 17. This sounds
absurd until you understand that different data has different shapes, and trying to force all
data into one shape makes every operation harder.

**Relational databases (PostgreSQL).** A relational database stores data in tables with rows and
columns, enforces relationships between tables (a `prediction` must reference a real `ticker`),
and lets you ask complex cross-table questions with SQL. PostgreSQL is the most capable
open-source relational database. It handles the core entities: tickers, users, OHLCV prices,
predictions, alert configs, API quotas.

**TimescaleDB.** A PostgreSQL extension that adds one critical feature: hypertables. A hypertable
automatically partitions time-series data into "chunks" by time range (say, one chunk per month).
When you query `WHERE time > NOW() - INTERVAL '7 days'`, PostgreSQL only opens the most recent
chunk instead of scanning the entire table. For OHLCV data (potentially millions of rows), this
makes the difference between a 50ms query and a 30-second query. TimescaleDB also compresses old
chunks using a columnar format, achieving roughly 10:1 compression on OHLCV data.

**Key-value store (Valkey).** A key-value store is the simplest possible database: a key points
to a value. Valkey keeps everything in RAM, which makes it extremely fast (sub-millisecond reads).
MarketPulse uses it as a cache (current stock prices, ML feature values), as a quota counter
(Valkey's `INCR` command is atomic and can be given a TTL, making it perfect for "100 API calls
per day"), and as an event bus (pub/sub messaging between the ingestion workers and the alert
system).

**Document store (MongoDB).** Relational databases require a fixed schema — every row in a table
has the same columns. Document stores let each record (document) have its own structure. A news
article from one source might have a `summary` field; an article from another source might have
`full_text`. MongoDB handles both without a schema change. It's used for news articles, Reddit
posts, SEC filings, and ML prediction explanations — all of which have variable structure.

**Vector store (ChromaDB).** A vector is a list of numbers representing the meaning of a piece
of text. Two semantically similar sentences (even if they use different words) will have similar
vectors. A vector database indexes these vectors so you can find the most similar documents to a
query. MarketPulse uses ChromaDB to deduplicate news: before storing an article, it checks whether
any existing article is more than 95% similar. If so, the new article is a near-duplicate and gets
discarded.

**Search engine (Elasticsearch).** Traditional databases search by exact match. A search engine
builds an inverted index, enabling full-text search across millions of documents in milliseconds.
"Find all articles that mention 'Fed rate hike' or 'interest rates'" is a natural-language search
operation — exactly what Elasticsearch is built for.

**Time-series database (InfluxDB).** Like TimescaleDB but purpose-built for metrics and
measurements. MarketPulse uses it for real-time data streams that don't need long-term retention:
Reddit mention counts, live sentiment scores. InfluxDB provides excellent tools for downsampling
old data (store per-minute data for 7 days, then aggregate to hourly for 30 days, then daily
forever).

**Object store (MinIO).** A database stores structured data; an object store stores arbitrary
files (blobs). MinIO is a self-hosted version of Amazon S3. MarketPulse stores candlestick chart
images, ML model files, and nightly Parquet archives of OHLCV data in MinIO.

**Graph databases (NetworkX + Neo4j).** In a relational database, relationships are implicit (a
foreign key). In a graph database, relationships are first-class data. NetworkX is an in-memory
Python graph library. Neo4j is a production graph database. MarketPulse uses them to store: which
tickers are correlated with each other, which sectors contain which companies, which insiders
have traded in which stocks. Graph queries like "find all tickers that are correlated with AAPL
and have been upgraded by an analyst this week" are trivial in a graph database and nightmarish
in a relational one.

**Embedded databases (SQLite, ZODB, DuckDB).** These run inside the Python process, with no
separate server. SQLite stores the event journal and audit ledger. ZODB persists Python objects
directly (the ticker registry). DuckDB is an embedded analytical query engine — it can read
Parquet files from MinIO and run aggregation queries directly without loading data into memory
first.

**Documentation links:**
- TimescaleDB hypertables: https://docs.timescale.com/use-timescale/latest/hypertables/
- Valkey TTL: https://valkey.io/commands/expire/
- ChromaDB: https://docs.trychroma.com/
- Elasticsearch inverted index: https://www.elastic.co/guide/en/elasticsearch/reference/current/documents-indices.html
- DuckDB: https://duckdb.org/docs/

---

## Lesson 2 — CI/CD and Code Quality: Automating the Boring Parts

**What this is about:** CI/CD (Continuous Integration / Continuous Deployment) is the practice
of automatically running tests and quality checks every time code changes. This lesson explains
why you set up the pipeline before writing any application code.

**Why automation before code?** Without automation, quality checks are things you remember to
run when you feel like it. With automation, they run on every push, every pull request, every
merge — guaranteed. The earlier you set up the pipeline, the more it catches. Setting it up
after Phase 10 would mean 10 phases of potentially broken code accumulating.

**GitHub Actions.** A free CI/CD system built into GitHub. You write a YAML file describing
"when code is pushed, run these commands." The commands run on GitHub's servers, not yours.
If any command fails, the pipeline is marked failed and (if you set up branch protection) the
code cannot be merged.

**Branch protection.** A GitHub setting that says: "before any code can merge into `main`, the
CI pipeline must pass, and at least one human must review it." This prevents accidentally
pushing code that breaks the tests.

**Why this matters for MarketPulse:** The ML pipeline is easy to break accidentally. A one-line
change to `assemble_features()` that introduces a subtle look-ahead bias (using future data to
predict the past) would train a model that looks great in backtesting but fails completely in
production. The test suite catches these regressions automatically on every push.

**Documentation links:**
- GitHub Actions quickstart: https://docs.github.com/en/actions/quickstart
- Branch protection: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches

---

## Lesson 2.5 — Modularity: The Plugin Pattern, Event Bus, and Feature Flags

**What this is about:** This is one of the most important design concepts in MarketPulse. Three
mechanisms work together to make the system extensible without editing existing code.

**The Plugin Pattern.** A plugin is a class that implements a known interface (an Abstract Base
Class, or ABC). The system discovers all plugins at startup and calls them through the interface
without knowing the specific class. Adding a new data source means creating one new file that
implements the `DataSourcePlugin` ABC — no other file changes.

Why does this matter? Imagine you have 10 data sources. Without plugins, adding an 11th source
means editing the ingestion worker (to call the new source), the quota tracker (to add the new
source), the admin console (to show the new source), and the health check (to verify the new
source). That's 4 files to change, 4 places to introduce bugs. With plugins, it's 1 file.

**The Abstract Base Class.** Python's `abc.ABC` and `@abc.abstractmethod` let you define
a class that cannot be instantiated directly, only through subclasses that implement all
abstract methods. If a plugin forgets to implement `fetch()`, Python raises `TypeError` at
import time — not at 3 AM during an ingestion run.

**The Event Bus.** The ingestion pipeline needs to trigger the alert system when something
interesting happens: a prediction changes, unusual volume is detected, a major news story breaks.
The naive solution is to call the alert system directly from the ingestion worker. The problem:
now the ingestion worker depends on the alert system. If the alert system is slow, the ingestion
worker is slow. If you add a new alert type, you edit the ingestion worker.

An event bus inverts this. The ingestion worker publishes an event ("prediction changed for AAPL")
to a channel and immediately continues. The alert system subscribes to the channel and processes
the event asynchronously. The ingestion worker doesn't know or care who is listening.

Valkey's pub/sub system is the event bus. Events are Python dataclasses serialized with
MessagePack (a compact binary format, more efficient than JSON).

**Feature Flags.** A feature flag is a boolean switch stored in the database that can turn a
feature on or off without redeploying code. The `feature_flags` table in PostgreSQL is mirrored
to Valkey at startup. When the system needs to check whether SMS alerts are enabled, it reads
from Valkey (fast, in-memory, sub-millisecond). The convention in MarketPulse is:
- `datasource.reddit` — enable/disable Reddit ingestion
- `ml.lstm` — include/exclude LSTM from the ensemble
- `alert.sms` — enable/disable Twilio SMS delivery
- `feature.earnings_calendar` — show/hide the earnings calendar feature

This pattern lets you ship code that's "dark" (deployed but disabled). When a new feature is
ready, flip the flag — no deployment required.

**Documentation links:**
- Python ABC: https://docs.python.org/3/library/abc.html
- Valkey pub/sub: https://valkey.io/docs/topics/pubsub/
- MessagePack: https://msgpack.org/
- Feature flags concept: https://martinfowler.com/articles/feature-toggles.html

---

## Lesson 3 — Domain Model: What Are We Even Modeling?

**What this is about:** Before writing API routes or database queries, you define the core
business entities as Python classes. These classes represent the real-world concepts of the
system.

**Domain-Driven Design (DDD).** A software design approach where the code structure mirrors the
business domain. The domain model is the set of classes that represent what the system does,
independent of how it's stored or displayed. A `Prediction` is a business concept. It has a
symbol, a horizon, a direction, and a confidence. Whether it's stored in PostgreSQL or MongoDB
or passed over HTTP as JSON is an implementation detail.

**Why domain objects before database schemas?** The domain model is the contract between all
parts of the system. The FastAPI routes accept and return domain objects. The database adapters
translate domain objects to and from rows. The ML sidecar returns domain objects. If you write
the database schema first, you end up with an API that leaks database details (column names,
integer IDs, SQL-specific types).

**Dataclasses.** Python's `@dataclass` decorator generates `__init__`, `__repr__`, and `__eq__`
for you based on class annotations. A `@dataclass(frozen=True)` is immutable — once created,
its values cannot change. Immutable domain objects prevent a whole class of bugs where a function
accidentally modifies an object that another part of the system is still reading.

**Why `NUMERIC(18,6)` not `FLOAT` for prices?** Floating-point numbers cannot represent most
decimal fractions exactly. `0.1 + 0.2 == 0.30000000000000004` in every language that uses IEEE
754 floats. For financial data, this matters: a price of `$150.12` stored as a float might be
retrieved as `$150.11999999999999`. PostgreSQL's `NUMERIC` type stores exact decimal arithmetic.
Python's `Decimal` type does the same. The domain model uses `Decimal` for all prices.

**Documentation links:**
- Python dataclasses: https://docs.python.org/3/library/dataclasses.html
- Decimal module: https://docs.python.org/3/library/decimal.html
- Domain-Driven Design intro: https://martinfowler.com/bliki/DomainDrivenDesign.html

---

## Lesson 4 — Database Adapters: The Repository Pattern

**What this is about:** A repository is a class that hides the details of a specific database
behind a clean interface. Application code asks "give me the latest OHLCV for AAPL" — it doesn't
write SQL, it doesn't know about asyncpg, it doesn't construct queries. That's the repository's job.

**Why isolate database code?** If database access is scattered throughout the application (SQL
in route handlers, MongoDB queries in ARQ tasks, InfluxDB writes in the ML pipeline), changing
any database becomes a nightmare. When you upgrade PostgreSQL or switch from MongoDB to a
different document store, you'd need to find and change every file that touches that database.
With repositories, you change one file.

**The repository interface contract.** A repository method signature tells you everything you
need to know:
```python
async def get_recent(self, symbol: str, days: int) -> list[OHLCVBar]:
```
This reads as: "give me the most recent `days` days of OHLCV bars for `symbol`."
The caller doesn't know whether this is reading from a hypertable, a cache, or a Parquet file.

**Async database access.** Python's `async/await` syntax lets the event loop handle other
requests while waiting for database I/O. Without async, a slow query blocks the entire server.
With async, while one request waits for PostgreSQL, other requests are served. `asyncpg` is an
async PostgreSQL driver. `motor` is an async MongoDB driver. `aiofiles` is async file I/O.

**Connection pooling.** Database connections are expensive to create (TCP handshake + auth).
A connection pool maintains a set of pre-established connections and lends them out for queries.
`asyncpg` has a built-in pool. The MarketPulse pool size is set in config based on expected
concurrency: 10 connections for the API (4 workers × 2.5 avg concurrent queries), 2 for ARQ.

**Documentation links:**
- asyncpg: https://magicstack.github.io/asyncpg/current/
- Repository pattern: https://martinfowler.com/eaaCatalog/repository.html
- motor (async MongoDB): https://motor.readthedocs.io/

---

## Lesson 4.5 — Database Migrations: Alembic

**What this is about:** Your database schema will change. A new feature needs a column. A
performance investigation shows you need an index. An old field gets renamed. The question is:
*how do you apply schema changes to a live database without losing data and without running raw
SQL by hand?* The answer is a migration tool. MarketPulse uses Alembic.

**Why migrations matter.** Your initial schema lives in `001_schema.sql`. That file creates all
17 databases' tables from scratch — perfect for a first install. But after the database is
running and holds real data, you can't just edit `001_schema.sql` and re-run it. The tables
already exist. Re-running the file would fail or destroy data. What you need instead is a script
that says: "the database currently looks like X; change it to look like Y." That script is a
*migration*.

**How Alembic works.** Alembic manages migrations as a chain of numbered Python scripts. Each
script has two functions:

```python
def upgrade() -> None:
    # Forward: apply the change
    op.add_column("tickers", sa.Column("sector", sa.Text()))

def downgrade() -> None:
    # Backward: undo the change
    op.drop_column("tickers", "sector")
```

Each script has a unique revision ID (e.g., `a3f9b12c`) and knows its parent revision. Running
`alembic upgrade head` walks the chain from your current revision to the latest one, applying
each `upgrade()` in order. Running `alembic downgrade -1` calls the most recent `downgrade()`
and steps back one revision.

**Key files.**
- `alembic.ini` — the config file. Points at the database URL and the migrations directory.
- `alembic/env.py` — the migration environment. Connects to the database and, optionally, imports
  your SQLAlchemy models so Alembic can detect schema differences automatically.
- `alembic/versions/` — the migration scripts, one file per revision.

**Autogenerate vs. manual.** Alembic can compare your SQLAlchemy model definitions to the live
database and write the migration script for you:

```
alembic revision --autogenerate -m "add sector column to tickers"
```

This generates the `add_column` / `drop_column` calls automatically. You review the output and
run it. For complex migrations (data backfills, computed columns, multi-step transforms) you
write the migration by hand — but the structure is the same.

**Checking migration state.** Two commands you'll use constantly:
- `alembic current` — which revision is the database currently at?
- `alembic history --verbose` — list all revisions in order, with descriptions.

**How MarketPulse uses it.** The PostgreSQL schema starts from `001_schema.sql` (Phase 1 setup).
Alembic is initialized in Phase 2 (`alembic init alembic` in the project root). From Phase 3
onward, every schema change — new columns, new indexes, new tables — is made through an Alembic
migration rather than by editing the SQL file directly. Alembic writes a `alembic_version` table
into PostgreSQL so it always knows the current revision and where to pick up.

**The stamp command.** Because `001_schema.sql` creates the initial schema *outside* of Alembic,
you can't run `alembic upgrade head` on a database that was set up that way — Alembic would try
to re-create tables that already exist. Instead, you run `alembic stamp head` once after the
initial SQL setup. This tells Alembic "the database is already at the latest revision" without
actually running any migration. From that point on, all new schema changes go through migrations.

**Documentation links:**
- Alembic tutorial: https://alembic.sqlalchemy.org/en/latest/tutorial.html
- Auto-generating migrations: https://alembic.sqlalchemy.org/en/latest/autogenerate.html
- SQLAlchemy types reference: https://docs.sqlalchemy.org/en/20/core/types.html

---

## Lesson 5 — FastAPI: The API Layer

**What this is about:** FastAPI is the HTTP server that exposes MarketPulse's data to the web
dashboard, mobile app, Discord bot, and voice integrations. This lesson covers what makes FastAPI
different from other frameworks and why it fits this use case.

**ASGI and async.** FastAPI is an ASGI (Asynchronous Server Gateway Interface) framework. Because
it's async, a single uvicorn worker can handle hundreds of concurrent requests — as long as those
requests spend most of their time waiting for I/O (database, HTTP, file). A synchronous (WSGI)
framework like Flask can only handle one request per worker at a time. MarketPulse's requests are
mostly I/O-bound (read from database, return data), so ASGI is the right choice.

**Pydantic validation.** Every FastAPI route that accepts a request body or returns a response
uses a Pydantic model for validation. Pydantic checks that every required field is present, every
field has the correct type, and values are within expected ranges. If a client sends a request
with a missing required field, FastAPI returns a 422 Unprocessable Entity with a clear error
message before the route handler even runs.

**OpenAPI automatic documentation.** FastAPI automatically generates an OpenAPI spec from your
route definitions and Pydantic models. Visit `/docs` and you get a Swagger UI where you can read
the API documentation and make real API calls. This is not manually maintained — it's generated
from the code and always up to date.

**Dependency injection.** FastAPI's `Depends()` system is a lightweight dependency injection
mechanism. The most common use: `current_user: User = Depends(get_current_user)`. This function
is called once per request, reads the JWT from the Authorization header, verifies it, and
returns the authenticated user. Any route that needs the current user declares this dependency;
the framework handles the rest. If the token is invalid, FastAPI returns 401 automatically.

**Lifespan.** The `@asynccontextmanager` on the FastAPI `lifespan` function runs code at startup
(connect to all databases, load plugins, sync feature flags) and at shutdown (close connections
gracefully). This is the correct place for application initialization — not at module import time.

**Documentation links:**
- FastAPI tutorial: https://fastapi.tiangolo.com/tutorial/
- Pydantic: https://docs.pydantic.dev/latest/
- Uvicorn: https://www.uvicorn.org/

---

## Lesson 6 — OHLCV: The Atomic Unit of Market Data

**What this is about:** Every chart, every indicator, every ML prediction in MarketPulse starts
with OHLCV data. Understanding what it is and where it comes from is the foundation for everything
else.

**OHLCV defined.** For every trading session (usually a day), a stock's price movement is
summarized by five numbers:
- **Open** — the price at market open (9:30 AM Eastern for US stocks)
- **High** — the highest price reached during the session
- **Low** — the lowest price during the session
- **Close** — the price at market close (4:00 PM Eastern for US stocks)
- **Volume** — the total number of shares traded during the session

These five numbers are the universal language of financial data. Every data provider, every
charting library, every technical analysis library speaks OHLCV.

**Why not just use real-time tick data?** Tick data captures every single trade — a large-cap
stock like AAPL can generate millions of ticks per day. Storing, processing, and training on
tick data requires massive infrastructure. Daily OHLCV achieves 90% of the predictive signal
with a tiny fraction of the storage and compute.

**Where the data comes from.** MarketPulse uses a tiered approach:
- **yfinance:** A Python library that downloads historical data from Yahoo Finance. Free, no API
  key, but the data is delayed ~15 minutes for real-time quotes and limited for bulk downloads.
  Used for historical backfill.
- **Polygon.io:** Professional financial data API with 5 free calls/minute. Used for end-of-day
  data and intraday bars during market hours.
- **CoinGecko:** Crypto OHLCV data. Free tier allows 10,000 calls/month.

**Rate limiting with a semaphore.** When fetching data for 25 tickers at once, you can't fire
off 25 simultaneous requests to a provider that allows 5 per minute. An `asyncio.Semaphore(5)`
limits concurrency to 5 simultaneous requests. Combined with a 60-second sliding window, this
respects the rate limit without needing to pause between every request.

**ARQ task chaining.** After the OHLCV ingestion task writes data to TimescaleDB, it enqueues
the indicator computation task for that ticker. The indicator task, when it finishes, enqueues
the prediction task. This chain ensures that the ML model always trains on current indicator
values — you never accidentally train on yesterday's indicators with today's OHLCV.

**Documentation links:**
- yfinance: https://pypi.org/project/yfinance/
- Polygon.io REST API: https://polygon.io/docs/stocks
- asyncio.Semaphore: https://docs.python.org/3/library/asyncio-sync.html#asyncio.Semaphore

---

## Lesson 7 — News and RSS: Turning Headlines into Numbers

**What this is about:** Sentiment analysis starts with text. This lesson covers how news articles
get from the internet into MarketPulse, and how they're stored efficiently.

**RSS feeds.** RSS (Really Simple Syndication) is a standardized XML format that websites publish
to announce new content. Every major financial news site (Reuters, AP, SeekingAlpha, Benzinga)
publishes RSS feeds. `feedparser` is a Python library that parses RSS feeds into Python
dictionaries. It handles the 15+ variations of RSS and Atom formats transparently. MarketPulse
polls its list of RSS feeds every 15 minutes.

**Deduplication with vector similarity.** News agencies often distribute the same story through
multiple wires. A Reuters story might be picked up by Yahoo Finance, Bloomberg, and MarketWatch
with slightly different titles but identical content. Without deduplication, the same story gets
stored 3 times and triple-counts its sentiment signal.

ChromaDB deduplication works like this: every article's headline and summary are converted into a
768-dimensional vector (a list of 768 floating-point numbers) using the
`all-MiniLM-L6-v2` sentence embedding model. Two articles with nearly identical meaning will have
vectors with a cosine similarity above 0.95. Before storing a new article, MarketPulse checks
whether any existing article is within this threshold. If so, the article is discarded.

**Why two sentiment models?** VADER (Valence Aware Dictionary and sEntiment Reasoner) is a
rule-based sentiment analyzer that runs in microseconds. It was built for social media text and
works well for short, informal content (Reddit posts, tweet-style headlines). FinBERT is a
BERT-based transformer model fine-tuned specifically on financial text. It understands that "the
company's losses narrowed" is positive news (losing less money is good) while VADER might score
it negatively. But FinBERT runs in ~200ms per sentence on CPU. The pipeline uses VADER as a fast
first pass to score everything immediately, then runs FinBERT post-market in batch for articles
that will be used in the next day's ML predictions.

**Documentation links:**
- feedparser: https://feedparser.readthedocs.io/
- sentence-transformers: https://www.sbert.net/
- VADER: https://github.com/cjhutto/vaderSentiment
- FinBERT: https://huggingface.co/ProsusAI/finbert

---

## Lesson 8 — Reddit and PRAW: The Pulse of Retail Sentiment

**What this is about:** Retail investor sentiment on Reddit has demonstrably moved stock prices
(see: GameStop, AMC, BlackBerry in January 2021). This lesson covers how to read Reddit safely
and responsibly.

**PRAW.** The Python Reddit API Wrapper. Reddit's API allows reading public posts and comments
with a rate limit of 100 requests/minute per OAuth client. PRAW handles authentication,
pagination, and rate limiting for you. You must create a Reddit "app" to get credentials.

**Subreddits as signal sources.** Different subreddits provide different signals:
- `r/wallstreetbets` — high-volatility retail speculation, leading indicator of meme stock moves
- `r/investing` — longer-term fundamental discussion
- `r/stocks` — general stock market discussion
- `r/options` — options flow discussion (directional bets by retail traders)
- `r/CryptoCurrency` — crypto sentiment

**Comment weighting.** Not all Reddit posts are equal. A post with 500 upvotes and 200 comments
carries more signal than a post with 2 upvotes. MarketPulse weights each post's sentiment by
`log(1 + upvotes + 0.5 * comment_count)`. The log function prevents a single viral post from
completely dominating the daily sentiment score.

**Ticker mention extraction.** Reddit posts mention tickers as `$AAPL` or just `AAPL` in
all-caps. A regex `\$[A-Z]{1,5}|(?<!\w)[A-Z]{2,5}(?!\w)` extracts potential tickers, which are
then filtered against the set of active tickers in the system.

**Documentation links:**
- PRAW quickstart: https://praw.readthedocs.io/en/stable/getting_started/quick_start.html
- Reddit API rules: https://www.reddit.com/wiki/api

---

## Lesson 9 — Technical Indicators: What the Charts Are Saying

**What this is about:** Technical indicators are mathematical formulas applied to OHLCV data that
claim to signal future price direction. MarketPulse includes them as features in the ML model.
This lesson covers the most important ones.

**Why indicators at all?** Machine learning models learn from examples. If you give the model
raw OHLCV prices, it struggles: prices in 2022 are on a completely different scale than prices
in 1999. Indicators normalize the data. RSI is always between 0 and 100. MACD measures the
difference between two moving averages as a percentage. The model can learn "RSI above 70 often
precedes a pullback" without needing to know whether the absolute price is $5 or $5,000.

**The most important indicators:**

**RSI (Relative Strength Index)** — measures how fast prices are moving up or down. Calculated
over a 14-day window: RSI = 100 - (100 / (1 + avg_gains / avg_losses)). Values above 70 suggest
overbought (too far up, might pull back). Values below 30 suggest oversold (might bounce). This
is the most commonly cited technical indicator.

**MACD (Moving Average Convergence Divergence)** — compares two exponential moving averages (12-day
and 26-day). When the short MA crosses above the long MA, momentum is building upward. When it
crosses below, momentum is building downward. The "signal line" is a 9-day EMA of the MACD line.
MACD above signal = bullish momentum.

**Bollinger Bands** — a 20-day moving average with bands 2 standard deviations above and below.
They measure volatility: wide bands = high volatility, narrow bands = low volatility. Price touching
the upper band after a low-volatility period can signal a breakout. Price touching the lower band
can signal oversold conditions.

**Volume SMA** — the simple moving average of volume. Unusually high volume on an up day confirms
the move; high volume on a down day confirms the sell-off. A price move on below-average volume is
often a false signal.

**Minimum lookback period.** The 200-day moving average needs 200 days of history to compute.
MarketPulse requires a minimum of 200 days of OHLCV history before computing indicators for a
ticker. Indicators computed on less data are unreliable.

**ta.** A Python library that computes 130+ technical indicators from a pandas DataFrame
of OHLCV data. One line: `ta.momentum.RSIIndicator(close=df["Close"], window=14).rsi()` returns
the RSI series. It handles all the edge cases (NaN handling at the start of the series, correct EMA initialization).

**Documentation links:**
- ta: https://github.com/bukosabino/ta
- ta docs: https://technical-analysis-library-in-python.readthedocs.io/
- Investopedia RSI: https://www.investopedia.com/terms/r/rsi.asp
- Investopedia MACD: https://www.investopedia.com/terms/m/macd.asp

---

## Lesson 10 — Sentiment Analysis: VADER vs. FinBERT

**What this is about:** Sentiment analysis converts text into a number between -1 (very negative)
and +1 (very positive). This lesson goes deep on how the two models work and when to use each.

**VADER in detail.** VADER uses a hand-curated lexicon of ~7,500 words and phrases, each with
a sentiment score (e.g., "great" = +3.1, "terrible" = -2.5). It has special rules for:
- Capitalization ("GREAT" scores higher than "great")
- Punctuation ("great!!!" scores higher than "great")
- Negation ("not great" flips the score)
- "But" contrast ("The earnings were good, but guidance was weak" — the part after "but" gets
  heavier weight)

The compound score normalizes everything to [-1, 1]. VADER runs in microseconds with no GPU.
It works best on short, informal text (Reddit posts, Twitter, headline text).

**FinBERT in detail.** BERT (Bidirectional Encoder Representations from Transformers) is a
transformer model pre-trained on massive amounts of text to understand language context. FinBERT
fine-tuned BERT on financial news articles. It produces a probability for each of three classes:
positive, negative, neutral. The sentiment score is `P(positive) - P(negative)`.

FinBERT understands financial language that confuses VADER:
- "The company beat estimates by 5 cents" → positive (VADER struggles with "beat")
- "Revenue declined less than feared" → positive (VADER sees "declined" and scores negative)
- "Shares fell on profit-taking" → more neutral than negative (it's normal market behavior)

**The two-pass pipeline:**
1. VADER runs on every new article immediately on ingestion. Score stored in MongoDB.
2. FinBERT runs post-market (6 PM UTC) in batch on articles ingested during the trading day.
   Score stored in MongoDB, overwrites VADER score for those articles.
3. The ML feature vector uses FinBERT scores where available, VADER scores otherwise.

**Sentiment aggregation.** Individual article scores are aggregated per ticker per day:
- Simple average: equal weight to all articles
- Source-weighted: Reuters articles weighted more than random blogs
- Recency-weighted: exponential decay — articles from 2 hours ago matter more than from 48 hours ago

**Documentation links:**
- FinBERT paper: https://arxiv.org/abs/1908.10063
- FinBERT on HuggingFace: https://huggingface.co/ProsusAI/finbert
- Transformers library: https://huggingface.co/docs/transformers/

---

## Lesson 11 — The ML Prediction Pipeline: From Data to Direction

**What this is about:** This is the core of MarketPulse. This lesson explains every component
of the ML pipeline, with particular focus on the most common mistake — look-ahead bias.

**The prediction problem.** For each ticker and each time horizon (1 day, 3 days, 7 days, 30
days), the model predicts one of three outcomes: UP (close price will be > 2% higher), DOWN
(close price will be > 2% lower), or FLAT (within ±2%). A three-class classification problem.

**The feature vector.** The model's input is a fixed-length vector of numbers derived from:
- OHLCV-derived: log return, normalized RSI, MACD, Bollinger Band position, volume ratio
- Sentiment-derived: weighted news sentiment score, Reddit mention velocity, FinBERT average
- Technical: whether price is above/below 50-day and 200-day moving averages
- Macro: 10-year Treasury yield, VIX level, sector ETF performance

All features are z-score normalized per ticker (subtract mean, divide by standard deviation)
so the model doesn't see "AAPL trades at $175" but rather "AAPL is currently 0.8 standard
deviations above its average price."

**Look-ahead bias — the most critical concept in financial ML.** Look-ahead bias means using
data from the future to predict the past. It's the single most common mistake in financial ML
and it's subtle. An example:
```
You're predicting AAPL's price on Monday.
Your feature vector includes the volume ratio for Monday.
But volume for Monday isn't known until Monday's trading session ends.
You've used Monday's data to predict Monday — you've cheated.
```
This produces a model that looks extraordinary in backtesting (80%+ accuracy) but performs at
chance level (33%) in production, because in production, future data isn't available.

MarketPulse prevents this with a temporal boundary: when computing features for a prediction
at time T, every data point in the feature vector must have `timestamp < T`. The
`assemble_features()` function raises `TemporalViolationError` if any feature has a timestamp ≥ T.

**LSTM for sequential patterns.** An LSTM (Long Short-Term Memory) is a type of recurrent
neural network designed to learn patterns in sequential data. It processes one OHLCV bar at a
time, updating its internal state, and produces a final prediction after seeing 30 days of data.
LSTMs can learn: "when the price is above the 50-day MA and RSI crosses above 50 after being
below it for 5 days, the stock tends to continue upward for 7 days."

**XGBoost and LightGBM for tabular features.** Gradient boosting algorithms. They're given the
flat feature vector (all 45 features at once, not as a sequence) and trained to classify
UP/FLAT/DOWN. They're faster to train than LSTMs, interpretable (feature importance is
extractable), and often more accurate for tabular data.

**Ensemble.** The final prediction combines all three models. The ensemble weights are learned:
for each ticker, the model that historically performs best gets the highest weight. Some tickers
are more momentum-driven (LSTM performs well); others are more news-driven (sentiment features
and XGBoost perform well).

**Confidence and calibration.** The model outputs a probability (e.g., 80% confidence in UP).
Without calibration, "80% confident" might mean the model is only right 60% of the time at that
confidence level. Calibration using isotonic regression adjusts the probabilities so that 80%
confidence corresponds to ~80% observed accuracy. This is measured on a held-out validation set.

**Walk-forward backtesting.** The only valid way to evaluate a financial ML model:
1. Train on months 1–24
2. Test on months 25–27
3. Train on months 1–27
4. Test on months 28–30
5. Repeat, always training on the past and testing on the future
This mirrors real production conditions: the model was trained on historical data and tested on
what comes next.

**ONNX Runtime for inference.** ONNX (Open Neural Network Exchange) is a standard format for
ML models. XGBoost and LightGBM can export to ONNX. ONNX Runtime runs inference faster than the
native libraries and doesn't require the training libraries to be installed. The inference
container needs only `onnxruntime`, not `xgboost` or `lightgbm`.

**gRPC sidecar.** The ML code runs in a separate Python process (the "sidecar"), communicating
with the FastAPI backend via gRPC. This means:
1. Crashes in the ML process don't crash the API
2. The ML process can use a different Python environment (e.g., with GPU libraries)
3. The ML sidecar can be replaced (e.g., with a newer model) without restarting the API

**Circuit breaker.** If the ML sidecar crashes or is slow, the FastAPI backend's gRPC client
opens a circuit breaker after 3 consecutive failures. For the next 60 seconds, all prediction
requests return the last cached prediction instead of attempting to call the sidecar. After 60
seconds, the circuit "half-opens" and tries one request to see if the sidecar has recovered.

**SHAP values.** SHAP (SHapley Additive exPlanations) decomposes a model's prediction into
contributions from each input feature. For a given AAPL prediction, SHAP might tell you:
"RSI below 30 contributed +12% to UP confidence; negative news sentiment contributed -8%."
These explanations are stored in MongoDB and shown in the dashboard's "Why" tab.

**Documentation links:**
- PyTorch LSTM tutorial: https://pytorch.org/tutorials/beginner/nlp/sequence_models_tutorial.html
- XGBoost: https://xgboost.readthedocs.io/en/stable/
- SHAP: https://shap.readthedocs.io/
- sklearn calibration: https://scikit-learn.org/stable/modules/calibration.html
- ONNX tutorial: https://onnxruntime.ai/docs/get-started/with-python.html

---

## Lesson 12 — The Alert System: Pub/Sub, Evaluation, and Delivery

**What this is about:** This lesson covers how events flow from detection to delivery through
the event bus.

**The problem with direct calls.** If the prediction worker called the email delivery function
directly: (1) a slow email server blocks the prediction worker, (2) adding Discord delivery means
editing the prediction worker, (3) if Discord is disabled by a feature flag, the prediction worker
needs to know about that flag. The prediction worker should do one thing: make predictions.

**Pub/sub.** Publish-subscribe messaging: a publisher puts a message on a channel; any number of
subscribers read from that channel. Publisher and subscriber don't know about each other. Adding a
new delivery channel means creating a new subscriber, not editing the publisher.

**Alert evaluation.** When a `PredictionChangedEvent` arrives on the subscriber, the alert
evaluator checks every active alert config for every user. An alert fires when its conditions
match: "notify me when AAPL's 1-day prediction changes to UP with > 80% confidence." The
evaluator checks this condition against the event. If it matches, it sends the alert through the
configured delivery channels.

**12 alert types.** The alert types in MarketPulse range from `prediction_change` (the most
common) to `earnings_date` (notify the day before a ticker's earnings report), `insider_purchase`
(an officer bought > $100K of their own company's stock), and `sentiment_spike` (the aggregated
news sentiment for a ticker jumps more than 2 standard deviations in 24 hours).

**OneSignal vs. Twilio.** OneSignal handles web push and mobile push notifications — when a
prediction changes, a push notification appears on the phone or browser without the user having
the app open. Twilio handles SMS — a text message to a phone number. Twilio costs money (about
$0.0079 per message); OneSignal is free up to 10,000 subscribers. That's why `alert.sms` is
feature-flagged off by default.

**Documentation links:**
- OneSignal REST API: https://documentation.onesignal.com/reference
- Twilio Python helper: https://www.twilio.com/docs/libraries/python

---

## Lesson 13 — The Discord Bot: Commands, Embeds, and Charts

**What this is about:** The Discord bot is a fully functional interface to MarketPulse that
lives inside a Discord server. This lesson covers how it works technically.

**discord.py application commands.** Modern Discord bots use "slash commands" (typed with `/`)
rather than prefix commands (like `!predict`). Slash commands are registered with Discord's API
and appear in the Discord autocomplete menu. The `@bot.tree.command()` decorator registers a
slash command. After registration, Discord sends a WebSocket message to the bot whenever a user
invokes the command.

**Embeds.** Discord messages can include rich embeds: structured cards with a title, color,
thumbnail, and multiple fields. MarketPulse prediction embeds include: a color-coded header
(green for UP, red for DOWN, gray for FLAT), four horizon cards in the body (1d, 3d, 7d, 30d),
confidence as a percentage, and a "Why" summary from the top SHAP features.

**Chart generation.** When a user runs `/chart AAPL 1m`, the bot:
1. Calls `GET /tickers/AAPL/ohlcv?period=1m` on the FastAPI backend
2. Converts the response to a pandas DataFrame
3. Calls `mplfinance.plot(df, type='candle', style='charles', ...)` to render a PNG
4. Uploads the PNG to MinIO and gets a presigned URL
5. Sends the URL as a Discord image attachment

`mplfinance` renders publication-quality candlestick charts with volume bars. It supports
multiple styles and can overlay technical indicators.

**The bot calls the API, not the databases.** The Discord bot is a client of the FastAPI API,
not a database client. It never opens a direct connection to PostgreSQL or Valkey. This means:
- The bot runs with no database credentials
- The API's auth middleware protects all data
- Rate limiting and quota checking happens in one place (the API)

**Documentation links:**
- discord.py: https://discordpy.readthedocs.io/
- mplfinance: https://github.com/matplotlib/mplfinance
- Discord application commands: https://discord.com/developers/docs/interactions/application-commands

---

## Lesson 14 — The Web Dashboard: React, State Management, and Real-Time Updates

**What this is about:** The web dashboard is a React single-page application that talks to the
FastAPI API. This lesson covers the key architectural decisions.

**React + Vite.** React is a JavaScript/TypeScript library for building user interfaces from
components. Vite is a build tool that replaces Create React App — it's significantly faster at
both dev-server startup and production builds.

**Redux Toolkit and RTK Query.** Redux is a global state management library. Redux Toolkit (RTK)
is the recommended way to use it — it eliminates the boilerplate. RTK Query is a data fetching
layer built on top of Redux that handles caching, invalidation, and background refetching. When
you define an RTK Query endpoint for `GET /tickers/{symbol}/predictions`, RTK Query:
1. Caches the response in the Redux store
2. Serves the cached response immediately for subsequent renders
3. Refetches in the background on focus or after a configurable interval
4. Automatically invalidates the cache when a mutation (like adding a ticker) runs

**Real-time updates via WebSocket.** The dashboard subscribes to a WebSocket connection at
`ws://localhost:8080/ws/prices`. The FastAPI backend sends JSON messages whenever a price or
prediction changes. The frontend dispatches these as Redux actions that update the store
immediately without a full page reload. This is how the dashboard shows "live" price updates.

**TypeScript strict mode.** TypeScript adds static types to JavaScript. Strict mode enables the
most aggressive type checking: no implicit `any`, no possibly-null property access without
checking. The MarketPulse frontend defines TypeScript interfaces for every API response shape.
When the API changes a field name, TypeScript catches all the frontend places that use the old
name at compile time — before it reaches production.

**Progressive disclosure.** The UI reveals complexity only when the user asks for it:
- Home page: just a grid of ticker cards with direction and confidence
- Click a ticker card: the detail drawer slides in (still the same page, no navigation)
- Click "Why": the SHAP explanation tab appears
- Click the gear icon: the config slideout appears

At each level, information density increases. A user who only wants to see "is AAPL going up?"
never sees the complexity intended for power users.

**Documentation links:**
- React: https://react.dev/learn
- Vite: https://vitejs.dev/guide/
- Redux Toolkit: https://redux-toolkit.js.org/introduction/getting-started
- RTK Query: https://redux-toolkit.js.org/rtk-query/overview

---

## Lesson 15 — The Mobile App: React Native CLI and Push Notifications

**What this is about:** The mobile app is a React Native bare workflow application. This lesson
explains what "bare workflow" means and how push notifications work on mobile.

**Expo vs. bare workflow.** Expo is a set of tools that abstracts away the native iOS and Android
build systems. It's fast to start but limits which native modules you can use. The "bare workflow"
(React Native CLI) gives you full access to the native build systems. MarketPulse uses the bare
workflow because some native modules (OneSignal's native push SDK) aren't available in the
managed Expo environment. There's no Firebase in MarketPulse — OneSignal handles all push.

**How mobile push works.** The push notification delivery chain:
1. MarketPulse backend calls the OneSignal REST API: "send a push notification about AAPL to
   user X's devices"
2. OneSignal calls Apple's APNs (Apple Push Notification Service) for iOS devices
3. APNs delivers the notification to the device
4. The device OS shows the notification, even if the app is in the background

The mobile app registers with OneSignal at startup and sends its registration token. OneSignal
maps this token to a user ID. When the backend sends a notification to user X, OneSignal knows
which device tokens belong to user X.

**Documentation links:**
- React Native CLI setup: https://reactnative.dev/docs/environment-setup
- OneSignal React Native: https://documentation.onesignal.com/docs/react-native-sdk

---

## Lesson 16 — Voice Integration: Local Alexa and Google Home

**What this is about:** Voice assistants process spoken queries and call an HTTP endpoint on
your server to fulfill the request. This lesson explains the architecture.

**How Alexa Skills work.** When a user says "Alexa, ask MarketPulse what the prediction is for
Apple," Alexa:
1. Recognizes "MarketPulse" as your skill's invocation name
2. Recognizes "prediction for Apple" as your `GetPredictionIntent`
3. Identifies "Apple" as the `ticker` slot value
4. Makes an HTTPS POST request to your skill's endpoint (a FastAPI route)
5. Your endpoint queries the API and returns a JSON response with the speech text
6. Alexa speaks the response to the user

The `ask-sdk-core` Python library handles the JSON request/response format. You write
`@sb.request_handler(can_handle_func=is_intent_name("GetPredictionIntent"))` and the SDK routes
the request to your function.

**How Google Home Actions work.** Similar architecture. Google sends a JSON webhook to your
fulfillment endpoint. The Google Actions SDK parses the request and routes to your intent handler.

**Cloudflare Tunnel.** Both Alexa and Google require your fulfillment endpoint to be accessible
from the internet over HTTPS. Instead of configuring port forwarding on your router and managing
TLS certificates, Cloudflare Tunnel creates a secure tunnel from Cloudflare's edge to your
local server. The command `cloudflared tunnel run` maintains this tunnel. From the outside, your
endpoint appears to be at `https://voice.yourdomain.com/alexa`.

**Documentation links:**
- Alexa Skills Kit Python SDK: https://developer.amazon.com/en-US/docs/alexa/alexa-skills-kit-sdk-for-python/overview.html
- Google Actions SDK: https://developers.google.com/assistant/actions/sdk/reference/rest
- Cloudflare Tunnel: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/

---

## Lesson 17 — RSS Bidirectional: Consuming and Producing RSS

**What this is about:** RSS flows both ways. MarketPulse consumes RSS feeds from news sources
and produces its own RSS feed that users can subscribe to.

**Consuming RSS (feedparser).** Already covered in Lesson 7 (news ingestion). The key point:
`feedparser.parse(url)` handles all the quirks of different RSS versions, encoding issues, and
malformed feeds. It returns a consistent dictionary structure regardless of the feed format.

**Producing RSS (Python xml.etree).** An RSS 2.0 feed is a valid XML document with a specific
structure. MarketPulse's prediction RSS feed:
```xml
<rss version="2.0">
  <channel>
    <title>MarketPulse High-Confidence Predictions</title>
    <link>https://marketpulse.yourdomain.com</link>
    <item>
      <title>AAPL: UP predicted with 83% confidence (1-day horizon)</title>
      <link>https://marketpulse.yourdomain.com/tickers/AAPL</link>
      <pubDate>Thu, 06 Aug 2026 04:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
```

Any RSS reader (Feedly, NetNewsWire, even Slack via /feed) can subscribe to this feed and
display high-confidence predictions as news items.

---

## Lesson 18 — Data Export: Five Formats, One Endpoint

**What this is about:** Users may want to take MarketPulse data into their own spreadsheets,
analytics tools, or other systems. This lesson covers the export formats and why each exists.

**CSV.** The most portable tabular format. Opens in Excel, Google Sheets, pandas. Every tool
on earth can read CSV. Use it when the recipient needs to do their own analysis.

**PDF.** For a pre-formatted report that looks professional when printed or shared. `reportlab`
generates PDFs programmatically. The MarketPulse prediction report PDF includes: a header with
the ticker and generation timestamp, a price chart image (fetched from MinIO), a table of all
four horizon predictions, and a sentiment timeline chart.

**JSON.** The native format of the API. When the recipient is another program (a trading
algorithm, a spreadsheet with a JSON import feature, another dashboard), JSON is the cleanest
option because it preserves types (numbers as numbers, not strings).

**NDJSON (Newline-Delimited JSON).** NDJSON streams one JSON object per line. This makes it
possible to process large datasets without loading the entire file into memory — you can read
one line, process it, and move to the next. Pandas, DuckDB, and many data engineering tools
accept NDJSON directly.

**XML.** For enterprise integrations that expect XML. Less common for new systems, but some
financial tools (Bloomberg Terminal add-ins, some bank APIs) require XML format.

---

## Lesson 19 — Authentication: JWT, bcrypt, TOTP 2FA

**What this is about:** Authentication verifies who a user is. This lesson covers the complete
MarketPulse authentication stack.

**bcrypt for passwords.** Passwords must never be stored in plain text. bcrypt is a
password-hashing function with a "work factor" (also called "cost factor") that controls how
slow the hash is. MarketPulse uses work factor 12, which takes ~250ms to hash a password on
modern hardware. This is intentional: it makes brute-force attacks impractical. An attacker
who steals the database can only test about 4 guesses/second per CPU core, not billions.

**JWT for sessions.** JSON Web Tokens are a standard format for access tokens. A JWT consists of
three Base64-encoded parts: header (algorithm), payload (user ID, roles, expiry), and signature.
The server signs the token with a secret key. Any request that includes a valid JWT is
authenticated — no database lookup required to verify who the user is. This makes JWTs fast
(no Redis or DB query per request) but non-revocable by default.

**JWT blocklist.** JWTs can't be invalidated before expiry — that's the design trade-off. To
support logout (and force-logout from admin), MarketPulse maintains a blocklist: the `jti` (JWT
ID, a unique identifier in the payload) is stored in Valkey with a TTL equal to the token's
remaining validity. Any request with a blocklisted `jti` is rejected. The blocklist uses Valkey
because it's in-memory and the check happens on every request — it must be fast.

**TOTP 2FA.** Time-based One-Time Passwords. When a user enrolls in TOTP:
1. The server generates a random 20-byte secret
2. The secret is encoded as a QR code using the `otpauth://` URI format
3. The user scans the QR code with Google Authenticator or Authy
4. From then on, logging in requires the current 6-digit code

The code rotates every 30 seconds, derived from: `HMAC-SHA1(secret, floor(unix_time / 30))`.
The server computes the expected code at login time and checks whether the user's code matches.
`pyotp` handles all of this in one line: `pyotp.TOTP(secret).verify(code)`.

**OPA (Open Policy Agent).** After authentication verifies who the user is, authorization
determines what they can do. OPA is a policy engine that evaluates policies written in Rego (a
declarative language). Policies live in version-controlled `.rego` files. An example policy:
```rego
allow if {
    input.user.role == "admin"
    input.resource == "admin_panel"
}
```
FastAPI middleware sends the request context (user ID, role, resource, action) to OPA's HTTP API
and checks the response. Policies are separate from code — you can update them without
redeploying.

**Documentation links:**
- JWT explained: https://jwt.io/introduction
- passlib bcrypt: https://passlib.readthedocs.io/en/stable/lib/passlib.hash.bcrypt.html
- pyotp: https://pyauth.github.io/pyotp/
- OPA: https://www.openpolicyagent.org/docs/latest/

---

## Lesson 20 — The Admin Paradigm Console: Introspection

**What this is about:** The admin paradigm console is a section of the web dashboard that makes
the system's internal mechanisms observable. This lesson explains the philosophy.

**Why make internals visible?** A well-designed system is introspectable — its behavior can be
observed and understood from the outside without reading source code. The admin console takes
every significant paradigm in MarketPulse and exposes it as a live panel:
- The event bus panel shows messages flowing through Valkey pub/sub in real time
- The feature flags panel shows all flags and lets you toggle them
- The quota panel shows API usage with countdown timers
- The circuit breaker panel shows ML sidecar health and the current circuit state

**Why does this exist in a stock prediction tool?** Because the admin console turns MarketPulse
from a black box into a teaching tool. When you build something yourself, you understand it. When
you can watch the OHLCV pipeline run, see the MessagePack events appear on the event bus, and
observe the feature flag check happen in real time — you've internalized the system.

---

## Lesson 21 — Security Hardening: Defense in Depth

**What this is about:** "Defense in depth" means no single security failure should compromise
the entire system. This lesson covers the layers of security in MarketPulse.

**The audit ledger with hash chain.** Every privileged action (user creation, role change, flag
toggle) is appended to the SQLite audit ledger. Each row includes a SHA-256 hash of the previous
row's content plus its own content. This forms a hash chain: if any historical record is tampered
with, all subsequent hashes become invalid. `verify_chain()` checks the entire chain integrity
in O(n) time.

**Input validation.** Every external input (API request bodies, query parameters, WebSocket
messages) is validated by Pydantic before reaching application logic. SQL injection is prevented
by asyncpg's parameterized queries (values are never string-interpolated into SQL). SSRF
(Server-Side Request Forgery) is prevented by validating URLs against an allowlist.

**bandit.** A static analysis tool that scans Python code for common security mistakes:
hardcoded passwords, use of `eval()`, insecure random number generators, shell injection risks.
MarketPulse's CI pipeline runs `bandit -r app/ ml_sidecar/` and fails on any high-severity finding.

**Secrets management.** In development, secrets live in `.env` (gitignored). In production, they
live in HashiCorp Vault, and the application reads them at startup via the Vault API. This means
secrets are never in the Git repository, never in Docker images, and can be rotated without
redeployment.

---

## Lesson 22 — Testing: The Pyramid, Property Testing, and Mutation Testing

**What this is about:** A test suite that gives you genuine confidence, not just high coverage
numbers. This lesson covers each layer of MarketPulse's test pyramid.

**The testing pyramid.** Unit tests (many, fast), integration tests (some, slower), end-to-end
tests (few, slowest). Run unit tests on every file save. Run integration tests on every commit.
Run E2E tests before every release.

**Unit tests.** Test one function, one class, one pure computation in isolation. Mock all
dependencies. Fast enough to run in milliseconds. In MarketPulse: VADER score for a known text,
domain object construction with invalid arguments raises the right exception, feature vector
with NaN raises `ValueError`.

**Integration tests.** Test a component against its real dependencies (a real database, a real
cache). Use Docker containers for the databases. Slow (seconds to minutes). In MarketPulse:
`OHLCVRepository.insert_batch()` then `get_recent()` returns the inserted data.

**Property-based testing with Hypothesis.** Instead of writing "test that RSI for THIS specific
input is 67.3," write "test that RSI is ALWAYS between 0 and 100 for ANY valid input." Hypothesis
generates hundreds of random inputs and checks the property. It specifically seeks out edge cases:
empty series, all-same-price series, single-element series. This catches bugs that handwritten
examples would never find.

**Mutation testing with mutmut.** Mutation testing automatically introduces small bugs into your
code (changing `>` to `>=`, deleting a line, negating a boolean) and checks whether your test
suite catches them. A test suite with 90% line coverage might miss 40% of injected mutations —
revealing that the tests aren't actually verifying the logic.

**OPA policy testing.** OPA has a built-in test framework. You write Rego unit tests that
assert "given THIS input, this policy SHOULD allow/deny." Run with `opa test policies/`.

---

## Lesson 23 — Seed Data: Making the System Useful From Day One

**What this is about:** A prediction system with no predictions is useless. Seed data populates
the system with enough historical data to make every feature functional on launch day.

**Why historical predictions?** The accuracy tracker can't show meaningful statistics without
historical predictions that have been resolved (we know what AAPL actually did after the prediction
was made). Seed predictions with known outcomes allow the accuracy panel to show real data from
the first time you open it.

**yfinance for historical backfill.** yfinance's `download()` function can fetch up to 730 days
of daily OHLCV data for any ticker. For the 25 seed tickers, this provides the training dataset
for the initial model training run and enough historical data to compute all technical indicators.

**What "seeded news" means.** The news ingestion pipeline is run for 3–7 days before "launch"
to populate MongoDB with a realistic number of articles. This allows the sentiment aggregation to
have enough data to compute meaningful scores.

---

## Lesson 24 — Deployment: From Docker Compose to Production

**What this is about:** Moving from "it works on my laptop" to a self-hosted production system
on three Proxmox nodes. This lesson covers Ansible, Argo CD, blue/green, and canary deployments.

**Ansible.** An infrastructure-as-code tool that automates server configuration. You write
"playbooks" (YAML files) that describe the desired state of a server. Running
`ansible-playbook node1.yml` installs Docker, configures firewall rules, creates users, copies
config files, and starts services — all automatically, idempotently (running it twice produces
the same result as running it once).

**Argo CD and GitOps.** GitOps is the practice of using a Git repository as the single source of
truth for infrastructure configuration. Argo CD watches your Git repository for changes and
automatically applies them to your cluster. When you push a new Docker image tag to the
`deploy/node2.yaml` manifest, Argo CD detects the change and restarts the service with the new
image — without any manual SSH or kubectl commands.

**Blue/green deployment.** Running two identical environments: "blue" (current production) and
"green" (new version). Deploy the new version to green, run smoke tests, then switch the load
balancer to route traffic to green. If something goes wrong, switch back to blue instantly.
Zero downtime.

**Canary deployment for ML models.** Releasing a new ML model to 100% of traffic immediately
is risky — if the new model is worse, all users get worse predictions. A canary release sends
5% of traffic to the new model and 95% to the current model. After 24 hours, if the canary's
accuracy is at least as good as the current model's, the canary is promoted to 100%.

**Documentation links:**
- Ansible: https://docs.ansible.com/ansible/latest/getting_started/
- Argo CD: https://argo-cd.readthedocs.io/
- Cloudflare Tunnel: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/

---

## Lesson 25 — Final Verification: How to Know the System Works

**What this is about:** The final phase is verification — structured checks that confirm the
system does what it claims to do.

**Smoke testing.** A smoke test is a quick sanity check: does the system start up? Do the
critical paths work? Not a comprehensive test — just "is this on fire?" For MarketPulse: can
you get a prediction for AAPL? Does the Discord bot respond? Did notifications arrive? A smoke
test takes 5 minutes to run and catches deployment failures immediately.

**Performance benchmarking.** Measuring whether the system meets its performance targets under
realistic load. Locust simulates concurrent users making API calls. Key targets for MarketPulse:
- p99 < 200ms for cached prediction reads
- p99 < 2s for ML predictions (gRPC call)
- OHLCV ingestion for 25 tickers in < 5 minutes

**The 24-hour stability test.** Let the system run completely unattended for 24 hours and verify
that: no processes have crashed, storage hasn't grown unexpectedly, all daily ingestion jobs have
completed, predictions have been generated for all tickers, and no errors appear in the structured
logs.

**Why this phase matters.** Building each piece individually and building a running system are
different things. Integration problems — the OHLCV task finishes but doesn't correctly enqueue
the indicator task, or the ML sidecar runs out of memory under load — only appear when the full
system runs together. Final verification is the phase where these systemic issues are discovered
and fixed.
# MarketPulse — Exercises

> One exercise per lesson from README_7. Each is completable in under two hours.
> These files describe exactly what to build and verify. Do not look up a solution — work from
> the library documentation linked in each exercise. Treat these as proof-of-concept scripts:
> production-quality code goes in the application itself.

---

## Exercise 0 — Environment Verification Script

**Lesson it reinforces:** Developer Environment (Lesson 0)

**What you build:** A script named `ex00_verify_env.py` saved in the `exercises/` directory.
It imports every major MarketPulse dependency and reports which are installed and which are
missing. Run this after Phase 0 to confirm the venv is complete.

**Time estimate:** 20 minutes

---

### What to implement

Create a `dataclass` called `Check` with three fields: `name` (the display label), `module` (the
Python import name), and `subprocess` (a boolean that defaults to `False`).

Build a list of `Check` instances covering every package below. The import name is what you
pass to `__import__()` — it is NOT always the pip package name.

| Display name | pip package | Import name |
|---|---|---|
| FastAPI | fastapi | fastapi |
| Pydantic | pydantic | pydantic |
| asyncpg | asyncpg | asyncpg |
| Redis (valkey) | redis | redis |
| ChromaDB | chromadb | chromadb |
| Motor (MongoDB) | motor | motor |
| Elasticsearch | elasticsearch | elasticsearch |
| InfluxDB client | influxdb-client | influxdb_client |
| MinIO | minio | minio |
| PyTorch | torch | torch |
| XGBoost | xgboost | xgboost |
| LightGBM | lightgbm | lightgbm |
| Transformers | transformers | transformers |
| VADER | vaderSentiment | vaderSentiment |
| sentence-trans. | sentence-transformers | sentence_transformers |
| grpcio | grpcio | grpc |
| pandas | pandas | pandas |
| ta | ta | ta |
| numpy | numpy | numpy |
| PRAW | praw | praw |
| feedparser | feedparser | feedparser |
| yfinance | yfinance | yfinance |
| ARQ | arq | arq |
| discord.py | discord.py | discord |
| mplfinance | mplfinance | mplfinance |
| Pillow | Pillow | PIL |
| pyotp | pyotp | pyotp |
| structlog | structlog | structlog |
| msgpack | msgpack | msgpack |
| DuckDB | duckdb | duckdb |
| ZODB | ZODB | ZODB |
| NetworkX | networkx | networkx |
| reportlab | reportlab | reportlab |
| tenacity | tenacity | tenacity |
| Hypothesis | hypothesis | hypothesis |
| Locust | locust | locust |
| cassandra-driver | cassandra-driver | cassandra |
| neo4j driver | neo4j | neo4j |
| web3.py | web3 | web3 |
| qrcode | qrcode | qrcode |
| Alembic | alembic | alembic |
| aiosmtplib | aiosmtplib | aiosmtplib |
| Twilio | twilio | twilio |

Loop over the list. For each `Check`, wrap `__import__(check.module)` in a try/except catching
`ImportError`. On success print `  ✓  {check.name}`. On failure print `  ✗  {check.name}  →  {e}`.
Track a running count of passed and failed checks. After the loop, print `{N} passed, {N} failed`.
Call `sys.exit(1)` if any failed.

**Locust requires special handling.** Locust calls `gevent.monkey.patch_all()` the moment it is
imported. This corrupts the SSL context that asyncio-based libraries (aiohttp, anyio, jwt) already
loaded, causing a `RecursionError` deep in `ssl.py`. The fix: for any `Check` where
`check.subprocess is True`, instead of calling `__import__()`, use `subprocess.run()` to launch a
fresh child process (`sys.executable`, `-c`, `f"import {check.module}"`) and check its return code.
If the return code is non-zero, decode `stderr`, extract the last line, and raise `ImportError` from
it. Mark Locust with `subprocess=True` in your check list.

**Documentation:**
- `dataclasses` module: https://docs.python.org/3/library/dataclasses.html
- `__import__` built-in: https://docs.python.org/3/library/functions.html#import__
- `subprocess.run`: https://docs.python.org/3/library/subprocess.html#subprocess.run
- `sys.exit`: https://docs.python.org/3/library/sys.html#sys.exit

---

### Expected output

```
  ✓  FastAPI
  ✓  Pydantic
  ✓  asyncpg
  ...
  ✓  Alembic
  ✓  aiosmtplib
  ✓  Twilio

43 passed, 0 failed
```

---

## Exercise 1 — OHLCV from yfinance + RSI from Scratch

**Lesson it reinforces:** OHLCV fundamentals and technical indicators (Lessons 1 and 6)

**What you build:** A script named `ex01_ohlcv_rsi.py`. Fetch 2 years of real AAPL daily OHLCV
data. Implement the RSI-14 formula from scratch using only pandas and numpy. Verify your result
numerically matches the `ta` library's RSIIndicator output within a floating-point tolerance.
Print a summary of the latest close price and RSI signal.

**Time estimate:** 45 minutes

---

### What to implement

**Step 1 — Fetch OHLCV data.** Use `yfinance.Ticker("AAPL").history(period="2y")` to download
2 years of daily data. The result is a pandas DataFrame with columns `Open`, `High`, `Low`,
`Close`, `Volume`, `Dividends`, and `Stock Splits`. The index is a timezone-aware DatetimeIndex.
Strip the timezone using `.tz_localize(None)` so comparisons work cleanly. Print the row count
and the last 3 rows of the five OHLCV columns.

**Step 2 — Implement RSI-14 from scratch.** Write a function `compute_rsi(close, period=14)`
that accepts a `pd.Series` of closing prices and returns a `pd.Series` of RSI values. Implement
the exact Wilder smoothing formula:

1. Compute `delta = close.diff()` — the one-day price change for each row.
2. Split into gains (values where delta > 0, zero elsewhere) and losses (absolute values where
   delta < 0, zero elsewhere).
3. Compute the exponential moving average of gains and losses separately using Wilder's smoothing.
   Wilder's smoothing is identical to an EWM with `alpha = 1 / period`. Call
   `.ewm(alpha=1/period, min_periods=period, adjust=False).mean()` on both series.
4. Compute `rs = avg_gain / avg_loss`.
5. Compute `rsi = 100 - (100 / (1 + rs))`.
6. Return the rsi Series. The first `period - 1` values will be NaN due to the warmup period —
   this is correct behavior.

**Step 3 — Verify against the `ta` library.** Import `RSIIndicator` from `ta.momentum`. Create
an instance with `close=df["Close"]` and `window=14`, then call `.rsi()` to get the ta-computed
RSI series. Build a comparison DataFrame with three columns: `scratch` (your result), `ta` (the
library result), and `diff` (absolute difference). Drop NaN rows and print the last 5 rows of
the comparison. Assert that the maximum difference is less than `0.01`. If it is not, your EWM
parameters are wrong — re-read the Wilder smoothing section in the `ta` source and the pandas
EWM docs.

**Step 4 — Print a signal summary.** Print the latest closing price and latest RSI value. Print
`OVERBOUGHT (>70)`, `OVERSOLD (<30)`, or `NEUTRAL` based on the RSI value.

**Important subtlety:** The `adjust=False` parameter in `.ewm()` is critical. Without it, pandas
uses a different initialization that does not match Wilder's method and your values will diverge
from the `ta` library after the first few rows.

**Documentation:**
- yfinance: https://github.com/ranaroussi/yfinance
- pandas `.ewm()`: https://pandas.pydata.org/docs/reference/api/pandas.Series.ewm.html
- ta library RSIIndicator: https://technical-analysis-library-in-python.readthedocs.io/en/latest/ta.html#ta.momentum.RSIIndicator

---

### Expected output (values vary with current market data)

```
Fetched 503 rows of AAPL OHLCV data
[last 3 rows of Open/High/Low/Close/Volume]

RSI comparison (last 5 trading days):
         scratch      ta    diff
Date
...       54.23    54.23  0.0000
...       51.88    51.88  0.0000

✓ RSI from scratch matches ta (max diff: 0.000123)

AAPL summary:
  Latest close: $221.34
  RSI-14:       56.1
  Signal:       NEUTRAL
```

---

## Exercise 2 — News Headlines + VADER

**Lesson it reinforces:** News and RSS ingestion (Lesson 7)

**What you build:** A script named `ex02_news_vader.py`. Fetch the 20 most recent English-language
news articles mentioning AAPL from the NewsAPI REST endpoint. Score each article's title and
description with VADER. Print the 3 most bullish and 3 most bearish headlines. Print an aggregate
sentiment label for AAPL.

**Time estimate:** 30 minutes

**Prerequisite:** A free NewsAPI key from https://newsapi.org. Store it as the environment variable
`NEWSAPI_KEY`. Read it with `os.environ.get("NEWSAPI_KEY")` and raise a descriptive `ValueError`
if it is missing.

---

### What to implement

**Step 1 — Fetch news.** Make a GET request to `https://newsapi.org/v2/everything` using the
`requests` library. Pass these query parameters: `q` set to `"AAPL OR Apple stock"`, `sortBy`
set to `"publishedAt"`, `language` set to `"en"`, `pageSize` set to `20`, and `apiKey` set to
your key. Use a timeout of 10 seconds. Call `.raise_for_status()` on the response. Parse the JSON
and extract the `"articles"` list. Print the count of articles fetched.

**Step 2 — Score with VADER.** Import `SentimentIntensityAnalyzer` from
`vaderSentiment.vaderSentiment`. Create a single analyzer instance outside the loop (instantiation
is expensive). For each article, combine the `title` and `description` fields into one string with
a period separator. Handle missing descriptions — `article.get("description")` can return `None`;
replace it with an empty string in that case. Call `analyzer.polarity_scores(text)` which returns
a dict with four keys: `compound` (overall score from -1 to +1), `pos`, `neg`, and `neu`. Store
the headline (truncated to 80 characters), compound score, and all three sub-scores in a list.

**Step 3 — Sort and display.** Sort the scored list by compound score descending (most positive
first). Print the top 3 (most bullish) and bottom 3 (most bearish) headlines with their compound
scores formatted to 3 decimal places. A compound score above `+0.05` is conventionally bullish;
below `-0.05` is bearish.

**Step 4 — Aggregate.** Average the compound scores across all 20 articles. Print the average and
label it `BULLISH` (> 0.05), `BEARISH` (< -0.05), or `NEUTRAL`.

**Documentation:**
- NewsAPI everything endpoint: https://newsapi.org/docs/endpoints/everything
- requests library: https://docs.python-requests.org/en/latest/user/quickstart/
- VADER (vaderSentiment): https://github.com/cjhutto/vaderSentiment
- VADER compound score explanation: https://github.com/cjhutto/vaderSentiment#about-the-scoring

---

### Expected output (varies daily)

```
Fetched 20 articles

=== TOP 3 MOST BULLISH ===
  [+0.872] Apple beats Q3 earnings estimates, raises guidance for Q4 revenue
  [+0.614] iPhone 17 pre-orders smash records according to analyst estimates
  [+0.421] Apple's AI features drive record App Store spending this quarter

=== TOP 3 MOST BEARISH ===
  [-0.532] Apple supply chain issues could impact holiday season production
  [-0.314] Regulators open antitrust probe into Apple's App Store fees
  [-0.102] Apple stock retreats from all-time high on profit-taking

Aggregate AAPL news sentiment: +0.187
Overall tone: BULLISH
```

---

## Exercise 3 — Reddit + PRAW Sentiment

**Lesson it reinforces:** Reddit ingestion (Lesson 8)

**What you build:** A script named `ex03_reddit_praw.py`. Connect to Reddit using PRAW. Fetch the
top 200 hot posts from r/wallstreetbets. Filter for posts that mention AAPL or TSLA. Score each
matching post with VADER. Compute an upvote-weighted sentiment score per ticker. Print a ranked
table and per-ticker aggregates.

**Time estimate:** 30 minutes

**Prerequisites:** A Reddit developer app (https://www.reddit.com/prefs/apps — create a "script"
type app). Store credentials as environment variables: `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`,
`REDDIT_USER_AGENT`. `REDDIT_USER_AGENT` defaults to `"MarketPulse/1.0"` if not set.

---

### What to implement

**Step 1 — Connect to Reddit.** Create a `praw.Reddit` instance passing `client_id`,
`client_secret`, and `user_agent` from environment variables.

**Step 2 — Ticker detection.** Write a function `extract_tickers(text)` that finds ticker
mentions in a string. Use a compiled `re.compile` pattern that matches either `$TICKER` format
(dollar sign followed by 1-5 uppercase letters) or standalone 2-5 character uppercase words
that are not surrounded by word characters. `re.compile(r'\$([A-Z]{1,5})|(?<!\w)([A-Z]{2,5})(?!\w)')`
achieves this. After extracting all regex matches, return only the subset that are in your target
set `{"AAPL", "TSLA"}` — this prevents false positives like "I", "THE", "AND" from matching.

**Step 3 — Fetch and filter posts.** Call `reddit.subreddit("wallstreetbets").hot(limit=200)`.
Iterate over the result. For each post, concatenate `post.title` and `post.selftext` and run your
ticker detection function. If any target tickers are found, score the post title with VADER (use
only the title for sentiment — `selftext` is too noisy). Compute a log-scaled engagement weight
using `math.log1p(post.score + 0.5 * post.num_comments)` where `post.score` is upvotes.
Multiply the raw VADER compound score by the weight to get the weighted score. Store: title
(truncated to 70 chars), matched tickers, upvote count, comment count, raw VADER score, weight,
and weighted score. Stop after collecting 10 matching posts.

**Step 4 — Display.** Print a table with columns: title, tickers, raw VADER score, weight, and
weighted score. Align with f-string formatting.

**Step 5 — Aggregate per ticker.** For each target ticker, filter the posts list to those that
mentioned it. Compute the total weight as the sum of individual weights. Compute the weighted
average sentiment as the sum of weighted scores divided by total weight. Print each ticker's
weighted average, post count, and total weight.

**Documentation:**
- PRAW quickstart: https://praw.readthedocs.io/en/stable/getting_started/quick_start.html
- PRAW Subreddit.hot: https://praw.readthedocs.io/en/stable/code_overview/models/subreddit.html
- Python `re` module: https://docs.python.org/3/library/re.html
- `math.log1p`: https://docs.python.org/3/library/math.html#math.log1p

---

### Expected output (varies daily)

```
Found 10 relevant posts in r/wallstreetbets

Title                                                                    Tickers      Raw   Weight  Weighted
AAPL calls printing after earnings beat, up 8% premarket                AAPL       +0.636   8.42    +5.355
I've been holding TSLA for 3 years and I'm finally in the green         TSLA       +0.440   7.15    +3.146
...

=== AGGREGATE SENTIMENT ===
  AAPL: +0.312  (6 posts, total weight 48.3)
  TSLA: +0.189  (4 posts, total weight 29.1)
```

---

## Exercise 4 — All Technical Indicators with ta

**Lesson it reinforces:** Technical indicators (Lesson 9)

**What you build:** A script named `ex04_indicators.py`. Fetch 1 year of MSFT daily OHLCV.
Compute six families of technical indicators using the `ta` library. Print a table of the last
5 values for each indicator. Assert that no indicator column has NaN in the last 5 rows.

**Time estimate:** 30 minutes

---

### What to implement

**Step 1 — Fetch data.** Use `yfinance.Ticker("MSFT").history(period="1y")`. Strip timezone from
the index.

**Step 2 — Compute all indicators.** Add each indicator as a new column on the DataFrame using
the `ta` library's class-based API. All classes live under `ta.<family>.<ClassName>`. Every
class is instantiated with keyword arguments, then you call a method on the instance to get the
series.

Indicators to compute and the exact class and method for each:

- **RSI-14**: `ta.momentum.RSIIndicator(close=df["Close"], window=14).rsi()` → store as `RSI_14`
- **MACD line**: `ta.trend.MACD(close=df["Close"], window_fast=12, window_slow=26, window_sign=9).macd()` → store as `MACD_line`
- **MACD signal**: same `MACD` instance, call `.macd_signal()` → store as `MACD_signal`
- **MACD histogram**: same `MACD` instance, call `.macd_diff()` → store as `MACD_hist`
- **Bollinger upper**: `ta.volatility.BollingerBands(close=df["Close"], window=20, window_dev=2).bollinger_hband()` → store as `BBU`
- **Bollinger middle**: same `BollingerBands` instance, `.bollinger_mavg()` → store as `BBM`
- **Bollinger lower**: same `BollingerBands` instance, `.bollinger_lband()` → store as `BBL`
- **Bollinger %B**: same `BollingerBands` instance, `.bollinger_pband()` → store as `BBP`
- **OBV**: `ta.volume.OnBalanceVolumeIndicator(close=df["Close"], volume=df["Volume"]).on_balance_volume()` → store as `OBV`
- **ATR-14**: `ta.volatility.AverageTrueRange(high=df["High"], low=df["Low"], close=df["Close"], window=14).average_true_range()` → store as `ATR_14`
- **ADX-14**: `ta.trend.ADXIndicator(high=df["High"], low=df["Low"], close=df["Close"], window=14).adx()` → store as `ADX_14`
- **Volume SMA-20**: `df["Volume"].rolling(20).mean()` → store as `Volume_SMA_20`

**Important:** Create a single MACD instance and a single BollingerBands instance for each — do
not create a new instance for each method call. Three method calls on one instance is correct.

**Step 3 — Validate and display.** Build an ordered dict mapping human-readable names to column
names. Iterate over it. For each, take the last 5 values of that column. Check for NaN using
`pd.isna()`. If any NaN exists, print `✗ {name} has NaN` and set a flag. If all are finite,
print `✓ {name}` followed by the 5 values formatted to 2 decimal places. After the loop, print
the overall result.

**Documentation:**
- ta library full API: https://technical-analysis-library-in-python.readthedocs.io/en/latest/ta.html
- ta GitHub (source, examples): https://github.com/bukosabino/ta
- pandas `.rolling()`: https://pandas.pydata.org/docs/reference/api/pandas.Series.rolling.html

---

### Expected output

```
MSFT: 252 trading days

Indicator               5 days ago    4 days ago    3 days ago     Yesterday        Today
──────────────────────────────────────────────────────────────────────────────────────────
  ✓ RSI-14                   58.34         57.89         60.12         59.43        61.78
  ✓ MACD Line                 1.23          1.45          2.01          1.87         2.34
  ✓ MACD Signal               0.98          1.08          1.35          1.54         1.76
  ✓ MACD Hist                 0.25          0.37          0.66          0.33         0.58
  ...
  ✓ Volume SMA-20       21345678     21456789     21567890     21678901    21789012

✓ All indicators valid
```

---

## Exercise 5 — Minimal LSTM for Price Direction

**Lesson it reinforces:** ML prediction pipeline (Lesson 11)

**What you build:** A script named `ex05_lstm.py`. Fetch 2 years of GOOGL daily close prices.
Transform to log returns. Build a PyTorch Dataset that produces 30-day input windows and binary
direction labels. Train a 2-layer LSTM for 20 epochs. Evaluate on a held-out test set. Print
training loss every 5 epochs and final test accuracy.

**Time estimate:** 90 minutes

---

### What to implement

**Step 1 — Load and transform data.** Use yfinance to fetch 2 years of GOOGL daily history.
Extract the `Close` series as a numpy float32 array. Compute log returns as
`log_returns = np.log(close[1:] / close[:-1])`. Print the count, mean, and standard deviation.
Log returns are stationary (no upward drift), which makes them far better LSTM inputs than raw
prices.

**Step 2 — Dataset class.** Subclass `torch.utils.data.Dataset`. In `__init__`, build two lists:
`X` (input windows) and `y` (labels). Iterate `i` from `WINDOW` to `len(returns)`. For each `i`,
the input window is `returns[i-WINDOW:i]` — the 30 days ending at index `i-1`, with no
look-ahead. The label is `1` if `returns[i] > 0` (tomorrow is up), else `0`. After the loop,
convert `X` to a `torch.float32` tensor of shape `(N, WINDOW, 1)` — the final `1` is the input
feature dimension expected by the LSTM. Convert `y` to a `torch.long` tensor (required by
`CrossEntropyLoss`). Use `WINDOW = 30`. Implement `__len__` and `__getitem__` as required by the
PyTorch Dataset contract.

**Step 3 — Train/test split.** Split 80% train, 20% test by index, not by shuffling — shuffling
would cause look-ahead bias. Create two `Subset` views of the full dataset using
`torch.utils.data.Subset(dataset, range(...))`. Wrap each in a `DataLoader` with `batch_size=16`.
Set `shuffle=True` for the training loader only.

**Step 4 — LSTM model.** Subclass `nn.Module`. In `__init__`, create an `nn.LSTM` with
`input_size=1`, `hidden_size=32`, `num_layers=2`, `batch_first=True`, and `dropout=0.2`. Create
an `nn.Linear(32, 2)` fully-connected output layer (2 classes: down, up). In `forward`, pass the
input through the LSTM and receive `(out, _)`. Take only the last timestep: `out[:, -1, :]`.
Pass that through the linear layer. Return the logits. Print the total parameter count using
`sum(p.numel() for p in model.parameters())`.

**Step 5 — Training loop.** Use `nn.CrossEntropyLoss()` and `torch.optim.Adam` with `lr=0.001`.
For each epoch: set model to `train()` mode, iterate the training DataLoader, call `optimizer.zero_grad()`,
compute `logits = model(X_batch)`, compute `loss = criterion(logits, y_batch)`, call
`loss.backward()` and `optimizer.step()`. Accumulate the loss and compute the average per epoch.
Print `Epoch {n}/20  loss={avg:.4f}` every 5 epochs.

**Step 6 — Evaluation.** Set model to `eval()` mode. Use `torch.no_grad()`. Iterate the test
DataLoader. For each batch, get predictions with `.argmax(dim=1)` and compare to labels. Sum
correct predictions and total samples. Compute accuracy as `correct / total`. Print the accuracy
as a percentage and compare it to the 50% random-guessing baseline.

**Note on results:** 20 epochs is not enough to train a production model. You will likely see
accuracy in the 50–56% range. The important outcome is that the architecture runs without errors
and the loss decreases during training. Production training uses 200+ epochs, walk-forward cross-
validation, and probability calibration.

**Documentation:**
- PyTorch Dataset/DataLoader tutorial: https://pytorch.org/tutorials/beginner/basics/data_tutorial.html
- nn.LSTM: https://pytorch.org/docs/stable/generated/torch.nn.LSTM.html
- nn.CrossEntropyLoss: https://pytorch.org/docs/stable/generated/torch.nn.CrossEntropyLoss.html
- Adam optimizer: https://pytorch.org/docs/stable/generated/torch.optim.Adam.html

---

### Expected output (approximate — results vary due to random initialization)

```
Fetching GOOGL data...
Log returns: 502 values, mean=0.0007, std=0.0182

Model parameters: 14,018

Training...
  Epoch  5/20  loss=0.6912
  Epoch 10/20  loss=0.6887
  Epoch 15/20  loss=0.6854
  Epoch 20/20  loss=0.6821

Test accuracy: 53.2%
Baseline (random): 50.0%
Lift over baseline: +3.2 percentage points
```

---

## Exercise 6 — Minimal gRPC Client + Server

**Lesson it reinforces:** gRPC sidecar architecture (Lesson 11)

**What you build:** A `.proto` schema file, a gRPC server in `ex06_server.py`, and a gRPC client
in `ex06_client.py`. The server accepts prediction requests and returns stub responses. The client
sends 12 requests (3 symbols × 4 horizons) and prints each response with latency.

**Time estimate:** 60 minutes

---

### What to implement

**Step 1 — Write the `.proto` file.** Save as `exercises/ex06_prediction.proto`. Define a
package named `exercises`. Define a service `PredictionService` with one RPC method `Predict`
that takes a `PredictionRequest` and returns a `PredictionResponse`. The request message must have:
`symbol` (string, field 1), `horizon` (string — "1d", "3d", "7d", "30d" — field 2), and
`features` (repeated float, field 3). The response message must have: `symbol` (string, field 1),
`horizon` (string, field 2), `direction` (string — "UP", "DOWN", "FLAT" — field 3),
`confidence` (float from 0.0 to 1.0, field 4), `model_version` (string, field 5), and
`error` (string for error messages, field 6).

**Step 2 — Generate Python stubs.** From the `exercises/` directory, run:

```
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. ex06_prediction.proto
```

This generates two files: `ex06_prediction_pb2.py` (message classes) and
`ex06_prediction_pb2_grpc.py` (service base classes and stubs). Do not edit these files — they
are auto-generated.

**Step 3 — Implement the server** (`ex06_server.py`). Import the generated `pb2` and `pb2_grpc`
modules. Import `grpc`, `random`, `time`, and `concurrent.futures`. Create a servicer class that
inherits from `pb2_grpc.PredictionServiceServicer`. Override the `Predict` method. Inside it,
print that a request was received for the given symbol and horizon, and print the feature vector
length. Generate a random direction from `["UP", "DOWN", "FLAT"]` and a random confidence between
0.45 and 0.92. Sleep 50ms to simulate inference time. Return a `pb2.PredictionResponse` populated
with all fields. In the `serve()` function: create a `grpc.server` with a `ThreadPoolExecutor(max_workers=4)`,
register the servicer with `pb2_grpc.add_PredictionServiceServicer_to_server`, add port 50051
with `server.add_insecure_port("[::]:50051")`, call `server.start()`, print that the server is
listening, then call `server.wait_for_termination()`. Call `serve()` inside `if __name__ == "__main__"`.

**Step 4 — Implement the client** (`ex06_client.py`). Import the same generated modules. Write a
`predict(symbol, horizon, features)` function that opens an insecure channel to `"localhost:50051"`,
creates a stub, builds a `PredictionRequest`, records the start time with `time.perf_counter()`,
calls `stub.Predict(request, timeout=5.0)`, computes latency in milliseconds, and returns the
response and latency. In `__main__`, generate a list of 45 random Gaussian floats as a fake
feature vector. Iterate over all combinations of 3 symbols (`AAPL`, `TSLA`, `BTC-USD`) and 4
horizons (`1d`, `3d`, `7d`, `30d`). Call `predict()` for each and print the symbol, horizon,
direction, confidence percentage, latency in ms, and model version.

**Step 5 — Run both.** Open two separate PowerShell terminals, both with the venv activated.
In Terminal 1: `python exercises/ex06_server.py`. In Terminal 2: `python exercises/ex06_client.py`.

**Documentation:**
- gRPC Python basics: https://grpc.io/docs/languages/python/basics/
- grpc_tools.protoc usage: https://grpc.io/docs/languages/python/quickstart/
- Protocol Buffers language guide: https://protobuf.dev/programming-guides/proto3/
- grpc.server API: https://grpc.github.io/grpc/python/grpc.html#grpc.server

---

### Expected output — Terminal 1 (server)

```
gRPC server listening on port 50051
  [server] Received prediction request for AAPL 1d
  [server] Feature vector length: 45
  [server] Received prediction request for AAPL 3d
  ... (12 total requests)
```

### Expected output — Terminal 2 (client)

```
Sending prediction requests...

  AAPL     1d  →  UP    72.3%  (53ms)  [model: stub-v0.1]
  AAPL     3d  →  FLAT  61.8%  (51ms)  [model: stub-v0.1]
  AAPL     7d  →  DOWN  88.4%  (49ms)  [model: stub-v0.1]
  AAPL     30d →  UP    53.2%  (52ms)  [model: stub-v0.1]
  TSLA     1d  →  DOWN  79.1%  (50ms)  [model: stub-v0.1]
  ... (12 total responses)
```

---

## Exercise 7 — Candlestick Chart with mplfinance

**Lesson it reinforces:** Discord bot chart generation (Lesson 13)

**What you build:** A script named `ex07_chart.py`. Fetch 90 days of NVDA OHLCV. Compute a 50-day
SMA and Bollinger Bands (20-day, 2 standard deviations). Render a publication-quality candlestick
chart with volume bars, SMA-50, and Bollinger Band overlays using mplfinance. Save as PNG. Verify
the file size is under 200 KB.

**Time estimate:** 45 minutes

---

### What to implement

**Step 1 — Fetch and prepare data.** Use `yfinance.Ticker("NVDA").history(period="90d")`. Strip
the timezone from the index. Extract the five standard columns (`Open`, `High`, `Low`, `Close`,
`Volume`) into a copy — mplfinance requires these exact column names, capitalized.

**Step 2 — Compute overlays.** Add `SMA50` to the DataFrame using `df["Close"].rolling(50).mean()`.
Create a `BollingerBands` instance from `ta.volatility` with `window=20` and `window_dev=2`.
Store the upper band (`bollinger_hband()`) and lower band (`bollinger_lband()`) as `BBU` and
`BBL` columns. Note: 90 calendar days of trading data is roughly 63 trading days, which is enough
for a 20-day period but the SMA-50 will have NaN for the first ~50 rows — this is expected and
mplfinance handles it gracefully.

**Step 3 — Build addplots.** Use `mpf.make_addplot()` to create three overlay plot objects:
one for `SMA50` (solid blue line, width 1.5), one for `BBU` (gray dashed line, width 1.0), one
for `BBL` (gray dashed line, width 1.0). Each addplot is overlaid on the price panel by default.
The `make_addplot` function takes the pandas Series as its first argument, then keyword arguments
for `color`, `linestyle`, `width`, and `label`.

**Step 4 — Render and save.** Call `mpf.plot()` with: the DataFrame as the first argument,
`type="candle"`, `style="charles"`, `title="NVDA — 90 Day Chart"`, `ylabel="Price (USD)"`,
`volume=True`, `addplot=[ap_sma, ap_bbu, ap_bbl]`, `figsize=(14, 8)`, and
`savefig=dict(fname="exercises/nvda_chart.png", dpi=100, bbox_inches="tight")`. The `volume=True`
parameter adds a second panel below the candlesticks. The `style="charles"` style uses a dark
background with green/red candles.

**Step 5 — Verify.** Get the file size in KB with `os.path.getsize()`. Assert it is under 200.
Print the path and size.

**What this exercise teaches about the Discord bot:** After generating this PNG, the production
bot uploads it to MinIO using `minio_client.put_object()`, generates a presigned URL with
`presigned_get_object()`, and sends it in a Discord message using `discord.File(path)`. Print
these three steps as informational output at the end.

**Documentation:**
- mplfinance: https://github.com/matplotlib/mplfinance
- mplfinance `make_addplot`: https://github.com/matplotlib/mplfinance/blob/master/examples/addplot.ipynb
- mplfinance styles: https://github.com/matplotlib/mplfinance/blob/master/examples/styles.ipynb
- ta BollingerBands: https://technical-analysis-library-in-python.readthedocs.io/en/latest/ta.html#ta.volatility.BollingerBands
- `os.path.getsize`: https://docs.python.org/3/library/os.path.html#os.path.getsize

---

### Expected output

```
NVDA: 63 trading days of OHLCV
Chart saved to: exercises/nvda_chart.png
File size: 143.7 KB
✓ Chart generated successfully (under 200 KB)

In the Discord bot, the next step would be:
  1. Upload this PNG to MinIO: minio_client.put_object('charts', 'NVDA_chart.png', ...)
  2. Get presigned URL: minio_client.presigned_get_object('charts', 'NVDA_chart.png')
  3. Send to Discord: await interaction.followup.send(file=discord.File(output_path))
```

---

## Exercise 8 — Minimal Discord Bot with One Slash Command

**Lesson it reinforces:** Discord bot (Lesson 13)

**What you build:** A running Discord bot in `ex08_discord_bot.py` with one slash command
called `/hello`. When a user invokes `/hello` in your test server, the bot replies with a
formatted embed showing the user's name, the current UTC time, and a made-up sample prediction
for AAPL.

**Time estimate:** 45 minutes

**Prerequisites:** Create a Discord application and bot at https://discord.com/developers/applications.
Under "Bot", create a token and copy it. Under "OAuth2 → URL Generator", select the `bot` and
`applications.commands` scopes, select "Send Messages" and "Embed Links" permissions, and use the
generated URL to invite the bot to your test server. Store as `DISCORD_BOT_TOKEN` (the bot token)
and `DISCORD_GUILD_ID` (your server's ID — right-click the server name → Copy Server ID) in
environment variables.

---

### What to implement

**Step 1 — Set up the client class.** Create a class that inherits from `discord.Client`. In
`__init__`, call the parent `__init__` with `intents=discord.Intents.default()` and create an
`app_commands.CommandTree(self)` instance stored as `self.tree`. This tree is the registry for
slash commands.

**Step 2 — Guild sync.** Override `setup_hook` (an async method called before the bot connects).
Inside it, create a `discord.Object(id=GUILD_ID)` representing your test server. Call
`self.tree.copy_global_to(guild=guild)` to copy any global commands to the guild, then
`await self.tree.sync(guild=guild)` to push them to Discord. Print the number of synced commands.
Guild sync is instant (used for development). Global sync takes up to 1 hour.

**Step 3 — Ready event.** Override `on_ready` (also async). Print the bot's username and ID.
Print a message telling you to go type `/hello` in your server.

**Step 4 — Register the slash command.** Below the class definition, after instantiating the
client, use `@client.tree.command(name="hello", description="...")` to decorate an async function.
The function must accept `interaction: discord.Interaction` as its sole parameter. Inside it:
read `interaction.user.display_name`. Get the current UTC time using `datetime.now(timezone.utc)`
and format it as `"YYYY-MM-DD HH:MM UTC"`. Build a `discord.Embed` with a title, description
that greets the user by name, and `color=discord.Color.green()`. Add three inline fields:
`Direction` ("⬆️ **UP**"), `Confidence` ("**82.4%**"), `Horizon` ("**1 day**"). Add one
non-inline field named `Signal` with a short made-up signal description. Add a footer with
`"MarketPulse • {now_utc}"`. Call `await interaction.response.send_message(embed=embed)`. Print
to the terminal that the command was invoked and by whom.

**Step 5 — Run the bot.** Call `client.run(TOKEN)` at the bottom of the script.

**Documentation:**
- discord.py quickstart: https://discordpy.readthedocs.io/en/stable/quickstart.html
- app_commands introduction: https://discordpy.readthedocs.io/en/stable/interactions/api.html
- discord.Embed: https://discordpy.readthedocs.io/en/stable/api.html#discord.Embed
- discord.Intents: https://discordpy.readthedocs.io/en/stable/api.html#discord.Intents
- Setup hook lifecycle: https://discordpy.readthedocs.io/en/stable/api.html#discord.Client.setup_hook

---

### Expected output — terminal

```
Synced 1 command(s) to guild 123456789
Logged in as MarketPulseBot#1234 (ID: 987654321)
─────────────────────────────────────
Ready. Go to your Discord server and type /hello
  /hello called by Brodie
```

### Expected output — Discord

A green-bordered embed card with title "📈 AAPL — Sample Prediction", a greeting message, three
inline fields showing Direction/Confidence/Horizon, and one body field with a signal explanation.

---

## Exercise 9 — TOTP 2FA from Scratch

**Lesson it reinforces:** Authentication (Lesson 19)

**What you build:** A script named `ex09_totp.py` that walks through the complete TOTP enrollment
and verification flow. Generate a secret. Create an `otpauth://` QR code URI. Save a QR code PNG
that an authenticator app could scan. Verify the current code. Demonstrate the valid time window.
Explain the replay attack vulnerability and how to block it.

**Time estimate:** 40 minutes

---

### What to implement

**Step 1 — Generate the secret.** Call `pyotp.random_base32()` to generate a random Base32-
encoded secret. In production this is generated once per user during 2FA enrollment and stored
encrypted in the database. Print it with a note that it must be stored securely.

**Step 2 — Create the QR code URI.** Instantiate `pyotp.TOTP(secret)`. Call
`.provisioning_uri(name="your-email@example.com", issuer_name="MarketPulse")` to generate an
`otpauth://totp/...` URI. This is the standard format understood by Google Authenticator, Authy,
Microsoft Authenticator, and 1Password. Print the URI.

**Step 3 — Generate and save the QR code.** Call `qrcode.make(uri)` to create a QR code image.
Call `.save("exercises/ex09_totp_qr.png")` to write it to disk. Print the save path. Print a
note that in a real app, this PNG is returned as a base64-encoded string in the enrollment API
response so the frontend can display it inline.

**Step 4 — Simulate verification.** Call `totp.now()` to get the code that a properly-configured
authenticator app would show right now. Print it along with a note that it is valid for up to 30
seconds. Call `totp.verify(current_code, valid_window=1)` and print whether it is valid. Assert
that it returns `True` — if it doesn't, your system clock is wrong. The `valid_window=1` parameter
accepts codes from the previous and next 30-second window to handle minor clock skew between the
server and the user's device.

**Step 5 — Demonstrate the time window.** Show that a code from 30 seconds ago is also accepted
with `valid_window=1`. Generate it using `pyotp.TOTP(secret).at(time.time() - 30)`. Verify it
with the same `valid_window=1` call and print the result. This is why `valid_window` must be
kept at 1, not higher — every additional window increases the attack surface.

**Step 6 — Replay attack.** Demonstrate that the same code can be verified twice in the same
30-second window (try calling `totp.verify(current_code, valid_window=1)` twice — both return
`True`). Print a warning that production code must store every used code in Valkey with a TTL of
90 seconds (one window before + current window + one window after) to prevent replay attacks.
Print the key pattern: `totp:used:{user_id}:{code}` with `EXPIRE 90`.

**Documentation:**
- pyotp: https://pyauth.github.io/pyotp/
- pyotp TOTP: https://pyauth.github.io/pyotp/#time-based-otps
- RFC 6238 (TOTP standard): https://datatracker.ietf.org/doc/html/rfc6238
- qrcode library: https://github.com/lincolnloop/python-qrcode
- otpauth URI format: https://github.com/google/google-authenticator/wiki/Key-Uri-Format

---

### Expected output

```
Generated TOTP secret (store this securely!): JBSWY3DPEHPK3PXP

otpauth URI: otpauth://totp/MarketPulse:your-email@example.com?secret=JBSWY3DPEHPK3PXP&issuer=MarketPulse

QR code saved to: exercises/ex09_totp_qr.png

Current TOTP code (valid for up to 30 seconds): 482931
Verification result: ✓ VALID

Window behavior:
  Current code:  482931 → valid
  Code from 30s ago: 719234 → valid (within window)

⚠ Replay attack note:
  Code '482931' can be verified again: True
  Production code must track used codes in Valkey to prevent replay attacks.
  Key pattern: totp:used:<user_id>:<code>  with TTL=90 seconds
```

---

## Exercise 10 — Valkey INCR Quota Counter

**Lesson it reinforces:** API quota tracking (Lesson 6)

**What you build:** An async script named `ex10_quota_counter.py`. Connect to Valkey. Simulate
100+ API calls against a daily quota key, demonstrating the INCR-based counter pattern. Show the
quota being exceeded. Demonstrate a per-minute rate limit key. Print the two-layer quota check
pattern and explain it in comments.

**Time estimate:** 30 minutes

**Prerequisite:** Valkey running locally. Start it with:
`docker run -d -p 6379:6379 valkey/valkey:7.2`

---

### What to implement

**Step 1 — Connect.** Use `redis.asyncio.from_url("redis://localhost:6379", decode_responses=True)`.
Call `await client.ping()` to verify the connection. Wrap everything in an async `main()` function
called with `asyncio.run(main())`.

**Step 2 — Define the key pattern.** Write a helper function `quota_key(source, day)` that takes
a string source name and a `datetime.date` object and returns a string in the format
`api:quota:{source}:{YYYY-MM-DD}`. This is the production key pattern — the date component makes
the key automatically namespace per day.

**Step 3 — Simulate daily quota.** Use a NewsAPI daily limit of 100 calls. Delete the key first
to reset the counter for this demo (`await client.delete(key)`). Loop 104 iterations. On each,
call `await client.incr(key)` and store the result. When the count is exactly 1 (first call of
the day), call `await client.expire(key, 86400)` to set a 24-hour TTL — this ensures the counter
automatically resets even if your cleanup job fails. Print the call number, current count,
remaining quota (max 0), and a ✓ or ✗ status for iterations 1–5 and 98–104. After the loop,
print the final count and the key's TTL using `await client.ttl(key)`.

**Step 4 — Per-minute rate limit.** Demonstrate a second pattern for Polygon.io's 5 calls/minute
limit. The key for this must include both the date and the current minute bucket — use integer
division of the current time by 60 to get a minute-stable bucket ID. Set a 60-second TTL on the
first increment. Loop 7 calls and print the result of each.

**Step 5 — Two-layer pattern explanation.** Print a multi-line explanation (as print statements
with inline code) showing the production `check_and_increment` function pattern that MarketPulse
uses. The function increments first (using a pipeline to run INCR and EXPIRE atomically), checks
the result, and if it exceeds the limit, decrements to roll back and returns `(False, count)`.
Simultaneously, it fires a non-blocking `asyncio.create_task` to log the call to PostgreSQL for
audit purposes.

**Documentation:**
- redis-py async: https://redis-py.readthedocs.io/en/stable/examples/asyncio_examples.html
- redis-py commands: https://redis-py.readthedocs.io/en/stable/commands.html
- Redis INCR: https://redis.io/docs/latest/commands/incr/
- Redis EXPIRE: https://redis.io/docs/latest/commands/expire/
- Redis pipeline: https://redis-py.readthedocs.io/en/stable/advanced_features.html#pipelines

---

### Expected output

```
Connected to Valkey

Simulating NewsAPI calls...
  Call   1: count=  1  remaining= 99  ✓
  Call   2: count=  2  remaining= 98  ✓
  ...
  Call 100: count=100  remaining=  0  ✓
  Call 101: count=101  remaining=  0  ✗ QUOTA EXCEEDED
  Call 104: count=104  remaining=  0  ✗ QUOTA EXCEEDED

Final NewsAPI count today: 104
Key TTL: 86399 seconds

Simulating Polygon.io rate limiting (5 calls/minute)...
  Call 1: minute_count=1  ✓
  Call 5: minute_count=5  ✓
  Call 6: minute_count=6  ✗ RATE LIMITED — wait

✓ Exercise complete
```

---

## Exercise 11 — SEC EDGAR Insider Trading Filings

**Lesson it reinforces:** Alternative data sources (Lessons 1 and 9)

**What you build:** A script named `ex11_sec_edgar.py`. Fetch the 10 most recent Form 4 (insider
transaction) filings for Apple (AAPL) from the SEC EDGAR REST API. Print a table of the filings.
Print the API endpoints used and explain what MarketPulse extracts from Form 4 XML documents.

**Time estimate:** 40 minutes

**No API key required.** The SEC EDGAR API is freely accessible — you only need a descriptive
User-Agent header to comply with SEC policy.

---

### What to implement

**Step 1 — Set the User-Agent header.** The SEC requires all API consumers to include a
descriptive `User-Agent` header in the format `"{App}/{version} {email}"`. Without it, your
requests will receive 403 responses. Set it as a module-level constant and include it in every
request. The SEC rate limit is 10 requests per second — add a 0.12-second sleep between requests
using `time.sleep(0.12)`.

**Step 2 — AAPL's CIK.** Every company registered with the SEC has a Central Index Key (CIK).
AAPL's CIK is `0000320193`. The EDGAR API requires it zero-padded to 10 digits in URLs.

**Step 3 — Fetch the submissions record.** Make a GET request to
`https://data.sec.gov/submissions/CIK{cik}.json` using the `requests` library with your User-Agent
header and a 10-second timeout. Call `.raise_for_status()`. Parse the JSON. Extract `data["name"]`
for the company name. Print it along with the CIK.

**Step 4 — Extract Form 4 filings.** The response contains a `filings.recent` object with
parallel arrays: `form`, `filingDate`, `accessionNumber`, and others. Iterate all three in
parallel using `zip()`. Collect entries where `form == "4"`. Stop after finding 10 results.
For each, strip hyphens from the accession number (the stored format is `XXXXXXXXXX-YY-ZZZZZZ`;
the URL format uses no hyphens).

**Step 5 — Display.** Print a numbered table with the filing date and accession number for each
of the 10 results.

**Step 6 — Document the next steps.** Print the three EDGAR API endpoints that MarketPulse uses:
the submissions endpoint, the company facts endpoint (`/api/xbrl/companyfacts/CIK{cik}.json`),
and the filing index URL pattern. Print a list of what the MarketPulse ingestion pipeline extracts
from the Form 4 XML: insider name, title (officer/director/10% owner), transaction type (P=purchase,
S=sale, A=award), number of shares, price per share, and post-transaction holdings.

**Documentation:**
- SEC EDGAR API overview: https://www.sec.gov/developer
- EDGAR submissions endpoint: https://data.sec.gov/submissions/CIK{cik}.json
- EDGAR company facts endpoint: https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json
- EDGAR full-text search: https://efts.sec.gov/LATEST/search-index?q=%22Apple+Inc%22&dateRange=custom&startdt=2024-01-01
- Form 4 XML schema: https://www.sec.gov/files/form4.xsd

---

### Expected output

```
Fetching AAPL insider filings from SEC EDGAR...

Company: Apple Inc.  (CIK: 0000320193)

Found 10 recent Form 4 filings:

#    Date         Accession Number
────────────────────────────────────────────
1    2026-07-28   000032019326000089
2    2026-07-15   000032019326000081
...

EDGAR API endpoints used:
  Company submissions: https://data.sec.gov/submissions/CIK{cik}.json
  Company facts:       https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json
  Form index:         https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/

In MarketPulse, the Form 4 XML documents are parsed to extract:
  - Insider name and title (officer, director, 10% owner)
  - Transaction type (P=purchase, S=sale, A=award, D=disposition)
  - Number of shares
  - Price per share
  - Post-transaction holdings
```

---

## Exercise 12 — FRED Federal Funds Rate + Plot

**Lesson it reinforces:** Macro indicators (Lesson 9)

**What you build:** A script named `ex12_fred_macro.py`. Query FRED for four macro series over
the past 5 years: the Federal Funds Rate, the 10-Year Treasury yield, CPI, and VIX. Print a
summary table of recent monthly observations. Save a 2×2 subplot chart as a PNG file.

**Time estimate:** 30 minutes

**Prerequisite:** A free FRED API key from https://fred.stlouisfed.org/api/. Store it as
`FRED_API_KEY` in your environment. Read it at startup and raise `ValueError` with a helpful
message if it is missing.

---

### What to implement

**Step 1 — Define the fetch function.** Write a function `fetch_series(series_id, name)` that
makes a GET request to `https://api.stlouisfed.org/fred/series/observations`. Pass four query
parameters: `series_id`, `observation_start` (5 years ago from today, formatted as `YYYY-MM-DD`
using `datetime.date.today() - timedelta(days=365*5)`), `api_key`, and `file_type="json"`. Parse
the `"observations"` list from the JSON response. Each observation is a dict with `"date"` and
`"value"` keys. Skip any observations where `value == "."` — FRED uses a period for missing data.
Build a `pd.Series` mapping date strings to float values, set the name to the `name` parameter,
convert the index to `pd.to_datetime`, and return it. Print the series name, series ID, number of
observations, and the most recent value.

**Step 2 — Fetch four series.** Call `fetch_series` for:
- `"FEDFUNDS"` — Federal Funds Rate (monthly percentage)
- `"GS10"` — 10-Year Treasury Constant Maturity Rate (daily percentage)
- `"CPIAUCSL"` — Consumer Price Index for All Urban Consumers (monthly index level)
- `"VIXCLS"` — CBOE Volatility Index (daily)

**Step 3 — Print summary.** Combine the Federal Funds Rate and 10-Year Treasury into a DataFrame
using `pd.DataFrame({...})`. Call `.dropna()` to align the monthly/daily frequency difference.
Print the last 6 rows rounded to 2 decimal places.

**Step 4 — Plot.** Create a 2×2 matplotlib subplot figure with `figsize=(14, 8)` and a centered
super-title. Write a helper function `plot_series(ax, series, title, color, ylabel)` that plots
the series as a line, sets the title, y-axis label, and x-axis date format to 4-digit years using
`mdates.DateFormatter("%Y")`, enables a light grid, and adds an annotation in the top-right corner
showing the latest value. Call this helper for each of the four series using distinct colors.
Call `plt.tight_layout()`, save to `exercises/ex12_fred_macro.png` at 100 DPI, and close the
figure.

**Step 5 — Document the feature vector.** Print a list of how these four indicators appear in
MarketPulse's ML feature vector: `fed_funds_rate` (normalized z-score), `t10_yield` (yield curve
signal), `vix_level` (market fear level), and `yield_curve_spread` (`GS10 - GS2`, a recession
predictor — negative spread historically precedes recessions).

**Documentation:**
- FRED API documentation: https://fred.stlouisfed.org/docs/api/fred/
- FRED series observations endpoint: https://fred.stlouisfed.org/docs/api/fred/series_observations.html
- Series IDs reference: https://fred.stlouisfed.org/categories
- matplotlib subplots: https://matplotlib.org/stable/gallery/subplots_axes_and_figures/subplots_demo.html
- matplotlib dates: https://matplotlib.org/stable/api/dates_api.html

---

### Expected output

```
Fetching FRED macro indicators (5-year history)...

  Federal Funds Rate (FEDFUNDS): 62 observations, latest=5.33%
  10-Year Treasury Yield (GS10): 1254 observations, latest=4.21%
  CPI (Urban Consumers) (CPIAUCSL): 60 observations, latest=314.54
  VIX Volatility Index (VIXCLS): 1255 observations, latest=18.32

Last 6 monthly observations:

            Fed Funds Rate  10Y Treasury
2026-02-01            5.33          4.18
2026-03-01            5.33          4.23
...

Chart saved to: exercises/ex12_fred_macro.png

In MarketPulse's ML feature vector, these macro indicators appear as:
  - fed_funds_rate:     current Fed Funds target rate (normalized z-score per ticker)
  - t10_yield:          10-year Treasury yield (yield curve signal)
  - vix_level:          current VIX (market fear/uncertainty level)
  - yield_curve_spread: GS10 - GS2 (recession predictor; inversion = warning)
```

---

## Exercise 13 — Database Migrations with Alembic

**Lesson it reinforces:** Database migrations (Lesson 4.5)

**What you build:** Initialize Alembic in the MarketPulse project, create a migration that adds a
column to the `tickers` table, apply it, verify the column exists in PostgreSQL with asyncpg, and
roll it back cleanly.

**Time estimate:** 45 minutes

**Prerequisites:** MarketPulse PostgreSQL container running
(`docker compose up -d marketpulse-postgres`). `alembic` and `asyncpg` installed (both are in
the pip install batches).

---

### Step 1 — Initialize Alembic

Run this once from your project root (`C:\marketpulse\MarketPulse\`):

```
alembic init alembic
```

This creates:

```
alembic\
  env.py          ← migration environment (you will edit this)
  script.py.mako  ← template for new revision files
  versions\       ← generated migration scripts go here
alembic.ini       ← config file (you will edit this)
```

---

### Step 2 — Configure `alembic.ini`

Open `alembic.ini`. Find this line:

```
sqlalchemy.url = driver://user:pass@localhost/dbname
```

Replace it with the MarketPulse connection string:

```
sqlalchemy.url = postgresql://marketpulse:marketpulse@localhost:5432/marketpulse_core
```

---

### Step 3 — Stamp the existing schema

Because `001_schema.sql` created the tables outside of Alembic, running a migration would try to
re-create tables that already exist. Stamp the database instead — this registers the current state
as the starting point without touching any tables:

```
alembic stamp head
```

Alembic creates an `alembic_version` table in PostgreSQL and writes an initial revision ID. All
future migrations will chain from this point.

---

### Step 4 — Generate a revision

```
alembic revision -m "add notes column to tickers"
```

Alembic prints the path of the generated file, e.g.:

```
Generating alembic\versions\a3f9b12c_add_notes_column_to_tickers.py
```

Open that file. It contains two empty stubs — `upgrade()` and `downgrade()`. Fill them in using
the `op` and `sa` objects that Alembic imports at the top of the file. `op.add_column` takes the
table name and an `sa.Column(...)` definition. `op.drop_column` takes the table name and the
column name as a string. Add a nullable `TEXT` column named `notes` to the `tickers` table.
The `downgrade()` must be the exact inverse of `upgrade()` — dropping the same column.

---

### Step 5 — Apply, verify, and roll back

Write a script named `ex13_alembic.py` that does the following in order:

1. **Upgrade.** Use `subprocess.run(["alembic", "upgrade", "head"], ...)` and check the return
   code. Print stdout. If the return code is non-zero, print stderr and raise `SystemExit`.

2. **Verify the column was added.** Use asyncpg to connect to the database and query
   `information_schema.columns` where `table_name = 'tickers'` and `column_name = 'notes'`.
   Assert the query returns a row. Print a success message. Use `asyncio.run()` to call the async
   function from the synchronous script.

3. **Print migration history.** Run `alembic history --verbose` via subprocess and print the
   output. This shows every revision in the chain.

4. **Print current revision.** Run `alembic current` via subprocess and print the output.

5. **Downgrade.** Run `alembic downgrade -1` via subprocess (the `-1` means one step back).
   Check the return code the same way as the upgrade step.

6. **Verify the column was removed.** Query `information_schema.columns` again. Assert that the
   query returns NO row this time.

7. Print `✓ Exercise 13 complete — Alembic migration cycle works.`

**Documentation:**
- Alembic tutorial: https://alembic.sqlalchemy.org/en/latest/tutorial.html
- Alembic `op.add_column`: https://alembic.sqlalchemy.org/en/latest/ops.html#alembic.operations.Operations.add_column
- Alembic `op.drop_column`: https://alembic.sqlalchemy.org/en/latest/ops.html#alembic.operations.Operations.drop_column
- SQLAlchemy column types: https://docs.sqlalchemy.org/en/20/core/types.html
- asyncpg `connect`: https://magicstack.github.io/asyncpg/current/api/index.html#asyncpg.connect
- `information_schema.columns`: https://www.postgresql.org/docs/current/infoschema-columns.html

---

### Expected output

```
=== alembic upgrade head ===
INFO  [alembic.runtime.migration] Running upgrade <base> -> a3f9b12c, add notes column to tickers
✓ Column 'notes' exists in tickers

=== alembic history ===
Rev: a3f9b12c (head)
  add notes column to tickers

=== alembic current ===
a3f9b12c (head)

=== alembic downgrade -1 ===
INFO  [alembic.runtime.migration] Running downgrade a3f9b12c -> <base>, add notes column to tickers
✓ Column 'notes' removed from tickers

✓ Exercise 13 complete — Alembic migration cycle works.
```

---

## Exercises Summary

| # | Exercise | Lesson | Key Skill | Est. Time |
|---|----------|--------|-----------|-----------|
| 0 | Environment verification script | 0 | Import checking, subprocess isolation | 20 min |
| 1 | OHLCV + RSI from scratch | 1, 6 | yfinance, Wilder EWM, pandas math | 45 min |
| 2 | News headlines + VADER | 7 | requests, VADER compound score | 30 min |
| 3 | Reddit PRAW sentiment | 8 | PRAW, regex, log-weighted scoring | 30 min |
| 4 | All technical indicators | 9 | ta class-based API, NaN verification | 30 min |
| 5 | Minimal LSTM | 11 | PyTorch Dataset/DataLoader, LSTM | 90 min |
| 6 | gRPC client + server | 11 | protobuf, grpcio, two-process IPC | 60 min |
| 7 | Candlestick chart | 13 | mplfinance, addplot, file size | 45 min |
| 8 | Discord slash command | 13 | discord.py app_commands, embeds | 45 min |
| 9 | TOTP 2FA from scratch | 19 | pyotp, qrcode, replay attack | 40 min |
| 10 | Valkey INCR quota counter | 6 | redis-py async, atomic INCR, TTL | 30 min |
| 11 | SEC EDGAR insider filings | 9 | REST API, rate limiting, User-Agent | 40 min |
| 12 | FRED macro data + plot | 9 | FRED API, matplotlib, pandas | 30 min |
| 13 | Database migrations with Alembic | 4.5 | alembic init/stamp/revision/upgrade/downgrade | 45 min |

**Total exercise time: ~8 hours** (spread across all 26 build phases)
# Account Modal & Authentication Verification - Test Plan

**Document ID:** TP-FE-ACCTMODAL-001  
**Feature:** Phase 2 Stage 2: Persistent Account Icon & Account Modal  
**Target Application:** MarketPulse Web Dashboard (`web_dashboard/src/components/layout/Topbar.tsx`, `AccountModal.tsx`)  
**Role:** Test Engineer  
**Status:** Ready for Execution  

---

## 1. Overview & Objectives

Following the Phase 2 Stage 1 cleanup of the Settings page, user account information (Name, Email, Role) is transitioned into a persistent account component accessible globally from the topbar navigation. 

Per user requirement:
> *"Y. I would like you to make sure that it's actually pulling my account data"*

The primary objectives of this test plan are to verify:
1. **Account Data Retrieval:** Ensure that the application triggers an authenticated call to `/api/api/v1/auth/me` (or configured API proxy endpoint) with the active JWT Bearer token, returning and displaying the user's live email and profile attributes rather than hardcoded mock strings.
2. **Topbar Icon & Modal Interaction:** Verify that clicking the `UserCircle` icon in the Topbar opens the Account Modal/Dropdown, toggles it closed upon re-click, dismisses on backdrop/outside clicks, and closes when pressing the `Escape` key.
3. **Sign Out & JWT Token Flush:** Confirm that executing the "Sign Out" action inside the modal completely flushes the JWT access token from `localStorage`, terminates the authenticated session, closes the modal, and safely redirects the user to the `/login` screen.
4. **Resilience & State Management:** Validate behavior when the token is missing, expired, or corrupted (401 Unauthorized), verifying proper error handling and fallback states.
5. **Theme & Responsive Layout:** Verify visual consistency and readability across Light/Dark modes, mobile, tablet, and desktop viewports.

---

## 2. Test Environment & Prerequisites

- **Frontend URL:** `http://localhost:5173` (or active Vite development server)
- **Backend API Base:** `http://192.168.1.134:8080` (FastAPI backend proxied via `/api`)
- **Authentication Endpoints Under Test:**
  - `POST /api/api/v1/auth/login` (or `/auth/login`) - OAuth2 Token Login
  - `GET /api/api/v1/auth/me` (or `/auth/me`) - Authenticated User Profile
- **Test Credentials:**
  - Standard User: `test@test.com` / `test1234`
  - Secondary User (to verify dynamic email switching): `admin@marketpulse.local` / `securePass123`
- **Required Browser DevTools:**
  - **Network Tab:** Filter by `Fetch/XHR` to inspect headers, request payload, response status, and response bodies for `/auth/me`.
  - **Application/Storage Tab:** Inspect `Local Storage` -> `token` key.
  - **Console Tab:** Monitor for runtime errors, Axios interceptor logs, or unhandled promise rejections.

---

## 3. System Architecture & Data Flow

```
+-------------------------------------------------------------------------+
| Topbar (web_dashboard)                                                  |
|  [Logo] [Overview]                     [Bell] [UserCircle Icon (Click)] |
+-------------------------------------------------------------|-----------+
                                                              |
                                                    Toggles State (isOpen)
                                                              v
+-------------------------------------------------------------------------+
| AccountModal Component                                                  |
|                                                                         |
| 1. On Mount / Open:                                                     |
|    apiClient.get('/auth/me')                                            |
|    Headers: { Authorization: "Bearer <token>" }                         |
|                                                                         |
| 2. Backend (FastAPI router: /auth/me):                                  |
|    Validates JWT -> Returns User schema { id, email, role, is_active }  |
|                                                                         |
| 3. Render:                                                              |
|    - Email: actual user email (e.g. "test@test.com")                   |
|    - Role: "user" or "admin"                                            |
|                                                                         |
| 4. Sign Out Button Clicked:                                             |
|    localStorage.removeItem('token')                                     |
|    Redirect -> /login                                                   |
+-------------------------------------------------------------------------+
```

---

## 4. Test Cases

### TC-ACC-01: UserCircle Icon Rendering & Placement in Topbar
**Objective:** Confirm the `UserCircle` icon replaces or augments the legacy avatar and renders in the top-right navigation area.

- **Preconditions:**
  - User is authenticated and navigating any dashboard page (e.g., `/`, `/settings`, `/paper-trading`).
- **Steps:**
  1. Inspect the right side of the Topbar header.
  2. Locate the user account trigger element.
  3. Verify the presence of the `lucide-react` `UserCircle` (or designated user icon).
  4. Inspect the button attributes:
     - Must have accessible label/aria attributes (`aria-label="User Account"`, `aria-haspopup="dialog"` or `"menu"`).
     - Hover states provide visual feedback (`hover:bg-gray-100`, `dark:hover:bg-gray-700`).
  5. Check layout on viewport widths: Desktop (>=1024px), Tablet (768px - 1023px), and Mobile (<768px).
- **Expected Results:**
  - The icon is clearly visible, vertically centered in the 64px (`h-16`) Topbar.
  - Sizing is balanced with adjacent notification (`Bell`) and navigation icons.
  - Renders cleanly without clipping on mobile screens.

---

### TC-ACC-02: Modal Open/Close Toggle Interactions
**Objective:** Verify that clicking the `UserCircle` icon toggles the account modal and all dismissal mechanisms function properly.

- **Preconditions:**
  - Dashboard is loaded; modal is initially closed (`isOpen === false`).
- **Steps:**
  1. Click the `UserCircle` icon once.
     - Verify the Account Modal opens and appears anchored below the Topbar trigger or centered as a dialog.
  2. Click the `UserCircle` icon a second time.
     - Verify the modal closes immediately.
  3. Click the `UserCircle` icon to re-open the modal.
  4. Click anywhere outside the modal bounds (backdrop or dashboard background).
     - Verify the click-outside handler dismisses the modal.
  5. Click the `UserCircle` icon to open the modal again.
  6. Press the `Escape` key on the keyboard.
     - Verify the modal dismisses immediately.
  7. If an explicit close button (`X`) is provided inside the modal, click it and verify closure.
- **Expected Results:**
  - Modal toggles smoothly without UI jitter or flickering.
  - Dismissal triggers (re-click, outside click, ESC key, close button) reliably update state.
  - Focus returns to the trigger button upon closure for accessibility.

---

### TC-ACC-03: Real Account Data Fetching via `/api/api/v1/auth/me`
**Objective:** Verify that the modal actively queries `/api/api/v1/auth/me` and returns genuine account data for the logged-in user.

- **Preconditions:**
  - User logged in as `test@test.com` with a valid JWT token stored in `localStorage.getItem('token')`.
  - DevTools Network tab is open and recording network log.
- **Steps:**
  1. Click the `UserCircle` icon to trigger modal display.
  2. Inspect the Network tab:
     - Filter for `auth/me` or `/api/api/v1/auth/me`.
     - Verify an HTTP `GET` request was dispatched.
  3. Inspect the Request Headers:
     - Confirm header: `Authorization: Bearer <JWT_TOKEN_STRING>`.
  4. Inspect the Response:
     - Status code: `200 OK`.
     - Payload format:
       ```json
       {
         "id": "...",
         "email": "test@test.com",
         "role": "user",
         "is_active": true,
         "created_at": "...",
         "updated_at": "..."
       }
       ```
  5. Verify the payload email matches the active session (`test@test.com`).
  6. Log out, log in with an alternate account (e.g. `admin@marketpulse.local`), open the modal, and verify the network response returns `admin@marketpulse.local`.
- **Expected Results:**
  - Network request is dispatched with valid Bearer token credentials.
  - Response status is `200 OK`.
  - The email field dynamically reflects the authentic authenticated user rather than hardcoded mock strings (e.g. `"demo@example.com"` or `"Admin"`).

---

### TC-ACC-04: Account Modal UI Data Binding & Presentation
**Objective:** Verify that the data returned from `/auth/me` binds correctly to the modal UI elements.

- **Preconditions:**
  - Modal opened following successful `200 OK` response from `/auth/me`.
- **Steps:**
  1. Inspect the modal content:
     - Verify the Email field displays the exact string returned by the API (`test@test.com`).
     - Verify user Role/Status badge (e.g., "Active", "Role: User" or "Admin").
  2. Test loading state:
     - Simulate a throttled network connection (DevTools "Slow 3G").
     - Click the `UserCircle` icon.
     - Verify a loading skeleton or spinner appears while the `/auth/me` request is in-flight.
  3. Test error state:
     - Block request URL or simulate network failure.
     - Verify graceful error message (e.g., "Unable to load account details") with retry button or sign-out option.
- **Expected Results:**
  - Account information is rendered clearly with proper typography and alignment.
  - No undefined values (e.g., `undefined`, `NaN`, `[object Object]`) appear in the DOM.
  - Loading and error states provide clear, non-blocking user feedback.

---

### TC-ACC-05: Sign Out Execution & JWT Token Flush
**Objective:** Confirm that clicking the "Sign Out" button flushes the JWT token and terminates the session.

- **Preconditions:**
  - User is authenticated with `token` present in `localStorage`.
  - Account Modal is open.
- **Steps:**
  1. Inspect `localStorage` via DevTools Application tab:
     - Confirm `localStorage.getItem('token')` has a valid non-empty JWT string.
  2. Click the **Sign Out** (or **Log Out**) button inside the modal.
  3. Verify storage cleanup:
     - Inspect `localStorage`: Confirm `token` key is completely removed (`null`) or emptied.
  4. Verify application routing:
     - Confirm user is immediately redirected to `/login`.
  5. Verify modal state:
     - Ensure the modal is closed and removed from DOM.
  6. Attempt to navigate back via browser "Back" button:
     - Verify protected routes redirect immediately back to `/login`.
  7. Verify subsequent API calls:
     - Confirm no background requests are sent using the discarded token.
- **Expected Results:**
  - `localStorage.removeItem('token')` is successfully executed.
  - Stored token is completely eliminated.
  - Session is fully terminated and user is redirected to the `/login` route.

---

### TC-ACC-06: Session Expiry & 401 Unauthorized Resilience
**Objective:** Verify application behavior when opening the modal with an invalid, manipulated, or expired token.

- **Preconditions:**
  - User is on the dashboard.
- **Steps:**
  1. In DevTools Application tab, edit `localStorage.getItem('token')` to an invalid string: `"invalid_token_12345"`.
  2. Click the `UserCircle` icon to open the modal.
  3. Observe Network tab:
     - `GET /api/api/v1/auth/me` returns `401 Unauthorized` or `403 Forbidden`.
  4. Verify frontend handling:
     - Interceptor or modal catches the 401 response.
     - Clears the invalid token from `localStorage`.
     - Redirects user to `/login` with an informational message ("Session expired. Please log in again.").
- **Expected Results:**
  - Application does not crash or display an infinite loading state.
  - Expired/invalid tokens are automatically purged and user is prompted to re-authenticate.

---

### TC-ACC-07: Light & Dark Theme Continuity
**Objective:** Ensure the modal and its contents maintain WCAG AA contrast and match the application's design system in both themes.

- **Preconditions:**
  - Navigate to dashboard.
- **Steps:**
  1. Open Account Modal in Light Mode:
     - Inspect background (`bg-white`), borders (`border-gray-200`), primary text (`text-gray-900`), and secondary text (`text-gray-500`).
  2. Toggle Dark Mode ON via Settings or theme context.
  3. Open Account Modal in Dark Mode:
     - Inspect background (`dark:bg-gray-800`), borders (`dark:border-gray-700`), text (`dark:text-white`, `dark:text-gray-300`), and buttons (`hover:bg-gray-700`).
     - Check Sign Out button contrast (e.g., `text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30`).
- **Expected Results:**
  - Full aesthetic parity with the dashboard design system.
  - Contrast ratios pass WCAG AA standards in both themes.

---

## 5. Automated / API Diagnostic Scripts

For rapid regression testing, the following automated scripts verify the backend `/auth/me` contract and token lifecycle.

### Python Backend Verification Script (`test_auth_me.py`)

```python
import asyncio
import httpx

API_BASE = "http://192.168.1.134:8080"

async def test_auth_me_pipeline():
    async with httpx.AsyncClient(base_url=API_BASE) as client:
        # Step 1: Authenticate
        login_res = await client.post(
            "/auth/login",
            data={"username": "test@test.com", "password": "test1234"}
        )
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        token = login_res.json()["access_token"]
        print(f"[PASS] Token acquired: {token[:15]}...")

        # Step 2: Fetch Account Data via /auth/me
        headers = {"Authorization": f"Bearer {token}"}
        me_res = await client.get("/auth/me", headers=headers)
        assert me_res.status_code == 200, f"/auth/me failed: {me_res.text}"
        user_data = me_res.json()
        print(f"[PASS] /auth/me returned data: {user_data}")
        
        # Step 3: Validate Specific User Email
        assert user_data.get("email") == "test@test.com", "Email mismatch!"
        assert "id" in user_data, "Missing user ID"
        print(f"[PASS] Verified user email matches: {user_data['email']}")

        # Step 4: Validate Unauthorized Request Without Token
        unauth_res = await client.get("/auth/me")
        assert unauth_res.status_code == 401, f"Expected 401, got {unauth_res.status_code}"
        print("[PASS] Unauthenticated access properly rejected (401)")

if __name__ == "__main__":
    asyncio.run(test_auth_me_pipeline())
```

---

## 6. Verification Checklist

| Check ID | Verification Item | Target Standard | Status | Notes |
| :--- | :--- | :--- | :---: | :--- |
| **CHK-ACC-01** | `UserCircle` Topbar Icon | Rendered in top-right with accessible attributes | [ ] | Replaces/supplements static Admin text |
| **CHK-ACC-02** | Modal Toggle Open/Close | Opens on click, closes on re-click | [ ] | Smooth transition, no layout shift |
| **CHK-ACC-03** | Modal Dismissal Triggers | Closes on outside click, close button, and `Escape` key | [ ] | Focus restored to trigger |
| **CHK-ACC-04** | `/auth/me` API Invocation | Dispatches GET with `Authorization: Bearer <token>` | [ ] | Verify via DevTools Network tab |
| **CHK-ACC-05** | Real Email Binding | Displays live authenticated email (e.g. `test@test.com`) | [ ] | Zero mock/hardcoded email strings |
| **CHK-ACC-06** | Sign Out Token Flush | `localStorage.removeItem('token')` called | [ ] | `token` key is cleared immediately |
| **CHK-ACC-07** | Post-Signout Navigation | User redirected to `/login`; back button protected | [ ] | Session terminated completely |
| **CHK-ACC-08** | 401 Session Expiry | Invalid/expired token purges storage and redirects | [ ] | Graceful degradation, no crashes |
| **CHK-ACC-09** | Dark/Light Mode Styling | Theme classes applied, contrast WCAG AA compliant | [ ] | Tested on both light and dark |
| **CHK-ACC-10** | Mobile Responsiveness | Dropdown/modal adapts to viewports < 768px | [ ] | No horizontal overflow or clipping |

---

## 7. Sign-Off Criteria

Phase 2 Stage 2 Account Modal implementation is certified for production release when:
1. All checklist items (**CHK-ACC-01** through **CHK-ACC-10**) are marked as **PASSED**.
2. DevTools Network inspection confirms `/auth/me` returns `200 OK` with the exact email of the signed-in user.
3. Clicking **Sign Out** reliably clears the JWT token from `localStorage` and routes to `/login`.
4. Zero unhandled console exceptions or visual regressions are present across Chrome, Firefox, Edge, and mobile viewports.
# Dark Mode Toggle - Manual Verification Test Plan

**Document ID:** TP-FE-DARKMODE-001
**Feature:** Phase 1 Stage 2: Dark Mode Toggle
**Target Application:** MarketPulse Web Dashboard (`web_dashboard`)
**Role:** Test Engineer
**Status:** Ready for Execution

---

## 1. Overview & Objectives

This test plan outlines manual verification procedures for the dark mode toggle feature in the MarketPulse Web Dashboard. The primary objectives are to verify:
1. **Toggle Switch UI State & Accessibility:** Correct visual indicators, knob translation, and ARIA state transitions.
2. **Theme Application & Text Color Contrast:** Accurate application of Tailwind `dark` class to the document root, ensuring proper contrast and readability across text, headings, backgrounds, cards, and navigation elements.
3. **`localStorage` Persistence:** Reliable persistence of the theme setting across hard page reloads, cross-route navigation, and new browser tabs/sessions.
4. **Responsive / Viewport Compatibility:** Consistent behavior and visual integrity on desktop, tablet, and mobile viewports.

---

## 2. Test Environment & Prerequisites

- **URL:** `http://localhost:5173` (or configured dev/staging server)
- **Browsers Tested:** Chromium-based (Chrome/Edge), Firefox, Safari (or mobile emulation)
- **DevTools Open:** Console (to monitor errors) and Application/Storage tab (to inspect `localStorage` and DOM `<html>` element).
- **Authentication:** User logged in and able to access `/settings`.

---

## 3. Test Cases

### TC-DM-01: Toggle Switch Visual & ARIA State Verification
**Objective:** Confirm that the switch component in Settings reflects its toggled state visually and accessibly.

- **Preconditions:**
  - Navigate to `/settings`.
  - Initial theme is Light Mode.
- **Steps:**
  1. Inspect the toggle switch element located in the **Preferences > Dark Theme** section.
  2. Verify initial attributes:
     - Outer button background color is light gray (e.g. `bg-gray-200`).
     - Inner knob slider is positioned at origin (`translate-x-0`).
     - Accessibility attribute is `aria-checked="false"`.
  3. Click or tap the toggle switch.
  4. Observe the toggle switch animation and state change.
  5. Inspect attributes post-click:
     - Outer button background changes to active theme accent (e.g. `bg-blue-600` or `bg-indigo-600`).
     - Inner knob slider translates to the right (e.g. `translate-x-5`).
     - Accessibility attribute updates to `aria-checked="true"`.
  6. Click the toggle switch a second time to revert back to Light Mode.
- **Expected Results:**
  - Switch smoothly toggles between states without visual artifacts or delay.
  - `aria-checked` accurately reflects `"true"` when enabled and `"false"` when disabled.
  - Knob slides left/right smoothly with appropriate CSS transition timing.

---

### TC-DM-02: Text Colors, Backgrounds, and Visual Hierarchy
**Objective:** Verify that text, card surfaces, and UI elements adapt with proper contrast and readability in dark mode.

- **Preconditions:**
  - User is on `/settings`.
- **Steps:**
  1. Toggle Dark Mode to **ON**.
  2. Verify root element:
     - Ensure `<html class="dark">` has the `dark` class applied.
  3. Check text elements on the Settings page:
     - Primary page title ("Settings") switches from dark text (`text-gray-900` / `text-gray-800`) to light text (e.g. `text-white` / `text-gray-100`).
     - Section headings ("ML Trading Configuration", "User Profile", "Preferences") are clearly legible with light text.
     - Secondary/subtext descriptions (e.g. "Toggle dark mode for the dashboard.") change from `text-gray-500` to a legible subdued shade (e.g. `text-gray-400`).
  4. Check card containers and surfaces:
     - White card panels (`bg-white`) switch to dark theme background surfaces (e.g. `dark:bg-gray-800` or `dark:bg-slate-900`).
     - Card borders and divider lines switch to appropriate dark contrast tones (e.g. `dark:border-gray-700`).
  5. Check input fields and sliders:
     - Text inputs, sliders, and strategy selection cards remain distinct, legible, and usable.
     - Input text inside form fields remains clearly readable against input backgrounds.
  6. Navigate to other pages (e.g. `/`, `/paper-trading`, `/sentiment`, `/admin`):
     - Ensure topbar, sidebar, charts, and metrics cards correctly render light-on-dark styles.
     - Verify no unstyled "flash of white" or illegible dark-on-dark text occurs.
- **Expected Results:**
  - All text meets WCAG AA contrast ratios (minimum 4.5:1 for normal text).
  - No black text on dark background or white text on white background.
  - Theme changes apply immediately across all visible components without requiring a refresh.

---

### TC-DM-03: `localStorage` Persistence & Page Reload
**Objective:** Ensure that the user's theme selection persists across reloads and navigation.

- **Preconditions:**
  - User is on `/settings`.
  - Browser DevTools is open to **Application > Local Storage** (or **Storage > Local Storage**).
- **Steps:**
  1. Clear any existing `theme` key in `localStorage` or verify default state.
  2. Toggle Dark Mode to **ON**.
  3. Inspect `localStorage`:
     - Verify a key (e.g., `theme`) is stored with value `"dark"`.
  4. Perform a standard browser reload (`F5` or `Ctrl+R` / `Cmd+R`).
  5. Observe the initial page render:
     - Confirm the page reloads directly in Dark Mode without a flash of Light Mode (FOUC).
     - Confirm `<html class="dark">` retains the `dark` class.
     - Confirm the toggle button in `/settings` remains in the active ("true") state.
  6. Perform a hard refresh (`Ctrl+F5` or `Ctrl+Shift+R` / `Cmd+Shift+R`).
  7. Confirm dark mode remains active and all states hold.
  8. Navigate to a different route (e.g., `/`, `/paper-trading`) and back to `/settings`.
  9. Confirm the theme persists across client-side router transitions.
  10. Toggle Dark Mode to **OFF**.
  11. Check `localStorage`:
      - Verify key value updates to `"light"` (or is removed, per implementation).
  12. Reload the page and verify Light Mode persists.
- **Expected Results:**
  - Theme preference is immediately synchronized with `localStorage`.
  - Reloading the page respects the stored preference with zero theme flicker.
  - Router transitions preserve the active theme across the entire session.

---

### TC-DM-04: Multi-Tab & Session Continuity
**Objective:** Verify theme synchronization across browser tabs and fresh sessions.

- **Preconditions:**
  - Browser session active in Tab 1.
- **Steps:**
  1. In Tab 1, set theme to **Dark Mode**.
  2. Open a new browser tab (Tab 2) and navigate to `http://localhost:5173/settings`.
  3. Check the theme in Tab 2 upon initial load.
  4. In Tab 2, toggle Dark Mode to **OFF**.
  5. Switch back to Tab 1 and reload (or observe if cross-tab `storage` event listener is implemented).
- **Expected Results:**
  - New tabs open directly in the user's saved theme.
  - `localStorage` value is consistently read upon startup.

---

### TC-DM-05: Responsive & Mobile Viewport Verification
**Objective:** Confirm that the dark mode toggle and dark theme work seamlessly on mobile and small viewport screens.

- **Preconditions:**
  - DevTools device toolbar active (e.g., iPhone 12/14, Pixel 7, or custom 375px width).
- **Steps:**
  1. Open `/settings` on mobile viewport.
  2. Locate the Dark Theme toggle under Preferences.
  3. Ensure the toggle switch is fully visible, not cut off or overlapping surrounding elements.
  4. Tap the toggle switch to activate Dark Mode.
  5. Verify touch responsiveness (touch targets ≥ 44x44px or easily tappable).
  6. Open the mobile navigation drawer / hamburger menu.
  7. Check drawer background, icons, text, and active state styles in Dark Mode.
  8. Close drawer and scroll through Settings page to check for clipping, horizontal scrollbars, or styling glitches.
- **Expected Results:**
  - Mobile layout remains fully responsive and aligned.
  - Toggle switch responds promptly to touch/click interactions.
  - Mobile drawer and overlays respect the dark theme palette.

---

### TC-DM-06: Edge Cases & Error Resilience
**Objective:** Validate graceful degradation and fallback behavior.

- **Preconditions:**
  - Application loaded.
- **Steps:**
  1. **Corrupted/Invalid Storage:** Open DevTools console and set `localStorage.setItem('theme', 'invalid_value')`. Reload the page. Verify the app falls back safely to default (Light or System preference) without throwing runtime exceptions.
  2. **Rapid Toggling:** Click the toggle switch 10 times in rapid succession. Verify no race conditions occur, switch state matches DOM class, and `localStorage` retains the final state.
  3. **No Storage Available:** Simulate private browsing / blocked storage (if applicable). Verify the toggle still operates in-memory for the current session without crashing.
- **Expected Results:**
  - No unhandled exceptions in browser console.
  - App degrades gracefully to default theme upon unexpected storage values.

---

## 4. Verification Checklist & Sign-Off Criteria

| Criterion | Requirement | Verified (Y/N) |
| :--- | :--- | :---: |
| **Switch UI State** | Toggle background and knob change state accurately with smooth transition | [ ] |
| **Accessibility** | `role="switch"` and `aria-checked` accurately reflect active state | [ ] |
| **DOM Class** | `dark` class added to / removed from `document.documentElement` (`<html class="dark">`) | [ ] |
| **Text Contrast** | All text, headings, and descriptions remain legible (WCAG AA) | [ ] |
| **Surface Contrast** | Cards, inputs, modals, and navigation panels display appropriate dark backgrounds | [ ] |
| **Persistence** | Selection saved to `localStorage` and persists across soft and hard reloads | [ ] |
| **Routing** | Theme remains consistent during SPA client navigation | [ ] |
| **Mobile UX** | Layout, drawer, and touch targets work without visual breakage on mobile | [ ] |
| **Console Cleanliness** | Zero console errors or unhandled warnings during theme changes | [ ] |
# Global Topbar Theme Toggle & Settings Cleanup - Verification Test Plan

**Document ID:** TP-FE-GLOBALTHEME-001  
**Feature:** Phase 2 Stage 3: Global Dark Mode Switch  
**Target Application:** MarketPulse Web Dashboard (`web_dashboard`)  
**Components Under Test:** 
- `web_dashboard/src/components/layout/Topbar.tsx` (Global Theme Toggle)
- `web_dashboard/src/pages/Settings.tsx` (Legacy Preferences / Toggle Removal)
- `web_dashboard/src/ThemeContext.tsx` (Theme Provider & State Hook)
**Role:** Test Engineer  
**Status:** Ready for Execution  

---

## 1. Overview & Objectives

In Phase 2 Stage 3, the dark mode toggle is elevated from the localized Settings page into the global Topbar navigation header, positioned directly adjacent to the Account icon (`UserCircle`). Concurrently, the legacy "Preferences" section (containing the redundant dark theme toggle switch) is cleanly excised from `Settings.tsx`.

This test plan defines the end-to-end verification procedures to ensure:
1. **Instant Root Class Application:** Toggling the theme from the Topbar immediately adds or removes the `dark` class on the HTML document root (`<html class="dark">` / `document.documentElement.classList`) without delay, animation lag, or requiring a page reload.
2. **Settings Page Cleanup:** The `Settings.tsx` view no longer contains the old "Preferences" card, "Dark Theme" label, description text, or switch button, while all ML Trading Configuration controls remain fully functional.
3. **Global Accessibility & Persistence:** The theme toggle is accessible from any route via the persistent Topbar, and the user's preference is reliably stored in `localStorage` (`theme: 'dark' | 'light'`) and respected across client-side route transitions and browser hard reloads.
4. **Visual Hierarchy & Accessibility:** The toggle button integrates seamlessly into the Topbar layout across desktop, tablet, and mobile viewports with proper ARIA attributes, keyboard navigation, and WCAG AA contrast compliance.

---

## 2. Test Environment & Prerequisites

- **Frontend URL:** `http://localhost:5173` (or active Vite development server port)
- **Supported Browsers:** Chromium-based (Google Chrome, Microsoft Edge, Brave), Mozilla Firefox, WebKit (Apple Safari)
- **Screen Viewports:**
  - Desktop: 1440x900px, 1280x800px
  - Tablet: 768x1024px (iPad portrait / landscape)
  - Mobile: 375x812px (iPhone X/13), 390x844px (Pixel / Galaxy)
- **DevTools Open:**
  - **Elements / Inspector:** Monitor `<html class="...">` tag mutations in real time.
  - **Console Tab:** Verify absence of React warnings, syntax errors, or null reference errors.
  - **Application / Storage Tab:** Monitor `localStorage` key `theme`.
- **Prerequisites:** User is logged in with valid JWT token in `localStorage` (`token`) so that authenticated dashboard layouts and `Topbar` render.

---

## 3. System Architecture & State Flow

```
+---------------------------------------------------------------------------------------+
| Topbar.tsx                                                                            |
|  [Logo / Overview]              [ThemeToggle Button (Sun/Moon)]  [Bell]  [UserCircle] |
+---------------------------------------------------|-----------------------------------+
                                                    |
                                          onClick: toggleTheme()
                                                    |
                                                    v
+---------------------------------------------------------------------------------------+
| ThemeContext.tsx (useTheme Hook)                                                      |
|                                                                                       |
|  setIsDark(prev => !prev)                                                             |
|                                                                                       |
|  useEffect Trigger:                                                                   |
|    if (isDark) {                                                                      |
|      document.documentElement.classList.add('dark');                                  |
|      localStorage.setItem('theme', 'dark');                                           |
|    } else {                                                                           |
|      document.documentElement.classList.remove('dark');                               |
|      localStorage.setItem('theme', 'light');                                          |
|    }                                                                                  |
+---------------------------------------------------|-----------------------------------+
                                                    |
                         +--------------------------+--------------------------+
                         |                                                     |
                         v                                                     v
+-----------------------------------------------+     +---------------------------------+
| DOM Document Root                             |     | localStorage                    |
| <html class="dark"> (Instant Tailwind cascade)|     | key: "theme", value: "dark"     |
+-----------------------------------------------+     +---------------------------------+
```

### Settings Page Before vs. After (Phase 2 Stage 3)

```
BEFORE:
+-------------------------------------------------------+
| Settings.tsx                                          |
|  - [Card 1] ML Trading Configuration                  |
|  - [Card 2] Preferences (Dark Theme switch) <-- REMOVE|
+-------------------------------------------------------+

AFTER:
+-------------------------------------------------------+
| Settings.tsx                                          |
|  - [Card 1] ML Trading Configuration (Sole focus)     |
+-------------------------------------------------------+
```

---

## 4. Test Cases

### TC-GT-01: Global Topbar Theme Toggle Placement & Icon Rendering
**Objective:** Verify that the theme toggle button renders in the Topbar, adjacent to the Account icon, with proper visual indicators.

- **Preconditions:**
  - User logged in and navigating on any dashboard route (e.g. `/`, `/settings`, `/paper-trading`).
- **Steps:**
  1. Inspect the right side of the Topbar.
  2. Verify the layout order of navigation items in the top-right flex cluster:
     - Notification icon (`Bell`)
     - Theme Toggle button (Moon `Lucide` icon when in Light mode / Sun `Lucide` icon when in Dark mode)
     - User Account container (`UserCircle` + "Admin" badge)
  3. Inspect the toggle button element:
     - Button has accessible attributes: `aria-label="Toggle theme"` or `aria-label="Switch to dark mode"` / `"Switch to light mode"`.
     - Styling conforms to Topbar icon buttons (`p-2`, rounded hover effects `hover:bg-gray-100 dark:hover:bg-gray-700`).
  4. Hover over the button and observe feedback states.
- **Expected Results:**
  - The toggle button is clearly visible, vertically aligned within the 64px (`h-16`) Topbar.
  - Sizing is harmonious with adjacent icons (20px icon size, consistent padding).
  - Hover state provides smooth visual feedback with no layout shift.

---

### TC-GT-02: Instant Application of `dark` Class to Document Root (`<html>`)
**Objective:** Confirm that clicking the Topbar theme toggle immediately adds `dark` to `<html class="...">` without page refresh or latency.

- **Preconditions:**
  - Application is initially in **Light Mode** (`<html class="">` or `<html>` without `dark` class).
  - DevTools **Elements** panel open, focused on the `<html>` root tag.
- **Steps:**
  1. Observe the current class attribute of `document.documentElement`:
     ```js
     document.documentElement.classList.contains('dark'); // returns false
     ```
  2. Click the Topbar theme toggle button once.
  3. Immediately observe the `<html>` tag in DevTools Elements and evaluate via console:
     ```js
     document.documentElement.classList.contains('dark'); // must return true
     ```
  4. Verify the visual styling instantaneously transitions:
     - Topbar background transitions to `dark:bg-gray-800` and border to `dark:border-gray-700`.
     - Sidebar background transitions to `dark:bg-gray-800`.
     - Main layout background transitions to `dark:bg-gray-900` with text `dark:text-gray-100`.
     - Current page content (cards, tables, buttons) applies Tailwind dark styles.
  5. Click the Topbar theme toggle button a second time.
  6. Immediately observe the `<html>` tag:
     ```js
     document.documentElement.classList.contains('dark'); // must return false
     ```
  7. Verify all surfaces immediately revert to Light Mode styles (`bg-white`, `bg-gray-50`, `text-gray-800`).
- **Expected Results:**
  - The `dark` class is appended/removed synchronously with the state change.
  - Latency is under 16ms (within 1 browser frame).
  - Zero full-page reload or route re-mounting occurs.
  - No flickering or unstyled elements appear.

---

### TC-GT-03: Complete Removal of Old Toggle from `Settings.tsx`
**Objective:** Verify that the old Preferences card and dark mode toggle switch are completely eliminated from `Settings.tsx`.

- **Preconditions:**
  - Navigate to `/settings`.
- **Steps:**
  1. Visually review the entire Settings page layout from top to bottom.
  2. Verify that only the "ML Trading Configuration" card renders beneath the "Settings" page header.
  3. Inspect DOM elements:
     - Search DOM for heading text matching `"Preferences"`:
       ```js
       Array.from(document.querySelectorAll('h2, h3')).some(el => el.textContent?.includes('Preferences')); // must be false
       ```
     - Search DOM for label text matching `"Dark Theme"`:
       ```js
       Array.from(document.querySelectorAll('*')).some(el => el.textContent === 'Dark Theme'); // must be false
       ```
     - Search DOM for description text `"Toggle dark mode for the dashboard."`:
       ```js
       Array.from(document.querySelectorAll('*')).some(el => el.textContent?.includes('Toggle dark mode for the dashboard')); // must be false
       ```
     - Search DOM for role switch buttons:
       ```js
       document.querySelectorAll('button[role="switch"]').length; // must be 0
       ```
  4. Verify that `useTheme` is no longer imported or called unnecessarily inside `Settings.tsx` (unless explicitly needed for other settings).
  5. Check ML Trading Configuration functionality:
     - Click each strategy card (Zero-Loss Random Forest, Social Sentiment Scalper, Options Flow StatArb, Omni-Fusion Ensemble).
     - Move the Confidence Threshold slider.
     - Click "Save Configuration".
- **Expected Results:**
  - Zero remnant traces of the Preferences section or old theme switch in `Settings.tsx`.
  - No orphaned styling or blank whitespace containers at the bottom of `/settings`.
  - ML Trading Configuration operates without errors or console warnings.

---

### TC-GT-04: `localStorage` Synchronization & Page Reload Persistence
**Objective:** Verify that the theme setting persists in browser storage and initializes with zero Flash of Unstyled Content (FOUC).

- **Preconditions:**
  - User is on any page with DevTools **Application > Local Storage** open.
- **Steps:**
  1. In the console, execute `localStorage.clear()` or verify existing `theme` key.
  2. Click the Topbar theme toggle to activate **Dark Mode**.
  3. Inspect `localStorage`:
     - Key `theme` must equal `"dark"`.
  4. Perform a standard browser reload (`F5` or `Ctrl+R` / `Cmd+R`).
  5. Inspect the initial render:
     - Document root must immediately mount with `<html class="dark">`.
     - Page renders dark styling instantly with no light-mode flicker.
     - Topbar toggle icon displays the Sun icon (indicating active dark mode).
  6. Perform a hard reload (`Ctrl+Shift+R` / `Cmd+Shift+R`).
  7. Verify `<html class="dark">` and dark theme styling persist.
  8. Click the Topbar theme toggle to activate **Light Mode**.
  9. Inspect `localStorage`:
     - Key `theme` must equal `"light"`.
  10. Reload the page; verify Light Mode persists with zero flicker.
- **Expected Results:**
  - `localStorage` accurately tracks the active theme at all times.
  - Page reload immediately re-hydrates the saved theme without visual flashes.

---

### TC-GT-05: Cross-Route Navigation Consistency
**Objective:** Confirm that the active theme remains stable while navigating across different dashboard routes.

- **Preconditions:**
  - User is on Dashboard (`/`).
- **Steps:**
  1. Toggle theme to **Dark Mode** via the Topbar toggle.
  2. Using the Sidebar navigation, sequentially visit each route:
     - `/paper-trading`
     - `/settings`
     - `/admin`
     - `/sentiment`
     - `/macro`
     - `/analytics`
     - `/why`
  3. On each page, verify:
     - `<html class="dark">` remains present on the root.
     - The page body, cards, tables, charts, and text render with dark mode colors.
     - The Topbar toggle remains in the Sun (Dark Mode active) state.
  4. While on `/settings`, click the Topbar toggle to switch back to **Light Mode**.
  5. Verify `/settings` instantly switches to light mode.
  6. Navigate back to `/` and `/paper-trading`.
  7. Verify all pages remain in Light Mode.
- **Expected Results:**
  - Route changes preserve the active theme without resetting or glitching.
  - Topbar remains globally mounted and synchronized across client-side transitions.

---

### TC-GT-06: Accessibility, Keyboard Interaction, & Contrast
**Objective:** Ensure the Topbar toggle meets WCAG AA accessibility standards.

- **Preconditions:**
  - Navigate to any dashboard page.
- **Steps:**
  1. Use the `Tab` key on the keyboard to navigate through the Topbar controls.
  2. Verify that focus reaches the Theme Toggle button.
  3. Inspect visual focus indicator:
     - Must show clear focus ring (e.g. `focus:outline-none focus:ring-2 focus:ring-indigo-500` or `focus:ring-blue-500`).
  4. Press `Enter` or `Space`:
     - Theme must toggle instantly.
     - Focus must remain on the toggle button.
  5. Inspect screen reader accessibility:
     - Button must have an informative `aria-label` describing the action (e.g. `"Switch to dark mode"` / `"Switch to light mode"`).
  6. Perform contrast checks on text and icons against the Topbar background in both light (`#ffffff`) and dark (`#1f2937`) modes:
     - Text/icon contrast must be >= 4.5:1.
- **Expected Results:**
  - Full keyboard accessibility without requiring mouse input.
  - Clear focus indicator visible in both modes.
  - Screen reader accessible with accurate dynamic labels.

---

### TC-GT-07: Responsive & Mobile Viewport Compatibility
**Objective:** Verify that the Topbar theme toggle renders cleanly and operates responsively on mobile and tablet screens.

- **Preconditions:**
  - Open DevTools Device Mode (e.g. 375px width, iPhone SE / 13).
- **Steps:**
  1. Inspect the mobile Topbar layout:
     - Left: Hamburger menu button (`Menu`).
     - Right: Flex cluster containing Notification (`Bell`), Theme Toggle, and Account button (`UserCircle`).
  2. Verify that the Theme Toggle button remains visible, fully tappable, and is not hidden or obscured by text or borders.
  3. Tap the Theme Toggle button:
     - Verify instant touch response with minimal tap target of 40x40px (or padded 44x44px target area).
     - Theme toggles instantly to Dark Mode.
  4. Open the mobile sidebar drawer (`Menu` click):
     - Drawer renders dark background (`dark:bg-gray-800`) and dark theme navigation links.
  5. Close drawer and rotate screen to landscape (e.g. 667px / 844px width):
     - Ensure no layout wrapping, overlapping icons, or horizontal scrolling occurs.
- **Expected Results:**
  - Topbar items fit neatly without collision on screens down to 360px width.
  - Mobile touch target is responsive and easy to tap.

---

## 5. Automated / Console Verification Scripts

### Script 1: Browser DevTools Console Automated Test Runner
Run this snippet directly in the browser DevTools console on `http://localhost:5173/settings` to automatically validate DOM root class manipulation, `localStorage` synchronization, and absence of legacy toggle in Settings:

```javascript
(async function runGlobalThemeVerification() {
  console.group('%c[MarketPulse Test Suite] Phase 2 Stage 3: Global Theme Verification', 'color: #3b82f6; font-weight: bold; font-size: 14px;');
  
  const results = [];
  const assert = (name, condition, detail = '') => {
    const passed = Boolean(condition);
    results.push({ test: name, passed, detail });
    if (passed) {
      console.log(`%c[PASS]%c ${name}`, 'color: #10b981; font-weight: bold;', 'color: inherit;');
    } else {
      console.error(`%c[FAIL]%c ${name} - ${detail}`, 'color: #ef4444; font-weight: bold;', 'color: inherit;');
    }
  };

  // 1. Check Settings Page Cleanup
  const isSettingsPage = window.location.pathname.includes('/settings');
  if (isSettingsPage) {
    const prefHeaders = Array.from(document.querySelectorAll('h2, h3')).filter(el => el.textContent?.trim() === 'Preferences');
    assert('Settings: Preferences heading removed', prefHeaders.length === 0, `Found ${prefHeaders.length} elements`);

    const darkThemeLabels = Array.from(document.querySelectorAll('*')).filter(el => el.children.length === 0 && el.textContent?.trim() === 'Dark Theme');
    assert('Settings: "Dark Theme" label removed', darkThemeLabels.length === 0, `Found ${darkThemeLabels.length} elements`);

    const oldSwitches = document.querySelectorAll('.p-6 button[role="switch"]');
    assert('Settings: Old switch button removed', oldSwitches.length === 0, `Found ${oldSwitches.length} switch buttons`);

    const mlConfig = Array.from(document.querySelectorAll('h2')).some(el => el.textContent?.includes('ML Trading Configuration'));
    assert('Settings: ML Trading Configuration preserved', mlConfig, 'ML Trading Configuration card missing');
  } else {
    console.warn('Navigate to /settings to execute Settings cleanup assertions.');
  }

  // 2. Check Topbar Theme Toggle Button Existence
  const themeButtons = Array.from(document.querySelectorAll('header button, div[class*="h-16"] button')).filter(btn => {
    const aria = btn.getAttribute('aria-label') || '';
    const html = btn.innerHTML;
    return aria.toLowerCase().includes('theme') || html.includes('lucide-sun') || html.includes('lucide-moon') || btn.title?.toLowerCase().includes('theme');
  });
  assert('Topbar: Global theme toggle button present', themeButtons.length >= 1, `Found ${themeButtons.length} candidate buttons`);

  // 3. Root Class & LocalStorage Mutation Test
  const initialTheme = localStorage.getItem('theme') || 'light';
  const initialHasDark = document.documentElement.classList.contains('dark');
  
  // Test Toggle Action
  const toggleBtn = themeButtons[0];
  if (toggleBtn) {
    toggleBtn.click();
    await new Promise(r => setTimeout(r, 50)); // Allow microtask/render cycle
    const toggledHasDark = document.documentElement.classList.contains('dark');
    const toggledStorage = localStorage.getItem('theme');
    
    assert('Toggle: Root dark class flipped', toggledHasDark !== initialHasDark, `Previous: ${initialHasDark}, Now: ${toggledHasDark}`);
    assert('Toggle: localStorage updated', toggledStorage !== initialTheme, `Storage: ${toggledStorage}`);

    // Revert toggle
    toggleBtn.click();
    await new Promise(r => setTimeout(r, 50));
    const restoredHasDark = document.documentElement.classList.contains('dark');
    assert('Toggle: State restored on second click', restoredHasDark === initialHasDark, `Restored to: ${restoredHasDark}`);
  } else {
    assert('Toggle execution', false, 'Toggle button not found to simulate click');
  }

  console.table(results);
  console.groupEnd();
})();
```

---

### Script 2: Vitest / React Testing Library Unit Test Specification
Create or reference unit test specifications for `Topbar.test.tsx` and `Settings.test.tsx`:

```tsx
// web_dashboard/src/components/layout/__tests__/Topbar.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Topbar } from '../Topbar';
import { ThemeProvider } from '../../../ThemeContext';

describe('Topbar Global Theme Toggle', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.className = '';
  });

  it('renders the theme toggle button next to account controls', () => {
    render(
      <ThemeProvider>
        <Topbar />
      </ThemeProvider>
    );
    const themeBtn = screen.getByRole('button', { name: /theme|mode/i });
    expect(themeBtn).toBeInTheDocument();
  });

  it('instantly toggles dark class on document.documentElement upon click', () => {
    render(
      <ThemeProvider>
        <Topbar />
      </ThemeProvider>
    );
    const themeBtn = screen.getByRole('button', { name: /theme|mode/i });

    expect(document.documentElement.classList.contains('dark')).toBe(false);

    fireEvent.click(themeBtn);
    expect(document.documentElement.classList.contains('dark')).toBe(true);
    expect(localStorage.getItem('theme')).toBe('dark');

    fireEvent.click(themeBtn);
    expect(document.documentElement.classList.contains('dark')).toBe(false);
    expect(localStorage.getItem('theme')).toBe('light');
  });
});
```

```tsx
// web_dashboard/src/pages/__tests__/Settings.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Settings } from '../Settings';
import { ThemeProvider } from '../../ThemeContext';

describe('Settings Page Legacy Toggle Removal', () => {
  it('renders ML Trading Configuration but does NOT render Preferences or Dark Theme toggle', () => {
    render(
      <ThemeProvider>
        <Settings />
      </ThemeProvider>
    );

    // Verify ML Trading Configuration is intact
    expect(screen.getByText('ML Trading Configuration')).toBeInTheDocument();

    // Verify Preferences and Dark Theme sections are absent
    expect(screen.queryByText('Preferences')).not.toBeInTheDocument();
    expect(screen.queryByText('Dark Theme')).not.toBeInTheDocument();
    expect(screen.queryByText('Toggle dark mode for the dashboard.')).not.toBeInTheDocument();
    expect(screen.queryByRole('switch')).not.toBeInTheDocument();
  });
});
```

---

## 6. Verification Matrix & Checklist

| Check ID | Verification Item | Target Component | Expected Result | Status | Notes |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **CHK-GT-01** | Topbar Theme Button Rendering | `Topbar.tsx` | Button renders in Topbar header adjacent to Account icon (`UserCircle`) | [ ] | Check icon presence and alignment |
| **CHK-GT-02** | Topbar Dynamic Icon State | `Topbar.tsx` | Displays Moon icon in Light Mode, Sun icon in Dark Mode | [ ] | Visual confirmation of Lucide icon switch |
| **CHK-GT-03** | Instant HTML Root Class Toggle | `<html>` / DOM | `<html class="dark">` added/removed instantly on toggle click | [ ] | Zero delay or reload required |
| **CHK-GT-04** | Tailwind Dark Style Cascade | Dashboard Views | Card surfaces, text, sidebar, and navbar apply dark palette | [ ] | No light borders or text clipping |
| **CHK-GT-05** | Storage Persistence (`theme`) | `localStorage` | Value updates to `'dark'` or `'light'` immediately | [ ] | Inspect Application tab |
| **CHK-GT-06** | Hard Page Reload Persistence | `main.tsx` / Root | Hard refresh loads directly in active theme with zero FOUC | [ ] | Test `Ctrl+Shift+R` in both modes |
| **CHK-GT-07** | Cross-Route State Stability | Router / Layout | Theme remains consistent across navigation to `/settings`, `/`, etc. | [ ] | Test multiple routes in sequence |
| **CHK-GT-08** | "Preferences" Section Removed | `Settings.tsx` | No "Preferences" card header or section container in DOM | [ ] | Inspect `/settings` DOM |
| **CHK-GT-09** | "Dark Theme" Label & Switch Removed | `Settings.tsx` | No "Dark Theme" label, helper text, or `role="switch"` button | [ ] | Ensure 0 matches in DOM |
| **CHK-GT-10** | ML Trading Config Preservation | `Settings.tsx` | Strategy cards, threshold slider, and save button fully intact | [ ] | Verify slider and card selection work |
| **CHK-GT-11** | Keyboard Navigation & Focus Ring | `Topbar.tsx` | Accessible via `Tab`, toggles via `Enter`/`Space`, clear focus ring | [ ] | Test without mouse |
| **CHK-GT-12** | Mobile Viewport Integration | Mobile Topbar | Accessible and uncluttered on 375px screens with >=40px tap area | [ ] | Test in mobile emulation |

---

## 7. Sign-off & Success Criteria

The Phase 2 Stage 3 implementation is deemed **PASSED** and ready for production deployment when:
1. All 12 checks (**CHK-GT-01** through **CHK-GT-12**) in the Verification Matrix are verified and marked complete.
2. Clicking the Topbar theme toggle instantly alters the `dark` class on `<html class="...">` without console errors.
3. No remnants of the old theme switch exist in `Settings.tsx`.
4. The dashboard maintains consistent styling, persistence, and usability across reloads, navigation, and mobile viewports.
# Settings Page Cleanup - Verification Test Plan

**Document ID:** TP-FE-SETTINGS-001  
**Feature:** Phase 2 Stage 1: Clean Up Settings  
**Target Application:** MarketPulse Web Dashboard (`web_dashboard/src/pages/Settings.tsx`)  
**Role:** Test Engineer  
**Status:** Ready for Execution  

---

## 1. Overview & Objectives

In Phase 2 Stage 1, the Settings page is streamlined to focus solely on application configuration. Account-specific fields ("User Profile" containing Name and Email) are removed, leaving profile management for a dedicated view in the future.

The objective of this test plan is to verify that:
1. **Profile Fields Removal:** The "User Profile" card, including Name and Email input fields and associated labels/values, is completely removed from the page DOM and visual layout.
2. **ML Trading Configuration Card Preservation:** The ML strategy selector cards, confidence threshold slider, and save actions continue to render and function as expected.
3. **Preferences Card Preservation:** The appearance preferences card (Dark Theme toggle switch) continues to render and function with proper state toggling and styling.
4. **Layout & Visual Hierarchy:** The vertical rhythm, spacing, and responsive layout remain clean, balanced, and free of orphan elements or layout gaps in both light and dark modes.

---

## 2. Test Environment & Prerequisites

- **Application URL:** `http://localhost:5173/settings` (or current dev server port)
- **Browsers:** Chromium (Chrome / Edge), Firefox, WebKit / Safari
- **Tools:** Browser Developer Tools (Elements inspector, Console, Network tab)
- **Prerequisites:** Web dashboard running, user authenticated / navigating to `/settings`.

---

## 3. Test Cases

### TC-SET-01: Absence of Name and Email (Profile Cleanup)
**Objective:** Ensure the User Profile section and its inputs are completely absent.

- **Preconditions:**
  - Navigate to `/settings`.
- **Steps:**
  1. Inspect the visual layout of the page.
  2. Search DOM/inspect elements for headings matching `"User Profile"`.
  3. Search DOM for inputs containing values `"Demo User"` or `"demo@example.com"`.
  4. Search DOM for labels matching `"Name"` or `"Email"`.
  5. Check browser developer console for any undefined references, warnings, or errors.
- **Expected Results:**
  - No "User Profile" heading or section card is rendered.
  - No input fields for "Name" or "Email" exist in the DOM or accessibility tree.
  - Page console shows zero errors or unhandled exceptions related to missing profile data.

---

### TC-SET-02: ML Trading Configuration Card Rendering & Functionality
**Objective:** Confirm the ML Trading Configuration card remains fully intact and functional.

- **Preconditions:**
  - Navigate to `/settings`.
- **Steps:**
  1. Verify the "ML Trading Configuration" card header and card surface render correctly.
  2. Verify all configured strategies render in the grid:
     - Zero-Loss Random Forest
     - Social Sentiment Scalper
     - Options Flow StatArb
     - Omni-Fusion Ensemble
  3. Click to select different strategy cards; confirm active border (`border-blue-500`) and checkmark badge toggle appropriately.
  4. Inspect the Confidence Threshold slider and percentage display badge (e.g. `99.9%`).
  5. Drag or adjust the slider and verify the displayed percentage updates in real-time.
  6. Click "Save Configuration" and verify the save network request (`PUT /api/api/v1/settings/trading`) and status feedback indicator.
- **Expected Results:**
  - Card displays with proper padding, typography, and contrast.
  - Strategy selection and slider adjustments are responsive and maintain state.
  - Save operation triggers and provides user feedback without issue.

---

### TC-SET-03: Preferences Card Rendering & Functionality
**Objective:** Confirm the Preferences card (Appearance / Theme toggle) renders and operates properly.

- **Preconditions:**
  - Navigate to `/settings`.
- **Steps:**
  1. Verify the "Preferences" card header renders below the ML Trading Configuration card.
  2. Verify the "Dark Theme" label and description ("Toggle dark mode for the dashboard.") are visible.
  3. Verify the toggle switch component is present with proper accessibility role (`role="switch"`).
  4. Click the toggle switch to enable Dark Theme:
     - Observe background transitions and knob slide animation (`translate-x-5`).
     - Confirm `aria-checked="true"`.
     - Confirm `dark` class is toggled on the document root (`<html>`).
  5. Click the toggle switch again to return to Light Theme:
     - Confirm knob returns to `translate-x-0` and `aria-checked="false"`.
- **Expected Results:**
  - Preferences card renders smoothly with no visual regressions.
  - Theme toggle correctly switches between Light and Dark modes.

---

### TC-SET-04: Responsive Layout & Visual Hierarchy
**Objective:** Ensure card spacing and page aesthetics remain balanced without the profile card.

- **Preconditions:**
  - Navigate to `/settings`.
- **Steps:**
  1. View page on desktop viewport (>= 1024px). Verify spacing between page title, ML Trading Configuration card, and Preferences card.
  2. Resize viewport to tablet (768px - 1023px) and mobile (< 768px).
  3. Verify card margins, padding, and vertical stacking (`space-y-6`).
  4. Check both Light Mode and Dark Mode aesthetics.
- **Expected Results:**
  - Cards stack cleanly with uniform spacing.
  - No awkward gaps, layout shifts, or horizontal scrollbars occur across viewport sizes.

---

## 4. Verification Checklist

| Check ID | Verification Item | Status | Notes |
| :--- | :--- | :---: | :--- |
| **CHK-01** | "User Profile" card removed | [ ] | Verify card container is absent |
| **CHK-02** | "Name" input & label removed | [ ] | Ensure no input or label in DOM |
| **CHK-03** | "Email" input & label removed | [ ] | Ensure no input or label in DOM |
| **CHK-04** | ML Trading Configuration card intact | [ ] | Strategy selection & threshold functional |
| **CHK-05** | Preferences card intact | [ ] | Dark theme toggle switch functional |
| **CHK-06** | Responsive layout & styling clean | [ ] | Consistent padding/spacing, zero console errors |

---

## 5. Sign-Off Criteria

The Stage 1 Settings cleanup is considered verified and ready for release when all checklist items (**CHK-01** through **CHK-06**) pass with zero console errors and no visual regressions in both light and dark themes.
# System-Status Badge & Infrastructure Health Polling - Test Plan

**Document ID:** TP-FE-SYSSTAT-001  
**Feature:** Phase 2 Stage 4: System-Status Badge (`useHealthCheck` Polling)  
**Target Application:** MarketPulse Web Dashboard (`web_dashboard/src/hooks/useHealthCheck.ts`, `web_dashboard/src/components/layout/Topbar.tsx`) & Backend API (`app/routers/health.py`)  
**Role:** Test Engineer  
**Status:** Ready for Execution  

---

## 1. Overview & Objectives

In Phase 2 Stage 4, MarketPulse introduces an infrastructure health indicator badge in the dashboard topbar. The frontend periodically polls the backend `/health/full` endpoint using the `useHealthCheck` React hook to monitor core infrastructure subsystems (PostgreSQL/TimescaleDB, Valkey/Redis, MongoDB, ChromaDB) and dynamically display the operational state to the user.

The system supports three primary health states:
1. **Healthy (Green):** API is online and all database and vector store subsystems report `"ok"`.
2. **Degraded (Yellow/Amber):** API is reachable, but one or more backing services (e.g., PostgreSQL, Valkey, MongoDB, ChromaDB) report an error or timeout.
3. **Offline (Red):** The API server is completely unreachable (connection refused, network disconnected, timeout, or 5xx gateway failure).

### Primary Testing Objectives:
- **Verification of `useHealthCheck` Polling:** Confirm that the hook issues periodic GET requests to `/health/full` on the designated cadence (default 10 seconds), avoids duplicate intervals, and cleans up timers on unmount.
- **Degraded State Verification:** Validate that failing a database connection (specifically PostgreSQL or Valkey/Mongo/Chroma) accurately reflects `status: "degraded"` in the backend response and transitions the UI badge from green to yellow/amber.
- **Offline State Verification:** Validate that terminating the API process or blocking network transport immediately triggers the catch block, transitioning the badge from green/yellow to red ("offline").
- **Recovery & Reconnection Verification:** Ensure that restoring failing services automatically transitions the badge back to "healthy" (green) on the subsequent polling tick without requiring a manual page refresh.
- **UI, Accessibility & Theme Compliance:** Verify badge rendering, pulsating animation, tooltip descriptions, ARIA attributes (`role="status"`, `aria-label`), and contrast in both Light and Dark themes.

---

## 2. System Architecture & Polling Data Flow

```
+---------------------------------------------------------------------------------------+
| MarketPulse Web Dashboard (Browser)                                                   |
|                                                                                       |
|   Topbar.tsx                                                                          |
|   +-------------------------------------------------------------------------------+   |
|   | [Overview] [Status Badge (🟢/🟡/🔴)]       [Theme Toggle] [Bell] [User Profile]|   |
|   +-------------------------------------------------------------------------------+   |
|                               ^                                                       |
|                               | status: 'healthy' | 'degraded' | 'offline'            |
|                               |                                                       |
|   useHealthCheck(intervalMs = 10000)                                                  |
|   - Starts setInterval on mount                                                       |
|   - Invokes apiClient.get('/health/full')                                             |
|   - Cleans up clearInterval on unmount                                                |
+---------------------------------------------------------------------------------------+
                                |
               HTTP GET /api/v1/health/full
               (Interval: 10 seconds)
                                v
+---------------------------------------------------------------------------------------+
| MarketPulse FastAPI Backend (`app/routers/health.py`)                                  |
|                                                                                       |
|   Endpoint: @router.get("/health/full")                                               |
|   Performs async ping checks with 3-second connect timeouts:                          |
|   +-------------------+-------------------+-------------------+-------------------+   |
|   | PostgreSQL        | Valkey (Redis)    | MongoDB           | ChromaDB          |   |
|   | (asyncpg.connect) | (redis.ping)      | (motor admin cmd) | (/heartbeat)      |   |
|   +-------------------+-------------------+-------------------+-------------------+   |
|                                                                                       |
|   Status Determination:                                                               |
|   - All checks == "ok"                --> {"status": "ok", "checks": {...}}           |
|   - Any check != "ok" (Exception)     --> {"status": "degraded", "checks": {...}}     |
|   - Process terminated / Unreachable  --> Network Error (Axios catch -> "offline")    |
+---------------------------------------------------------------------------------------+
```

---

## 3. Test Environment & Prerequisites

### 3.1 Environments Under Test
- **Frontend Client:** `http://localhost:5173` (Vite dev server) or deployed dashboard container
- **Backend API:** `http://127.0.0.1:8080` (local uvicorn) or `http://192.168.1.134:8080` (LXC API server)
- **Infrastructure Services (Docker Compose / Podman / LXC):**
  - PostgreSQL / TimescaleDB: Port `5432` (`marketpulse-postgres`)
  - Valkey: Port `6379` (`marketpulse-valkey`)
  - MongoDB: Port `27017` (`marketpulse-mongo`)
  - ChromaDB: Port `8000` (`marketpulse-chroma`)

### 3.2 Required Tools & Instrumentation
- **Browser Developer Tools:**
  - **Network Tab:** Filter by `health/full` to inspect request cadence, headers, and JSON responses.
  - **Console Tab:** Monitor for unexpected errors or uncaught promise rejections.
  - **Network Throttling:** Ability to toggle "Offline" mode.
- **Terminal Access:** Access to execute `docker`, `curl`, or command-line scripts to halt/restart backend and DB services.

---

## 4. Health Check States & Specification Matrix

| State | Backend Endpoint HTTP Status | Backend Response Body (`/health/full`) | Hook `status` Value | UI Dot Color | Badge Label / Tooltip |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Healthy** | `200 OK` | `{"status": "ok", "checks": {"postgres": "ok", "valkey": "ok", "mongodb": "ok", "chroma": "ok"}}` | `'healthy'` | Green (`bg-emerald-500` / `bg-green-500`) | "Systems Operational" |
| **Degraded** | `200 OK` | `{"status": "degraded", "checks": {"postgres": "connection refused...", "valkey": "ok", ...}}` | `'degraded'` | Yellow/Amber (`bg-amber-500` / `bg-yellow-500`) | "System Degraded (DB Issue)" |
| **Offline** | Network Error / `502 Bad Gateway` / `ECONNREFUSED` / Timeout | *(None - Request Failed / Rejected Promise)* | `'offline'` | Red (`bg-rose-500` / `bg-red-500`) | "System Offline" |

---

## 5. Fault Injection & Simulation Methodology

To systematically verify the badge and hook behavior, use the following simulation techniques for **Degraded** and **Offline** conditions.

### 5.1 Triggering the "Degraded" State (Failed DB Connection)

The system transitions to "Degraded" when the API is running, but one or more backing databases fail their connection check. Choose one of the following methods:

#### Method A: Docker Container Suspension (Live Infrastructure)
1. Ensure the full stack is running (`docker compose up -d` or active LXC containers).
2. Stop only the PostgreSQL database container:
   ```bash
   docker stop marketpulse-postgres
   ```
   *(Alternatively, stop Valkey: `docker stop marketpulse-valkey` or Mongo: `docker stop marketpulse-mongo`)*
3. Observe backend logs (`docker logs -f marketpulse-api` or uvicorn console).
4. Verify backend endpoint directly via curl:
   ```bash
   curl -s http://localhost:8080/health/full | jq .
   ```
   **Expected Response:**
   ```json
   {
     "status": "degraded",
     "checks": {
       "postgres": "Connection refused or timed out",
       "valkey": "ok",
       "mongodb": "ok",
       "chroma": "ok"
     }
   }
   ```
5. To recover:
   ```bash
   docker start marketpulse-postgres
   ```

#### Method B: Temporary Backend Code Mock (Isolated Testing)
If running without Docker or in a local mock environment, temporarily simulate a DB failure in `app/routers/health.py`:
```python
# In app/routers/health.py under health_full():
# Simulate DB error:
checks["postgres"] = "ConnectionRefusedError: [Errno 111] Connection refused"
```
Revert the change once testing is complete.

#### Method C: Browser DevTools Network Interception / Local Overrides
1. Open DevTools in Chrome/Edge (`F12`).
2. Go to the **Network** tab, find a request to `health/full`.
3. Right-click the request and select **Override content** (or use Request Interceptor / Mockoon).
4. Edit the response body to:
   ```json
   {
     "status": "degraded",
     "checks": {
       "postgres": "Mocked asyncpg connection timeout",
       "valkey": "ok",
       "mongodb": "ok",
       "chroma": "ok"
     }
   }
   ```
5. Save the override. The next polling tick will consume the mocked degraded response.

---

### 5.2 Triggering the "Offline" State (API Outage)

The system transitions to "Offline" when the network request to `/health/full` fails entirely. Choose one of the following methods:

#### Method A: Terminate the Backend API Process (Service Outage)
1. Stop the running FastAPI / Uvicorn server:
   - If running in terminal: Press `Ctrl + C`.
   - If running in Docker:
     ```bash
     docker stop marketpulse-api
     ```
   - If running in Linux/LXC:
     ```bash
     sudo systemctl stop marketpulse-api
     ```
2. Verify with curl:
   ```bash
   curl http://localhost:8080/health/full
   # Output: curl: (7) Failed to connect to localhost port 8080: Connection refused
   ```
3. To recover: Restart the FastAPI server (`docker start marketpulse-api` or restart uvicorn).

#### Method B: Browser DevTools Offline Mode (Client-Side Network Loss)
1. In the browser where the dashboard is running, open **DevTools** (`F12`).
2. Navigate to the **Network** tab.
3. In the throttling dropdown (labeled "No throttling" by default), select **Offline**.
4. Within 10 seconds (the next polling tick), Axios will fail with `ERR_INTERNET_DISCONNECTED` or `Network Error`.
5. To recover: Switch the throttling dropdown back to **No throttling**.

#### Method C: URL Blocking in DevTools
1. In DevTools, open the **Network Request Blocking** drawer (`Ctrl+Shift+P` -> `Show Network request blocking`).
2. Click **Add pattern** and enter `*health/full*`.
3. Check the enable box. Subsequent polling requests will return `(blocked:devtools)`.
4. To recover: Uncheck the blocking rule.

---

## 6. Detailed Test Cases

### TC-SYSSTAT-01: Nominal Polling & Healthy State Verification
**Objective:** Confirm initial load and continuous polling of the `/health/full` endpoint when all services are operational.

- **Preconditions:**
  - Backend API is running with all database containers active (Postgres, Valkey, Mongo, Chroma).
  - Web dashboard is loaded at `http://localhost:5173`.
  - Browser DevTools is open to the **Network** tab (filter: `health`).
- **Steps:**
  1. Open or refresh the dashboard page.
  2. Inspect the Network tab immediately upon page load.
  3. Observe the initial HTTP GET request to `/health/full`.
  4. Inspect the HTTP response code and payload.
  5. Inspect the Topbar status indicator in the UI.
  6. Hover over or inspect the status indicator.
- **Expected Results:**
  - An initial request to `/health/full` is fired immediately on component mount (line 29 in `useHealthCheck.ts`).
  - Response code is `200 OK`.
  - Response body contains `status: "ok"`.
  - Status indicator in the Topbar renders a solid or pulsing **Green** dot (`bg-emerald-500` or `bg-green-500`).
  - Tooltip/text displays "Healthy", "Operational", or "All systems normal".
  - Console shows no unhandled errors or warnings.

---

### TC-SYSSTAT-02: Polling Interval Cadence & Memory Cleanup
**Objective:** Verify that `useHealthCheck` polls every 10 seconds and releases interval timers upon component unmount.

- **Preconditions:**
  - User is on the dashboard.
  - Browser DevTools **Network** tab is open with timestamps enabled.
- **Steps:**
  1. Leave the dashboard open without user interaction for 45 seconds.
  2. Record the timestamps of consecutive requests to `/health/full`.
  3. Calculate the delta between successive requests.
  4. Navigate away from the view containing Topbar (or unmount Topbar in test harness).
  5. Observe the Network tab for another 30 seconds.
- **Expected Results:**
  - Successive `/health/full` requests occur at consistent intervals of **10,000 ms ± 500 ms** (10 seconds).
  - No duplicate or overlapping polling loops are initiated (exactly 1 request per interval).
  - When the component unmounts, the interval is cleared via `clearInterval`, and no further network calls are dispatched.

---

### TC-SYSSTAT-03: Degraded State Simulation via DB Failure
**Objective:** Verify that a database connection failure transitions the status badge to "Degraded" (Yellow/Amber).

- **Preconditions:**
  - Dashboard is open and currently displaying "Healthy" (Green dot).
  - Terminal access is available.
- **Steps:**
  1. Trigger a DB failure using Section 5.1 (e.g., `docker stop marketpulse-postgres` or apply backend mock).
  2. Watch the **Network** tab in the browser for the next scheduled polling tick (within 10 seconds).
  3. Inspect the response payload of the `/health/full` request.
  4. Observe the status badge in the Topbar.
  5. Hover over the badge to inspect the tooltip or status text.
- **Expected Results:**
  - Endpoint returns HTTP `200 OK` with payload:
    `{ "status": "degraded", "checks": { "postgres": "<error string>", ... } }`
  - Hook state updates to `'degraded'`.
  - Topbar status indicator changes from Green to **Yellow/Amber** (`bg-amber-500` or `bg-yellow-500`).
  - Status tooltip or label updates to reflect "Degraded" or "Database Warning".
  - The rest of the dashboard remains interactive without application crashes.

---

### TC-SYSSTAT-04: Degraded Recovery to Healthy
**Objective:** Verify automatic self-healing transition from "Degraded" back to "Healthy" when the DB reconnects.

- **Preconditions:**
  - System is currently in "Degraded" state (Yellow dot, PostgreSQL stopped).
- **Steps:**
  1. Restore the database service:
     ```bash
     docker start marketpulse-postgres
     ```
  2. Wait up to 10 seconds for the next polling cycle.
  3. Inspect the `/health/full` network request in DevTools.
  4. Observe the status badge in the Topbar.
- **Expected Results:**
  - Once Postgres is ready, `/health/full` returns `{"status": "ok", "checks": {"postgres": "ok", ...}}`.
  - Hook state transitions from `'degraded'` to `'healthy'`.
  - Topbar indicator seamlessly transitions from Yellow/Amber back to **Green**.
  - No manual page reload or user intervention is required.

---

### TC-SYSSTAT-05: Offline State Simulation via API Shutdown
**Objective:** Verify that stopping the backend API server transitions the status badge to "Offline" (Red).

- **Preconditions:**
  - Dashboard is open and currently displaying "Healthy" or "Degraded".
  - Terminal access is available.
- **Steps:**
  1. Stop the backend API using Section 5.2 (e.g., `docker stop marketpulse-api` or terminate the Uvicorn process).
  2. Wait up to 10 seconds for the next polling tick.
  3. Inspect the Network tab in DevTools: observe failed HTTP request (`ERR_CONNECTION_REFUSED` or timeout).
  4. Observe the status badge in the Topbar.
  5. Hover over the badge to inspect the tooltip or status text.
- **Expected Results:**
  - The request to `/health/full` fails and is caught by the `catch (error)` block in `useHealthCheck.ts`.
  - Hook state updates to `'offline'`.
  - Topbar status indicator transitions to **Red** (`bg-rose-500` or `bg-red-500`).
  - Tooltip/label indicates "System Offline" or "Backend Unreachable".
  - The application handles the error gracefully without throwing uncaught React errors or rendering a blank screen.

---

### TC-SYSSTAT-06: Offline Recovery to Healthy
**Objective:** Verify automatic recovery from "Offline" back to "Healthy" when the API server resumes.

- **Preconditions:**
  - System is in "Offline" state (Red dot, API stopped).
  - Dashboard remains open in the browser.
- **Steps:**
  1. Restart the backend API server:
     ```bash
     docker start marketpulse-api
     ```
     *(Or start uvicorn: `uvicorn app.main:app --port 8080`)*
  2. Wait for the server to finish initialization.
  3. Allow `useHealthCheck` to execute its subsequent polling tick.
  4. Inspect the Network tab and Topbar badge.
- **Expected Results:**
  - The polling request succeeds with HTTP `200 OK`.
  - Hook state transitions from `'offline'` to `'healthy'`.
  - Topbar status badge switches from Red back to **Green**.
  - System logs confirm successful connection restoration.

---

### TC-SYSSTAT-07: Rapid State Flapping / Transition Sequences
**Objective:** Verify state stability across rapid transitions (Healthy -> Degraded -> Offline -> Degraded -> Healthy).

- **Preconditions:**
  - Stack is running.
- **Steps:**
  1. Start at Healthy (Green).
  2. Stop PostgreSQL container -> Verify badge turns Yellow within 10s.
  3. Stop API container -> Verify badge turns Red within 10s.
  4. Restart API container (with Postgres still stopped) -> Verify badge turns Yellow within 10s.
  5. Restart PostgreSQL container -> Verify badge returns to Green within 10s.
- **Expected Results:**
  - Badge reliably reflects each state in sequence without getting stuck in an outdated state.
  - React state updates correctly without race conditions or memory leaks.

---

### TC-SYSSTAT-08: UI Presentation, Accessibility & Theme Contrast
**Objective:** Verify visual appearance, theme switching (Light/Dark), and accessibility compliance.

- **Preconditions:**
  - User is on the dashboard.
- **Steps:**
  1. Inspect the status badge element in the Topbar DOM:
     - Verify presence of `role="status"` or `aria-live="polite"`.
     - Verify accessible `aria-label` (e.g. `aria-label="System status: healthy"`).
  2. Switch the dashboard to **Dark Mode** via the Topbar theme toggle:
     - Verify Green dot (`bg-emerald-500`), Yellow dot (`bg-amber-500`), and Red dot (`bg-rose-500`) remain vibrant and clearly distinguishable against dark header background (`dark:bg-gray-800`).
  3. Switch back to **Light Mode**:
     - Verify all three colors maintain sufficient contrast against light header background (`bg-white`).
  4. Test on a mobile viewport (width: 375px):
     - Ensure the badge does not cause layout overflow or displace adjacent icons (Theme, Bell, User profile).
- **Expected Results:**
  - Color contrast meets WCAG AA criteria (minimum 3:1 for graphical UI indicators).
  - Badge is fully responsive and readable across all viewport sizes.
  - Screen readers announce the system status change cleanly.

---

## 7. Automated Test Suites & Code Snippets

### 7.1 Frontend Hook Unit Test (Vitest / React Testing Library)

Create or execute unit tests for `useHealthCheck` using mock timers:

```typescript
import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useHealthCheck } from './useHealthCheck';
import apiClient from '../api/client';

vi.mock('../api/client');

describe('useHealthCheck Hook', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('initializes with healthy and maintains healthy when status is ok', async () => {
    (apiClient.get as any).mockResolvedValue({
      data: { status: 'ok', checks: { postgres: 'ok', valkey: 'ok' } }
    });

    const { result } = renderHook(() => useHealthCheck(5000));

    await act(async () => {
      vi.advanceTimersByTime(100);
    });

    expect(result.current.status).toBe('healthy');
    expect(apiClient.get).toHaveBeenCalledWith('/health/full');
  });

  it('transitions to degraded when response indicates degraded', async () => {
    (apiClient.get as any).mockResolvedValue({
      data: { status: 'degraded', checks: { postgres: 'connection timeout' } }
    });

    const { result } = renderHook(() => useHealthCheck(5000));

    await act(async () => {
      vi.advanceTimersByTime(100);
    });

    expect(result.current.status).toBe('degraded');
  });

  it('transitions to offline when API request fails (network error)', async () => {
    (apiClient.get as any).mockRejectedValue(new Error('Network Error'));

    const { result } = renderHook(() => useHealthCheck(5000));

    await act(async () => {
      vi.advanceTimersByTime(100);
    });

    expect(result.current.status).toBe('offline');
  });

  it('polls at designated interval and cleans up on unmount', async () => {
    (apiClient.get as any).mockResolvedValue({ data: { status: 'ok' } });

    const { unmount } = renderHook(() => useHealthCheck(10000));

    expect(apiClient.get).toHaveBeenCalledTimes(1);

    await act(async () => {
      vi.advanceTimersByTime(10000);
    });
    expect(apiClient.get).toHaveBeenCalledTimes(2);

    await act(async () => {
      vi.advanceTimersByTime(10000);
    });
    expect(apiClient.get).toHaveBeenCalledTimes(3);

    unmount();

    await act(async () => {
      vi.advanceTimersByTime(20000);
    });
    expect(apiClient.get).toHaveBeenCalledTimes(3); // No additional calls after unmount
  });
});
```

---

### 7.2 Backend Health Endpoint Test (Pytest + FastAPI TestClient)

```python
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_health_full_all_ok():
    with patch("asyncpg.connect", new_callable=AsyncMock), \
         patch("redis.asyncio.Redis.ping", new_callable=AsyncMock), \
         patch("motor.motor_asyncio.AsyncIOMotorClient.admin", new_callable=AsyncMock), \
         patch("httpx.AsyncClient.get", return_value=AsyncMock(status_code=200)):
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/health/full")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["checks"]["postgres"] == "ok"

@pytest.mark.asyncio
async def test_health_full_degraded_when_postgres_fails():
    with patch("asyncpg.connect", side_effect=Exception("connection refused")), \
         patch("redis.asyncio.Redis.ping", new_callable=AsyncMock), \
         patch("motor.motor_asyncio.AsyncIOMotorClient.admin", new_callable=AsyncMock), \
         patch("httpx.AsyncClient.get", return_value=AsyncMock(status_code=200)):
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/health/full")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
            assert "connection refused" in data["checks"]["postgres"]
```

---

## 8. Verification Execution Checklist

| ID | Test Case | Target State | Execution Method | Result (Pass/Fail) | Sign-off Date |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-SYSSTAT-01** | Nominal Polling | Healthy (🟢) | Live API & DBs | Pending | |
| **TC-SYSSTAT-02** | Cadence (10s) & Cleanup | Lifecycle | DevTools Network & Timers | Pending | |
| **TC-SYSSTAT-03** | Failed DB Connection | Degraded (🟡) | Stop Postgres container | Pending | |
| **TC-SYSSTAT-04** | Recovery from Degraded | Healthy (🟢) | Start Postgres container | Pending | |
| **TC-SYSSTAT-05** | Total API Shutdown | Offline (🔴) | Stop API process / DevTools Offline | Pending | |
| **TC-SYSSTAT-06** | Recovery from Offline | Healthy (🟢) | Restart API process | Pending | |
| **TC-SYSSTAT-07** | Transition Sequence | Multi-State | Rapid Stop/Start sequence | Pending | |
| **TC-SYSSTAT-08** | Accessibility & Themes | UI Compliance | Light/Dark inspection & ARIA | Pending | |

---

## 9. Rollback & Emergency Procedures

- If polling creates excessive server load:
  - Adjust default `intervalMs` from `10000` (10s) to `30000` (30s) or `60000` (60s) in `useHealthCheck.ts`.
- If the `/health/full` endpoint hangs on dead connections:
  - Ensure timeouts in `app/routers/health.py` (currently 3 seconds for asyncpg, valkey, motor, and httpx) are strictly enforced and do not block the worker thread.
- If CORS or Axios interceptor issues arise:
  - Confirm proxy configuration in `web_dashboard/src/api/client.ts` strips `/api/` prefix appropriately.
# ML Model Training UI & WebSocket Telemetry - Test Plan

**Document ID:** TP-FE-TRAINUI-001
**Feature:** Phase 3 Stage 1: Live Progress Bar & WebSocket Telemetry (`/training`)
**Target Application:** MarketPulse Web Dashboard (`web_dashboard/src/pages/Training.tsx`, `web_dashboard/src/components/training/*`) & Backend WebSocket API (`app/routers/ws.py`, `ml_sidecar/server.py`)
**Role:** Test Engineer
**Status:** Ready for Execution

---

## 1. Overview & Objectives

In Phase 3 Stage 1 of the MarketPulse development plan, the platform transitions model retraining into a dedicated, interactive, real-time control room accessible at the `/training` route. Previously, training operations were unmonitored or triggered blindly via static API endpoints without streaming progress indicators.

The `/training` page introduces an end-to-end interactive training console featuring:
1. **Model Training Control:** A primary **"Start Training"** action button allowing operators to initiate model training runs with configurable parameters.
2. **Real-Time Progress Bar:** A dynamic progress bar that advances smoothly from 0% to 100% reflecting current training completion status.
3. **Live Telemetry HUD:** Real-time metrics streaming over WebSocket, including current execution stage (e.g., data ingestion, feature engineering, model fitting, validation), active data source, step/epoch counters, current batch loss, validation loss, and elapsed time.
4. **Auto-Scrolling Terminal Console:** An embedded ANSI/monospaced terminal viewer displaying streaming stdout/stderr training logs that automatically scrolls to the latest incoming line as new WebSocket telemetry arrives.
5. **Sticky Scrolling & User Override:** Automatic scrolling must pin to the bottom when the user is at the bottom, but allow manual scrolling inspection when the user scrolls upward, resuming auto-scroll when returned to the bottom.
6. **Error Handling & Resilience:** Graceful handling of WebSocket disconnections, backend exceptions, and network latency without freezing the user interface.

### Primary Testing Objectives:
- **Route & Layout Verification:** Confirm `/training` is properly registered in `App.tsx`, secured with authentication (`PrivateRoute`), and accessible via the application navigation `Sidebar.tsx`.
- **Start Training Trigger:** Verify that clicking the "Start Training" button issues the appropriate training initiation request, transitions the UI into the active state, disables duplicate submissions, and initializes the WebSocket stream.
- **Progress Bar Advancement:** Verify that incoming WebSocket telemetry packets update the progress bar width, percentage label, and ARIA attributes in real time.
- **Terminal Log Streaming & Auto-Scroll:** Verify that received log chunks are appended without data truncation and that the terminal container automatically scrolls (`scrollTop = scrollHeight`) to keep the latest message visible.
- **Scroll Lock / Override Behavior:** Validate that if a user manually scrolls up to inspect previous epoch outputs, the auto-scroll does not aggressively yank the viewport back down until the user scrolls back to the bottom.
- **Telemetry HUD Metric Updates:** Ensure stage indicators, epoch/step counters, and loss values update synchronously with incoming telemetry frames.
- **Completion & Error States:** Validate state transitions upon normal completion (100% progress, summary metrics) and error scenarios (failed training, disconnected socket, timeout).
- **Responsive Design & Dark Theme:** Confirm terminal contrast, progress bar styling, and layout stability across desktop, tablet, and mobile viewports in both Light and Dark modes.

---

## 2. System Architecture & Telemetry Data Flow

```
+-----------------------------------------------------------------------------------------------+
| MarketPulse Web Dashboard (Browser Client)                                                    |
|                                                                                               |
|  /training Route                                                                              |
|  +-----------------------------------------------------------------------------------------+  |
|  | Header: ML Retraining Station               [Status: IDLE / TRAINING / COMPLETED]       |  |
|  | Configuration Options: Model [RandomForest v1] | Tickers [AAPL, NVDA] | Epochs [10]     |  |
|  | [ ▶ Start Training ] [ ⏹ Abort ]                                                        |  |
|  +-----------------------------------------------------------------------------------------+  |
|  | Telemetry HUD:                                                                          |  |
|  | [ Stage: Fitting Model ] [ Source: TimescaleDB ] [ Epoch: 4/10 ] [ Loss: 0.0341 ]       |  |
|  +-----------------------------------------------------------------------------------------+  |
|  | Progress Bar: [=============================>                  ] 40%                    |  |
|  +-----------------------------------------------------------------------------------------+  |
|  | Terminal Console (Monospace Log Stream - Auto-Scrolling):                               |  |
|  | [19:15:01] Ingesting 2,500 OHLCV bars from TimescaleDB...                               |  |
|  | [19:15:03] Generating 23 technical indicators (RSI, MACD, BB, VWAP)...                   |  |
|  | [19:15:06] Training RandomForestRegressor - Estimator 40/100...                         |  |
|  | [19:15:08] Epoch 4/10 - Batch loss: 0.0341 - Val score: 0.892 <--- Auto-scroll pinned  |  |
|  +-----------------------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------------------+
                             |                                           ^
              1. POST /api/v1/training/start                             | 2. WebSocket Frames
                 (or WS Handshake)                                       |    (Telemetry & Logs)
                             v                                           |
+-----------------------------------------------------------------------------------------------+
| MarketPulse Backend API (`app/routers/ws.py` & `app/routers/training.py`)                      |
|                                                                                               |
|  WebSocket Endpoint: `/ws/training` or `/api/v1/training/stream`                              |
|  - Accepts client connection with JWT validation                                             |
|  - Spawns / attaches to background training runner                                            |
|  - Streams real-time telemetry packets (JSON) & stdout lines to connected client              |
+-----------------------------------------------------------------------------------------------+
                                             ^
                                             | Inter-process pipes / Redis PubSub / Celery
                                             v
+-----------------------------------------------------------------------------------------------+
| MarketPulse ML Sidecar / Worker (`ml_sidecar/train_model.py`)                                  |
|                                                                                               |
|  - Fetches data from PostgreSQL / TimescaleDB & sentiment caches                              |
|  - Runs feature engineering pipeline                                                          |
|  - Trains ensemble models & calculates step loss                                              |
|  - Emits telemetry events every batch/step                                                    |
+-----------------------------------------------------------------------------------------------+
```

---

## 3. WebSocket Telemetry Schema Specification

The frontend terminal and progress components consume JSON telemetry frames over the WebSocket connection. The protocol adheres to the following message contracts:

### 3.1 Connection Handshake / Status Frame
Sent immediately upon successful connection establishment:
```json
{
  "type": "connection_ack",
  "session_id": "trn-20260916-01a",
  "status": "connected",
  "timestamp": "2026-09-16T19:15:00.000Z"
}
```

### 3.2 Live Progress & Telemetry Frame
Broadcast periodically (e.g., every 250ms - 500ms or on each training step):
```json
{
  "type": "telemetry",
  "session_id": "trn-20260916-01a",
  "stage": "model_training",
  "stage_display": "Fitting Ensemble Model",
  "data_source": "timescaledb_ohlcv",
  "epoch": 4,
  "total_epochs": 10,
  "step": 140,
  "total_steps": 350,
  "progress_pct": 40.0,
  "loss": 0.0341,
  "val_loss": 0.0418,
  "log_line": "[TRAIN] [19:15:08] Epoch 4/10 (step 140/350) - Loss: 0.0341 - Estimators fitted: 40/100",
  "elapsed_seconds": 12.4,
  "timestamp": "2026-09-16T19:15:08.120Z"
}
```

### 3.3 Training Completed Frame
Broadcast when the pipeline finishes successfully:
```json
{
  "type": "completed",
  "session_id": "trn-20260916-01a",
  "stage": "completed",
  "stage_display": "Training Complete",
  "progress_pct": 100.0,
  "metrics": {
    "final_loss": 0.0215,
    "accuracy": 0.914,
    "duration_seconds": 28.6,
    "model_path": "/opt/marketpulse/models/rf_baseline_model.joblib"
  },
  "log_line": "[SUCCESS] [19:15:28] Retraining complete. New model artifacts deployed and hot-reloaded.",
  "timestamp": "2026-09-16T19:15:28.650Z"
}
```

### 3.4 Training Error / Failure Frame
Broadcast if an unhandled exception or data ingestion error occurs:
```json
{
  "type": "error",
  "session_id": "trn-20260916-01a",
  "stage": "error",
  "stage_display": "Training Failed",
  "error_message": "TimescaleDB connection timeout while fetching OHLCV data for AAPL",
  "log_line": "[ERROR] [19:15:14] Traceback (most recent call last): ConnectionRefusedError: [Errno 111]",
  "timestamp": "2026-09-16T19:15:14.300Z"
}
```

---

## 4. Test Environment & Prerequisites

### 4.1 Environments Under Test
- **Frontend URL:** `http://localhost:5173/training` (Vite dev server)
- **Backend API Base:** `http://localhost:8080` (FastAPI backend) or `http://192.168.1.134:8080`
- **WebSocket Endpoint:** `ws://localhost:8080/ws/training` (or proxied via Vite `/api/ws`)
- **ML Sidecar Service:** `http://192.168.1.134:8085` (`ml_sidecar`)

### 4.2 Required Browser Tools & Setup
- **Browser Developer Tools:**
  - **Network Tab:** Filter by `WS` to inspect the live WebSocket frames, message cadence, and payload sizes.
  - **Console Tab:** Monitor for connection state changes, WebSocket errors, or unhandled React render warnings.
  - **Elements / Inspector:** Verify DOM scroll position (`element.scrollTop`, `element.scrollHeight`, `element.clientHeight`) and ARIA attributes.
- **Authentication:** Valid JWT session stored in `localStorage.getItem('token')`.

---

## 5. Training UI State Machine & Verification Matrix

| State | "Start Training" Button | Progress Bar | Telemetry HUD | Terminal Console | Status Indicator |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Idle** | Enabled (`bg-indigo-600`, "Start Training") | 0% (`w-0`, hidden or grey track) | Dashes (`--`), "Idle" | Shows initial prompt: `Ready. Click "Start Training" to begin.` | Grey/Neutral ("Ready") |
| **Starting / Connecting** | Disabled + Spinner ("Connecting...") | 0% (Indeterminate pulse optional) | "Initializing connection..." | `[INFO] Initializing WebSocket connection to training engine...` | Amber/Yellow ("Connecting") |
| **Running / In-Progress** | Disabled ("Training in progress...") | Dynamic (0% -> 99%), Smooth transition | Live stage, epoch, step, loss updating | Continuously appending lines, pinned to bottom (`auto-scroll: ON`) | Blue/Pulsing ("Running") |
| **User Scrolled Up** | Disabled ("Training in progress...") | Dynamic (0% -> 99%) | Live updating | Logs continue appending, scroll frozen on inspected line, "Scroll to Bottom" badge appears | Blue/Pulsing ("Running") |
| **Completed** | Enabled ("Start New Run") | 100% (`bg-emerald-500` / `bg-green-500`) | Final metrics: Stage: Completed, Final Loss, Elapsed Time | Appends completion banner, final model hash/path | Green ("Completed") |
| **Error / Failed** | Enabled ("Retry Training") | Frozen % or Red (`bg-rose-500` / `bg-red-500`) | Stage: Error, error detail card | Appends red error traceback, error summary | Red ("Failed") |
| **Disconnected** | Enabled or "Reconnect" button | Preserved last known % | Stage: Disconnected | `[WARN] WebSocket connection closed unexpectedly.` | Red/Amber ("Disconnected") |

---

## 6. Test Harness & Simulation Methodology

To execute verification without requiring a 30-minute heavy GPU/CPU retraining pipeline for every single test cycle, use the following test harness options:

### 6.1 Method A: Mock WebSocket Telemetry Server (Fast Automated Testing)
Use a lightweight Python mock script (`test_training_mock_ws.py`) that simulates the exact telemetry frames at controlled intervals (e.g. 100ms per step):

```python
import asyncio
import json
import websockets

async def handler(websocket):
    print("Client connected to mock training WS")
    await websocket.send(json.dumps({
        "type": "connection_ack",
        "session_id": "test-mock-001",
        "status": "connected"
    }))

    stages = [
        ("data_ingestion", "TimescaleDB Ingestion", 10, "Fetching 10,000 bars..."),
        ("feature_engineering", "Feature Calculation", 30, "Calculating RSI, MACD, Bollinger Bands..."),
        ("model_training", "RandomForest Fitting", 75, "Fitting trees in forest..."),
        ("validation", "Evaluating Metrics", 95, "Calculating RMSE and direction accuracy...")
    ]

    for stage_key, stage_name, target_pct, desc in stages:
        current_pct = target_pct - 15
        while current_pct <= target_pct:
            await asyncio.sleep(0.3)
            await websocket.send(json.dumps({
                "type": "telemetry",
                "session_id": "test-mock-001",
                "stage": stage_key,
                "stage_display": stage_name,
                "data_source": "timescale_aapl",
                "epoch": 2,
                "total_epochs": 5,
                "step": int(current_pct * 4),
                "total_steps": 400,
                "progress_pct": float(current_pct),
                "loss": round(0.08 - (current_pct * 0.0006), 4),
                "log_line": f"[{stage_name}] Step {int(current_pct * 4)}: {desc} (Loss: {round(0.08 - (current_pct * 0.0006), 4)})"
            }))
            current_pct += 5

    await asyncio.sleep(0.5)
    await websocket.send(json.dumps({
        "type": "completed",
        "session_id": "test-mock-001",
        "stage": "completed",
        "stage_display": "Training Complete",
        "progress_pct": 100.0,
        "metrics": {"final_loss": 0.0182, "duration_seconds": 12.5},
        "log_line": "[SUCCESS] Training pipeline completed successfully."
    }))

async def main():
    async with websockets.serve(handler, "127.0.0.1", 8089):
        print("Mock training WebSocket running on ws://127.0.0.1:8089")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
```

### 6.2 Method B: Live Backend Integration
1. Ensure the FastAPI backend is running on `http://localhost:8080`.
2. Connect to the actual training router (`/ws/training` or `/retrain` pipeline).
3. Observe live output streaming directly from `ml_sidecar/train_model.py`.

---

## 7. Detailed Test Cases

### TC-TRN-01: Navigation & Route Registration Verification
**Objective:** Confirm that `/training` is registered in client routes, protected by `PrivateRoute`, and accessible from the Sidebar.

- **Preconditions:**
  - Web dashboard is running (`http://localhost:5173`).
  - User is authenticated with a valid JWT.
- **Steps:**
  1. Navigate to `http://localhost:5173/`.
  2. Inspect the left navigation sidebar.
  3. Verify the existence of a navigation item labeled **"Model Training"** or **"Training"** with an appropriate icon (e.g. `Brain`, `Cpu`, or `Activity` from `lucide-react`).
  4. Click the sidebar item.
  5. Inspect the address bar and page title.
  6. Open an incognito browser window (without authentication) and attempt to directly navigate to `http://localhost:5173/training`.
- **Expected Results:**
  - Sidebar contains the "Training" navigation link.
  - Clicking the link navigates seamlessly to `/training` without full page reload.
  - Active navigation state highlights the Training link in the sidebar (`bg-indigo-50 text-indigo-700` or dark mode equivalent).
  - Unauthenticated access redirects immediately to `/login`.

---

### TC-TRN-02: Initial Page Layout & Idle State Verification
**Objective:** Confirm all UI elements render in their default idle state prior to launching training.

- **Preconditions:**
  - User is navigated to `/training`.
  - No active training session is running.
- **Steps:**
  1. Inspect the main header and description.
  2. Locate the **"Start Training"** button:
     - Verify it is visible, clickable, and styled with primary action colors (e.g., `bg-indigo-600 hover:bg-indigo-700 text-white`).
     - Verify it does not display a loading spinner.
  3. Inspect the **Progress Bar** component:
     - Verify the bar width is 0% (`w-0` or `width: 0%`).
     - Verify percentage indicator text reads `"0%"` or `"Ready"`.
     - Inspect ARIA attributes: `role="progressbar"`, `aria-valuenow="0"`, `aria-valuemin="0"`, `aria-valuemax="100"`.
  4. Inspect the **Telemetry HUD / Metrics Cards**:
     - Status badge displays `"IDLE"` or `"READY"`.
     - Stage card displays `"--"` or `"Standby"`.
     - Data source card displays `"--"`.
     - Epoch counter displays `0 / 0` or `"--"`.
     - Current Loss card displays `"--"`.
  5. Inspect the **Terminal Console**:
     - Verify dark monospaced container styling (`bg-gray-900`, `text-green-400` or `text-gray-200`, `font-mono`).
     - Displays initial placeholder message (e.g. `Ready to train. Click "Start Training" to begin streaming logs.`).
     - No unhandled exceptions or NaN values appear in the DOM.
- **Expected Results:**
  - Clean, professional idle state rendered with zero UI glitches or console warnings.

---

### TC-TRN-03: "Start Training" Click & WebSocket Handshake
**Objective:** Verify that clicking "Start Training" triggers the training process and establishes the WebSocket stream.

- **Preconditions:**
  - User is on `/training`.
  - Browser DevTools open to **Network** (filter: `WS`) and **Console**.
- **Steps:**
  1. Click the **"Start Training"** button.
  2. Observe button state immediately upon click:
     - Verify button text changes to `"Initializing..."` or `"Training in progress..."`.
     - Verify a spinner icon appears.
     - Verify button is `disabled` (`cursor-not-allowed` / `opacity-50`) to prevent duplicate submissions.
  3. Inspect the **Network** tab:
     - Look for WebSocket upgrade request (e.g., `GET /ws/training` with `101 Switching Protocols`).
     - Verify headers include JWT token authorization (via subprotocol, query param, or initial auth frame).
  4. Inspect initial messages exchanged:
     - Look for incoming `connection_ack` or initial telemetry frame.
  5. Inspect Terminal Console:
     - Verify an initial connection log appears (e.g., `[INFO] Connected to telemetry stream. Training job initialized...`).
- **Expected Results:**
  - WebSocket connection opens with HTTP status `101 Switching Protocols`.
  - Single connection established (no duplicate or rapid socket reconnections).
  - Button transitions cleanly to disabled loading state.

---

### TC-TRN-04: Real-Time Progress Bar Advancement
**Objective:** Verify that incoming telemetry packets advance the progress bar smoothly and accurately from 0% towards 100%.

- **Preconditions:**
  - Training has started and WebSocket telemetry packets are arriving.
- **Steps:**
  1. Observe the progress bar fill element as telemetry arrives.
  2. Inspect the DOM element style / class:
     - Verify `width: X%` corresponds to the incoming `progress_pct` value.
     - Verify CSS transition class is applied (e.g., `transition-all duration-300 ease-out`) so the bar moves smoothly rather than jumping abruptly.
  3. Observe the numerical percentage label:
     - Confirm it updates monotonically: `10%` -> `25%` -> `50%` -> `75%` -> `100%`.
  4. Inspect accessibility attributes in the DOM:
     - `aria-valuenow` updates dynamically to match the current percentage.
  5. Verify stage color transitions (optional design enhancement):
     - Normal progress renders in brand/indigo/emerald colors.
- **Expected Results:**
  - Progress bar advances smoothly in direct synchrony with incoming WebSocket frames.
  - Percentage text does not flicker or wrap awkwardly.
  - The bar reaches exactly 100% upon completion.

---

### TC-TRN-05: Real-Time Telemetry HUD & Metrics Synchronization
**Objective:** Verify that stage, data source, epoch/step counters, and loss values update synchronously with telemetry packets.

- **Preconditions:**
  - WebSocket telemetry stream is actively receiving frames.
- **Steps:**
  1. Compare incoming WebSocket frame data in DevTools with the rendered cards on screen:
  2. **Stage Card:** Verify it reflects current phase (e.g., "Data Ingestion" -> "Feature Engineering" -> "Fitting RandomForest" -> "Validation").
  3. **Data Source Card:** Verify active source is displayed (e.g., `TimescaleDB (OHLCV)`, `Reddit Sentiment Cache`).
  4. **Epoch / Step Card:** Verify step and epoch counters update dynamically (e.g. `Epoch: 3 / 10 | Step: 120 / 400`).
  5. **Current Loss Card:** Verify loss values update dynamically and format cleanly to 4 decimal places (e.g. `0.0412`).
  6. **Elapsed Time Counter:** Verify counter increments every second during active training.
- **Expected Results:**
  - Every telemetry packet immediately updates the respective HUD metric card without lag.
  - Numbers format cleanly (no unhandled `NaN`, `undefined`, or overflow strings).

---

### TC-TRN-06: Terminal Console Auto-Scrolling Verification
**Objective:** Verify that the terminal window automatically scrolls to the bottom as new lines of telemetry log text arrive.

- **Preconditions:**
  - Telemetry is actively streaming log lines.
  - Number of log lines exceeds the vertical height of the terminal container (scrollbar is present).
- **Steps:**
  1. Do not touch mouse, trackpad, or keyboard.
  2. Observe the terminal console window as 20+ log lines arrive in succession.
  3. Verify that the most recently received log line is always completely visible at the bottom of the viewport.
  4. Open DevTools Console and execute the scroll verification check:
     ```javascript
     const term = document.querySelector('[data-testid="terminal-container"]') || document.querySelector('.terminal-window');
     console.log({
       scrollHeight: term.scrollHeight,
       scrollTop: term.scrollTop,
       clientHeight: term.clientHeight,
       isAtBottom: Math.abs(term.scrollHeight - term.clientHeight - term.scrollTop) < 5
     });
     ```
  5. Repeat the check across 5 consecutive log updates.
- **Expected Results:**
  - `isAtBottom` returns `true` (within a tolerance of 2–5 pixels) on every incoming log line.
  - Terminal scrolls downward automatically with zero jitter.
  - Log lines maintain monospaced font formatting, preserving timestamp, tag, and message indentation.

---

### TC-TRN-07: Auto-Scroll User Override (Sticky vs Free Scrolling)
**Objective:** Verify that manual upward scrolling pauses auto-scrolling, and scrolling back to bottom resumes it.

- **Preconditions:**
  - Training is running and terminal has accumulated over 50 lines of logs with continuous incoming messages.
- **Steps:**
  1. While logs are actively streaming, use the mouse wheel or trackpad to scroll upward by 20 lines to inspect an earlier log message.
  2. Stop scrolling and observe the viewport for 5 seconds while new messages continue to arrive.
  3. **Verify:** The viewport does **not** forcefully yank back to the bottom. The inspected text remains stable and readable.
  4. Look for an optional user helper badge (e.g. `"New logs below ↓"` or `"Scroll to bottom"` button).
  5. Now scroll the container all the way back to the bottom (or click the "Scroll to bottom" helper button).
  6. Observe subsequent incoming messages.
- **Expected Results:**
  - When the user scrolls away from the bottom (`scrollTop < scrollHeight - clientHeight - 20px`), auto-scroll is temporarily suspended.
  - When the user returns to the bottom (`scrollTop >= scrollHeight - clientHeight - 10px`), auto-scroll automatically re-engages and keeps new messages pinned.

---

### TC-TRN-08: Training Pipeline Normal Completion
**Objective:** Verify system behavior and UI transitions when the training pipeline reaches 100% completion.

- **Preconditions:**
  - Training session in progress, reaching its final epoch.
- **Steps:**
  1. Allow the mock or live training run to complete.
  2. Observe the WebSocket frame with `type: "completed"`.
  3. Inspect the UI elements post-completion:
     - Progress bar reaches `100%` and turns green (`bg-emerald-500`).
     - Telemetry HUD status badge switches to `"COMPLETED"`.
     - Final metrics banner surfaces summary statistics (Total Duration, Final Loss, Validation Score).
     - Terminal displays a clear success banner (e.g. `[SUCCESS] Retraining complete. Model hot-reloaded.`).
     - "Start Training" button re-enables or changes to `"Start New Run"` allowing subsequent sessions.
  4. Click "Start New Run":
     - Verify state resets properly (progress bar returns to 0%, terminal clears or adds divider, ready for next run).
- **Expected Results:**
  - Clean transition to completed state without hanging spinners or deadlocks.
  - Operators can immediately start a fresh run if desired.

---

### TC-TRN-09: Error Handling & Pipeline Failure Simulation
**Objective:** Verify UI error state handling when the backend training process fails or reports an exception.

- **Preconditions:**
  - User is on `/training`.
- **Steps:**
  1. Trigger a failing training run (e.g. via mock sending `type: "error"` or stopping backend database during ingestion).
  2. Click **"Start Training"**.
  3. Observe incoming WebSocket error message.
  4. Inspect the UI:
     - Progress bar stops advancing and switches to error styling (e.g., red `bg-rose-500`).
     - Telemetry HUD status badge switches to `"ERROR"` or `"FAILED"`.
     - An error alert card displays the failure reason (e.g., `"TimescaleDB connection timeout"`).
     - Terminal highlights the error in red text with timestamp and traceback.
     - "Start Training" button re-enables with label `"Retry Training"`.
  5. Click `"Retry Training"`.
- **Expected Results:**
  - Application does not crash, freeze, or throw unhandled white-screen errors.
  - Clear, human-readable error messages are surfaced to the operator.
  - Retry mechanism functions properly.

---

### TC-TRN-10: WebSocket Connection Drop & Reconnection Resilience
**Objective:** Verify application resilience if the network drops or the WebSocket disconnects mid-stream.

- **Preconditions:**
  - Training is running at ~50% progress.
- **Steps:**
  1. In DevTools Network tab, toggle throttling to **Offline**, or terminate the mock WebSocket server.
  2. Observe the terminal and status header:
     - Terminal appends `[WARN] Telemetry stream disconnected. Attempting reconnection...`.
     - Status indicator displays `"DISCONNECTED"` or `"RECONNECTING"`.
     - UI does not reset progress to 0% prematurely.
  3. In DevTools, toggle throttling back to **No throttling** (or restart the WebSocket server).
  4. Observe the socket behavior:
     - Client attempts automatic exponential backoff reconnection.
     - Once reconnected, terminal logs `[INFO] Telemetry stream re-established.`.
- **Expected Results:**
  - Network interruption is surfaced transparently without losing existing terminal history.
  - Automatic reconnection or a manual "Reconnect" action restores connectivity.

---

### TC-TRN-11: Theme Compatibility (Dark Mode vs Light Mode)
**Objective:** Ensure all training UI elements, especially terminal and progress bar, meet contrast standards in both themes.

- **Preconditions:**
  - Global theme toggle is available in topbar.
- **Steps:**
  1. Switch application to **Dark Mode** (`<html class="dark">`).
  2. Inspect `/training`:
     - Terminal background remains deep black/slate (`bg-gray-950` or `bg-gray-900`).
     - Terminal log text has high contrast (bright green `text-emerald-400`, cyan `text-cyan-300`, white `text-gray-100`, red `text-rose-400`).
     - Progress bar track (`bg-gray-800`) and fill (`bg-indigo-500` / `bg-emerald-500`) are distinct.
     - Metric cards use dark surface backgrounds (`dark:bg-gray-800 dark:border-gray-700`).
  3. Switch application to **Light Mode**.
  4. Inspect `/training`:
     - Terminal container maintains a dark code-editor theme or cleanly styled light-slate terminal with legible dark/colored monospaced text.
     - Progress bar track (`bg-gray-200`) and labels are crisp and readable.
- **Expected Results:**
  - All text meets WCAG AA 4.5:1 contrast standards across both themes.
  - No low-contrast grey-on-dark or dark-on-dark text artifacts.

---

### TC-TRN-12: Responsive Viewports & Layout Stability
**Objective:** Validate layout integrity on Desktop, Tablet, and Mobile screen sizes.

- **Preconditions:**
  - Browser responsive design mode open.
- **Steps:**
  1. Test at **Desktop** (1920x1080 and 1280x720):
     - Metric cards arrange in a 4-column or 2x2 grid.
     - Terminal window has comfortable vertical height (min `400px` - `500px`).
  2. Test at **Tablet** (768x1024):
     - Metric cards wrap into 2 columns.
     - Progress bar and terminal scale without clipping horizontal margins.
  3. Test at **Mobile** (375x667 and 412x915):
     - Metric cards stack vertically (1 column).
     - Terminal window maintains `max-h-[300px]` with internal scroll.
     - Log lines wrap or allow smooth horizontal scroll without breaking page width.
     - "Start Training" button spans full width (`w-full`) for easy touch accessibility.
- **Expected Results:**
  - Zero horizontal page overflow or layout breakage on mobile viewports.

---

## 8. Automated E2E Test Specification (Playwright Example)

For CI/CD and regression automation, the following Playwright test outlines the exact automated verification of the "Start Training" click, progress bar advance, and terminal auto-scroll:

```typescript
import { test, expect } from '@playwright/test';

test.describe('Phase 3 Stage 1: Training UI & Telemetry E2E', () => {
  test.beforeEach(async ({ page }) => {
    // Authenticate and navigate
    await page.goto('/login');
    await page.fill('input[type="email"]', 'test@test.com');
    await page.fill('input[type="password"]', 'test1234');
    await page.click('button[type="submit"]');
    await page.waitForURL('/');

    // Navigate to /training
    await page.goto('/training');
    await expect(page).toHaveURL('/training');
  });

  test('Start Training clicks, progress bar advances, and terminal auto-scrolls', async ({ page }) => {
    // 1. Verify initial Idle state
    const startButton = page.locator('button:has-text("Start Training")');
    const progressBar = page.locator('[role="progressbar"]');
    const terminal = page.locator('[data-testid="terminal-container"]');

    await expect(startButton).toBeVisible();
    await expect(startButton).toBeEnabled();
    await expect(progressBar).toHaveAttribute('aria-valuenow', '0');

    // 2. Click Start Training
    await startButton.click();

    // 3. Verify button transitions to disabled/loading
    await expect(startButton).toBeDisabled();

    // 4. Verify Progress Bar advances beyond 0%
    await expect(async () => {
      const val = await progressBar.getAttribute('aria-valuenow');
      expect(Number(val)).toBeGreaterThan(0);
    }).toPass({ timeout: 5000 });

    // 5. Verify Terminal receives logs and auto-scrolls to bottom
    await expect(async () => {
      const logLines = await terminal.locator('.terminal-line').count();
      expect(logLines).toBeGreaterThan(5);

      // Evaluate scroll position
      const scrollInfo = await terminal.evaluate((el) => ({
        scrollHeight: el.scrollHeight,
        clientHeight: el.clientHeight,
        scrollTop: el.scrollTop,
      }));

      // Verify scrollTop is pinned at or near the bottom
      const distanceToBottom = scrollInfo.scrollHeight - scrollInfo.clientHeight - scrollInfo.scrollTop;
      expect(distanceToBottom).toBeLessThanOrEqual(10);
    }).toPass({ timeout: 10000 });

    // 6. Verify Completion
    await expect(page.locator('text=Completed')).toBeVisible({ timeout: 30000 });
    await expect(progressBar).toHaveAttribute('aria-valuenow', '100');
  });
});
```

---

## 9. QA Sign-Off & Execution Checklist

| ID | Test Case Title | Target Area | Pass / Fail | Notes / Defects |
| :--- | :--- | :--- | :--- | :--- |
| **TC-TRN-01** | Navigation & Route Registration | Routing / Sidebar | [ ] | Verified `/training` route & auth |
| **TC-TRN-02** | Initial Page Layout & Idle State | UI Layout | [ ] | Button, 0% bar, idle HUD rendered |
| **TC-TRN-03** | "Start Training" Click & WS Handshake | WebSocket | [ ] | 101 status, disabled button spinner |
| **TC-TRN-04** | Real-Time Progress Bar Advancement | UI Animation | [ ] | Smooth width %, ARIA values |
| **TC-TRN-05** | Telemetry HUD & Metrics Sync | State Management | [ ] | Stage, source, epoch, loss sync |
| **TC-TRN-06** | Terminal Console Auto-Scrolling | DOM Scroll | [ ] | `scrollTop = scrollHeight` pinned |
| **TC-TRN-07** | Auto-Scroll User Override | UX Scroll Lock | [ ] | Pauses on scroll up, resumes at base |
| **TC-TRN-08** | Training Pipeline Normal Completion | Lifecycle | [ ] | 100% state, summary card, reset |
| **TC-TRN-09** | Error Handling & Failure Simulation | Error Boundary | [ ] | Red bar, traceback log, retry button |
| **TC-TRN-10** | WebSocket Disconnect & Reconnect | Network Resilience | [ ] | Graceful reconnect without state wipe|
| **TC-TRN-11** | Theme Compatibility (Dark & Light) | Accessibility / CSS | [ ] | WCAG AA contrast in terminal/cards |
| **TC-TRN-12** | Responsive Viewports & Layout | Mobile / Tablet | [ ] | No overflow, clean stacked layout |

---
*End of Test Plan: TP-FE-TRAINUI-001*
# Test Sweep Report

**Date:** 2026-09-17
**Directory:** `c:\marketpulse\MarketPulse\app`

## Overview
A full test sweep was attempted using `pytest`. Unfortunately, **zero tests passed** because the entire test suite failed at the collection phase. Pytest threw 12 distinct collection errors, preventing any individual test from actually executing.

## Failed Tests & Issues

### 1. Missing `SURREAL_URL` in Settings
- **Location:** `tests/integration/conftest.py`
- **Error:** `AttributeError: 'Settings' object has no attribute 'SURREAL_URL'`
- **Reason:** The integration test configuration attempts to parse `settings.SURREAL_URL`, but the `Settings` schema (likely in `app/core/config.py` or similar) does not define this attribute.
- **Estimated Fix:** Add `SURREAL_URL` to the Pydantic `Settings` model, or handle its absence gracefully in `conftest.py` if SurrealDB is optional.

### 2. Missing Python Packages
- **Locations:**
  - `tests/plugins/datasources/test_fred_plugin.py`
  - `tests/plugins/datasources/test_polygon_plugin.py`
  - `tests/plugins/datasources/test_reddit_plugin.py`
  - `tests/routers/test_data_stream.py`
- **Errors:**
  - `ModuleNotFoundError: No module named 'respx'`
  - `ModuleNotFoundError: No module named 'prometheus_fastapi_instrumentator'`
- **Reason:** The virtual environment (`.venv`) lacks these dependencies, which are required for mocking HTTP calls (`respx`) and instrumenting the FastAPI app.
- **Estimated Fix:** Add `respx` and `prometheus-fastapi-instrumentator` to the project's `requirements.txt` or `pyproject.toml` (likely under a `[dev]` or `[test]` group) and run `pip install`.

### 3. Missing / Ghost Database Modules
- **Locations:**
  - `tests/unit/db/astra/test_api_call_log.py`
  - `tests/unit/db/elastic/test_news_search.py`
  - `tests/unit/db/embedded/test_company_geo.py` (also attempts to import `db.elastic`)
  - `tests/unit/db/embedded/test_zodb_registry.py`
  - `tests/unit/db/influx/test_mention_count.py`
  - `tests/unit/db/surreal/test_cross_domain.py`
  - `tests/unit/db/surreal/test_sector.py`
- **Errors:** `ModuleNotFoundError` for `db.astra`, `db.elastic`, `db.embedded.zodb_registry`, `db.influx`, and `db.surreal`.
- **Reason:** The test files are trying to import database implementations that **do not exist** in the `app/db` directory. A check of `app/db` shows only `chroma`, `embedded`, `minio`, `mongo`, `neo4j`, `postgres`, and `valkey`. There are no folders for Astra, Elastic, Influx, or Surreal, and no `zodb_registry.py` in `embedded`.
- **Estimated Fix:** These appear to be orphaned tests, likely copied from another project or left over from architectural changes. If these databases are no longer part of the stack, these test files should be **deleted**. If they are planned for the future, the missing implementations must be written.

## Conclusion
To get the test suite running again:
1. Clean up or delete the ghost database tests.
2. Install the missing mock and observability packages.
3. Fix the `conftest.py` setting attribute. 

Once these collection errors are resolved, `pytest` will be able to discover and run the actual tests.
