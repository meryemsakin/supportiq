"""
Priority Scoring Service

Calculates ticket priority based on multiple factors including
keywords, sentiment, customer tier, and category.
"""

import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from loguru import logger


class PriorityLevel(str, Enum):
    """Priority level names."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"


@dataclass
class PriorityFactor:
    """Represents a factor affecting priority."""
    name: str
    weight: int
    description: str


class PriorityScorer:
    """
    Calculate ticket priority (1-5) based on multiple factors.
    
    Factors:
    - Urgent keywords (English and Turkish)
    - High-priority keywords
    - Sentiment analysis (negative/angry = higher priority)
    - Customer tier (VIP, premium, standard, free)
    - Category criticality
    - SLA considerations
    - Custom rules
    """
    
    # Urgent keywords (highest priority boost)
    URGENT_KEYWORDS = {
        "en": [
            "urgent", "asap", "immediately", "critical", "emergency",
            "right now", "can't wait", "deadline", "down", "outage"
        ],
        "tr": [
            "acil", "hemen", "kritik", "acilen", "ivedi", "derhal",
            "bekleyemez", "şimdi", "çöktü", "erişilemiyor"
        ]
    }
    
    # High priority keywords
    HIGH_KEYWORDS = {
        "en": [
            "not working", "broken", "error", "can't access", "failed",
            "stuck", "blocked", "crash", "lost", "missing", "deleted"
        ],
        "tr": [
            "çalışmıyor", "bozuk", "hata", "erişemiyorum", "başarısız",
            "takıldı", "engellendi", "çöktü", "kayboldu", "silindi"
        ]
    }
    
    # Medium priority keywords
    MEDIUM_KEYWORDS = {
        "en": [
            "issue", "problem", "help", "question", "confused",
            "doesn't work", "slow", "delay"
        ],
        "tr": [
            "sorun", "problem", "yardım", "soru", "anlamadım",
            "çalışmıyor", "yavaş", "gecikme"
        ]
    }
    
    # Categories with inherent priority boost
    CRITICAL_CATEGORIES = {
        "technical_issue": 1,
        "bug_report": 1,
        "complaint": 2,
    }
    
    LOW_PRIORITY_CATEGORIES = {
        "feature_request": -1,
        "general_inquiry": 0,
    }
    
    # Customer tier boosts
    TIER_BOOSTS = {
        "enterprise": 2,
        "vip": 2,
        "premium": 1,
        "standard": 0,
        "free": -1,
    }
    
    # Priority level mapping
    LEVEL_MAP = {
        5: PriorityLevel.CRITICAL,
        4: PriorityLevel.HIGH,
        3: PriorityLevel.MEDIUM,
        2: PriorityLevel.LOW,
        1: PriorityLevel.MINIMAL,
    }
    
    def __init__(self, custom_rules: Optional[List[Dict]] = None):
        """
        Initialize priority scorer.
        
        Args:
            custom_rules: List of custom priority rules
        """
        self.custom_rules = custom_rules or []
        logger.info("PriorityScorer initialized")
    
    def _check_keywords(
        self,
        text: str,
        keywords: Dict[str, List[str]],
        language: str = "en"
    ) -> List[str]:
        """Check for keywords in text."""
        
        text_lower = text.lower()
        found = []
        
        # Check both languages
        for lang in ["en", "tr"]:
            for keyword in keywords.get(lang, []):
                if keyword in text_lower:
                    found.append(keyword)
        
        return found
    
    def _analyze_text_patterns(self, text: str) -> Dict[str, Any]:
        """Analyze text for priority-affecting patterns."""
        
        patterns = {
            "caps_ratio": 0.0,
            "exclamation_count": 0,
            "question_marks": 0,
            "word_count": 0,
            "has_deadline_mention": False,
            "has_money_mention": False,
        }
        
        if not text:
            return patterns
        
        # Caps ratio (shouting)
        alpha_chars = [c for c in text if c.isalpha()]
        if alpha_chars:
            patterns["caps_ratio"] = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
        
        # Punctuation
        patterns["exclamation_count"] = text.count("!")
        patterns["question_marks"] = text.count("?")
        patterns["word_count"] = len(text.split())
        
        # Deadline mentions
        deadline_patterns = [
            r"deadline", r"due date", r"by \w+ \d+", r"until",
            r"son tarih", r"tarihe kadar", r"süre"
        ]
        patterns["has_deadline_mention"] = any(
            re.search(p, text, re.IGNORECASE) for p in deadline_patterns
        )
        
        # Money mentions
        money_patterns = [
            r"\$\d+", r"€\d+", r"£\d+", r"\d+\s*(TL|tl|lira|dolar|euro)",
            r"para", r"ücret", r"ödeme", r"fatura"
        ]
        patterns["has_money_mention"] = any(
            re.search(p, text, re.IGNORECASE) for p in money_patterns
        )
        
        return patterns
    
    def _apply_custom_rules(
        self,
        text: str,
        metadata: Dict[str, Any]
    ) -> List[PriorityFactor]:
        """Apply custom priority rules."""
        
        factors = []
        
        for rule in self.custom_rules:
            rule_type = rule.get("type")
            
            if rule_type == "keyword":
                keywords = rule.get("keywords", [])
                if any(kw.lower() in text.lower() for kw in keywords):
                    factors.append(PriorityFactor(
                        name=rule.get("name", "custom_keyword"),
                        weight=rule.get("weight", 1),
                        description=rule.get("description", "Custom keyword match")
                    ))
            
            elif rule_type == "customer_field":
                field = rule.get("field")
                value = rule.get("value")
                if metadata.get(field) == value:
                    factors.append(PriorityFactor(
                        name=rule.get("name", "custom_field"),
                        weight=rule.get("weight", 1),
                        description=rule.get("description", "Custom field match")
                    ))
        
        return factors
    
    def calculate(
        self,
        text: str,
        sentiment: Optional[str] = None,
        sentiment_score: Optional[float] = None,
        anger_level: Optional[float] = None,
        customer_tier: str = "standard",
        category: Optional[str] = None,
        language: str = "en",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculate priority score for a ticket.
        
        Args:
            text: Ticket content
            sentiment: Sentiment label (positive, neutral, negative, angry)
            sentiment_score: Sentiment score (-1 to 1)
            anger_level: Anger level (0 to 1)
            customer_tier: Customer tier (enterprise, vip, premium, standard, free)
            category: Ticket category
            language: Language code
            metadata: Additional metadata for custom rules
            
        Returns:
            Dict with priority calculation results:
            {
                "score": int,  # 1-5
                "level": str,  # critical, high, medium, low, minimal
                "factors": List[str],
                "factor_details": List[Dict],
                "breakdown": Dict
            }
        """
        
        base_score = 3  # Start at medium
        factors: List[PriorityFactor] = []
        metadata = metadata or {}
        
        # 1. Check urgent keywords
        urgent_found = self._check_keywords(text, self.URGENT_KEYWORDS, language)
        if urgent_found:
            factors.append(PriorityFactor(
                name="urgent_keyword",
                weight=2,
                description=f"Urgent keywords detected: {', '.join(urgent_found[:3])}"
            ))
        
        # 2. Check high priority keywords
        high_found = self._check_keywords(text, self.HIGH_KEYWORDS, language)
        if high_found and not urgent_found:
            factors.append(PriorityFactor(
                name="high_priority_keyword",
                weight=1,
                description=f"High priority keywords: {', '.join(high_found[:3])}"
            ))
        
        # 3. Sentiment impact
        if sentiment in ["negative", "angry"]:
            weight = 2 if sentiment == "angry" else 1
            factors.append(PriorityFactor(
                name=f"sentiment_{sentiment}",
                weight=weight,
                description=f"Customer sentiment is {sentiment}"
            ))
        
        # 4. High anger level
        if anger_level is not None and anger_level >= 0.7:
            factors.append(PriorityFactor(
                name="high_anger",
                weight=1,
                description=f"High anger level detected ({anger_level:.2f})"
            ))
        
        # 5. Customer tier
        tier_boost = self.TIER_BOOSTS.get(customer_tier.lower(), 0)
        if tier_boost != 0:
            factors.append(PriorityFactor(
                name=f"customer_tier_{customer_tier}",
                weight=tier_boost,
                description=f"Customer tier: {customer_tier}"
            ))
        
        # 6. Category impact
        if category:
            if category in self.CRITICAL_CATEGORIES:
                factors.append(PriorityFactor(
                    name=f"critical_category_{category}",
                    weight=self.CRITICAL_CATEGORIES[category],
                    description=f"Critical category: {category}"
                ))
            elif category in self.LOW_PRIORITY_CATEGORIES:
                factors.append(PriorityFactor(
                    name=f"low_priority_category_{category}",
                    weight=self.LOW_PRIORITY_CATEGORIES[category],
                    description=f"Low priority category: {category}"
                ))
        
        # 7. Text pattern analysis
        patterns = self._analyze_text_patterns(text)
        
        # High caps ratio (shouting)
        if patterns["caps_ratio"] > 0.5:
            factors.append(PriorityFactor(
                name="excessive_caps",
                weight=1,
                description="Excessive use of capital letters"
            ))
        
        # Multiple exclamation marks
        if patterns["exclamation_count"] >= 3:
            factors.append(PriorityFactor(
                name="multiple_exclamations",
                weight=1,
                description=f"Multiple exclamation marks ({patterns['exclamation_count']})"
            ))
        
        # Deadline mention
        if patterns["has_deadline_mention"]:
            factors.append(PriorityFactor(
                name="deadline_mention",
                weight=1,
                description="Deadline mentioned in text"
            ))
        
        # 8. Apply custom rules
        custom_factors = self._apply_custom_rules(text, metadata)
        factors.extend(custom_factors)
        
        # Calculate final score
        total_weight = sum(f.weight for f in factors)
        final_score = base_score + total_weight
        
        # Clamp to 1-5
        final_score = max(1, min(5, final_score))
        
        # Get level
        level = self.LEVEL_MAP.get(final_score, PriorityLevel.MEDIUM)
        
        # Build response
        result = {
            "score": final_score,
            "level": level.value,
            "factors": [f.name for f in factors],
            "factor_details": [
                {
                    "name": f.name,
                    "weight": f.weight,
                    "description": f.description
                }
                for f in factors
            ],
            "breakdown": {
                "base_score": base_score,
                "total_adjustment": total_weight,
                "final_score": final_score,
                "text_patterns": patterns
            }
        }
        
        logger.info(
            f"Priority calculated: {final_score} ({level.value}) "
            f"with {len(factors)} factors"
        )
        
        return result
    
    def recalculate_with_override(
        self,
        current_score: int,
        override_factors: List[str],
        direction: str = "up"
    ) -> Dict[str, Any]:
        """
        Recalculate priority with manual override factors.
        
        Args:
            current_score: Current priority score
            override_factors: List of manual override reasons
            direction: "up" or "down"
            
        Returns:
            Updated priority calculation
        """
        
        adjustment = 1 if direction == "up" else -1
        new_score = max(1, min(5, current_score + adjustment))
        
        return {
            "score": new_score,
            "level": self.LEVEL_MAP.get(new_score, PriorityLevel.MEDIUM).value,
            "factors": override_factors,
            "factor_details": [
                {
                    "name": "manual_override",
                    "weight": adjustment,
                    "description": f"Manual {direction} adjustment: {', '.join(override_factors)}"
                }
            ],
            "breakdown": {
                "previous_score": current_score,
                "adjustment": adjustment,
                "final_score": new_score,
                "override": True
            }
        }


# Singleton instance
_scorer: Optional[PriorityScorer] = None


def get_priority_scorer(custom_rules: Optional[List[Dict]] = None) -> PriorityScorer:
    """Get or create priority scorer instance."""
    global _scorer
    if _scorer is None or custom_rules is not None:
        _scorer = PriorityScorer(custom_rules)
    return _scorer
