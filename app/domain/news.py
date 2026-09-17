from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class NewsArticle:
    """A single news article ingested from any external source.

    Fields
    ------
    url
        Canonical URL — used as the unique key in MongoDB and Elasticsearch.
    headline
        The article title.
    symbol
        The primary ticker this article relates to (e.g. "AAPL").
    source
        Publisher or data-provider name (e.g. "reuters", "benzinga").
    published_at
        UTC publication timestamp.
    summary
        Optional body excerpt or auto-generated summary.
    vader_score
        VADER compound sentiment score in [-1, 1].  None until scored.
    finbert_score
        FinBERT sentiment score in [-1, 1].  None until scored.
    embedding
        Sentence-transformer vector used by ChromaDB for deduplication.
        Not persisted to MongoDB — computed on ingestion and passed
        directly to the ChromaDB repository.
    """

    url: str
    headline: str
    symbol: str
    source: str
    published_at: datetime
    summary: str | None = None
    vader_score: float | None = None
    finbert_score: float | None = None
    embedding: list[float] | None = field(default=None, repr=False)

    @property
    def is_scored(self) -> bool:
        """True when both sentiment scores have been computed."""
        return self.vader_score is not None and self.finbert_score is not None

    @property
    def composite_sentiment(self) -> float | None:
        """Average of VADER and FinBERT scores, or None if either is missing."""
        if self.vader_score is None or self.finbert_score is None:
            return None
        return (self.vader_score + self.finbert_score) / 2.0

    def to_mongo_doc(self) -> dict:
        """Return a dict safe for MongoDB insertion (excludes the embedding)."""
        return {
            "url": self.url,
            "headline": self.headline,
            "symbol": self.symbol,
            "source": self.source,
            "published_at": self.published_at,
            "summary": self.summary,
            "vader_score": self.vader_score,
            "finbert_score": self.finbert_score,
        }

    @classmethod
    def from_mongo_doc(cls, doc: dict) -> NewsArticle:
        """Construct from a raw MongoDB document (drops the _id field)."""
        doc = {k: v for k, v in doc.items() if k != "_id"}
        return cls(**doc)

    def to_elastic_doc(self) -> dict:
        """Return a dict safe for Elasticsearch indexing (excludes the embedding)."""
        return {
            "headline": self.headline,
            "summary": self.summary,
            "symbol": self.symbol,
            "source": self.source,
            "published_at": self.published_at.isoformat(),
            "vader_score": self.vader_score,
            "finbert_score": self.finbert_score,
        }
