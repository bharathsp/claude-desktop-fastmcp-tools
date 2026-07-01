"""FastMCP server that proxies custom tools from the local Tools API."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path when launched by Claude Desktop
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastmcp import FastMCP

from mcp_server.config import settings
from mcp_server.middleware.session_logging import SessionLoggingMiddleware
from mcp_server.tools_client import tools_client

mcp = FastMCP(settings.server_name)
mcp.add_middleware(SessionLoggingMiddleware())


# ---------------------------------------------------------------------------
# Tools — each calls the local Tools API
# ---------------------------------------------------------------------------


@mcp.tool
async def add(a: float, b: float) -> str:
    """Add two numbers together."""
    result = await tools_client.post("/math/add", {"a": a, "b": b})
    return result["expression"]


@mcp.tool
async def calculate_percentage(value: float, percent: float) -> str:
    """Calculate a percentage of a value (e.g. 15% of 200)."""
    result = await tools_client.post("/math/percentage", {"value": value, "percent": percent})
    return result["expression"]


@mcp.tool
async def fibonacci(n: int) -> str:
    """Generate the first n Fibonacci numbers (1-50)."""
    result = await tools_client.get(f"/math/fibonacci/{n}")
    return f"First {result['count']} Fibonacci numbers: {result['sequence']}"


@mcp.tool
async def stock_quote(symbol: str) -> str:
    """Get a live stock quote from Yahoo Finance for a ticker symbol (e.g. AAPL, TSLA)."""
    result = await tools_client.post("/finance/quote", {"symbol": symbol})
    lines = [
        f"**{result.get('name', symbol)}** ({result['symbol']})",
        f"Price: {result['price']} {result.get('currency', 'USD')}",
    ]
    if result.get("change") is not None:
        lines.append(f"Change: {result['change']} ({result.get('change_percent', 0):.2f}%)")
    if result.get("market_cap"):
        lines.append(f"Market Cap: {result['market_cap']:,}")
    return "\n".join(lines)


@mcp.tool
async def stock_history(symbol: str, period: str = "1mo") -> str:
    """Get historical stock price data. Period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y."""
    result = await tools_client.get(f"/finance/history/{symbol}", params={"period": period})
    lines = [f"**{result['symbol']}** — last {len(result['history'])} days ({result['period']}):"]
    for row in result["history"]:
        lines.append(f"  {row['date']}: O={row['open']} H={row['high']} L={row['low']} C={row['close']}")
    return "\n".join(lines)


@mcp.tool
async def current_weather(city: str) -> str:
    """Get current weather for a city using Open-Meteo (no API key required)."""
    result = await tools_client.get("/weather/current", params={"city": city})
    return (
        f"Weather in **{result['city']}, {result['country']}**:\n"
        f"  Temperature: {result['temperature_c']}°C\n"
        f"  Humidity: {result['humidity_percent']}%\n"
        f"  Wind: {result['wind_speed_kmh']} km/h\n"
        f"  Conditions: {result['conditions']}"
    )


@mcp.tool
async def weather_forecast(city: str, days: int = 5) -> str:
    """Get a multi-day weather forecast (1-7 days) for a city via Open-Meteo."""
    result = await tools_client.get("/weather/forecast", params={"city": city, "days": days})
    lines = [f"**{days}-day forecast for {result['city']}, {result['country']}:**"]
    for day in result["forecast"]:
        lines.append(
            f"  {day['date']}: {day['temp_min_c']}°C – {day['temp_max_c']}°C, "
            f"{day['conditions']}, precip {day['precipitation_mm']}mm"
        )
    return "\n".join(lines)


@mcp.tool
async def exchange_rate(from_currency: str, to_currency: str, amount: float = 1.0) -> str:
    """Convert currency using live exchange rates (Frankfurter API)."""
    result = await tools_client.get(
        "/misc/exchange-rate",
        params={"from_currency": from_currency, "to_currency": to_currency, "amount": amount},
    )
    return (
        f"{result['amount']} {result['from']} = {result['converted']} {result['to']} "
        f"(rate as of {result['date']})"
    )


@mcp.tool
async def wikipedia_summary(topic: str) -> str:
    """Get a short Wikipedia summary for any topic."""
    result = await tools_client.get("/misc/wikipedia", params={"topic": topic})
    return f"**{result['title']}**\n\n{result['extract']}\n\nRead more: {result['url']}"


@mcp.tool
async def random_fact() -> str:
    """Return a random interesting fact."""
    result = await tools_client.get("/misc/random-fact")
    return f"Did you know? {result['fact']}"


@mcp.tool
async def country_info(country_code: str) -> str:
    """Get country information by ISO 3166-1 alpha-2 code (e.g. US, IN, JP)."""
    result = await tools_client.get(f"/misc/country-info/{country_code}")
    lines = [
        f"**{result['name']}** ({result.get('official_name', result['name'])})",
        f"Capital: {', '.join(result.get('capital', [])) or 'N/A'}",
        f"Region: {result.get('region', 'N/A')} / {result.get('subregion', 'N/A')}",
    ]
    if result.get("population"):
        lines.append(f"Population: {result['population']:,}")
    if result.get("summary"):
        lines.append(f"\n{result['summary']}")
    if result.get("url"):
        lines.append(f"\nRead more: {result['url']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


@mcp.resource("config://server")
def get_server_config() -> str:
    """Static server configuration and available capabilities."""
    config = {
        "server_name": settings.server_name,
        "tools_api_url": settings.tools_api_base_url,
        "version": "1.0.0",
        "capabilities": {
            "math": ["add", "percentage", "fibonacci"],
            "finance": ["stock_quote", "stock_history"],
            "weather": ["current_weather", "weather_forecast"],
            "misc": ["exchange_rate", "wikipedia", "random_fact", "country_info"],
        },
        "data_sources": {
            "finance": "Yahoo Finance (yfinance)",
            "weather": "Open-Meteo",
            "exchange": "Frankfurter API",
            "wikipedia": "Wikipedia REST API",
            "countries": "World Bank + Wikipedia",
        },
    }
    return json.dumps(config, indent=2)


@mcp.resource("status://health")
async def get_health_status() -> str:
    """Live health check of the Tools API backend."""
    try:
        health = await tools_client.health_check()
        return json.dumps(
            {
                "mcp_server": "running",
                "tools_api": health,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        )
    except Exception as exc:
        return json.dumps(
            {
                "mcp_server": "running",
                "tools_api": {"status": "unreachable", "error": str(exc)},
                "checked_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        )


@mcp.resource("greeting://{name}")
def personalized_greeting(name: str) -> str:
    """Generate a personalized greeting for the given name."""
    return f"Hello, {name}! Welcome to the Custom Tools MCP Server. How can I help you today?"


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


@mcp.prompt
def research_assistant(topic: str) -> str:
    """Generate a research prompt that leverages Wikipedia and web tools."""
    return f"""You are a helpful research assistant. The user wants to learn about: **{topic}**.

