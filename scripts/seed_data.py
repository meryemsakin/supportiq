#!/usr/bin/env python3
"""
Seed Database Script

Populates the database with initial data for development and testing.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from uuid import uuid4
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import AsyncSessionLocal, init_db
from src.models.category import Category, DEFAULT_CATEGORIES
from src.models.rule import RoutingRule, DEFAULT_ROUTING_RULES
from src.models.agent import Agent, AgentStatus, AgentRole
from src.models.customer import Customer, CustomerTier
from src.models.ticket import Ticket, TicketStatus
from src.models.response import ResponseTemplate, DEFAULT_TEMPLATES


async def seed_categories(db: AsyncSession) -> int:
    """Seed default categories."""
    count = 0
    
    for cat_data in DEFAULT_CATEGORIES:
        existing = await db.execute(
            text(f"SELECT 1 FROM categories WHERE name = '{cat_data['name']}'")
        )
        if existing.scalar():
            continue
        
        category = Category(**cat_data)
        db.add(category)
        count += 1
    
    await db.commit()
    print(f"  Created {count} categories")
    return count


async def seed_routing_rules(db: AsyncSession) -> int:
    """Seed default routing rules."""
    count = 0
    
    for rule_data in DEFAULT_ROUTING_RULES:
        existing = await db.execute(
            text(f"SELECT 1 FROM routing_rules WHERE name = '{rule_data['name']}'")
        )
        if existing.scalar():
            continue
        
        rule = RoutingRule(**rule_data)
        db.add(rule)
        count += 1
    
    await db.commit()
    print(f"  Created {count} routing rules")
    return count


async def seed_response_templates(db: AsyncSession) -> int:
    """Seed default response templates."""
    count = 0
    
    for template_data in DEFAULT_TEMPLATES:
        existing = await db.execute(
            text(f"SELECT 1 FROM response_templates WHERE name = '{template_data['name']}'")
        )
        if existing.scalar():
            continue
        
        template = ResponseTemplate(**template_data)
        db.add(template)
        count += 1
    
    await db.commit()
    print(f"  Created {count} response templates")
    return count


async def seed_sample_agents(db: AsyncSession) -> int:
    """Seed sample agents for development."""
    
    agents_data = [
        {
            "email": "michael.scott@example.com",
            "name": "Michael Scott",
            "role": AgentRole.SENIOR_AGENT,
            "team": "Technical Support",
            "skills": ["technical_issue", "bug_report"],
            "languages": ["en"],
            "experience_level": 4,
            "max_load": 15,
            "status": AgentStatus.ONLINE,
            "can_handle_critical": True,
            "can_handle_vip": True
        },
        {
            "email": "pam.beesly@example.com",
            "name": "Pam Beesly",
            "role": AgentRole.AGENT,
            "team": "Billing",
            "skills": ["billing_question", "return_refund", "account_management"],
            "languages": ["en"],
            "experience_level": 3,
            "max_load": 12,
            "status": AgentStatus.ONLINE,
            "can_handle_critical": False,
            "can_handle_vip": True
        },
        {
            "email": "jim.halpert@example.com",
            "name": "Jim Halpert",
            "role": AgentRole.AGENT,
            "team": "General Support",
            "skills": ["general_inquiry", "feature_request", "complaint"],
            "languages": ["en"],
            "experience_level": 2,
            "max_load": 10,
            "status": AgentStatus.ONLINE,
            "can_handle_critical": False,
            "can_handle_vip": False
        },
        {
            "email": "sarah.connor@example.com",
            "name": "Sarah Connor",
            "role": AgentRole.TEAM_LEAD,
            "team": "Technical Support",
            "skills": ["technical_issue", "bug_report", "complaint"],
            "languages": ["en", "es"],
            "experience_level": 5,
            "max_load": 8,
            "status": AgentStatus.ONLINE,
            "can_handle_critical": True,
            "can_handle_vip": True
        }
    ]
    
    count = 0
    for agent_data in agents_data:
        existing = await db.execute(
            text(f"SELECT 1 FROM agents WHERE email = '{agent_data['email']}'")
        )
        if existing.scalar():
            continue
        
        agent = Agent(**agent_data)
        db.add(agent)
        count += 1
    
    await db.commit()
    print(f"  Created {count} sample agents")
    return count


async def seed_sample_customers(db: AsyncSession) -> int:
    """Seed sample customers for development."""
    
    customers_data = [
        {
            "email": "vip.customer@bigcorp.com",
            "name": "John Bighead",
            "company": "BigCorp Inc.",
            "tier": CustomerTier.VIP,
            "preferred_language": "en",
            "lifetime_value": 50000.0
        },
        {
            "email": "premium.user@example.com",
            "name": "Jane Doe",
            "company": "TechStartup LLC",
            "tier": CustomerTier.PREMIUM,
            "preferred_language": "en",
            "lifetime_value": 5000.0
        },
        {
            "email": "standard.user@gmail.com",
            "name": "Bob Smith",
            "tier": CustomerTier.STANDARD,
            "preferred_language": "en"
        },
        {
            "email": "free.user@hotmail.com",
            "name": "Alice Wonderland",
            "tier": CustomerTier.FREE,
            "preferred_language": "en"
        }
    ]
    
    count = 0
    for customer_data in customers_data:
        existing = await db.execute(
            text(f"SELECT 1 FROM customers WHERE email = '{customer_data['email']}'")
        )
        if existing.scalar():
            continue
        
        customer = Customer(**customer_data)
        db.add(customer)
        count += 1
    
    await db.commit()
    print(f"  Created {count} sample customers")
    return count


async def seed_sample_tickets(db: AsyncSession) -> int:
    """Seed sample tickets for development."""
    
    # Get agent and customer IDs
    agent_result = await db.execute(text("SELECT id FROM agents LIMIT 1"))
    agent_row = agent_result.first()
    agent_id = agent_row[0] if agent_row else None
    
    customer_result = await db.execute(text("SELECT id, email, name FROM customers LIMIT 4"))
    customers = customer_result.fetchall()
    
    if not customers:
        print("  No customers found, skipping ticket creation")
        return 0
    
    tickets_data = [
        {
            "content": "Your app won't open, it keeps showing 'Connection error' message. I need an urgent solution!",
            "subject": "App not opening - URGENT",
            "category": "technical_issue",
            "sentiment": "negative",
            "sentiment_score": -0.7,
            "priority": 4,
            "priority_level": "high",
            "status": TicketStatus.OPEN,
            "language": "en"
        },
        {
            "content": "There's an error on my invoice. I paid $100 last month but $200 was charged this month. Please check.",
            "subject": "Invoice Error",
            "category": "billing_question",
            "sentiment": "negative",
            "sentiment_score": -0.4,
            "priority": 3,
            "priority_level": "medium",
            "status": TicketStatus.OPEN,
            "language": "en"
        },
        {
            "content": "Could you add dark mode feature to the mobile app? It would be great for nighttime use.",
            "subject": "Feature Request: Dark Mode",
            "category": "feature_request",
            "sentiment": "positive",
            "sentiment_score": 0.5,
            "priority": 2,
            "priority_level": "low",
            "status": TicketStatus.NEW,
            "language": "en"
        },
        {
            "content": "Password reset email isn't coming. I tried 3 times but none of them arrived. I can't access my account.",
            "subject": "Password Reset Issue",
            "category": "account_management",
            "sentiment": "negative",
            "sentiment_score": -0.5,
            "priority": 4,
            "priority_level": "high",
            "status": TicketStatus.IN_PROGRESS,
            "language": "en"
        }
    ]
    
    count = 0
    for i, ticket_data in enumerate(tickets_data):
        customer = customers[i % len(customers)]
        
        ticket = Ticket(
            **ticket_data,
            customer_email=customer[1],
            customer_name=customer[2],
            customer_tier="standard",
            assigned_agent_id=agent_id,
            source="seed_script",
            is_processed=True
        )
        db.add(ticket)
        count += 1
    
    await db.commit()
    print(f"  Created {count} sample tickets")
    return count


async def main():
    """Main seed function."""
    print("=" * 50)
    print("Seeding Database")
    print("=" * 50)
    
    # Initialize database
    print("\n1. Initializing database...")
    await init_db()
    print("  Database initialized")
    
    async with AsyncSessionLocal() as db:
        # Seed data
        print("\n2. Seeding categories...")
        await seed_categories(db)
        
        print("\n3. Seeding routing rules...")
        await seed_routing_rules(db)
        
        print("\n4. Seeding response templates...")
        await seed_response_templates(db)
        
        print("\n5. Seeding sample agents...")
        await seed_sample_agents(db)
        
        print("\n6. Seeding sample customers...")
        await seed_sample_customers(db)
        
        print("\n7. Seeding sample tickets...")
        await seed_sample_tickets(db)
    
    print("\n" + "=" * 50)
    print("Database seeding completed!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
