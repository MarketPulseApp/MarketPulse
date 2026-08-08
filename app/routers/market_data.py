from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_market_data():
    # TODO: implement
    return {"message": "market data endpoint - not yet implemented"}


@router.get("/{symbol}/ohlcv")
async def get_ohlcv(symbol: str):
    # TODO: query TimescaleDB ohlcv hypertable
    return {"symbol": symbol, "data": []}


@router.get("/{symbol}/indicators")
async def get_indicators(symbol: str):
    # TODO: query TimescaleDB technical_indicators hypertable
    return {"symbol": symbol, "indicators": []}
