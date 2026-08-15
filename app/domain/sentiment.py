from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass
class SentimentScore:
    source_type: Literal["reddit", "news", "combined"]
    score: float
    source_name: str | None = None
    article_count: int = 0
    post_count: int = 0
    recorded_at: datetime | None = None
    symbol: str | None = None

    def __post_init__(self):
        self.score = self.clamp(self.score, -1.0, 1.0)

    def clamp(self, value: float, min_val: float, max_val: float) -> float:
        if value < min_val:
            return min_val
        elif value > max_val:
            return max_val
        else:
            return value


@dataclass
class NewsArticle:
    symbol: str
    headline: str
    url: str
    source: str
    published_at: datetime
    finbert_score: float | None = None
    summary: str | None = None


@dataclass
class RedditPost:
    symbol: str
    subreddit: str
    title: str
    url: str
    score: int
    created_utc: datetime
    comment_count: int = 0
    vader_score: float | None = None
