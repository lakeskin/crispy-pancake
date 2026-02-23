"""
Message routes — send messages, fetch history, mark as read.
Real-time delivery is handled by Supabase Realtime on the frontend.
"""

from typing import Optional
import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from services.supabase_client import get_supabase
from auth.dependencies import get_current_user

logger = logging.getLogger("salikchat.messages")

router = APIRouter(prefix="/api/conversations", tags=["messages"])


# ---------- Models ----------

class SendMessageRequest(BaseModel):
    content: Optional[str] = None
    message_type: str = "text"  # text, image, audio, video, file, diagnosis
    media_url: Optional[str] = None
    metadata: Optional[dict] = None


class MarkReadRequest(BaseModel):
    message_ids: list[str]


# ---------- Endpoints ----------

@router.get("/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
):
    """Get message history for a conversation (paginated, newest last)."""
    sb = get_supabase()

    # Verify user is a participant
    try:
        conv = sb.table("conversations").select(
            "customer_id, mechanic_id"
        ).eq("id", conversation_id).single().execute()
    except Exception:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if not conv.data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.data["customer_id"] != user["id"] and conv.data["mechanic_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not a participant")

    offset = (page - 1) * limit
    messages = sb.table("messages").select(
        "*, profiles!messages_sender_id_fkey(full_name, avatar_url)"
    ).eq(
        "conversation_id", conversation_id
    ).order("created_at", desc=False).range(offset, offset + limit - 1).execute()

    return {"messages": messages.data or [], "page": page, "limit": limit}


@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    body: SendMessageRequest,
    user: dict = Depends(get_current_user),
):
    """Send a message in a conversation."""
    sb = get_supabase()

    # Verify user is a participant
    try:
        conv = sb.table("conversations").select(
            "customer_id, mechanic_id"
        ).eq("id", conversation_id).single().execute()
    except Exception:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if not conv.data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.data["customer_id"] != user["id"] and conv.data["mechanic_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not a participant")

    if not body.content and not body.media_url:
        raise HTTPException(status_code=400, detail="Message must have content or media")

    msg_data = {
        "conversation_id": conversation_id,
        "sender_id": user["id"],
        "content": body.content,
        "message_type": body.message_type,
        "media_url": body.media_url,
        "metadata": body.metadata or {},
    }
    res = sb.table("messages").insert(msg_data).execute()

    # Update conversation last_message_at
    sb.table("conversations").update({
        "last_message_at": "now()",
    }).eq("id", conversation_id).execute()

    # Notify the other participant
    other_id = (
        conv.data["mechanic_id"]
        if conv.data["customer_id"] == user["id"]
        else conv.data["customer_id"]
    )
    sb.table("notifications").insert({
        "user_id": other_id,
        "type": "new_message",
        "title": "New message",
        "body": body.content[:100] if body.content else "Sent a media message",
        "data": {"conversation_id": conversation_id},
    }).execute()

    return res.data[0] if res.data else {}


@router.post("/{conversation_id}/messages/read")
async def mark_messages_read(
    conversation_id: str,
    body: MarkReadRequest,
    user: dict = Depends(get_current_user),
):
    """Mark messages as read."""
    sb = get_supabase()

    # Only mark messages that aren't from the current user
    sb.table("messages").update({"is_read": True}).in_(
        "id", body.message_ids
    ).neq("sender_id", user["id"]).execute()

    return {"message": "Messages marked as read"}
