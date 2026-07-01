"""Miscellaneous open API tool endpoints (no API keys required)."""

import httpx
from fastapi import APIRouter, HTTPException, Query

from tools_api.http_client import async_client

router = APIRouter(prefix="/misc", tags=["misc"])

FRANKFURTER_API = "https://api.frankfurter.dev/v1/latest"


def _external_api_error(exc: Exception, service: str) -> HTTPException:
    if isinstance(exc, httpx.HTTPStatusError):
        return HTTPException(
            status_code=502,
            detail=f"{service} returned HTTP {exc.response.status_code}",
        )
    if isinstance(exc, httpx.ConnectError) and "CERTIFICATE_VERIFY_FAILED" in str(exc):
        return HTTPException(
            status_code=502,
            detail=(
                f"SSL error reaching {service}. "
                "Restart Tools API with: $env:TOOLS_API_SSL_VERIFY='false'"
            ),
        )
    return HTTPException(status_code=502, detail=f"Could not reach {service}: {exc}")


@router.get("/exchange-rate")
async def exchange_rate(
    from_currency: str = Query("USD", description="Source currency code"),
    to_currency: str = Query("EUR", description="Target currency code"),
    amount: float = Query(1.0, ge=0, description="Amount to convert"),
) -> dict:
    """Convert currency using the free Frankfurter API."""
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    try:
        async with async_client() as client:
            response = await client.get(
                FRANKFURTER_API,
                params={"from": from_currency, "to": to_currency, "amount": amount},
            )
            if response.status_code == 404:
                raise HTTPException(status_code=400, detail="Invalid currency code")
            response.raise_for_status()
            data = response.json()
    except HTTPException:
        raise
    except Exception as exc:
        raise _external_api_error(exc, "Frankfurter API") from exc

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
    """Get basic country information (World Bank + Wikipedia; no API key required)."""
    code = country_code.upper()
    wiki_headers = {"User-Agent": "CustomMCPServer/1.0 (educational project)"}

    try:
        async with async_client() as client:
            wb_response = await client.get(
                f"https://api.worldbank.org/v2/country/{code}",
                params={"format": "json"},
            )
            wb_response.raise_for_status()
            wb_payload = wb_response.json()

            if not isinstance(wb_payload, list) or len(wb_payload) < 2 or not wb_payload[1]:
                raise HTTPException(status_code=404, detail=f"Country not found: {code}")

            country = wb_payload[1][0]
            name = country.get("name", code)

            population = None
            pop_response = await client.get(
                f"https://api.worldbank.org/v2/country/{code}/indicator/SP.POP.TOTL",
                params={"format": "json", "per_page": 1, "date": "2023:2024"},
            )
            if pop_response.status_code == 200:
                pop_payload = pop_response.json()
                if isinstance(pop_payload, list) and len(pop_payload) > 1 and pop_payload[1]:
                    latest = pop_payload[1][0]
                    if latest.get("value") is not None:
                        population = int(latest["value"])

            wiki_response = await client.get(
                f"https://en.wikipedia.org/api/rest_v1/page/summary/{name.replace(' ', '_')}",
                headers=wiki_headers,
            )
            wiki_data = wiki_response.json() if wiki_response.status_code == 200 else {}

    except HTTPException:
        raise
    except Exception as exc:
        raise _external_api_error(exc, "World Bank / Wikipedia") from exc

    capital = country.get("capitalCity")
    region = country.get("region", {}).get("value")
    income_level = country.get("incomeLevel", {}).get("value")

    return {
        "name": name,
        "official_name": wiki_data.get("title", name),
        "capital": [capital] if capital else [],
        "region": region,
        "subregion": income_level,
        "population": population,
        "languages": [],
        "currencies": [],
        "flag": "",
        "summary": wiki_data.get("extract"),
        "latitude": country.get("latitude"),
        "longitude": country.get("longitude"),
        "url": wiki_data.get("content_urls", {}).get("desktop", {}).get("page"),
        "source": "worldbank+wikipedia",
    }
