#!/usr/bin/env python3
"""Quick multi-model test for IBM MCP"""
import requests
import time
import sys

API = "http://9.30.147.112:8000/api"
QUERY = "Get all users from QRadar"

models = [
    ("Claude 4.5", "anthropic/claude-sonnet-4.5"),
    ("Claude 3.5", "anthropic/claude-3.5-sonnet"),  
    ("Gemini 2.5", "google/gemini-2.5-flash"),
    ("Llama 3.3", "meta-llama/llama-3-3-70b-instruct"),
]

print("=" * 60)
print("MULTI-MODEL TEST")
print("=" * 60)

results = []

for name, model_id in models:
    print(f"\n{name} ({model_id})...")
    sys.stdout.flush()
    
    try:
        resp = requests.get(f"{API}/connections/models", timeout=10)
        existing = resp.json()
        
        found = False
        for m in existing:
            if m.get("model_id") == model_id:
                m["is_default"] = True
                requests.put(f"{API}/connections/models/{m['id']}", json=m, timeout=10)
                found = True
                break
        
        if not found:
            print(f"  Model not configured")
            results.append((name, "NOT CONFIGURED", 0))
            continue
            
        time.sleep(3)
        
        start = time.time()
        resp = requests.post(
            f"{API}/chat/", 
            json={"message": QUERY, "chat_id": f"test-{name.replace(' ','-')}-{int(time.time())}"}, 
            timeout=120
        )
        elapsed = time.time() - start
        
        if resp.status_code == 200:
            content = resp.json()["message"]["content"]
            has_table = "|" in content
            has_users = "admin" in content.lower() or "user" in content.lower()
            print(f"  SUCCESS ({elapsed:.1f}s)")
            print(f"  Table: {has_table}, Users: {has_users}")
            print(f"  Response: {content[:120]}...")
            results.append((name, "SUCCESS", elapsed))
        else:
            print(f"  FAILED: HTTP {resp.status_code}")
            results.append((name, "HTTP ERROR", 0))
            
    except requests.Timeout:
        print(f"  TIMEOUT")
        results.append((name, "TIMEOUT", 0))
    except Exception as e:
        print(f"  ERROR: {e}")
        results.append((name, "ERROR", 0))

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
for name, status, elapsed in results:
    print(f"  {name:<20} {status:<15} {elapsed:.1f}s")
