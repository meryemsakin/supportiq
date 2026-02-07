"""
Ticket API Endpoints

CRUD operations and processing for support tickets.
"""

import time
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from loguru import logger

from src.database import get_async_db
from src.models.ticket import Ticket, TicketStatus
from src.models.customer import Customer
from src.models.agent import Agent
from src.schemas.ticket import (
    TicketCreate,
    TicketUpdate,
    TicketResponse,
    TicketProcessResponse,
    TicketFilterParams,
    TicketReassignRequest,
    TicketBulkUpdateRequest,
    TicketBulkUpdateResponse,
)
from src.schemas.common import PaginatedResponse, PaginationParams
from src.services.classifier import get_classifier
from src.services.sentiment import get_sentiment_analyzer
from src.services.priority_scorer import get_priority_scorer
from src.services.router import TicketRouter
from src.services.rag import knowledge_base
from src.utils.text_processing import TextProcessor

router = APIRouter()


async def process_ticket_pipeline(
    ticket: Ticket,
    db: AsyncSession
) -> dict:
    """
    Run the full ticket processing pipeline.
    
    1. Classify category
    2. Analyze sentiment
    3. Calculate priority
    4. Route to agent
    5. Generate suggested responses
    """
    
    start_time = time.time()
    results = {}
    
    try:
        # 1. Classification
        classifier = get_classifier()
        classification = await classifier.classify(
            text=ticket.content,
            language=ticket.language
        )
        
        ticket.category = classification.get("primary_category")
        ticket.category_confidence = classification.get("confidence")
        ticket.classification_reasoning = classification.get("reasoning")
        
        results["classification"] = classification
        
        # 2. Sentiment Analysis
        analyzer = get_sentiment_analyzer()
        sentiment = await analyzer.analyze(
            text=ticket.content,
            language=ticket.language
        )
        
        ticket.sentiment = sentiment.get("sentiment")
        ticket.sentiment_score = sentiment.get("score")
        
        results["sentiment"] = sentiment
        
        # 3. Priority Scoring
        scorer = get_priority_scorer()
        priority = scorer.calculate(
            text=ticket.content,
            sentiment=ticket.sentiment,
            sentiment_score=ticket.sentiment_score,
            anger_level=sentiment.get("anger_level"),
            customer_tier=ticket.customer_tier or "standard",
            category=ticket.category,
            language=ticket.language
        )
        
        ticket.priority = priority.get("score")
        ticket.priority_level = priority.get("level")
        ticket.priority_factors = priority.get("factors")
        
        results["priority"] = priority
        
        # 4. Routing
        router_service = TicketRouter(db)
        routing = await router_service.route(
            category=ticket.category,
            priority=ticket.priority,
            language=ticket.language,
            customer_tier=ticket.customer_tier,
            content=ticket.content,
            sentiment=ticket.sentiment
        )
        
        if routing.get("agent_id"):
            ticket.assigned_agent_id = routing["agent_id"]
            ticket.assignment_reason = routing.get("reason")
            ticket.assignment_confidence = routing.get("confidence")
            
            # Update agent load
            agent = await db.get(Agent, routing["agent_id"])
            if agent:
                agent.current_load += 1
        
        results["routing"] = routing
        
        # 5. Suggested Responses
        try:
            suggestions = await knowledge_base.generate_suggested_responses(
                ticket_content=ticket.content,
                category=ticket.category,
                language=ticket.language,
                limit=3
            )
            ticket.suggested_responses = suggestions
            results["suggested_responses"] = suggestions
        except Exception as e:
            logger.warning(f"Suggested responses failed: {e}")
            results["suggested_responses"] = []
        
        # Mark as processed
        ticket.is_processed = True
        ticket.status = TicketStatus.OPEN
        
        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)
        results["processing_time_ms"] = processing_time
        
        await db.commit()
        
        logger.info(
            f"Ticket {ticket.id} processed: "
            f"category={ticket.category}, "
            f"priority={ticket.priority}, "
            f"agent={ticket.assigned_agent_id}"
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Ticket processing failed: {e}")
        ticket.processing_error = str(e)
        await db.commit()
        raise


@router.post("", response_model=TicketProcessResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    ticket_data: TicketCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db)
) -> TicketProcessResponse:
    """
    Create a new ticket and process it.
    
    - Creates ticket in database
    - Runs AI classification, sentiment analysis, priority scoring
    - Routes to appropriate agent
    - Generates suggested responses
    """
    
    # Find or create customer
    customer = None
    if ticket_data.customer_email:
        result = await db.execute(
            select(Customer).where(Customer.email == ticket_data.customer_email)
        )
        customer = result.scalar_one_or_none()
        
        if not customer:
            customer = Customer(
                email=ticket_data.customer_email,
                name=ticket_data.customer_name,
                tier=ticket_data.customer_tier or "standard"
            )
            db.add(customer)
            await db.flush()
    
    # Create ticket
    ticket = Ticket(
        content=ticket_data.content,
        subject=ticket_data.subject,
        customer_id=customer.id if customer else None,
        customer_email=ticket_data.customer_email,
        customer_name=ticket_data.customer_name,
        customer_tier=ticket_data.customer_tier or "standard",
        external_id=ticket_data.external_id,
        external_system=ticket_data.external_system,
        source=ticket_data.source or "api",
        channel=ticket_data.channel,
        language=ticket_data.language or TextProcessor.detect_language(ticket_data.content)[0],
        tags=ticket_data.tags or [],
        custom_fields=ticket_data.custom_fields or {},
        status=TicketStatus.NEW
    )
    
    db.add(ticket)
    await db.flush()
    
    # Process ticket
    if ticket_data.process_async:
        # Queue for background processing
        background_tasks.add_task(process_ticket_pipeline, ticket, db)
        await db.commit()
        
        return TicketProcessResponse(
            ticket_id=ticket.id,
            status="queued",
            processing_time_ms=None
        )
    else:
        # Process synchronously
        try:
            results = await process_ticket_pipeline(ticket, db)
            
            return TicketProcessResponse(
                ticket_id=ticket.id,
                status="processed",
                classification=results.get("classification"),
                sentiment=results.get("sentiment"),
                priority=results.get("priority"),
                routing=results.get("routing"),
                suggested_responses=results.get("suggested_responses"),
                processing_time_ms=results.get("processing_time_ms")
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ticket processing failed: {str(e)}"
            )


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: UUID,
    db: AsyncSession = Depends(get_async_db)
) -> TicketResponse:
    """Get ticket by ID."""
    
    ticket = await db.get(Ticket, ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found"
        )
    
    return TicketResponse.model_validate(ticket)


