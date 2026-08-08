from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_watchlist():
    # TODO: query watchlist_tickers table
    return {"tickers": []}


@router.post("/{symbol}")
async def add_to_watchlist(symbol: str):
    # TODO: insert into watchlist_tickers
    return {"added": symbol}


@router.delete("/{symbol}")
async def remove_from_watchlist(symbol: str):
    # TODO: delete from watchlist_tickers
    return {"removed": symbol}
