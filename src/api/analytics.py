"""
Analytics API Endpoints

Provides analytics and reporting for tickets and agents.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case
from loguru import logger

from src.database import get_async_db
from src.models.ticket import Ticket, TicketStatus
from src.models.agent import Agent
from src.models.category import Category

router = APIRouter()


@router.get("/overview")
async def get_overview(
    period_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """
    Get overview analytics for the dashboard.
    
    Returns:
    - Total tickets
    - Open tickets
    - Resolved tickets
    - Average resolution time
    - Category distribution
    - Priority distribution
    """
    
    period_start = datetime.utcnow() - timedelta(days=period_days)
    
    # Basic counts
    counts_query = select(
        func.count(Ticket.id).label("total"),
        func.count(Ticket.id).filter(
            Ticket.status.in_([TicketStatus.NEW, TicketStatus.OPEN, TicketStatus.IN_PROGRESS])
        ).label("open"),
        func.count(Ticket.id).filter(
            Ticket.status == TicketStatus.RESOLVED
        ).label("resolved"),
        func.count(Ticket.id).filter(
            Ticket.escalated == True
        ).label("escalated"),
        func.avg(
            func.extract('epoch', Ticket.resolved_at - Ticket.created_at) / 3600
        ).filter(Ticket.resolved_at.isnot(None)).label("avg_resolution_hours")
    ).where(Ticket.created_at >= period_start)
    
    result = await db.execute(counts_query)
    counts = result.one()
    
    # Category distribution
    category_query = select(
        Ticket.category,
        func.count(Ticket.id).label("count")
    ).where(
        and_(
            Ticket.created_at >= period_start,
            Ticket.category.isnot(None)
        )
    ).group_by(Ticket.category)
    
    cat_result = await db.execute(category_query)
    categories = {row.category: row.count for row in cat_result}
    
    # Priority distribution
    priority_query = select(
        Ticket.priority,
        func.count(Ticket.id).label("count")
    ).where(Ticket.created_at >= period_start).group_by(Ticket.priority)
    
    pri_result = await db.execute(priority_query)
    priorities = {str(row.priority): row.count for row in pri_result}
    
    # Sentiment distribution
    sentiment_query = select(
        Ticket.sentiment,
        func.count(Ticket.id).label("count")
    ).where(
        and_(
            Ticket.created_at >= period_start,
            Ticket.sentiment.isnot(None)
        )
    ).group_by(Ticket.sentiment)
    
    sent_result = await db.execute(sentiment_query)
    sentiments = {row.sentiment: row.count for row in sent_result}
    
    return {
        "period_days": period_days,
        "period_start": period_start.isoformat(),
        "period_end": datetime.utcnow().isoformat(),
        "summary": {
            "total_tickets": counts.total or 0,
            "open_tickets": counts.open or 0,
            "resolved_tickets": counts.resolved or 0,
            "escalated_tickets": counts.escalated or 0,
            "resolution_rate": round((counts.resolved / counts.total * 100) if counts.total else 0, 1),
            "avg_resolution_hours": round(counts.avg_resolution_hours or 0, 1)
        },
        "by_category": categories,
        "by_priority": priorities,
        "by_sentiment": sentiments
    }


@router.get("/categories")
async def get_category_analytics(
    period_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """Get detailed analytics by category."""
    
    period_start = datetime.utcnow() - timedelta(days=period_days)
    
    query = select(
        Ticket.category,
        func.count(Ticket.id).label("total"),
        func.count(Ticket.id).filter(
            Ticket.status == TicketStatus.RESOLVED
        ).label("resolved"),
        func.avg(Ticket.priority).label("avg_priority"),
        func.avg(
            func.extract('epoch', Ticket.resolved_at - Ticket.created_at) / 3600
        ).filter(Ticket.resolved_at.isnot(None)).label("avg_resolution_hours")
    ).where(
        and_(
            Ticket.created_at >= period_start,
            Ticket.category.isnot(None)
        )
    ).group_by(Ticket.category)
    
    result = await db.execute(query)
    
    categories = []
    for row in result:
        categories.append({
            "category": row.category,
            "total_tickets": row.total,
            "resolved_tickets": row.resolved,
            "resolution_rate": round((row.resolved / row.total * 100) if row.total else 0, 1),
            "avg_priority": round(row.avg_priority or 0, 2),
            "avg_resolution_hours": round(row.avg_resolution_hours or 0, 1)
        })
    
    # Sort by total tickets descending
    categories.sort(key=lambda x: x["total_tickets"], reverse=True)
    
    return {
        "period_days": period_days,
        "categories": categories
    }


@router.get("/performance")
async def get_agent_performance(
    period_days: int = Query(30, ge=1, le=365),
    team: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """Get agent performance analytics."""
    
    period_start = datetime.utcnow() - timedelta(days=period_days)
    
    # Get agents
    agent_query = select(Agent)
    if team:
        agent_query = agent_query.where(Agent.team == team)
    
    agent_result = await db.execute(agent_query)
    agents = agent_result.scalars().all()
    
    performance = []
    
    for agent in agents:
        # Get ticket stats for agent
        stats_query = select(
            func.count(Ticket.id).label("total"),
            func.count(Ticket.id).filter(
                Ticket.status == TicketStatus.RESOLVED
            ).label("resolved"),
            func.count(Ticket.id).filter(
                Ticket.escalated == True
            ).label("escalated"),
            func.avg(
                func.extract('epoch', Ticket.resolved_at - Ticket.created_at) / 3600
            ).filter(Ticket.resolved_at.isnot(None)).label("avg_resolution_hours"),
            func.avg(
                func.extract('epoch', Ticket.first_response_at - Ticket.created_at) / 60
            ).filter(Ticket.first_response_at.isnot(None)).label("avg_first_response_mins")
        ).where(
            and_(
                Ticket.assigned_agent_id == agent.id,
                Ticket.created_at >= period_start
            )
        )
        
        result = await db.execute(stats_query)
        stats = result.one()
        
        performance.append({
            "agent_id": str(agent.id),
            "agent_name": agent.name,
            "team": agent.team,
            "status": agent.status.value if agent.status else "unknown",
            "current_load": agent.current_load,
            "max_load": agent.max_load,
            "tickets": {
                "assigned": stats.total or 0,
                "resolved": stats.resolved or 0,
                "escalated": stats.escalated or 0,
                "resolution_rate": round((stats.resolved / stats.total * 100) if stats.total else 0, 1)
            },
            "metrics": {
                "avg_resolution_hours": round(stats.avg_resolution_hours or 0, 1),
                "avg_first_response_mins": round(stats.avg_first_response_mins or 0, 1),
                "customer_satisfaction": agent.customer_satisfaction_score,
                "quality_score": agent.quality_score
            }
        })
    
    # Sort by resolution rate descending
    performance.sort(key=lambda x: x["tickets"]["resolution_rate"], reverse=True)
    
    return {
        "period_days": period_days,
        "agents": performance
    }


@router.get("/trends")
async def get_trends(
    period_days: int = Query(30, ge=1, le=365),
    granularity: str = Query("day", regex="^(day|week|month)$"),
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """Get ticket trends over time."""
    
    period_start = datetime.utcnow() - timedelta(days=period_days)
    
    # Determine date truncation
    if granularity == "day":
        date_func = func.date_trunc('day', Ticket.created_at)
    elif granularity == "week":
        date_func = func.date_trunc('week', Ticket.created_at)
    else:
        date_func = func.date_trunc('month', Ticket.created_at)
    
    query = select(
        date_func.label("period"),
        func.count(Ticket.id).label("total"),
        func.count(Ticket.id).filter(
            Ticket.status == TicketStatus.RESOLVED
        ).label("resolved"),
        func.avg(Ticket.priority).label("avg_priority")
    ).where(
        Ticket.created_at >= period_start
    ).group_by(date_func).order_by(date_func)
    
    result = await db.execute(query)
    
    trends = []
    for row in result:
        trends.append({
            "period": row.period.isoformat() if row.period else None,
            "total_tickets": row.total,
            "resolved_tickets": row.resolved,
            "avg_priority": round(row.avg_priority or 0, 2)
        })
    
    return {
        "period_days": period_days,
        "granularity": granularity,
        "data": trends
    }


@router.get("/sla")
async def get_sla_metrics(
    period_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """Get SLA compliance metrics."""
    
    period_start = datetime.utcnow() - timedelta(days=period_days)
    
    query = select(
        func.count(Ticket.id).label("total"),
        func.count(Ticket.id).filter(
            Ticket.sla_breached == True
        ).label("breached"),
        func.count(Ticket.id).filter(
            and_(
                Ticket.first_response_at.isnot(None),
                Ticket.sla_due_at.isnot(None),
                Ticket.first_response_at <= Ticket.sla_due_at
            )
        ).label("response_within_sla"),
        func.count(Ticket.id).filter(
            and_(
                Ticket.resolved_at.isnot(None),
                Ticket.sla_due_at.isnot(None),
                Ticket.resolved_at <= Ticket.sla_due_at
            )
        ).label("resolved_within_sla")
    ).where(Ticket.created_at >= period_start)
    
    result = await db.execute(query)
    stats = result.one()
    
    total = stats.total or 1  # Avoid division by zero
    
    return {
        "period_days": period_days,
        "total_tickets": stats.total or 0,
        "sla_breached": stats.breached or 0,
        "sla_breach_rate": round((stats.breached / total * 100), 1),
        "first_response_compliance": round((stats.response_within_sla / total * 100), 1) if stats.response_within_sla else 0,
        "resolution_compliance": round((stats.resolved_within_sla / total * 100), 1) if stats.resolved_within_sla else 0
    }
