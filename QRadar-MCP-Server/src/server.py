"""
QRadar MCP Server

4 tools covering all 728 QRadar API v26.0 endpoints.
"""

import logging
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .client import QRadarClient
from .tools import TOOLS, execute_tool

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("qradar-mcp")

server = Server("qradar-mcp-server")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
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


async def main():
    logger.info("QRadar MCP Server - 4 tools, 728 endpoints")
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
