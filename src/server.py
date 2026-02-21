"""
QRadar MCP Server

4 tools covering all 728 QRadar API v26.0 endpoints.
Supports both stdio (for Claude Desktop) and HTTP/SSE (for containers/web).
MCP OAuth 2.1 compliant (RFC 8414, RFC 7591, PKCE).
"""

import os
import logging
import asyncio
import argparse
from mcp.server import Server
from mcp.server.stdio import stdio_server

from .client import QRadarClient
from .tools import TOOLS, execute_tool
from .oauth import (
    get_metadata,
    register_client,
    authorize_get,
    authorize_post,
    exchange_token,
    verify_access_token,
    www_authenticate_header,
    is_oauth_configured,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("qradar-mcp")

server = Server("qradar-mcp-server")

# API key for HTTP mode (Layer 1 security)
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
    """
    Validate request authentication. Supports dual auth:
    (a) Static API key — Bearer <MCP_API_KEY>
    (b) OAuth JWT access token — Bearer <jwt>
    Returns True if either is valid.
    """
    if not MCP_API_KEY:
        return True  # No API key configured — allow all requests
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return False
    token = auth_header[7:]
    # Check static API key first (fast path)
    if token == MCP_API_KEY:
        return True
    # Check OAuth JWT token
    payload = verify_access_token(token)
    if payload:
        return True
    return False


async def main_http(host: str = "0.0.0.0", port: int = 8001):
    """Run server in HTTP/SSE mode (for containers, web clients)."""
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Route, Mount
    from starlette.responses import JSONResponse, HTMLResponse, Response
    from starlette.middleware import Middleware
    from starlette.middleware.base import BaseHTTPMiddleware
    import uvicorn

    auth_required = bool(MCP_API_KEY)
    oauth_enabled = is_oauth_configured()
    logger.info(f"QRadar MCP Server [HTTP] - 4 tools, 728 endpoints on {host}:{port}")
    logger.info(f"  API key authentication: {'ENABLED' if auth_required else 'DISABLED (set MCP_API_KEY to enable)'}")
    logger.info(f"  OAuth 2.1: {'ENABLED' if oauth_enabled else 'DISABLED (set OAUTH_JWT_SECRET + OAUTH_PASSWORD to enable)'}")
    
    sse = SseServerTransport("/messages/")

    def _base_url(request) -> str:
        """Derive base URL from request (handles proxies)."""
        scheme = request.headers.get("x-forwarded-proto", "http")
        host_header = request.headers.get("host", f"{host}:{port}")
        return f"{scheme}://{host_header}"

    # --- Auth middleware (protects /sse, /messages, /tools) ---
    # Public endpoints: /health, /.well-known/*, /register, /authorize, /token
    _PUBLIC_PATHS = {"/health", "/.well-known/oauth-authorization-server", "/register", "/authorize", "/token"}

    class AuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            if request.url.path in _PUBLIC_PATHS:
                return await call_next(request)
            if not _check_auth(request):
                base = _base_url(request)
                headers = {}
                if oauth_enabled:
                    headers["WWW-Authenticate"] = www_authenticate_header(base)
                return JSONResponse(
                    {"error": "Unauthorized. Provide Authorization: Bearer <token> header."},
                    status_code=401,
                    headers=headers,
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
            "oauth_enabled": oauth_enabled,
        })

    # --- OAuth 2.1 endpoints ---
    async def oauth_metadata(request):
        """RFC 8414 — Authorization Server Metadata."""
        base = _base_url(request)
        return JSONResponse(get_metadata(base))

    async def oauth_register(request):
        """RFC 7591 — Dynamic Client Registration."""
        if not oauth_enabled:
            return JSONResponse({"error": "OAuth not configured"}, status_code=501)
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "invalid_request"}, status_code=400)
        result, status = register_client(body)
        return JSONResponse(result, status_code=status)

    async def oauth_authorize(request):
        """Authorization endpoint — GET shows login, POST processes it."""
        if not oauth_enabled:
            return JSONResponse({"error": "OAuth not configured"}, status_code=501)
        if request.method == "GET":
            params = dict(request.query_params)
            body, status, headers = authorize_get(params)
            return HTMLResponse(body, status_code=status, headers=headers)
        else:  # POST
            form_data = await request.form()
            form = {k: v for k, v in form_data.items()}
            body, status, headers = authorize_post(form)
            if status == 302:
                return Response("", status_code=302, headers=headers)
            return HTMLResponse(body, status_code=status, headers=headers)

    async def oauth_token(request):
        """Token endpoint — exchange code or refresh token."""
        if not oauth_enabled:
            return JSONResponse({"error": "OAuth not configured"}, status_code=501)
        try:
            body = await request.json()
        except Exception:
            # Try form-encoded (some clients send form data)
            try:
                form_data = await request.form()
                body = {k: v for k, v in form_data.items()}
            except Exception:
                return JSONResponse({"error": "invalid_request"}, status_code=400)
        result, status = exchange_token(body)
        return JSONResponse(result, status_code=status)
    
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
            # OAuth 2.1 routes
            Route("/.well-known/oauth-authorization-server", endpoint=oauth_metadata),
            Route("/register", endpoint=oauth_register, methods=["POST"]),
            Route("/authorize", endpoint=oauth_authorize, methods=["GET", "POST"]),
            Route("/token", endpoint=oauth_token, methods=["POST"]),
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
