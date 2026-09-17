import asyncio
import json
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.api.deps import get_market_service, get_paper_trading_service
from app.core.services.market_service import MarketService
from app.core.services.paper_trading_service import PaperTradingService

router = APIRouter()


def serialize_datetime(obj: Any) -> Any:
    from datetime import datetime

    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


@router.websocket("/market")
async def market_websocket(
    websocket: WebSocket,
    market_service: MarketService = Depends(get_market_service),
    paper_service: PaperTradingService = Depends(get_paper_trading_service),
):
    await websocket.accept()

    symbol = "AAPL"

    try:
        while True:
            # Fetch latest OHLCV and latest trade
            ohlcv_data = await market_service.get_ohlcv(symbol, limit=1)
            trades_data = await paper_service.get_trades(limit=1)

            # Prepare payload
            # OHLCV is a dataclass, PaperTrade is a pydantic model
            payload = {
                "type": "update",
                "ohlcv": [asdict(o) for o in ohlcv_data],
                "trade": [t.model_dump() for t in trades_data],
            }

            # We can use json.dumps with a custom encoder for datetimes, or websocket.send_text
            text_data = json.dumps(payload, default=serialize_datetime)
            await websocket.send_text(text_data)

            await asyncio.sleep(1)
    except WebSocketDisconnect:
        print("WebSocket client disconnected")


import random


@router.websocket("/training")
async def training_websocket(websocket: WebSocket):
    await websocket.accept()

    try:
        epoch = 1
        loss = 2.5
        progress = 0
        data_sources = ["Binance", "Coinbase", "Kraken", "Twitter Sentiment", "Macro Data"]

        while True:
            # Simulate training step
            loss = loss * random.uniform(0.95, 0.99)
            progress += random.randint(1, 5)

            if progress >= 100:
                progress = 0
                epoch += 1

            current_source = random.choice(data_sources)

            status_payload = {
                "type": "status",
                "payload": {
                    "epoch": epoch,
                    "loss": loss,
                    "dataSource": current_source,
                    "stage": "Forward Pass" if random.random() > 0.5 else "Backpropagation",
                    "progress": progress,
                },
            }

            log_payload = {
                "type": "log",
                "message": f"Epoch {epoch} | Loss: {loss:.4f} | Source: {current_source} | Progress: {progress}%",
            }

            await websocket.send_text(json.dumps(status_payload))
            await websocket.send_text(json.dumps(log_payload))

            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        print("Training WebSocket client disconnected")
