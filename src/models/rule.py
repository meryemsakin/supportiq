"""
Routing Rule Model

Defines rules for ticket routing logic.
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum

from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime,
    Boolean, JSON, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID
import uuid

from src.database import Base


class RuleType(str, Enum):
    """Types of routing rules."""
    CATEGORY = "category"  # Route based on category
    KEYWORD = "keyword"  # Route based on keywords
    SENTIMENT = "sentiment"  # Route based on sentiment
    PRIORITY = "priority"  # Route based on priority
    CUSTOMER = "customer"  # Route based on customer attributes
    TIME = "time"  # Route based on time/schedule
    LANGUAGE = "language"  # Route based on language
    CUSTOM = "custom"  # Custom rule with expression


class RuleAction(str, Enum):
    """Actions a rule can take."""
    ASSIGN_AGENT = "assign_agent"
    ASSIGN_TEAM = "assign_team"
    SET_PRIORITY = "set_priority"
    ADD_TAG = "add_tag"
    ESCALATE = "escalate"
    AUTO_REPLY = "auto_reply"
    NOTIFY = "notify"
    SKIP_QUEUE = "skip_queue"


class RoutingRule(Base):
    """
    Routing rule model for ticket assignment logic.
    
    Rules are evaluated in priority order. First matching rule wins
    unless marked as non-exclusive.
    
    Attributes:
        id: Unique rule identifier
        name: Human-readable rule name
        description: Rule description
        
        # Conditions
        rule_type: Type of rule
        conditions: JSON conditions to match
        
        # Actions
        action: What to do when rule matches
        action_params: Parameters for the action
        
        # Control
        priority: Rule evaluation order (higher = first)
        is_active: Whether rule is active
        is_exclusive: Whether to stop after this rule matches
    """
    
    __tablename__ = "routing_rules"
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    
    # Basic info
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Rule type and conditions
    rule_type = Column(
        SQLEnum(RuleType),
        nullable=False,
        index=True
    )
    
    # Conditions (JSON structure depends on rule_type)
    # Examples:
    # - category: {"categories": ["technical_issue", "bug_report"]}
    # - keyword: {"keywords": ["urgent", "asap"], "match_mode": "any"}
    # - sentiment: {"sentiments": ["negative", "angry"]}
    # - priority: {"min_priority": 4}
    # - customer: {"tiers": ["vip", "enterprise"]}
    # - time: {"hours": {"start": "09:00", "end": "17:00"}, "days": [0,1,2,3,4]}
    # - language: {"languages": ["tr"]}
    conditions = Column(JSON, nullable=False, default=dict)
    
    # Action to take
    action = Column(
        SQLEnum(RuleAction),
        nullable=False
    )
    
    # Action parameters (JSON structure depends on action)
    # Examples:
    # - assign_agent: {"agent_id": "uuid"}
    # - assign_team: {"team": "technical_support"}
    # - set_priority: {"priority": 5}
    # - add_tag: {"tags": ["urgent", "vip"]}
    # - escalate: {"reason": "VIP customer", "to_team": "senior"}
    # - auto_reply: {"template_id": "uuid"}
    # - notify: {"channels": ["email", "slack"], "recipients": ["manager@example.com"]}
    action_params = Column(JSON, nullable=False, default=dict)
    
    # Control
    priority = Column(Integer, default=0, index=True)  # Higher = evaluated first
    is_active = Column(Boolean, default=True, index=True)
    is_exclusive = Column(Boolean, default=True)  # Stop after match?
    
    # Scope (stored as JSON for SQLite compatibility)
    applies_to_sources = Column(JSON, nullable=True)  # ["zendesk", "email"]
    applies_to_categories = Column(JSON, nullable=True)
    
    # Time restrictions
    active_from = Column(DateTime(timezone=True), nullable=True)
    active_until = Column(DateTime(timezone=True), nullable=True)
    active_hours_start = Column(String(5), nullable=True)  # HH:MM
    active_hours_end = Column(String(5), nullable=True)
    active_days = Column(JSON, nullable=True)  # 0=Mon, 6=Sun
    
    # Statistics
    times_triggered = Column(Integer, default=0)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    
    # Extra data
    created_by = Column(String(255), nullable=True)
    extra_data = Column(JSON, default=dict)
    
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
    
    def __repr__(self) -> str:
        return f"<RoutingRule(name={self.name}, type={self.rule_type}, action={self.action})>"
    
    def matches(self, ticket_data: dict) -> bool:
        """
        Check if rule matches the given ticket data.
        
        Args:
            ticket_data: Dictionary with ticket attributes
            
        Returns:
            bool: True if rule conditions match
        """
        if not self.is_active:
            return False
        
        # Check time restrictions
        if not self._check_time_restrictions():
            return False
        
        # Check source restriction
        if self.applies_to_sources:
            source = ticket_data.get("source")
            if source and source not in self.applies_to_sources:
                return False
        
        # Check category restriction
        if self.applies_to_categories:
            category = ticket_data.get("category")
            if category and category not in self.applies_to_categories:
                return False
        
        # Check specific conditions based on rule type
        return self._evaluate_conditions(ticket_data)
    
    def _check_time_restrictions(self) -> bool:
        """Check if rule is active based on time restrictions."""
        now = datetime.utcnow()
        
        # Check date range
        if self.active_from and now < self.active_from:
            return False
        if self.active_until and now > self.active_until:
            return False
        
        # Check day of week (0=Monday)
        if self.active_days is not None:
            if now.weekday() not in self.active_days:
                return False
        
        # Check time of day
        if self.active_hours_start and self.active_hours_end:
            current_time = now.strftime("%H:%M")
            if not (self.active_hours_start <= current_time <= self.active_hours_end):
                return False
        
        return True
    
    def _evaluate_conditions(self, ticket_data: dict) -> bool:
        """Evaluate rule conditions against ticket data."""
        conditions = self.conditions
        
        if self.rule_type == RuleType.CATEGORY:
            categories = conditions.get("categories", [])
            return ticket_data.get("category") in categories
        
        elif self.rule_type == RuleType.KEYWORD:
            keywords = conditions.get("keywords", [])
            match_mode = conditions.get("match_mode", "any")
            content = (ticket_data.get("content", "") + " " + ticket_data.get("subject", "")).lower()
            
            if match_mode == "any":
                return any(kw.lower() in content for kw in keywords)
            else:  # all
                return all(kw.lower() in content for kw in keywords)
        
        elif self.rule_type == RuleType.SENTIMENT:
            sentiments = conditions.get("sentiments", [])
            return ticket_data.get("sentiment") in sentiments
        
        elif self.rule_type == RuleType.PRIORITY:
            min_priority = conditions.get("min_priority", 1)
            max_priority = conditions.get("max_priority", 5)
            ticket_priority = ticket_data.get("priority", 3)
            return min_priority <= ticket_priority <= max_priority
        
        elif self.rule_type == RuleType.CUSTOMER:
            tiers = conditions.get("tiers", [])
            return ticket_data.get("customer_tier") in tiers
        
        elif self.rule_type == RuleType.LANGUAGE:
            languages = conditions.get("languages", [])
            return ticket_data.get("language") in languages
        
        elif self.rule_type == RuleType.CUSTOM:
            # Custom rules use a simple expression evaluator
            # This is a simplified implementation
            expression = conditions.get("expression", "")
            # TODO: Implement safe expression evaluation
            return False
        
        return False


# Default routing rules to seed
DEFAULT_ROUTING_RULES = [
    {
        "name": "VIP Customer Priority",
        "description": "Escalate VIP and Enterprise customer tickets",
        "rule_type": RuleType.CUSTOMER,
        "conditions": {"tiers": ["vip", "enterprise"]},
        "action": RuleAction.SKIP_QUEUE,
        "action_params": {"priority_boost": 2},
        "priority": 100,
    },
    {
        "name": "Angry Customer Escalation",
        "description": "Escalate tickets from angry customers to senior agents",
        "rule_type": RuleType.SENTIMENT,
        "conditions": {"sentiments": ["angry"]},
        "action": RuleAction.ESCALATE,
        "action_params": {"to_team": "senior_support", "reason": "angry_customer"},
        "priority": 90,
    },
    {
        "name": "Critical Priority Alert",
        "description": "Notify management for critical priority tickets",
        "rule_type": RuleType.PRIORITY,
        "conditions": {"min_priority": 5},
        "action": RuleAction.NOTIFY,
        "action_params": {"channels": ["email"], "template": "critical_alert"},
        "priority": 80,
        "is_exclusive": False,
    },
    {
        "name": "Technical Issues to Tech Team",
        "description": "Route technical issues to technical support team",
        "rule_type": RuleType.CATEGORY,
        "conditions": {"categories": ["technical_issue", "bug_report"]},
        "action": RuleAction.ASSIGN_TEAM,
        "action_params": {"team": "technical_support"},
        "priority": 50,
    },
    {
        "name": "Billing to Finance Team",
        "description": "Route billing questions to finance team",
        "rule_type": RuleType.CATEGORY,
        "conditions": {"categories": ["billing_question", "return_refund"]},
        "action": RuleAction.ASSIGN_TEAM,
        "action_params": {"team": "finance"},
        "priority": 50,
    },
]
