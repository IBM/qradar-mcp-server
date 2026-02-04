"""MCP router - manages MCP server Docker containers."""

from fastapi import APIRouter, HTTPException
import uuid
import subprocess
import json
from typing import Optional

from app.models.schemas import MCPServerCreate, MCPServer, MCPServerStatus, MCPTool
from app import config_store

router = APIRouter()


def get_container_runtime():
    """Detect if podman or docker is available."""
    for runtime in ["podman", "docker"]:
        try:
            result = subprocess.run([runtime, "--version"], capture_output=True, timeout=5)
            if result.returncode == 0:
                return runtime
        except:
            continue
    return "docker"


@router.get("/servers", response_model=list[MCPServer])
async def list_servers():
    """List all MCP servers."""
    servers = config_store.get_mcp_servers()
    
    for server in servers:
        # Check transport/serverMode
        is_http_mode = server.get("transport") == "http" or server.get("serverMode") == "http"
        is_container_mode = not is_http_mode and (server.get("serverMode") == "container" or server.get("containerName"))
        
        # If user manually disconnected, keep it disconnected
        if server.get("connected") == False:
            server["status"] = "stopped"
            continue
        
        if is_http_mode:
            # For HTTP mode: check if server is reachable
            server_url = server.get("serverUrl", "http://localhost:8001")
            try:
                import httpx
                resp = httpx.get(f"{server_url}/health", timeout=3)
                server["status"] = "running" if resp.status_code == 200 else "stopped"
                server["container_running"] = None  # Not applicable
            except:
                server["status"] = "stopped"
                server["container_running"] = None
        elif is_container_mode:
            # For container mode: check if container is running
            runtime = server.get("containerRuntime") or get_container_runtime()
            container_name = server.get("containerName") or f"mcp-server-{server.get('id')}"
            
            try:
                result = subprocess.run(
                    [runtime, "inspect", "-f", "{{.State.Running}}", container_name],
                    capture_output=True, text=True, timeout=5
                )
                container_running = result.stdout.strip() == "true"
            except:
                container_running = False
            
            server["container_running"] = container_running
            if not container_running:
                server["status"] = "stopped"
        else:
            # Local process mode
            server["status"] = server.get("status", "stopped")
            server["container_running"] = None
    
    return servers


@router.post("/servers", response_model=MCPServer)
async def create_server(server: MCPServerCreate):
    """Create a new MCP server configuration."""
    server_data = server.model_dump()
    server_data["id"] = str(uuid.uuid4())
    server_data["status"] = "stopped"
    return config_store.save_mcp_server(server_data)


@router.get("/servers/{server_id}")
async def get_server(server_id: str):
    """Get a specific MCP server."""
    servers = config_store.get_mcp_servers()
    server = next((s for s in servers if s["id"] == server_id), None)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    # Check status based on transport mode
    transport = server.get("transport", "stdio")
    
    if transport == "http":
        # HTTP mode - check health endpoint
        try:
            import httpx
            server_url = server.get("serverUrl", "http://localhost:8001")
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{server_url}/health")
                server["status"] = "running" if response.status_code == 200 else "stopped"
        except:
            server["status"] = "stopped"
    else:
        # Container/stdio mode - check container status
        runtime = server.get("containerRuntime") or get_container_runtime()
        container_name = server.get("containerName") or f"mcp-server-{server_id}"
        
        try:
            result = subprocess.run(
                [runtime, "inspect", "-f", "{{.State.Running}}", container_name],
                capture_output=True, text=True, timeout=5
            )
            server["status"] = "running" if result.stdout.strip() == "true" else "stopped"
        except:
            server["status"] = "stopped"
    
    return server


@router.put("/servers/{server_id}")
async def update_server(server_id: str, server: MCPServerCreate):
    """Update an MCP server configuration."""
    server_data = server.model_dump()
    server_data["id"] = server_id
    return config_store.save_mcp_server(server_data)


@router.delete("/servers/{server_id}")
async def delete_server(server_id: str):
    """Delete an MCP server configuration."""
    servers = config_store.get_mcp_servers()
    server = next((s for s in servers if s["id"] == server_id), None)
    
    # Only try to stop if it's not using an existing container
    if server and server.get("serverMode") != "container":
        runtime = server.get("containerRuntime") or get_container_runtime()
        container_name = f"mcp-server-{server_id}"
        try:
            subprocess.run([runtime, "stop", container_name], capture_output=True, timeout=5)
        except:
            pass
    
    config_store.delete_mcp_server(server_id)
    return {"message": "Server deleted"}


