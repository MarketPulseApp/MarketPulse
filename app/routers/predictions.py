from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_active_user
from app.domain.user import User

router = APIRouter()


@router.get("/")
async def list_predictions(current_user: Annotated[User, Depends(get_current_active_user)]):
    # TODO: implement
    return {"message": "predictions endpoint - not yet implemented"}


@router.get("/{symbol}")
async def get_predictions(
    symbol: str, current_user: Annotated[User, Depends(get_current_active_user)]
):
    # TODO: query predictions hypertable
    return {"symbol": symbol, "predictions": []}
