"""
conftest.py for Proxmox integration tests.
Place at: app/tests/integration/conftest.py

Uses app.core.config.settings as the single source of truth for all
connection details — no duplication of env vars.

Node layout:
  Node 1 — 192.168.1.123  PostgreSQL, Valkey, ChromaDB, SurrealDB, MinIO
  Node 2 — 192.168.1.162  MongoDB, Elasticsearch, InfluxDB
  Node 3 — ML sidecar (gRPC — tested separately)
  Cloud  — Neo4j AuraDB, DataStax Astra (external)
"""

from __future__ import annotations

import os
import socket
import sys

import pytest

# Make app/ importable regardless of where pytest is invoked from
_APP_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _APP_ROOT not in sys.path:
    sys.path.insert(0, _APP_ROOT)

from core.config import settings  # noqa: E402

# ── helpers ───────────────────────────────────────────────────────────────────


def _reachable(host: str, port: int, timeout: float = 2.0) -> bool:
    """Return True if a TCP connection to host:port succeeds."""
    if not host:
        return False
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _parse_host_port(url: str, default_port: int) -> tuple[str, int]:
    """Extract host and port from http://host:port, ws://host:port, or host:port."""
    url = url.replace("http://", "").replace("https://", "").replace("ws://", "")
    url = url.split("/")[0]
    if ":" in url:
        host, port_str = url.rsplit(":", 1)
        return host, int(port_str)
    return url, default_port


def _skip(host: str, port: int, node: str, service: str):
    return pytest.mark.skipif(
        not _reachable(host, port),
        reason=(
            f"{service} not reachable at {host}:{port} [{node}] — "
            f"is the service running on that node?"
        ),
    )


# ── Node 1 — 192.168.1.123 ───────────────────────────────────────────────────

skip_postgres = _skip(
    settings.POSTGRES_HOST, settings.POSTGRES_PORT, "Node 1 · 192.168.1.123", "PostgreSQL"
)
skip_valkey = _skip(settings.VALKEY_HOST, settings.VALKEY_PORT, "Node 1 · 192.168.1.123", "Valkey")

_chroma_host, _chroma_port = _parse_host_port(settings.CHROMA_URL or "192.168.1.123:8000", 8000)
_surreal_host, _surreal_port = _parse_host_port(settings.SURREAL_URL or "192.168.1.123:8001", 8001)
_minio_host, _minio_port = _parse_host_port(settings.MINIO_URL or "192.168.1.123:9000", 9000)

skip_chroma = _skip(_chroma_host, _chroma_port, "Node 1 · 192.168.1.123", "ChromaDB")
skip_surreal = _skip(_surreal_host, _surreal_port, "Node 1 · 192.168.1.123", "SurrealDB")
skip_minio = _skip(_minio_host, _minio_port, "Node 1 · 192.168.1.123", "MinIO")

# ── Node 2 — 192.168.1.162 ───────────────────────────────────────────────────

_mongo_host, _mongo_port = _parse_host_port(settings.MONGO_URL or "192.168.1.162:27017", 27017)
_elastic_host, _elastic_port = _parse_host_port(settings.ELASTIC_URL or "192.168.1.162:9200", 9200)
_influx_host, _influx_port = _parse_host_port(settings.INFLUX_URL or "192.168.1.162:8086", 8086)

skip_mongo = _skip(_mongo_host, _mongo_port, "Node 2 · 192.168.1.162", "MongoDB")
skip_elastic = _skip(_elastic_host, _elastic_port, "Node 2 · 192.168.1.162", "Elasticsearch")
skip_influx = _skip(_influx_host, _influx_port, "Node 2 · 192.168.1.162", "InfluxDB")

# ── Cloud ─────────────────────────────────────────────────────────────────────

skip_neo4j = pytest.mark.skipif(
    not bool(settings.NEO4J_URI and settings.NEO4J_PASSWORD),
    reason="Neo4j AuraDB — NEO4J_URI / NEO4J_PASSWORD not set in .env",
)
skip_astra = pytest.mark.skipif(
    not bool(settings.ASTRA_DB_ID),
    reason="DataStax Astra — ASTRA_DB_ID not set in .env",
)

# ── Parsed values exported to test fixtures ───────────────────────────────────

CHROMA_HOST = _chroma_host
CHROMA_PORT = _chroma_port
SURREAL_HOST = _surreal_host
SURREAL_PORT = _surreal_port
MINIO_HOST = _minio_host
MINIO_PORT = _minio_port
MONGO_HOST = _mongo_host
MONGO_PORT = _mongo_port
ELASTIC_HOST = _elastic_host
ELASTIC_PORT = _elastic_port
INFLUX_HOST = _influx_host
INFLUX_PORT = _influx_port
