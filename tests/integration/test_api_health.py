"""
Integration Tests for Health API

Tests for health check endpoints.
"""

import pytest
from httpx import AsyncClient


class TestHealthAPI:
    """Integration tests for health endpoints."""
    
    @pytest.mark.asyncio
    async def test_basic_health(self, client: AsyncClient):
        """Test basic health check."""
        response = await client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "timestamp" in data
    
    @pytest.mark.asyncio
    async def test_detailed_health(self, client: AsyncClient):
        """Test detailed health check."""
        response = await client.get("/api/v1/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "checks" in data
        assert "database" in data["checks"]
    
    @pytest.mark.asyncio
    async def test_readiness(self, client: AsyncClient):
        """Test readiness probe."""
        response = await client.get("/api/v1/ready")
        
        assert response.status_code == 200
        data = response.json()
        assert "ready" in data
    
    @pytest.mark.asyncio
    async def test_liveness(self, client: AsyncClient):
        """Test liveness probe."""
        response = await client.get("/api/v1/live")
        
        assert response.status_code == 200
        data = response.json()
        assert data["alive"] == True
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """Test root endpoint."""
        response = await client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "status" in data
