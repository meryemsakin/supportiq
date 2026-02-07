"""
Pytest Configuration and Fixtures

Shared fixtures for all tests.
"""

import asyncio
import os
from typing import AsyncGenerator, Generator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import event

# Set test environment
os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["OPENAI_API_KEY"] = "test-key"

from src.main import app
from src.database import Base, get_async_db
from src.models.ticket import Ticket, TicketStatus
from src.models.agent import Agent, AgentStatus, AgentRole
from src.models.category import Category
from src.models.customer import Customer, CustomerTier


# Test database setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False}
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()
    
    # Drop tables after test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database session override."""
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_async_db] = override_get_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


# =============================================================================
# Model Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def sample_agent(db_session: AsyncSession) -> Agent:
    """Create a sample agent."""
    agent = Agent(
        id=uuid4(),
        email="agent@example.com",
        name="Test Agent",
        role=AgentRole.AGENT,
        team="support",
        skills=["technical_issue", "billing_question"],
        languages=["tr", "en"],
        experience_level=3,
        max_load=10,
        current_load=0,
        status=AgentStatus.ONLINE,
        is_active=True,
        can_handle_critical=True,
        can_handle_vip=True
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)
    return agent


@pytest_asyncio.fixture
async def sample_customer(db_session: AsyncSession) -> Customer:
    """Create a sample customer."""
    customer = Customer(
        id=uuid4(),
        email="customer@example.com",
        name="Test Customer",
        tier=CustomerTier.PREMIUM,
        preferred_language="tr",
        is_active=True
    )
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)
    return customer


@pytest_asyncio.fixture
async def sample_category(db_session: AsyncSession) -> Category:
    """Create a sample category."""
    category = Category(
        id=uuid4(),
        name="technical_issue",
        display_name="Technical Issue",
        display_name_tr="Teknik Sorun",
        is_active=True,
        priority_boost=1,
        keywords=["error", "bug", "not working"],
        keywords_tr=["hata", "çalışmıyor", "bozuk"]
    )
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category


@pytest_asyncio.fixture
async def sample_ticket(
    db_session: AsyncSession,
    sample_agent: Agent,
    sample_customer: Customer
) -> Ticket:
    """Create a sample ticket."""
    ticket = Ticket(
        id=uuid4(),
        content="Uygulamanız çalışmıyor, sürekli hata veriyor.",
        subject="Uygulama Hatası",
        customer_id=sample_customer.id,
        customer_email=sample_customer.email,
        customer_name=sample_customer.name,
        customer_tier="premium",
        status=TicketStatus.OPEN,
        category="technical_issue",
        category_confidence=0.9,
        sentiment="negative",
        sentiment_score=-0.6,
        priority=4,
        priority_level="high",
        assigned_agent_id=sample_agent.id,
        language="tr",
        source="api",
        is_processed=True
    )
    db_session.add(ticket)
    await db_session.commit()
    await db_session.refresh(ticket)
    return ticket


# =============================================================================
# Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    return {
        "primary_category": "technical_issue",
        "confidence": 0.92,
        "all_categories": {
            "technical_issue": 0.92,
            "bug_report": 0.45,
            "general_inquiry": 0.1
        },
        "reasoning": "Customer mentions 'not working' and 'error'"
    }


@pytest.fixture
def mock_sentiment_response():
    """Mock sentiment analysis response."""
    return {
        "sentiment": "negative",
        "score": -0.6,
        "confidence": 0.88,
        "anger_level": 0.3,
        "satisfaction_prediction": 2,
        "key_phrases": ["çalışmıyor", "hata"],
        "reasoning": "Customer expressing frustration"
    }
