"""
MCP Agent - Connects LLM with MCP Server tools

This is our own lightweight agent that:
1. Takes user message
2. Sends to LLM (Watsonx) with tool definitions
3. Parses tool calls from LLM response
4. Executes tools via MCP Server (subprocess/stdio)
5. Returns results to user
"""

import asyncio
import json
import subprocess
import sys
from typing import Optional, Any
from dataclasses import dataclass
import httpx


@dataclass
class ToolCall:
    """Represents a tool call from the LLM."""
    name: str
    arguments: dict


@dataclass 
class AgentResponse:
    """Response from the agent."""
    content: str
    tool_calls: list[ToolCall] = None
    tool_results: list[dict] = None


class WatsonxLLM:
    """Watsonx LLM client for chat completions with tool support."""
    
    def __init__(
        self,
        api_key: str,
        project_id: str,
        model_id: str = "ibm/granite-3-8b-instruct",
        base_url: str = "https://us-south.ml.cloud.ibm.com"
    ):
        self.api_key = api_key
        self.project_id = project_id
        self.model_id = model_id
        self.base_url = base_url
        self._token: Optional[str] = None
        self._token_expiry: float = 0
    
    async def _get_token(self) -> str:
        """Get IAM token, refreshing if needed."""
        import time
        if self._token and time.time() < self._token_expiry - 60:
            return self._token
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://iam.cloud.ibm.com/identity/token",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=f"grant_type=urn:ibm:params:oauth:grant-type:apikey&apikey={self.api_key}"
            )
            data = response.json()
            self._token = data["access_token"]
            self._token_expiry = time.time() + data.get("expires_in", 3600)
            return self._token
    
    def _format_tools_for_prompt(self, tools: list[dict]) -> str:
        """Format tools as part of the system prompt for Granite."""
        if not tools:
            return ""
        
        tool_descriptions = []
        for tool in tools:
            desc = f"- {tool['name']}: {tool.get('description', 'No description')}"
            if 'inputSchema' in tool:
                props = tool['inputSchema'].get('properties', {})
                if props:
                    params = ", ".join([f"{k}: {v.get('type', 'any')}" for k, v in props.items()])
                    desc += f"\n  Parameters: {params}"
            tool_descriptions.append(desc)
        
        return f"""You have access to the following tools to help answer questions about QRadar:

{chr(10).join(tool_descriptions)}

When you need to use a tool, respond ONLY with a JSON object in this exact format (nothing else):
{{"tool_call": {{"name": "tool_name", "arguments": {{"param1": "value1"}}}}}}

After receiving tool results, provide a CLEAN, DIRECT, CONCISE response. Rules:
1. NO thinking out loud - just the answer
2. NO asking follow-up questions like "Would you like A, B, or C?"
3. NO repeating yourself
4. Keep responses under 500 words
5. Use markdown tables when showing data
6. If a tool fails, explain briefly and suggest the correct approach"""

    async def chat(
        self,
        message: str,
        tools: list[dict] = None,
        system_prompt: str = None,
        context: str = None
    ) -> dict:
        """Send a chat message and get response."""
        token = await self._get_token()
        
        # Build the prompt with tool instructions
        tool_prompt = self._format_tools_for_prompt(tools) if tools else ""
        
        full_system = """You are a QRadar security assistant. Be concise and direct.

IMPORTANT ENDPOINT HINTS:
- Users: GET/DELETE /config/access/users/{id} or /staged_config/access/users/{id}
- Offenses: GET/POST /siem/offenses/{id}
- Reference sets: /reference_data/sets/{name}
- System info: /system/about

When deleting users, use: qradar_delete with endpoint="/staged_config/access/users/{id}"
"""
        if system_prompt:
            full_system = system_prompt
        if tool_prompt:
            full_system += f"\n\n{tool_prompt}"
        
        # Add context from previous conversation if available
        context_str = ""
        if context:
            context_str = f"\nContext from previous response:\n{context}\n"
        
        full_prompt = f"{full_system}{context_str}\n\nUser: {message}\n\nAssistant:"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/ml/v1/text/generation?version=2024-01-01",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "model_id": self.model_id,
                    "project_id": self.project_id,
                    "input": full_prompt,
                    "parameters": {
                        "max_new_tokens": 800,
                        "temperature": 0.3,
                        "stop_sequences": ["\nUser:", "\n\nUser:", "Would you like", "Type your", "Waiting"],
                    }
                }
            )
            
            if response.status_code != 200:
                return {"content": f"Error: {response.text}", "tool_call": None}
            
            result = response.json()
            generated_text = result.get("results", [{}])[0].get("generated_text", "")
            
            # Try to parse tool call from response
            tool_call = self._parse_tool_call(generated_text)
            
            return {
                "content": generated_text,
                "tool_call": tool_call
            }
    
    def _parse_tool_call(self, text: str) -> Optional[dict]:
        """Try to parse a tool call from the LLM response."""
        try:
            import re
            
            # Method 1: Look for {"tool_call": {...}} pattern
            # Find the start of tool_call JSON
            tool_call_start = text.find('"tool_call"')
            if tool_call_start != -1:
                # Find the opening brace before tool_call
                brace_start = text.rfind('{', 0, tool_call_start)
                if brace_start != -1:
                    # Extract and parse the JSON
                    depth = 0
                    for i, char in enumerate(text[brace_start:], brace_start):
                        if char == '{':
                            depth += 1
                        elif char == '}':
                            depth -= 1
                            if depth == 0:
                                json_str = text[brace_start:i+1]
                                try:
                                    data = json.loads(json_str)
                                    if "tool_call" in data:
                                        return data["tool_call"]
                                except json.JSONDecodeError:
                                    pass
                                break
            
            # Method 2: Look for {"name": "...", "arguments": {...}} pattern
            name_match = re.search(r'\{\s*"name"\s*:\s*"([^"]+)"', text)
            if name_match:
                start = name_match.start()
                depth = 0
                for i, char in enumerate(text[start:], start):
                    if char == '{':
                        depth += 1
                    elif char == '}':
                        depth -= 1
                        if depth == 0:
                            json_str = text[start:i+1]
                            try:
                                return json.loads(json_str)
                            except json.JSONDecodeError:
                                pass
                            break
                
        except Exception as e:
            print(f"Error parsing tool call: {e}")
        return None


