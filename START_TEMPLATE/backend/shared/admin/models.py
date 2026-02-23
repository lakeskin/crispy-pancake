"""
Admin Pydantic Models
=====================
Type-safe models for admin API requests and responses.

These models ensure consistent API responses across all admin endpoints.
"""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Literal
from datetime import datetime


# =============================================================================
# Config Definition Models
# =============================================================================

class ConfigDefinition(BaseModel):
    """Definition of a configuration file for the admin system."""
    path: str = Field(..., description="Path to the configuration file")
    name: str = Field(..., description="Human-readable name")
    description: str = Field("", description="Description of this config")
    category: str = Field("core", description="Category for grouping (core, models, system, business, ui)")
    format: Optional[Literal['yaml', 'json']] = Field(None, description="File format (auto-detected if None)")
    
    class Config:
        extra = 'allow'


# =============================================================================
# API Response Models
# =============================================================================

class ConfigListItem(BaseModel):
    """Item in the config list response."""
    id: str = Field(..., description="Unique config identifier")
    name: str = Field(..., description="Human-readable name")
    description: str = Field("", description="Config description")
    category: str = Field(..., description="Config category")
    path: str = Field(..., description="File path")
    exists: bool = Field(..., description="Whether file exists")
    size: int = Field(0, description="File size in bytes")
    last_modified: Optional[str] = Field(None, description="ISO timestamp of last modification")
    format: Optional[str] = Field(None, description="File format (yaml/json)")


class ConfigResponse(BaseModel):
    """Response when fetching a configuration."""
    success: bool = Field(..., description="Whether the request succeeded")
    config_id: Optional[str] = Field(None, description="Config identifier")
    name: Optional[str] = Field(None, description="Config name")
    data: Optional[Dict[str, Any]] = Field(None, description="Configuration data")
    path: Optional[str] = Field(None, description="File path")
    last_modified: Optional[str] = Field(None, description="ISO timestamp")
    error: Optional[str] = Field(None, description="Error message if failed")


class SaveConfigResponse(BaseModel):
    """Response when saving a configuration."""
    success: bool = Field(..., description="Whether save succeeded")
    message: Optional[str] = Field(None, description="Success/info message")
    backup_path: Optional[str] = Field(None, description="Path to backup if created")
    error: Optional[str] = Field(None, description="Error message if failed")


class SectionResponse(BaseModel):
    """Response when fetching a config section."""
    success: bool
    config_id: str
    section: str
    data: Any


# =============================================================================
# Search Models
# =============================================================================

class SearchMatch(BaseModel):
    """A single search match."""
    path: str = Field(..., description="Dot-notation path to match")
    type: Literal['key', 'value'] = Field(..., description="Whether match is in key or value")
    match: str = Field(..., description="The matched string")


class SearchResult(BaseModel):
    """Search result for a single config."""
    config_id: str = Field(..., description="Config identifier")
    config_name: str = Field(..., description="Config name")
    matches: List[SearchMatch] = Field(default_factory=list, description="List of matches")


class SearchResponse(BaseModel):
    """Response for search across configs."""
    success: bool
    query: str
    results: List[SearchResult]
    total_matches: int


# =============================================================================
# Backup Models
# =============================================================================

class BackupItem(BaseModel):
    """Information about a backup file."""
    filename: str = Field(..., description="Backup filename")
    path: str = Field(..., description="Full path to backup")
    size: int = Field(..., description="File size in bytes")
    created: str = Field(..., description="ISO timestamp of creation")
    config_name: Optional[str] = Field(None, description="Original config name")


class BackupListResponse(BaseModel):
    """Response when listing backups."""
    success: bool
    backups: List[BackupItem]
    total: int


class RestoreResponse(BaseModel):
    """Response when restoring a backup."""
    success: bool
    message: str
    restored_from: str
    restored_to: str
    previous_backup: Optional[str] = None


# =============================================================================
# Reload Models
# =============================================================================

class ReloadError(BaseModel):
    """Error during config reload."""
    config: str
    error: str


class ReloadResponse(BaseModel):
    """Response for hot-reload endpoint."""
    success: bool
    reloaded: List[str]
    errors: List[ReloadError]
    message: str


# =============================================================================
# Request Models
# =============================================================================

class SaveConfigRequest(BaseModel):
    """Request body for saving a config."""
    data: Dict[str, Any] = Field(..., description="Configuration data to save")


class SaveSectionRequest(BaseModel):
    """Request body for saving a config section."""
    data: Any = Field(..., description="Section data to save")


class SearchRequest(BaseModel):
    """Request body for search."""
    query: str = Field(..., min_length=1, description="Search query")
    case_sensitive: bool = Field(False, description="Case-sensitive search")


class CleanupRequest(BaseModel):
    """Request for backup cleanup."""
    keep_count: int = Field(10, ge=1, description="Number of backups to keep per config")
    config_name: Optional[str] = Field(None, description="Only cleanup this config")
    older_than_days: Optional[int] = Field(None, ge=1, description="Delete backups older than N days")
