"""Pydantic models for API requests and responses."""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============== Chat Models ==============

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ToolCallStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    ERROR = "error"


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: Dict[str, Any]
    result: Optional[str] = None
    status: ToolCallStatus = ToolCallStatus.PENDING


class Message(BaseModel):
    id: str
    role: MessageRole
    content: str
    timestamp: datetime
    tool_calls: Optional[List[ToolCall]] = None


class ChatRequest(BaseModel):
    message: str
    chat_id: Optional[str] = None
    qradar_connection_id: Optional[str] = None
    model_id: Optional[str] = None


class ChatResponse(BaseModel):
    chat_id: str
    message: Message


# ============== Connection Models ==============

class QRadarConnectionCreate(BaseModel):
    name: str
    url: str
    token: str
    verify: bool = True
    is_default: bool = False


class QRadarConnection(QRadarConnectionCreate):
    id: str
    status: Optional[str] = None


class QRadarConnectionTest(BaseModel):
    success: bool
    message: str
    version: Optional[str] = None


# ============== MCP Models ==============

class MCPServerCreate(BaseModel):
    name: str
    command: str
    args: List[str] = []
    env: Dict[str, str] = {}
    serverPath: Optional[str] = None
    qradarConnectionId: Optional[str] = None
    containerName: Optional[str] = None
    containerRuntime: Optional[str] = "podman"
    serverMode: Optional[str] = "container"
    transport: Optional[str] = "stdio"  # "stdio" or "http"
    serverUrl: Optional[str] = "http://mcp-server:8001"  # For HTTP transport


class MCPServerStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class MCPTool(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any]


class MCPServer(MCPServerCreate):
    id: str
    status: Optional[str] = "stopped"
    tools: Optional[List[MCPTool]] = None
    container_running: Optional[bool] = None


# ============== LLM Models ==============

class LLMProvider(str, Enum):
    WATSONX = "watsonx"
    OPENROUTER = "openrouter"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


class LLMModelCreate(BaseModel):
    provider: LLMProvider
    name: str
    display_name: str
    model_id: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    project_id: Optional[str] = None  # For Watsonx
    is_default: bool = False


class LLMModel(LLMModelCreate):
    id: str
