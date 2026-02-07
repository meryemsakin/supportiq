"""
Base Integration Class

Abstract base class for external system integrations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class ExternalTicket:
    """Represents a ticket from an external system."""
    
    id: str
    subject: Optional[str]
    content: str
    status: str
    priority: Optional[int]
    requester_email: Optional[str]
    requester_name: Optional[str]
    created_at: str
    updated_at: Optional[str]
    tags: List[str]
    custom_fields: Dict[str, Any]


class BaseIntegration(ABC):
    """
    Abstract base class for helpdesk integrations.
    
    All integration clients should inherit from this class
    and implement the required methods.
    """
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Authenticate with the external system.
        
        Returns:
            bool: True if authentication successful
        """
        pass
    
    @abstractmethod
    async def get_ticket(self, ticket_id: str) -> Optional[ExternalTicket]:
        """
        Get a single ticket by ID.
        
        Args:
            ticket_id: External ticket ID
            
        Returns:
            ExternalTicket or None if not found
        """
        pass
    
    @abstractmethod
    async def get_tickets(
        self,
        status: Optional[str] = None,
        since: Optional[str] = None,
        limit: int = 100
    ) -> List[ExternalTicket]:
        """
        Get multiple tickets with optional filtering.
        
        Args:
            status: Filter by status
            since: Get tickets created/updated since this datetime
            limit: Maximum number of tickets to return
            
        Returns:
            List of ExternalTicket objects
        """
        pass
    
    @abstractmethod
    async def create_ticket(
        self,
        subject: str,
        content: str,
        requester_email: str,
        priority: Optional[int] = None,
        tags: Optional[List[str]] = None,
        custom_fields: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new ticket in the external system.
        
        Args:
            subject: Ticket subject
            content: Ticket content/body
            requester_email: Customer email
            priority: Priority level
            tags: List of tags
            custom_fields: Additional fields
            
        Returns:
            str: Created ticket ID
        """
        pass
    
    @abstractmethod
    async def update_ticket(
        self,
        ticket_id: str,
        status: Optional[str] = None,
        priority: Optional[int] = None,
        assignee: Optional[str] = None,
        tags: Optional[List[str]] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> bool:
        """
        Update a ticket in the external system.
        
        Args:
            ticket_id: External ticket ID
            status: New status
            priority: New priority
            assignee: New assignee ID
            tags: Updated tags
            custom_fields: Updated custom fields
            
        Returns:
            bool: True if update successful
        """
        pass
    
    @abstractmethod
    async def add_comment(
        self,
        ticket_id: str,
        content: str,
        public: bool = True,
        author_id: Optional[str] = None
    ) -> bool:
        """
        Add a comment to a ticket.
        
        Args:
            ticket_id: External ticket ID
            content: Comment content
            public: Whether comment is public
            author_id: Comment author ID
            
        Returns:
            bool: True if comment added successfully
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close any open connections."""
        pass
