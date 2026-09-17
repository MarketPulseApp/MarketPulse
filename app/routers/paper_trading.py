from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_active_user, get_paper_trading_service
from app.core.services.paper_trading_service import PaperTradingService
from app.domain.paper_trading import PaperPortfolio, PaperTrade
from app.domain.user import User

router = APIRouter()


@router.get("/portfolio", response_model=PaperPortfolio)
async def get_portfolio(
    current_user: Annotated[User, Depends(get_current_active_user)],
    service: PaperTradingService = Depends(get_paper_trading_service),
):
    """
    Get the current balance/equity from paper_portfolio.
    """
    portfolio = await service.get_portfolio()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio


@router.get("/trades", response_model=list[PaperTrade])
async def get_trades(
    current_user: Annotated[User, Depends(get_current_active_user)],
    limit: int = 50,
    service: PaperTradingService = Depends(get_paper_trading_service),
):
    """
    Get the recent execution history from paper_trades.
    """
    trades = await service.get_trades(limit=limit)
    return trades
