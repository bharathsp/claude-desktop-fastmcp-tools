@echo off
REM Start the MCP Server (run in another terminal, after Tools API is up)
cd /d "%~dp0.."
call venv\Scripts\activate.bat
python -m mcp_server.server
