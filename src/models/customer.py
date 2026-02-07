"""
Customer Model

Represents customers who submit support tickets.
"""

from datetime import datetime
from typing import Optional
from enum import Enum

from sqlalchemy import (
    Column, String, Integer, Float, DateTime,
    Boolean, JSON, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from src.database import Base


class CustomerTier(str, Enum):
    """Customer tier levels."""
    FREE = "free"
    STANDARD = "standard"
    PREMIUM = "premium"
    VIP = "vip"
    ENTERPRISE = "enterprise"


class Customer(Base):
    """
    Customer model representing a support ticket submitter.
    
    Attributes:
        id: Unique customer identifier
        external_id: ID from external system
        email: Customer email address
        name: Full name
        
        # Tier and status
        tier: Customer tier (free, standard, premium, vip)
        is_active: Whether customer account is active
        
        # Contact info
        phone: Phone number
        company: Company name
        
        # Preferences
        preferred_language: Preferred communication language
        timezone: Customer timezone
        
        # History and metrics
        total_tickets: Total tickets submitted
        avg_satisfaction: Average satisfaction score
        
        # External references
        zendesk_user_id: Zendesk user ID
        freshdesk_contact_id: Freshdesk contact ID
    """
    
    __tablename__ = "customers"
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    
    # External reference
    external_id = Column(String(255), nullable=True, unique=True)
    external_system = Column(String(50), nullable=True)
    
    # Basic info
    email = Column(String(255), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    
    # Contact info
    phone = Column(String(50), nullable=True)
    company = Column(String(255), nullable=True, index=True)
    job_title = Column(String(100), nullable=True)
    
    # Tier and status
    tier = Column(
        SQLEnum(CustomerTier),
        default=CustomerTier.STANDARD,
        nullable=False,
        index=True
    )
    is_active = Column(Boolean, default=True, index=True)
    is_verified = Column(Boolean, default=False)
    
    # Preferences
    preferred_language = Column(String(10), default="tr")
    timezone = Column(String(50), default="Europe/Istanbul")
    communication_preference = Column(String(20), default="email")  # email, phone, chat
    
    # Customer value (for prioritization)
    lifetime_value = Column(Float, nullable=True)  # Total spending
    monthly_recurring_revenue = Column(Float, nullable=True)
    subscription_plan = Column(String(100), nullable=True)
    subscription_start = Column(DateTime(timezone=True), nullable=True)
    
    # History metrics
    total_tickets = Column(Integer, default=0)
    open_tickets = Column(Integer, default=0)
    resolved_tickets = Column(Integer, default=0)
    avg_satisfaction = Column(Float, nullable=True)  # 0-5
    last_satisfaction_score = Column(Float, nullable=True)
    
    # Engagement
    first_contact_at = Column(DateTime(timezone=True), nullable=True)
    last_contact_at = Column(DateTime(timezone=True), nullable=True)
    
    # Risk indicators
    churn_risk = Column(Float, nullable=True)  # 0-1
    sentiment_trend = Column(String(20), nullable=True)  # improving, stable, declining
    
    # Notes and tags
    notes = Column(JSON, default=list)  # List of note objects
    tags = Column(JSON, default=list)  # Custom tags
    custom_fields = Column(JSON, default=dict)
    
    # External system IDs
    zendesk_user_id = Column(String(255), nullable=True)
    freshdesk_contact_id = Column(String(255), nullable=True)
    crm_id = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    tickets = relationship("Ticket", back_populates="customer")
    
    def __repr__(self) -> str:
        return f"<Customer(id={self.id}, email={self.email}, tier={self.tier})>"
    
    @property
    def full_name(self) -> str:
        """Get customer's full name."""
        if self.name:
            return self.name
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.last_name:
            parts.append(self.last_name)
        return " ".join(parts) if parts else self.email.split("@")[0]
    
    @property
    def is_vip(self) -> bool:
        """Check if customer is VIP tier or higher."""
        return self.tier in [CustomerTier.VIP, CustomerTier.ENTERPRISE]
    
    @property
    def priority_boost(self) -> int:
        """Get priority boost based on tier."""
        boosts = {
            CustomerTier.FREE: -1,
            CustomerTier.STANDARD: 0,
            CustomerTier.PREMIUM: 1,
            CustomerTier.VIP: 2,
            CustomerTier.ENTERPRISE: 2,
        }
        return boosts.get(self.tier, 0)
    
    def get_sla_multiplier(self) -> float:
        """Get SLA time multiplier based on tier (lower = faster response)."""
        multipliers = {
            CustomerTier.FREE: 2.0,
            CustomerTier.STANDARD: 1.0,
            CustomerTier.PREMIUM: 0.75,
            CustomerTier.VIP: 0.5,
            CustomerTier.ENTERPRISE: 0.25,
        }
        return multipliers.get(self.tier, 1.0)
