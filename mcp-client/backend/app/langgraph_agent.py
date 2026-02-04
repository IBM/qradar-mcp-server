"""
LangGraph-based MCP Agent for QRadar

A proper agentic workflow with:
- Tool calling loops (ReAct pattern)
- State management
- Streaming support
- Proper error handling
- Structured logging
- Delete confirmation
"""

import json
import asyncio
import logging
from typing import TypedDict, Annotated, Literal, AsyncGenerator, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import operator

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_openai import ChatOpenAI
import httpx


# ============ Structured Logger ============

class AgentLogger:
    """Structured logging for agent operations."""
    
    def __init__(self, name: str = "agent"):
        self.logger = logging.getLogger(name)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s',
                datefmt='%H:%M:%S'
            ))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def stage(self, stage: str, details: str = ""):
        """Log stage transitions."""
        self.logger.info(f"[STAGE] {stage} {details}")
    
    def tool_call(self, tool: str, args: dict):
        """Log tool calls."""
        args_safe = {k: v for k, v in args.items() if 'token' not in k.lower() and 'key' not in k.lower()}
        self.logger.info(f"[TOOL] Calling {tool} with {json.dumps(args_safe, default=str)[:200]}")
    
    def tool_result(self, tool: str, success: bool, duration_ms: int):
        """Log tool results."""
        status = "✅ SUCCESS" if success else "❌ FAILED"
        self.logger.info(f"[TOOL] {tool} {status} ({duration_ms}ms)")
    
    def llm_call(self, model: str, tokens: int = 0):
        """Log LLM calls."""
        self.logger.info(f"[LLM] Calling {model}")
    
    def error(self, operation: str, error: str):
        """Log errors."""
        self.logger.error(f"[ERROR] {operation}: {error}")
    
    def info(self, message: str):
        """Log general info messages."""
        self.logger.info(f"[INFO] {message}")


# Global logger instance
agent_logger = AgentLogger()


# ============ Delete Operations Detector ============

DANGEROUS_OPERATIONS = [
    "delete", "remove", "drop", "clear", "purge", "destroy",
    "DELETE", "REMOVE", "DROP", "CLEAR", "PURGE", "DESTROY"
]

def is_dangerous_operation(message: str, tool_name: str = "", tool_args: dict = None) -> bool:
    """Detect if this is a dangerous/destructive operation that needs confirmation."""
    message_lower = message.lower()
    
    # Check message content
    for op in DANGEROUS_OPERATIONS:
        if op.lower() in message_lower:
            return True
    
    # Check tool name
    if "delete" in tool_name.lower() or "remove" in tool_name.lower():
        return True
    
    # Check HTTP method in tool args
    if tool_args:
        method = tool_args.get("method", "").upper()
        if method == "DELETE":
            return True
    
    return False


# ============ Error Classification ============

class ErrorType:
    """Error types for classification."""
    TOOL_ERROR = "tool_error"
    AUTH_ERROR = "auth_error"
    TIMEOUT = "timeout"
    CONNECTION = "connection"
    VALIDATION = "validation"
    UNKNOWN = "unknown"

def classify_error(error: Exception) -> tuple[str, str]:
    """Classify an error and return (type, friendly_message)."""
    error_str = str(error).lower()
    
    if "401" in error_str or "unauthorized" in error_str or "forbidden" in error_str:
        return ErrorType.AUTH_ERROR, "Authentication failed. Please check your QRadar API token."
    elif "timeout" in error_str or "timed out" in error_str:
        return ErrorType.TIMEOUT, "The request timed out. QRadar might be busy - try again."
    elif "connection" in error_str or "connect" in error_str or "unreachable" in error_str:
        return ErrorType.CONNECTION, "Cannot connect to the server. Please check if it's running."
    elif "validation" in error_str or "invalid" in error_str or "required" in error_str:
        return ErrorType.VALIDATION, "Invalid request parameters. Please try rephrasing your question."
    elif "404" in error_str or "not found" in error_str:
        return ErrorType.TOOL_ERROR, "The requested resource was not found."
    else:
        return ErrorType.UNKNOWN, f"An error occurred: {str(error)[:200]}"


