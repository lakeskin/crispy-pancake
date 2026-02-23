"""
Upload routes — proxy file uploads to Supabase Storage via service key.
This avoids storage RLS issues when the frontend uses the anon key.
"""

import uuid
import logging
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from services.supabase_client import get_supabase
from auth.dependencies import get_current_user

logger = logging.getLogger("salikchat.uploads")

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


@router.post("/issue-media")
async def upload_issue_media(
    file: UploadFile = File(...),
    issue_id: str = Form(...),
    user: dict = Depends(get_current_user),
):
    """Upload a file to the issue-media bucket."""
    sb = get_supabase()

    # Verify issue ownership
    try:
        issue = sb.table("car_issues").select("customer_id").eq("id", issue_id).single().execute()
    except Exception:
        raise HTTPException(status_code=404, detail="Issue not found")
    if not issue.data or issue.data["customer_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not your issue")

    # Read file content
    content = await file.read()
    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "bin"
    unique_name = f"{uuid.uuid4().hex[:12]}.{ext}"
    path = f"{user['id']}/{issue_id}/{unique_name}"

    try:
        sb.storage.from_("issue-media").upload(
            path, content, {"content-type": file.content_type or "application/octet-stream"}
        )
        logger.info("Uploaded %s to issue-media/%s", file.filename, path)
    except Exception as e:
        logger.exception("Upload failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")

    # Get public URL
    public_url = sb.storage.from_("issue-media").get_public_url(path)

    return {
        "storage_path": path,
        "public_url": public_url,
        "file_name": file.filename,
        "file_size": len(content),
        "content_type": file.content_type,
    }


@router.post("/chat-media")
async def upload_chat_media(
    file: UploadFile = File(...),
    conversation_id: str = Form(...),
    user: dict = Depends(get_current_user),
):
    """Upload a file to the chat-media bucket."""
    sb = get_supabase()

    # Verify user is participant
    try:
        conv = sb.table("conversations").select("customer_id, mechanic_id").eq("id", conversation_id).single().execute()
    except Exception:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if not conv.data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.data["customer_id"] != user["id"] and conv.data["mechanic_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not a participant")

    content = await file.read()
    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "bin"
    unique_name = f"{uuid.uuid4().hex[:12]}.{ext}"
    path = f"{conversation_id}/{unique_name}"

    try:
        sb.storage.from_("chat-media").upload(
            path, content, {"content-type": file.content_type or "application/octet-stream"}
        )
        logger.info("Uploaded %s to chat-media/%s", file.filename, path)
    except Exception as e:
        logger.exception("Chat upload failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")

    # Generate signed URL for private bucket
    signed = sb.storage.from_("chat-media").create_signed_url(path, 3600)

    return {
        "storage_path": path,
        "signed_url": signed.get("signedURL", ""),
        "file_name": file.filename,
        "file_size": len(content),
        "content_type": file.content_type,
    }


@router.post("/avatars")
async def upload_avatar(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Upload an avatar image."""
    sb = get_supabase()

    content = await file.read()
    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "jpg"
    path = f"{user['id']}/avatar.{ext}"

    # Remove old avatar first (ignore errors)
    try:
        sb.storage.from_("avatars").remove([path])
    except Exception:
        pass

    try:
        sb.storage.from_("avatars").upload(
            path, content, {"content-type": file.content_type or "image/jpeg", "upsert": "true"}
        )
        logger.info("Uploaded avatar for user %s", user["id"])
    except Exception as e:
        logger.exception("Avatar upload failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")

    public_url = sb.storage.from_("avatars").get_public_url(path)

    # Update profile with avatar URL
    sb.table("profiles").update({"avatar_url": public_url}).eq("id", user["id"]).execute()

    return {
        "storage_path": path,
        "public_url": public_url,
    }
