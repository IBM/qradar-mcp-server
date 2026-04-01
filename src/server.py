"""
QRadar MCP Server

4 tools covering all 728 QRadar API v26.0 endpoints.
Supports three transport modes:
  - stdio        : for Claude Desktop / local CLI
  - sse          : legacy HTTP/SSE (deprecated)
  - streamable-http : modern Streamable HTTP (recommended, default for HTTP)
"""

import os
import logging
import asyncio
import argparse
import uuid
from contextlib import asynccontextmanager

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


# ---------------------------------------------------------------------------
# Transport: STDIO
# ---------------------------------------------------------------------------

async def main_stdio():
    """Run server in stdio mode (for Claude Desktop, local CLI)."""
    logger.info("QRadar MCP Server [STDIO] — 4 tools, 728 endpoints")
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


# ---------------------------------------------------------------------------
# Shared HTTP helpers
# ---------------------------------------------------------------------------

def _check_auth(request) -> bool:
    """Validate request authentication via static API key.

    Returns False (deny) when MCP_API_KEY is not configured — server
    must not be open by default. Set MCP_API_KEY env var to grant access.
    """
    if not MCP_API_KEY:
        return False  # No key configured — deny all requests (fail secure)
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return False
    token = auth_header[7:]
    return token == MCP_API_KEY


def _build_rest_routes():
    """Build the shared REST API routes (health, tools list, tools call)."""
    from starlette.routing import Route
    from starlette.responses import JSONResponse

    auth_required = bool(MCP_API_KEY)

    _UNAUTHORIZED = JSONResponse(
        {"error": "Unauthorized. Provide Authorization: Bearer <MCP_API_KEY> header."},
        status_code=401,
    )

    async def health(request):
        return JSONResponse({
            "status": "healthy",
            "tools": 4,
            "endpoints": 728,
            "auth_required": auth_required,
        })

    async def list_tools_api(request):
        if not _check_auth(request):
            return _UNAUTHORIZED
        tools_list = [
            {
                "name": t.name,
                "description": t.description,
                "inputSchema": t.inputSchema,
            }
            for t in TOOLS
        ]
        return JSONResponse({"tools": tools_list})

    async def call_tool_api(request):
        if not _check_auth(request):
            return _UNAUTHORIZED
        try:
            body = await request.json()
            tool_name = body.get("name")
            arguments = body.get("arguments", {})

            from .client import QRadarClient as _QRC
            client = _QRC(
                host=arguments.get("qradar_host"),
                api_token=arguments.get("qradar_token"),
            )
            result = await execute_tool(client, tool_name, arguments)
            return JSONResponse({"result": result})
        except SystemExit:
            return JSONResponse(
                {"error": "QRadar credentials not provided. Pass qradar_host and qradar_token in arguments."},
                status_code=400,
            )
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    return [
        Route("/health", endpoint=health),
        Route("/tools", endpoint=list_tools_api),
        Route("/tools/call", endpoint=call_tool_api, methods=["POST"]),
    ]


# ---------------------------------------------------------------------------
# Transport: SSE (legacy, deprecated)
# ---------------------------------------------------------------------------

async def main_sse(host: str = "0.0.0.0", port: int = 8001):
    """Run server in HTTP/SSE mode (legacy — deprecated, use streamable-http)."""
    import warnings
    warnings.warn(
        "SSE transport is deprecated and will be removed in a future version. "
        "Use --transport streamable-http instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Route
    from starlette.responses import JSONResponse
    import uvicorn

    auth_required = bool(MCP_API_KEY)
    logger.info(f"QRadar MCP Server [SSE] (deprecated) — 4 tools, 728 endpoints on {host}:{port}")
    logger.info(f"  API key authentication: {'ENABLED' if auth_required else 'LOCKED — set MCP_API_KEY'}")

    sse = SseServerTransport("/messages/")

    _UNAUTHORIZED = JSONResponse(
        {"error": "Unauthorized. Provide Authorization: Bearer <MCP_API_KEY> header."},
        status_code=401,
    )

    async def handle_sse(request):
        if not _check_auth(request):
            return _UNAUTHORIZED
        async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
            await server.run(streams[0], streams[1], server.create_initialization_options())

    async def handle_messages(request):
        if not _check_auth(request):
            return _UNAUTHORIZED
        await sse.handle_post_message(request.scope, request.receive, request._send)

    routes = [
        Route("/sse", endpoint=handle_sse),
        Route("/messages/", endpoint=handle_messages, methods=["POST"]),
    ] + _build_rest_routes()

    app = Starlette(routes=routes)

    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server_instance = uvicorn.Server(config)
    await server_instance.serve()


# ---------------------------------------------------------------------------
# Transport: Streamable HTTP (recommended)
# ---------------------------------------------------------------------------

async def main_streamable_http(host: str = "0.0.0.0", port: int = 8001):
    """Run server in Streamable HTTP mode (modern MCP transport)."""
    from mcp.server.streamable_http import StreamableHTTPServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Route, Mount
    from starlette.responses import JSONResponse
    import uvicorn

    auth_required = bool(MCP_API_KEY)
    logger.info(f"QRadar MCP Server [Streamable HTTP] — 4 tools, 728 endpoints on {host}:{port}")
    logger.info(f"  API key authentication: {'ENABLED' if auth_required else 'LOCKED — set MCP_API_KEY'}")

    session_id = uuid.uuid4().hex
    transport = StreamableHTTPServerTransport(mcp_session_id=session_id)

    _UNAUTHORIZED = JSONResponse(
        {"error": "Unauthorized. Provide Authorization: Bearer <MCP_API_KEY> header."},
        status_code=401,
    )

    async def handle_mcp(request):
        if not _check_auth(request):
            return _UNAUTHORIZED
        await transport.handle_request(request.scope, request.receive, request._send)

    @asynccontextmanager
    async def lifespan(app):
        async with transport.connect() as (read_stream, write_stream):
            # Run MCP server in background task
            async def _run():
                await server.run(read_stream, write_stream, server.create_initialization_options())

            import anyio
            async with anyio.create_task_group() as tg:
                tg.start_soon(_run)
                yield
                tg.cancel_scope.cancel()

    routes = [
        Route("/mcp", endpoint=handle_mcp, methods=["GET", "POST", "DELETE"]),
    ] + _build_rest_routes()

    app = Starlette(routes=routes, lifespan=lifespan)

    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server_instance = uvicorn.Server(config)
    await server_instance.serve()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="QRadar MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default=None,
        help="Transport mode (default: streamable-http for HTTP, stdio with --stdio flag)",
    )
    parser.add_argument("--stdio", action="store_true", help="Run in stdio mode (shortcut for --transport stdio)")
    parser.add_argument("--host", default="0.0.0.0", help="HTTP host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8001, help="HTTP port (default: 8001)")
    args = parser.parse_args()

    # Resolve transport mode
    if args.stdio:
        transport = "stdio"
    elif args.transport:
        transport = args.transport
    else:
        transport = "streamable-http"  # Default for HTTP

    if transport == "stdio":
        asyncio.run(main_stdio())
    elif transport == "sse":
        asyncio.run(main_sse(args.host, args.port))
    elif transport == "streamable-http":
        asyncio.run(main_streamable_http(args.host, args.port))


if __name__ == "__main__":
    main()
