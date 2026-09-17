import json
from datetime import datetime

import asyncpg
import redis.asyncio as redis

from app.db.postgres.ohlcv import OHLCVRepository
from app.db.valkey.price_cache import PriceCacheRepository
from app.domain.market import OHLCV, MarketRepository, OrderBook, OrderBookLevel, Tick


class MarketRepositoryImpl(MarketRepository):
    def __init__(self, valkey_client: redis.Redis, pg_pool: asyncpg.Pool):
        self.valkey_client = valkey_client
        self.price_cache = PriceCacheRepository(valkey_client)
        self.ohlcv_repo = OHLCVRepository(pg_pool)

    async def get_latest_tick(self, symbol: str) -> Tick | None:
        # Try getting from price cache
        data = await self.price_cache.get(symbol)
        if data:
            return Tick(
                symbol=symbol,
                price=data.get("price", 0.0),
                volume=data.get("volume", 0.0),
                timestamp=datetime.fromisoformat(data.get("timestamp", datetime.utcnow().isoformat()))
            )
        
        # Try raw valkey
        raw = await self.valkey_client.get(f"tick:{symbol}")
        if raw:
            try:
                d = json.loads(raw) if isinstance(raw, str) else json.loads(raw.decode())
                return Tick(
                    symbol=symbol,
                    price=d.get("price", 0.0),
                    volume=d.get("volume", 0.0),
                    timestamp=datetime.fromisoformat(d.get("timestamp", datetime.utcnow().isoformat()))
                )
            except Exception:
                pass
        return None

    async def get_order_book(self, symbol: str) -> OrderBook | None:
        raw = await self.valkey_client.get(f"orderbook:{symbol}")
        if raw:
            try:
                d = json.loads(raw) if isinstance(raw, str) else json.loads(raw.decode())
                bids = [OrderBookLevel(price=b["price"], volume=b["volume"]) for b in d.get("bids", [])]
                asks = [OrderBookLevel(price=a["price"], volume=a["volume"]) for a in d.get("asks", [])]
                return OrderBook(
                    symbol=symbol,
                    bids=bids,
                    asks=asks,
                    timestamp=datetime.fromisoformat(d.get("timestamp", datetime.utcnow().isoformat()))
                )
            except Exception:
                pass
        return None

    async def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> list[OHLCV]:
        days = limit
        if timeframe.endswith("d"):
            days = int(timeframe[:-1]) * limit
        elif timeframe.endswith("h"):
            days = max(1, (int(timeframe[:-1]) * limit) // 24)
            
        rows = await self.ohlcv_repo.get_recent(symbol, days)
        rows = rows[:limit]
        
        res = []
        for r in rows:
            res.append(OHLCV(
                symbol=symbol,
                timestamp=r.get("time", r.get("bucket", datetime.utcnow())),
                open=float(r.get("open_price", r.get("open", 0.0))),
                high=float(r.get("high_price", r.get("high", 0.0))),
                low=float(r.get("low_price", r.get("low", 0.0))),
                close=float(r.get("close_price", r.get("close", 0.0))),
                volume=float(r.get("volume", 0.0))
            ))
        return res
