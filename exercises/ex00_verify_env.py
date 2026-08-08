# exercises/ex00_verify_env.py
"""
Verify that all MarketPulse dependencies are importable.
Expected output: all green checkmarks, no red X marks.
"""

import sys
import subprocess
from dataclasses import dataclass

@dataclass
class Check:
    name: str
    module: str
    subprocess: bool = False

CHECKS = [
    Check("FastAPI",           "fastapi"),
    Check("Pydantic",          "pydantic"),
    Check("asyncpg",           "asyncpg"),
    Check("Redis (valkey)",    "redis"),
    Check("ChromaDB",          "chromadb"),
    Check("Motor (MongoDB)",   "motor"),
    Check("Elasticsearch",     "elasticsearch"),
    Check("InfluxDB client",   "influxdb_client"),
    Check("MinIO",             "minio"),
    Check("PyTorch",           "torch"),
    Check("XGBoost",           "xgboost"),
    Check("LightGBM",          "lightgbm"),
    Check("Transformers",      "transformers"),
    Check("VADER",             "vaderSentiment"),
    Check("sentence-trans.",   "sentence_transformers"),
    Check("grpcio",            "grpc"),
    Check("pandas",            "pandas"),
    Check("ta",                "ta"),
    Check("numpy",             "numpy"),
    Check("PRAW",              "praw"),
    Check("feedparser",        "feedparser"),
    Check("yfinance",          "yfinance"),
    Check("ARQ",               "arq"),
    Check("discord.py",        "discord"),
    Check("mplfinance",        "mplfinance"),
    Check("Pillow",            "PIL"),
    Check("pyotp",             "pyotp"),
    Check("structlog",         "structlog"),
    Check("msgpack",           "msgpack"),
    Check("DuckDB",            "duckdb"),
    Check("ZODB",              "ZODB"),
    Check("NetworkX",          "networkx"),
    Check("reportlab",         "reportlab"),
    Check("tenacity",          "tenacity"),
    Check("Hypothesis",        "hypothesis"),
    Check("Locust",            "locust",    subprocess=True),
    Check("cassandra-driver",  "cassandra"),
    Check("neo4j driver",      "neo4j"),
    Check("web3.py",           "web3"),
    Check("qrcode",            "qrcode"),
    Check("Alembic",           "alembic"),
    Check("aiosmtplib",        "aiosmtplib"),
    Check("Twilio",            "twilio"),
]

passed = 0
failed = 0

for check in CHECKS:
    try:
        if check.subprocess:
            result = subprocess.run(
                [sys.executable, "-c", f"import {check.module}"],
                capture_output=True,
            )
            if result.returncode != 0:
                raise ImportError(result.stderr.decode().strip().splitlines()[-1])
        else:
            __import__(check.module)
        print(f"  ✓  {check.name}")
        passed += 1
    except ImportError as e:
        print(f"  ✗  {check.name}  →  {e}")
        failed += 1

print(f"\n{passed} passed, {failed} failed")
if failed > 0:
    print("\nRun: pip install -r requirements.txt")
    sys.exit(1)