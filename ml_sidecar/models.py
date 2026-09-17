from pydantic import BaseModel, Field


class OHLCVData(BaseModel):
    """
    Domain model representing a single OHLCV candlestick.
    """

    time: str | int = Field(..., description="Timestamp of the candle")
    open: float = Field(..., description="Open price")
    high: float = Field(..., description="High price")
    low: float = Field(..., description="Low price")
    close: float = Field(..., description="Close price")
    volume: float = Field(..., description="Volume traded")
    put_call_ratio: float | None = Field(None, description="Options put/call ratio")
    macro_cpi: float | None = Field(None, description="Macro CPI data")
    stocktwits_sentiment: float | None = Field(None, description="StockTwits sentiment score")
    congressional_buys: float | None = Field(None, description="Congressional insider trading buys")
    insider_buys: float | None = Field(None, description="Corporate insider trading buys")
    insider_sells: float | None = Field(None, description="Corporate insider trading sells")
    reddit_sentiment: float | None = Field(None, description="Reddit sentiment score")
    rss_sentiment: float | None = Field(None, description="RSS news sentiment score")


class OHLCVPayload(BaseModel):
    """
    Presentation payload containing a list of OHLCV data.
    """

    data: list[OHLCVData] = Field(..., description="List of OHLCV candles")
