#!/usr/bin/env python3
"""
Multi-Model Test Suite for IBM MCP Agent
Tests various models to find the best cost-effective alternative to Claude 4.5
"""

import requests
import json
import time
from datetime import datetime

API_URL = "http://9.30.147.112:8000/api"

# Models to test (provider, model_id, name, cost_per_1k_tokens)
MODELS_TO_TEST = [
    # OpenRouter models
    ("openrouter", "anthropic/claude-sonnet-4.5", "Claude 4.5 (baseline)", 0.018),
    ("openrouter", "anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet", 0.009),
    ("openrouter", "google/gemini-2.5-flash", "Gemini 2.5 Flash", 0.0014),
    ("openrouter", "openai/gpt-4o-mini", "GPT-4o Mini", 0.0006),
    
    # WatsonX models (FREE for enterprise)
    ("watsonx", "meta-llama/llama-3-3-70b-instruct", "Llama 3.3 70B (WatsonX)", 0),
    ("watsonx", "ibm/granite-3-8b-instruct", "Granite 3.3 8B (WatsonX)", 0),
    ("watsonx", "mistralai/mistral-large", "Mistral Large (WatsonX)", 0),
]

# Test queries
TEST_QUERIES = [
    "Get all users from QRadar",
    "Show me the system version",
    "List open offenses",
]

# Config for WatsonX
WATSONX_CONFIG = {
    "api_key": "k2RhDo_zslNjh0iyyWTnGGqHC-2Uad8U7YFSMWXDA_5S",
    "base_url": "https://us-south.ml.cloud.ibm.com",
    "project_id": "ff280e11-e5e9-4148-80e1-4a8dec588396"
}

# Config for OpenRouter
OPENROUTER_CONFIG = {
    "api_key": "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",
    "base_url": "https://openrouter.ai/api/v1"
}


def update_model_config(provider: str, model_id: str) -> bool:
    """Update the default model in MCP client config."""
    try:
        # Get all models
        resp = requests.get(f"{API_URL}/connections/models")
        models = resp.json()
        
        # Find or create the model config
        target_model = None
        for m in models:
            if m.get("model_id") == model_id:
                target_model = m
                break
        
        if not target_model:
            # Create new model config
            if provider == "watsonx":
                config = {
                    "provider": "watsonx",
                    "name": model_id,
                    "display_name": model_id.split("/")[-1],
                    "model_id": model_id,
                    "api_key": WATSONX_CONFIG["api_key"],
                    "base_url": WATSONX_CONFIG["base_url"],
                    "project_id": WATSONX_CONFIG["project_id"],
                    "is_default": True
                }
            else:
                config = {
                    "provider": "openrouter",
                    "name": model_id,
                    "display_name": model_id.split("/")[-1],
                    "model_id": model_id,
                    "api_key": OPENROUTER_CONFIG["api_key"],
                    "base_url": OPENROUTER_CONFIG["base_url"],
                    "project_id": "",
                    "is_default": True
                }
            resp = requests.post(f"{API_URL}/connections/models", json=config)
            if resp.status_code != 200:
                print(f"  ❌ Failed to create model: {resp.text}")
                return False
            target_model = resp.json()
        
        # Set as default
        target_model["is_default"] = True
        resp = requests.put(f"{API_URL}/connections/models/{target_model['id']}", json=target_model)
        
        # Restart agent to pick up new config
        time.sleep(1)
        
        return True
    except Exception as e:
        print(f"  ❌ Config error: {e}")
        return False


def test_query(query: str, timeout: int = 60) -> dict:
    """Test a single query and return results."""
    chat_id = f"test-{int(time.time())}"
    
    try:
        start = time.time()
        response = requests.post(
            f"{API_URL}/chat/",
            json={"message": query, "chat_id": chat_id},
            timeout=timeout
        )
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            content = data['message']['content']
            tool_calls = data['message'].get('tool_calls')
            
            return {
                "success": True,
                "content": content,
                "has_table": '|' in content,
                "has_data": any(word in content.lower() for word in ['user', 'version', 'offense', 'found', 'retrieved']),
                "tool_calls": tool_calls,
                "response_time": elapsed,
                "word_count": len(content.split())
            }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text[:100]}"
            }
    except requests.Timeout:
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def test_model(provider: str, model_id: str, name: str) -> dict:
    """Test a model with all queries."""
    print(f"\n{'='*70}")
    print(f"Testing: {name}")
    print(f"Model: {provider}/{model_id}")
    print(f"{'='*70}")
    
    # Update config
    print("  Configuring model...")
    if not update_model_config(provider, model_id):
        return {"model": name, "success": 0, "failed": len(TEST_QUERIES), "results": []}
    
    time.sleep(3)  # Wait for agent restart
    
    results = []
    success = 0
    
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\n  Query {i}: {query}")
        result = test_query(query)
        results.append(result)
        
        if result["success"]:
            print(f"    ✅ Success ({result['response_time']:.1f}s)")
            print(f"    📊 Table: {'✓' if result['has_table'] else '✗'} | Data: {'✓' if result['has_data'] else '✗'}")
            print(f"    📝 {result['content'][:150]}...")
            success += 1
        else:
            print(f"    ❌ Failed: {result.get('error', 'Unknown')}")
    
    return {
        "model": name,
        "provider": provider,
        "model_id": model_id,
        "success": success,
        "failed": len(TEST_QUERIES) - success,
        "results": results
    }


def main():
    print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║           IBM MCP Agent - Multi-Model Test Suite                  ║
║                                                                       ║
║  Goal: Find the best cost-effective model with tool calling support   ║
║  Tests: {len(TEST_QUERIES)} queries × {len(MODELS_TO_TEST)} models = {len(TEST_QUERIES) * len(MODELS_TO_TEST)} total tests            ║
║  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                               ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    
    all_results = []
    
    for provider, model_id, name, cost in MODELS_TO_TEST:
        result = test_model(provider, model_id, name)
        result["cost"] = cost
        all_results.append(result)
        time.sleep(2)
    
    # Summary
    print(f"\n\n{'#'*70}")
    print(f"#  RESULTS SUMMARY")
    print(f"{'#'*70}\n")
    
    print(f"{'Model':<35} {'Success':<10} {'Cost/1K':<10} {'Status'}")
    print(f"{'-'*35} {'-'*10} {'-'*10} {'-'*20}")
    
    for r in sorted(all_results, key=lambda x: (-x['success'], x['cost'])):
        success_rate = f"{r['success']}/{r['success']+r['failed']}"
        cost_str = "FREE" if r['cost'] == 0 else f"${r['cost']:.4f}"
        status = "✅ WORKS" if r['success'] == len(TEST_QUERIES) else "⚠️ PARTIAL" if r['success'] > 0 else "❌ FAILED"
        print(f"{r['model']:<35} {success_rate:<10} {cost_str:<10} {status}")
    
    # Recommendation
    working_models = [r for r in all_results if r['success'] == len(TEST_QUERIES)]
    if working_models:
        best = min(working_models, key=lambda x: x['cost'])
        print(f"\n🏆 RECOMMENDATION: {best['model']}")
        cost_display = "FREE" if best['cost'] == 0 else f"${best['cost']:.4f}/1K tokens"
        print(f"   Cost: {cost_display}")
        print(f"   Model ID: {best['model_id']}")
    else:
        print("\n⚠️ No model passed all tests. Claude 4.5 is recommended.")


if __name__ == "__main__":
    main()
