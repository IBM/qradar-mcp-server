#!/usr/bin/env python3
"""Test MCP Agent with different models"""
import requests
import time

API = "http://9.30.147.112:8000/api"

MODELS = [
    ("anthropic/claude-sonnet-4.5", "Claude 4.5"),
    ("google/gemini-2.5-flash", "Gemini 2.5 Flash"),
    ("anthropic/claude-3.5-sonnet", "Claude 3.5"),
]

QUERIES = [
    ("Get QRadar system version", "7.5"),
    ("List all users", "admin"),
    ("Show open offenses", "offense"),
]

def set_model(model_id):
    resp = requests.get(f"{API}/connections/models")
    for m in resp.json():
        m["is_default"] = (m.get("model_id") == model_id)
        requests.put(f"{API}/connections/models/{m['id']}", json=m)
    time.sleep(3)

def test_query(query, expected):
    try:
        resp = requests.post(
            f"{API}/chat/",
            json={"message": query, "chat_id": f"mcp-test-{int(time.time())}"},
            timeout=120
        )
        if resp.status_code == 200:
            content = resp.json()["message"]["content"]
            has_data = expected.lower() in content.lower()
            has_table = "|" in content
            return True, has_data, has_table, content[:150]
        return False, False, False, f"HTTP {resp.status_code}"
    except Exception as e:
        return False, False, False, str(e)[:50]

print("=" * 70)
print("MCP AGENT TOOL-CALLING TEST")
print("=" * 70)

results = {}

for model_id, model_name in MODELS:
    print(f"\n>>> Testing {model_name} ({model_id})")
    set_model(model_id)
    
    passed = 0
    for query, expected in QUERIES:
        ok, has_data, has_table, preview = test_query(query, expected)
        if ok and has_data:
            print(f"  [PASS] {query}")
            print(f"         Table: {'Yes' if has_table else 'No'}, Preview: {preview[:80]}...")
            passed += 1
        else:
            print(f"  [FAIL] {query} - {preview}")
    
    results[model_name] = passed

print("\n" + "=" * 70)
print("FINAL RESULTS")
print("=" * 70)
for model, score in results.items():
    status = "WORKING" if score == 3 else "PARTIAL" if score > 0 else "BROKEN"
    print(f"  {model:<25} {score}/3 tests passed  [{status}]")

# Restore default
set_model("anthropic/claude-sonnet-4.5")
print("\nRestored Claude 4.5 as default")
