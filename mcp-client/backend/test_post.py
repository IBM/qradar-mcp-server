#!/usr/bin/env python3
"""Test MCP Agent with POST/DELETE operations"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.langgraph_agent import LangGraphAgent, MCPClient

# Test queries including POST operations
TEST_QUERIES = [
    # GET operations
    ("Get all users from QRadar", "admin", "GET"),
    ("Show system version", "7.5", "GET"),
    
    # POST operations  
    ("Trigger a full deployment", "deploy", "POST"),
    ("Create a reference set named test_ips with IP type", "reference", "POST"),
    ("Add note 'Test note from agent' to offense ID 1", "note", "POST"),
    
    # Complex operations
    ("Get open offenses and show their severity", "offense", "GET"),
    ("Check deployment status", "status", "GET/POST"),
]

async def test_model_comprehensive(model_id, model_name):
    print(f"\n{'='*70}")
    print(f"COMPREHENSIVE TEST: {model_name}")
    print(f"{'='*70}")
    
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
    
    results = []
    
    try:
        await agent.start()
        print(f"Agent started!\n")
        
        for query, expected, op_type in TEST_QUERIES:
            print(f"[{op_type}] {query}")
            try:
                response = await agent.chat(query)
                content = response.get("content", "").lower()
                tools = response.get("tools_called", [])
                
                has_expected = expected.lower() in content
                success = has_expected or "error" not in content[:100].lower()
                
                status = "✅" if success else "❌"
                print(f"  {status} Response: {len(content)} chars, Tools: {len(tools)}")
                print(f"     Preview: {content[:100]}...")
                
                results.append({
                    "query": query,
                    "type": op_type,
                    "success": success,
                    "has_expected": has_expected
                })
                
            except Exception as e:
                print(f"  ❌ Error: {str(e)[:50]}")
                results.append({"query": query, "type": op_type, "success": False, "error": str(e)})
        
        await agent.stop()
        
    except Exception as e:
        print(f"Agent error: {e}")
    
    # Summary
    print(f"\n{'='*70}")
    print(f"RESULTS for {model_name}")
    print(f"{'='*70}")
    
    get_success = sum(1 for r in results if r.get("type") == "GET" and r.get("success"))
    get_total = sum(1 for r in results if r.get("type") == "GET")
    post_success = sum(1 for r in results if "POST" in r.get("type", "") and r.get("success"))
    post_total = sum(1 for r in results if "POST" in r.get("type", ""))
    
    print(f"GET operations:  {get_success}/{get_total}")
    print(f"POST operations: {post_success}/{post_total}")
    print(f"Total: {get_success + post_success}/{len(results)}")
    
    return results

async def main():
    # Test with just one model for now (Claude 4.5)
    model_id = sys.argv[1] if len(sys.argv) > 1 else "anthropic/claude-sonnet-4.5"
    model_name = sys.argv[2] if len(sys.argv) > 2 else model_id
    
    await test_model_comprehensive(model_id, model_name)

if __name__ == "__main__":
    asyncio.run(main())
