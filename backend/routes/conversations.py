"""
Conversation routes — start & list conversations between customers and mechanics.
"""

from typing import Optional
import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from services.supabase_client import get_supabase
from auth.dependencies import get_current_user

logger = logging.getLogger("salikchat.conversations")

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


# ---------- Models ----------

class StartConversationRequest(BaseModel):
    issue_id: str
    mechanic_id: str


# ---------- Endpoints ----------

@router.post("")
async def start_conversation(body: StartConversationRequest, user: dict = Depends(get_current_user)):
    """
    Start a conversation between a customer and a mechanic for a given issue.
    Returns existing conversation if one already exists.
    """
    sb = get_supabase()

    # Verify issue belongs to this customer
    try:
        issue = sb.table("car_issues").select("customer_id").eq("id", body.issue_id).single().execute()
    except Exception:
        raise HTTPException(status_code=404, detail="Issue not found")
    if not issue.data:
        raise HTTPException(status_code=404, detail="Issue not found")
    if issue.data["customer_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not your issue")

    # Check if conversation already exists
    existing = sb.table("conversations").select("*").eq(
        "issue_id", body.issue_id
    ).eq("mechanic_id", body.mechanic_id).execute()

    if existing.data:
        return existing.data[0]

    # Create new conversation
    conv_data = {
        "issue_id": body.issue_id,
        "customer_id": user["id"],
        "mechanic_id": body.mechanic_id,
    }
    res = sb.table("conversations").insert(conv_data).execute()

    # Send system message
    if res.data:
        sb.table("messages").insert({
            "conversation_id": res.data[0]["id"],
            "sender_id": user["id"],
            "content": "Conversation started",
            "message_type": "system",
        }).execute()

        # Notify mechanic
        sb.table("notifications").insert({
            "user_id": body.mechanic_id,
            "type": "new_conversation",
            "title": "New conversation",
            "body": "A customer wants to chat about their car issue",
            "data": {
                "conversation_id": res.data[0]["id"],
                "issue_id": body.issue_id,
            },
        }).execute()

    return res.data[0] if res.data else {}


@router.get("")
async def list_conversations(
    user: dict = Depends(get_current_user),
    status: Optional[str] = Query(None),
):
    """List all conversations for the current user (as customer or mechanic)."""
    sb = get_supabase()
    role = user.get("role", "customer")

    # Get conversations where user is either customer or mechanic
    if role == "mechanic":
        query = sb.table("conversations").select(
            "*, car_issues(title, category, urgency, car_make, car_model, car_year), profiles!conversations_customer_id_fkey(full_name, avatar_url)"
        ).eq("mechanic_id", user["id"])
    else:
        query = sb.table("conversations").select(
            "*, car_issues(title, category, urgency, car_make, car_model, car_year), profiles!conversations_mechanic_id_fkey(full_name, avatar_url)"
        ).eq("customer_id", user["id"])

    if status:
        query = query.eq("status", status)

    query = query.order("last_message_at", desc=True)
    res = query.execute()

    conversations = res.data or []

    # Get unread counts for each conversation
    for conv in conversations:
        unread = sb.table("messages").select(
            "id", count="exact"
        ).eq(
            "conversation_id", conv["id"]
        ).eq("is_read", False).neq("sender_id", user["id"]).execute()
        conv["unread_count"] = unread.count or 0

    return {"conversations": conversations}


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str, user: dict = Depends(get_current_user)):
    """Get a single conversation with details."""
    sb = get_supabase()

    try:
        conv = sb.table("conversations").select(
            "*, car_issues(*, issue_media(*))"
        ).eq("id", conversation_id).single().execute()
    except Exception:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if not conv.data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Verify user is a participant
    data = conv.data
    if data["customer_id"] != user["id"] and data["mechanic_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not a participant in this conversation")

    # Fetch customer and mechanic profiles separately (PostgREST can't join same table twice)
    for key, uid_field in [("customer_profile", "customer_id"), ("mechanic_profile", "mechanic_id")]:
        try:
            prof = sb.table("profiles").select(
                "full_name, avatar_url, city"
            ).eq("id", data[uid_field]).single().execute()
            data[key] = prof.data
        except Exception:
            data[key] = None

    return data
