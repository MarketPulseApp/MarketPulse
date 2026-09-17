"""
Connectivity smoke test — all Proxmox nodes at once.

Place at: app/tests/integration/test_all_nodes.py

Run this first before the per-node tests to get a quick health summary
of every service across both nodes:

    python -m pytest app/tests/integration/test_all_nodes.py -v

Each test does the absolute minimum to confirm the service is alive.
If a test fails here, the detailed per-node tests will tell you exactly what's wrong.
"""

from __future__ import annotations

import os

import pytest
from core.config import settings

from .conftest import (
    CHROMA_HOST,
    CHROMA_PORT,
    ELASTIC_HOST,
    ELASTIC_PORT,
    INFLUX_HOST,
    INFLUX_PORT,
    MINIO_HOST,
    MINIO_PORT,
    MONGO_HOST,
    MONGO_PORT,
    SURREAL_HOST,
    SURREAL_PORT,
    skip_chroma,
    skip_elastic,
    skip_influx,
    skip_minio,
    skip_mongo,
    skip_neo4j,
    skip_postgres,
    skip_surreal,
    skip_valkey,
)

# ── Node 1 — 192.168.1.123 ───────────────────────────────────────────────────


@pytest.mark.asyncio
@skip_postgres
async def test_smoke_postgres():
    """Node 1 · PostgreSQL 5432 — SELECT 1."""
    import asyncpg

    conn = await asyncpg.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database=settings.POSTGRES_DATABASE,
    )
    assert await conn.fetchval("SELECT 1") == 1
    await conn.close()


@pytest.mark.asyncio
@skip_valkey
async def test_smoke_valkey():
    """Node 1 · Valkey 6379 — PING."""
    import redis.asyncio as aioredis

    r = aioredis.Redis(
        host=settings.VALKEY_HOST,
        port=settings.VALKEY_PORT,
        password=settings.VALKEY_PASSWORD,
        decode_responses=True,
    )
    assert await r.ping() is True
    await r.aclose()


@pytest.mark.asyncio
@skip_chroma
async def test_smoke_chroma():
    """Node 1 · ChromaDB 8000 — heartbeat."""
    import chromadb

    client = await chromadb.AsyncHttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    result = await client.heartbeat()
    assert result is not None


@pytest.mark.asyncio
@skip_surreal
async def test_smoke_surreal():
    """Node 1 · SurrealDB 8001 — connect and authenticate."""
    from surrealdb import AsyncSurreal

    db = AsyncSurreal(f"ws://{SURREAL_HOST}:{SURREAL_PORT}/rpc")
    await db.connect()
    await db.signin(
        {
            "username": os.getenv("SURREAL_USER", "root"),
            "password": os.getenv("SURREAL_PASSWORD", ""),
        }
    )
    await db.close()


@skip_minio
def test_smoke_minio():
    """Node 1 · MinIO 9000 — list_buckets succeeds."""
    from minio import Minio

    client = Minio(
        f"{MINIO_HOST}:{MINIO_PORT}",
        access_key=os.getenv("MINIO_ACCESS_KEY", ""),
        secret_key=os.getenv("MINIO_SECRET_KEY", ""),
        secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
    )
    buckets = client.list_buckets()
    assert isinstance(buckets, list)


# ── Node 2 — 192.168.1.162 ───────────────────────────────────────────────────


@pytest.mark.asyncio
@skip_mongo
async def test_smoke_mongo():
    """Node 2 · MongoDB 27017 — ping."""
    from motor.motor_asyncio import AsyncIOMotorClient

    uri = (
        settings.MONGO_URL
        or f"mongodb://{os.getenv('MONGO_USER','')}:{os.getenv('MONGO_PASSWORD','')}@{MONGO_HOST}:{MONGO_PORT}/{os.getenv('MONGO_DB','marketpulse')}?authSource=admin"
    )
    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=3000)
    result = await client[os.getenv("MONGO_DB", "marketpulse")].command("ping")
    assert result.get("ok") == 1.0
    client.close()


@pytest.mark.asyncio
@skip_elastic
async def test_smoke_elastic():
    """Node 2 · Elasticsearch 9200 — cluster health."""
    from elasticsearch import AsyncElasticsearch

    url = settings.ELASTIC_URL or f"http://{ELASTIC_HOST}:{ELASTIC_PORT}"
    es = AsyncElasticsearch(
        url,
        basic_auth=(os.getenv("ELASTIC_USER", "elastic"), os.getenv("ELASTIC_PASSWORD", "")),
        request_timeout=5,
        verify_certs=False,
    )
    health = await es.cluster.health()
    assert health["status"] in ("green", "yellow")
    await es.close()


@pytest.mark.asyncio
@skip_influx
async def test_smoke_influx():
    """Node 2 · InfluxDB 8086 — ping."""
    from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync

    url = settings.INFLUX_URL or f"http://{INFLUX_HOST}:{INFLUX_PORT}"
    client = InfluxDBClientAsync(
        url=url,
        token=os.getenv("INFLUX_ADMIN_TOKEN", ""),
        org=os.getenv("INFLUX_ORG", "marketpulse"),
    )
    assert await client.ping() is True
    await client.close()


# ── Cloud ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@skip_neo4j
async def test_smoke_neo4j():
    """Neo4j AuraDB — verify_connectivity."""
    from neo4j import AsyncGraphDatabase

    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
    )
    await driver.verify_connectivity()
    await driver.close()
