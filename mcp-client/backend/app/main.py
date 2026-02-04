"""
IBM MCP Client - Backend Server

FastAPI application providing:
- Chat API with LLM integration
- MCP server management
- QRadar connection management
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import os

from app.routers import chat, connections, mcp

app = FastAPI(
    title="IBM MCP Client API",
    description="Backend API for IBM MCP Client",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(connections.router, prefix="/api/connections", tags=["connections"])
app.include_router(mcp.router, prefix="/api/mcp", tags=["mcp"])

# Determine static directory (container vs local dev)
static_dir = Path("/app/static")
if not static_dir.exists():
    # Local development - use frontend dist
    local_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
    if local_dist.exists():
        static_dir = local_dist

@app.get("/api")
async def root():
    return {"message": "MCP Client API", "version": "1.0.0"}

@app.get("/api/health")
async def health():
    return {"status": "healthy"}

# Serve static frontend files (must be after API routes)
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")
    
    @app.get("/")
    async def serve_index():
        return FileResponse(static_dir / "index.html")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve React frontend for all non-API routes"""
        if full_path.startswith("api/"):
            return {"error": "Not found"}
        
        file_path = static_dir / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        
        # Serve index.html for SPA routing
        return FileResponse(static_dir / "index.html")
