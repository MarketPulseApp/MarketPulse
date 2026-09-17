from __future__ import annotations

import pytest
from db.embedded.audit_ledger import AuditLedgerRepository


@pytest.fixture
async def repo(tmp_path):
    r = AuditLedgerRepository(str(tmp_path / "audit.db"))
    await r.initialize()
    return r


@pytest.mark.asyncio
async def test_initialize_idempotent(tmp_path):
    r = AuditLedgerRepository(str(tmp_path / "audit.db"))
    await r.initialize()
    await r.initialize()


@pytest.mark.asyncio
async def test_append_single_entry(repo):
    await repo.append("CREATE", actor_id="user1", target_type="ticker", target_id="AAPL")
    entries = await repo.get_recent(n=10)
    assert len(entries) == 1
    assert entries[0]["action"] == "CREATE"


@pytest.mark.asyncio
async def test_verify_chain_empty_is_true(repo):
    assert await repo.verify_chain() is True


@pytest.mark.asyncio
async def test_verify_chain_intact(repo):
    await repo.append("CREATE", actor_id="u1", target_type="order", target_id="o1")
    await repo.append(
        "UPDATE",
        actor_id="u1",
        target_type="order",
        target_id="o1",
        old_value={"status": "pending"},
        new_value={"status": "filled"},
    )
    await repo.append("DELETE", actor_id="admin", target_type="order", target_id="o1")
    assert await repo.verify_chain() is True


@pytest.mark.asyncio
async def test_verify_chain_detects_tamper(repo, tmp_path):
    import aiosqlite

    await repo.append("CREATE", actor_id="u1")
    await repo.append("UPDATE", actor_id="u1")

    # Tamper with the first row's action
    db_path = str(tmp_path / "audit.db")
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute("UPDATE audit_log SET action = 'TAMPERED' WHERE id = 1")
        await conn.commit()

    assert await repo.verify_chain() is False


@pytest.mark.asyncio
async def test_get_recent_returns_n_entries(repo):
    for i in range(5):
        await repo.append("EV", actor_id=str(i))
    entries = await repo.get_recent(n=3)
    assert len(entries) == 3


@pytest.mark.asyncio
async def test_hash_chain_links_entries(repo):
    await repo.append("A")
    await repo.append("B")
    entries = await repo.get_recent(n=10)
    # Both entries should have non-empty row_hash values
    for e in entries:
        assert e["row_hash"] and len(e["row_hash"]) == 64  # SHA-256 hex
