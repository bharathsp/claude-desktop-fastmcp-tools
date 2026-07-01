@echo off
REM Launcher for Claude Desktop — ensures correct working directory and env vars.
cd /d "%~dp0.."
set "MCP_TOOLS_API_BASE_URL=http://127.0.0.1:8100"
set "FASTMCP_SHOW_SERVER_BANNER=false"
"%~dp0..\venv\Scripts\python.exe" -m mcp_server.server
