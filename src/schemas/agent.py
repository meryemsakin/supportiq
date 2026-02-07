"""
Agent Pydantic Schemas

Request/response schemas for agent-related operations.
"""

from datetime import datetime
from typing import Optional, List, Dict
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr, ConfigDict

from src.schemas.common import PaginatedResponse


# -----------------------------------------------------------------------------
# Agent Create
# -----------------------------------------------------------------------------

class AgentCreate(BaseModel):
    """Schema for creating a new agent."""
    
    email: EmailStr = Field(description="Agent email address")
    name: str = Field(min_length=1, max_length=255, description="Full name")
    display_name: Optional[str] = Field(default=None, max_length=100)
    
    # Role and team
    role: str = Field(default="agent", description="Agent role")
    team: Optional[str] = Field(default=None, max_length=100)
    department: Optional[str] = Field(default=None, max_length=100)
    
    # Skills
    skills: List[str] = Field(default_factory=list, description="Skill categories")
    languages: List[str] = Field(default=["tr"], description="Languages spoken")
    experience_level: int = Field(default=1, ge=1, le=5, description="Experience level")
    
    # Workload
    max_load: int = Field(default=10, ge=1, description="Maximum concurrent tickets")
    daily_capacity: int = Field(default=50, ge=1, description="Daily ticket capacity")
    
    # Working hours
    work_hours_start: str = Field(default="09:00", pattern=r"^\d{2}:\d{2}$")
    work_hours_end: str = Field(default="18:00", pattern=r"^\d{2}:\d{2}$")
    timezone: str = Field(default="Europe/Istanbul")
    working_days: List[int] = Field(default=[0, 1, 2, 3, 4])
    
    # Capabilities
    can_handle_critical: bool = Field(default=False)
    can_handle_vip: bool = Field(default=False)
    
    # External IDs
    external_id: Optional[str] = Field(default=None)
    zendesk_user_id: Optional[str] = Field(default=None)
    freshdesk_agent_id: Optional[str] = Field(default=None)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "mehmet@example.com",
                "name": "Mehmet Demir",
                "role": "agent",
                "team": "technical_support",
                "skills": ["technical_issue", "bug_report"],
                "languages": ["tr", "en"],
                "experience_level": 3,
                "max_load": 15
            }
        }
    )


# -----------------------------------------------------------------------------
# Agent Update
# -----------------------------------------------------------------------------

class AgentUpdate(BaseModel):
    """Schema for updating an agent."""
    
    name: Optional[str] = Field(default=None, max_length=255)
    display_name: Optional[str] = Field(default=None, max_length=100)
    
    # Role and team
    role: Optional[str] = Field(default=None)
    team: Optional[str] = Field(default=None)
    department: Optional[str] = Field(default=None)
    
    # Skills
    skills: Optional[List[str]] = Field(default=None)
    languages: Optional[List[str]] = Field(default=None)
    experience_level: Optional[int] = Field(default=None, ge=1, le=5)
    specializations: Optional[Dict[str, float]] = Field(default=None)
    
    # Workload
    max_load: Optional[int] = Field(default=None, ge=1)
    daily_capacity: Optional[int] = Field(default=None, ge=1)
    
    # Availability
    status: Optional[str] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)
    
    # Working hours
    work_hours_start: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    work_hours_end: Optional[str] = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    timezone: Optional[str] = Field(default=None)
    working_days: Optional[List[int]] = Field(default=None)
    
    # Capabilities
    can_handle_critical: Optional[bool] = Field(default=None)
    can_handle_vip: Optional[bool] = Field(default=None)
    
    # External IDs
    zendesk_user_id: Optional[str] = Field(default=None)
    freshdesk_agent_id: Optional[str] = Field(default=None)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "online",
                "max_load": 20,
                "skills": ["technical_issue", "bug_report", "billing_question"]
            }
        }
    )


# -----------------------------------------------------------------------------
# Agent Response
# -----------------------------------------------------------------------------

class AgentResponse(BaseModel):
    """Schema for agent in API responses."""
    
    id: UUID
    external_id: Optional[str] = None
    
    # Basic info
    email: str
    name: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    
    # Role and team
    role: str
    team: Optional[str] = None
    department: Optional[str] = None
    
    # Skills
    skills: List[str]
    languages: List[str]
    experience_level: int
    specializations: Dict[str, float] = {}
    
    # Workload
    current_load: int
    max_load: int
    daily_capacity: int
    tickets_handled_today: int
    
    # Computed workload fields
    load_percentage: float
    available_capacity: int
    is_available: bool
    
    # Availability
    status: str
    is_active: bool
    last_active_at: Optional[datetime] = None
    
    # Working hours
    work_hours_start: str
    work_hours_end: str
    timezone: str
    working_days: List[int]
    
    # Capabilities
    can_handle_critical: bool
    can_handle_vip: bool
    
    # Performance metrics
    avg_resolution_time: Optional[int] = None
    avg_first_response_time: Optional[int] = None
    customer_satisfaction_score: Optional[float] = None
    quality_score: Optional[float] = None
    
    # Statistics
    total_tickets_resolved: int
    tickets_resolved_today: int
    tickets_escalated: int
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------------------------------
# Agent List Response
# -----------------------------------------------------------------------------

class AgentListResponse(PaginatedResponse[AgentResponse]):
    """Paginated list of agents."""
    pass


# -----------------------------------------------------------------------------
# Agent Filter Parameters
# -----------------------------------------------------------------------------

class AgentFilterParams(BaseModel):
    """Filter parameters for listing agents."""
    
    status: Optional[str] = Field(default=None, description="Filter by status")
    team: Optional[str] = Field(default=None, description="Filter by team")
    role: Optional[str] = Field(default=None, description="Filter by role")
    is_active: Optional[bool] = Field(default=None, description="Filter by active status")
    is_available: Optional[bool] = Field(default=None, description="Filter by availability")
    skill: Optional[str] = Field(default=None, description="Filter by skill")
    language: Optional[str] = Field(default=None, description="Filter by language")
    can_handle_critical: Optional[bool] = Field(default=None)
    can_handle_vip: Optional[bool] = Field(default=None)
    
    # Search
    search: Optional[str] = Field(default=None, description="Search in name and email")


# -----------------------------------------------------------------------------
# Agent Status Update
# -----------------------------------------------------------------------------

class AgentStatusUpdate(BaseModel):
    """Request to update agent status."""
    
    status: str = Field(description="New status (online, offline, busy, away, on_break)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "online"
            }
        }
    )


# -----------------------------------------------------------------------------
# Agent Performance Stats
# -----------------------------------------------------------------------------

class AgentPerformanceStats(BaseModel):
    """Agent performance statistics."""
    
    agent_id: UUID
    agent_name: str
    
    # Volume
    tickets_assigned: int
    tickets_resolved: int
    tickets_escalated: int
    tickets_reopened: int
    
    # Time metrics (in seconds)
    avg_first_response_time: Optional[int] = None
    avg_resolution_time: Optional[int] = None
    avg_handle_time: Optional[int] = None
    
    # Quality
    customer_satisfaction_score: Optional[float] = None
    quality_score: Optional[float] = None
    first_contact_resolution_rate: Optional[float] = None
    
    # Period
    period_start: datetime
    period_end: datetime
