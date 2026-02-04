#!/usr/bin/env python3
"""
Local test for MCP Agent with different models
Tests tool calling capability directly without HTTP
"""
import asyncio
import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.langgraph_agent import LangGraphAgent, MCPClient

# OpenRouter API key (from config)
OPENROUTER_KEY = "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"

# IBM MCP Server path
MCP_SERVER_PATH = "/Users/anujshrivastava/code/QRadar-MCP/QRadar-MCP-Server"

# QRadar credentials
QRADAR_HOST = "https://useast.services.cloud.techzone.ibm.com:23768"
QRADAR_TOKEN = "4edfffda-86ee-4d63-ae3c-740622ba4563"

# Models to test
MODELS = [
    ("anthropic/claude-sonnet-4.5", "Claude 4.5 Sonnet"),
    ("google/gemini-2.5-flash", "Gemini 2.5 Flash"),
    ("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet"),
]

# Test query
TEST_QUERY = "Get all users from QRadar"
EXPECTED_WORD = "admin"


async def test_model(model_id: str, model_name: str) -> dict:
    """Test a single model with the MCP agent."""
    print(f"\n{'='*60}")
    print(f"Testing: {model_name} ({model_id})")
    print(f"{'='*60}")
    
    # Create MCP client
    mcp_client = MCPClient(
        command="python3",
        args=["-m", "src.server"],
        env={
            "QRADAR_HOST": QRADAR_HOST,
            "QRADAR_API_TOKEN": QRADAR_TOKEN,
        },
        cwd=MCP_SERVER_PATH
    )
    
    # Create agent with this model
    agent = LangGraphAgent(
        api_key=OPENROUTER_KEY,
        model_id=model_id,
        base_url="https://openrouter.ai/api/v1",
        mcp_client=mcp_client
    )
    
    try:
        # Start agent
        print("  Starting agent...")
        await agent.start()
        
        # Run query
        print(f"  Query: {TEST_QUERY}")
        response = await agent.chat(TEST_QUERY)
        
        # Analyze response
        content = response.get("content", "")
        tools_used = response.get("tools_called", [])
        
        has_data = EXPECTED_WORD.lower() in content.lower()
        has_table = "|" in content
        used_tools = len(tools_used) > 0
        
        print(f"  Response length: {len(content)} chars")
        print(f"  Tools called: {len(tools_used)}")
        print(f"  Has expected data: {has_data}")
        print(f"  Has table: {has_table}")
        print(f"\n  Preview: {content[:200]}...")
        
        if tools_used:
            print(f"  Tool calls: {[t.get('name') for t in tools_used]}")
        
        await agent.stop()
        
        return {
            "model": model_name,
            "success": has_data,
            "used_tools": used_tools,
            "has_table": has_table,
            "tools": tools_used
        }
        
    except Exception as e:
        print(f"  ERROR: {e}")
        try:
            await agent.stop()
        except:
            pass
        return {
            "model": model_name,
            "success": False,
            "error": str(e)
        }


async def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║       LOCAL MCP AGENT TEST - Direct Model Testing            ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    results = []
    
    for model_id, model_name in MODELS:
        result = await test_model(model_id, model_name)
        results.append(result)
    
    # Summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    print(f"{'Model':<25} {'Success':<10} {'Tools':<10} {'Status'}")
    print("-" * 60)
    
    for r in results:
        success = "✓" if r.get("success") else "✗"
        tools = "✓" if r.get("used_tools") else "✗"
        status = "✅ WORKS" if r.get("success") else "❌ FAILED"
        print(f"{r['model']:<25} {success:<10} {tools:<10} {status}")
    
    # Best alternative
    working = [r for r in results if r.get("success") and r["model"] != "Claude 4.5 Sonnet"]
    if working:
        print(f"\n🏆 Best alternative: {working[0]['model']}")


if __name__ == "__main__":
    asyncio.run(main())
