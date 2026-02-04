"""
Configuration storage using JSON file.
Stores all settings in ~/.ibm-mcp/config.json
"""

import json
import os
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".ibm-mcp"
CONFIG_FILE = CONFIG_DIR / "config.json"


def _ensure_config_dir():
    """Create config directory if it doesn't exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _load_config() -> dict:
    """Load config from file."""
    _ensure_config_dir()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_config(config: dict):
    """Save config to file."""
    _ensure_config_dir()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


# ============== QRadar Connections ==============

def get_qradar_connections() -> list[dict]:
    """Get all QRadar connections."""
    config = _load_config()
    return config.get("qradar_connections", [])


def save_qradar_connection(conn: dict) -> dict:
    """Save a QRadar connection."""
    config = _load_config()
    connections = config.get("qradar_connections", [])
    
    # Check if updating existing
    existing_idx = next((i for i, c in enumerate(connections) if c["id"] == conn.get("id")), None)
    
    if existing_idx is not None:
        connections[existing_idx] = conn
    else:
        connections.append(conn)
    
    # Handle default flag
    if conn.get("is_default"):
        for c in connections:
            if c["id"] != conn["id"]:
                c["is_default"] = False
    
    config["qradar_connections"] = connections
    _save_config(config)
    return conn


def delete_qradar_connection(conn_id: str) -> bool:
    """Delete a QRadar connection."""
    config = _load_config()
    connections = config.get("qradar_connections", [])
    config["qradar_connections"] = [c for c in connections if c["id"] != conn_id]
    _save_config(config)
    return True


def get_qradar_connection(conn_id: str) -> dict | None:
    """Get a specific QRadar connection."""
    connections = get_qradar_connections()
    return next((c for c in connections if c["id"] == conn_id), None)


# ============== MCP Servers ==============

def get_mcp_servers() -> list[dict]:
    """Get all MCP server configs."""
    config = _load_config()
    return config.get("mcp_servers", [])


def save_mcp_server(server: dict) -> dict:
    """Save an MCP server config."""
    config = _load_config()
    servers = config.get("mcp_servers", [])
    
    existing_idx = next((i for i, s in enumerate(servers) if s["id"] == server.get("id")), None)
    
    if existing_idx is not None:
        servers[existing_idx] = server
    else:
        servers.append(server)
    
    config["mcp_servers"] = servers
    _save_config(config)
    return server


def delete_mcp_server(server_id: str) -> bool:
    """Delete an MCP server config."""
    config = _load_config()
    servers = config.get("mcp_servers", [])
    config["mcp_servers"] = [s for s in servers if s["id"] != server_id]
    _save_config(config)
    return True


# ============== LLM Models ==============

def get_llm_models() -> list[dict]:
    """Get all LLM model configs."""
    config = _load_config()
    return config.get("llm_models", [])


def save_llm_model(model: dict) -> dict:
    """Save an LLM model config."""
    config = _load_config()
    models = config.get("llm_models", [])
    
    existing_idx = next((i for i, m in enumerate(models) if m["id"] == model.get("id")), None)
    
    if existing_idx is not None:
        models[existing_idx] = model
    else:
        models.append(model)
    
    # Handle default flag
    if model.get("is_default"):
        for m in models:
            if m["id"] != model["id"]:
                m["is_default"] = False
    
    config["llm_models"] = models
    _save_config(config)
    return model


def delete_llm_model(model_id: str) -> bool:
    """Delete an LLM model config."""
    config = _load_config()
    models = config.get("llm_models", [])
    config["llm_models"] = [m for m in models if m["id"] != model_id]
    _save_config(config)
    return True


# ============== Utility ==============

def get_default_qradar() -> dict | None:
    """Get the default QRadar connection."""
    connections = get_qradar_connections()
    return next((c for c in connections if c.get("is_default")), connections[0] if connections else None)


def get_default_model() -> dict | None:
    """Get the default LLM model."""
    models = get_llm_models()
    return next((m for m in models if m.get("is_default")), models[0] if models else None)