@router.post("/servers/{server_id}/start")
async def start_server(server_id: str):
    """Start an MCP server - behavior depends on server mode."""
    servers = config_store.get_mcp_servers()
    server = next((s for s in servers if s["id"] == server_id), None)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    # HTTP mode - just check if server is reachable and mark as connected
    if server.get("transport") == "http" or server.get("serverMode") == "http":
        server_url = server.get("serverUrl", "http://localhost:8001")
        try:
            import httpx
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{server_url}/health")
                if response.status_code == 200:
                    server["status"] = "running"
                    server["connected"] = True  # Mark as connected
                    config_store.save_mcp_server(server)
                    return {"message": "Connected to MCP Server", "status": "running"}
                else:
                    raise HTTPException(status_code=500, detail=f"Server returned status {response.status_code}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Cannot reach server at {server_url}: {str(e)}")
    
    runtime = server.get("containerRuntime") or get_container_runtime()
    
    # Check if using existing container mode (e.g., qradar-mcp-server)
    if server.get("serverMode") == "container" or server.get("containerName"):
        container_name = server.get("containerName", "qradar-mcp-server")
        
        # Verify container exists and is running
        try:
            result = subprocess.run(
                [runtime, "inspect", "-f", "{{.State.Running}}", container_name],
                capture_output=True, text=True, timeout=5
            )
            if result.stdout.strip() == "true":
                # Container is running - update server status
                server["status"] = "running"
                config_store.save_mcp_server(server)
                return {"message": f"Container '{container_name}' is running", "status": "running"}
            else:
                # Container exists but not running - start it
                start_result = subprocess.run(
                    [runtime, "start", container_name],
                    capture_output=True, text=True, timeout=30
                )
                if start_result.returncode == 0:
                    server["status"] = "running"
                    config_store.save_mcp_server(server)
                    return {"message": f"Container '{container_name}' started", "status": "running"}
                else:
                    raise HTTPException(status_code=500, detail=f"Failed to start container: {start_result.stderr}")
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=500, detail="Timeout checking container status")
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail=f"{runtime} not found")
    
    # Legacy mode - create new container
    container_name = f"mcp-server-{server_id}"
    
    # Check if already running
    try:
        result = subprocess.run(
            [runtime, "inspect", "-f", "{{.State.Running}}", container_name],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip() == "true":
            return {"message": "Server already running", "status": "running"}
    except:
        pass
    
    # Get QRadar connection for env vars
    env_vars = []
    if server.get("qradarConnectionId"):
        qradar_conn = config_store.get_qradar_connection(server["qradarConnectionId"])
        if qradar_conn:
            env_vars.extend([
                "-e", f"QRADAR_HOST={qradar_conn.get('url', '')}",
                "-e", f"QRADAR_API_TOKEN={qradar_conn.get('token', '')}"
            ])
    
    server_path = server.get("serverPath", "/opt/ibm-mcp/QRadar-MCP-Server")
    cmd = [
        runtime, "run", "-d", "-i",
        "--name", container_name,
        "-v", f"{server_path}:/app",
        "-w", "/app",
        *env_vars,
        "-e", "PYTHONPATH=/app",
        "ibm-mcp-server:latest"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=True)
        return {"message": "Server started", "status": "running", "container_id": result.stdout.strip()}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Failed to start server: {e.stderr}")


@router.post("/servers/{server_id}/stop")
async def stop_server(server_id: str):
    """Stop an MCP server - behavior depends on server mode."""
    servers = config_store.get_mcp_servers()
    server = next((s for s in servers if s["id"] == server_id), None)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    # HTTP mode - just mark as disconnected (can't actually stop remote server)
    if server.get("transport") == "http" or server.get("serverMode") == "http":
        server["status"] = "stopped"
        server["connected"] = False  # Mark as disconnected
        config_store.save_mcp_server(server)
        return {
            "message": "Disconnected from MCP Server",
            "status": "stopped",
            "note": "Remote server is still running"
        }
    
    runtime = server.get("containerRuntime") or get_container_runtime()
    
    # Container mode - we DON'T stop the container, just mark as disconnected
    # The container runs independently and we just exec into it when chatting
    if server.get("serverMode") == "container" or server.get("containerName"):
        # Just update status - container keeps running
        server["status"] = "stopped"
        config_store.save_mcp_server(server)
        return {
            "message": f"Disconnected from container '{server.get('containerName')}'",
            "status": "stopped",
            "note": "Container is still running. Use podman/docker stop to actually stop it."
        }
    
    # Local process mode - we created the container, so we can stop it
    container_name = f"mcp-server-{server_id}"
    
    try:
        subprocess.run(
            [runtime, "stop", container_name],
            capture_output=True, text=True, timeout=10
        )
        subprocess.run(
            [runtime, "rm", "-f", container_name],
            capture_output=True, text=True, timeout=5
        )
        server["status"] = "stopped"
        config_store.save_mcp_server(server)
        return {"message": "Server stopped", "status": "stopped"}
    except subprocess.CalledProcessError:
        return {"message": "Server not running", "status": "stopped"}


@router.get("/servers/{server_id}/tools")
async def get_server_tools(server_id: str):
    """Get the tools available from an MCP server - not implemented for Docker."""
    raise HTTPException(status_code=501, detail="Tool inspection not yet implemented")