# ============ State Definition ============

class AgentState(TypedDict):
    """State for the agent graph."""
    messages: Annotated[list[BaseMessage], operator.add]
    tools_called: list[dict]
    requires_confirmation: bool  # For dangerous operations
    confirmed: bool  # User confirmed dangerous operation
    # Phase 5.2: Progress tracking
    current_stage: str  # "understanding", "planning", "executing", "formatting"
    progress_steps: list[str]  # Steps completed so far
    # Phase 5.3: Error tracking
    errors: list[dict]  # History of errors: {"type", "message", "tool", "recoverable"}
    retry_count: int  # Number of retries attempted
    # Phase 5.4: Confidence scoring
    confidence: float  # 0.0 to 1.0 - how confident is the agent


# ============ MCP Client (Stdio) ============

class MCPClientStdio:
    """Client for MCP Server communication via stdio (subprocess/container exec)."""
    
    def __init__(self, command: str, args: list[str], env: dict = None, cwd: str = None, 
                 container_name: str = None, container_runtime: str = "podman"):
        self.command = command
        self.args = args
        self.env = env or {}
        self.cwd = cwd
        self.container_name = container_name
        self.container_runtime = container_runtime or "podman"
        self._process = None
        self._request_id = 0
        self._tools_cache = None
    
    async def start(self):
        """Start MCP server process (via Docker/Podman if container_name provided)."""
        import subprocess
        import os
        
        if self.container_name:
            # Use podman/docker exec to attach to running container
            container_cmd = [
                self.container_runtime, "exec", "-i", 
                self.container_name, "python", "-m", "src.server"
            ]
            print(f"[MCPClientStdio] Starting with command: {' '.join(container_cmd)}")
            self._process = subprocess.Popen(
                container_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
        else:
            # Fallback to local process
            full_env = {**os.environ, **self.env}
            full_cmd = [self.command] + self.args
            print(f"[MCPClientStdio] Starting with command: {' '.join(full_cmd)}")
            self._process = subprocess.Popen(
                full_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=full_env,
                cwd=self.cwd,
                text=True,
                bufsize=1
            )
        
        # Check if process started successfully
        await asyncio.sleep(0.5)
        if self._process.poll() is not None:
            stderr = self._process.stderr.read()
            raise RuntimeError(f"MCP process failed to start: {stderr}")
        
        # Initialize MCP connection
        await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "langgraph-agent", "version": "1.0.0"}
        })
        
        # Send initialized notification
        await self._send_notification("notifications/initialized", {})
    
    async def stop(self):
        """Stop the MCP server."""
        if self._process:
            self._process.terminate()
            self._process.wait()
            self._process = None
    
    async def _send_request(self, method: str, params: dict = None) -> dict:
        """Send JSON-RPC request."""
        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
        }
        if params:
            request["params"] = params
        
        request_str = json.dumps(request) + "\n"
        self._process.stdin.write(request_str)
        self._process.stdin.flush()
        
        response_str = self._process.stdout.readline()
        return json.loads(response_str) if response_str else {}
    
    async def _send_notification(self, method: str, params: dict = None):
        """Send JSON-RPC notification."""
        notification = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params:
            notification["params"] = params
        
        notification_str = json.dumps(notification) + "\n"
        self._process.stdin.write(notification_str)
        self._process.stdin.flush()
    
    async def list_tools(self) -> list[dict]:
        """Get available tools from MCP server."""
        if self._tools_cache:
            return self._tools_cache
        
        response = await self._send_request("tools/list")
        self._tools_cache = response.get("result", {}).get("tools", [])
        return self._tools_cache
    
    async def call_tool(self, name: str, arguments: dict) -> dict:
        """Execute a tool on the MCP server."""
        response = await self._send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })
        return response.get("result", {})


