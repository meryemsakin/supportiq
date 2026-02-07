"""
Celery Task Definitions

Background tasks for ticket processing and system maintenance.
"""

import asyncio
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta

from celery import shared_task
from loguru import logger
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from src.workers.celery_app import celery_app
from src.database import SyncSessionLocal
from src.models.ticket import Ticket, TicketStatus
from src.models.agent import Agent


def run_async(coro):
    """Helper to run async code in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_ticket_task(self, ticket_id: str) -> Dict[str, Any]:
    """
    Process a ticket through the AI pipeline.
    
    This task:
    1. Classifies the ticket
    2. Analyzes sentiment
    3. Calculates priority
    4. Routes to agent
    5. Generates suggested responses
    """
    
    logger.info(f"Processing ticket {ticket_id}")
    
    db = SyncSessionLocal()
    
    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        
        if not ticket:
            logger.error(f"Ticket {ticket_id} not found")
            return {"status": "error", "message": "Ticket not found"}
        
        # Run async processing
        async def process():
            from src.services.classifier import get_classifier
            from src.services.sentiment import get_sentiment_analyzer
            from src.services.priority_scorer import get_priority_scorer
            from src.services.rag import knowledge_base
            
            results = {}
            
            # 1. Classification
            classifier = get_classifier()
            classification = await classifier.classify(
                text=ticket.content,
                language=ticket.language or "tr"
            )
            
            ticket.category = classification.get("primary_category")
            ticket.category_confidence = classification.get("confidence")
            ticket.classification_reasoning = classification.get("reasoning")
            results["classification"] = classification
            
            # 2. Sentiment
            analyzer = get_sentiment_analyzer()
            sentiment = await analyzer.analyze(
                text=ticket.content,
                language=ticket.language or "tr"
            )
            
            ticket.sentiment = sentiment.get("sentiment")
            ticket.sentiment_score = sentiment.get("score")
            results["sentiment"] = sentiment
            
            # 3. Priority
            scorer = get_priority_scorer()
            priority = scorer.calculate(
                text=ticket.content,
                sentiment=ticket.sentiment,
                anger_level=sentiment.get("anger_level"),
                customer_tier=ticket.customer_tier or "standard",
                category=ticket.category,
                language=ticket.language or "tr"
            )
            
            ticket.priority = priority.get("score")
            ticket.priority_level = priority.get("level")
            ticket.priority_factors = priority.get("factors")
            results["priority"] = priority
            
            # 4. Suggested responses
            try:
                suggestions = await knowledge_base.generate_suggested_responses(
                    ticket_content=ticket.content,
                    category=ticket.category,
                    language=ticket.language or "tr",
                    limit=3
                )
                ticket.suggested_responses = suggestions
                results["suggested_responses"] = suggestions
            except Exception as e:
                logger.warning(f"Suggested responses failed: {e}")
            
            return results
        
        results = run_async(process())
        
        # Mark as processed
        ticket.is_processed = True
        ticket.status = TicketStatus.OPEN
        ticket.updated_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(
            f"Ticket {ticket_id} processed: "
            f"category={ticket.category}, priority={ticket.priority}"
        )
        
        return {
            "status": "success",
            "ticket_id": ticket_id,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Failed to process ticket {ticket_id}: {e}")
        db.rollback()
        
        # Retry
        raise self.retry(exc=e)
        
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def sync_external_ticket_task(
    self,
    ticket_id: str,
    external_system: str
) -> Dict[str, Any]:
    """
    Sync ticket status with external system (Zendesk, Freshdesk, etc.)
    """
    
    logger.info(f"Syncing ticket {ticket_id} with {external_system}")
    
    db = SyncSessionLocal()
    
    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        
        if not ticket:
            return {"status": "error", "message": "Ticket not found"}
        
        if external_system == "zendesk":
            from src.integrations.zendesk import ZendeskClient
            client = ZendeskClient()
            run_async(client.update_ticket(
                ticket_id=ticket.external_id,
                category=ticket.category,
                priority=ticket.priority,
                status=ticket.status.value if ticket.status else None
            ))
            
        elif external_system == "freshdesk":
            from src.integrations.freshdesk import FreshdeskClient
            client = FreshdeskClient()
            run_async(client.update_ticket(
                ticket_id=ticket.external_id,
                category=ticket.category,
                priority=ticket.priority
            ))
        
        return {"status": "success", "ticket_id": ticket_id}
        
    except Exception as e:
        logger.error(f"Failed to sync ticket {ticket_id}: {e}")
        raise self.retry(exc=e)
        
    finally:
        db.close()


@celery_app.task
def send_notification_task(
    notification_type: str,
    recipients: list,
    data: dict
) -> Dict[str, Any]:
    """
    Send notifications (email, Slack, etc.)
    """
    
    logger.info(f"Sending {notification_type} notification to {len(recipients)} recipients")
    
    try:
        if notification_type == "email":
            # TODO: Implement email sending
            pass
        elif notification_type == "slack":
            # TODO: Implement Slack notification
            pass
        
        return {"status": "success", "sent_to": len(recipients)}
        
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task
def reset_daily_stats_task() -> Dict[str, Any]:
    """
    Reset daily statistics for agents.
    Runs at midnight via Celery Beat.
    """
    
    logger.info("Resetting daily agent stats")
    
    db = SyncSessionLocal()
    
    try:
        # Reset daily counters
        db.query(Agent).update({
            Agent.tickets_handled_today: 0,
            Agent.tickets_resolved_today: 0
        })
        
        db.commit()
        
        return {"status": "success", "message": "Daily stats reset"}
        
    except Exception as e:
        logger.error(f"Failed to reset daily stats: {e}")
        db.rollback()
        return {"status": "error", "message": str(e)}
        
    finally:
        db.close()


@celery_app.task
def check_sla_breaches_task() -> Dict[str, Any]:
    """
    Check for SLA breaches and mark tickets.
    Runs every 5 minutes via Celery Beat.
    """
    
    logger.info("Checking for SLA breaches")
    
    db = SyncSessionLocal()
    
    try:
        now = datetime.utcnow()
        
        # Find tickets with breached SLA
        breached = db.query(Ticket).filter(
            and_(
                Ticket.sla_due_at.isnot(None),
                Ticket.sla_due_at < now,
                Ticket.sla_breached == False,
                Ticket.status.in_([
                    TicketStatus.NEW,
                    TicketStatus.OPEN,
                    TicketStatus.IN_PROGRESS
                ])
            )
        ).all()
        
        count = 0
        for ticket in breached:
            ticket.sla_breached = True
            ticket.priority = min(ticket.priority + 1, 5)  # Boost priority
            count += 1
        
        db.commit()
        
        if count > 0:
            logger.warning(f"Marked {count} tickets as SLA breached")
        
        return {"status": "success", "breached_count": count}
        
    except Exception as e:
        logger.error(f"Failed to check SLA breaches: {e}")
        db.rollback()
        return {"status": "error", "message": str(e)}
        
    finally:
        db.close()


@celery_app.task
def sync_external_systems_task() -> Dict[str, Any]:
    """
    Sync with external systems (Zendesk, Freshdesk).
    Runs every 10 minutes via Celery Beat.
    """
    
    logger.info("Syncing with external systems")
    
    # This is a placeholder - actual implementation would:
    # 1. Fetch new tickets from external systems
    # 2. Update local ticket statuses
    # 3. Push local changes to external systems
    
    return {"status": "success", "message": "Sync completed"}


@celery_app.task
def cleanup_old_data_task(days: int = 90) -> Dict[str, Any]:
    """
    Clean up old processed data.
    Should be run periodically (e.g., weekly).
    """
    
    logger.info(f"Cleaning up data older than {days} days")
    
    db = SyncSessionLocal()
    
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Delete old closed tickets
        deleted = db.query(Ticket).filter(
            and_(
                Ticket.status == TicketStatus.CLOSED,
                Ticket.closed_at < cutoff
            )
        ).delete()
        
        db.commit()
        
        logger.info(f"Deleted {deleted} old tickets")
        
        return {"status": "success", "deleted_count": deleted}
        
    except Exception as e:
        logger.error(f"Failed to cleanup old data: {e}")
        db.rollback()
        return {"status": "error", "message": str(e)}
        
    finally:
        db.close()
