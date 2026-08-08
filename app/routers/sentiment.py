from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_sentiment():
    # TODO: implement
    return {"message": "sentiment endpoint - not yet implemented"}


@router.get("/{symbol}")
async def get_sentiment(symbol: str):
    # TODO: query sentiment_scores and news_sentiment hypertables
    return {"symbol": symbol, "sentiment": None}
