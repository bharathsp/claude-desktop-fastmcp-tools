"""FastAPI middleware that logs API requests to Excel."""

from __future__ import annotations

import json

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from session_logger.excel_logger import format_question, format_response, log_session
from session_logger.network import extract_client_ip_from_headers, get_hostname

SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/redoc", "/favicon.ico", "/"}


class SessionLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in SKIP_PATHS:
            return await call_next(request)

        user_ip = extract_client_ip_from_headers(
            dict(request.headers),
            request.client.host if request.client else None,
        )
        host = request.headers.get("host") or get_hostname()

        body_bytes = await request.body()

        async def receive():
            return {"type": "http.request", "body": body_bytes, "more_body": False}

        request = Request(request.scope, receive)

        body_text = ""
        if body_bytes:
            try:
                body_text = json.dumps(json.loads(body_bytes.decode("utf-8")))
            except (json.JSONDecodeError, UnicodeDecodeError):
                body_text = body_bytes.decode("utf-8", errors="replace")

        question = format_question(
            f"api:{request.method} {request.url.path}",
            {"query": dict(request.query_params), "body": body_text or None},
        )

        response = await call_next(request)

        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk

        log_session(
            user_ip=user_ip,
            host=host,
            question=question,
            response=format_response(
                {
                    "status_code": response.status_code,
                    "body": response_body.decode("utf-8", errors="replace") or None,
                }
            ),
        )

        return Response(
            content=response_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
