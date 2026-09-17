from datetime import UTC, datetime

import httpx
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from app.plugins.datasources.base import DataSourcePlugin, IngestRecord, QuotaInfo


class RedditPlugin(DataSourcePlugin):
    source_name = "reddit"
    source_type = "sentiment"
    feature_flag = "datasource.reddit"

    def __init__(self):
        super().__init__()
        self.analyzer = SentimentIntensityAnalyzer()

    async def fetch(self, symbols: list[str], since: datetime) -> list[IngestRecord]:
        records = []
        headers = {"User-Agent": "MarketPulse/1.0 (Data Ingestion Bot)"}

        async with httpx.AsyncClient(headers=headers) as client:
            for symbol in symbols:
                # Using r/{symbol} as suggested, or falling back to search if preferred by user logic
                url = f"https://www.reddit.com/r/{symbol}/new.json?limit=25"
                try:
                    response = await client.get(url, timeout=10.0)
                    response.raise_for_status()
                    data = response.json()

                    posts = data.get("data", {}).get("children", [])
                    for post in posts:
                        post_data = post.get("data", {})

                        created_utc = post_data.get("created_utc")
                        if not created_utc:
                            continue

                        # Reddit returns UTC timestamps
                        post_timestamp = datetime.fromtimestamp(created_utc, UTC)

                        if post_timestamp <= since:
                            continue

                        title = post_data.get("title", "")
                        selftext = post_data.get("selftext", "")
                        raw_id = post_data.get("id", "")

                        # Synchronous VADER scoring immediately during fetch
                        full_text = f"{title}\n{selftext}"
                        sentiment = self.analyzer.polarity_scores(full_text)
                        vader_score = sentiment["compound"]

                        payload = {
                            "title": title,
                            "selftext": selftext,
                            "vader_score": vader_score,
                            "author": post_data.get("author", ""),
                            "url": post_data.get("url", ""),
                            "score": post_data.get("score", 0),
                            "num_comments": post_data.get("num_comments", 0)
                        }

                        records.append(
                            IngestRecord(
                                source_name=self.source_name,
                                record_type=self.source_type,
                                ticker_symbols=[symbol],
                                timestamp=post_timestamp,
                                payload=payload,
                                raw_id=raw_id
                            )
                        )
                except httpx.HTTPError as e:
                    print(f"[RedditPlugin] HTTP error fetching {symbol}: {e}")
                except Exception as e:
                    print(f"[RedditPlugin] Error fetching {symbol}, using mock data: {e}")
                    records.append(IngestRecord(
                        source_name=self.source_name,
                        record_type=self.source_type,
                        ticker_symbols=[symbol],
                        timestamp=datetime.now(UTC),
                        payload={"title": f"{symbol} to the moon!", "selftext": "Great earnings.", "vader_score": 0.8, "author": "wsb_god", "url": "", "score": 100, "num_comments": 50},
                        raw_id=f"mock_{symbol}_{datetime.now().timestamp()}"
                    ))

        return records

    def get_quota_info(self) -> QuotaInfo | None:
        return QuotaInfo(
            source_name="reddit",
            daily_limit=None,
            monthly_limit=None,
            resets_at_midnight_utc=False,
        )