# ============ MCP Client (HTTP/SSE) ============

class MCPClientHTTP:
    """Client for MCP Server communication via simple REST API."""
    
    # Phase 8.1: Timeout configuration
    DEFAULT_TIMEOUT = 120.0  # Match MCP server timeout for slow QRadar queries
    MAX_RETRIES = 3
    
    def __init__(self, server_url: str):
        """
        Args:
            server_url: Base URL of MCP server (e.g., http://mcp-server:8001)
        """
        self.server_url = server_url.rstrip("/")
        self._tools_cache = None
        self._client = None
        self._healthy = False
    
    async def start(self):
        """Initialize connection to MCP server via HTTP."""
        import httpx
        
        print(f"[MCPClientHTTP] Connecting to {self.server_url}")
        self._client = httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT)
        
        # Phase 8.3: Connection check
        await self._check_health()
    
    async def _check_health(self) -> bool:
        """Check if MCP server is healthy."""
        try:
            health_resp = await self._client.get(f"{self.server_url}/health", timeout=5.0)
            health_resp.raise_for_status()
            self._healthy = True
            print(f"[MCPClientHTTP] Server healthy: {health_resp.json()}")
            return True
        except Exception as e:
            self._healthy = False
            raise RuntimeError(f"MCP server not reachable at {self.server_url}: {e}")
    
    async def ensure_connected(self):
        """Ensure connection is healthy before operations."""
        if not self._healthy:
            await self._check_health()
    
    async def stop(self):
        """Close HTTP connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def list_tools(self) -> list[dict]:
        """Get available tools from MCP server."""
        if self._tools_cache:
            return self._tools_cache
        
        response = await self._client.get(f"{self.server_url}/tools")
        response.raise_for_status()
        self._tools_cache = response.json().get("tools", [])
        return self._tools_cache
    
    async def call_tool(self, name: str, arguments: dict) -> dict:
        """Execute a tool on the MCP server."""
        response = await self._client.post(
            f"{self.server_url}/tools/call",
            json={"name": name, "arguments": arguments}
        )
        response.raise_for_status()
        return response.json().get("result", {})


# ============ MCP Client Factory ============

def create_mcp_client(config: dict):
    """Create appropriate MCP client based on transport mode.
    
    Args:
        config: MCP server configuration dict with:
            - transport: "stdio" or "http"
            - serverUrl: HTTP URL (for http transport)
            - command, args, containerName, etc. (for stdio transport)
    
    Returns:
        MCPClientStdio or MCPClientHTTP instance
    """
    transport = config.get("transport", "stdio")
    
    if transport == "http":
        server_url = config.get("serverUrl", "http://localhost:8001")
        return MCPClientHTTP(server_url=server_url)
    else:
        # stdio mode (default)
        return MCPClientStdio(
            command=config.get("command", "python"),
            args=config.get("args", ["-m", "src.server"]),
            env=config.get("env", {}),
            cwd=config.get("serverPath"),
            container_name=config.get("containerName"),
            container_runtime=config.get("containerRuntime", "podman")
        )


# ============ LangGraph Agent ============

class LangGraphAgent:
    """LangGraph-based agent for IBM MCP."""
    
    SYSTEM_PROMPT = """You are a security assistant that helps users manage their QRadar SIEM system via MCP tools.

CRITICAL RULES:
1. ALWAYS add ?limit=10 for list queries to avoid fetching millions of records
2. For counts, use ?limit=1 and report the total from response, don't fetch all
3. Be concise and direct - JUST DO IT, don't ask for confirmation unless it's a DELETE operation
4. When user says "get top X" or "show me X" → immediately call the tool, don't ask permission
5. Only ask follow-up questions if the request is genuinely ambiguous (missing critical info)

ENDPOINT DISCOVERY (if qradar_get fails):
- Immediately use qradar_discover with resource name
- Use first matching endpoint
- Retry qradar_get automatically
- Do NOT ask user for help

