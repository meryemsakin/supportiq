"""
Zendesk Integration

Client for Zendesk API v2.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.integrations.base import BaseIntegration, ExternalTicket


class ZendeskClient(BaseIntegration):
    """
    Zendesk API client.
    
    Provides integration with Zendesk for:
    - Fetching tickets
    - Creating tickets
    - Updating ticket status, priority, assignee
    - Adding comments
    """
    
    def __init__(
        self,
        subdomain: Optional[str] = None,
        email: Optional[str] = None,
        api_token: Optional[str] = None
    ):
        """
        Initialize Zendesk client.
        
        Args:
            subdomain: Zendesk subdomain (e.g., 'company' for company.zendesk.com)
            email: Zendesk account email
            api_token: Zendesk API token
        """
        self.subdomain = subdomain or settings.zendesk_subdomain
        self.email = email or settings.zendesk_email
        self.api_token = api_token or settings.zendesk_api_token
        
        if not all([self.subdomain, self.email, self.api_token]):
            logger.warning("Zendesk credentials not fully configured")
        
        self.base_url = f"https://{self.subdomain}.zendesk.com/api/v2"
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                auth=(f"{self.email}/token", self.api_token),
                headers={"Content-Type": "application/json"},
                timeout=30.0
            )
        
        return self._client
    
    async def authenticate(self) -> bool:
        """Test authentication with Zendesk."""
        
        try:
            client = await self._get_client()
            response = await client.get("/users/me.json")
            response.raise_for_status()
            
            user = response.json().get("user", {})
            logger.info(f"Authenticated with Zendesk as {user.get('email')}")
            
            return True
            
        except Exception as e:
            logger.error(f"Zendesk authentication failed: {e}")
            return False
    
    def _parse_ticket(self, data: Dict) -> ExternalTicket:
        """Parse Zendesk ticket data into ExternalTicket."""
        
        return ExternalTicket(
            id=str(data.get("id")),
            subject=data.get("subject"),
            content=data.get("description", ""),
            status=data.get("status", "new"),
            priority=self._map_priority_from_zendesk(data.get("priority")),
            requester_email=data.get("requester", {}).get("email"),
            requester_name=data.get("requester", {}).get("name"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            tags=data.get("tags", []),
            custom_fields={
                f.get("id"): f.get("value")
                for f in data.get("custom_fields", [])
            }
        )
    
    def _map_priority_from_zendesk(self, priority: Optional[str]) -> int:
        """Map Zendesk priority to our 1-5 scale."""
        mapping = {
            "urgent": 5,
            "high": 4,
            "normal": 3,
            "low": 2
        }
        return mapping.get(priority, 3)
    
    def _map_priority_to_zendesk(self, priority: int) -> str:
        """Map our priority to Zendesk priority."""
        if priority >= 5:
            return "urgent"
        elif priority >= 4:
            return "high"
        elif priority >= 3:
            return "normal"
        else:
            return "low"
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def get_ticket(self, ticket_id: str) -> Optional[ExternalTicket]:
        """Get a single ticket from Zendesk."""
        
        try:
            client = await self._get_client()
            response = await client.get(f"/tickets/{ticket_id}.json")
            
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            
            data = response.json().get("ticket", {})
            return self._parse_ticket(data)
            
        except Exception as e:
            logger.error(f"Failed to get Zendesk ticket {ticket_id}: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def get_tickets(
        self,
        status: Optional[str] = None,
        since: Optional[str] = None,
        limit: int = 100
    ) -> List[ExternalTicket]:
        """Get tickets from Zendesk."""
        
        try:
            client = await self._get_client()
            
            # Build query
            params = {"per_page": min(limit, 100)}
            
            if status:
                params["query"] = f"status:{status}"
            
            response = await client.get("/tickets.json", params=params)
            response.raise_for_status()
            
            data = response.json()
            tickets = [self._parse_ticket(t) for t in data.get("tickets", [])]
            
            return tickets
            
        except Exception as e:
            logger.error(f"Failed to get Zendesk tickets: {e}")
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
        """Create a new ticket in Zendesk."""
        
        try:
            client = await self._get_client()
            
            ticket_data = {
                "ticket": {
                    "subject": subject,
                    "description": content,
                    "requester": {"email": requester_email},
                    "tags": tags or []
                }
            }
            
            if priority:
                ticket_data["ticket"]["priority"] = self._map_priority_to_zendesk(priority)
            
            if custom_fields:
                ticket_data["ticket"]["custom_fields"] = [
                    {"id": k, "value": v}
                    for k, v in custom_fields.items()
                ]
            
            response = await client.post("/tickets.json", json=ticket_data)
            response.raise_for_status()
            
            created = response.json().get("ticket", {})
            ticket_id = str(created.get("id"))
            
            logger.info(f"Created Zendesk ticket: {ticket_id}")
            
            return ticket_id
            
        except Exception as e:
            logger.error(f"Failed to create Zendesk ticket: {e}")
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
        """Update a ticket in Zendesk."""
        
        try:
            client = await self._get_client()
            
            ticket_data: Dict[str, Any] = {}
            
            if status:
                # Map our status to Zendesk status
                status_map = {
                    "new": "new",
                    "open": "open",
                    "in_progress": "pending",
                    "pending": "pending",
                    "resolved": "solved",
                    "closed": "closed"
                }
                ticket_data["status"] = status_map.get(status, status)
            
            if priority:
                ticket_data["priority"] = self._map_priority_to_zendesk(priority)
            
            if assignee:
                ticket_data["assignee_id"] = assignee
            
            if tags:
                ticket_data["tags"] = tags
            
            if category:
                # Add category as tag
                if "tags" not in ticket_data:
                    ticket_data["tags"] = []
                ticket_data["tags"].append(f"category:{category}")
            
            if custom_fields:
                ticket_data["custom_fields"] = [
                    {"id": k, "value": v}
                    for k, v in custom_fields.items()
                ]
            
            if not ticket_data:
                return True
            
            response = await client.put(
                f"/tickets/{ticket_id}.json",
                json={"ticket": ticket_data}
            )
            response.raise_for_status()
            
            logger.info(f"Updated Zendesk ticket: {ticket_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update Zendesk ticket {ticket_id}: {e}")
            return False
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def add_comment(
        self,
        ticket_id: str,
        content: str,
        public: bool = True,
        author_id: Optional[str] = None
    ) -> bool:
        """Add a comment to a Zendesk ticket."""
        
        try:
            client = await self._get_client()
            
            comment_data = {
                "ticket": {
                    "comment": {
                        "body": content,
                        "public": public
                    }
                }
            }
            
            if author_id:
                comment_data["ticket"]["comment"]["author_id"] = author_id
            
            response = await client.put(
                f"/tickets/{ticket_id}.json",
                json=comment_data
            )
            response.raise_for_status()
            
            logger.info(f"Added comment to Zendesk ticket: {ticket_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add comment to Zendesk ticket {ticket_id}: {e}")
            return False
    
    async def close(self) -> None:
        """Close HTTP client."""
        
        if self._client:
            await self._client.aclose()
            self._client = None
