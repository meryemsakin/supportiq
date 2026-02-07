"""
Freshdesk Integration

Client for Freshdesk API v2.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import base64

import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.integrations.base import BaseIntegration, ExternalTicket


class FreshdeskClient(BaseIntegration):
    """
    Freshdesk API client.
    
    Provides integration with Freshdesk for:
    - Fetching tickets
    - Creating tickets
    - Updating ticket status, priority, assignee
    - Adding notes/replies
    """
    
    # Freshdesk status codes
    STATUS_MAP = {
        2: "open",
        3: "pending",
        4: "resolved",
        5: "closed"
    }
    
    STATUS_REVERSE_MAP = {
        "new": 2,
        "open": 2,
        "pending": 3,
        "in_progress": 3,
        "resolved": 4,
        "closed": 5
    }
    
    # Freshdesk priority codes
    PRIORITY_MAP = {
        1: 1,  # Low
        2: 2,  # Medium
        3: 3,  # High
        4: 4   # Urgent
    }
    
    def __init__(
        self,
        domain: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize Freshdesk client.
        
        Args:
            domain: Freshdesk domain (e.g., 'company' for company.freshdesk.com)
            api_key: Freshdesk API key
        """
        self.domain = domain or settings.freshdesk_domain
        self.api_key = api_key or settings.freshdesk_api_key
        
        if not all([self.domain, self.api_key]):
            logger.warning("Freshdesk credentials not fully configured")
        
        self.base_url = f"https://{self.domain}.freshdesk.com/api/v2"
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        
        if self._client is None:
            # Freshdesk uses API key as username with any password
            auth = base64.b64encode(f"{self.api_key}:X".encode()).decode()
            
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Basic {auth}",
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
        
        return self._client
    
    async def authenticate(self) -> bool:
        """Test authentication with Freshdesk."""
        
        try:
            client = await self._get_client()
            response = await client.get("/agents/me")
            response.raise_for_status()
            
            agent = response.json()
            logger.info(f"Authenticated with Freshdesk as {agent.get('contact', {}).get('email')}")
            
            return True
            
        except Exception as e:
            logger.error(f"Freshdesk authentication failed: {e}")
            return False
    
    def _parse_ticket(self, data: Dict) -> ExternalTicket:
        """Parse Freshdesk ticket data into ExternalTicket."""
        
        return ExternalTicket(
            id=str(data.get("id")),
            subject=data.get("subject"),
            content=data.get("description_text", data.get("description", "")),
            status=self.STATUS_MAP.get(data.get("status"), "open"),
            priority=data.get("priority", 2),
            requester_email=data.get("requester", {}).get("email"),
            requester_name=data.get("requester", {}).get("name"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            tags=data.get("tags", []),
            custom_fields=data.get("custom_fields", {})
        )
    
    def _map_priority_to_freshdesk(self, priority: int) -> int:
        """Map our 1-5 priority to Freshdesk 1-4 scale."""
        if priority >= 5:
            return 4  # Urgent
        elif priority >= 4:
            return 3  # High
        elif priority >= 3:
            return 2  # Medium
        else:
            return 1  # Low
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def get_ticket(self, ticket_id: str) -> Optional[ExternalTicket]:
        """Get a single ticket from Freshdesk."""
        
        try:
            client = await self._get_client()
            response = await client.get(f"/tickets/{ticket_id}")
            
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            
            data = response.json()
            return self._parse_ticket(data)
            
        except Exception as e:
            logger.error(f"Failed to get Freshdesk ticket {ticket_id}: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def get_tickets(
        self,
        status: Optional[str] = None,
        since: Optional[str] = None,
        limit: int = 100
    ) -> List[ExternalTicket]:
        """Get tickets from Freshdesk."""
        
        try:
            client = await self._get_client()
            
            params = {"per_page": min(limit, 100)}
            
            # Build filter query
            filters = []
            if status:
                status_code = self.STATUS_REVERSE_MAP.get(status)
                if status_code:
                    filters.append(f"status:{status_code}")
            
            if since:
                filters.append(f"updated_at:>'{since}'")
            
            if filters:
                params["query"] = " AND ".join(filters)
                endpoint = "/search/tickets"
            else:
                endpoint = "/tickets"
            
            response = await client.get(endpoint, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Handle search vs list response format
            if "results" in data:
                tickets = [self._parse_ticket(t) for t in data.get("results", [])]
            else:
                tickets = [self._parse_ticket(t) for t in data]
            
            return tickets
            
        except Exception as e:
            logger.error(f"Failed to get Freshdesk tickets: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def create_ticket(
        self,
        subject: str,
        content: str,
        requester_email: str,
        priority: Optional[int] = None,
        tags: Optional[List[str]] = None,
        custom_fields: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new ticket in Freshdesk."""
        
        try:
            client = await self._get_client()
            
            ticket_data = {
                "subject": subject,
                "description": content,
                "email": requester_email,
                "status": 2,  # Open
                "priority": self._map_priority_to_freshdesk(priority or 3),
                "source": 2  # Portal
            }
            
            if tags:
                ticket_data["tags"] = tags
            
            if custom_fields:
                ticket_data["custom_fields"] = custom_fields
            
            response = await client.post("/tickets", json=ticket_data)
            response.raise_for_status()
            
            created = response.json()
            ticket_id = str(created.get("id"))
            
            logger.info(f"Created Freshdesk ticket: {ticket_id}")
            
            return ticket_id
            
        except Exception as e:
            logger.error(f"Failed to create Freshdesk ticket: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def update_ticket(
        self,
        ticket_id: str,
        status: Optional[str] = None,
        priority: Optional[int] = None,
        assignee: Optional[str] = None,
        tags: Optional[List[str]] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
        category: Optional[str] = None,
        **kwargs
    ) -> bool:
        """Update a ticket in Freshdesk."""
        
        try:
            client = await self._get_client()
            
            ticket_data: Dict[str, Any] = {}
            
            if status:
                status_code = self.STATUS_REVERSE_MAP.get(status)
                if status_code:
                    ticket_data["status"] = status_code
            
            if priority:
                ticket_data["priority"] = self._map_priority_to_freshdesk(priority)
            
            if assignee:
                ticket_data["responder_id"] = int(assignee)
            
            if tags:
                ticket_data["tags"] = tags
            
            if category:
                # Add category as tag
                if "tags" not in ticket_data:
                    ticket_data["tags"] = []
                ticket_data["tags"].append(f"category:{category}")
            
            if custom_fields:
                ticket_data["custom_fields"] = custom_fields
            
            if not ticket_data:
                return True
            
            response = await client.put(
                f"/tickets/{ticket_id}",
                json=ticket_data
            )
            response.raise_for_status()
            
            logger.info(f"Updated Freshdesk ticket: {ticket_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update Freshdesk ticket {ticket_id}: {e}")
            return False
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def add_comment(
        self,
        ticket_id: str,
        content: str,
        public: bool = True,
        author_id: Optional[str] = None
    ) -> bool:
        """Add a note/reply to a Freshdesk ticket."""
        
        try:
            client = await self._get_client()
            
            if public:
                # Add a reply
                endpoint = f"/tickets/{ticket_id}/reply"
                note_data = {"body": content}
            else:
                # Add a private note
                endpoint = f"/tickets/{ticket_id}/notes"
                note_data = {
                    "body": content,
                    "private": True
                }
            
            if author_id:
                note_data["user_id"] = int(author_id)
            
            response = await client.post(endpoint, json=note_data)
            response.raise_for_status()
            
            logger.info(f"Added {'reply' if public else 'note'} to Freshdesk ticket: {ticket_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add comment to Freshdesk ticket {ticket_id}: {e}")
            return False
    
    async def close(self) -> None:
        """Close HTTP client."""
        
        if self._client:
            await self._client.aclose()
            self._client = None
