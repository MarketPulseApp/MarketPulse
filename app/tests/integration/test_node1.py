"""
Integration tests — Node 1 (192.168.1.123)
Services: PostgreSQL/TimescaleDB, Valkey, ChromaDB, SurrealDB, MinIO
"""

from __future__ import annotations

import io
import os
from datetime import UTC, datetime, timedelta

import pytest
from core.config import settings

from .conftest import (
    CHROMA_HOST,
    CHROMA_PORT,
    MINIO_HOST,
    MINIO_PORT,
    SURREAL_HOST,
    SURREAL_PORT,
    skip_chroma,
    skip_minio,
    skip_postgres,
    skip_surreal,
    skip_valkey,
)

# ── MinIO bucket/key names must match [a-z0-9][a-z0-9-]{1,61}[a-z0-9] ──────
_TEST_BUCKET = "proxmox-int-test"
_TEST_KEY = "proxmox-test/ping.txt"
_TEST_DATA = b"MarketPulse Proxmox node1 integration test"


# ═══════════════════════════════════════════════════════════════════════════════
# PostgreSQL / TimescaleDB  (Node 1 · 192.168.1.123:5432)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
async def pg():
    import asyncpg

    conn = await asyncpg.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database=settings.POSTGRES_DATABASE,
    )
    yield conn
    await conn.close()


@pytest.mark.asyncio
@skip_postgres
async def test_postgres_connectivity(pg):
    """Node 1 PostgreSQL — basic SELECT 1."""
    assert await pg.fetchval("SELECT 1") == 1


@pytest.mark.asyncio
@skip_postgres
async def test_postgres_version(pg):
    """Node 1 PostgreSQL — server is running PostgreSQL 16."""
    version = await pg.fetchval("SELECT version()")
    assert "PostgreSQL" in version


@pytest.mark.asyncio
@skip_postgres
async def test_postgres_timescaledb_extension(pg):
    """Node 1 PostgreSQL — TimescaleDB extension is installed."""
    count = await pg.fetchval("SELECT COUNT(*) FROM pg_extension WHERE extname = 'timescaledb'")
    assert count == 1, "TimescaleDB not installed — run: CREATE EXTENSION timescaledb;"


@pytest.mark.asyncio
@skip_postgres
async def test_postgres_ohlcv_hypertable_exists(pg):
    """Node 1 PostgreSQL — ohlcv hypertable is registered."""
    count = await pg.fetchval(
        """
        SELECT COUNT(*)
        FROM timescaledb_information.hypertables
        WHERE hypertable_name = 'ohlcv'
    """
    )
    assert count >= 1, "ohlcv hypertable not found — has the schema been applied?"


@pytest.mark.asyncio
@skip_postgres
async def test_postgres_crud(pg):
    """Node 1 PostgreSQL — insert, read on a temp table."""
    await pg.execute("CREATE TEMP TABLE proxmox_test (id SERIAL PRIMARY KEY, val TEXT)")
    await pg.execute("INSERT INTO proxmox_test (val) VALUES ($1)", "node1_ok")
    row = await pg.fetchrow("SELECT val FROM proxmox_test WHERE val = $1", "node1_ok")
    assert row["val"] == "node1_ok"


@pytest.mark.asyncio
@skip_postgres
async def test_postgres_write_numeric(pg):
    """Node 1 PostgreSQL — NUMERIC(18,6) stores financial data precisely."""
    await pg.execute(
        """
        CREATE TEMP TABLE proxmox_ohlcv_test (
            ts     TIMESTAMPTZ NOT NULL,
            symbol TEXT        NOT NULL,
            close  NUMERIC(18,6)
        )
    """
    )
    await pg.execute(
        "INSERT INTO proxmox_ohlcv_test VALUES ($1, $2, $3)",
        datetime.now(UTC),
        "AAPL",
        185.25,
    )
    row = await pg.fetchrow("SELECT close FROM proxmox_ohlcv_test WHERE symbol = 'AAPL'")
    assert float(row["close"]) == pytest.approx(185.25)


# ═══════════════════════════════════════════════════════════════════════════════
# Valkey  (Node 1 · 192.168.1.123:6379)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
async def valkey():
    import redis.asyncio as aioredis

    client = aioredis.Redis(
        host=settings.VALKEY_HOST,
        port=settings.VALKEY_PORT,
        password=settings.VALKEY_PASSWORD,
        decode_responses=True,
    )
    yield client
    await client.aclose()


@pytest.mark.asyncio
@skip_valkey
async def test_valkey_ping(valkey):
    """Node 1 Valkey — PING returns PONG."""
    assert await valkey.ping() is True


@pytest.mark.asyncio
@skip_valkey
async def test_valkey_set_get_delete(valkey):
    """Node 1 Valkey — SET / GET / DEL round-trip."""
    key = "proxmox:test:basic"
    await valkey.set(key, "node1_valkey_ok")
    assert await valkey.get(key) == "node1_valkey_ok"
    await valkey.delete(key)
    assert await valkey.exists(key) == 0


