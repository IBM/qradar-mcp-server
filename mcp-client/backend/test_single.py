#!/usr/bin/env python3
"""Quick single model test for MCP Agent"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.langgraph_agent import LangGraphAgent, MCPClient

async def test_one_model(model_id, model_name):
    print(f"Testing {model_name}...")
    
    mcp_client = MCPClient(
        command="python3",
        args=["-m", "src.server"],
        env={
            "QRADAR_HOST": "https://useast.services.cloud.techzone.ibm.com:23768",
            "QRADAR_API_TOKEN": "4edfffda-86ee-4d63-ae3c-740622ba4563",
        },
        cwd="/Users/anujshrivastava/code/QRadar-MCP/QRadar-MCP-Server"
    )
    
    agent = LangGraphAgent(
        api_key="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",
        model_id=model_id,
        base_url="https://openrouter.ai/api/v1",
        mcp_client=mcp_client
    )
    
    try:
        await agent.start()
        print(f"  Agent started, sending query...")
        
        response = await agent.chat("Get all QRadar users")
        content = response.get("content", "")
        tools = response.get("tools_called", [])
        
        has_admin = "admin" in content.lower()
        has_table = "|" in content
        
        print(f"  ✅ Response: {len(content)} chars")
        print(f"  Tools called: {len(tools)}")
        print(f"  Has user data: {has_admin}")
        print(f"  Has table: {has_table}")
        print(f"\n  Preview:\n{content[:400]}...")
        
        await agent.stop()
        return has_admin
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

if __name__ == "__main__":
    import sys
    model_id = sys.argv[1] if len(sys.argv) > 1 else "anthropic/claude-sonnet-4.5"
    name = sys.argv[2] if len(sys.argv) > 2 else model_id
    asyncio.run(test_one_model(model_id, name))
