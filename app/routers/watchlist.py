from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_active_user
from app.domain.user import User

router = APIRouter()


@router.get("/")
async def get_watchlist(current_user: Annotated[User, Depends(get_current_active_user)]):
    # TODO: query watchlist_tickers table
    return {"tickers": []}


@router.post("/{symbol}")
async def add_to_watchlist(
    symbol: str, current_user: Annotated[User, Depends(get_current_active_user)]
):
    # TODO: insert into watchlist_tickers
    return {"added": symbol}


@router.delete("/{symbol}")
async def remove_from_watchlist(
    symbol: str, current_user: Annotated[User, Depends(get_current_active_user)]
):
    # TODO: delete from watchlist_tickers
    return {"removed": symbol}