class OpenRouterLLM:
    """OpenRouter LLM client - supports Claude, GPT-4, and other models."""
    
    def __init__(
        self,
        api_key: str,
        model_id: str = "anthropic/claude-sonnet-4",
        base_url: str = "https://openrouter.ai/api/v1"
    ):
        self.api_key = api_key
        self.model_id = model_id
        self.base_url = base_url
    
    def _format_tools_for_openai(self, tools: list[dict]) -> list[dict]:
        """Format tools in OpenAI function calling format."""
        if not tools:
            return []
        
        formatted = []
        for tool in tools:
            formatted.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("inputSchema", {"type": "object", "properties": {}})
                }
            })
        return formatted
    
    async def chat(
        self,
        message: str,
        tools: list[dict] = None,
        system_prompt: str = None,
        context: str = None
    ) -> dict:
        """Send a chat message and get response with native function calling."""
        
        system = system_prompt or """You are a QRadar security assistant. Be concise and direct.

IMPORTANT ENDPOINT HINTS for QRadar API:
- Users: GET/DELETE /config/access/users/{id} or /staged_config/access/users/{id}
- Offenses: GET/POST /siem/offenses/{id}
- Reference sets: /reference_data/sets/{name}
- System info: /system/about

When deleting users, use: qradar_delete with endpoint="/staged_config/access/users/{id}"

Keep responses concise. Use markdown tables for data. Do not ask follow-up questions."""
        
        messages = [{"role": "system", "content": system}]
        
        if context:
            messages.append({"role": "assistant", "content": context})
        
        messages.append({"role": "user", "content": message})
        
        request_body = {
            "model": self.model_id,
            "messages": messages,
            "max_tokens": 1024,
            "temperature": 0.3,
        }
        
        # Add tools if available (native function calling)
        if tools:
            request_body["tools"] = self._format_tools_for_openai(tools)
            request_body["tool_choice"] = "auto"
        
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://ibm-mcp-client.local",
                    "X-Title": "IBM MCP Client"
                },
                json=request_body
            )
            
            if response.status_code != 200:
                return {"content": f"Error: {response.text}", "tool_call": None}
            
            result = response.json()
            choice = result.get("choices", [{}])[0]
            message_resp = choice.get("message", {})
            
            content = message_resp.get("content", "")
            tool_call = None
            
            # Check for native tool calls
            tool_calls = message_resp.get("tool_calls", [])
            if tool_calls:
                tc = tool_calls[0]  # Take first tool call
                func = tc.get("function", {})
                try:
                    tool_call = {
                        "name": func.get("name"),
                        "arguments": json.loads(func.get("arguments", "{}"))
                    }
                    print(f"[OpenRouter] Parsed tool call: {tool_call}")
                except json.JSONDecodeError as e:
                    print(f"[OpenRouter] Failed to parse tool arguments: {e}")
                    pass
            
            return {
                "content": content or "",
                "tool_call": tool_call
            }


