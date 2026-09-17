from __future__ import annotations

import asyncpg

from app.domain.user import User


class UserRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def get_by_email(self, email: str) -> User | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, email, password_hash as hashed_password, role, created_at, updated_at FROM users WHERE email = $1",
                email,
            )
            if row:
                return self._to_domain(row)
            return None

    async def get_by_id(self, user_id: str) -> User | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, email, password_hash as hashed_password, role, created_at, updated_at FROM users WHERE id = $1",
                user_id,
            )
            if row:
                return self._to_domain(row)
            return None

    async def create(self, user: User) -> User:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO users (id, email, password_hash, role, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, email, password_hash as hashed_password, role, created_at, updated_at
                """,
                user.id,
                user.email,
                user.hashed_password,
                user.role,
                user.created_at,
                user.updated_at,
            )
            return self._to_domain(row)

    @staticmethod
    def _to_domain(row) -> User:
        return User(
            id=str(row["id"]),
            email=row["email"],
            hashed_password=row["hashed_password"],
            is_active=True,
            role=row["role"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
