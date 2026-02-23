"""
Comprehensive test of all SalikChat backend endpoints.
Run: python test_all_endpoints.py
"""

import json
import urllib.request
import urllib.error
import sys
import os

BASE = "http://localhost:8001/api"
PASS_COUNT = 0
FAIL_COUNT = 0


def req(method, path, data=None, token=None, expect_status=None):
    """Make an HTTP request and return (status_code, parsed_json_or_None)."""
    global PASS_COUNT, FAIL_COUNT
    url = BASE + path
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = json.dumps(data).encode() if data else None
    r = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        resp = urllib.request.urlopen(r)
        status = resp.status
        text = resp.read().decode()
        result = json.loads(text) if text else {}
    except urllib.error.HTTPError as e:
        status = e.code
        text = e.read().decode()
        try:
            result = json.loads(text)
        except Exception:
            result = {"raw": text}

    label = f"{method} {path}"
    if expect_status and status != expect_status:
        print(f"  FAIL  {label}  expected={expect_status} got={status}  {json.dumps(result)[:200]}")
        FAIL_COUNT += 1
    else:
        print(f"  OK    {label}  {status}  {json.dumps(result)[:150]}")
        PASS_COUNT += 1

    return status, result


def main():
    global PASS_COUNT, FAIL_COUNT

    print("=" * 60)
    print("SALIKCHAT BACKEND — FULL ENDPOINT TEST")
    print("=" * 60)

    # ── 1. Health ──
    print("\n--- Health ---")
    req("GET", "/health", expect_status=200)

    # ── 2. Config endpoints ──
    print("\n--- Config ---")
    req("GET", "/config/categories", expect_status=200)
    req("GET", "/config/urgency-levels", expect_status=200)
    req("GET", "/config/budget-ranges", expect_status=200)
    req("GET", "/config/confidence-levels", expect_status=200)
    req("GET", "/config/specializations", expect_status=200)
    req("GET", "/config/upload-limits", expect_status=200)

    # ── 3. Auth ──
    print("\n--- Auth: Login ---")
    status, login_data = req("POST", "/auth/login", {
        "email": "asaadhshm@gmail.com",
        "password": "Asaad888",
    }, expect_status=200)

    if status != 200:
        print("FATAL: Cannot login, aborting tests.")
        sys.exit(1)

    token = login_data["session"]["access_token"]
    user_id = login_data["user"]["id"]
    print(f"  Logged in as: {login_data['user']['email']} (id={user_id})")

    # ── 4. Auth: Verify ──
    print("\n--- Auth: Verify ---")
    req("GET", "/auth/verify", token=token, expect_status=200)

    # ── 5. Auth: Bad token should fail ──
    print("\n--- Auth: Bad token ---")
    req("GET", "/auth/verify", token="bad_token_123", expect_status=401)

    # ── 6. Auth: No token on protected route ──
    print("\n--- Auth: No token ---")
    req("GET", "/conversations", expect_status=401)

    # ── 7. Profile ──
    print("\n--- Profile: Get my profile ---")
    status, profile_data = req("GET", "/profiles/me", token=token, expect_status=200)

    print("\n--- Profile: Update ---")
    req("PATCH", "/profiles/me", {"city": "Dubai"}, token=token, expect_status=200)

    print("\n--- Profile: Public profile ---")
    req("GET", f"/profiles/{user_id}", expect_status=200)

    # ── 8. Issues: List (public, no auth needed) ──
    print("\n--- Issues: List public ---")
    req("GET", "/issues", expect_status=200)

    # ── 9. Issues: List my issues ──
    print("\n--- Issues: List my issues ---")
    req("GET", "/issues?my_issues=true", token=token, expect_status=200)

    # ── 10. Issues: Create ──
    print("\n--- Issues: Create ---")
    status, issue_data = req("POST", "/issues", {
        "title": "Test issue - grinding noise",
        "description": "Hear a grinding noise when braking at low speed. Started last week.",
        "car_make": "Toyota",
        "car_model": "Camry",
        "car_year": 2020,
        "car_mileage": 45000,
        "category": "brakes",
        "urgency": "normal",
        "location_city": "Dubai",
        "budget_range": "50_200",
    }, token=token, expect_status=200)

    if status != 200:
        print("FATAL: Cannot create issue, some tests will be skipped.")
        issue_id = None
    else:
        issue_id = issue_data.get("id")
        print(f"  Created issue: {issue_id}")

    # ── 11. Issues: Get by ID ──
    if issue_id:
        print("\n--- Issues: Get by ID ---")
        req("GET", f"/issues/{issue_id}", token=token, expect_status=200)

    # ── 12. Issues: Update ──
    if issue_id:
        print("\n--- Issues: Update ---")
        req("PATCH", f"/issues/{issue_id}", {"title": "Updated test issue"}, token=token, expect_status=200)

    # ── 13. Issues: Add media metadata (register not upload) ──
    if issue_id:
        print("\n--- Issues: Add media ---")
        req("POST", f"/issues/{issue_id}/media", {
            "media_type": "image",
            "storage_path": f"{user_id}/{issue_id}/test.jpg",
            "file_name": "test.jpg",
            "file_size": 12345,
        }, token=token, expect_status=200)

    # ── 14. Issues: Get again to verify media attached ──
    if issue_id:
        print("\n--- Issues: Verify media attached ---")
        status, detail = req("GET", f"/issues/{issue_id}", token=token, expect_status=200)
        media_count = len(detail.get("issue_media", []))
        if media_count > 0:
            print(f"  OK    Media attached: {media_count} item(s)")
            PASS_COUNT += 1
        else:
            print(f"  FAIL  No media found in issue detail")
            FAIL_COUNT += 1

    # ── 15. Issues: Get non-existent issue ──
    print("\n--- Issues: Non-existent ---")
    req("GET", "/issues/00000000-0000-0000-0000-000000000000", expect_status=404)

    # ── 16. Responses: List (should be empty) ──
    if issue_id:
        print("\n--- Responses: List ---")
        status, resp_data = req("GET", f"/issues/{issue_id}/responses", expect_status=200)
        print(f"  Response count: {len(resp_data.get('responses', []))}")

    # ── 17. Responses: Submit (will fail because user is customer, not mechanic) ──
    if issue_id:
        print("\n--- Responses: Submit as customer (should fail 403) ---")
        req("POST", f"/issues/{issue_id}/responses", {
            "initial_diagnosis": "Test diagnosis",
            "confidence_level": "medium",
        }, token=token, expect_status=403)

    # ── 18. Conversations: List (should be empty) ──
    print("\n--- Conversations: List ---")
    status, conv_list = req("GET", "/conversations", token=token, expect_status=200)
    print(f"  Conversation count: {len(conv_list.get('conversations', []))}")

    # ── 19. Conversations: Get non-existent ──
    print("\n--- Conversations: Non-existent ---")
    req("GET", "/conversations/00000000-0000-0000-0000-000000000000", token=token, expect_status=404)

    # ── 20. Messages: Get for non-existent conversation ──
    print("\n--- Messages: Non-existent conversation ---")
    req("GET", "/conversations/00000000-0000-0000-0000-000000000000/messages", token=token, expect_status=404)

    # ── 21. Auth: Refresh token ──
    print("\n--- Auth: Refresh ---")
    refresh_token = login_data["session"]["refresh_token"]
    status, refresh_data = req("POST", "/auth/refresh", {"refresh_token": refresh_token}, expect_status=200)
    if status == 200 and refresh_data.get("access_token"):
        print(f"  New token starts with: {refresh_data['access_token'][:20]}")

    # ── 22. Auth: Bad refresh token ──
    print("\n--- Auth: Bad refresh ---")
    req("POST", "/auth/refresh", {"refresh_token": "bad_token"}, expect_status=401)

    # ── 23. Issues: Delete ──
    if issue_id:
        print("\n--- Issues: Delete ---")
        req("DELETE", f"/issues/{issue_id}", token=token, expect_status=200)

        print("\n--- Issues: Verify deleted ---")
        req("GET", f"/issues/{issue_id}", expect_status=404)

    # ── SUMMARY ──
    print("\n" + "=" * 60)
    print(f"RESULTS:  {PASS_COUNT} passed   {FAIL_COUNT} failed")
    print("=" * 60)

    if FAIL_COUNT > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
