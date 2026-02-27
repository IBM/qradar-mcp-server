"""
QRadar MCP Server

4 tools covering all 728 QRadar API v26.0 endpoints.
Supports both stdio (for Claude Desktop) and HTTP/SSE (for containers/web).
"""

import os
import logging
import asyncio
import argparse
from mcp.server import Server
from mcp.server.stdio import stdio_server

from .client import QRadarClient
from .tools import TOOLS, execute_tool

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("qradar-mcp")

server = Server("qradar-mcp-server")

# API key for HTTP mode
MCP_API_KEY = os.environ.get("MCP_API_KEY", "")


@server.list_tools()
async def list_tools() -> list:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list:
    from mcp.types import TextContent
    logger.info(f"Tool: {name}")
    
    try:
        client = QRadarClient()
        result = await execute_tool(client, name, arguments)
        
        import json
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    except ValueError as e:
        return [TextContent(type="text", text=f'{{"success": false, "error": "{str(e)}"}}')]
    except Exception as e:
        logger.error(f"Error: {e}")
        return [TextContent(type="text", text=f'{{"success": false, "error": "{str(e)}"}}')]


async def main_stdio():
    """Run server in stdio mode (for Claude Desktop, local CLI)."""
    logger.info("QRadar MCP Server [STDIO] - 4 tools, 728 endpoints")
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def _check_auth(request) -> bool:
    """Validate request authentication via static API key."""
    if not MCP_API_KEY:
        return True  # No auth configured — allow all requests
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return False
    token = auth_header[7:]
    return token == MCP_API_KEY


async def main_http(host: str = "0.0.0.0", port: int = 8001):
    """Run server in HTTP/SSE mode (for containers, web clients)."""
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Route, Mount
    from starlette.responses import JSONResponse
    from starlette.middleware import Middleware
    from starlette.middleware.base import BaseHTTPMiddleware
    import uvicorn

    auth_required = bool(MCP_API_KEY)
    logger.info(f"QRadar MCP Server [HTTP] - 4 tools, 728 endpoints on {host}:{port}")
    logger.info(f"  API key authentication: {'ENABLED' if auth_required else 'DISABLED (set MCP_API_KEY to enable)'}")
    
    sse = SseServerTransport("/messages/")

    # --- Auth middleware (protects /sse, /messages, /tools) ---
    _PUBLIC_PATHS = {"/health"}

    class AuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            if request.url.path in _PUBLIC_PATHS:
                return await call_next(request)
            if not _check_auth(request):
                return JSONResponse(
                    {"error": "Unauthorized. Provide Authorization: Bearer <MCP_API_KEY> header."},
                    status_code=401,
                )
            return await call_next(request)
    
    # --- MCP SSE handlers ---
    async def handle_sse(request):
        async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
            await server.run(streams[0], streams[1], server.create_initialization_options())
    
    async def handle_messages(request):
        await sse.handle_post_message(request.scope, request.receive, request._send)
    
    # --- Health ---
    async def health(request):
        return JSONResponse({
            "status": "healthy",
            "mode": "http",
            "tools": 4,
            "endpoints": 728,
            "auth_required": auth_required,
        })

    # --- Direct REST API endpoints ---
    async def list_tools_api(request):
        """Return list of available tools."""
        tools_list = [
            {
                "name": t.name,
                "description": t.description,
                "inputSchema": t.inputSchema
            }
            for t in TOOLS
        ]
        return JSONResponse({"tools": tools_list})
    
    async def call_tool_api(request):
        """Execute a tool and return result."""
        try:
            body = await request.json()
            tool_name = body.get("name")
            arguments = body.get("arguments", {})
            
            from .client import QRadarClient
            client = QRadarClient(
                host=arguments.get("qradar_host"),
                api_token=arguments.get("qradar_token")
            )
            result = await execute_tool(client, tool_name, arguments)
            
            return JSONResponse({"result": result})
        except SystemExit:
            return JSONResponse({"error": "QRadar credentials not provided. Pass qradar_host and qradar_token in arguments."}, status_code=400)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    middleware = [Middleware(AuthMiddleware)] if auth_required else []

    app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
            Route("/health", endpoint=health),
            Route("/tools", endpoint=list_tools_api),
            Route("/tools/call", endpoint=call_tool_api, methods=["POST"]),
        ],
        middleware=middleware,
    )
    
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server_instance = uvicorn.Server(config)
    await server_instance.serve()


def main():
    parser = argparse.ArgumentParser(description="QRadar MCP Server")
    parser.add_argument("--stdio", action="store_true", help="Run in stdio mode (for Claude Desktop)")
    parser.add_argument("--host", default="0.0.0.0", help="HTTP host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8001, help="HTTP port (default: 8001)")
    args = parser.parse_args()
    
    if args.stdio:
        asyncio.run(main_stdio())
    else:
        # Default: HTTP mode (for containers)
        asyncio.run(main_http(args.host, args.port))


if __name__ == "__main__":
    main()
