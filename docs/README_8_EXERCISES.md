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
