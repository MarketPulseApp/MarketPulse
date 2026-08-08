import asyncpg
import httpx
import redis.asyncio as redis
from core.config import settings
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": "marketpulse-api"}


@router.get("/health/full")
async def health_full():
    checks = {}

    # PostgreSQL
    try:
        conn = await asyncpg.connect(settings.POSTGRES_URL, timeout=3)
        await conn.close()
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = str(e)

    # Valkey/Redis
    try:
        r = redis.from_url(settings.VALKEY_URL, socket_connect_timeout=3)
        await r.ping()
        await r.aclose()
        checks["valkey"] = "ok"
    except Exception as e:
        checks["valkey"] = str(e)

    # MongoDB
    try:
        from motor.motor_asyncio import AsyncIOMotorClient

        client = AsyncIOMotorClient(settings.MONGO_URL, serverSelectionTimeoutMS=3000)
        await client.admin.command("ping")
        client.close()
        checks["mongodb"] = "ok"
    except Exception as e:
        checks["mongodb"] = str(e)

    # Elasticsearch
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{settings.ELASTIC_URL}/_cluster/health")
            checks["elasticsearch"] = r.json().get("status", "unknown")
    except Exception as e:
        checks["elasticsearch"] = str(e)

    # ChromaDB
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{settings.CHROMA_URL}/api/v2/heartbeat")
            checks["chroma"] = "ok" if r.status_code == 200 else "error"
    except Exception as e:
        checks["chroma"] = str(e)

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}