@router.get("", response_model=PaginatedResponse[TicketResponse])
async def list_tickets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    priority: Optional[int] = Query(None, ge=1, le=5),
    min_priority: Optional[int] = Query(None, ge=1, le=5),
    sentiment: Optional[str] = Query(None),
    assigned_agent_id: Optional[UUID] = Query(None),
    is_processed: Optional[bool] = Query(None),
    escalated: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    created_after: Optional[datetime] = Query(None),
    created_before: Optional[datetime] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    db: AsyncSession = Depends(get_async_db)
) -> PaginatedResponse[TicketResponse]:
    """
    List tickets with filtering and pagination.
    """
    
    # Build query
    query = select(Ticket)
    count_query = select(func.count(Ticket.id))
    
    # Apply filters
    filters = []
    
    if status:
        filters.append(Ticket.status == status)
    if category:
        filters.append(Ticket.category == category)
    if priority:
        filters.append(Ticket.priority == priority)
    if min_priority:
        filters.append(Ticket.priority >= min_priority)
    if sentiment:
        filters.append(Ticket.sentiment == sentiment)
    if assigned_agent_id:
        filters.append(Ticket.assigned_agent_id == assigned_agent_id)
    if is_processed is not None:
        filters.append(Ticket.is_processed == is_processed)
    if escalated is not None:
        filters.append(Ticket.escalated == escalated)
    if created_after:
        filters.append(Ticket.created_at >= created_after)
    if created_before:
        filters.append(Ticket.created_at <= created_before)
    if search:
        search_filter = or_(
            Ticket.subject.ilike(f"%{search}%"),
            Ticket.content.ilike(f"%{search}%")
        )
        filters.append(search_filter)
    
    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply sorting
    sort_column = getattr(Ticket, sort_by, Ticket.created_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    tickets = result.scalars().all()
    
    return PaginatedResponse.create(
        items=[TicketResponse.model_validate(t) for t in tickets],
        total=total,
        page=page,
        page_size=page_size
    )


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: UUID,
    ticket_data: TicketUpdate,
    db: AsyncSession = Depends(get_async_db)
) -> TicketResponse:
    """Update ticket fields."""
    
    ticket = await db.get(Ticket, ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found"
        )
    
    # Update fields
    update_data = ticket_data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(ticket, field, value)
    
    ticket.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(ticket)
    
    return TicketResponse.model_validate(ticket)


