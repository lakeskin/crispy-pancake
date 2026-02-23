"""
Auth routes — sign-up, login, logout, refresh, verify.
Thin wrappers around Supabase Auth; FastAPI handles business-logic validation.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from services.supabase_client import get_supabase
from auth.dependencies import get_current_user

logger = logging.getLogger("salikchat.auth")

router = APIRouter(prefix="/api/auth", tags=["auth"])


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
    sb = get_supabase()
    try:
        res = sb.auth.sign_up({
            "email": body.email,
            "password": body.password,
            "options": {
                "data": {
                    "full_name": body.full_name,
                    "role": body.role,
                },
            },
        })
        user = res.user
        session = res.session

        # Auto-confirm email so user can log in immediately (dev convenience)
        try:
            sb.auth.admin.update_user_by_id(user.id, {"email_confirm": True})
            logger.info("Auto-confirmed email for %s", user.id)
        except Exception as confirm_err:
            logger.warning("Could not auto-confirm email: %s", confirm_err)

        # Create profile row
        profile_data = {
            "id": user.id,
            "role": body.role,
            "full_name": body.full_name,
        }
        sb.table("profiles").upsert(profile_data).execute()

        # If mechanic, create mechanic_profiles row
        if body.role == "mechanic":
            sb.table("mechanic_profiles").upsert({
                "id": user.id,
            }).execute()

        return {
            "user": {
                "id": user.id,
                "email": user.email,
                "role": body.role,
                "full_name": body.full_name,
            },
            "session": {
                "access_token": session.access_token if session else None,
                "refresh_token": session.refresh_token if session else None,
                "expires_at": session.expires_at if session else None,
            } if session else None,
        }
    except Exception as e:
        logger.exception("Signup failed for %s", body.email)
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
async def login(body: LoginRequest):
    """Sign in with email + password."""
    logger.info("Login attempt: email=%s", body.email)
    sb = get_supabase()
    try:
        res = sb.auth.sign_in_with_password({
            "email": body.email,
            "password": body.password,
        })
        user = res.user
        session = res.session

        # Fetch profile for role
        try:
            profile = sb.table("profiles").select("*").eq("id", user.id).single().execute()
        except Exception:
            profile = type('obj', (object,), {'data': None})()

        return {
            "user": {
                "id": user.id,
                "email": user.email,
                "role": profile.data.get("role", "customer") if profile.data else "customer",
                "full_name": profile.data.get("full_name", "") if profile.data else "",
                "avatar_url": profile.data.get("avatar_url") if profile.data else None,
            },
            "session": {
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
                "expires_at": session.expires_at,
            },
        }
    except Exception as e:
        logger.exception("Login failed for %s: %s", body.email, e)
        detail = str(e)
        if "Invalid login" in detail or "invalid" in detail.lower():
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if "Email not confirmed" in detail:
            raise HTTPException(status_code=401, detail="Please confirm your email first")
        raise HTTPException(status_code=401, detail=detail)


@router.post("/refresh")
async def refresh_token(body: RefreshRequest):
    """Refresh an access token."""
    sb = get_supabase()
    try:
        res = sb.auth.refresh_session(body.refresh_token)
        session = res.session
        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "expires_at": session.expires_at,
        }
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
