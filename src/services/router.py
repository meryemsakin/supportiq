"""
Ticket Routing Service

Intelligently routes tickets to the most appropriate agents
based on skills, availability, workload, and routing rules.
"""

from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime, time
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from loguru import logger

from src.models.agent import Agent, AgentStatus
from src.models.rule import RoutingRule, RuleAction


class RoutingReason(str, Enum):
    """Reasons for routing decisions."""
    SKILL_MATCH = "skill_match"
    LANGUAGE_MATCH = "language_match"
    VIP_HANDLER = "vip_handler"
    CRITICAL_HANDLER = "critical_handler"
    LOAD_BALANCE = "load_balance"
    ROUND_ROBIN = "round_robin"
    RULE_BASED = "rule_based"
    ESCALATION = "escalation"
    NO_AGENTS = "no_available_agents"


@dataclass
class RoutingCandidate:
    """Represents a potential agent for routing."""
    agent: Agent
    score: float
    reasons: List[str]


class TicketRouter:
    """
    Routes tickets to appropriate agents using multiple strategies.
    
    Routing strategies:
    1. Rule-based routing (custom rules)
    2. Skill matching (category expertise)
    3. Language matching
    4. VIP/Critical handling
    5. Load balancing
    6. Round-robin fallback
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize router with database session.
        
        Args:
            db: Async database session
        """
        self.db = db
        logger.info("TicketRouter initialized")
    
    async def _get_available_agents(
        self,
        category: Optional[str] = None,
        language: Optional[str] = None,
        priority: int = 3,
        require_vip_handler: bool = False,
        require_critical_handler: bool = False
    ) -> List[Agent]:
        """Get list of available agents matching criteria."""
        
        # Base query: active and online agents with capacity
        query = select(Agent).where(
            and_(
                Agent.is_active == True,
                Agent.status == AgentStatus.ONLINE,
                Agent.current_load < Agent.max_load
            )
        )
        
        # VIP handler requirement
        if require_vip_handler:
            query = query.where(Agent.can_handle_vip == True)
        
        # Critical handler requirement  
        if require_critical_handler:
            query = query.where(Agent.can_handle_critical == True)
        
        result = await self.db.execute(query)
        agents = result.scalars().all()
        
        return list(agents)
    
    async def _get_routing_rules(
        self,
        category: Optional[str] = None,
        source: Optional[str] = None
    ) -> List[RoutingRule]:
        """Get applicable routing rules."""
        
        query = select(RoutingRule).where(
            RoutingRule.is_active == True
        ).order_by(RoutingRule.priority.desc())
        
        result = await self.db.execute(query)
        rules = result.scalars().all()
        
        return list(rules)
    
    def _calculate_agent_score(
        self,
        agent: Agent,
        category: Optional[str] = None,
        language: str = "tr",
        priority: int = 3,
        customer_tier: str = "standard"
    ) -> RoutingCandidate:
        """
        Calculate routing score for an agent.
        
        Higher score = better match.
        """
        
        score = 50.0  # Base score
        reasons = []
        
        # Skill match (highest weight)
        if category and agent.skills:
            if category in agent.skills:
                score += 30
                reasons.append(f"skill_match:{category}")
                
                # Check specialization level
                if agent.specializations:
                    expertise = agent.specializations.get(category, 0.5)
                    score += expertise * 10
                    reasons.append(f"expertise:{expertise:.2f}")
        
        # Language match
        if language and agent.languages:
            if language in agent.languages:
                score += 15
                reasons.append(f"language_match:{language}")
        
        # Experience level for high priority
        if priority >= 4:
            score += agent.experience_level * 5
            reasons.append(f"experience:{agent.experience_level}")
        
        # VIP handling capability
        if customer_tier in ["vip", "enterprise"]:
            if agent.can_handle_vip:
                score += 20
                reasons.append("vip_handler")
        
        # Critical handling for critical priority
        if priority == 5:
            if agent.can_handle_critical:
                score += 20
                reasons.append("critical_handler")
        
        # Load balancing (prefer lower load)
        if agent.max_load > 0:
            load_ratio = agent.current_load / agent.max_load
            score -= load_ratio * 20  # Penalize high load
            reasons.append(f"load_ratio:{load_ratio:.2f}")
        
        # Performance bonus
        if agent.customer_satisfaction_score:
            score += (agent.customer_satisfaction_score - 3) * 5
        
        # Quality score bonus
        if agent.quality_score:
            score += (agent.quality_score / 100) * 10
        
        return RoutingCandidate(
            agent=agent,
            score=score,
            reasons=reasons
        )
    
    async def _apply_routing_rules(
        self,
        ticket_data: Dict[str, Any],
        agents: List[Agent]
    ) -> Optional[Dict[str, Any]]:
        """Apply routing rules to find matching rule."""
        
        rules = await self._get_routing_rules(
            category=ticket_data.get("category"),
            source=ticket_data.get("source")
        )
        
        for rule in rules:
            if rule.matches(ticket_data):
                logger.info(f"Rule matched: {rule.name}")
                
                if rule.action == RuleAction.ASSIGN_AGENT:
                    agent_id = rule.action_params.get("agent_id")
                    agent = next(
                        (a for a in agents if str(a.id) == agent_id),
                        None
                    )
                    if agent:
                        return {
                            "agent_id": agent.id,
                            "agent_name": agent.name,
                            "team": agent.team,
                            "reason": RoutingReason.RULE_BASED.value,
                            "confidence": 1.0,
                            "rule_name": rule.name
                        }
                
                elif rule.action == RuleAction.ASSIGN_TEAM:
                    team = rule.action_params.get("team")
                    team_agents = [a for a in agents if a.team == team]
                    if team_agents:
                        # Pick best from team
                        best = min(team_agents, key=lambda a: a.current_load)
                        return {
                            "agent_id": best.id,
                            "agent_name": best.name,
                            "team": best.team,
                            "reason": RoutingReason.RULE_BASED.value,
                            "confidence": 0.9,
                            "rule_name": rule.name
                        }
                
                elif rule.action == RuleAction.ESCALATE:
                    return {
                        "agent_id": None,
                        "agent_name": None,
                        "team": rule.action_params.get("to_team"),
                        "reason": RoutingReason.ESCALATION.value,
                        "confidence": 1.0,
                        "escalation_reason": rule.action_params.get("reason"),
                        "rule_name": rule.name
                    }
        
        return None
    
    def _is_within_working_hours(self, agent: Agent) -> bool:
        """Check if agent is within working hours."""
        
        now = datetime.utcnow()
        
        # Check day of week
        if agent.working_days and now.weekday() not in agent.working_days:
            return False
        
        # Check time
        try:
            current_time = now.strftime("%H:%M")
            if agent.work_hours_start and agent.work_hours_end:
                return agent.work_hours_start <= current_time <= agent.work_hours_end
        except:
            pass
        
        return True
    
    async def route(
        self,
        category: Optional[str] = None,
        priority: int = 3,
        language: str = "tr",
        customer_tier: str = "standard",
        customer_id: Optional[UUID] = None,
        source: Optional[str] = None,
        content: Optional[str] = None,
        sentiment: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Route ticket to the best available agent.
        
        Args:
            category: Ticket category
            priority: Priority score (1-5)
            language: Ticket language
            customer_tier: Customer tier
            customer_id: Customer UUID (for relationship tracking)
            source: Ticket source
            content: Ticket content (for rule matching)
            sentiment: Detected sentiment
            metadata: Additional routing context
            
        Returns:
            Routing decision:
            {
                "agent_id": UUID or None,
                "agent_name": str or None,
                "team": str or None,
                "reason": str,
                "confidence": float,
                "alternatives": List[Dict]
            }
        """
        
        metadata = metadata or {}
        
        # Build ticket data for rule matching
        ticket_data = {
            "category": category,
            "priority": priority,
            "language": language,
            "customer_tier": customer_tier,
            "source": source,
            "content": content or "",
            "sentiment": sentiment,
            "subject": metadata.get("subject", ""),
            **metadata
        }
        
        # Determine requirements
        require_vip = customer_tier in ["vip", "enterprise"]
        require_critical = priority == 5
        
        # Get available agents
        agents = await self._get_available_agents(
            category=category,
            language=language,
            priority=priority,
            require_vip_handler=require_vip,
            require_critical_handler=require_critical
        )
        
        if not agents:
            # Try without VIP/critical requirements
            agents = await self._get_available_agents(
                category=category,
                language=language,
                priority=priority
            )
        
        if not agents:
            logger.warning("No available agents for routing")
            return {
                "agent_id": None,
                "agent_name": None,
                "team": None,
                "reason": RoutingReason.NO_AGENTS.value,
                "confidence": 0.0,
                "alternatives": [],
                "message": "No agents currently available"
            }
        
        # Filter by working hours
        agents = [a for a in agents if self._is_within_working_hours(a)]
        
        if not agents:
            # Fall back to any online agent
            all_agents = await self._get_available_agents()
            agents = all_agents
        
        if not agents:
            return {
                "agent_id": None,
                "agent_name": None,
                "team": None,
                "reason": RoutingReason.NO_AGENTS.value,
                "confidence": 0.0,
                "alternatives": []
            }
        
        # Try rule-based routing first
        rule_result = await self._apply_routing_rules(ticket_data, agents)
        if rule_result:
            return rule_result
        
        # Calculate scores for all agents
        candidates = [
            self._calculate_agent_score(
                agent=a,
                category=category,
                language=language,
                priority=priority,
                customer_tier=customer_tier
            )
            for a in agents
        ]
        
        # Sort by score (descending)
        candidates.sort(key=lambda c: c.score, reverse=True)
        
        # Select best candidate
        best = candidates[0]
        
        # Determine primary reason
        if "skill_match" in str(best.reasons):
            reason = RoutingReason.SKILL_MATCH
        elif "vip_handler" in best.reasons:
            reason = RoutingReason.VIP_HANDLER
        elif "critical_handler" in best.reasons:
            reason = RoutingReason.CRITICAL_HANDLER
        elif "language_match" in str(best.reasons):
            reason = RoutingReason.LANGUAGE_MATCH
        else:
            reason = RoutingReason.LOAD_BALANCE
        
        # Calculate confidence based on score distribution
        if len(candidates) > 1:
            score_diff = best.score - candidates[1].score
            confidence = min(0.5 + (score_diff / 100), 0.99)
        else:
            confidence = 0.95
        
        # Build alternatives list
        alternatives = [
            {
                "agent_id": c.agent.id,
                "agent_name": c.agent.name,
                "score": c.score,
                "reasons": c.reasons
            }
            for c in candidates[1:4]  # Top 3 alternatives
        ]
        
        result = {
            "agent_id": best.agent.id,
            "agent_name": best.agent.name,
            "team": best.agent.team,
            "reason": reason.value,
            "confidence": round(confidence, 3),
            "score": round(best.score, 2),
            "score_breakdown": best.reasons,
            "alternatives": alternatives
        }
        
        logger.info(
            f"Routed to agent '{best.agent.name}' "
            f"(score: {best.score:.1f}, reason: {reason.value})"
        )
        
        return result
    
    async def reassign(
        self,
        ticket_id: UUID,
        current_agent_id: Optional[UUID],
        exclude_agents: Optional[List[UUID]] = None,
        reason: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Reassign ticket to a different agent.
        
        Args:
            ticket_id: Ticket to reassign
            current_agent_id: Current agent (to exclude)
            exclude_agents: Additional agents to exclude
            reason: Reason for reassignment
            **kwargs: Routing parameters
            
        Returns:
            New routing decision
        """
        
        exclude = set(exclude_agents or [])
        if current_agent_id:
            exclude.add(current_agent_id)
        
        # Get routing with exclusions
        result = await self.route(**kwargs)
        
        # If best agent is excluded, try alternatives
        if result.get("agent_id") in exclude:
            alternatives = result.get("alternatives", [])
            for alt in alternatives:
                if alt["agent_id"] not in exclude:
                    result.update({
                        "agent_id": alt["agent_id"],
                        "agent_name": alt["agent_name"],
                        "reason": "reassignment",
                        "previous_agent_id": current_agent_id,
                        "reassignment_reason": reason
                    })
                    break
        
        return result
    
    async def get_agent_recommendations(
        self,
        category: str,
        priority: int = 3,
        language: str = "tr",
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get ranked list of recommended agents for a ticket type.
        
        Useful for manual assignment UI.
        """
        
        agents = await self._get_available_agents(
            category=category,
            language=language,
            priority=priority
        )
        
        candidates = [
            self._calculate_agent_score(
                agent=a,
                category=category,
                language=language,
                priority=priority
            )
            for a in agents
        ]
        
        candidates.sort(key=lambda c: c.score, reverse=True)
        
        return [
            {
                "agent_id": c.agent.id,
                "agent_name": c.agent.name,
                "team": c.agent.team,
                "score": round(c.score, 2),
                "current_load": c.agent.current_load,
                "max_load": c.agent.max_load,
                "skills": c.agent.skills,
                "reasons": c.reasons
            }
            for c in candidates[:limit]
        ]
