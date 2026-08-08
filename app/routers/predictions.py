from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_predictions():
    # TODO: implement
    return {"message": "predictions endpoint - not yet implemented"}


@router.get("/{symbol}")
async def get_predictions(symbol: str):
    # TODO: query predictions hypertable
    return {"symbol": symbol, "predictions": []}
