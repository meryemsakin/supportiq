"""
AI-Powered Ticket Classification Service

Uses OpenAI GPT-4 for intelligent ticket categorization with
Turkish language support and confidence scoring.
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from openai import AsyncOpenAI
from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import redis.asyncio as redis

from src.config import settings


class ClassificationError(Exception):
    """Exception raised when classification fails."""
    pass


class TicketClassifier:
    """
    AI-powered ticket classification using OpenAI GPT-4.
    
    Features:
    - Multi-category classification with confidence scores
    - Turkish and English language support
    - Caching for repeated queries
    - Retry logic for API failures
    - Fallback to rule-based classification
    """
    
    DEFAULT_CATEGORIES = [
        "technical_issue",
        "billing_question",
        "feature_request",
        "bug_report",
        "account_management",
        "return_refund",
        "general_inquiry",
        "complaint"
    ]
    
    CATEGORY_DESCRIPTIONS = {
        "technical_issue": {
            "en": "Technical problems, system errors, and functionality issues",
            "tr": "Teknik sorunlar, sistem hataları ve işlevsellik sorunları"
        },
        "billing_question": {
            "en": "Payment, invoice, pricing, and billing inquiries",
            "tr": "Ödeme, fatura, fiyatlandırma ve faturalandırma soruları"
        },
        "feature_request": {
            "en": "Suggestions for new features or improvements",
            "tr": "Yeni özellik veya iyileştirme önerileri"
        },
        "bug_report": {
            "en": "Software bugs, defects, and unexpected behavior reports",
            "tr": "Yazılım hataları, kusurlar ve beklenmedik davranış raporları"
        },
        "account_management": {
            "en": "Account settings, password, login, and profile issues",
            "tr": "Hesap ayarları, şifre, giriş ve profil sorunları"
        },
        "return_refund": {
            "en": "Product returns, refunds, and exchange requests",
            "tr": "Ürün iadesi, geri ödeme ve değişim talepleri"
        },
        "general_inquiry": {
            "en": "General questions and information requests",
            "tr": "Genel sorular ve bilgi talepleri"
        },
        "complaint": {
            "en": "Customer complaints and negative feedback",
            "tr": "Müşteri şikayetleri ve olumsuz geri bildirimler"
        }
    }
    
    def __init__(
        self,
        categories: Optional[List[str]] = None,
        cache_enabled: bool = True,
        cache_ttl: int = 3600
    ):
        """
        Initialize the classifier.
        
        Args:
            categories: Custom categories (uses defaults if None)
            cache_enabled: Enable Redis caching
            cache_ttl: Cache TTL in seconds
        """
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.categories = categories or self.DEFAULT_CATEGORIES
        self.cache_enabled = cache_enabled and settings.redis_url
        self.cache_ttl = cache_ttl
        self._redis: Optional[redis.Redis] = None
        
        logger.info(f"TicketClassifier initialized with {len(self.categories)} categories")
    
    async def _get_redis(self) -> Optional[redis.Redis]:
        """Get Redis connection for caching."""
        if not self.cache_enabled:
            return None
        
        if self._redis is None:
            try:
                self._redis = redis.from_url(settings.redis_url)
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
                return None
        
        return self._redis
    
    async def _get_cached(self, cache_key: str) -> Optional[Dict]:
        """Get cached classification result."""
        redis_client = await self._get_redis()
        if not redis_client:
            return None
        
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
        
        return None
    
    async def _set_cached(self, cache_key: str, result: Dict) -> None:
        """Cache classification result."""
        redis_client = await self._get_redis()
        if not redis_client:
            return
        
        try:
            await redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(result)
            )
        except Exception as e:
            logger.warning(f"Cache write error: {e}")
    
    def _build_system_prompt(self, language: str = "en") -> str:
        """Build system prompt for classification."""
        
        category_list = []
        for cat in self.categories:
            desc = self.CATEGORY_DESCRIPTIONS.get(cat, {})
            desc_text = desc.get(language, desc.get("en", cat))
            category_list.append(f"- {cat}: {desc_text}")
        
        categories_text = "\n".join(category_list)
        
        # Use unified English prompt for all languages (AI can process any language input with English instructions)
        return f"""You are an experienced customer support analyst and ticket categorization expert with years of experience analyzing customer issues.

