"""
Profile routes — view & edit user/mechanic profiles.
"""

from typing import Optional, List
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from services.supabase_client import get_supabase
from auth.dependencies import get_current_user

logger = logging.getLogger("salikchat.profiles")

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


# ---------- Models ----------

class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None


class UpdateMechanicProfileRequest(BaseModel):
    specializations: Optional[List[str]] = None
    experience_years: Optional[int] = None
    bio: Optional[str] = None
    hourly_rate: Optional[float] = None
    is_available: Optional[bool] = None


# ---------- Endpoints ----------

@router.get("/me")
async def get_my_profile(user: dict = Depends(get_current_user)):
    """Get the current user's full profile."""
    sb = get_supabase()
    try:
        profile = sb.table("profiles").select("*").eq("id", user["id"]).single().execute()
    except Exception:
        raise HTTPException(status_code=404, detail="Profile not found")
    if not profile.data:
        raise HTTPException(status_code=404, detail="Profile not found")

    result = profile.data
    # If mechanic, also fetch mechanic-specific data
    if result.get("role") == "mechanic":
        try:
            mp = sb.table("mechanic_profiles").select("*").eq("id", user["id"]).single().execute()
            if mp.data:
                result["mechanic_profile"] = mp.data
        except Exception:
            pass  # No mechanic profile row yet

    return result


@router.patch("/me")
async def update_my_profile(body: UpdateProfileRequest, user: dict = Depends(get_current_user)):
    """Update the current user's basic profile."""
    sb = get_supabase()
    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    res = sb.table("profiles").update(update_data).eq("id", user["id"]).execute()
    return res.data[0] if res.data else {}


@router.patch("/me/mechanic")
async def update_my_mechanic_profile(
    body: UpdateMechanicProfileRequest,
    user: dict = Depends(get_current_user),
):
    """Update mechanic-specific profile fields."""
    if user.get("role") != "mechanic":
        raise HTTPException(status_code=403, detail="Only mechanics can update mechanic profiles")

    sb = get_supabase()
    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    res = sb.table("mechanic_profiles").update(update_data).eq("id", user["id"]).execute()
    return res.data[0] if res.data else {}


@router.get("/{user_id}")
async def get_public_profile(user_id: str):
    """Get a user's public profile (for viewing mechanic profiles, etc.)."""
    sb = get_supabase()
    try:
        profile = sb.table("profiles").select(
            "id, full_name, role, avatar_url, city, country, created_at"
        ).eq("id", user_id).single().execute()
    except Exception:
        raise HTTPException(status_code=404, detail="User not found")

    if not profile.data:
        raise HTTPException(status_code=404, detail="User not found")

    result = profile.data

    if result.get("role") == "mechanic":
        try:
            mp = sb.table("mechanic_profiles").select(
                "specializations, experience_years, bio, hourly_rate, rating_avg, rating_count, is_available, verification_status"
            ).eq("id", user_id).single().execute()
            if mp.data:
                result["mechanic_profile"] = mp.data
        except Exception:
            pass  # No mechanic profile row yet

    return result
