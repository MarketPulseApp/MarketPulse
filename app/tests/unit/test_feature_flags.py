"""
tests/unit/test_feature_flags.py

Unit tests for feature flag resolution (app/core/feature_flags.py).

Covers Phase 2.5.10:
  - is_enabled() returns False for disabled flags even when PostgreSQL says enabled
  - Valkey cache wins over PostgreSQL until the next sync
  - is_enabled() returns True when flag is enabled in cache
  - is_enabled() falls back to PostgreSQL default when flag is absent from cache
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.feature_flags import is_enabled, sync_flags_to_cache

# ── is_enabled() ──────────────────────────────────────────────────────────────


class TestIsEnabled:
    @pytest.mark.asyncio
    async def test_returns_true_when_flag_enabled_in_cache(self):
        """Valkey cache says enabled — should return True."""
        with patch("app.core.feature_flags.redis") as mock_redis:
            mock_redis.get = AsyncMock(return_value="1")
            result = await is_enabled("datasource.newsapi")
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_flag_disabled_in_cache(self):
        """
        Valkey cache says disabled — should return False even if PostgreSQL
        has the flag marked as enabled. Cache wins until next sync.
        """
        with patch("app.core.feature_flags.redis") as mock_redis:
            mock_redis.get = AsyncMock(return_value="0")
            result = await is_enabled("datasource.newsapi")
        assert result is False

    @pytest.mark.asyncio
    async def test_cache_false_overrides_postgres_true(self):
        """
        Core requirement from README_5 2.5.10:
        If Valkey cache contradicts PostgreSQL, Valkey wins until next sync.
        Postgres says enabled=True, cache says "0" — result must be False.
        """
        with patch("app.core.feature_flags.redis") as mock_redis:
            mock_redis.get = AsyncMock(return_value="0")

            # Even if we were to query postgres it would say True —
            # the function must never reach postgres when cache has a value.
            with patch("app.core.feature_flags.get_flag_from_db") as mock_db:
                mock_db.return_value = True
                result = await is_enabled("datasource.newsapi")

        assert result is False
        mock_db.assert_not_called()

    @pytest.mark.asyncio
    async def test_falls_back_to_postgres_when_flag_absent_from_cache(self):
        """
        Cache miss (None) — fall back to PostgreSQL and return its value.
        """
        with patch("app.core.feature_flags.redis") as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)

            with patch("app.core.feature_flags.get_flag_from_db") as mock_db:
                mock_db.return_value = True
                result = await is_enabled("datasource.newsapi")

        assert result is True
        mock_db.assert_called_once_with("datasource.newsapi")

    @pytest.mark.asyncio
    async def test_returns_false_when_absent_from_cache_and_postgres(self):
        """
        Unknown flag not in cache or database — should default to False (disabled).
        """
        with patch("app.core.feature_flags.redis") as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)

            with patch("app.core.feature_flags.get_flag_from_db") as mock_db:
                mock_db.return_value = None
                result = await is_enabled("flag.that.does.not.exist")

        assert result is False


# ── sync_flags_to_cache() ─────────────────────────────────────────────────────


class TestSyncFlagsToCache:
    @pytest.mark.asyncio
    async def test_writes_all_flags_from_postgres_to_cache(self):
        """
        sync_flags_to_cache() should read all flags from PostgreSQL and
        write each one to Valkey with the correct key format.
        """
        fake_flags = [
            {"name": "datasource.newsapi", "is_enabled": True},
            {"name": "alert.sms", "is_enabled": False},
        ]

        with patch("app.core.feature_flags.get_all_flags_from_db") as mock_db:
            mock_db.return_value = fake_flags

            with patch("app.core.feature_flags.redis") as mock_redis:
                mock_redis.set = AsyncMock()
                mock_pipe = MagicMock()
                mock_pipe.execute = AsyncMock()
                mock_redis.pipeline.return_value = mock_pipe
                await sync_flags_to_cache()

        assert mock_pipe.set.call_count == 2

    @pytest.mark.asyncio
    async def test_disabled_flag_written_as_zero_string(self):
        """
        Disabled flags must be stored as "0" in Valkey so is_enabled()
        can distinguish them from cache misses (None).
        """
        fake_flags = [{"name": "alert.sms", "is_enabled": False}]

        with patch("app.core.feature_flags.get_all_flags_from_db") as mock_db:
            mock_db.return_value = fake_flags

            with patch("app.core.feature_flags.redis") as mock_redis:
                mock_pipe = MagicMock()
                mock_pipe.execute = AsyncMock()
                mock_redis.pipeline.return_value = mock_pipe
                await sync_flags_to_cache()

        call_args = mock_pipe.set.call_args_list[0][0]
        assert call_args[1] == "0"

    @pytest.mark.asyncio
    async def test_enabled_flag_written_as_one_string(self):
        """Enabled flags must be stored as "1" in Valkey."""
        fake_flags = [{"name": "datasource.newsapi", "is_enabled": True}]

        with patch("app.core.feature_flags.get_all_flags_from_db") as mock_db:
            mock_db.return_value = fake_flags

            with patch("app.core.feature_flags.redis") as mock_redis:
                mock_pipe = MagicMock()
                mock_pipe.execute = AsyncMock()
                mock_redis.pipeline.return_value = mock_pipe
                await sync_flags_to_cache()

        call_args = mock_pipe.set.call_args_list[0][0]
        assert call_args[1] == "1"