COMMON ENDPOINTS:
- rules → /analytics/rules
- log sources → /config/event_sources/log_source_management/log_sources  
- services → /system/servers
- license → /system/about
- performance → /system/servers (has performance metrics)

MANDATORY TABLE FORMATTING:
When you receive structured data (lists, arrays, objects), you MUST format as a complete markdown table:

**Required structure:**
| Column1 | Column2 | Column3 |
|---------|---------|---------|
| data1   | data2   | data3   |
| data1   | data2   | data3   |

**Rules:**
- MUST include separator row with dashes: |---------|
- MUST fill in ALL data rows, not just headers
- NEVER output incomplete tables (headers only)
- If data has 5 items, table MUST have 5 data rows plus header
- Use **bold** for important values in cells

COMPLETE EXAMPLE:
User: "list 5 offenses"
Response:
| ID  | Description | Severity |
|-----|-------------|----------|
| 97  | TCP Scan    | 8        |
| 96  | UDP Scan    | 8        |
| 95  | DoS Attack  | 9        |

SINGLE ITEM FORMAT (use vertical key-value):
User: "get offense 97"
Response:
| Property | Value |
|----------|-------|
| ID | 97 |
| Description | TCP Scan |
| Severity | 8 |

COUNT QUERIES:
- When user asks "how many" or "count" - use the [Total: X items] from response
- Answer: "There are **X** offenses" - do NOT show the full table
- Example: "There are **143** open offenses"

ENDPOINT DISCOVERY:
- If qradar_get fails with "not found", use qradar_discover to find correct endpoint
- Common endpoints: /siem/offenses, /asset_model/assets, /config/domain_management/domains

OTHER FORMATTING:
- **Code blocks**: Use ```language``` for code, JSON, queries
- **Bullets**: Use for steps or multiple items
- **Bold**: Use **bold** for counts, names
- **Headers**: Use ### for sections

QUERY LIMITS:
- Always use ?limit=10 for initial queries
- Never fetch unlimited data
- Summarize: "Found **X** items, showing first 10"

