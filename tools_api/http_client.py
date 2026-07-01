"""Shared HTTP client helpers with configurable SSL verification."""

import certifi
import httpx

from tools_api.config import settings

DEFAULT_TIMEOUT = 15.0


def _verify_setting() -> bool | str:
    if settings.ssl_verify:
        return certifi.where()
    return False


def async_client(**kwargs) -> httpx.AsyncClient:
    """Create an async HTTP client."""
    kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
    kwargs.setdefault("verify", _verify_setting())
    kwargs.setdefault("follow_redirects", True)
    return httpx.AsyncClient(**kwargs)


def sync_client(**kwargs) -> httpx.Client:
    """Create a sync HTTP client."""
    kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
    kwargs.setdefault("verify", _verify_setting())
    kwargs.setdefault("follow_redirects", True)
    return httpx.Client(**kwargs)
