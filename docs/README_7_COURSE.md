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