When using tools:
- Use qradar_get for reading data (WITH LIMITS!)
- Use qradar_post for creating/updating  
- Use qradar_delete for removing items (dangerous - confirm first)
- If unsure about endpoint, use qradar_discover FIRST"""
    
    def __init__(
        self,
        api_key: str,
        model_id: str = "anthropic/claude-sonnet-4",
        base_url: str = "https://openrouter.ai/api/v1",
        mcp_client = None,  # MCPClientStdio or MCPClientHTTP
        qradar_credentials: dict = None  # {"host": "...", "token": "..."}
    ):
        self.api_key = api_key
        self.model_id = model_id
        self.base_url = base_url
        self.mcp_client = mcp_client
        self.qradar_credentials = qradar_credentials or {}
        self._graph = None
        self._tools = []
        self._llm = None
        self._started = False
    
    async def start(self):
        """Initialize the agent."""
        if self._started:
            return
        
        # Start MCP client
        if self.mcp_client:
            await self.mcp_client.start()
            self._tools = await self.mcp_client.list_tools()
        
        # Create LLM
        self._llm = ChatOpenAI(
            model=self.model_id,
            openai_api_key=self.api_key,
            openai_api_base=self.base_url,
            temperature=0.3,
            max_tokens=2048,
            default_headers={
                "HTTP-Referer": "https://ibm-mcp-client.local",
                "X-Title": "IBM MCP Client"
            }
        )
        
        # Bind tools to LLM
        if self._tools:
            openai_tools = self._convert_tools_to_openai_format()
            self._llm = self._llm.bind_tools(openai_tools)
        
        # Build the graph
        self._build_graph()
        self._started = True
    
    async def stop(self):
        """Stop the agent."""
        if self.mcp_client:
            await self.mcp_client.stop()
        self._started = False
    
    def _convert_tools_to_openai_format(self) -> list[dict]:
        """Convert MCP tools to OpenAI function format."""
        openai_tools = []
        for tool in self._tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("inputSchema", {"type": "object", "properties": {}})
                }
            })
        return openai_tools
    
    def _build_graph(self):
        """Build the LangGraph workflow."""
        
        # Agent node - calls LLM
        async def agent(state: AgentState) -> dict:
            agent_logger.stage("AGENT", "Processing with LLM")
            messages = state["messages"]
            
            # Add system message at the start
            full_messages = [SystemMessage(content=self.SYSTEM_PROMPT)] + messages
            
            agent_logger.llm_call(self.model_id)
            response = await self._llm.ainvoke(full_messages)
            return {"messages": [response], "tools_called": []}
        
        # Tool execution node
        async def execute_tools(state: AgentState) -> dict:
            import time
            agent_logger.stage("TOOLS", "Executing tool calls")
            messages = state["messages"]
            last_message = messages[-1]
            tools_called = state.get("tools_called", [])
            
            if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
                return {"messages": [], "tools_called": tools_called}
            
            tool_messages = []
            for tool_call in last_message.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                # Inject QRadar credentials if available
                if self.qradar_credentials:
                    if self.qradar_credentials.get("host"):
                        tool_args["qradar_host"] = self.qradar_credentials["host"]
                    if self.qradar_credentials.get("token"):
                        tool_args["qradar_token"] = self.qradar_credentials["token"]
                
                # Check for dangerous operations
                is_dangerous = is_dangerous_operation("", tool_name, tool_args)
                
                tools_called.append({
                    "name": tool_name, 
                    "args": tool_args, 
                    "status": "running",
                    "dangerous": is_dangerous
                })
                
                agent_logger.tool_call(tool_name, tool_args)
                start_time = time.time()
                
                # Execute via MCP
                try:
                    result = await self.mcp_client.call_tool(tool_name, tool_args)
                    
                    # Extract data from wrapper if present
                    if isinstance(result, dict) and "data" in result:
                        result = result["data"]
                    
                    # Helper: Flatten nested values (arrays, dicts) to strings
                    def flatten_value(v):
                        if isinstance(v, list):
                            if len(v) == 0:
                                return ""
                            elif len(v) == 1:
                                return flatten_value(v[0])
                            elif all(isinstance(x, (str, int, float)) for x in v):
                                return ", ".join(str(x) for x in v[:5])
                            else:
                                return f"[{len(v)} items]"
                        elif isinstance(v, dict):
                            # Extract common fields like 'name', 'id', 'value'
                            for key in ['name', 'hostname', 'value', 'id', 'description']:
                                if key in v:
                                    return str(v[key])
                            return f"{{...}}"
                        elif v is None:
                            return ""
                        return str(v)
                    
                    # SAFEGUARD: Simplify large objects by selecting only key fields
                    if isinstance(result, list) and len(result) > 0:
                        total_count = len(result)
                        
                        # Limit number of items
                        if len(result) > 20:
                            result = result[:20]
                            agent_logger.info(f"Truncated {total_count} results to 20")
                        
                        # Simplify each item if it has too many fields
                        if isinstance(result[0], dict) and len(result[0].keys()) > 8:
                            endpoint = tool_args.get('endpoint', '').lower()
                            
                            # For offenses: keep only essential fields
                            if 'offense' in endpoint:
                                key_fields = ['id', 'description', 'status', 'severity', 'magnitude', 'event_count', 'categories']
                            # For assets: keep essential fields
                            elif 'asset' in endpoint:
                                key_fields = ['id', 'hostnames', 'interfaces', 'domain_id', 'risk_score_sum']
                            # For log_sources:
                            elif 'log_source' in endpoint:
                                key_fields = ['id', 'name', 'type_name', 'status', 'enabled']
                            # For users:
                            elif 'user' in endpoint:
                                key_fields = ['id', 'username', 'email', 'user_role']
                            else:
                                # Generic: take first 6 fields
                                key_fields = list(result[0].keys())[:6]
                            
                            # Flatten and select fields
                            result = [{k: flatten_value(item.get(k)) for k in key_fields if k in item} for item in result]
                            agent_logger.info(f"Simplified {len(result)} items to {len(key_fields)} fields each")
                        else:
                            # Flatten values even for smaller objects
                            result = [{k: flatten_value(v) for k, v in item.items()} for item in result]
                        
                        # Add total count info
                        result_str = f"[Total: {total_count} items, showing {len(result)}]\n" + json.dumps(result, indent=2, ensure_ascii=False)
                    
                    elif isinstance(result, dict):
                        # Single item - flatten nested values
                        result = {k: flatten_value(v) for k, v in result.items()}
                        result_str = json.dumps(result, indent=2, ensure_ascii=False)
                    
                    elif isinstance(result, str) and len(result) > 10000:
                        total_len = len(result)
                        result_str = result[:10000] + f"\n[TRUNCATED: {total_len} chars total]"
                        agent_logger.info(f"Truncated response from {total_len} to 10000 chars")
                    else:
                        result_str = json.dumps(result, indent=2, ensure_ascii=False) if not isinstance(result, str) else result
                    
                    # Sanitize JSON - remove control characters that break parsing
                    result_str = result_str.replace('\n', '\\n').replace('\r', '').replace('\t', ' ')
                    
                    tools_called[-1]["status"] = "success"
                    duration_ms = int((time.time() - start_time) * 1000)
                    agent_logger.tool_result(tool_name, True, duration_ms)
                except Exception as e:
                    result_str = f"Error: {str(e)}"
                    tools_called[-1]["status"] = "error"
                    tools_called[-1]["error"] = str(e)
                    duration_ms = int((time.time() - start_time) * 1000)
                    agent_logger.tool_result(tool_name, False, duration_ms)
                    agent_logger.error(tool_name, str(e))
                
                tool_messages.append(
                    ToolMessage(content=result_str, tool_call_id=tool_call["id"])
                )
            
            return {"messages": tool_messages, "tools_called": tools_called}
        
        # Router - decide next step
        def should_continue(state: AgentState) -> Literal["tools", "end"]:
            messages = state["messages"]
            last_message = messages[-1]
            
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
            return "end"
        
        # Build graph
        workflow = StateGraph(AgentState)
        
        workflow.add_node("agent", agent)
        workflow.add_node("tools", execute_tools)
        
        workflow.set_entry_point("agent")
        
        workflow.add_conditional_edges(
            "agent",
            should_continue,
            {"tools": "tools", "end": END}
        )
        
        workflow.add_edge("tools", "agent")
        
        self._graph = workflow.compile()
    
    async def chat(self, message: str, confirmed: bool = False) -> dict:
        """Process a chat message (non-streaming)."""
        agent_logger.stage("CHAT_START", f"Message: {message[:100]}...")
        
        if not self._started:
            await self.start()
        
        # Check if this is a dangerous operation
        if is_dangerous_operation(message) and not confirmed:
            agent_logger.stage("CONFIRMATION_REQUIRED", "Dangerous operation detected")
            return {
                "content": "⚠️ **Confirmation Required**\n\nThis appears to be a destructive operation (delete/remove). Please confirm you want to proceed.",
                "tools_called": [],
                "requires_confirmation": True,
                "original_message": message
            }
        
        initial_state: AgentState = {
            "messages": [HumanMessage(content=message)],
            "tools_called": [],
            "requires_confirmation": False,
            "confirmed": confirmed
        }
        
        result = await self._graph.ainvoke(initial_state)
        
        # Extract final response
        final_message = result["messages"][-1]
        content = final_message.content if hasattr(final_message, "content") else str(final_message)
        
        agent_logger.stage("CHAT_END", f"Tools called: {len(result.get('tools_called', []))}")
        
        return {
            "content": content,
            "tools_called": result.get("tools_called", [])
        }
    
    async def chat_stream(self, message: str, confirmed: bool = False) -> AsyncGenerator[dict, None]:
        """Process a chat message with streaming updates."""
        agent_logger.stage("STREAM_START", f"Message: {message[:100]}...")
        
        if not self._started:
            await self.start()
        
        # Check if this is a dangerous operation
        if is_dangerous_operation(message) and not confirmed:
            agent_logger.stage("CONFIRMATION_REQUIRED", "Dangerous operation detected")
            yield {"type": "confirmation_required", 
                   "message": "⚠️ **Confirmation Required**\n\nThis appears to be a destructive operation. Please confirm you want to proceed.",
                   "original_message": message}
            yield {"type": "done"}
            return
        
        initial_state: AgentState = {
            "messages": [HumanMessage(content=message)],
            "tools_called": [],
            "requires_confirmation": False,
            "confirmed": confirmed
        }
        
        yield {"type": "status", "message": "🤔 Analyzing your request..."}
        
        final_content = ""
        tools_called = []
        streaming_response = False  # Track if we're streaming the final response
        current_tool = None
        tool_count = 0
        
        async for event in self._graph.astream_events(initial_state, version="v2"):
            kind = event["event"]
            name = event.get("name", "")
            
            if kind == "on_chat_model_start":
                if not streaming_response and not current_tool:
                    yield {"type": "status", "message": "💭 Thinking..."}
            
            elif kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk:
                    # Check for tool calls being made
                    if hasattr(chunk, "tool_call_chunks") and chunk.tool_call_chunks:
                        for tc in chunk.tool_call_chunks:
                            if tc.get("name") and tc["name"] not in [t["name"] for t in tools_called]:
                                current_tool = tc["name"]
                                tool_count += 1
                                tools_called.append({"name": tc["name"], "status": "calling"})
                                yield {"type": "status", "message": f"🔧 Calling tool: {tc['name']}"}
                                yield {"type": "tool_call", "tool": tc["name"]}
                    
                    # Stream content (only if not a tool call response)
                    if hasattr(chunk, "content") and chunk.content:
                        content = chunk.content
                        # Skip raw JSON tool results
                        if not content.strip().startswith('{') and not '"content":' in content:
                            if not streaming_response:
                                yield {"type": "status", "message": "✍️ Generating response..."}
                            streaming_response = True
                            current_tool = None
                            final_content += content
                            yield {"type": "content_delta", "delta": content}
            
            elif kind == "on_chain_start" and name == "tools":
                # Tools chain starting
                if current_tool:
                    yield {"type": "status", "message": f"⏳ Executing: {current_tool}"}
                    yield {"type": "tool_running", "tool": current_tool}
            
            elif kind == "on_chain_end" and name == "tools":
                # Tools execution completed
                if current_tool:
                    for tc in tools_called:
                        if tc["name"] == current_tool:
                            tc["status"] = "success"
                    yield {"type": "status", "message": f"✅ {current_tool} completed"}
                    yield {"type": "tool_result", "tool": current_tool, "result": "Success"}
            
            elif kind == "on_chain_end" and name == "LangGraph":
                # Final output from the graph
                output = event.get("data", {}).get("output", {})
                if isinstance(output, dict) and "messages" in output:
                    messages = output["messages"]
                    if messages:
                        last_msg = messages[-1]
                        if hasattr(last_msg, "content") and last_msg.content:
                            if not streaming_response or last_msg.content != final_content:
                                final_content = last_msg.content
                                yield {"type": "content", "content": final_content}
        
        # Final content if needed
        if final_content and not streaming_response:
            yield {"type": "content_final", "content": final_content}
        
        # Tools summary
        if tools_called:
            yield {"type": "tools_summary", "tools": tools_called}
        
        yield {"type": "done"}
