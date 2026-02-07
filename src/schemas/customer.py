"""
Customer Pydantic Schemas

Request/response schemas for customer-related operations.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr, ConfigDict


# -----------------------------------------------------------------------------
# Customer Create
# -----------------------------------------------------------------------------

class CustomerCreate(BaseModel):
    """Schema for creating a new customer."""
    
    email: EmailStr = Field(description="Customer email address")
    name: Optional[str] = Field(default=None, max_length=255)
    first_name: Optional[str] = Field(default=None, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)
    
    # Contact
    phone: Optional[str] = Field(default=None, max_length=50)
    company: Optional[str] = Field(default=None, max_length=255)
    job_title: Optional[str] = Field(default=None, max_length=100)
    
    # Tier
    tier: str = Field(default="standard")
    
    # Preferences
    preferred_language: str = Field(default="tr", max_length=10)
    timezone: str = Field(default="Europe/Istanbul", max_length=50)
    
    # External
    external_id: Optional[str] = Field(default=None)
    zendesk_user_id: Optional[str] = Field(default=None)
    freshdesk_contact_id: Optional[str] = Field(default=None)
    crm_id: Optional[str] = Field(default=None)
    
    # Custom data
    tags: List[str] = Field(default_factory=list)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "musteri@example.com",
                "name": "Ahmet Yılmaz",
                "company": "ABC Şirketi",
                "tier": "premium",
                "preferred_language": "tr"
            }
        }
    )


# -----------------------------------------------------------------------------
# Customer Update
# -----------------------------------------------------------------------------

class CustomerUpdate(BaseModel):
    """Schema for updating a customer."""
    
    name: Optional[str] = Field(default=None, max_length=255)
    first_name: Optional[str] = Field(default=None, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)
    
    phone: Optional[str] = Field(default=None, max_length=50)
    company: Optional[str] = Field(default=None, max_length=255)
    job_title: Optional[str] = Field(default=None, max_length=100)
    
    tier: Optional[str] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)
    
    preferred_language: Optional[str] = Field(default=None, max_length=10)
    timezone: Optional[str] = Field(default=None, max_length=50)
    
    zendesk_user_id: Optional[str] = Field(default=None)
    freshdesk_contact_id: Optional[str] = Field(default=None)
    crm_id: Optional[str] = Field(default=None)
    
    tags: Optional[List[str]] = Field(default=None)
    custom_fields: Optional[Dict[str, Any]] = Field(default=None)


# -----------------------------------------------------------------------------
# Customer Response
# -----------------------------------------------------------------------------

class CustomerResponse(BaseModel):
    """Schema for customer in API responses."""
    
    id: UUID
    external_id: Optional[str] = None
    
    # Basic info
    email: str
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: str
    
    # Contact
    phone: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    
    # Tier
    tier: str
    is_active: bool
    is_verified: bool
    is_vip: bool
    
    # Preferences
    preferred_language: str
    timezone: str
    communication_preference: str
    
    # Value
    lifetime_value: Optional[float] = None
    monthly_recurring_revenue: Optional[float] = None
    subscription_plan: Optional[str] = None
    
    # Metrics
    total_tickets: int
    open_tickets: int
    resolved_tickets: int
    avg_satisfaction: Optional[float] = None
    
    # Engagement
    first_contact_at: Optional[datetime] = None
    last_contact_at: Optional[datetime] = None
    
    # Risk
    churn_risk: Optional[float] = None
    sentiment_trend: Optional[str] = None
    
    # Custom
    tags: List[str]
    custom_fields: Dict[str, Any]
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------------------------------
# Customer Search
# -----------------------------------------------------------------------------

class CustomerSearchParams(BaseModel):
    """Search parameters for customers."""
    
    search: Optional[str] = Field(default=None, description="Search in email, name, company")
    email: Optional[str] = Field(default=None)
    company: Optional[str] = Field(default=None)
    tier: Optional[str] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)
    has_open_tickets: Optional[bool] = Field(default=None)
    min_tickets: Optional[int] = Field(default=None, ge=0)


# -----------------------------------------------------------------------------
# Customer Note
# -----------------------------------------------------------------------------

class CustomerNoteCreate(BaseModel):
    """Schema for adding a note to customer."""
    
    content: str = Field(min_length=1, max_length=5000)
    is_pinned: bool = Field(default=False)


class CustomerNoteResponse(BaseModel):
    """Schema for customer note."""
    
    id: str
    content: str
    is_pinned: bool
    created_by: Optional[str] = None
    created_at: datetime
