"""FastMCP middleware that logs tool, resource, and prompt calls to Excel."""

from __future__ import annotations

import contextlib
import json

import mcp.types as mt
from fastmcp.server.middleware.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools.base import ToolResult

from session_logger.excel_logger import format_question, format_response, log_session
from session_logger.network import extract_client_ip_from_headers, get_hostname, get_local_ip


def _client_info() -> tuple[str, str]:
    user_ip = get_local_ip()
    host = get_hostname()

    with contextlib.suppress(Exception):
        from fastmcp.server.dependencies import get_http_request

        request = get_http_request()
        user_ip = extract_client_ip_from_headers(
            dict(request.headers),
            request.client.host if request.client else None,
        )
        host = request.headers.get("host") or host

    return user_ip, host


def _tool_result_text(result: ToolResult) -> str:
    parts: list[str] = []
    for block in result.content:
        if hasattr(block, "text"):
            parts.append(block.text)
        else:
            parts.append(str(block))
    if result.structured_content is not None:
        parts.append(json.dumps(result.structured_content, default=str))
    if result.is_error:
        return f"ERROR: {' | '.join(parts)}"
    return " | ".join(parts) if parts else str(result)


class SessionLoggingMiddleware(Middleware):
    """Log MCP tool, resource, and prompt interactions to Excel."""

    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next: CallNext[mt.CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        params = context.message
        user_ip, host = _client_info()
        question = format_question(
            f"tool:{params.name}",
            {"name": params.name, "arguments": params.arguments},
        )

        try:
            result = await call_next(context)
            response = _tool_result_text(result)
            log_session(user_ip=user_ip, host=host, question=question, response=response)
            return result
        except Exception as exc:
            log_session(
                user_ip=user_ip,
                host=host,
                question=question,
                response=format_response(f"ERROR: {exc}"),
            )
            raise

    async def on_read_resource(
        self,
        context: MiddlewareContext[mt.ReadResourceRequestParams],
        call_next: CallNext[mt.ReadResourceRequestParams, object],
    ) -> object:
        params = context.message
        user_ip, host = _client_info()
        question = format_question("resource:read", {"uri": str(params.uri)})

        try:
            result = await call_next(context)
            log_session(
                user_ip=user_ip,
                host=host,
                question=question,
                response=format_response(result),
            )
            return result
        except Exception as exc:
            log_session(
                user_ip=user_ip,
                host=host,
                question=question,
                response=format_response(f"ERROR: {exc}"),
            )
            raise

    async def on_get_prompt(
        self,
        context: MiddlewareContext[mt.GetPromptRequestParams],
        call_next: CallNext[mt.GetPromptRequestParams, object],
    ) -> object:
        params = context.message
        user_ip, host = _client_info()
        question = format_question(
            f"prompt:{params.name}",
            {"name": params.name, "arguments": params.arguments},
        )

        try:
            result = await call_next(context)
            log_session(
                user_ip=user_ip,
                host=host,
                question=question,
                response=format_response(result),
            )
            return result
        except Exception as exc:
            log_session(
                user_ip=user_ip,
                host=host,
                question=question,
                response=format_response(f"ERROR: {exc}"),
            )
            raise
