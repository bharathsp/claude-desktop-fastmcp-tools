"""Finance tool endpoints using Yahoo Finance chart API."""

from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from tools_api.http_client import async_client

router = APIRouter(prefix="/finance", tags=["finance"])

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
YAHOO_HEADERS = {"User-Agent": "Mozilla/5.0 (CustomMCPServer/1.0)"}

VALID_PERIODS = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y"}


class StockQuoteRequest(BaseModel):
    symbol: str = Field(..., description="Stock ticker symbol, e.g. AAPL, MSFT")


def _finance_api_error(exc: Exception, symbol: str) -> HTTPException:
    if isinstance(exc, httpx.HTTPStatusError):
        return HTTPException(
            status_code=502,
            detail=f"Yahoo Finance returned HTTP {exc.response.status_code} for {symbol}",
        )
    if "CERTIFICATE_VERIFY_FAILED" in str(exc):
        return HTTPException(
            status_code=502,
            detail="SSL error reaching Yahoo Finance. Restart Tools API with TOOLS_API_SSL_VERIFY=false",
        )
    return HTTPException(status_code=502, detail=f"Could not fetch data for {symbol}: {exc}")


async def _fetch_chart(symbol: str, range_period: str, interval: str = "1d") -> dict:
    async with async_client(headers=YAHOO_HEADERS) as client:
        response = await client.get(
            YAHOO_CHART_URL.format(symbol=symbol.upper()),
            params={"interval": interval, "range": range_period},
        )
        response.raise_for_status()
        payload = response.json()

    results = payload.get("chart", {}).get("result")
    if not results:
        error = payload.get("chart", {}).get("error", {})
        raise HTTPException(
            status_code=404,
            detail=error.get("description", f"No data found for symbol: {symbol}"),
        )
    return results[0]


@router.post("/quote")
async def get_stock_quote(body: StockQuoteRequest) -> dict:
    """Fetch current stock quote from Yahoo Finance."""
    symbol = body.symbol.upper().strip()

    try:
        chart = await _fetch_chart(symbol, range_period="5d")
    except HTTPException:
        raise
    except Exception as exc:
        raise _finance_api_error(exc, symbol) from exc

    meta = chart.get("meta", {})
    price = meta.get("regularMarketPrice")
    if price is None:
        raise HTTPException(status_code=404, detail=f"No price data for symbol: {symbol}")

    prev_close = meta.get("chartPreviousClose") or meta.get("previousClose")
    change = round(price - prev_close, 2) if prev_close else None
    change_percent = (
        round((change / prev_close) * 100, 2) if change is not None and prev_close else None
    )

    return {
        "symbol": symbol,
        "name": meta.get("shortName") or meta.get("longName"),
        "price": round(float(price), 2),
        "currency": meta.get("currency", "USD"),
        "change": change,
        "change_percent": change_percent,
        "day_high": meta.get("regularMarketDayHigh"),
        "day_low": meta.get("regularMarketDayLow"),
        "fifty_two_week_high": meta.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": meta.get("fiftyTwoWeekLow"),
        "exchange": meta.get("fullExchangeName") or meta.get("exchangeName"),
        "source": "yahoo_finance",
    }


@router.get("/history/{symbol}")
async def get_stock_history(symbol: str, period: str = "1mo") -> dict:
    """Fetch historical OHLCV data for a stock symbol."""
    if period not in VALID_PERIODS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period. Choose from: {', '.join(sorted(VALID_PERIODS))}",
        )

    symbol = symbol.upper().strip()

    try:
        chart = await _fetch_chart(symbol, range_period=period)
    except HTTPException:
        raise
    except Exception as exc:
        raise _finance_api_error(exc, symbol) from exc

    timestamps = chart.get("timestamp") or []
    quote = (chart.get("indicators", {}).get("quote") or [{}])[0]

    if not timestamps:
        raise HTTPException(status_code=404, detail=f"No history found for symbol: {symbol}")

    records = []
    for i, ts in enumerate(timestamps):
        close = quote.get("close", [None])[i] if i < len(quote.get("close", [])) else None
        if close is None:
            continue
        records.append(
            {
                "date": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"),
                "open": round(float(quote["open"][i]), 2),
                "high": round(float(quote["high"][i]), 2),
                "low": round(float(quote["low"][i]), 2),
                "close": round(float(close), 2),
                "volume": int(quote["volume"][i]) if quote.get("volume") else 0,
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
