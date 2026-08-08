from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from routers import health, market_data, predictions, sentiment, watchlist

app = FastAPI(title="MarketPulse API", version="0.1.0")

Instrumentator().instrument(app).expose(app)

app.include_router(health.router)
app.include_router(market_data.router, prefix="/market", tags=["market"])
app.include_router(sentiment.router, prefix="/sentiment", tags=["sentiment"])
app.include_router(predictions.router, prefix="/predictions", tags=["predictions"])
app.include_router(watchlist.router, prefix="/watchlist", tags=["watchlist"])
