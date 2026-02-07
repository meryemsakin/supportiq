"""
Category Pydantic Schemas

Request/response schemas for category-related operations.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# -----------------------------------------------------------------------------
# Category Create
# -----------------------------------------------------------------------------

class CategoryCreate(BaseModel):
    """Schema for creating a new category."""
    
    name: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[a-z_]+$",
        description="Category slug/key (lowercase, underscores only)"
    )
    display_name: str = Field(min_length=1, max_length=200)
    display_name_tr: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None)
    description_tr: Optional[str] = Field(default=None)
    
    icon: Optional[str] = Field(default=None, max_length=50)
    color: Optional[str] = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    
    # Priority
    priority_boost: int = Field(default=0, ge=-2, le=2)
    
    # SLA
    sla_first_response_hours: float = Field(default=4.0, gt=0)
    sla_resolution_hours: float = Field(default=24.0, gt=0)
    
    # Keywords for AI
    keywords: List[str] = Field(default_factory=list)
    keywords_tr: List[str] = Field(default_factory=list)
    negative_keywords: List[str] = Field(default_factory=list)
    
    # Routing
    default_team: Optional[str] = Field(default=None)
    requires_senior: bool = Field(default=False)
    auto_assign: bool = Field(default=True)
    
    # Examples for AI few-shot learning
    examples: List[Dict[str, str]] = Field(default_factory=list)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "technical_issue",
                "display_name": "Technical Issue",
                "display_name_tr": "Teknik Sorun",
                "description": "Technical problems and errors",
                "icon": "🔧",
                "color": "#EF4444",
                "priority_boost": 1,
                "keywords": ["error", "bug", "crash", "not working"],
                "keywords_tr": ["hata", "çalışmıyor", "bozuk"],
                "default_team": "technical_support",
                "sla_first_response_hours": 2.0
            }
        }
    )


# -----------------------------------------------------------------------------
# Category Update
# -----------------------------------------------------------------------------

class CategoryUpdate(BaseModel):
    """Schema for updating a category."""
    
    display_name: Optional[str] = Field(default=None, max_length=200)
    display_name_tr: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None)
    description_tr: Optional[str] = Field(default=None)
    
    icon: Optional[str] = Field(default=None, max_length=50)
    color: Optional[str] = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    
    is_active: Optional[bool] = Field(default=None)
    
    priority_boost: Optional[int] = Field(default=None, ge=-2, le=2)
    
    sla_first_response_hours: Optional[float] = Field(default=None, gt=0)
    sla_resolution_hours: Optional[float] = Field(default=None, gt=0)
    
    keywords: Optional[List[str]] = Field(default=None)
    keywords_tr: Optional[List[str]] = Field(default=None)
    negative_keywords: Optional[List[str]] = Field(default=None)
    
    default_team: Optional[str] = Field(default=None)
    requires_senior: Optional[bool] = Field(default=None)
    auto_assign: Optional[bool] = Field(default=None)
    
    examples: Optional[List[Dict[str, str]]] = Field(default=None)
    
    sort_order: Optional[int] = Field(default=None)


# -----------------------------------------------------------------------------
# Category Response
# -----------------------------------------------------------------------------

class CategoryResponse(BaseModel):
    """Schema for category in API responses."""
    
    id: UUID
    name: str
    display_name: str
    display_name_tr: Optional[str] = None
    description: Optional[str] = None
    description_tr: Optional[str] = None
    
    icon: Optional[str] = None
    color: Optional[str] = None
    
    is_active: bool
    is_default: bool
    
    priority_boost: int
    min_priority: int
    max_priority: int
    
    sla_first_response_hours: float
    sla_resolution_hours: float
    
    keywords: List[str]
    keywords_tr: List[str]
    negative_keywords: List[str]
    
    default_team: Optional[str] = None
    escalation_team: Optional[str] = None
    requires_senior: bool
    requires_specialist: bool
    auto_assign: bool
    
    # Statistics
    ticket_count: int
    avg_resolution_time: Optional[int] = None
    
    sort_order: int
    
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------------------------------
# Category List Response
# -----------------------------------------------------------------------------

class CategoryListResponse(BaseModel):
    """List of categories."""
    
    items: List[CategoryResponse]
    total: int


# -----------------------------------------------------------------------------
# Category Stats
# -----------------------------------------------------------------------------

class CategoryStats(BaseModel):
    """Statistics for a category."""
    
    category_id: UUID
    category_name: str
    display_name: str
    
    # Volume
    total_tickets: int
    open_tickets: int
    resolved_tickets: int
    escalated_tickets: int
    
    # Performance
    avg_first_response_time: Optional[int] = None  # seconds
    avg_resolution_time: Optional[int] = None
    sla_compliance_rate: Optional[float] = None
    
    # Quality
    avg_satisfaction_score: Optional[float] = None
    first_contact_resolution_rate: Optional[float] = None
    
    # Trends
    ticket_trend: Optional[str] = None  # increasing, stable, decreasing
    volume_change_percent: Optional[float] = None
    
    # Period
    period_start: datetime
    period_end: datetime
