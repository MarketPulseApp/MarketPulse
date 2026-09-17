from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_active_user
from app.domain.user import User

router = APIRouter()


@router.get("/")
async def list_sentiment(current_user: Annotated[User, Depends(get_current_active_user)]):
    # TODO: implement
    return {"message": "sentiment endpoint - not yet implemented"}


@router.get("/{symbol}")
async def get_sentiment(
    symbol: str, current_user: Annotated[User, Depends(get_current_active_user)]
):
    # TODO: query sentiment_scores and news_sentiment hypertables
    return {"symbol": symbol, "sentiment": None}
