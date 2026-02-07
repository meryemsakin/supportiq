"""
Agent API Endpoints

CRUD operations and management for support agents.
"""

from typing import Optional, List
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from loguru import logger

from src.database import get_async_db
from src.models.agent import Agent, AgentStatus, AgentRole
from src.schemas.agent import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentFilterParams,
    AgentStatusUpdate,
    AgentPerformanceStats,
)
from src.schemas.common import PaginatedResponse

router = APIRouter()


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    db: AsyncSession = Depends(get_async_db)
) -> AgentResponse:
    """Create a new agent."""
    
    # Check if email already exists
    result = await db.execute(
        select(Agent).where(Agent.email == agent_data.email)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent with email {agent_data.email} already exists"
        )
    
    # Create agent
    agent = Agent(
        email=agent_data.email,
        name=agent_data.name,
        display_name=agent_data.display_name,
        role=AgentRole(agent_data.role) if agent_data.role else AgentRole.AGENT,
        team=agent_data.team,
        department=agent_data.department,
        skills=agent_data.skills,
        languages=agent_data.languages,
        experience_level=agent_data.experience_level,
        max_load=agent_data.max_load,
        daily_capacity=agent_data.daily_capacity,
        work_hours_start=agent_data.work_hours_start,
        work_hours_end=agent_data.work_hours_end,
        timezone=agent_data.timezone,
        working_days=agent_data.working_days,
        can_handle_critical=agent_data.can_handle_critical,
        can_handle_vip=agent_data.can_handle_vip,
        external_id=agent_data.external_id,
        zendesk_user_id=agent_data.zendesk_user_id,
        freshdesk_agent_id=agent_data.freshdesk_agent_id,
        status=AgentStatus.OFFLINE,
        is_active=True
    )
    
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    
    logger.info(f"Created agent: {agent.name} ({agent.email})")
    
    return AgentResponse.model_validate(agent)


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_async_db)
) -> AgentResponse:
    """Get agent by ID."""
    
    agent = await db.get(Agent, agent_id)
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
    
    return AgentResponse.model_validate(agent)


@router.get("", response_model=PaginatedResponse[AgentResponse])
async def list_agents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    is_available: Optional[bool] = Query(None),
    skill: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    can_handle_critical: Optional[bool] = Query(None),
    can_handle_vip: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("name"),
    sort_order: str = Query("asc"),
    db: AsyncSession = Depends(get_async_db)
) -> PaginatedResponse[AgentResponse]:
    """List agents with filtering and pagination."""
    
    query = select(Agent)
    count_query = select(func.count(Agent.id))
    
    filters = []
    
    if status:
        filters.append(Agent.status == status)
    if team:
        filters.append(Agent.team == team)
    if role:
        filters.append(Agent.role == role)
    if is_active is not None:
        filters.append(Agent.is_active == is_active)
    if is_available:
        filters.append(and_(
            Agent.is_active == True,
            Agent.status == AgentStatus.ONLINE,
            Agent.current_load < Agent.max_load
        ))
    if skill:
        filters.append(Agent.skills.contains([skill]))
    if language:
        filters.append(Agent.languages.contains([language]))
    if can_handle_critical is not None:
        filters.append(Agent.can_handle_critical == can_handle_critical)
    if can_handle_vip is not None:
        filters.append(Agent.can_handle_vip == can_handle_vip)
    if search:
        filters.append(or_(
            Agent.name.ilike(f"%{search}%"),
            Agent.email.ilike(f"%{search}%")
        ))
    
    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply sorting
    sort_column = getattr(Agent, sort_by, Agent.name)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    agents = result.scalars().all()
    
    return PaginatedResponse.create(
        items=[AgentResponse.model_validate(a) for a in agents],
        total=total,
        page=page,
        page_size=page_size
    )


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    agent_data: AgentUpdate,
    db: AsyncSession = Depends(get_async_db)
) -> AgentResponse:
    """Update agent fields."""
    
    agent = await db.get(Agent, agent_id)
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
    
    update_data = agent_data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        if field == "role" and value:
            value = AgentRole(value)
        elif field == "status" and value:
            value = AgentStatus(value)
        setattr(agent, field, value)
    
    agent.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(agent)
    
    logger.info(f"Updated agent: {agent.name}")
    
    return AgentResponse.model_validate(agent)


