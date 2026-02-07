"""
Pydantic Schemas for API Request/Response Validation

This package contains all Pydantic models for data validation.
"""

from src.schemas.ticket import (
    TicketCreate,
    TicketUpdate,
    TicketResponse,
    TicketListResponse,
    TicketProcessResponse,
)
from src.schemas.agent import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentListResponse,
)
from src.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
)
from src.schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
)
from src.schemas.common import (
    PaginationParams,
    PaginatedResponse,
    HealthResponse,
    ErrorResponse,
)

__all__ = [
    # Ticket
    "TicketCreate",
    "TicketUpdate",
    "TicketResponse",
    "TicketListResponse",
    "TicketProcessResponse",
    # Agent
    "AgentCreate",
    "AgentUpdate",
    "AgentResponse",
    "AgentListResponse",
    # Category
    "CategoryCreate",
    "CategoryUpdate",
    "CategoryResponse",
    # Customer
    "CustomerCreate",
    "CustomerUpdate",
    "CustomerResponse",
    # Common
    "PaginationParams",
    "PaginatedResponse",
    "HealthResponse",
    "ErrorResponse",
]
