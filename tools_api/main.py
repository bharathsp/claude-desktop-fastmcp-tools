"""FastAPI application hosting custom tools as local REST endpoints."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tools_api.config import settings
from tools_api.middleware.session_logging import SessionLoggingMiddleware
from tools_api.routers import finance_tools, math_tools, misc_tools, weather_tools

app = FastAPI(
    title="Custom Tools API",
    description="Local REST API hosting custom tool implementations for the MCP server.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionLoggingMiddleware)

api_prefix = settings.api_prefix
app.include_router(math_tools.router, prefix=api_prefix)
app.include_router(finance_tools.router, prefix=api_prefix)
app.include_router(weather_tools.router, prefix=api_prefix)
app.include_router(misc_tools.router, prefix=api_prefix)


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "service": "tools-api", "version": "1.0.0"}


@app.get("/")
def root() -> dict:
    return {
        "message": "Custom Tools API",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "math": f"{api_prefix}/math",
            "finance": f"{api_prefix}/finance",
            "weather": f"{api_prefix}/weather",
            "misc": f"{api_prefix}/misc",
        },
    }


def run() -> None:
    import uvicorn

    uvicorn.run(
        "tools_api.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    run()