class MCPServerClient:
    """Client for communicating with MCP Server via stdio."""
    
    def __init__(
        self,
        command: str,
        args: list[str] = None,
        env: dict = None,
        cwd: str = None
    ):
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.cwd = cwd
        self._process: Optional[subprocess.Popen] = None
        self._request_id = 0
        self._tools_cache: list[dict] = None
    
    async def start(self):
        """Start the MCP server process."""
        import os
        full_env = {**os.environ, **self.env}
        
        self._process = subprocess.Popen(
            [self.command] + self.args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=full_env,
            cwd=self.cwd,
            text=True,
            bufsize=1
        )
        
        # Initialize MCP connection
        await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "ibm-mcp-agent", "version": "1.0.0"}
        })
        
        # Send initialized notification
        await self._send_notification("notifications/initialized", {})
    
    async def stop(self):
        """Stop the MCP server process."""
        if self._process:
            self._process.terminate()
            self._process.wait()
            self._process = None
    
    async def _send_request(self, method: str, params: dict = None) -> dict:
        """Send a JSON-RPC request and get response."""
        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
        }
        if params:
            request["params"] = params
        
        request_line = json.dumps(request) + "\n"
        self._process.stdin.write(request_line)
        self._process.stdin.flush()
        
        # Read response
        response_line = self._process.stdout.readline()
        if response_line:
            return json.loads(response_line)
        return {}
    
    async def _send_notification(self, method: str, params: dict = None):
        """Send a JSON-RPC notification (no response expected)."""
        notification = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params:
            notification["params"] = params
        
        notification_line = json.dumps(notification) + "\n"
        self._process.stdin.write(notification_line)
        self._process.stdin.flush()
    
    async def list_tools(self) -> list[dict]:
        """Get list of available tools from MCP server."""
        if self._tools_cache:
            return self._tools_cache
        
        response = await self._send_request("tools/list", {})
        tools = response.get("result", {}).get("tools", [])
        self._tools_cache = tools
        return tools
    
    async def call_tool(self, name: str, arguments: dict) -> dict:
        """Call a tool on the MCP server."""
        response = await self._send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })
        return response.get("result", {})


