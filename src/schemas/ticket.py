"""
Ticket Pydantic Schemas

Request/response schemas for ticket-related operations.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr, ConfigDict

from src.schemas.common import (
    ClassificationResult,
    SentimentResult,
    PriorityResult,
    RoutingResult,
    SuggestedResponseItem,
    PaginatedResponse,
)


# -----------------------------------------------------------------------------
# Ticket Create
# -----------------------------------------------------------------------------

class TicketCreate(BaseModel):
    """Schema for creating a new ticket."""
    
    # Required fields
    content: str = Field(
        min_length=1,
        max_length=50000,
        description="Ticket content/body"
    )
    
    # Optional content fields
    subject: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Ticket subject/title"
    )
    
    # Customer info
    customer_email: Optional[EmailStr] = Field(
        default=None,
        description="Customer email address"
    )
    customer_name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Customer name"
    )
    customer_tier: Optional[str] = Field(
        default="standard",
        description="Customer tier (free, standard, premium, vip)"
    )
    
    # External system
    external_id: Optional[str] = Field(
        default=None,
        max_length=255,
        description="External system ticket ID"
    )
    external_system: Optional[str] = Field(
        default=None,
        max_length=50,
        description="External system name (zendesk, freshdesk, etc.)"
    )
    
    # Metadata
    source: Optional[str] = Field(
        default="api",
        description="Ticket source (api, email, zendesk, freshdesk, webhook)"
    )
    channel: Optional[str] = Field(
        default=None,
        description="Communication channel (web, mobile, email, chat)"
    )
    language: Optional[str] = Field(
        default=None,
        max_length=10,
        description="Ticket language (auto-detected if not provided)"
    )
    tags: Optional[List[str]] = Field(
        default_factory=list,
        description="Custom tags"
    )
    custom_fields: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional custom fields"
    )
    
    # Processing options
    process_async: bool = Field(
        default=True,
        description="Process ticket asynchronously via Celery"
    )
    skip_routing: bool = Field(
        default=False,
        description="Skip automatic routing"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": "Hello, I can't log in to your app. I'm getting error code 500.",
                "subject": "Login issue - Error 500",
                "customer_email": "customer@example.com",
                "customer_name": "John Smith",
                "customer_tier": "premium",
                "source": "api",
                "language": "en"
            }
        }
    )


# -----------------------------------------------------------------------------
# Ticket Update
# -----------------------------------------------------------------------------

class TicketUpdate(BaseModel):
    """Schema for updating a ticket."""
    
    subject: Optional[str] = Field(default=None, max_length=500)
    content: Optional[str] = Field(default=None, max_length=50000)
    status: Optional[str] = Field(default=None)
    category: Optional[str] = Field(default=None)
    priority: Optional[int] = Field(default=None, ge=1, le=5)
    assigned_agent_id: Optional[UUID] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)
    custom_fields: Optional[Dict[str, Any]] = Field(default=None)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "in_progress",
                "priority": 4,
                "tags": ["urgent", "vip"]
            }
        }
    )


# -----------------------------------------------------------------------------
# Ticket Response
# -----------------------------------------------------------------------------

class TicketResponse(BaseModel):
    """Schema for ticket in API responses."""
    
    id: UUID
    external_id: Optional[str] = None
    external_system: Optional[str] = None
    
    # Content
    subject: Optional[str] = None
    content: str
    
    # Status
    status: str
    
    # Classification
    category: Optional[str] = None
    category_confidence: Optional[float] = None
    classification_reasoning: Optional[str] = None
    
    # Sentiment
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None
    
    # Priority
    priority: int
    priority_level: Optional[str] = None
    priority_factors: Optional[List[str]] = None
    
    # Assignment
    assigned_agent_id: Optional[UUID] = None
    assignment_reason: Optional[str] = None
    
    # Customer
    customer_id: Optional[UUID] = None
    customer_email: Optional[str] = None
    customer_name: Optional[str] = None
    customer_tier: Optional[str] = None
    
    # Language
    language: str
    
    # Metadata
    source: str
    channel: Optional[str] = None
    tags: List[str] = []
    custom_fields: Dict[str, Any] = {}
    
    # Suggested responses
    suggested_responses: Optional[List[Dict[str, Any]]] = None
    
    # Flags
    is_processed: bool
    escalated: bool = False
    sla_breached: bool = False
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    first_response_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------------------------------
# Ticket List Response
# -----------------------------------------------------------------------------

class TicketListResponse(PaginatedResponse[TicketResponse]):
    """Paginated list of tickets."""
    pass


# -----------------------------------------------------------------------------
# Ticket Process Response
# -----------------------------------------------------------------------------

class TicketProcessResponse(BaseModel):
    """Response after processing a ticket."""
    
    ticket_id: UUID
    status: str = Field(description="Processing status (processed, queued, failed)")
    
    # Processing results
    classification: Optional[ClassificationResult] = None
    sentiment: Optional[SentimentResult] = None
    priority: Optional[PriorityResult] = None
    routing: Optional[RoutingResult] = None
    suggested_responses: Optional[List[SuggestedResponseItem]] = None
    
    # Processing time
    processing_time_ms: Optional[int] = Field(
        default=None,
        description="Processing time in milliseconds"
    )
    
    # Error info
    error: Optional[str] = Field(default=None, description="Error message if failed")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticket_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "processed",
                "classification": {
                    "primary_category": "technical_issue",
                    "confidence": 0.92,
                    "reasoning": "Customer mentions 'not working' and 'error'"
                },
                "sentiment": {
                    "sentiment": "negative",
                    "score": -0.6,
                    "confidence": 0.88
                },
                "priority": {
                    "score": 4,
                    "level": "high",
                    "factors": ["negative_sentiment", "premium_customer"]
                },
                "routing": {
                    "agent_id": "456e7890-e89b-12d3-a456-426614174000",
                    "agent_name": "Mehmet Demir",
                    "reason": "skill_match",
                    "confidence": 0.95
                },
                "processing_time_ms": 1250
            }
        }
    )


# -----------------------------------------------------------------------------
# Ticket Filter Parameters
# -----------------------------------------------------------------------------

class TicketFilterParams(BaseModel):
    """Filter parameters for listing tickets."""
    
    status: Optional[str] = Field(default=None, description="Filter by status")
    category: Optional[str] = Field(default=None, description="Filter by category")
    priority: Optional[int] = Field(default=None, ge=1, le=5, description="Filter by priority")
    min_priority: Optional[int] = Field(default=None, ge=1, le=5, description="Minimum priority")
    sentiment: Optional[str] = Field(default=None, description="Filter by sentiment")
    assigned_agent_id: Optional[UUID] = Field(default=None, description="Filter by assigned agent")
    customer_email: Optional[str] = Field(default=None, description="Filter by customer email")
    source: Optional[str] = Field(default=None, description="Filter by source")
    is_processed: Optional[bool] = Field(default=None, description="Filter by processing status")
    escalated: Optional[bool] = Field(default=None, description="Filter by escalation status")
    
    # Date filters
    created_after: Optional[datetime] = Field(default=None)
    created_before: Optional[datetime] = Field(default=None)
    
    # Search
    search: Optional[str] = Field(default=None, description="Search in subject and content")


# -----------------------------------------------------------------------------
# Ticket Reassign Request
# -----------------------------------------------------------------------------

class TicketReassignRequest(BaseModel):
    """Request to reassign a ticket."""
    
    agent_id: Optional[UUID] = Field(
        default=None,
        description="New agent ID (null to unassign)"
    )
    reason: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Reason for reassignment"
    )
    notify_previous_agent: bool = Field(
        default=True,
        description="Notify previous agent about reassignment"
    )
    notify_new_agent: bool = Field(
        default=True,
        description="Notify new agent about assignment"
    )


# -----------------------------------------------------------------------------
# Ticket Bulk Operations
# -----------------------------------------------------------------------------

class TicketBulkUpdateRequest(BaseModel):
    """Request for bulk ticket updates."""
    
    ticket_ids: List[UUID] = Field(
        min_length=1,
        max_length=100,
        description="List of ticket IDs to update"
    )
    status: Optional[str] = Field(default=None)
    category: Optional[str] = Field(default=None)
    priority: Optional[int] = Field(default=None, ge=1, le=5)
    assigned_agent_id: Optional[UUID] = Field(default=None)
    add_tags: Optional[List[str]] = Field(default=None)
    remove_tags: Optional[List[str]] = Field(default=None)


class TicketBulkUpdateResponse(BaseModel):
    """Response for bulk ticket updates."""
    
    updated: int = Field(description="Number of tickets updated")
    failed: int = Field(description="Number of tickets that failed to update")
    errors: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Error details for failed updates"
    )
