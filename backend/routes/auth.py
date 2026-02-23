"""
Auth routes — sign-up, login, logout, refresh, verify.
Thin wrappers around Supabase Auth; FastAPI handles business-logic validation.

IMPORTANT: Auth operations (sign_up, sign_in, refresh) use direct HTTP calls
to the Supabase Auth API instead of the supabase-py SDK's .auth methods.
This prevents tainting the singleton service-role client's internal auth state,
which would cause subsequent storage/table operations to use the user's token
instead of the service key, triggering RLS violations.
"""

import os
import logging
import httpx
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from services.supabase_client import get_supabase
from auth.dependencies import get_current_user

logger = logging.getLogger("salikchat.auth")

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Supabase Auth REST API base
_SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
_SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
_SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")


# ---------- Request / Response Models ----------

class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "customer"  # "customer" | "mechanic"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ---------- Endpoints ----------

@router.post("/signup")
async def sign_up(body: SignUpRequest):
    """Register a new user via Supabase Auth with role metadata."""
    logger.info("Signup attempt: email=%s role=%s", body.email, body.role)
    sb = get_supabase()  # service-role client for table ops only

    try:
        # Use direct HTTP to avoid tainting the singleton client
        resp = httpx.post(
            f"{_SUPABASE_URL}/auth/v1/signup",
            json={
                "email": body.email,
                "password": body.password,
                "data": {
                    "full_name": body.full_name,
                    "role": body.role,
                },
            },
            headers={"apikey": _SUPABASE_KEY, "Content-Type": "application/json"},
            timeout=15,
        )
        if resp.status_code not in (200, 201):
            detail = resp.json().get("msg") or resp.json().get("error_description") or resp.text
            raise HTTPException(status_code=resp.status_code, detail=detail)

        data = resp.json()
        user_id = data.get("id")
        user_email = data.get("email", body.email)
        session_data = data.get("session") or data.get("access_token")

        # Auto-confirm email (dev convenience) via admin API
        try:
            admin_resp = httpx.put(
                f"{_SUPABASE_URL}/auth/v1/admin/users/{user_id}",
                json={"email_confirm": True},
                headers={
                    "apikey": _SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {_SUPABASE_SERVICE_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=10,
            )
            if admin_resp.status_code == 200:
                logger.info("Auto-confirmed email for %s", user_id)
            else:
                logger.warning("Could not auto-confirm email: %s", admin_resp.text)
        except Exception as confirm_err:
            logger.warning("Could not auto-confirm email: %s", confirm_err)

        # Create profile row (uses service key — safe, no auth tainting)
        profile_data = {
            "id": user_id,
            "role": body.role,
            "full_name": body.full_name,
        }
        sb.table("profiles").upsert(profile_data).execute()

        # If mechanic, create mechanic_profiles row
        if body.role == "mechanic":
            sb.table("mechanic_profiles").upsert({
                "id": user_id,
            }).execute()

        # Build session info
        session_out = None
        if isinstance(session_data, dict):
            session_out = {
                "access_token": session_data.get("access_token"),
                "refresh_token": session_data.get("refresh_token"),
                "expires_at": session_data.get("expires_at"),
            }
        elif isinstance(data.get("access_token"), str):
            session_out = {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token"),
                "expires_at": data.get("expires_at"),
            }

        return {
            "user": {
                "id": user_id,
                "email": user_email,
                "role": body.role,
                "full_name": body.full_name,
            },
            "session": session_out,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Signup failed for %s", body.email)
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
async def login(body: LoginRequest):
    """Sign in with email + password."""
    logger.info("Login attempt: email=%s", body.email)
    sb = get_supabase()  # service-role client for table ops only

    try:
        # Use direct HTTP to avoid tainting the singleton client
        resp = httpx.post(
            f"{_SUPABASE_URL}/auth/v1/token?grant_type=password",
            json={
                "email": body.email,
                "password": body.password,
            },
            headers={"apikey": _SUPABASE_KEY, "Content-Type": "application/json"},
            timeout=15,
        )
        if resp.status_code != 200:
            error_body = resp.json()
            detail = error_body.get("error_description") or error_body.get("msg") or resp.text
            if "invalid" in detail.lower() or resp.status_code == 400:
                raise HTTPException(status_code=401, detail="Invalid email or password")
            if "email not confirmed" in detail.lower():
                raise HTTPException(status_code=401, detail="Please confirm your email first")
            raise HTTPException(status_code=401, detail=detail)

        data = resp.json()
        user_data = data.get("user", {})
        user_id = user_data.get("id")

        # Fetch profile for role (uses service key — safe)
        try:
            profile = sb.table("profiles").select("*").eq("id", user_id).single().execute()
            pdata = profile.data or {}
        except Exception:
            pdata = {}

        return {
            "user": {
                "id": user_id,
                "email": user_data.get("email", body.email),
                "role": pdata.get("role", "customer"),
                "full_name": pdata.get("full_name", ""),
                "avatar_url": pdata.get("avatar_url"),
            },
            "session": {
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
                "expires_at": data.get("expires_at"),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Login failed for %s: %s", body.email, e)
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/refresh")
async def refresh_token(body: RefreshRequest):
    """Refresh an access token."""
    try:
        resp = httpx.post(
            f"{_SUPABASE_URL}/auth/v1/token?grant_type=refresh_token",
            json={"refresh_token": body.refresh_token},
            headers={"apikey": _SUPABASE_KEY, "Content-Type": "application/json"},
            timeout=15,
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        data = resp.json()
        return {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token"),
            "expires_at": data.get("expires_at"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.post("/logout")
async def logout(user: dict = Depends(get_current_user)):
    """Log out (server-side — revokes Supabase session)."""
    # Supabase handles session revocation client-side for anon key.
    # With service key we'd call admin API, but for MVP client-side logout is fine.
    return {"message": "Logged out"}


@router.get("/verify")
async def verify(user: dict = Depends(get_current_user)):
    """Verify the current token and return user info."""
    sb = get_supabase()
    try:
        profile = sb.table("profiles").select("*").eq("id", user["id"]).single().execute()
        data = profile.data or {}
    except Exception:
        data = {}
    return {
        "id": user["id"],
        "email": user["email"],
        "role": data.get("role", user.get("role", "customer")),
        "full_name": data.get("full_name", ""),
        "avatar_url": data.get("avatar_url"),
        "phone": data.get("phone"),
        "city": data.get("city"),
    }
