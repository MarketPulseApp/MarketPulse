"""
Feature flag resolution — checks Valkey cache first, falls back to PostgreSQL.
Flags are synced from PostgreSQL to Valkey at startup and every 60 seconds.

Valkey key format:  flag:{flag_name}
Valkey values:      "1" = enabled, "0" = disabled
"""

from __future__ import annotations

from app.infrastructure.valkey import redis


# Cache key helper
def _cache_key(flag_name: str) -> str:
    return f"flag:{flag_name}"


# Database helpers
async def get_flag_from_db(flag_name: str) -> bool | None:
    """
    Fetch a single flag's enabled status from PostgreSQL.
    Returns None if the flag does not exist in the database.

    Replace with a real FeatureFlagRepository query in Phase 4.
    """
    pass


async def get_all_flags_from_db() -> list[dict]:
    """
    Fetch all feature flags from PostgreSQL.
    Returns a list of dicts with 'name' and 'is_enabled' keys:
        [{"name": "datasource.newsapi", "is_enabled": True}, ...]

    Replace with a real FeatureFlagRepository query in Phase 4.
    """
    pass


# Public API


async def sync_flags_to_cache():
    """
    Read all feature flags from PostgreSQL and write them to Valkey.
    Called at app startup and every 60 seconds by a background task.

    Uses a pipeline to write all flags in a single round-trip.
    Valkey cache wins over PostgreSQL until the next sync runs.
    """
    flags = await get_all_flags_from_db()
    pipe = redis.pipeline()
    for flag in flags:
        pipe.set(_cache_key(flag["name"]), "1" if flag["is_enabled"] else "0")
    await pipe.execute()


async def is_enabled(flag_name: str, default: bool = False) -> bool:
    """
    Return True if the named feature flag is enabled.

    Resolution order:
      1. Valkey cache — returns immediately if "1" or "0" is found
      2. PostgreSQL   — queried on cache miss
      3. default      — returned if the flag is absent from both (False by default)

    Valkey always wins when a value is present, even if it contradicts
    PostgreSQL. This is intentional — PostgreSQL is only authoritative
    after the next sync_flags_to_cache() run.
    """
    cached = await redis.get(_cache_key(flag_name))

    if cached is not None:
        return cached == "1"

    db_value = await get_flag_from_db(flag_name)

    if db_value is not None:
        return db_value

    return default
