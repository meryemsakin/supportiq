"""
Webhook API Endpoints

Handle incoming webhooks from external systems like Zendesk, Freshdesk, etc.
"""

import hmac
import hashlib
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Header, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.database import get_async_db
from src.config import settings
from src.schemas.ticket import TicketCreate

router = APIRouter()


def verify_zendesk_signature(
    payload: bytes,
    signature: str,
    secret: str
) -> bool:
    """Verify Zendesk webhook signature."""
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)


def verify_freshdesk_signature(
    payload: bytes,
    signature: str,
    secret: str
) -> bool:
    """Verify Freshdesk webhook signature."""
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha1
    ).hexdigest()
    return hmac.compare_digest(signature, expected)


@router.post("/zendesk")
async def zendesk_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_zendesk_webhook_signature: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """
    Handle incoming Zendesk webhooks.
    
    Supports:
    - Ticket created
    - Ticket updated
    - Ticket comment added
    """
    
    body = await request.body()
    
    # Verify signature if secret is configured
    if settings.zendesk_webhook_secret:
        if not x_zendesk_webhook_signature:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing webhook signature"
            )
        
        if not verify_zendesk_signature(
            body,
            x_zendesk_webhook_signature,
            settings.zendesk_webhook_secret
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
    
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )
    
    logger.info(f"Received Zendesk webhook: {data.get('type', 'unknown')}")
    
    # Handle different event types
    event_type = data.get("type")
    
    if event_type == "ticket.created" or event_type == "zen:event-type:ticket.created":
        ticket_data = data.get("ticket", data)
        
        # Import here to avoid circular imports
        from src.api.tickets import create_ticket
        
        ticket_create = TicketCreate(
            content=ticket_data.get("description", ""),
            subject=ticket_data.get("subject"),
            customer_email=ticket_data.get("requester", {}).get("email"),
            customer_name=ticket_data.get("requester", {}).get("name"),
            external_id=str(ticket_data.get("id")),
            external_system="zendesk",
            source="zendesk",
            tags=ticket_data.get("tags", []),
            custom_fields={
                "zendesk_status": ticket_data.get("status"),
                "zendesk_priority": ticket_data.get("priority")
            }
        )
        
        # Process ticket in background
        result = await create_ticket(ticket_create, background_tasks, db)
        
        return {
            "status": "accepted",
            "ticket_id": str(result.ticket_id),
            "external_id": ticket_create.external_id
        }
    
    elif event_type == "ticket.updated":
        # Handle ticket updates
        ticket_data = data.get("ticket", data)
        logger.info(f"Zendesk ticket updated: {ticket_data.get('id')}")
        
        return {
            "status": "acknowledged",
            "event": "ticket.updated"
        }
    
    else:
        logger.warning(f"Unhandled Zendesk event type: {event_type}")
        return {
            "status": "ignored",
            "reason": f"Unhandled event type: {event_type}"
        }


@router.post("/freshdesk")
async def freshdesk_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """
    Handle incoming Freshdesk webhooks.
    
    Supports:
    - Ticket created
    - Ticket updated
    """
    
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )
    
    logger.info(f"Received Freshdesk webhook")
    
    # Freshdesk sends ticket data directly
    ticket_data = data.get("freshdesk_webhook", data)
    
    # Check if this is a new ticket
    if ticket_data.get("ticket_id"):
        from src.api.tickets import create_ticket
        
        ticket_create = TicketCreate(
            content=ticket_data.get("ticket_description", ""),
            subject=ticket_data.get("ticket_subject"),
            customer_email=ticket_data.get("ticket_requester_email"),
            customer_name=ticket_data.get("ticket_requester_name"),
            external_id=str(ticket_data.get("ticket_id")),
            external_system="freshdesk",
            source="freshdesk",
            tags=ticket_data.get("ticket_tags", "").split(",") if ticket_data.get("ticket_tags") else [],
            custom_fields={
                "freshdesk_status": ticket_data.get("ticket_status"),
                "freshdesk_priority": ticket_data.get("ticket_priority")
            }
        )
        
        result = await create_ticket(ticket_create, background_tasks, db)
        
        return {
            "status": "accepted",
            "ticket_id": str(result.ticket_id),
            "external_id": ticket_create.external_id
        }
    
    return {
        "status": "acknowledged"
    }


@router.post("/generic")
async def generic_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_webhook_secret: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """
    Handle generic webhooks from any system.
    
    Expected payload format:
    ```json
    {
        "content": "Ticket content/message",
        "subject": "Optional subject",
        "customer_email": "customer@example.com",
        "customer_name": "Customer Name",
        "external_id": "external-system-id",
        "source": "custom-system",
        "priority": 3,
        "tags": ["tag1", "tag2"],
        "custom_fields": {}
    }
    ```
    """
    
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )
    
    # Validate required fields
    if not data.get("content"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required field: content"
        )
    
    logger.info(f"Received generic webhook from {data.get('source', 'unknown')}")
    
    from src.api.tickets import create_ticket
    
    ticket_create = TicketCreate(
        content=data["content"],
        subject=data.get("subject"),
        customer_email=data.get("customer_email"),
        customer_name=data.get("customer_name"),
        customer_tier=data.get("customer_tier", "standard"),
        external_id=data.get("external_id"),
        external_system=data.get("source"),
        source="webhook",
        channel=data.get("channel"),
        language=data.get("language"),
        tags=data.get("tags", []),
        custom_fields=data.get("custom_fields", {})
    )
    
    result = await create_ticket(ticket_create, background_tasks, db)
    
    return {
        "status": "accepted",
        "ticket_id": str(result.ticket_id),
        "processing_status": result.status
    }


@router.post("/email")
async def email_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """
    Handle email forwarding webhooks.
    
    Expected payload (e.g., from Mailgun, SendGrid, etc.):
    ```json
    {
        "from": "customer@example.com",
        "to": "support@yourcompany.com",
        "subject": "Email subject",
        "body-plain": "Plain text body",
        "body-html": "HTML body",
        "message-id": "unique-message-id"
    }
    ```
    """
    
    try:
        # Try JSON first
        data = await request.json()
    except Exception:
        # Fall back to form data
        form = await request.form()
        data = dict(form)
    
    # Extract email fields (support multiple formats)
    sender = data.get("from") or data.get("sender") or data.get("From")
    subject = data.get("subject") or data.get("Subject")
    body = (
        data.get("body-plain") or 
        data.get("text") or 
        data.get("body") or
        data.get("stripped-text") or
        ""
    )
    message_id = data.get("message-id") or data.get("Message-Id")
    
    if not body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing email body"
        )
    
    # Parse sender email
    import re
    email_match = re.search(r'[\w\.-]+@[\w\.-]+', sender or "")
    customer_email = email_match.group() if email_match else None
    
    # Extract name from sender
    customer_name = None
    if sender and "<" in sender:
        customer_name = sender.split("<")[0].strip().strip('"')
    
    logger.info(f"Received email webhook from {customer_email}")
    
    from src.api.tickets import create_ticket
    
    ticket_create = TicketCreate(
        content=body,
        subject=subject,
        customer_email=customer_email,
        customer_name=customer_name,
        external_id=message_id,
        external_system="email",
        source="email",
        channel="email"
    )
    
    result = await create_ticket(ticket_create, background_tasks, db)
    
    return {
        "status": "accepted",
        "ticket_id": str(result.ticket_id)
    }
