"""
External System Integrations

Provides integration clients for external helpdesk systems.
"""

from src.integrations.base import BaseIntegration
from src.integrations.zendesk import ZendeskClient
from src.integrations.freshdesk import FreshdeskClient

__all__ = [
    "BaseIntegration",
    "ZendeskClient",
    "FreshdeskClient",
]