## TASK
Analyze customer support requests, categorize them, and provide action recommendations.

## CATEGORIES
{categories_text}

## ANALYSIS STEPS (Think step by step)

### Step 1: Initial Reading
- What is the customer's main complaint/request?
- What emotional state are they in? (calm, worried, angry, hopeful)
- What is the urgency level?

### Step 2: Deep Analysis
- How many different requests/issues are in the message? (Multi-intent detection)
- Are there hidden/implied issues?
- What does the customer expect? (solution, information, apology, compensation)

### Step 3: Categorization
- What is the primary category?
- Are there secondary categories?
- Why this category? (reasoning)

### Step 4: Risk Assessment
- Is there churn risk?
- Is escalation needed?
- Are there VIP/Premium customer signals?

## EXAMPLE CASES

### Example 1: Complex Technical Issue
Input: "I haven't been able to log in for 3 days, password reset doesn't work either, and there's no live support. I'm paying for premium membership but can't get any service!"

Analysis:
- Main issue: Cannot login (technical_issue)
- Secondary issue: Password reset problem (account_management)
- Hidden issue: Premium membership dissatisfaction (complaint)
- Emotional state: Angry and disappointed
- Risk: High churn risk, VIP customer
- Action: Priority, coordinated technical + account team solution

Output: primary_category: "technical_issue", confidence: 0.85, secondary: ["account_management", "complaint"]

### Example 2: Ambiguous Request
Input: "Hello, I'd like some information"

Analysis:
- Main issue: Unclear
- Action: Request details
- Category: general_inquiry (low confidence)

Output: primary_category: "general_inquiry", confidence: 0.4

## IMPORTANT RULES
1. Understand nuances (slang, implied expressions, anger beneath politeness)
2. If there are multiple issues, detect all of them
3. Catch what the customer implies but doesn't say
4. If confidence is below 0.6, indicate uncertainty
5. Always respond in valid JSON format
6. Evaluate risk level (low, medium, high)
7. Provide recommended action"""
    
    def _build_user_prompt(self, text: str, language: str = "en") -> str:
        """Build user prompt for classification."""
        
        # Use unified English prompt for all languages
        return f"""Analyze the following customer support request:

---
{text}
---

