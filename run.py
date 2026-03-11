"""WXO STDIO entry point for QRadar MCP Server."""
import os
import sys
import asyncio

# Force STDIO mode
from src.server import main_stdio

if __name__ == "__main__":
    asyncio.run(main_stdio())
