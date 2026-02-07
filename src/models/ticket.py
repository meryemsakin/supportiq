"""
Ticket Model

Represents customer support tickets in the system.
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum

from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime, 
    ForeignKey, Enum as SQLEnum, JSON, Boolean
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from src.database import Base


class TicketStatus(str, Enum):
    """Ticket status enumeration."""
    NEW = "new"
    OPEN = "open"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ESCALATED = "escalated"


class TicketPriority(int, Enum):
    """Ticket priority levels."""
    MINIMAL = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    CRITICAL = 5


class TicketSentiment(str, Enum):
    """Sentiment analysis results."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    ANGRY = "angry"


class Ticket(Base):
    """
    Ticket model representing a customer support ticket.
    
    Attributes:
        id: Unique ticket identifier (UUID)
        external_id: ID from external system (Zendesk, Freshdesk, etc.)
        external_system: Name of external system
        subject: Ticket subject/title
        content: Full ticket content/body
        content_cleaned: Preprocessed/cleaned content
        
        # Classification
        category: Primary category (AI-assigned)
        category_confidence: Classification confidence score
        secondary_categories: Additional relevant categories
        
        # Sentiment
        sentiment: Detected sentiment
        sentiment_score: Sentiment score (-1 to 1)
        
        # Priority
        priority: Priority level (1-5)
        priority_factors: Factors contributing to priority
        
        # Routing
        assigned_agent_id: Currently assigned agent
        assignment_reason: Why this agent was chosen
        
        # Customer info
        customer_id: Customer UUID
        customer_email: Customer email
        customer_name: Customer name
        language: Detected/specified language
        
        # Metadata
        source: Where ticket came from (email, api, zendesk, etc.)
        tags: Custom tags
        custom_fields: Additional custom data
        
        # Suggested responses
        suggested_responses: AI-suggested response texts
        
        # Timestamps
        created_at: When ticket was created
        updated_at: Last update time
        first_response_at: When first response was sent
        resolved_at: When ticket was resolved
    """
    
    __tablename__ = "tickets"
    
    # Primary key
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        index=True
    )
    
    # External system reference
    external_id = Column(String(255), nullable=True, index=True)
    external_system = Column(String(50), nullable=True)  # zendesk, freshdesk, email, api
    
    # Content
    subject = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)
    content_cleaned = Column(Text, nullable=True)
    
    # Status
    status = Column(
        SQLEnum(TicketStatus), 
        default=TicketStatus.NEW,
        nullable=False,
        index=True
    )
    
    # Classification
    category = Column(String(100), nullable=True, index=True)
    category_confidence = Column(Float, nullable=True)
    secondary_categories = Column(JSON, nullable=True)  # List of (category, confidence) tuples
    classification_reasoning = Column(Text, nullable=True)
    
    # Sentiment
    sentiment = Column(SQLEnum(TicketSentiment), nullable=True, index=True)
    sentiment_score = Column(Float, nullable=True)  # -1 (negative) to 1 (positive)
    
    # Priority
    priority = Column(Integer, default=3, nullable=False, index=True)
    priority_level = Column(String(20), nullable=True)  # minimal, low, medium, high, critical
    priority_factors = Column(JSON, nullable=True)  # List of factors that influenced priority
    
    # Routing
    assigned_agent_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    previous_agent_id = Column(UUID(as_uuid=True), nullable=True)
    assignment_reason = Column(String(100), nullable=True)
    assignment_confidence = Column(Float, nullable=True)
    escalated = Column(Boolean, default=False)
    escalation_reason = Column(Text, nullable=True)
    
    # Customer
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    customer_email = Column(String(255), nullable=True, index=True)
    customer_name = Column(String(255), nullable=True)
    customer_tier = Column(String(50), default="standard")  # free, standard, premium, vip
    
    # Language
    language = Column(String(10), default="tr", nullable=False)
    language_confidence = Column(Float, nullable=True)
    
    # Source and metadata
    source = Column(String(50), default="api")  # api, email, zendesk, freshdesk, webhook
    channel = Column(String(50), nullable=True)  # web, mobile, email, chat
    tags = Column(JSON, default=list)  # List of string tags
    custom_fields = Column(JSON, default=dict)
    
    # Suggested responses
    suggested_responses = Column(JSON, nullable=True)  # List of suggested response objects
    
    # Processing flags
    is_processed = Column(Boolean, default=False)
    processing_error = Column(Text, nullable=True)
    
    # SLA tracking
    sla_due_at = Column(DateTime(timezone=True), nullable=True)
    sla_breached = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True), 
        default=datetime.utcnow, 
        nullable=False,
        index=True
    )
    updated_at = Column(
        DateTime(timezone=True), 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow,
        nullable=False
    )
    first_response_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    assigned_agent = relationship("Agent", back_populates="tickets")
    customer = relationship("Customer", back_populates="tickets")
    
    def __repr__(self) -> str:
        return f"<Ticket(id={self.id}, category={self.category}, status={self.status})>"
    
    @property
    def is_high_priority(self) -> bool:
        """Check if ticket is high priority."""
        return self.priority >= 4
    
    @property
    def is_overdue(self) -> bool:
        """Check if ticket is overdue based on SLA."""
        if self.sla_due_at is None:
            return False
        return datetime.utcnow() > self.sla_due_at
    
    @property
    def response_time_seconds(self) -> Optional[int]:
        """Calculate first response time in seconds."""
        if self.first_response_at is None:
            return None
        delta = self.first_response_at - self.created_at
        return int(delta.total_seconds())
    
    @property
    def resolution_time_seconds(self) -> Optional[int]:
        """Calculate resolution time in seconds."""
        if self.resolved_at is None:
            return None
        delta = self.resolved_at - self.created_at
        return int(delta.total_seconds())
