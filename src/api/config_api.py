"""
Configuration API Endpoints

Manage categories, routing rules, and system settings.
"""

from typing import Optional, List
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from loguru import logger

from src.database import get_async_db
from src.models.category import Category, DEFAULT_CATEGORIES
from src.models.rule import RoutingRule, RuleType, RuleAction, DEFAULT_ROUTING_RULES
from src.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryListResponse,
)

router = APIRouter()


# =============================================================================
# Categories
# =============================================================================

@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    db: AsyncSession = Depends(get_async_db)
) -> CategoryResponse:
    """Create a new ticket category."""
    
    # Check if name already exists
    result = await db.execute(
        select(Category).where(Category.name == category_data.name)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category '{category_data.name}' already exists"
        )
    
    category = Category(
        name=category_data.name,
        display_name=category_data.display_name,
        display_name_tr=category_data.display_name_tr,
        description=category_data.description,
        description_tr=category_data.description_tr,
        icon=category_data.icon,
        color=category_data.color,
        priority_boost=category_data.priority_boost,
        sla_first_response_hours=category_data.sla_first_response_hours,
        sla_resolution_hours=category_data.sla_resolution_hours,
        keywords=category_data.keywords,
        keywords_tr=category_data.keywords_tr,
        negative_keywords=category_data.negative_keywords,
        default_team=category_data.default_team,
        requires_senior=category_data.requires_senior,
        auto_assign=category_data.auto_assign,
        examples=category_data.examples,
        is_active=True
    )
    
    db.add(category)
    await db.commit()
    await db.refresh(category)
    
    logger.info(f"Created category: {category.name}")
    
    return CategoryResponse.model_validate(category)


@router.get("/categories", response_model=CategoryListResponse)
async def list_categories(
    include_inactive: bool = Query(False),
    db: AsyncSession = Depends(get_async_db)
) -> CategoryListResponse:
    """List all categories."""
    
    query = select(Category)
    
    if not include_inactive:
        query = query.where(Category.is_active == True)
    
    query = query.order_by(Category.sort_order, Category.name)
    
    result = await db.execute(query)
    categories = result.scalars().all()
    
    return CategoryListResponse(
        items=[CategoryResponse.model_validate(c) for c in categories],
        total=len(categories)
    )


@router.get("/categories/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_async_db)
) -> CategoryResponse:
    """Get category by ID."""
    
    category = await db.get(Category, category_id)
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category {category_id} not found"
        )
    
    return CategoryResponse.model_validate(category)


@router.patch("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: UUID,
    category_data: CategoryUpdate,
    db: AsyncSession = Depends(get_async_db)
) -> CategoryResponse:
    """Update category."""
    
    category = await db.get(Category, category_id)
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category {category_id} not found"
        )
    
    update_data = category_data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(category, field, value)
    
    category.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(category)
    
    logger.info(f"Updated category: {category.name}")
    
    return CategoryResponse.model_validate(category)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_async_db)
):
    """Delete category (soft delete)."""
    
    category = await db.get(Category, category_id)
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category {category_id} not found"
        )
    
    category.is_active = False
    category.updated_at = datetime.utcnow()
    
    await db.commit()
    
    logger.info(f"Deactivated category: {category.name}")


