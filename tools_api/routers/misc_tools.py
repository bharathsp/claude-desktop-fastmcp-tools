"""Miscellaneous open API tool endpoints (no API keys required)."""

from fastapi import APIRouter, HTTPException, Query
from tools_api.http_client import async_client

router = APIRouter(prefix="/misc", tags=["misc"])


@router.get("/exchange-rate")
async def exchange_rate(
    from_currency: str = Query("USD", description="Source currency code"),
    to_currency: str = Query("EUR", description="Target currency code"),
    amount: float = Query(1.0, ge=0, description="Amount to convert"),
) -> dict:
    """Convert currency using the free Frankfurter API."""
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    async with async_client() as client:
        response = await client.get(
            f"https://api.frankfurter.app/latest",
            params={"from": from_currency, "to": to_currency, "amount": amount},
        )
        if response.status_code == 404:
            raise HTTPException(status_code=400, detail="Invalid currency code")
        response.raise_for_status()
        data = response.json()

    rate = data["rates"].get(to_currency)
    return {
        "from": from_currency,
        "to": to_currency,
        "amount": amount,
        "rate": rate,
        "converted": rate,
        "date": data.get("date"),
        "source": "frankfurter",
    }


@router.get("/wikipedia")
async def wikipedia_summary(
    topic: str = Query(..., description="Topic to look up on Wikipedia"),
) -> dict:
    """Fetch a short Wikipedia summary for a topic."""
    async with async_client(
        headers={"User-Agent": "CustomMCPServer/1.0 (educational project)"},
    ) as client:
        response = await client.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{topic.replace(' ', '_')}",
        )
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Wikipedia page not found: {topic}")
        response.raise_for_status()
        data = response.json()

    return {
        "title": data.get("title"),
        "extract": data.get("extract"),
        "description": data.get("description"),
        "url": data.get("content_urls", {}).get("desktop", {}).get("page"),
        "source": "wikipedia",
    }


@router.get("/random-fact")
async def random_fact() -> dict:
    """Return a random interesting fact."""
    async with async_client() as client:
        response = await client.get("https://uselessfacts.jsph.pl/random.json?language=en")
        response.raise_for_status()
        data = response.json()

    return {
        "fact": data.get("text"),
        "source": data.get("source"),
        "api": "uselessfacts",
    }


@router.get("/country-info/{country_code}")
async def country_info(country_code: str) -> dict:
    """Get basic country information from REST Countries API."""
    code = country_code.upper()
    async with async_client() as client:
        response = await client.get(f"https://restcountries.com/v3.1/alpha/{code}")
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Country not found: {code}")
        response.raise_for_status()
        countries = response.json()

    country = countries[0]
    currencies = country.get("currencies", {})
    currency_list = [
        {"code": code, "name": info.get("name"), "symbol": info.get("symbol")}
        for code, info in currencies.items()
    ]

    return {
        "name": country.get("name", {}).get("common"),
        "official_name": country.get("name", {}).get("official"),
        "capital": country.get("capital", []),
        "region": country.get("region"),
        "subregion": country.get("subregion"),
        "population": country.get("population"),
        "languages": list(country.get("languages", {}).values()),
        "currencies": currency_list,
        "flag": country.get("flag"),
        "source": "restcountries",
    }
