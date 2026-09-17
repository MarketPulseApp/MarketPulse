import re
from datetime import UTC, datetime

import pytest
import respx
from httpx import Response

from app.plugins.datasources.base import IngestRecord
from app.plugins.datasources.reddit_plugin import RedditPlugin


@pytest.fixture
def mock_reddit_response():
    return {
        "data": {
            "children": [
                {
                    "data": {
                        "id": "12345",
                        "title": "AAPL is going to the moon!",
                        "selftext": "Apple is doing great this quarter.",
                        "created_utc": 1694900000.0,
                        "subreddit": "wallstreetbets",
                        "author": "stonk_guy",
                    }
                },
                {
                    "data": {
                        "id": "67890",
                        "title": "MSFT bears are wrong",
                        "selftext": "Microsoft cloud growth is insane.",
                        "created_utc": 1694900100.0,
                        "subreddit": "investing",
                        "author": "bull_guy",
                    }
                },
            ]
        }
    }


@pytest.mark.asyncio
@respx.mock
async def test_reddit_plugin_fetch_maps_to_ingest_record(mock_reddit_response):
    """
    Test that the Reddit plugin maps its external API payloads to the IngestRecord
    dataclass correctly, and that VADER scoring runs synchronously.
    """
    plugin = RedditPlugin()

    # We intercept any reddit.com API calls.
    # Note: If the plugin uses a specific endpoint like https://oauth.reddit.com/subreddits/search,
    # this regex catches it.
    route = respx.get(re.compile(r"https://.*reddit\.com/.*")).mock(
        return_value=Response(200, json=mock_reddit_response)
    )

    symbols = ["AAPL", "MSFT"]
    since = datetime(2023, 9, 16, tzinfo=UTC)

    # Note: Since the plugin is unimplemented, this will currently raise NotImplementedError.
    # We are writing the test to guide implementation (TDD).
    records = await plugin.fetch(symbols, since)

    # Verify that the plugin made an HTTP request
    assert route.called

    assert len(records) == 2

    # Check AAPL record
    aapl_record = records[0]
    assert isinstance(aapl_record, IngestRecord)
    assert aapl_record.source_name == "reddit"
    assert aapl_record.record_type == "sentiment"
    assert aapl_record.ticker_symbols == ["AAPL"]
    assert aapl_record.raw_id == "12345"
    assert aapl_record.timestamp == datetime.fromtimestamp(1694900000.0, UTC)

    # Verify payload contains necessary original data
    assert aapl_record.payload["title"] == "AAPL is going to the moon!"
    assert aapl_record.payload["selftext"] == "Apple is doing great this quarter."
    assert aapl_record.payload["author"] == "stonk_guy"
    assert aapl_record.payload["subreddit"] == "wallstreetbets"

    # Verify VADER scoring ran synchronously and is in the payload
    assert "vader_score" in aapl_record.payload
    assert isinstance(aapl_record.payload["vader_score"], dict)
    assert "compound" in aapl_record.payload["vader_score"]
    # The title "AAPL is going to the moon!" is very positive, so compound should be > 0.
    assert aapl_record.payload["vader_score"]["compound"] > 0.0

    # Check MSFT record
    msft_record = records[1]
    assert isinstance(msft_record, IngestRecord)
    assert msft_record.source_name == "reddit"
    assert msft_record.record_type == "sentiment"
    assert msft_record.ticker_symbols == ["MSFT"]
    assert msft_record.raw_id == "67890"
    assert msft_record.timestamp == datetime.fromtimestamp(1694900100.0, UTC)

    assert msft_record.payload["title"] == "MSFT bears are wrong"
    assert "vader_score" in msft_record.payload
    assert msft_record.payload["vader_score"]["compound"] != 0.0
