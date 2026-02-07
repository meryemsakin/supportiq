"""
Integration Tests for Ticket API

Tests for ticket-related API endpoints.
"""

import pytest
from httpx import AsyncClient
from uuid import uuid4

from src.models.ticket import TicketStatus


class TestTicketAPI:
    """Integration tests for ticket endpoints."""
    
    @pytest.mark.asyncio
    async def test_create_ticket(self, client: AsyncClient):
        """Test creating a new ticket via API."""
        response = await client.post(
            "/api/v1/tickets",
            json={
                "content": "Uygulamanız çalışmıyor",
                "subject": "Uygulama Hatası",
                "customer_email": "test@example.com",
                "customer_name": "Test User",
                "process_async": False
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "ticket_id" in data
        assert data["status"] in ["processed", "queued"]
    
    @pytest.mark.asyncio
    async def test_create_ticket_minimal(self, client: AsyncClient):
        """Test creating a ticket with minimal data."""
        response = await client.post(
            "/api/v1/tickets",
            json={
                "content": "Test ticket content"
            }
        )
        
        assert response.status_code == 201
    
    @pytest.mark.asyncio
    async def test_create_ticket_empty_content(self, client: AsyncClient):
        """Test creating a ticket with empty content fails."""
        response = await client.post(
            "/api/v1/tickets",
            json={
                "content": ""
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_get_ticket(self, client: AsyncClient, sample_ticket):
        """Test getting a ticket by ID."""
        response = await client.get(f"/api/v1/tickets/{sample_ticket.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_ticket.id)
        assert data["content"] == sample_ticket.content
    
    @pytest.mark.asyncio
    async def test_get_ticket_not_found(self, client: AsyncClient):
        """Test getting a non-existent ticket."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/tickets/{fake_id}")
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_list_tickets(self, client: AsyncClient, sample_ticket):
        """Test listing tickets."""
        response = await client.get("/api/v1/tickets")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
    
    @pytest.mark.asyncio
    async def test_list_tickets_with_filter(self, client: AsyncClient, sample_ticket):
        """Test listing tickets with filters."""
        response = await client.get(
            "/api/v1/tickets",
            params={"category": "technical_issue", "priority": 4}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["items"], list)
    
    @pytest.mark.asyncio
    async def test_list_tickets_pagination(self, client: AsyncClient):
        """Test ticket list pagination."""
        response = await client.get(
            "/api/v1/tickets",
            params={"page": 1, "page_size": 5}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5
    
    @pytest.mark.asyncio
    async def test_update_ticket(self, client: AsyncClient, sample_ticket):
        """Test updating a ticket."""
        response = await client.patch(
            f"/api/v1/tickets/{sample_ticket.id}",
            json={
                "priority": 5,
                "tags": ["urgent", "vip"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["priority"] == 5
        assert "urgent" in data["tags"]
    
    @pytest.mark.asyncio
    async def test_resolve_ticket(self, client: AsyncClient, sample_ticket):
        """Test resolving a ticket."""
        response = await client.post(f"/api/v1/tickets/{sample_ticket.id}/resolve")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved"
    
    @pytest.mark.asyncio
    async def test_escalate_ticket(self, client: AsyncClient, sample_ticket):
        """Test escalating a ticket."""
        response = await client.post(
            f"/api/v1/tickets/{sample_ticket.id}/escalate",
            params={"reason": "VIP customer"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["escalated"] == True
        assert data["status"] == "escalated"
    
    @pytest.mark.asyncio
    async def test_reassign_ticket(
        self,
        client: AsyncClient,
        sample_ticket,
        sample_agent
    ):
        """Test reassigning a ticket."""
        response = await client.post(
            f"/api/v1/tickets/{sample_ticket.id}/reassign",
            json={
                "agent_id": str(sample_agent.id),
                "reason": "Skill match"
            }
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_delete_ticket(self, client: AsyncClient, sample_ticket):
        """Test deleting a ticket."""
        response = await client.delete(f"/api/v1/tickets/{sample_ticket.id}")
        
        assert response.status_code == 204
        
        # Verify deleted
        get_response = await client.get(f"/api/v1/tickets/{sample_ticket.id}")
        assert get_response.status_code == 404


class TestTicketSearch:
    """Tests for ticket search functionality."""
    
    @pytest.mark.asyncio
    async def test_search_by_content(self, client: AsyncClient, sample_ticket):
        """Test searching tickets by content."""
        response = await client.get(
            "/api/v1/tickets",
            params={"search": "çalışmıyor"}
        )
        
        assert response.status_code == 200
        data = response.json()
        # If sample ticket exists, it should be found
        if data["total"] > 0:
            found = any(
                "çalışmıyor" in item.get("content", "").lower()
                for item in data["items"]
            )
            assert found or data["total"] == 0
    
    @pytest.mark.asyncio
    async def test_filter_by_status(self, client: AsyncClient, sample_ticket):
        """Test filtering tickets by status."""
        response = await client.get(
            "/api/v1/tickets",
            params={"status": "open"}
        )
        
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["status"] == "open"
    
    @pytest.mark.asyncio
    async def test_filter_by_sentiment(self, client: AsyncClient, sample_ticket):
        """Test filtering tickets by sentiment."""
        response = await client.get(
            "/api/v1/tickets",
            params={"sentiment": "negative"}
        )
        
        assert response.status_code == 200
