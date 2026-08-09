"""
Module-level async Redis client pointed at the Valkey instance.
Import the client anywhere with: from app.infrastructure.valkey import redis

Lifecycle is managed by the lifespan context manager in main.py.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from redis.asyncio import Redis

from app.core.config import settings

# Module-level client - created once, shared everywhere via connection pool.
redis: Redis | None = None


def create_client() -> Redis:
    """
    Create and return an async Redis client from VALKEY_URL in settings.
    """
    global redis
    redis = Redis(
        host=settings.VALKEY_HOST,
        port=settings.VALKEY_PORT,
        decode_responses=True,
        max_connections=10,
    )
    return redis


async def close_client() -> None:
    """
    Close the module-level client and release the connection pool.
    """
    global redis
    await redis.aclose()
    redis = None


@asynccontextmanager
async def lifespan_valkey() -> AsyncGenerator[None, None]:
    """
    Async context manager for use in the FastAPI lifespan.
    Initialises the module-level client on entry, closes it on exit.

    Usage in main.py:
        async with lifespan_valkey():
            yield
    """
    create_client()
    yield
    await close_client()
