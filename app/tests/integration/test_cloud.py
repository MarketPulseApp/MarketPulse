"""
Integration tests — Cloud services (Neo4j AuraDB, DataStax Astra)
These are external services — skipped if credentials are not set in .env.

Place at: app/tests/integration/test_cloud.py

Run with:
    python -m pytest app/tests/integration/test_cloud.py -v
"""

from __future__ import annotations

import os
from datetime import datetime

import pytest
from core.config import settings

from .conftest import skip_astra, skip_neo4j

# ═══════════════════════════════════════════════════════════════════════════════
# Neo4j AuraDB (Cloud)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
async def neo4j_driver():
    from neo4j import AsyncGraphDatabase

    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
    )
    yield driver
    await driver.close()


@pytest.mark.asyncio
@skip_neo4j
async def test_neo4j_connectivity(neo4j_driver):
    """Neo4j AuraDB — driver can verify connectivity."""
    await neo4j_driver.verify_connectivity()


@pytest.mark.asyncio
@skip_neo4j
async def test_neo4j_basic_query(neo4j_driver):
    """Neo4j AuraDB — RETURN 1 works."""
    async with neo4j_driver.session(database="neo4j") as session:
        result = await session.run("RETURN 1 AS n")
        record = await result.single()
        assert record["n"] == 1


@pytest.mark.asyncio
@skip_neo4j
async def test_neo4j_create_and_match_ticker_node(neo4j_driver):
    """Neo4j AuraDB — MERGE a Ticker node and MATCH it back."""
    async with neo4j_driver.session(database="neo4j") as session:
        await session.run(
            "MERGE (t:Ticker {symbol: $_sym}) SET t.name = $_name, t.is_active = true",
            _sym="_PROXMOX_TEST",
            _name="Proxmox Integration Test",
        )
        result = await session.run(
            "MATCH (t:Ticker {symbol: $_sym}) RETURN t.name AS name",
            _sym="_PROXMOX_TEST",
        )
        record = await result.single()
        assert record["name"] == "Proxmox Integration Test"


@pytest.mark.asyncio
@skip_neo4j
async def test_neo4j_sector_relationship(neo4j_driver):
    """Neo4j AuraDB — BELONGS_TO relationship between Ticker and Sector."""
    async with neo4j_driver.session(database="neo4j") as session:
        await session.run(
            """
            MERGE (t:Ticker {symbol: '_PROXMOX_TEST'})
            MERGE (s:Sector {name: '_ProxmoxTestSector'})
            MERGE (t)-[:BELONGS_TO]->(s)
        """
        )
        result = await session.run(
            """
            MATCH (t:Ticker {symbol: '_PROXMOX_TEST'})-[:BELONGS_TO]->(s:Sector)
            RETURN s.name AS sector
        """
        )
        record = await result.single()
        assert record["sector"] == "_ProxmoxTestSector"


@pytest.mark.asyncio
@skip_neo4j
async def test_neo4j_correlation_edge(neo4j_driver):
    """Neo4j AuraDB — CORRELATED_WITH edge has correct r value."""
    async with neo4j_driver.session(database="neo4j") as session:
        await session.run(
            """
            MERGE (a:Ticker {symbol: '_PROXMOX_A'})
            MERGE (b:Ticker {symbol: '_PROXMOX_B'})
            MERGE (a)-[rel:CORRELATED_WITH]-(b)
            SET rel.r = 0.87, rel.window_days = 90
        """
        )
        result = await session.run(
            """
            MATCH (a:Ticker {symbol: '_PROXMOX_A'})-[rel:CORRELATED_WITH]-(b)
            RETURN rel.r AS r
        """
        )
        record = await result.single()
        assert record["r"] == pytest.approx(0.87)


@pytest.mark.asyncio
@skip_neo4j
async def test_neo4j_cleanup(neo4j_driver):
    """Neo4j AuraDB — delete test nodes created above."""
    async with neo4j_driver.session(database="neo4j") as session:
        await session.run(
            "MATCH (n) WHERE n.symbol IN ['_PROXMOX_TEST', '_PROXMOX_A', '_PROXMOX_B'] "
            "DETACH DELETE n"
        )
        await session.run("MATCH (s:Sector {name: '_ProxmoxTestSector'}) DELETE s")


# ═══════════════════════════════════════════════════════════════════════════════
# DataStax Astra / Cassandra (Cloud)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def astra_session():
    from cassandra.auth import PlainTextAuthProvider
    from cassandra.cluster import Cluster

    client_id = os.getenv("ASTRA_CLIENT_ID", "")
    client_secret = os.getenv("ASTRA_CLIENT_SECRET", "")
    bundle_path = os.getenv("ASTRA_BUNDLE_PATH", "")

    if bundle_path and os.path.exists(bundle_path):
        cloud_config = {"secure_connect_bundle": bundle_path}
        auth = PlainTextAuthProvider(client_id, client_secret)
        cluster = Cluster(cloud=cloud_config, auth_provider=auth)
    else:
        pytest.skip("ASTRA_BUNDLE_PATH not set or file not found — download from Astra console")

    session = cluster.connect(settings.ASTRA_DB_KEYSPACE)
    yield session
    cluster.shutdown()


@skip_astra
def test_astra_connectivity(astra_session):
    """DataStax Astra — session executes a basic query."""
    row = astra_session.execute("SELECT release_version FROM system.local").one()
    assert row is not None


@skip_astra
def test_astra_api_call_log_table_exists(astra_session):
    """DataStax Astra — api_call_log table exists in keyspace."""
    rows = astra_session.execute(
        """
        SELECT table_name FROM system_schema.tables
        WHERE keyspace_name = %s AND table_name = 'api_call_log'
    """,
        (settings.ASTRA_DB_KEYSPACE,),
    )
    tables = [r.table_name for r in rows]
    assert (
        "api_call_log" in tables
    ), "api_call_log table not found — run the CQL schema from README_1_DATABASE_SETUP.md"


@skip_astra
def test_astra_insert_and_read_log_entry(astra_session):
    """DataStax Astra — insert and read an API call log entry."""
    now = datetime.utcnow()
    astra_session.execute(
        """
        INSERT INTO api_call_log (source, logged_at, endpoint, status_code, latency_ms)
        VALUES (%s, %s, %s, %s, %s)
    """,
        ("_proxmox_test", now, "/test", 200, 10),
    )

    rows = astra_session.execute(
        "SELECT * FROM api_call_log WHERE source = '_proxmox_test' LIMIT 1"
    )
    result = rows.one()
    assert result is not None
    assert result.endpoint == "/test"
    assert result.status_code == 200