@router.post("/categories/seed", status_code=status.HTTP_201_CREATED)
async def seed_default_categories(
    db: AsyncSession = Depends(get_async_db)
) -> dict:
    """Seed database with default categories."""
    
    created = 0
    skipped = 0
    
    for cat_data in DEFAULT_CATEGORIES:
        # Check if exists
        result = await db.execute(
            select(Category).where(Category.name == cat_data["name"])
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            skipped += 1
            continue
        
        category = Category(**cat_data)
        db.add(category)
        created += 1
    
    await db.commit()
    
    logger.info(f"Seeded categories: {created} created, {skipped} skipped")
    
    return {
        "created": created,
        "skipped": skipped,
        "total": len(DEFAULT_CATEGORIES)
    }


# =============================================================================
# Routing Rules
# =============================================================================

@router.get("/routing-rules")
async def list_routing_rules(
    include_inactive: bool = Query(False),
    rule_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_db)
) -> dict:
    """List all routing rules."""
    
    query = select(RoutingRule)
    
    if not include_inactive:
        query = query.where(RoutingRule.is_active == True)
    
    if rule_type:
        query = query.where(RoutingRule.rule_type == rule_type)
    
    query = query.order_by(RoutingRule.priority.desc())
    
    result = await db.execute(query)
    rules = result.scalars().all()
    
    return {
        "items": [
            {
                "id": str(r.id),
                "name": r.name,
                "description": r.description,
                "rule_type": r.rule_type.value if r.rule_type else None,
                "conditions": r.conditions,
                "action": r.action.value if r.action else None,
                "action_params": r.action_params,
                "priority": r.priority,
                "is_active": r.is_active,
                "times_triggered": r.times_triggered,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in rules
        ],
        "total": len(rules)
    }


@router.post("/routing-rules", status_code=status.HTTP_201_CREATED)
async def create_routing_rule(
    rule_data: dict,
    db: AsyncSession = Depends(get_async_db)
) -> dict:
    """Create a new routing rule."""
    
    try:
        rule = RoutingRule(
            name=rule_data["name"],
            description=rule_data.get("description"),
            rule_type=RuleType(rule_data["rule_type"]),
            conditions=rule_data["conditions"],
            action=RuleAction(rule_data["action"]),
            action_params=rule_data.get("action_params", {}),
            priority=rule_data.get("priority", 0),
            is_active=rule_data.get("is_active", True),
            is_exclusive=rule_data.get("is_exclusive", True),
            applies_to_sources=rule_data.get("applies_to_sources"),
            applies_to_categories=rule_data.get("applies_to_categories"),
            created_by=rule_data.get("created_by")
        )
        
        db.add(rule)
        await db.commit()
        await db.refresh(rule)
        
        logger.info(f"Created routing rule: {rule.name}")
        
        return {
            "id": str(rule.id),
            "name": rule.name,
            "status": "created"
        }
        
    except (ValueError, KeyError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid rule data: {str(e)}"
        )


@router.patch("/routing-rules/{rule_id}")
async def update_routing_rule(
    rule_id: UUID,
    rule_data: dict,
    db: AsyncSession = Depends(get_async_db)
) -> dict:
    """Update a routing rule."""
    
    rule = await db.get(RoutingRule, rule_id)
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found"
        )
    
    # Update fields
    for field in ["name", "description", "conditions", "action_params", "priority", "is_active", "is_exclusive"]:
        if field in rule_data:
            setattr(rule, field, rule_data[field])
    
    if "rule_type" in rule_data:
        rule.rule_type = RuleType(rule_data["rule_type"])
    
    if "action" in rule_data:
        rule.action = RuleAction(rule_data["action"])
    
    rule.updated_at = datetime.utcnow()
    
    await db.commit()
    
    logger.info(f"Updated routing rule: {rule.name}")
    
    return {"id": str(rule_id), "status": "updated"}


@router.delete("/routing-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_routing_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_async_db)
):
    """Delete a routing rule."""
    
    rule = await db.get(RoutingRule, rule_id)
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found"
        )
    
    await db.delete(rule)
    await db.commit()
    
    logger.info(f"Deleted routing rule: {rule.name}")


