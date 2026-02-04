#!/usr/bin/env python3
"""Test suite for IBM MCP Chat with various query types."""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://9.30.147.112:8000/api/chat/"

TEST_QUERIES = [
    # Simple data retrieval
    "Get all users from QRadar",
    "Show me system information",
    "List all offenses",
    
    # Complex queries
    "Show me the top 5 offenses with highest magnitude",
    "How many users are configured?",
    "Get offense statistics",
    
    # Action-oriented
    "Can you do a full deploy?",
    "Show me available API endpoints for users",
    "What reference data sets exist?",
    
    # Analysis queries
    "Analyze the security posture",
    "What's the current system health?",
    "Show me recent security events",
    
    # Multi-step queries
    "Get all offenses and tell me which ones are critical",
    "Find all users with admin privileges",
    "Show me the top assets by risk",
    
    # Edge cases
    "What can you help me with?",
    "Explain QRadar deployment process",
    "How do I create a reference set?",
]

def test_query(query: str, test_num: int):
    """Test a single query and return results."""
    chat_id = f"test-{int(time.time())}-{test_num}"
    
    print(f"\n{'='*80}")
    print(f"Test {test_num}: {query}")
    print(f"{'='*80}")
    
    start_time = time.time()
    
    try:
        response = requests.post(
            BASE_URL,
            json={"message": query, "chat_id": chat_id},
            timeout=30
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            content = data.get("message", {}).get("content", "")
            
            # Check if tools were used
            used_tools = "✓ Used tools" if "qradar_" in content.lower() or len(content) > 200 else "✗ No tools used"
            
            print(f"Status: ✓ SUCCESS ({elapsed:.2f}s)")
            print(f"Tools: {used_tools}")
            print(f"Response length: {len(content)} chars")
            print(f"\nResponse preview:")
            print(content[:300] + ("..." if len(content) > 300 else ""))
            
            return {
                "query": query,
                "success": True,
                "elapsed": elapsed,
                "used_tools": "qradar_" in content.lower() or len(content) > 200,
                "length": len(content),
                "refused": "cannot" in content.lower() or "limited" in content.lower()
            }
        else:
            print(f"Status: ✗ FAILED ({response.status_code})")
            print(f"Error: {response.text[:200]}")
            return {
                "query": query,
                "success": False,
                "elapsed": elapsed,
                "error": response.status_code
            }
            
    except Exception as e:
        print(f"Status: ✗ ERROR")
        print(f"Exception: {str(e)[:200]}")
        return {
            "query": query,
            "success": False,
            "error": str(e)
        }

def run_tests():
    """Run all test queries."""
    print(f"\n{'#'*80}")
    print(f"# IBM MCP Chat Test Suite")
    print(f"# Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"# Total queries: {len(TEST_QUERIES)}")
    print(f"{'#'*80}")
    
    results = []
    
    for i, query in enumerate(TEST_QUERIES, 1):
        result = test_query(query, i)
        results.append(result)
        time.sleep(1)  # Rate limiting
    
    # Summary
    print(f"\n{'#'*80}")
    print(f"# TEST SUMMARY")
    print(f"{'#'*80}")
    
    successful = sum(1 for r in results if r.get("success"))
    used_tools = sum(1 for r in results if r.get("used_tools"))
    refused = sum(1 for r in results if r.get("refused"))
    avg_time = sum(r.get("elapsed", 0) for r in results if r.get("success")) / max(successful, 1)
    
    print(f"Success rate: {successful}/{len(results)} ({successful/len(results)*100:.1f}%)")
    print(f"Tool usage: {used_tools}/{successful} ({used_tools/max(successful,1)*100:.1f}%)")
    print(f"Refusals: {refused}/{successful} ({refused/max(successful,1)*100:.1f}%)")
    print(f"Avg response time: {avg_time:.2f}s")
    
    # Detailed results
    print(f"\n{'='*80}")
    print("DETAILED RESULTS:")
    print(f"{'='*80}")
    for i, result in enumerate(results, 1):
        status = "✓" if result.get("success") else "✗"
        tools = "🔧" if result.get("used_tools") else "  "
        refused = "🚫" if result.get("refused") else "  "
        print(f"{status} {tools} {refused} Test {i:2d}: {result['query'][:60]}")
    
    return results

if __name__ == "__main__":
    results = run_tests()
