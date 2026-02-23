"""
Supabase client singleton for the backend.
Uses the service-role key for admin operations.
"""

import os
import logging
from functools import lru_cache
from supabase import create_client, Client

logger = logging.getLogger("salikchat.supabase")


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Return a singleton Supabase admin client (service-role key)."""
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        logger.error("SUPABASE_URL or SUPABASE_SERVICE_KEY not set!")
        raise RuntimeError("Missing Supabase configuration, check .env")
    logger.info("Creating Supabase client → %s", url)
    return create_client(url, key)


@lru_cache(maxsize=1)
def get_supabase_anon() -> Client:
    """Return a Supabase client with the anon key (for RLS-respecting ops)."""
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        logger.error("SUPABASE_URL or SUPABASE_KEY not set!")
        raise RuntimeError("Missing Supabase configuration, check .env")
    return create_client(url, key)
