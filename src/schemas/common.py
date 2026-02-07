"""
Common Pydantic Schemas

Shared schemas used across the application.
"""

from datetime import datetime
from typing import Generic, TypeVar, Optional, List, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# Generic type for paginated responses
T = TypeVar("T")


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""
    
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Alias for page_size."""
        return self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    
    items: List[T]
    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Items per page")
    pages: int = Field(description="Total number of pages")
    has_next: bool = Field(description="Whether there is a next page")
    has_prev: bool = Field(description="Whether there is a previous page")
    
    model_config = ConfigDict(from_attributes=True)
    
    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        page_size: int
    ) -> "PaginatedResponse[T]":
        """Create a paginated response."""
        pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1
        )


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(description="Service status")
    version: str = Field(description="API version")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    checks: dict = Field(default_factory=dict, description="Individual health checks")


class ErrorResponse(BaseModel):
    """Standard error response."""
    
    detail: str = Field(description="Error message")
    code: Optional[str] = Field(default=None, description="Error code")
    errors: Optional[List[dict]] = Field(default=None, description="Validation errors")


class SuccessResponse(BaseModel):
    """Standard success response."""
    
    message: str = Field(description="Success message")
    data: Optional[Any] = Field(default=None, description="Additional data")


class FilterParams(BaseModel):
    """Common filter parameters."""
    
    search: Optional[str] = Field(default=None, description="Search term")
    sort_by: Optional[str] = Field(default="created_at", description="Sort field")
    sort_order: Optional[str] = Field(default="desc", pattern="^(asc|desc)$", description="Sort order")
    created_after: Optional[datetime] = Field(default=None, description="Filter by creation date (after)")
    created_before: Optional[datetime] = Field(default=None, description="Filter by creation date (before)")


class ClassificationResult(BaseModel):
    """Result of AI classification."""
    
    primary_category: str = Field(description="Primary category")
    confidence: float = Field(ge=0, le=1, description="Confidence score")
    all_categories: Optional[dict] = Field(default=None, description="All category scores")
    reasoning: Optional[str] = Field(default=None, description="Classification reasoning")


class SentimentResult(BaseModel):
    """Result of sentiment analysis."""
    
    sentiment: str = Field(description="Detected sentiment")
    score: float = Field(ge=-1, le=1, description="Sentiment score")
    confidence: float = Field(ge=0, le=1, description="Confidence score")


class PriorityResult(BaseModel):
    """Result of priority scoring."""
    
    score: int = Field(ge=1, le=5, description="Priority score")
    level: str = Field(description="Priority level name")
    factors: List[str] = Field(default_factory=list, description="Contributing factors")


class RoutingResult(BaseModel):
    """Result of ticket routing."""
    
    agent_id: Optional[UUID] = Field(description="Assigned agent ID")
    agent_name: Optional[str] = Field(description="Assigned agent name")
    team: Optional[str] = Field(description="Assigned team")
    reason: str = Field(description="Routing reason")
    confidence: float = Field(ge=0, le=1, description="Routing confidence")


class SuggestedResponseItem(BaseModel):
    """A single suggested response."""
    
    content: str = Field(description="Response content")
    source: str = Field(description="Source type (rag, template, ai)")
    relevance_score: float = Field(ge=0, le=1, description="Relevance score")
    metadata: Optional[dict] = Field(default=None, description="Additional metadata")
