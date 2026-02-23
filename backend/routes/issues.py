"""
Car Issue routes — CRUD for car diagnostic requests.
"""

from typing import Optional, List
import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from services.supabase_client import get_supabase
from auth.dependencies import get_current_user, get_optional_user

logger = logging.getLogger("salikchat.issues")

router = APIRouter(prefix="/api/issues", tags=["issues"])


# ---------- Models ----------

class CreateIssueRequest(BaseModel):
    title: str
    description: str
    car_make: str
    car_model: str
    car_year: int
    car_mileage: Optional[int] = None
    category: str  # engine, brakes, electrical, etc.
    urgency: str = "normal"
    location_city: Optional[str] = None
    budget_range: Optional[str] = None


class UpdateIssueRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    is_public: Optional[bool] = None


class AddMediaRequest(BaseModel):
    media_type: str  # audio, image, video
    storage_path: str
    file_name: str
    file_size: Optional[int] = None
    duration_seconds: Optional[int] = None
    thumbnail_path: Optional[str] = None


# ---------- Endpoints ----------

@router.post("")
async def create_issue(body: CreateIssueRequest, user: dict = Depends(get_current_user)):
    """Create a new car issue."""
    sb = get_supabase()
    issue_data = {
        "customer_id": user["id"],
        **body.model_dump(),
    }
    res = sb.table("car_issues").insert(issue_data).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create issue")
    return res.data[0]


@router.get("")
async def list_issues(
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    urgency: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    my_issues: bool = Query(False),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    user: Optional[dict] = Depends(get_optional_user),
):
    """
    List car issues with filters.
    - my_issues=true → only the current user's issues
    - Otherwise → public open issues (for mechanic feed)
    """
    sb = get_supabase()
    offset = (page - 1) * limit

    query = sb.table("car_issues").select(
        "*, issue_media(*), profiles!car_issues_customer_id_fkey(full_name, avatar_url, city)"
    )

    if my_issues and user:
        query = query.eq("customer_id", user["id"])
    else:
        query = query.eq("is_public", True)

    if status:
        query = query.eq("status", status)
    if category:
        query = query.eq("category", category)
    if urgency:
        query = query.eq("urgency", urgency)
    if city:
        query = query.eq("location_city", city)

    query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
    res = query.execute()

    # Also get response counts for each issue
    issue_ids = [i["id"] for i in (res.data or [])]
    response_counts = {}
    if issue_ids:
        for issue_id in issue_ids:
            count_res = sb.table("mechanic_responses").select(
                "id", count="exact"
            ).eq("issue_id", issue_id).execute()
            response_counts[issue_id] = count_res.count or 0

    issues = res.data or []
    for issue in issues:
        issue["response_count"] = response_counts.get(issue["id"], 0)

    return {"issues": issues, "page": page, "limit": limit}


@router.get("/{issue_id}")
async def get_issue(issue_id: str, user: Optional[dict] = Depends(get_optional_user)):
    """Get full issue details including media and responses."""
    sb = get_supabase()

    try:
        issue = sb.table("car_issues").select(
            "*, issue_media(*), profiles!car_issues_customer_id_fkey(full_name, avatar_url, city)"
        ).eq("id", issue_id).single().execute()
    except Exception as e:
        logger.warning("Issue not found %s: %s", issue_id, e)
        raise HTTPException(status_code=404, detail="Issue not found")

    if not issue.data:
        raise HTTPException(status_code=404, detail="Issue not found")

    # Fetch responses with mechanic info
    responses = sb.table("mechanic_responses").select(
        "*, profiles!mechanic_responses_mechanic_id_fkey(full_name, avatar_url), mechanic_profiles!mechanic_responses_mechanic_id_fkey(rating_avg, rating_count, specializations, verification_status)"
    ).eq("issue_id", issue_id).order("created_at", desc=False).execute()

    result = issue.data
    result["responses"] = responses.data or []

    return result


@router.patch("/{issue_id}")
async def update_issue(
    issue_id: str,
    body: UpdateIssueRequest,
    user: dict = Depends(get_current_user),
):
    """Update an issue (owner only)."""
    sb = get_supabase()

    # Verify ownership
    try:
        existing = sb.table("car_issues").select("customer_id").eq("id", issue_id).single().execute()
    except Exception:
        raise HTTPException(status_code=404, detail="Issue not found")
    if not existing.data or existing.data["customer_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not your issue")

    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    res = sb.table("car_issues").update(update_data).eq("id", issue_id).execute()
    return res.data[0] if res.data else {}


@router.delete("/{issue_id}")
async def delete_issue(issue_id: str, user: dict = Depends(get_current_user)):
    """Delete an issue (owner only)."""
    sb = get_supabase()

    try:
        existing = sb.table("car_issues").select("customer_id").eq("id", issue_id).single().execute()
    except Exception:
        raise HTTPException(status_code=404, detail="Issue not found")
    if not existing.data or existing.data["customer_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not your issue")

    sb.table("car_issues").delete().eq("id", issue_id).execute()
    return {"message": "Issue deleted"}


@router.post("/{issue_id}/media")
async def add_media(
    issue_id: str,
    body: AddMediaRequest,
    user: dict = Depends(get_current_user),
):
    """Add media (audio/image/video) to an issue after uploading to Supabase Storage."""
    sb = get_supabase()

    # Verify ownership
    try:
        existing = sb.table("car_issues").select("customer_id").eq("id", issue_id).single().execute()
    except Exception:
        raise HTTPException(status_code=404, detail="Issue not found")
    if not existing.data or existing.data["customer_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not your issue")

    media_data = {
        "issue_id": issue_id,
        **body.model_dump(),
    }
    res = sb.table("issue_media").insert(media_data).execute()
    return res.data[0] if res.data else {}
