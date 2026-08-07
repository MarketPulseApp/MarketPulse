// MarketPulse MongoDB Init Script
// Save to: C:\marketpulse\init\mongo\init.js
// This runs automatically on first container start.

db = db.getSiblingDB('marketpulse');

// ── News Articles ──────────────────────────────────────────────────────────────
db.createCollection('news_articles');
db.news_articles.createIndex({ ticker_symbols: 1, published_at: -1 });
db.news_articles.createIndex({ source: 1, published_at: -1 });
db.news_articles.createIndex({ url: 1 }, { unique: true });
// 90-day TTL: articles expire automatically
db.news_articles.createIndex({ published_at: 1 }, { expireAfterSeconds: 7776000 });

// ── Reddit Posts ───────────────────────────────────────────────────────────────
db.createCollection('reddit_posts');
db.reddit_posts.createIndex({ ticker_symbols: 1, created_utc: -1 });
db.reddit_posts.createIndex({ subreddit: 1, created_utc: -1 });
db.reddit_posts.createIndex({ post_id: 1 }, { unique: true });
// 90-day TTL
db.reddit_posts.createIndex({ created_utc: 1 }, { expireAfterSeconds: 7776000 });

// ── SEC Filings ────────────────────────────────────────────────────────────────
db.createCollection('sec_filings');
db.sec_filings.createIndex({ symbol: 1, filed_at: -1 });
db.sec_filings.createIndex({ accession_number: 1 }, { unique: true });
db.sec_filings.createIndex({ insider_name: 1 });

// ── Prediction Explanations (SHAP) ────────────────────────────────────────────
db.createCollection('prediction_explanations');
db.prediction_explanations.createIndex({ symbol: 1, horizon: 1, time: -1 });
// Keep SHAP explanations for 1 year
db.prediction_explanations.createIndex({ time: 1 }, { expireAfterSeconds: 31536000 });

print('MarketPulse MongoDB collections and indexes created.');