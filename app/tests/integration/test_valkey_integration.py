"""
app/tests/integration/test_valkey_integration.py

Integration tests for app/infrastructure/valkey.py.
Makes a real connection to Valkey on Node 1 — requires the service to be running.

Run with:
    pytest app/tests/integration/test_valkey_integration.py -v -s
"""

import pytest

import app.infrastructure.valkey as valkey_module
from app.infrastructure.valkey import close_client, create_client, lifespan_valkey


class TestCreateClient:
    @pytest.mark.asyncio
    async def test_create_client_sets_module_level_redis(self):
        """create_client() should assign the module-level redis variable."""
        create_client()
        assert valkey_module.redis is not None

    @pytest.mark.asyncio
    async def test_create_client_returns_connected_client(self):
        """The returned client should be able to ping Valkey."""
        client = create_client()
        response = await client.ping()
        assert response is True
        await close_client()

    @pytest.mark.asyncio
    async def test_module_level_redis_is_same_object_as_returned(self):
        """The module-level redis and the returned client should be the same object."""
        client = create_client()
        assert client is valkey_module.redis
        await close_client()


class TestCloseClient:
    @pytest.mark.asyncio
    async def test_close_client_does_not_raise(self):
        """close_client() should close cleanly without raising."""
        create_client()
        await close_client()

    @pytest.mark.asyncio
    async def test_client_cannot_be_used_after_close(self):
        """After close_client(), the connection pool is released."""
        create_client()
        await close_client()
        with pytest.raises(Exception):
            await valkey_module.redis.ping()


class TestLifespanValkey:
    @pytest.mark.asyncio
    async def test_lifespan_sets_redis_on_entry(self):
        """redis should be usable inside the lifespan context."""
        async with lifespan_valkey():
            assert valkey_module.redis is not None
            response = await valkey_module.redis.ping()
            assert response is True

    @pytest.mark.asyncio
    async def test_lifespan_closes_on_exit(self):
        """After exiting the lifespan context, the pool should be closed."""
        async with lifespan_valkey():
            pass
        with pytest.raises(Exception):
            await valkey_module.redis.ping()

    @pytest.mark.asyncio
    async def test_lifespan_set_and_get(self):
        """Verify real read/write works inside the lifespan context."""
        async with lifespan_valkey():
            await valkey_module.redis.set("marketpulse:test:lifespan", "ok", ex=10)
            value = await valkey_module.redis.get("marketpulse:test:lifespan")
            assert value == "ok"
            await valkey_module.redis.delete("marketpulse:test:lifespan")
