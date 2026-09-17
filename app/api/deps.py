from typing import Annotated

import asyncpg
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.db.postgres.user import UserRepository
from app.domain.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Assuming we have a way to get the db pool, for example, from app state or a global dependency
# Since it's not setup yet, we'll create a placeholder dependency.
from app.core.services.market_service import MarketService
from app.db.postgres.ohlcv import create_pool
from app.infrastructure import valkey
from app.infrastructure.repositories.market_repository_impl import MarketRepositoryImpl

_pg_pool = None


async def get_db_pool() -> asyncpg.Pool:
    global _pg_pool
    if _pg_pool is None:
        _pg_pool = await create_pool()
    return _pg_pool


async def get_market_service(pg_pool: asyncpg.Pool = Depends(get_db_pool)) -> MarketService:
    repo = MarketRepositoryImpl(valkey_client=valkey.redis, pg_pool=pg_pool)
    return MarketService(repo)


from app.core.services.paper_trading_service import PaperTradingService
from app.infrastructure.repositories.paper_trading_repository import PaperTradingRepositoryImpl


async def get_paper_trading_service(
    pg_pool: asyncpg.Pool = Depends(get_db_pool),
) -> PaperTradingService:
    repo = PaperTradingRepositoryImpl(pg_pool)
    return PaperTradingService(repo)


async def get_user_repository(
    pool: Annotated[asyncpg.Pool, Depends(get_db_pool)]
) -> UserRepository:
    return UserRepository(pool)


from app.db.postgres.system_settings import SystemSettingsRepository


async def get_system_settings_repository(
    pool: Annotated[asyncpg.Pool, Depends(get_db_pool)]
) -> SystemSettingsRepository:
    return SystemSettingsRepository(pool)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = await user_repo.get_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_active_superuser(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough privileges")
    return current_user


import asyncpg
from fastapi import Depends

from app.db.postgres.quota import QuotaRepository


async def get_quota_repository(pg_pool: asyncpg.Pool = Depends(get_db_pool)) -> QuotaRepository:
    return QuotaRepository(pg_pool)
