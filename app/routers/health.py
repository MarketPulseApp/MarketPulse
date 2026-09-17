import asyncpg
import httpx
import redis.asyncio as redis
from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": "marketpulse-api"}


@router.get("/health/full")
async def health_full():
    checks = {}

    # PostgreSQL
    try:
        dsn = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DATABASE}"
        conn = await asyncpg.connect(dsn, timeout=3)
        await conn.close()
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = str(e)

    # Valkey/Redis
    try:
        r = redis.Redis(
            host=settings.VALKEY_HOST,
            port=settings.VALKEY_PORT,
            password=settings.VALKEY_PASSWORD or None,
            socket_connect_timeout=3,
        )
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

    # ChromaDB
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{settings.CHROMA_URL}/api/v2/heartbeat")
            checks["chroma"] = "ok" if r.status_code == 200 else "error"
    except Exception as e:
        checks["chroma"] = str(e)

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}