@router.post("/routing-rules/seed", status_code=status.HTTP_201_CREATED)
async def seed_default_rules(
    db: AsyncSession = Depends(get_async_db)
) -> dict:
    """Seed database with default routing rules."""
    
    created = 0
    skipped = 0
    
    for rule_data in DEFAULT_ROUTING_RULES:
        # Check if exists by name
        result = await db.execute(
            select(RoutingRule).where(RoutingRule.name == rule_data["name"])
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            skipped += 1
            continue
        
        rule = RoutingRule(**rule_data)
        db.add(rule)
        created += 1
    
    await db.commit()
    
    logger.info(f"Seeded routing rules: {created} created, {skipped} skipped")
    
    return {
        "created": created,
        "skipped": skipped,
        "total": len(DEFAULT_ROUTING_RULES)
    }


# =============================================================================
# Knowledge Base
# =============================================================================

from src.services.rag import knowledge_base

SAMPLE_FAQS = [
    {
        "faq_id": "faq_warranty",
        "question": "What is the warranty period for your products?",
        "answer": "All our products are covered by a 2-year manufacturer warranty. Free repair or replacement is provided for malfunctions caused by production defects during the warranty period. Paid service is available for situations outside the warranty coverage.",
        "category": "general_inquiry",
        "tags": ["warranty", "period", "duration"]
    },
    {
        "faq_id": "faq_refund",
        "question": "What are the return and exchange conditions?",
        "answer": "You can return our products within 14 days without any reason. For a return, the product must be unused, in its original packaging, and with its invoice. After submitting your return request to customer service, you can send it via courier. The refund amount will be deposited into your account within 5-7 business days.",
        "category": "return_refund",
        "tags": ["return", "exchange", "refund", "policy"]
    },
    {
        "faq_id": "faq_shipping",
        "question": "When will my order arrive?",
        "answer": "Your orders are usually delivered within 2-4 business days. Deliveries within the city take 1-2 days, while intercity deliveries take 2-4 days. Your tracking number will be sent via SMS and email after the order is confirmed.",
        "category": "general_inquiry",
        "tags": ["shipping", "delivery", "tracking"]
    },
    {
        "faq_id": "faq_payment",
        "question": "Which payment methods do you accept?",
        "answer": "We accept credit cards, debit cards, bank transfers, and cash on delivery. We offer 9 installments with credit cards. Thanks to our secure payment infrastructure, all your transactions are protected with SSL encryption.",
        "category": "billing_question",
        "tags": ["payment", "methods", "installment", "credit card"]
    },
    {
        "faq_id": "faq_password",
        "question": "I forgot my password, how can I reset it?",
        "answer": "You can send a password reset link to your registered email address by clicking the 'Forgot Password' link on the login page. The link is valid for 24 hours. If you don't receive the email, check your spam folder or contact customer service.",
        "category": "account_management",
        "tags": ["password", "reset", "account", "login"]
    },
    {
        "faq_id": "faq_cancel_order",
        "question": "Can I cancel my order?",
        "answer": "You can cancel orders that haven't been shipped yet. You can submit your cancellation request from the 'My Orders' section in your account or by calling our customer service. The return procedure applies to orders that have been shipped.",
        "category": "return_refund",
        "tags": ["cancel", "order", "cancellation"]
    },
    {
        "faq_id": "faq_technical_support",
        "question": "How can I get technical support?",
        "answer": "For technical support, you can call our line at 0850 XXX XX XX between 09:00-18:00 Monday-Friday. You can also reach us by sending an email to support@company.com or using the live support button on our website.",
        "category": "technical_issue",
        "tags": ["technical", "support", "help", "contact"]
    },
    {
        "faq_id": "faq_complaint",
        "question": "Where can I submit my complaint?",
        "answer": "You can submit your complaints to complaints@company.com. All complaints are reviewed within 24 hours and you will be contacted within 48 hours. For unresolved issues, you can call 0850 YYY YY YY to contact upper management.",
        "category": "complaint",
        "tags": ["complaint", "feedback", "report"]
    }
]


@router.post("/knowledge-base/seed")
async def seed_knowledge_base():
    """Seed knowledge base with sample FAQs."""
    
    await knowledge_base.initialize()
    
    added = 0
    skipped = 0
    
    for faq in SAMPLE_FAQS:
        try:
            success = await knowledge_base.add_faq(
                faq_id=faq["faq_id"],
                question=faq["question"],
                answer=faq["answer"],
                category=faq.get("category"),
                tags=faq.get("tags", [])
            )
            if success:
                added += 1
            else:
                skipped += 1
        except Exception as e:
            logger.warning(f"Failed to add FAQ {faq['faq_id']}: {e}")
            skipped += 1
    
    logger.info(f"Seeded knowledge base: {added} added, {skipped} skipped")
    
    return {
        "added": added,
        "skipped": skipped,
        "total": len(SAMPLE_FAQS)
    }


@router.get("/knowledge-base/stats")
async def get_knowledge_base_stats():
    """Get knowledge base statistics."""
    
    await knowledge_base.initialize()
    return await knowledge_base.get_stats()
