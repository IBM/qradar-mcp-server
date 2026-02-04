"""Chat router - handles chat messages and LLM interactions via LangGraph Agent."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator, Optional, Union
import json
import uuid
import os
from datetime import datetime

from app.models.schemas import ChatRequest, ChatResponse, Message, MessageRole
from app.langgraph_agent import LangGraphAgent, create_mcp_client
from app import config_store
from app.session_memory import get_session, clear_session
from app.conversation_handler import needs_clarification, extract_intent

router = APIRouter()


# In-memory chat storage (replace with database in production)
chats: dict = {}

# Agent instance (lazy initialized)
_agent: Optional[LangGraphAgent] = None
_agent_config_hash: Optional[str] = None  # Track config changes


async def get_agent() -> Optional[LangGraphAgent]:
    """Get or create the LangGraph Agent based on configuration."""
    global _agent, _agent_config_hash
    
    # Get current configuration
    models = config_store.get_llm_models()
    mcp_servers = config_store.get_mcp_servers()
    
    # Create a hash of the current config to detect changes
    import hashlib
    config_str = json.dumps({
        "models": models,
        "servers": mcp_servers
    }, sort_keys=True)
    current_hash = hashlib.md5(config_str.encode()).hexdigest()
    
    # Reset agent if config changed
    if _agent is not None and _agent_config_hash != current_hash:
        try:
            await _agent.stop()
        except:
            pass
        _agent = None
    
    if _agent is not None:
        return _agent
    
    _agent_config_hash = current_hash
    
    if not models:
        return None
    
    # Find default model
    llm_config = None
    for model in models:
        if model.get("is_default"):
            llm_config = model
            break
    
    # Fallback to first available model
    if not llm_config and models:
        llm_config = models[0]
    
    if not llm_config:
        return None
    
    # Get MCP server configuration
    if not mcp_servers:
        return None
    
    # Find first active MCP server
    mcp_config = None
    for server in mcp_servers:
        if server.get("is_active", True):
            mcp_config = server
            break
    
    if not mcp_config:
        return None
    
    try:
        # Get environment variables for MCP server
        env_vars = mcp_config.get("env", {})
        if isinstance(env_vars, str):
            env_vars = dict(item.split("=", 1) for item in env_vars.split() if "=" in item)
        
        # Get QRadar credentials to pass to agent
        qradar_credentials = {}
        if mcp_config.get("qradarConnectionId"):
            qradar_conn = config_store.get_qradar_connection(mcp_config["qradarConnectionId"])
            if qradar_conn:
                qradar_credentials = {
                    "host": qradar_conn.get("url", ""),
                    "token": qradar_conn.get("token", "")
                }
                # Also set as env vars for stdio mode backward compatibility
                env_vars["QRADAR_HOST"] = qradar_credentials["host"]
                env_vars["QRADAR_API_TOKEN"] = qradar_credentials["token"]
        
        # Build config for MCP client factory
        transport = mcp_config.get("transport", "stdio")
        client_config = {
            "transport": transport,
            "serverUrl": mcp_config.get("serverUrl", "http://localhost:8001"),
            "command": mcp_config.get("command", "python3"),
            "args": mcp_config.get("args", ["-m", "src.server"]),
            "env": env_vars,
            "serverPath": mcp_config.get("serverPath"),
            "containerName": mcp_config.get("containerName"),
            "containerRuntime": mcp_config.get("containerRuntime", "podman"),
        }
        
        print(f"[Chat] Creating MCP client: transport={transport}, config={client_config}")
        
        mcp_client = create_mcp_client(client_config)
        
        # Determine API settings based on provider
        provider = llm_config.get("provider", "openrouter")
        api_key = llm_config.get("api_key", "")
        model_id = llm_config.get("model_id", "anthropic/claude-sonnet-4")
        
        if provider == "openrouter":
            base_url = "https://openrouter.ai/api/v1"
        elif provider == "openai":
            base_url = "https://api.openai.com/v1"
        else:
            base_url = llm_config.get("base_url", "https://openrouter.ai/api/v1")
        
        # Create LangGraph agent
        _agent = LangGraphAgent(
            api_key=api_key,
            model_id=model_id,
            base_url=base_url,
            mcp_client=mcp_client,
            qradar_credentials=qradar_credentials
        )
        
        return _agent
        
    except Exception as e:
        print(f"Failed to create agent: {e}")
        import traceback
        traceback.print_exc()
        return None


@router.post("/", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """Send a chat message and get AI response."""
    
    # Generate or use existing chat ID
    chat_id = request.chat_id or str(uuid.uuid4())
    
    if chat_id not in chats:
        chats[chat_id] = []
    
    # Get session memory for this chat
    session = get_session(chat_id)
    
    # Check for duplicate queries (return cached response)
    cached_response = session.is_duplicate_query(request.message)
    if cached_response:
        assistant_message = Message(
            id=str(uuid.uuid4()),
            role=MessageRole.ASSISTANT,
            content=cached_response + "\n\n_📋 (cached response)_",
            timestamp=datetime.utcnow()
        )
        return ChatResponse(chat_id=chat_id, message=assistant_message)
    
    # Check if clarification needed
    needs_clarify, clarify_msg = needs_clarification(request.message)
    if needs_clarify and clarify_msg:
        assistant_message = Message(
            id=str(uuid.uuid4()),
            role=MessageRole.ASSISTANT,
            content=clarify_msg,
            timestamp=datetime.utcnow()
        )
        return ChatResponse(chat_id=chat_id, message=assistant_message)
    
    # Create user message
    user_message = Message(
        id=str(uuid.uuid4()),
        role=MessageRole.USER,
        content=request.message,
        timestamp=datetime.utcnow()
    )
    chats[chat_id].append(user_message)
    
    # Try to get agent
    agent = await get_agent()
    
    if agent:
        try:
            # Use the LangGraph agent
            response = await agent.chat(request.message)
            
            # Format response with tool information if available
            content = response.get("content", "")
            tools_called = response.get("tools_called", [])
            
            if tools_called:
                content += "\n\n---\n*Tools used:*\n"
                for tc in tools_called:
                    status = tc.get("status", "unknown")
                    if status == "error":
                        content += f"- {tc['name']}: ❌ Error - {tc.get('error', 'unknown')}\n"
                    else:
                        content += f"- {tc['name']}: ✅ Success\n"
            
            assistant_message = Message(
                id=str(uuid.uuid4()),
                role=MessageRole.ASSISTANT,
                content=content,
                timestamp=datetime.utcnow()
            )
            
            # Store in session memory
            session.add_exchange(
                user_message=request.message,
                assistant_response=content,
                tool_calls=tools_called
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            assistant_message = Message(
                id=str(uuid.uuid4()),
                role=MessageRole.ASSISTANT,
                content=f"Error processing request: {str(e)}",
                timestamp=datetime.utcnow()
            )
    else:
        # Fallback: No agent configured
        assistant_message = Message(
            id=str(uuid.uuid4()),
            role=MessageRole.ASSISTANT,
            content="⚠️ **Agent not configured**\n\nPlease configure:\n1. An LLM model (Settings → Models)\n2. An MCP server (Settings → MCP Servers)\n\nThen try again!",
            timestamp=datetime.utcnow()
        )
    
    chats[chat_id].append(assistant_message)
    
    return ChatResponse(
        chat_id=chat_id,
        message=assistant_message
    )


@router.post("/stream")
async def send_message_stream(request: ChatRequest):
    """Send a chat message and stream the AI response with LangGraph."""
    
    async def generate() -> AsyncGenerator[str, None]:
        # Generate or use existing chat ID
        chat_id = request.chat_id or str(uuid.uuid4())
        
        # Send chat ID first
        yield f"data: {json.dumps({'type': 'chat_id', 'chat_id': chat_id})}\n\n"
        
        # Try to get agent
        agent = await get_agent()
        
        if agent:
            try:
                final_content = ""
                tools_used = []
                
                # Use LangGraph streaming
                async for event in agent.chat_stream(request.message):
                    event_type = event.get("type")
                    
                    if event_type == "status":
                        yield f"data: {json.dumps(event)}\n\n"
                    
                    elif event_type == "tool_call":
                        tools_used.append(event.get("tool", "unknown"))
                        yield f"data: {json.dumps(event)}\n\n"
                    
                    elif event_type == "tool_result":
                        yield f"data: {json.dumps(event)}\n\n"
                    
                    elif event_type == "content_delta":
                        # Streaming content chunks
                        final_content += event.get("delta", "")
                        yield f"data: {json.dumps({'type': 'content_delta', 'delta': event.get('delta', '')})}\n\n"
                    
                    elif event_type in ("content", "content_final"):
                        final_content = event.get("content", "")
                        yield f"data: {json.dumps({'type': 'content', 'content': final_content})}\n\n"
                    
                    elif event_type == "tools_summary":
                        tools = event.get("tools", [])
                        if tools:
                            summary = "\n\n---\n*Tools used:*\n"
                            for t in tools:
                                summary += f"- {t.get('name', 'unknown')}: ✅ {t.get('status', 'done')}\n"
                            yield f"data: {json.dumps({'type': 'tools', 'content': summary})}\n\n"
                    
                    elif event_type == "done":
                        break
                        
            except Exception as e:
                import traceback
                traceback.print_exc()
                yield f"data: {json.dumps({'type': 'error', 'content': f'Error: {str(e)}'})}\n\n"
        else:
            # No agent configured
            error_msg = "⚠️ Agent not configured. Please configure an LLM model and MCP server in Settings."
            yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
        
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/history")
async def get_chat_history():
    """Get all chat history."""
    return {"chats": list(chats.keys())}


@router.get("/{chat_id}")
async def get_chat(chat_id: str):
    """Get a specific chat by ID."""
    if chat_id not in chats:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    return {"chat_id": chat_id, "messages": chats[chat_id]}


@router.delete("/{chat_id}")
async def delete_chat(chat_id: str):
    """Delete a chat by ID."""
    if chat_id not in chats:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    del chats[chat_id]
    return {"message": "Chat deleted"}


@router.post("/reset-agent")
async def reset_agent():
    """Reset the agent (useful after configuration changes)."""
    global _agent
    if _agent:
        try:
            await _agent.stop()
        except:
            pass
        _agent = None
    return {"message": "Agent reset. Will reinitialize on next chat."}


@router.get("/session/{chat_id}/stats")
async def get_session_stats(chat_id: str):
    """Get session memory statistics for a chat."""
    session = get_session(chat_id)
    return session.get_stats()


@router.delete("/session/{chat_id}")
async def clear_session_memory(chat_id: str):
    """Clear session memory for a chat."""
    clear_session(chat_id)
    return {"message": f"Session {chat_id} cleared."}