@router.put("/{agent_id}/status", response_model=AgentResponse)
async def update_agent_status(
    agent_id: UUID,
    status_data: AgentStatusUpdate,
    db: AsyncSession = Depends(get_async_db)
) -> AgentResponse:
    """Update agent availability status."""
    
    agent = await db.get(Agent, agent_id)
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
    
    try:
        agent.status = AgentStatus(status_data.status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {status_data.status}"
        )
    
    if agent.status == AgentStatus.ONLINE:
        agent.last_active_at = datetime.utcnow()
    
    agent.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(agent)
    
    logger.info(f"Agent {agent.name} status changed to {agent.status}")
    
    return AgentResponse.model_validate(agent)


@router.get("/{agent_id}/stats", response_model=AgentPerformanceStats)
async def get_agent_stats(
    agent_id: UUID,
    period_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_async_db)
) -> AgentPerformanceStats:
    """Get agent performance statistics."""
    
    from src.models.ticket import Ticket, TicketStatus
    from datetime import timedelta
    
    agent = await db.get(Agent, agent_id)
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
    
    period_start = datetime.utcnow() - timedelta(days=period_days)
    period_end = datetime.utcnow()
    
    # Get ticket counts
    tickets_query = select(
        func.count(Ticket.id).label("total"),
        func.count(Ticket.id).filter(Ticket.status == TicketStatus.RESOLVED).label("resolved"),
        func.count(Ticket.id).filter(Ticket.escalated == True).label("escalated"),
        func.avg(
            func.extract('epoch', Ticket.resolved_at - Ticket.created_at)
        ).filter(Ticket.resolved_at.isnot(None)).label("avg_resolution_time"),
        func.avg(
            func.extract('epoch', Ticket.first_response_at - Ticket.created_at)
        ).filter(Ticket.first_response_at.isnot(None)).label("avg_first_response_time")
    ).where(
        and_(
            Ticket.assigned_agent_id == agent_id,
            Ticket.created_at >= period_start
        )
    )
    
    result = await db.execute(tickets_query)
    stats = result.one()
    
    return AgentPerformanceStats(
        agent_id=agent.id,
        agent_name=agent.name,
        tickets_assigned=stats.total or 0,
        tickets_resolved=stats.resolved or 0,
        tickets_escalated=stats.escalated or 0,
        tickets_reopened=0,  # TODO: Track reopened tickets
        avg_first_response_time=int(stats.avg_first_response_time) if stats.avg_first_response_time else None,
        avg_resolution_time=int(stats.avg_resolution_time) if stats.avg_resolution_time else None,
        customer_satisfaction_score=agent.customer_satisfaction_score,
        quality_score=agent.quality_score,
        period_start=period_start,
        period_end=period_end
    )


@router.get("/available", response_model=List[AgentResponse])
async def get_available_agents(
    category: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    priority: int = Query(3, ge=1, le=5),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_async_db)
) -> List[AgentResponse]:
    """Get list of available agents for ticket assignment."""
    
    query = select(Agent).where(
        and_(
            Agent.is_active == True,
            Agent.status == AgentStatus.ONLINE,
            Agent.current_load < Agent.max_load
        )
    )
    
    if priority >= 4:
        query = query.order_by(Agent.experience_level.desc(), Agent.current_load.asc())
    else:
        query = query.order_by(Agent.current_load.asc())
    
    query = query.limit(limit)
    
    result = await db.execute(query)
    agents = result.scalars().all()
    
    # Filter by skill/language in Python for array columns
    filtered_agents = []
    for agent in agents:
        if category and agent.skills and category not in agent.skills:
            continue
        if language and agent.languages and language not in agent.languages:
            continue
        filtered_agents.append(agent)
    
    return [AgentResponse.model_validate(a) for a in filtered_agents[:limit]]


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_async_db)
):
    """Delete an agent (soft delete - sets is_active to False)."""
    
    agent = await db.get(Agent, agent_id)
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
    
    # Soft delete
    agent.is_active = False
    agent.status = AgentStatus.OFFLINE
    agent.updated_at = datetime.utcnow()
    
    await db.commit()
    
    logger.info(f"Agent {agent.name} deactivated")
