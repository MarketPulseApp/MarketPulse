from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_active_user, get_market_service
from app.core.services.market_service import MarketService
from app.domain.market import OHLCV, OrderBook, Tick
from app.domain.user import User

router = APIRouter()


@router.get("/tick/{symbol}", response_model=Tick)
async def get_latest_tick(
    symbol: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    market_service: MarketService = Depends(get_market_service),
):
    """
    Get the latest market tick for a given symbol.
    """
    tick = await market_service.get_latest_tick(symbol)
    if not tick:
        raise HTTPException(status_code=404, detail="Tick not found")
    return tick


@router.get("/orderbook/{symbol}", response_model=OrderBook)
async def get_order_book(
    symbol: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    market_service: MarketService = Depends(get_market_service),
):
    """
    Get the current order book for a given symbol.
    """
    ob = await market_service.get_order_book(symbol)
    if not ob:
        raise HTTPException(status_code=404, detail="Order book not found")
    return ob


@router.get("/ohlcv/{symbol}", response_model=list[OHLCV])
async def get_ohlcv(
    symbol: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    timeframe: str = "1d",
    limit: int = 100,
    market_service: MarketService = Depends(get_market_service),
):
    """
    Get OHLCV data for a given symbol.
    """
    return await market_service.get_ohlcv(symbol, timeframe, limit)


@router.get("/{symbol}/indicators")
async def get_indicators(
    symbol: str, current_user: Annotated[User, Depends(get_current_active_user)]
):
    # TODO: query TimescaleDB technical_indicators hypertable
    return {"symbol": symbol, "indicators": []}
