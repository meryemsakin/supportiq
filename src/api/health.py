"""
Health Check Endpoints

Provides health and readiness checks for the API.
"""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis

from src.database import get_async_db
from src.config import settings
from src.schemas.common import HealthResponse

router = APIRouter()


async def check_database(db: AsyncSession) -> Dict[str, Any]:
    """Check database connectivity."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "latency_ms": None}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_redis() -> Dict[str, Any]:
    """Check Redis connectivity."""
    try:
        client = redis.from_url(settings.redis_url)
        await client.ping()
        await client.close()
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_openai() -> Dict[str, Any]:
    """Check OpenAI API connectivity."""
    try:
        if not settings.openai_api_key:
            return {"status": "not_configured"}
        
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        # Simple models list call to verify API key
        await client.models.list()
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@router.get("/health", response_model=HealthResponse)
async def health_check(
    db: AsyncSession = Depends(get_async_db)
) -> HealthResponse:
    """
    Basic health check endpoint.
    
    Returns service status and version information.
    """
    
    # Check database
    db_status = await check_database(db)
    
    # Determine overall status
    status = "healthy" if db_status["status"] == "healthy" else "degraded"
    
    return HealthResponse(
        status=status,
        version="0.1.0",
        timestamp=datetime.utcnow(),
        checks={
            "database": db_status
        }
    )


@router.get("/health/detailed")
async def detailed_health_check(
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """
    Detailed health check with all service dependencies.
    
    Checks:
    - Database connectivity
    - Redis connectivity
    - OpenAI API connectivity
    """
    
    checks = {}
    
    # Database check
    checks["database"] = await check_database(db)
    
    # Redis check
    checks["redis"] = await check_redis()
    
    # OpenAI check
    checks["openai"] = await check_openai()
    
    # Calculate overall status
    statuses = [c.get("status") for c in checks.values()]
    if all(s == "healthy" for s in statuses):
        overall_status = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        overall_status = "unhealthy"
    else:
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "version": "0.1.0",
        "environment": settings.app_env,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks
    }


@router.get("/ready")
async def readiness_check(
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """
    Kubernetes-style readiness probe.
    
    Returns 200 if service is ready to accept traffic.
    """
    
    # Check critical dependencies
    db_status = await check_database(db)
    
    if db_status["status"] != "healthy":
        return {"ready": False, "reason": "database_unavailable"}
    
    return {"ready": True}


@router.get("/live")
async def liveness_check() -> Dict[str, Any]:
    """
    Kubernetes-style liveness probe.
    
    Returns 200 if service is alive.
    """
    return {"alive": True, "timestamp": datetime.utcnow().isoformat()}
