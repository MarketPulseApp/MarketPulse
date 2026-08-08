# exercises/ex02_news_vader.py
"""
Fetch AAPL news and VADER-score each headline.
Requires: NEWSAPI_KEY in environment.
"""

import os
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

api_key = os.environ.get("NEWSAPI_KEY")
if not api_key:
    raise ValueError("Set NEWSAPI_KEY environment variable. Get a free key at newsapi.org")

# ── Step 1: Fetch news ────────────────────────────────────────────────────────
url = "https://newsapi.org/v2/everything"
params = {
    "q": "AAPL OR Apple stock",
    "sortBy": "publishedAt",
    "language": "en",
    "pageSize": 20,
    "apiKey": api_key,
}
response = requests.get(url, params=params, timeout=10)
response.raise_for_status()
articles = response.json()["articles"]
print(f"Fetched {len(articles)} articles\n")

# ── Step 2: VADER score each headline ────────────────────────────────────────
analyzer = SentimentIntensityAnalyzer()

scored = []
for article in articles:
    headline = article["title"] or ""
    description = article.get("description") or ""
    text = f"{headline}. {description}"
    scores = analyzer.polarity_scores(text)
    scored.append({
        "headline": headline[:80],
        "compound": scores["compound"],
        "pos": scores["pos"],
        "neg": scores["neg"],
        "neu": scores["neu"],
    })

# ── Step 3: Display results ──────────────────────────────────────────────────
scored.sort(key=lambda x: x["compound"], reverse=True)

print("=== TOP 3 MOST BULLISH ===")
for item in scored[:3]:
    sentiment = "BULL" if item["compound"] > 0.05 else "NEUTRAL"
    print(f"  [{item['compound']:+.3f}] {item['headline']}")

print("\n=== TOP 3 MOST BEARISH ===")
for item in scored[-3:]:
    print(f"  [{item['compound']:+.3f}] {item['headline']}")

# ── Step 4: Aggregate ────────────────────────────────────────────────────────
compounds = [s["compound"] for s in scored]
avg_sentiment = sum(compounds) / len(compounds)
print(f"\nAggregate AAPL news sentiment: {avg_sentiment:+.3f}")
if avg_sentiment > 0.05:
    print("Overall tone: BULLISH")
elif avg_sentiment < -0.05:
    print("Overall tone: BEARISH")
else:
    print("Overall tone: NEUTRAL")