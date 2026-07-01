"""HTTP client for calling the local Tools API from the MCP server."""

from typing import Any

import certifi
import httpx

from mcp_server.config import settings


class ToolsAPIClient:
    def __init__(self) -> None:
        self.base_url = settings.tools_api_base_url.rstrip("/")
        self.api_prefix = settings.tools_api_prefix

    def _url(self, path: str) -> str:
        return f"{self.base_url}{self.api_prefix}{path}"

    def _verify(self) -> bool | str:
        if settings.ssl_verify:
            return certifi.where()
        return False

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0, verify=self._verify()) as client:
            response = await client.get(self._url(path), params=params)
            response.raise_for_status()
            return response.json()

    async def post(self, path: str, json: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0, verify=self._verify()) as client:
            response = await client.post(self._url(path), json=json)
            response.raise_for_status()
            return response.json()

    async def health_check(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=5.0, verify=self._verify()) as client:
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()


tools_client = ToolsAPIClient()
