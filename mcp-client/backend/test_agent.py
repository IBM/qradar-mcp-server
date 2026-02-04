#!/usr/bin/env python3
"""Test suite for IBM MCP Agent with Claude 3.5 Sonnet."""

import requests
import json
import time
from datetime import datetime

API_URL = "http://9.30.147.112:8000/api/chat/"

# Test queries inspired by Claude 4.5 capabilities
TEST_QUERIES = [
    # Basic data retrieval
    "Get all users from QRadar",
    "Show me the QRadar system version and status",
    "List all offenses",
    
    # Analytical queries
    "How many users are configured in the system?",
    "What is the current deployment status?",
    
    # Action-oriented
    "Can you initiate a full deployment?",
    "Show me open offenses with high magnitude",
    
    # Discovery
    "What endpoints are available for managing users?",
    "Find APIs related to reference data",
    
    # Complex multi-step
    "Get system info and tell me if there are any critical offenses",
    "List all users and identify which ones are administrators",
    
    # Edge cases
    "What can you help me with?",
    "Explain what tools you have access to",
    
    # Specific operations
    "Get the first 5 offenses sorted by start time",
    "Show me the reference data sets",
]

def test_query(query, test_num):
    """Test a single query and analyze response."""
    print(f"\n{'='*80}")
    print(f"TEST #{test_num}: {query}")
    print(f"{'='*80}")
    
    chat_id = f"test-{int(time.time())}-{test_num}"
    
    try:
        response = requests.post(
            API_URL,
            json={"message": query, "chat_id": chat_id},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            content = data['message']['content']
            
            # Analyze response
            has_table = '|' in content
            has_tool_use = 'qradar_' in content.lower() or any(word in content.lower() for word in ['retrieved', 'fetched', 'found'])
            word_count = len(content.split())
            
            print(f"\n✅ Response ({word_count} words):")
            print(content[:500] + "..." if len(content) > 500 else content)
            
            print(f"\n📊 Analysis:")
            print(f"  • Used tools: {'✓' if has_tool_use else '✗'}")
            print(f"  • Has table: {'✓' if has_table else '✗'}")
            print(f"  • Response length: {word_count} words")
            
            return True
        else:
            print(f"❌ HTTP {response.status_code}: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all tests."""
    print(f"\n{'#'*80}")
    print(f"# IBM MCP Agent Test Suite")
    print(f"# Model: Claude 3.5 Sonnet")
    print(f"# Prompt: Refined using Claude 4.5 best practices")
    print(f"# Tests: {len(TEST_QUERIES)}")
    print(f"# Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*80}")
    
    passed = 0
    failed = 0
    
    for i, query in enumerate(TEST_QUERIES, 1):
        if test_query(query, i):
            passed += 1
        else:
            failed += 1
        time.sleep(2)  # Rate limiting
    
    print(f"\n{'#'*80}")
    print(f"# RESULTS")
    print(f"{'#'*80}")
    print(f"✅ Passed: {passed}/{len(TEST_QUERIES)}")
    print(f"❌ Failed: {failed}/{len(TEST_QUERIES)}")
    print(f"Success Rate: {(passed/len(TEST_QUERIES)*100):.1f}%")

if __name__ == "__main__":
    main()