Think step by step and respond in JSON format:
{{
    "thinking": "Step by step thinking process...",
    "primary_category": "main_category",
    "secondary_categories": ["secondary_category1", "secondary_category2"],
    "confidence": 0.0-1.0,
    "all_categories": {{
        "technical_issue": 0.0-1.0,
        "billing_question": 0.0-1.0,
        "feature_request": 0.0-1.0,
        "bug_report": 0.0-1.0,
        "account_management": 0.0-1.0,
        "return_refund": 0.0-1.0,
        "general_inquiry": 0.0-1.0,
        "complaint": 0.0-1.0
    }},
    "customer_intent": "What the customer actually expects",
    "emotional_state": "calm|worried|angry|hopeful|disappointed",
    "urgency": "low|medium|high|critical",
    "risk_level": "low|medium|high",
    "churn_risk": true/false,
    "escalation_needed": true/false,
    "hidden_issues": ["detected hidden issues"],
    "recommended_action": "Recommended action",
    "reasoning": "Why this categorization was made - detailed explanation"
}}"""
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    async def _call_openai(
        self,
        system_prompt: str,
        user_prompt: str
    ) -> Dict:
        """Call OpenAI API with retry logic."""
        
        response = await self.client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=2000
        )
        
        content = response.choices[0].message.content
        return json.loads(content)
    
    def _rule_based_fallback(self, text: str) -> Dict:
        """
        Fallback rule-based classification when AI is unavailable.
        """
        text_lower = text.lower()
        
        # Keyword mappings
        keyword_map = {
            "technical_issue": [
                "error", "failure", "not working", "broken", "crash",
                "bug", "issue", "problem", "glitch", "defective"
            ],
            "billing_question": [
                "invoice", "payment", "charge", "price", "cost", 
                "bill", "receipt", "subscription", "fee", "refund"
            ],
            "feature_request": [
                "feature", "suggestion", "add", "request", "improve",
                "enhancement", "idea", "would be nice"
            ],
            "bug_report": [
                "bug", "defect", "flaw", "wrong", "unexpected",
                "error", "glitch", "malfunction"
            ],
            "account_management": [
                "account", "password", "login", "profile", "access",
                "register", "signup", "signin", "auth"
            ],
            "return_refund": [
                "return", "refund", "exchange", "cancel", "money back",
                "reimbursement"
            ],
            "complaint": [
                "complaint", "unhappy", "terrible", "bad", "worst",
                "disappointed", "awful", "horrible", "upset", "angry"
            ]
        }
        
        scores = {}
        for category, keywords in keyword_map.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            scores[category] = min(score * 0.2, 0.9)  # Cap at 0.9
        
        # Default to general_inquiry
        scores["general_inquiry"] = 0.3
        
        # Find best match
        best_category = max(scores, key=scores.get)
        best_score = scores[best_category]
        
        # Normalize scores
        total = sum(scores.values()) or 1
        normalized_scores = {k: round(v / total, 3) for k, v in scores.items()}
        
        return {
            "primary_category": best_category,
            "confidence": round(best_score, 3),
            "all_categories": normalized_scores,
            "reasoning": "Rule-based classification (AI fallback)",
            "method": "rule_based"
        }
    
    async def classify(
        self,
        text: str,
        language: str = "en",
        use_cache: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict:
        """
        Classify a ticket into categories.
        
        Args:
            text: Ticket content to classify
            language: Language code (tr, en)
            use_cache: Whether to use caching
            metadata: Additional context for classification
            
        Returns:
            Dict with classification results:
            {
                "primary_category": str,
                "confidence": float,
                "all_categories": Dict[str, float],
                "reasoning": str,
                "method": str  # "ai" or "rule_based"
            }
        """
        
        if not text or not text.strip():
            return {
                "primary_category": "general_inquiry",
                "confidence": 0.0,
                "all_categories": {"general_inquiry": 1.0},
                "reasoning": "Empty ticket content",
                "method": "default"
            }
        
        # Normalize text
        text = text.strip()[:5000]  # Limit length
        
        # Check cache
        if use_cache and self.cache_enabled:
            import hashlib
            cache_key = f"classify:{hashlib.md5(text.encode()).hexdigest()}"
            cached = await self._get_cached(cache_key)
            if cached:
                logger.debug(f"Cache hit for classification")
                cached["method"] = "ai_cached"
                return cached
        
        # Try AI classification
        try:
            system_prompt = self._build_system_prompt(language)
            user_prompt = self._build_user_prompt(text, language)
            
            result = await self._call_openai(system_prompt, user_prompt)
            
            # Validate result
            if "primary_category" not in result:
                raise ClassificationError("Invalid AI response: missing primary_category")
            
            if result["primary_category"] not in self.categories:
                logger.warning(f"AI returned unknown category: {result['primary_category']}")
                result["primary_category"] = "general_inquiry"
            
            result["method"] = "ai"
            
            # Cache result
            if use_cache and self.cache_enabled:
                await self._set_cached(cache_key, result)
            
            logger.info(
                f"Classified ticket as '{result['primary_category']}' "
                f"with confidence {result.get('confidence', 'N/A')}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"AI classification failed: {e}")
            
            # Fallback to rule-based
            result = self._rule_based_fallback(text)
            logger.info(f"Using rule-based fallback: {result['primary_category']}")
            
            return result
    
    async def classify_batch(
        self,
        texts: List[str],
        language: str = "en"
    ) -> List[Dict]:
        """
        Classify multiple tickets.
        
        Args:
            texts: List of ticket contents
            language: Language code
            
        Returns:
            List of classification results
        """
        import asyncio
        
        tasks = [
            self.classify(text, language)
            for text in texts
        ]
        
        return await asyncio.gather(*tasks)
    
    async def close(self) -> None:
        """Close connections."""
        if self._redis:
            await self._redis.close()


# Singleton instance
_classifier: Optional[TicketClassifier] = None


def get_classifier() -> TicketClassifier:
    """Get or create classifier instance."""
    global _classifier
    if _classifier is None:
        _classifier = TicketClassifier()
    return _classifier
