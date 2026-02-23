"""Comprehensive test of all SalikChat API endpoints including uploads."""
import httpx
import io
import sys
from dotenv import load_dotenv

load_dotenv()

BASE = "http://localhost:8001/api"
EMAIL = "asaadhshm@gmail.com"
PASSWORD = "Asaad888"

passed = 0
failed = 0


def test(name, fn):
    global passed, failed
    try:
        fn()
        print(f"  PASS: {name}")
        passed += 1
    except Exception as e:
        print(f"  FAIL: {name} -> {e}")
        failed += 1


# ─── AUTH ───
token = None


def t_login():
    global token
    r = httpx.post(f"{BASE}/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=15)
    assert r.status_code == 200, f"Login {r.status_code}: {r.text}"
    data = r.json()
    token = data.get("session", {}).get("access_token") or data.get("access_token")
    assert token, f"No token found in response: {list(data.keys())}"


print("=== AUTH ===")
test("Login", t_login)


def auth():
    return {"Authorization": f"Bearer {token}"}


def t_verify():
    r = httpx.get(f"{BASE}/auth/verify", headers=auth(), timeout=10)
    assert r.status_code == 200, f"Verify {r.status_code}: {r.text}"


test("Verify token", t_verify)

# ─── PROFILE ───
print("\n=== PROFILE ===")


def t_profile():
    r = httpx.get(f"{BASE}/profiles/me", headers=auth(), timeout=10)
    assert r.status_code == 200, f"Profile {r.status_code}: {r.text}"


test("Get my profile", t_profile)

# ─── ISSUES ───
print("\n=== ISSUES ===")
issue_id = None


def t_create_issue():
    global issue_id
    r = httpx.post(
        f"{BASE}/issues",
        json={"title": "Test Upload Issue", "description": "Testing file uploads", "category": "engine"},
        headers=auth(),
        timeout=15,
    )
    assert r.status_code in (200, 201), f"Create issue {r.status_code}: {r.text}"
    data = r.json()
    issue_id = data.get("id") or data.get("issue", {}).get("id")
    assert issue_id, f"No issue id in response: {list(data.keys())}"


test("Create issue", t_create_issue)


def t_list_issues():
    r = httpx.get(f"{BASE}/issues", timeout=10)
    assert r.status_code == 200, f"List issues {r.status_code}: {r.text}"


test("List issues (public)", t_list_issues)


def t_get_issue():
    r = httpx.get(f"{BASE}/issues/{issue_id}", headers=auth(), timeout=10)
    assert r.status_code == 200, f"Get issue {r.status_code}: {r.text}"


test("Get issue detail", t_get_issue)

# ─── UPLOAD: issue-media ───
print("\n=== UPLOADS ===")


def t_upload_issue_media():
    content = b"This is a test file for issue media upload."
    files = {"file": ("test.txt", io.BytesIO(content), "text/plain")}
    data = {"issue_id": issue_id}
    r = httpx.post(f"{BASE}/uploads/issue-media", files=files, data=data, headers=auth(), timeout=30)
    assert r.status_code == 200, f"Upload issue-media {r.status_code}: {r.text}"
    rdata = r.json()
    assert "public_url" in rdata, f"No public_url: {list(rdata.keys())}"
    assert rdata["file_size"] == len(content), f"Size mismatch: expected {len(content)}, got {rdata['file_size']}"
    print(f"    -> public_url: {rdata['public_url'][:80]}...")


test("Upload issue-media", t_upload_issue_media)


def t_upload_avatar():
    content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # fake PNG header
    files = {"file": ("avatar.png", io.BytesIO(content), "image/png")}
    r = httpx.post(f"{BASE}/uploads/avatars", files=files, headers=auth(), timeout=30)
    assert r.status_code == 200, f"Upload avatar {r.status_code}: {r.text}"
    rdata = r.json()
    assert "public_url" in rdata, f"No public_url: {list(rdata.keys())}"
    print(f"    -> public_url: {rdata['public_url'][:80]}...")


test("Upload avatar", t_upload_avatar)

# ─── CONVERSATIONS ───
print("\n=== CONVERSATIONS ===")


def t_list_conversations():
    r = httpx.get(f"{BASE}/conversations", headers=auth(), timeout=10)
    assert r.status_code == 200, f"List conv {r.status_code}: {r.text}"
    data = r.json()
    if isinstance(data, dict):
        assert "conversations" in data, f"Missing 'conversations' key: {list(data.keys())}"


test("List conversations", t_list_conversations)

# ─── RESPONSES ───
print("\n=== RESPONSES ===")


def t_list_responses():
    r = httpx.get(f"{BASE}/issues/{issue_id}/responses", headers=auth(), timeout=10)
    assert r.status_code == 200, f"List responses {r.status_code}: {r.text}"


test("List responses for issue", t_list_responses)

# ─── CLEANUP ───
print("\n=== CLEANUP ===")


def t_delete_issue():
    r = httpx.delete(f"{BASE}/issues/{issue_id}", headers=auth(), timeout=10)
    assert r.status_code == 200, f"Delete issue {r.status_code}: {r.text}"


test("Delete test issue", t_delete_issue)

print(f"\n{'='*50}")
print(f"RESULTS: {passed} passed, {failed} failed")
print(f"{'='*50}")

if failed > 0:
    sys.exit(1)