Use the available tools in this order:
1. Call `wikipedia_summary` with topic="{topic}" for a baseline overview.
2. If relevant, use `country_info` for geographic topics.
3. If it's a company, use `stock_quote` with the ticker symbol.
4. Synthesize findings into a clear, well-structured summary with sources cited.

Be concise but thorough. Highlight key facts and suggest follow-up questions."""


@mcp.prompt
def travel_planner(destination: str) -> str:
    """Generate a travel planning prompt using weather and country tools."""
    return f"""You are a travel planning assistant for **{destination}**.

Steps:
1. Use `current_weather` and `weather_forecast` for {destination}.
2. Use `country_info` if you know the country code.
3. Use `exchange_rate` to show typical currency conversions (USD to local currency).
4. Provide packing tips based on weather, best times to visit, and practical travel advice.

Format the response with sections: Weather, Currency, and Recommendations."""


@mcp.prompt
def market_analyst(symbol: str) -> str:
    """Generate a stock analysis prompt using finance tools."""
    return f"""You are a financial analyst reviewing **{symbol}**.

Steps:
1. Call `stock_quote` for the latest price and key metrics.
2. Call `stock_history` with period="3mo" for recent trend context.
3. Summarize: current valuation, recent price movement, and notable highs/lows.
4. Add a brief, balanced outlook (not financial advice).

Keep the analysis factual and data-driven."""


def run() -> None:
    mcp.run(show_banner=False)


if __name__ == "__main__":
    run()
