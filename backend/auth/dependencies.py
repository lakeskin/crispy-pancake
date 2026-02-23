"""
FastAPI authentication dependencies.
Adapted from the START_TEMPLATE Flask decorators for FastAPI's DI system.
"""

import logging
import os
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from services.supabase_client import get_supabase

logger = logging.getLogger("salikchat.auth.deps")


# ---------------------------------------------------------------------------
# Token extraction
# ---------------------------------------------------------------------------

def _extract_token(request: Request) -> Optional[str]:
    """Pull the Bearer token from the Authorization header."""
    auth = request.headers.get("Authorization")
    if not auth:
        return None
    parts = auth.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def _verify_jwt(token: str) -> dict:
    """
    Verify a Supabase JWT.
    Tries local decode first (HS256), then falls back to Supabase API.
    Supabase may use ES256, so the local decode may not work.
    """
    jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
    if jwt_secret:
        try:
            payload = jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
                options={"verify_exp": True},
            )
            logger.debug("JWT verified locally for user %s", payload.get("sub"))
            return {
                "id": payload.get("sub"),
                "email": payload.get("email"),
                "role": payload.get("user_metadata", {}).get("role", "customer"),
                "user_metadata": payload.get("user_metadata", {}),
            }
        except jwt.ExpiredSignatureError:
            logger.warning("JWT expired")
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError as e:
            # Token may use a different algorithm (e.g. ES256).
            # Fall through to Supabase API verification.
            logger.debug("Local JWT decode failed (%s), falling back to Supabase API", e)

    # Fallback: ask Supabase to validate
    try:
        sb = get_supabase()
        user_resp = sb.auth.get_user(token)
        u = user_resp.user
        logger.debug("JWT verified via Supabase API for user %s", u.id)
        return {
            "id": u.id,
            "email": u.email,
            "role": (u.user_metadata or {}).get("role", "customer"),
            "user_metadata": u.user_metadata or {},
        }
    except Exception as e:
        logger.warning("Supabase API token verification failed: %s", e)
        raise HTTPException(status_code=401, detail="Invalid token")


# ---------------------------------------------------------------------------
# Dependency callables
# ---------------------------------------------------------------------------

async def get_current_user(request: Request) -> dict:
    """
    FastAPI dependency — require authentication.
    Usage:  user = Depends(get_current_user)
    """
    token = _extract_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return _verify_jwt(token)


async def get_optional_user(request: Request) -> Optional[dict]:
    """
    FastAPI dependency — authenticate if token present, else None.
    Usage:  user = Depends(get_optional_user)
    """
    token = _extract_token(request)
    if not token:
        return None
    try:
        return _verify_jwt(token)
    except HTTPException:
        return None


def require_role(*allowed_roles: str):
    """
    FastAPI dependency factory — require specific role(s).
    Usage:  user = Depends(require_role("admin"))
    """
    async def _check(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {', '.join(allowed_roles)}",
            )
        return user
    return _check