@router.post("/{ticket_id}/reassign", response_model=TicketResponse)
async def reassign_ticket(
    ticket_id: UUID,
    reassign_data: TicketReassignRequest,
    db: AsyncSession = Depends(get_async_db)
) -> TicketResponse:
    """Manually reassign ticket to a different agent."""
    
    ticket = await db.get(Ticket, ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found"
        )
    
    # Store previous agent
    previous_agent_id = ticket.assigned_agent_id
    
    # Update agent load if previously assigned
    if previous_agent_id:
        prev_agent = await db.get(Agent, previous_agent_id)
        if prev_agent and prev_agent.current_load > 0:
            prev_agent.current_load -= 1
    
    # Assign new agent
    if reassign_data.agent_id:
        new_agent = await db.get(Agent, reassign_data.agent_id)
        if not new_agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {reassign_data.agent_id} not found"
            )
        
        new_agent.current_load += 1
        ticket.assigned_agent_id = new_agent.id
        ticket.assignment_reason = "manual_reassignment"
    else:
        ticket.assigned_agent_id = None
        ticket.assignment_reason = "unassigned"
    
    ticket.previous_agent_id = previous_agent_id
    ticket.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(ticket)
    
    logger.info(f"Ticket {ticket_id} reassigned from {previous_agent_id} to {ticket.assigned_agent_id}")
    
    return TicketResponse.model_validate(ticket)


@router.post("/{ticket_id}/escalate", response_model=TicketResponse)
async def escalate_ticket(
    ticket_id: UUID,
    reason: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_async_db)
) -> TicketResponse:
    """Escalate ticket to senior support."""
    
    ticket = await db.get(Ticket, ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found"
        )
    
    ticket.escalated = True
    ticket.escalation_reason = reason
    ticket.status = TicketStatus.ESCALATED
    ticket.priority = min(ticket.priority + 1, 5)  # Boost priority
    ticket.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(ticket)
    
    logger.info(f"Ticket {ticket_id} escalated: {reason}")
    
    return TicketResponse.model_validate(ticket)


@router.post("/{ticket_id}/resolve", response_model=TicketResponse)
async def resolve_ticket(
    ticket_id: UUID,
    db: AsyncSession = Depends(get_async_db)
) -> TicketResponse:
    """Mark ticket as resolved."""
    
    ticket = await db.get(Ticket, ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found"
        )
    
    ticket.status = TicketStatus.RESOLVED
    ticket.resolved_at = datetime.utcnow()
    ticket.updated_at = datetime.utcnow()
    
    # Update agent load
    if ticket.assigned_agent_id:
        agent = await db.get(Agent, ticket.assigned_agent_id)
        if agent and agent.current_load > 0:
            agent.current_load -= 1
            agent.tickets_resolved_today += 1
            agent.total_tickets_resolved += 1
    
    await db.commit()
    await db.refresh(ticket)
    
    logger.info(f"Ticket {ticket_id} resolved")
    
    return TicketResponse.model_validate(ticket)


@router.post("/bulk", response_model=TicketBulkUpdateResponse)
async def bulk_update_tickets(
    bulk_data: TicketBulkUpdateRequest,
    db: AsyncSession = Depends(get_async_db)
) -> TicketBulkUpdateResponse:
    """Bulk update multiple tickets."""
    
    updated = 0
    failed = 0
    errors = []
    
    for ticket_id in bulk_data.ticket_ids:
        try:
            ticket = await db.get(Ticket, ticket_id)
            
            if not ticket:
                failed += 1
                errors.append({"ticket_id": str(ticket_id), "error": "not_found"})
                continue
            
            # Apply updates
            if bulk_data.status:
                ticket.status = bulk_data.status
            if bulk_data.category:
                ticket.category = bulk_data.category
            if bulk_data.priority:
                ticket.priority = bulk_data.priority
            if bulk_data.assigned_agent_id:
                ticket.assigned_agent_id = bulk_data.assigned_agent_id
            if bulk_data.add_tags:
                ticket.tags = list(set(ticket.tags or []) | set(bulk_data.add_tags))
            if bulk_data.remove_tags:
                ticket.tags = [t for t in (ticket.tags or []) if t not in bulk_data.remove_tags]
            
            ticket.updated_at = datetime.utcnow()
            updated += 1
            
        except Exception as e:
            failed += 1
            errors.append({"ticket_id": str(ticket_id), "error": str(e)})
    
    await db.commit()
    
    return TicketBulkUpdateResponse(
        updated=updated,
        failed=failed,
        errors=errors if errors else None
    )


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(
    ticket_id: UUID,
    db: AsyncSession = Depends(get_async_db)
):
    """Delete a ticket."""
    
    ticket = await db.get(Ticket, ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found"
        )
    
    # Update agent load if assigned
    if ticket.assigned_agent_id:
        agent = await db.get(Agent, ticket.assigned_agent_id)
        if agent and agent.current_load > 0:
            agent.current_load -= 1
    
    await db.delete(ticket)
    await db.commit()
    
    logger.info(f"Ticket {ticket_id} deleted")
