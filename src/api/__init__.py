"""
API Endpoints Package

Contains all FastAPI router modules for the REST API.
"""

from src.api.tickets import router as tickets_router
from src.api.agents import router as agents_router
from src.api.analytics import router as analytics_router
from src.api.config_api import router as config_router
from src.api.webhooks import router as webhooks_router
from src.api.health import router as health_router

__all__ = [
    "tickets_router",
    "agents_router",
    "analytics_router",
    "config_router",
    "webhooks_router",
    "health_router",
]
