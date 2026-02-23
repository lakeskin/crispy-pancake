"""
Create 2 customer + 2 mechanic test accounts using Supabase Admin API.
Bypasses email rate limits by using the service_role key directly.
"""
import os
import json
import time
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

url = os.getenv("SUPABASE_URL")
service_key = os.getenv("SUPABASE_SERVICE_KEY")
sb = create_client(url, service_key)

accounts = [
    {"email": "customer1@salikchat.com", "password": "Customer1Pass!", "full_name": "Ahmed Al Maktoum", "role": "customer"},
    {"email": "customer2@salikchat.com", "password": "Customer2Pass!", "full_name": "Fatima Al Nahyan", "role": "customer"},
    {"email": "mechanic1@salikchat.com", "password": "Mechanic1Pass!", "full_name": "Omar Al Rashid",   "role": "mechanic"},
    {"email": "mechanic2@salikchat.com", "password": "Mechanic2Pass!", "full_name": "Hassan Al Farsi",  "role": "mechanic"},
]

results = []
for acc in accounts:
    try:
        # Use admin API to create user — bypasses rate limits
        res = sb.auth.admin.create_user({
            "email": acc["email"],
            "password": acc["password"],
            "email_confirm": True,  # auto-confirm so they can log in immediately
            "user_metadata": {
                "full_name": acc["full_name"],
                "role": acc["role"],
            },
        })
        user = res.user
        uid = user.id
        print(f"  AUTH OK: {acc['email']} ({acc['role']}) -> id={uid}")

        # Create profile row
        sb.table("profiles").upsert({
            "id": uid,
            "role": acc["role"],
            "full_name": acc["full_name"],
        }).execute()
        print(f"    profile created")

        # If mechanic, also create mechanic_profiles row
        if acc["role"] == "mechanic":
            sb.table("mechanic_profiles").upsert({"id": uid}).execute()
            print(f"    mechanic_profile created")

        results.append({**acc, "id": uid, "status": "created"})

    except Exception as e:
        err = str(e)
        if "already been registered" in err.lower() or "already exists" in err.lower():
            print(f"  SKIP: {acc['email']} already exists")
            results.append({**acc, "id": "exists", "status": "already_exists"})
        else:
            print(f"  FAIL: {acc['email']} -> {e}")
            results.append({**acc, "id": "N/A", "status": f"failed: {e}"})

    time.sleep(0.5)  # small delay between calls

print("\n" + json.dumps(results, indent=2))