class MCPAgent:
    """
    Main agent that orchestrates:
    - LLM (Watsonx) for understanding and decisions
    - MCP Server for tool execution
    """
    
    def __init__(
        self,
        llm: WatsonxLLM,
        mcp_client: MCPServerClient
    ):
        self.llm = llm
        self.mcp = mcp_client
        self._started = False
    
    async def start(self):
        """Initialize the agent and MCP connection."""
        if not self._started:
            await self.mcp.start()
            self._started = True
    
    async def stop(self):
        """Cleanup resources."""
        if self._started:
            await self.mcp.stop()
            self._started = False
    
    async def chat(self, message: str, max_tool_calls: int = 5, stream_callback=None) -> AgentResponse:
        """
        Process a user message:
        1. Get available tools from MCP
        2. Send to LLM with tools
        3. Execute any tool calls
        4. Return final response
        
        Args:
            message: User's message
            max_tool_calls: Maximum number of tool calls to make
            stream_callback: Optional async function to call with progress updates
        """
        if not self._started:
            await self.start()
        
        # Get available tools
        tools = await self.mcp.list_tools()
        
        if stream_callback:
            await stream_callback({"type": "status", "message": "Sending request to LLM..."})
        
        # Send to LLM
        llm_response = await self.llm.chat(message, tools=tools)
        
        tool_calls = []
        tool_results = []
        
        # Handle tool calls (with loop limit)
        iterations = 0
        current_response = llm_response
        
        while current_response.get("tool_call") and iterations < max_tool_calls:
            tool_call = current_response["tool_call"]
            tool_calls.append(ToolCall(
                name=tool_call["name"],
                arguments=tool_call.get("arguments", {})
            ))
            
            if stream_callback:
                await stream_callback({
                    "type": "tool_call",
                    "tool": tool_call["name"],
                    "arguments": tool_call.get("arguments", {})
                })
            
            # Execute tool
            try:
                if stream_callback:
                    await stream_callback({"type": "status", "message": f"Executing {tool_call['name']}..."})
                
                result = await self.mcp.call_tool(
                    tool_call["name"],
                    tool_call.get("arguments", {})
                )
                tool_results.append({
                    "tool": tool_call["name"],
                    "result": result
                })
                
                if stream_callback:
                    await stream_callback({
                        "type": "tool_result",
                        "tool": tool_call["name"],
                        "result": "Success"
                    })
                
                # Send result back to LLM for final response
                if stream_callback:
                    await stream_callback({"type": "status", "message": "Generating response..."})
                
                result_message = f"""Tool '{tool_call["name"]}' returned:
{json.dumps(result, indent=2)}

Based on this result, please provide a helpful response to the user's original question: {message}"""
                
                current_response = await self.llm.chat(result_message, tools=None)
                
            except Exception as e:
                tool_results.append({
                    "tool": tool_call["name"],
                    "error": str(e)
                })
                if stream_callback:
                    await stream_callback({
                        "type": "tool_result",
                        "tool": tool_call["name"],
                        "result": f"Error: {str(e)}"
                    })
                current_response = {"content": f"Error executing tool: {e}", "tool_call": None}
            
            iterations += 1
        
        return AgentResponse(
            content=current_response.get("content", ""),
            tool_calls=tool_calls if tool_calls else None,
            tool_results=tool_results if tool_results else None
        )


# Factory function to create agent with configuration
async def create_agent(
    watsonx_api_key: str,
    watsonx_project_id: str,
    watsonx_model_id: str = "ibm/granite-3-8b-instruct",
    watsonx_url: str = "https://us-south.ml.cloud.ibm.com",
    mcp_command: str = "python3",
    mcp_args: list[str] = None,
    mcp_env: dict = None
) -> MCPAgent:
    """Create and initialize an MCP Agent."""
    
    llm = WatsonxLLM(
        api_key=watsonx_api_key,
        project_id=watsonx_project_id,
        model_id=watsonx_model_id,
        base_url=watsonx_url
    )
    
    mcp_client = MCPServerClient(
        command=mcp_command,
        args=mcp_args or ["-m", "src.server"],
        env=mcp_env or {}
    )
    
    agent = MCPAgent(llm=llm, mcp_client=mcp_client)
    return agent
