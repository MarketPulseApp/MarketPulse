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