@pytest.mark.asyncio
@skip_valkey
async def test_valkey_ttl(valkey):
    """Node 1 Valkey — TTL is set and countable."""
    key = "proxmox:test:ttl"
    await valkey.set(key, "expires", ex=120)
    ttl = await valkey.ttl(key)
    assert 0 < ttl <= 120
    await valkey.delete(key)


@pytest.mark.asyncio
@skip_valkey
async def test_valkey_incr_quota_pattern(valkey):
    """Node 1 Valkey — INCR pattern used for API quota tracking."""
    key = "proxmox:test:quota:newsapi"
    await valkey.delete(key)
    assert await valkey.incr(key) == 1
    assert await valkey.incr(key) == 2
    assert await valkey.incr(key) == 3
    await valkey.delete(key)


@pytest.mark.asyncio
@skip_valkey
async def test_valkey_feature_flag_pattern(valkey):
    """Node 1 Valkey — feature flag keys read correctly."""
    key = "proxmox:test:flag:datasource.newsapi"
    await valkey.set(key, "1")
    assert await valkey.get(key) == "1"
    await valkey.set(key, "0")
    assert await valkey.get(key) == "0"
    await valkey.delete(key)


@pytest.mark.asyncio
@skip_valkey
async def test_valkey_pubsub_channel_publish(valkey):
    """Node 1 Valkey — PUBLISH to price_updates channel succeeds."""
    count = await valkey.publish("pubsub:price_updates", '{"symbol":"AAPL","price":185.5}')
    assert isinstance(count, int)


@pytest.mark.asyncio
@skip_valkey
async def test_valkey_prediction_cache_pattern(valkey):
    """Node 1 Valkey — predict:latest:{symbol}:{horizon} key pattern works."""
    key = "proxmox:test:predict:latest:AAPL:1d"
    await valkey.set(key, '{"direction":"UP","confidence":0.82}', ex=14400)
    val = await valkey.get(key)
    assert "UP" in val
    await valkey.delete(key)


# ═══════════════════════════════════════════════════════════════════════════════
# ChromaDB  (Node 1 · 192.168.1.123:8000)
# Collection names must match: [a-zA-Z0-9][a-zA-Z0-9._-]{1,510}[a-zA-Z0-9]
# No leading underscores or hyphens.
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
async def chroma():
    import chromadb

    client = await chromadb.AsyncHttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    yield client
    try:
        await client.delete_collection("proxmox.test")
    except Exception:
        pass


@pytest.mark.asyncio
@skip_chroma
async def test_chroma_heartbeat(chroma):
    """Node 1 ChromaDB — heartbeat responds."""
    result = await chroma.heartbeat()
    assert result is not None


@pytest.mark.asyncio
@skip_chroma
async def test_chroma_create_collection(chroma):
    """Node 1 ChromaDB — collection can be created with cosine space."""
    col = await chroma.get_or_create_collection("proxmox.test", metadata={"hnsw:space": "cosine"})
    assert col.name == "proxmox.test"


@pytest.mark.asyncio
@skip_chroma
async def test_chroma_add_and_query(chroma):
    """Node 1 ChromaDB — add embeddings and find nearest neighbour."""
    col = await chroma.get_or_create_collection("proxmox.test", metadata={"hnsw:space": "cosine"})
    await col.add(
        ids=["near", "far"],
        embeddings=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
    )
    result = await col.query(query_embeddings=[[0.99, 0.01, 0.0]], n_results=1)
    assert result["ids"][0][0] == "near"


@pytest.mark.asyncio
@skip_chroma
async def test_chroma_dedup_threshold(chroma):
    """Node 1 ChromaDB — identical vector has distance < 0.05 (dedup threshold)."""
    col = await chroma.get_or_create_collection("proxmox.test", metadata={"hnsw:space": "cosine"})
    vec = [0.1, 0.2, 0.3, 0.4, 0.5]
    await col.add(ids=["original"], embeddings=[vec])
    result = await col.query(query_embeddings=[vec], n_results=1, include=["distances"])
    assert result["distances"][0][0] < 0.05


@pytest.mark.asyncio
@skip_chroma
async def test_chroma_count(chroma):
    """Node 1 ChromaDB — count() returns correct number after adds."""
    col = await chroma.get_or_create_collection("proxmox.test")
    await col.add(ids=["a", "b", "c"], embeddings=[[0.1] * 3, [0.2] * 3, [0.3] * 3])
    assert await col.count() >= 3


