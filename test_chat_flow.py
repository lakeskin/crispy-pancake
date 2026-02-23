"""Quick test: login + get conversation + messages"""
import httpx
import json

BASE = "http://localhost:8001/api"

# Login
r = httpx.post(f"{BASE}/auth/login", json={"email": "asaadhshm@gmail.com", "password": "Asaad888"}, timeout=15)
assert r.status_code == 200, f"Login failed: {r.status_code}"
token = r.json()["session"]["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("1. Login OK")

# Get conversation
conv_id = "2df2b343-d1f6-4d0e-8ba1-048fb2a3f0f8"
r2 = httpx.get(f"{BASE}/conversations/{conv_id}", headers=headers, timeout=10)
print(f"2. GET conversation: {r2.status_code}")
if r2.status_code == 200:
    d = r2.json()
    print(f"   Keys: {list(d.keys())}")
    print(f"   customer_profile: {d.get('customer_profile')}")
    print(f"   mechanic_profile: {d.get('mechanic_profile')}")
    print(f"   car_issues title: {d.get('car_issues', {}).get('title')}")
else:
    print(f"   FAIL: {r2.text[:300]}")

# Get messages
r3 = httpx.get(f"{BASE}/conversations/{conv_id}/messages?per_page=100", headers=headers, timeout=10)
print(f"3. GET messages: {r3.status_code}")
if r3.status_code == 200:
    md = r3.json()
    if isinstance(md, dict):
        msgs = md.get("messages", [])
    else:
        msgs = md
    print(f"   Message count: {len(msgs)}")
else:
    print(f"   FAIL: {r3.text[:300]}")

# Mark read
r4 = httpx.post(f"{BASE}/conversations/{conv_id}/messages/read", headers=headers, timeout=10)
print(f"4. POST mark read: {r4.status_code}")
if r4.status_code != 200:
    print(f"   FAIL: {r4.text[:300]}")

print("\nDone!")
