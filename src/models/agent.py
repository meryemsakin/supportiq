"""
Agent Model

Represents support agents who handle tickets.
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum

from sqlalchemy import (
    Column, String, Integer, Float, DateTime,
    Boolean, JSON, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from src.database import Base


class AgentStatus(str, Enum):
    """Agent availability status."""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    AWAY = "away"
    ON_BREAK = "on_break"


class AgentRole(str, Enum):
    """Agent role types."""
    AGENT = "agent"
    SENIOR_AGENT = "senior_agent"
    TEAM_LEAD = "team_lead"
    SUPERVISOR = "supervisor"
    ADMIN = "admin"


class Agent(Base):
    """
    Agent model representing a support team member.
    
    Attributes:
        id: Unique agent identifier
        external_id: ID from external system
        email: Agent email address
        name: Full name
        
        # Skills and capabilities
        skills: List of skill categories agent can handle
        languages: Languages the agent speaks
        experience_level: Experience level (1-5)
        
        # Workload management
        current_load: Current number of assigned tickets
        max_load: Maximum tickets agent can handle
        daily_capacity: Total daily ticket capacity
        
        # Availability
        status: Current availability status
        is_active: Whether agent is active in system
        
        # Performance metrics
        avg_resolution_time: Average resolution time (seconds)
        avg_first_response_time: Average first response time
        customer_satisfaction_score: CSAT score (0-5)
        tickets_resolved_today: Number resolved today
        
        # External system reference
        zendesk_user_id: Zendesk user ID
        freshdesk_agent_id: Freshdesk agent ID
    """
    
    __tablename__ = "agents"
    
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
    name = Column(String(255), nullable=False)
    display_name = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    
    # Role and team
    role = Column(
        SQLEnum(AgentRole),
        default=AgentRole.AGENT,
        nullable=False
    )
    team = Column(String(100), nullable=True, index=True)
    department = Column(String(100), nullable=True)
    
    # Skills and capabilities (stored as JSON array for SQLite compatibility)
    skills = Column(JSON, default=list, nullable=False)
    languages = Column(JSON, default=lambda: ["en"], nullable=False)
    experience_level = Column(Integer, default=1)  # 1-5, junior to senior
    
    # Specializations (category expertise)
    specializations = Column(JSON, default=dict)  # {"technical_issue": 0.9, "billing": 0.7}
    
    # Workload
    current_load = Column(Integer, default=0)
    max_load = Column(Integer, default=10)
    daily_capacity = Column(Integer, default=50)
    tickets_handled_today = Column(Integer, default=0)
    
    # Availability
    status = Column(
        SQLEnum(AgentStatus),
        default=AgentStatus.OFFLINE,
        nullable=False,
        index=True
    )
    is_active = Column(Boolean, default=True, index=True)
    last_active_at = Column(DateTime(timezone=True), nullable=True)
    
    # Working hours (24h format)
    work_hours_start = Column(String(5), default="09:00")  # HH:MM
    work_hours_end = Column(String(5), default="18:00")
    timezone = Column(String(50), default="Europe/Istanbul")
    working_days = Column(JSON, default=lambda: [0, 1, 2, 3, 4])  # Mon-Fri
    
    # Performance metrics (cached, updated periodically)
    avg_resolution_time = Column(Integer, nullable=True)  # seconds
    avg_first_response_time = Column(Integer, nullable=True)  # seconds
    customer_satisfaction_score = Column(Float, nullable=True)  # 0-5
    quality_score = Column(Float, nullable=True)  # 0-100
    
    # Statistics
    total_tickets_resolved = Column(Integer, default=0)
    tickets_resolved_today = Column(Integer, default=0)
    tickets_escalated = Column(Integer, default=0)
    
    # Priority handling
    can_handle_critical = Column(Boolean, default=False)
    can_handle_vip = Column(Boolean, default=False)
    
    # External system IDs
    zendesk_user_id = Column(String(255), nullable=True)
    freshdesk_agent_id = Column(String(255), nullable=True)
    
    # Notifications
    notification_email = Column(Boolean, default=True)
    notification_slack = Column(Boolean, default=False)
    slack_user_id = Column(String(100), nullable=True)
    
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
    tickets = relationship("Ticket", back_populates="assigned_agent")
    
    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, name={self.name}, status={self.status})>"
    
    @property
    def is_available(self) -> bool:
        """Check if agent is available to receive tickets."""
        return (
            self.is_active and
            self.status == AgentStatus.ONLINE and
            self.current_load < self.max_load
        )
    
    @property
    def load_percentage(self) -> float:
        """Calculate current load as percentage of max capacity."""
        if self.max_load == 0:
            return 100.0
        return (self.current_load / self.max_load) * 100
    
    @property
    def available_capacity(self) -> int:
        """Calculate remaining capacity."""
        return max(0, self.max_load - self.current_load)
    
    def can_handle_category(self, category: str) -> bool:
        """Check if agent has skill for category."""
        return category in self.skills
    
    def can_handle_language(self, language: str) -> bool:
        """Check if agent speaks the language."""
        return language in self.languages
    
    def get_skill_score(self, category: str) -> float:
        """Get agent's expertise score for a category."""
        return self.specializations.get(category, 0.5)