# ═══════════════════════════════════════════════════════════════════════════════
# SurrealDB  (Node 1 · 192.168.1.123:8001)
# surrealdb v2.0.0: AsyncSurreal() is a factory function returning
# AsyncWsSurrealConnection. NOT a context manager — call connect()/close()
# explicitly. signin() takes {"username": ..., "password": ...} keys.
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
async def surreal():
    from surrealdb import AsyncSurreal

    url = f"ws://{SURREAL_HOST}:{SURREAL_PORT}/rpc"
    db = AsyncSurreal(url)
    await db.connect()
    await db.signin(
        {
            "username": os.getenv("SURREAL_USER", "root"),
            "password": os.getenv("SURREAL_PASSWORD", ""),
        }
    )
    await db.use(
        os.getenv("SURREAL_NAMESPACE", "marketpulse"),
        os.getenv("SURREAL_DATABASE", "main"),
    )
    yield db
    try:
        await db.query("DELETE proxmox_test_ticker;")
    except Exception:
        pass
    await db.close()


@pytest.mark.asyncio
@skip_surreal
async def test_surreal_connect(surreal):
    """Node 1 SurrealDB — connection, auth, and namespace selection succeed."""
    result = await surreal.query("SELECT * FROM proxmox_test_ticker LIMIT 1;")
    assert isinstance(result, list)


@pytest.mark.asyncio
@skip_surreal
async def test_surreal_create_and_select(surreal):
    """Node 1 SurrealDB — CREATE and SELECT a record."""
    await surreal.query(
        "CREATE proxmox_test_ticker:AAPL SET symbol = 'AAPL', sector = 'Technology';"
    )
    result = await surreal.query("SELECT * FROM proxmox_test_ticker WHERE symbol = 'AAPL';")
    records = result[0]["result"]
    assert any(r["symbol"] == "AAPL" for r in records)


@pytest.mark.asyncio
@skip_surreal
async def test_surreal_update(surreal):
    """Node 1 SurrealDB — UPDATE modifies a field."""
    await surreal.query("CREATE proxmox_test_ticker:MSFT SET symbol = 'MSFT', active = false;")
    await surreal.query("UPDATE proxmox_test_ticker:MSFT SET active = true;")
    result = await surreal.query("SELECT active FROM proxmox_test_ticker:MSFT;")
    assert result[0]["result"][0]["active"] is True


@pytest.mark.asyncio
@skip_surreal
async def test_surreal_delete(surreal):
    """Node 1 SurrealDB — DELETE removes a record."""
    await surreal.query("CREATE proxmox_test_ticker:DEL SET symbol = 'DEL';")
    await surreal.query("DELETE proxmox_test_ticker:DEL;")
    result = await surreal.query("SELECT * FROM proxmox_test_ticker WHERE symbol = 'DEL';")
    assert result[0]["result"] == []


# ═══════════════════════════════════════════════════════════════════════════════
# MinIO  (Node 1 · 192.168.1.123:9000)
# Bucket names: 3-63 chars, lowercase letters, numbers, hyphens only.
# Must start/end with a letter or number (no underscores, no leading hyphens).
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def minio():
    from minio import Minio

    access = os.getenv("MINIO_ACCESS_KEY", "")
    secret = os.getenv("MINIO_SECRET_KEY", "")
    secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
    client = Minio(
        f"{MINIO_HOST}:{MINIO_PORT}", access_key=access, secret_key=secret, secure=secure
    )
    if not client.bucket_exists(_TEST_BUCKET):
        client.make_bucket(_TEST_BUCKET)
    yield client
    try:
        client.remove_object(_TEST_BUCKET, _TEST_KEY)
    except Exception:
        pass


@skip_minio
def test_minio_connectivity(minio):
    """Node 1 MinIO — list_buckets() succeeds."""
    assert isinstance(minio.list_buckets(), list)


@skip_minio
def test_minio_upload_download(minio):
    """Node 1 MinIO — upload bytes and download them back intact."""
    minio.put_object(
        _TEST_BUCKET,
        _TEST_KEY,
        io.BytesIO(_TEST_DATA),
        length=len(_TEST_DATA),
        content_type="text/plain",
    )
    response = minio.get_object(_TEST_BUCKET, _TEST_KEY)
    try:
        data = response.read()
    finally:
        response.close()
        response.release_conn()
    assert data == _TEST_DATA


@skip_minio
def test_minio_presigned_url(minio):
    """Node 1 MinIO — presigned GET URL is a valid http string."""
    minio.put_object(
        _TEST_BUCKET,
        _TEST_KEY,
        io.BytesIO(_TEST_DATA),
        length=len(_TEST_DATA),
    )
    url = minio.presigned_get_object(_TEST_BUCKET, _TEST_KEY, expires=timedelta(hours=1))
    assert url.startswith("http") and _TEST_KEY in url


@skip_minio
def test_minio_delete(minio):
    """Node 1 MinIO — deleted object no longer listed."""
    minio.put_object(
        _TEST_BUCKET,
        _TEST_KEY,
        io.BytesIO(_TEST_DATA),
        length=len(_TEST_DATA),
    )
    minio.remove_object(_TEST_BUCKET, _TEST_KEY)
    keys = [obj.object_name for obj in minio.list_objects(_TEST_BUCKET)]
    assert _TEST_KEY not in keys
