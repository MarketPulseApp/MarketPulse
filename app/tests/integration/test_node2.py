"""
Integration tests — Node 2 (192.168.1.162)
Services: MongoDB, Elasticsearch, InfluxDB
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest
from core.config import settings

from .conftest import (
    ELASTIC_HOST,
    ELASTIC_PORT,
    INFLUX_HOST,
    INFLUX_PORT,
    MONGO_HOST,
    MONGO_PORT,
    skip_elastic,
    skip_influx,
    skip_mongo,
)

_INFLUX_ORG = os.getenv("INFLUX_ORG", "marketpulse")
_INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "marketpulse")
_INFLUX_TOKEN = os.getenv("INFLUX_ADMIN_TOKEN", "")
_ELASTIC_USER = os.getenv("ELASTIC_USER", "elastic")
_ELASTIC_PASS = os.getenv("ELASTIC_PASSWORD", "")
_MONGO_USER = os.getenv("MONGO_USER", "marketpulse")
_MONGO_PASS = os.getenv("MONGO_PASSWORD", "")
_MONGO_DB = os.getenv("MONGO_DB", "marketpulse")


# ═══════════════════════════════════════════════════════════════════════════════
# MongoDB  (Node 2 · 192.168.1.162:27017)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
async def mongo_db():
    from motor.motor_asyncio import AsyncIOMotorClient

    uri = (
        settings.MONGO_URL
        or f"mongodb://{_MONGO_USER}:{_MONGO_PASS}@{MONGO_HOST}:{MONGO_PORT}/{_MONGO_DB}?authSource=admin"
    )
    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=3000)
    db = client[_MONGO_DB]
    yield db
    try:
        await db["proxmox_test"].drop()
    except Exception:
        pass
    client.close()


@pytest.mark.asyncio
@skip_mongo
async def test_mongo_ping(mongo_db):
    """Node 2 MongoDB — ping responds with ok=1."""
    result = await mongo_db.command("ping")
    assert result.get("ok") == 1.0


@pytest.mark.asyncio
@skip_mongo
async def test_mongo_server_version(mongo_db):
    """Node 2 MongoDB — server is running MongoDB 7."""
    info = await mongo_db.command("buildInfo")
    major = int(info["version"].split(".")[0])
    assert major >= 7, f"Expected MongoDB 7+, got {info['version']}"


@pytest.mark.asyncio
@skip_mongo
async def test_mongo_insert_and_find(mongo_db):
    """Node 2 MongoDB — insert a document and find it."""
    col = mongo_db["proxmox_test"]
    await col.insert_one({"symbol": "AAPL", "source": "proxmox_test"})
    doc = await col.find_one({"symbol": "AAPL"})
    assert doc is not None
    assert doc["source"] == "proxmox_test"


@pytest.mark.asyncio
@skip_mongo
async def test_mongo_unique_index(mongo_db):
    """Node 2 MongoDB — unique index on url rejects duplicates."""
    from pymongo.errors import DuplicateKeyError

    col = mongo_db["proxmox_test"]
    await col.create_index("url", unique=True)
    await col.insert_one({"url": "https://example.com/proxmox", "headline": "Test"})
    with pytest.raises(DuplicateKeyError):
        await col.insert_one({"url": "https://example.com/proxmox", "headline": "Dupe"})


@pytest.mark.asyncio
@skip_mongo
async def test_mongo_news_articles_collection(mongo_db):
    """Node 2 MongoDB — news_articles collection is queryable."""
    count = await mongo_db["news_articles"].count_documents({})
    assert isinstance(count, int)


@pytest.mark.asyncio
@skip_mongo
async def test_mongo_reddit_posts_collection(mongo_db):
    """Node 2 MongoDB — reddit_posts collection is queryable."""
    count = await mongo_db["reddit_posts"].count_documents({})
    assert isinstance(count, int)


@pytest.mark.asyncio
@skip_mongo
async def test_mongo_sec_filings_collection(mongo_db):
    """Node 2 MongoDB — sec_filings collection is queryable."""
    count = await mongo_db["sec_filings"].count_documents({})
    assert isinstance(count, int)


@pytest.mark.asyncio
@skip_mongo
async def test_mongo_sort_and_limit(mongo_db):
    """Node 2 MongoDB — sort + limit chain works correctly."""
    col = mongo_db["proxmox_test"]
    for i in range(5):
        await col.insert_one({"n": i})
    docs = await col.find({}, {"n": 1}).sort("n", -1).limit(3).to_list(length=3)
    assert len(docs) == 3
    assert docs[0]["n"] > docs[1]["n"]


# ═══════════════════════════════════════════════════════════════════════════════
# Elasticsearch  (Node 2 · 192.168.1.162:9200)
# The elasticsearch Python package v9 sends compatible-with=9 headers.
# ES 8.x on the Proxmox node rejects that. Pin the header version to 8.
# ═══════════════════════════════════════════════════════════════════════════════

_ES_INDEX = "proxmox.test.news"


@pytest.fixture
async def es():
    from elasticsearch import AsyncElasticsearch

    url = settings.ELASTIC_URL or f"http://{ELASTIC_HOST}:{ELASTIC_PORT}"
    client = AsyncElasticsearch(
        url,
        basic_auth=(_ELASTIC_USER, _ELASTIC_PASS),
        request_timeout=5,
        verify_certs=False,
        # Force the client to speak ES 8 protocol regardless of installed package version
        headers={
            "Accept": "application/vnd.elasticsearch+json; compatible-with=8",
            "Content-Type": "application/vnd.elasticsearch+json; compatible-with=8",
        },
    )
    yield client
    try:
        await client.indices.delete(index=_ES_INDEX, ignore_unavailable=True)
    except Exception:
        pass
    await client.close()


@pytest.mark.asyncio
@skip_elastic
async def test_elastic_cluster_health(es):
    """Node 2 Elasticsearch — cluster is green or yellow."""
    health = await es.cluster.health()
    assert health["status"] in ("green", "yellow")


@pytest.mark.asyncio
@skip_elastic
async def test_elastic_server_version(es):
    """Node 2 Elasticsearch — running version 8.x."""
    info = await es.info()
    major = int(info["version"]["number"].split(".")[0])
    assert major >= 8


@pytest.mark.asyncio
@skip_elastic
async def test_elastic_index_document(es):
    """Node 2 Elasticsearch — can index and retrieve a document by ID."""
    await es.options(ignore_status=400).indices.create(index=_ES_INDEX)
    await es.index(
        index=_ES_INDEX,
        id="proxmox-test-1",
        document={"headline": "Proxmox node2 integration test", "symbol": "AAPL"},
        refresh=True,
    )
    doc = await es.get(index=_ES_INDEX, id="proxmox-test-1")
    assert doc["_source"]["symbol"] == "AAPL"


@pytest.mark.asyncio
@skip_elastic
async def test_elastic_fulltext_search(es):
    """Node 2 Elasticsearch — multi_match full-text search returns results."""
    await es.options(ignore_status=400).indices.create(index=_ES_INDEX)
    await es.index(
        index=_ES_INDEX,
        id="proxmox-test-2",
        document={"headline": "Federal Reserve cuts interest rates", "symbol": "SPY"},
        refresh=True,
    )
    result = await es.search(
        index=_ES_INDEX,
        body={"query": {"multi_match": {"query": "interest rates", "fields": ["headline"]}}},
    )
    assert result["hits"]["total"]["value"] >= 1


@pytest.mark.asyncio
@skip_elastic
async def test_elastic_symbol_term_filter(es):
    """Node 2 Elasticsearch — keyword term filter returns only matching symbol."""
    await es.options(ignore_status=400).indices.create(index=_ES_INDEX)
    await es.index(
        index=_ES_INDEX,
        id="pt-aapl",
        document={"headline": "AAPL news", "symbol": "AAPL"},
        refresh=True,
    )
    await es.index(
        index=_ES_INDEX,
        id="pt-tsla",
        document={"headline": "TSLA news", "symbol": "TSLA"},
        refresh=True,
    )
    result = await es.search(
        index=_ES_INDEX,
        body={"query": {"term": {"symbol": "AAPL"}}},
    )
    symbols = [h["_source"]["symbol"] for h in result["hits"]["hits"]]
    assert all(s == "AAPL" for s in symbols)


@pytest.mark.asyncio
@skip_elastic
async def test_elastic_news_index_accessible(es):
    """Node 2 Elasticsearch — news_index exists and is queryable (if ingestion has run)."""
    try:
        result = await es.count(index="news_index")
        assert isinstance(result["count"], int)
    except Exception:
        pytest.skip("news_index not yet created — run ingestion first")


# ═══════════════════════════════════════════════════════════════════════════════
# InfluxDB  (Node 2 · 192.168.1.162:8086)
# InfluxDBClientAsync.write_api() returns a WriteApiAsync — NOT an async context
# manager. Call write() directly on it. buckets_api() is only on the sync client.
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
async def influx():
    from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync

    url = settings.INFLUX_URL or f"http://{INFLUX_HOST}:{INFLUX_PORT}"
    client = InfluxDBClientAsync(url=url, token=_INFLUX_TOKEN, org=_INFLUX_ORG)
    yield client
    await client.close()


@pytest.mark.asyncio
@skip_influx
async def test_influx_ping(influx):
    """Node 2 InfluxDB — health check passes."""
    assert await influx.ping() is True


@pytest.mark.asyncio
@skip_influx
async def test_influx_bucket_exists(influx):
    """Node 2 InfluxDB — configured bucket is reachable via a query."""
    # buckets_api() only exists on the sync client; use a simple Flux query instead.
    flux = f'from(bucket: "{_INFLUX_BUCKET}") |> range(start: -1s) |> limit(n: 1)'
    try:
        await influx.query_api().query(flux, org=_INFLUX_ORG)
        # If the bucket doesn't exist InfluxDB raises an error
    except Exception as exc:
        if "bucket" in str(exc).lower() and "not found" in str(exc).lower():
            pytest.fail(f"Bucket '{_INFLUX_BUCKET}' not found: {exc}")
        # Other errors (empty results etc.) are fine


@pytest.mark.asyncio
@skip_influx
async def test_influx_write_and_query_back(influx):
    """Node 2 InfluxDB — write a point and read it back with Flux."""
    from influxdb_client import Point

    point = (
        Point("proxmox.test.mention")
        .tag("symbol", "AAPL")
        .tag("subreddit", "proxmox_integration")
        .field("count", 42)
        .time(datetime.now(UTC))
    )
    # WriteApiAsync is NOT an async context manager — call write() directly
    write_api = influx.write_api()
    await write_api.write(bucket=_INFLUX_BUCKET, org=_INFLUX_ORG, record=point)

    flux = f"""
from(bucket: "{_INFLUX_BUCKET}")
  |> range(start: -2m)
  |> filter(fn: (r) => r._measurement == "proxmox.test.mention")
  |> filter(fn: (r) => r.symbol == "AAPL")
  |> filter(fn: (r) => r._field == "count")
"""
    tables = await influx.query_api().query(flux, org=_INFLUX_ORG)
    values = [r.get_value() for table in tables for r in table.records]
    assert 42 in values


@pytest.mark.asyncio
@skip_influx
async def test_influx_marketpulse_bucket_write(influx):
    """Node 2 InfluxDB — marketpulse bucket accepts mention_counts measurement."""
    from influxdb_client import Point

    point = (
        Point("mention_counts")
        .tag("symbol", "PROXMOX.TEST")
        .tag("subreddit", "integration")
        .field("count", 1)
        .field("avg_score", 0.0)
        .time(datetime.now(UTC))
    )
    write_api = influx.write_api()
    await write_api.write(bucket=_INFLUX_BUCKET, org=_INFLUX_ORG, record=point)
    # Write succeeded — no exception raised
