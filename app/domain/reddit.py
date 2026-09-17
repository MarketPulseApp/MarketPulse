from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class RedditPost:
    """A single Reddit post collected from a finance subreddit.

    Fields
    ------
    post_id
        Reddit's native post ID (the t3_ prefix is stripped).
        Used as the unique key in MongoDB.
    subreddit
        Subreddit name without the r/ prefix, e.g. "wallstreetbets".
    title
        Post title.
    body
        Post body text (selftext). Empty string for link posts.
    symbol
        The primary ticker this post was matched to.
    score
        Reddit upvote score at collection time.
    created_at
        UTC timestamp from the Reddit API (converted from Unix epoch).
    url
        Permalink to the post, e.g. "https://reddit.com/r/.../comments/..."
    author
        Redditor username. Stored for deduplication and spam filtering.
    flair
        Post flair text, e.g. "DD", "Meme", "Discussion". None if unflaired.
    num_comments
        Comment count at collection time.
    sentiment_score
        VADER or FinBERT sentiment score in [-1, 1]. None until scored.
    embedding
        Sentence-transformer vector for ChromaDB clustering.
        Not persisted to MongoDB — passed directly to the ChromaDB repo.
    """

    post_id: str
    subreddit: str
    title: str
    body: str
    symbol: str
    score: int
    created_at: datetime
    url: str = ""
    author: str = ""
    flair: str | None = None
    num_comments: int = 0
    sentiment_score: float | None = None
    embedding: list[float] | None = field(default=None, repr=False)

    # ── convenience ─────────────────────────────────────────────────────────

    @property
    def full_text(self) -> str:
        """Title + body concatenated for NLP processing."""
        return f"{self.title} {self.body}".strip()

    @property
    def is_scored(self) -> bool:
        return self.sentiment_score is not None

    @property
    def is_bullish(self) -> bool | None:
        """True if scored and sentiment > 0.05, False if < -0.05, else None."""
        if self.sentiment_score is None:
            return None
        if self.sentiment_score > 0.05:
            return True
        if self.sentiment_score < -0.05:
            return False
        return None  # neutral

    def to_mongo_doc(self) -> dict:
        """Return a dict safe for MongoDB insertion (excludes embedding)."""
        return {
            "post_id": self.post_id,
            "subreddit": self.subreddit,
            "title": self.title,
            "body": self.body,
            "symbol": self.symbol,
            "score": self.score,
            "created_at": self.created_at,
            "url": self.url,
            "author": self.author,
            "flair": self.flair,
            "num_comments": self.num_comments,
            "sentiment_score": self.sentiment_score,
        }

    @classmethod
    def from_mongo_doc(cls, doc: dict) -> RedditPost:
        doc = {k: v for k, v in doc.items() if k != "_id"}
        return cls(**doc)

    @classmethod
    def from_praw(cls, submission, symbol: str) -> RedditPost:
        """Construct from a PRAW Submission object.

        Usage:
            import praw
            reddit = praw.Reddit(...)
            for sub in reddit.subreddit("wallstreetbets").new(limit=100):
                post = RedditPost.from_praw(sub, symbol="AAPL")
        """
        return cls(
            post_id=submission.id,
            subreddit=str(submission.subreddit),
            title=submission.title,
            body=submission.selftext or "",
            symbol=symbol,
            score=submission.score,
            created_at=datetime.fromtimestamp(submission.created_utc, tz=UTC),
            url=f"https://reddit.com{submission.permalink}",
            author=str(submission.author) if submission.author else "[deleted]",
            flair=submission.link_flair_text,
            num_comments=submission.num_comments,
        )
