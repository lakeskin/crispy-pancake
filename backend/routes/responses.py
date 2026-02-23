"""
Mechanic Response routes — submit responses / diagnoses to car issues.
"""

from typing import Optional
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from services.supabase_client import get_supabase
from auth.dependencies import get_current_user

logger = logging.getLogger("salikchat.responses")

router = APIRouter(prefix="/api/issues", tags=["responses"])


# ---------- Models ----------

class SubmitResponseRequest(BaseModel):
    initial_diagnosis: str
    estimated_cost_min: Optional[float] = None
    estimated_cost_max: Optional[float] = None
    estimated_fix_time: Optional[str] = None
    confidence_level: str = "medium"
    needs_video_call: bool = False


# ---------- Endpoints ----------

@router.post("/{issue_id}/responses")
async def submit_response(
    issue_id: str,
    body: SubmitResponseRequest,
    user: dict = Depends(get_current_user),
):
    """A mechanic submits a diagnosis response to an issue."""
    if user.get("role") != "mechanic":
        raise HTTPException(status_code=403, detail="Only mechanics can respond to issues")

    sb = get_supabase()

    # Verify issue exists and is open
    try:
        issue = sb.table("car_issues").select("id, status, customer_id").eq("id", issue_id).single().execute()
    except Exception:
        raise HTTPException(status_code=404, detail="Issue not found")
    if not issue.data:
        raise HTTPException(status_code=404, detail="Issue not found")
    if issue.data["status"] not in ("open", "in_progress"):
        raise HTTPException(status_code=400, detail="Issue is not accepting responses")
    if issue.data["customer_id"] == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot respond to your own issue")

    # Check if already responded
    existing = sb.table("mechanic_responses").select("id").eq(
        "issue_id", issue_id
    ).eq("mechanic_id", user["id"]).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="You already responded to this issue")

    response_data = {
        "issue_id": issue_id,
        "mechanic_id": user["id"],
        **body.model_dump(),
    }
    res = sb.table("mechanic_responses").insert(response_data).execute()

    # Create a notification for the customer
    sb.table("notifications").insert({
        "user_id": issue.data["customer_id"],
        "type": "new_response",
        "title": "New mechanic response",
        "body": f"A mechanic responded to your issue",
        "data": {"issue_id": issue_id, "response_id": res.data[0]["id"] if res.data else None},
    }).execute()

    return res.data[0] if res.data else {}


@router.get("/{issue_id}/responses")
async def list_responses(issue_id: str):
    """List all mechanic responses for an issue."""
    sb = get_supabase()

    responses = sb.table("mechanic_responses").select(
        "*, profiles!mechanic_responses_mechanic_id_fkey(full_name, avatar_url), mechanic_profiles!mechanic_responses_mechanic_id_fkey(rating_avg, rating_count, specializations, experience_years, verification_status)"
    ).eq("issue_id", issue_id).order("created_at", desc=False).execute()

    return {"responses": responses.data or []}
