"""Finance tool endpoints using Yahoo Finance (yfinance)."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import yfinance as yf

router = APIRouter(prefix="/finance", tags=["finance"])


class StockQuoteRequest(BaseModel):
    symbol: str = Field(..., description="Stock ticker symbol, e.g. AAPL, MSFT")


@router.post("/quote")
def get_stock_quote(body: StockQuoteRequest) -> dict:
    """Fetch current stock quote from Yahoo Finance."""
    symbol = body.symbol.upper().strip()
    ticker = yf.Ticker(symbol)
    info = ticker.info

    if not info or info.get("regularMarketPrice") is None:
        history = ticker.history(period="5d")
        if history.empty:
            raise HTTPException(status_code=404, detail=f"No data found for symbol: {symbol}")
        last = history.iloc[-1]
        return {
            "symbol": symbol,
            "price": round(float(last["Close"]), 2),
            "currency": info.get("currency", "USD"),
            "source": "yahoo_finance",
            "note": "Price from recent history (limited metadata)",
        }

    return {
        "symbol": symbol,
        "name": info.get("shortName") or info.get("longName"),
        "price": info.get("regularMarketPrice") or info.get("currentPrice"),
        "currency": info.get("currency", "USD"),
        "change": info.get("regularMarketChange"),
        "change_percent": info.get("regularMarketChangePercent"),
        "market_cap": info.get("marketCap"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
        "source": "yahoo_finance",
    }


@router.get("/history/{symbol}")
def get_stock_history(symbol: str, period: str = "1mo") -> dict:
    """Fetch historical OHLCV data for a stock symbol."""
    valid_periods = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y"}
    if period not in valid_periods:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period. Choose from: {', '.join(sorted(valid_periods))}",
        )

    symbol = symbol.upper().strip()
    ticker = yf.Ticker(symbol)
    history = ticker.history(period=period)

    if history.empty:
        raise HTTPException(status_code=404, detail=f"No history found for symbol: {symbol}")

    records = []
    for date, row in history.iterrows():
        records.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
            }
        )

    return {
        "symbol": symbol,
        "period": period,
        "data_points": len(records),
        "history": records[-10:],
        "note": "Showing last 10 data points",
        "source": "yahoo_finance",
    }
