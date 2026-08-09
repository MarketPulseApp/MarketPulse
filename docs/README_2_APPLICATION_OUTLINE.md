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
