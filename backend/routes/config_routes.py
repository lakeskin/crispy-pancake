"""
Config routes — serve YAML config values to the frontend.
No secrets exposed — only UI configuration (categories, urgency levels, etc.)
"""

from pathlib import Path
import yaml
from fastapi import APIRouter

router = APIRouter(prefix="/api/config", tags=["config"])

# Load config once
_config_path = Path(__file__).resolve().parent.parent / "config.yaml"
with open(_config_path, "r", encoding="utf-8") as f:
    _config = yaml.safe_load(f)


@router.get("/categories")
async def get_categories():
    return {"categories": _config["cars"]["categories"]}


@router.get("/urgency-levels")
async def get_urgency_levels():
    return {"urgency_levels": _config["cars"]["urgency_levels"]}


@router.get("/budget-ranges")
async def get_budget_ranges():
    return {"budget_ranges": _config["cars"]["budget_ranges"]}


@router.get("/confidence-levels")
async def get_confidence_levels():
    return {"confidence_levels": _config["cars"]["confidence_levels"]}


@router.get("/specializations")
async def get_specializations():
    return {"specializations": _config["mechanic"]["specializations"]}


@router.get("/upload-limits")
async def get_upload_limits():
    return {"uploads": _config["uploads"]}
