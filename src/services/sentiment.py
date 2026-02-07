"""
Sentiment Analysis Service

Analyzes customer sentiment using OpenAI and HuggingFace models
with special support for Turkish language.
"""

import json
from typing import Dict, Optional, List
from enum import Enum

from openai import AsyncOpenAI
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings


class Sentiment(str, Enum):
    """Sentiment classifications."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    ANGRY = "angry"


class SentimentAnalyzer:
    """
    Multi-model sentiment analysis with Turkish support.
    
    Features:
    - OpenAI GPT-4 for nuanced analysis
    - HuggingFace transformers fallback
    - Anger detection
    - Customer satisfaction prediction
    - Turkish language optimization
    """
    
    # Turkish sentiment indicators
    POSITIVE_TR = [
        "teşekkür", "memnun", "harika", "güzel", "mükemmel", "süper",
        "çok iyi", "başarılı", "mutlu", "sevindim", "beğendim", "muhteşem"
    ]
    
    NEGATIVE_TR = [
        "sorun", "problem", "hata", "kötü", "berbat", "rezalet",
        "memnuniyetsiz", "mutsuz", "hayal kırıklığı", "üzgün", "kızgın"
    ]
    
    ANGRY_TR = [
        "rezalet", "skandal", "kabul edilemez", "saçmalık", "utanç",
        "inanılmaz", "dava", "şikayet", "berbat", "felaket", "çok kızgın"
    ]
    
    # English sentiment indicators
    POSITIVE_EN = [
        "thank", "thanks", "great", "excellent", "wonderful", "happy",
        "satisfied", "love", "amazing", "perfect", "awesome"
    ]
    
    NEGATIVE_EN = [
        "problem", "issue", "bad", "terrible", "awful", "disappointed",
        "unhappy", "frustrated", "annoyed", "upset", "wrong"
    ]
    
    ANGRY_EN = [
        "unacceptable", "outrageous", "ridiculous", "furious", "lawsuit",
        "complaint", "worst", "hate", "disgusting", "horrible"
    ]
    
    def __init__(self, use_huggingface: bool = False):
        """
        Initialize sentiment analyzer.
        
        Args:
            use_huggingface: Use HuggingFace models (requires GPU)
        """
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.use_huggingface = use_huggingface
        self._hf_model_tr = None
        self._hf_model_en = None
        
        logger.info("SentimentAnalyzer initialized")
    
    def _load_huggingface_models(self):
        """Lazy load HuggingFace models."""
        if not self.use_huggingface:
            return
        
        try:
            from transformers import pipeline
            
            if self._hf_model_tr is None:
                self._hf_model_tr = pipeline(
                    "sentiment-analysis",
                    model=settings.sentiment_model_tr
                )
            
            if self._hf_model_en is None:
                self._hf_model_en = pipeline(
                    "sentiment-analysis",
                    model=settings.sentiment_model_en
                )
                
        except Exception as e:
            logger.warning(f"Failed to load HuggingFace models: {e}")
            self.use_huggingface = False
    
    def _build_prompt(self, text: str, language: str = "en") -> tuple:
        """Build prompts for sentiment analysis."""
        

        system = """You are a sentiment analysis and customer psychology expert. You analyze emotional nuances in customer support messages.

## YOUR EXPERTISE
- Understanding linguistic subtleties (slang, idioms, cultural expressions)
- Detecting hidden emotions in written text
- Recognizing customer behavior patterns
- Foreseeing crisis potential

## ANALYSIS FRAMEWORK

### 1. Surface Sentiment Analysis
- What emotions are explicitly expressed?
- What emotions do the words carry?

### 2. Deep Sentiment Analysis
- What's between the lines?
- What is the customer actually feeling?
- Is there anger beneath the "politeness mask"?

### 3. Behavioral Cues
- ALL CAPS usage (shouting)
- Multiple exclamation marks (!!!!) (intense emotion)
- Short, choppy sentences (irritation)
- Long, detailed explanation (disappointment)
- Threatening expressions ("I'll sue", "I'll post on social media")

### 4. Crisis Indicators
- "Lawsuit", "lawyer", "legal" words
- Social media threats ("Twitter", "Instagram")
- "Last time", "never again" expressions
- Competitor mentions
- Upper management requests

## EXAMPLE ANALYSES

### Example 1: Hidden Anger
Input: "I understand, you must be very busy. I've only been waiting for 3 days, no big deal."
Analysis: Appears understanding on the surface BUT is passive aggressive. The sarcastic tone in "must be", "only", "no big deal" masks anger.
Result: sentiment: "negative", anger_level: 0.6, hidden_anger: true

### Example 2: Genuine Thanks vs Backhanded Thanks  
Input 1: "Thank you so much, my problem was solved!"
Analysis: Genuine satisfaction, exclamation mark is positive.
Result: sentiment: "positive", score: 0.9

Input 2: "Thanks, it was finally resolved after 2 weeks."
Analysis: Backhanded thanks. "finally", "2 weeks" shows frustration with the delay.
Result: sentiment: "neutral" (surface) but underlying_sentiment: "negative"

### Example 3: Threat Detection
Input: "This is my last warning, I'll post on social media, I'll file a consumer complaint"
Analysis: Contains explicit threats, high customer loss and reputation risk.
Result: sentiment: "angry", anger_level: 0.95, threat_detected: true, crisis_potential: "high"

## OUTPUT FORMAT
Provide detailed analysis and return as JSON."""

        user = f"""Analyze the following customer message in depth:

---
{text}
---

Respond in detailed JSON format:
{{
    "sentiment": "positive|neutral|negative|angry",
    "score": -1.0 to 1.0,
    "confidence": 0.0 to 1.0,
    "anger_level": 0.0 to 1.0,
    "satisfaction_prediction": 1 to 5,
    "surface_sentiment": "Surface emotion",
    "underlying_sentiment": "Real/hidden emotion (if any)",
    "hidden_anger": true/false,
    "passive_aggressive": true/false,
    "threat_detected": true/false,
    "crisis_potential": "low|medium|high",
    "emotional_intensity": 0.0 to 1.0,
    "frustration_level": 0.0 to 1.0,
    "churn_indicator": true/false,
    "key_phrases": ["important/critical phrases"],
    "behavioral_cues": ["behavioral cues"],
    "recommended_tone": "Recommended response tone (empathetic/professional/apologetic/urgent)",
    "reasoning": "Detailed analysis explanation"
}}"""
        return system, user
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def _analyze_with_openai(
        self,
        text: str,
        language: str = "en"
    ) -> Dict:
        """Analyze sentiment using OpenAI."""
        
        system_prompt, user_prompt = self._build_prompt(text, language)
        
        response = await self.client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=1500
        )
        
        return json.loads(response.choices[0].message.content)
    
    def _analyze_with_rules(self, text: str, language: str = "en") -> Dict:
        """Rule-based sentiment analysis fallback."""
        
        text_lower = text.lower()
        
        # Select indicators based on language
        if language == "tr":
            positive_words = self.POSITIVE_TR
            negative_words = self.NEGATIVE_TR
            angry_words = self.ANGRY_TR
        else:
            positive_words = self.POSITIVE_EN
            negative_words = self.NEGATIVE_EN
            angry_words = self.ANGRY_EN
        
        # Count indicators
        positive_count = sum(1 for w in positive_words if w in text_lower)
        negative_count = sum(1 for w in negative_words if w in text_lower)
        angry_count = sum(1 for w in angry_words if w in text_lower)
        
        # Calculate score
        total = positive_count + negative_count + 1
        score = (positive_count - negative_count) / total
        
        # Determine sentiment
        anger_level = min(angry_count * 0.25, 1.0)
        
        if anger_level >= 0.7:
            sentiment = Sentiment.ANGRY
        elif score > 0.2:
            sentiment = Sentiment.POSITIVE
        elif score < -0.2:
            sentiment = Sentiment.NEGATIVE
        else:
            sentiment = Sentiment.NEUTRAL
        
        # Satisfaction prediction
        if sentiment == Sentiment.POSITIVE:
            satisfaction = 4 + score
        elif sentiment == Sentiment.ANGRY:
            satisfaction = 1
        elif sentiment == Sentiment.NEGATIVE:
            satisfaction = 2 - score
        else:
            satisfaction = 3
        
        return {
            "sentiment": sentiment.value,
            "score": round(score, 3),
            "confidence": 0.6,  # Lower confidence for rule-based
            "anger_level": round(anger_level, 3),
            "satisfaction_prediction": round(min(max(satisfaction, 1), 5)),
            "key_phrases": [],
            "reasoning": "Rule-based analysis",
            "method": "rule_based"
        }
    
    def _analyze_with_huggingface(
        self,
        text: str,
        language: str = "en"
    ) -> Dict:
        """Analyze using HuggingFace model."""
        
        self._load_huggingface_models()
        
        model = self._hf_model_tr if language == "tr" else self._hf_model_en
        
        if model is None:
            raise RuntimeError("HuggingFace model not available")
        
        result = model(text[:512])[0]  # Limit length
        
        label = result["label"].lower()
        hf_score = result["score"]
        
        # Map HuggingFace labels to our schema
        if "positive" in label or "pos" in label:
            sentiment = Sentiment.POSITIVE
            score = hf_score
        elif "negative" in label or "neg" in label:
            sentiment = Sentiment.NEGATIVE
            score = -hf_score
        else:
            sentiment = Sentiment.NEUTRAL
            score = 0
        
        # Check for anger using rules
        anger_level = self._detect_anger(text, language)
        if anger_level >= 0.7:
            sentiment = Sentiment.ANGRY
        
        return {
            "sentiment": sentiment.value,
            "score": round(score, 3),
            "confidence": round(hf_score, 3),
            "anger_level": round(anger_level, 3),
            "satisfaction_prediction": self._predict_satisfaction(sentiment, score),
            "key_phrases": [],
            "reasoning": f"HuggingFace model analysis",
            "method": "huggingface"
        }
    
    def _detect_anger(self, text: str, language: str = "en") -> float:
        """Detect anger level in text."""
        text_lower = text.lower()
        
        angry_words = self.ANGRY_TR if language == "tr" else self.ANGRY_EN
        count = sum(1 for w in angry_words if w in text_lower)
        
        # Also check for caps and exclamation marks
        caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
        exclamation_count = text.count("!")
        
        anger_score = min(
            (count * 0.2) + (caps_ratio * 0.5) + (exclamation_count * 0.1),
            1.0
        )
        
        return anger_score
    
    def _predict_satisfaction(self, sentiment: Sentiment, score: float) -> int:
        """Predict customer satisfaction score (1-5)."""
        
        base_scores = {
            Sentiment.POSITIVE: 4,
            Sentiment.NEUTRAL: 3,
            Sentiment.NEGATIVE: 2,
            Sentiment.ANGRY: 1
        }
        
        base = base_scores.get(sentiment, 3)
        adjustment = score * 0.5  # Small adjustment based on score
        
        return round(min(max(base + adjustment, 1), 5))
    
    async def analyze(
        self,
        text: str,
        language: str = "en",
        method: str = "auto"
    ) -> Dict:
        """
        Analyze sentiment of text.
        
        Args:
            text: Text to analyze
            language: Language code (tr, en)
            method: Analysis method (auto, openai, huggingface, rules)
            
        Returns:
            Dict with sentiment analysis results:
            {
                "sentiment": str,  # positive, neutral, negative, angry
                "score": float,  # -1 to 1
                "confidence": float,  # 0 to 1
                "anger_level": float,  # 0 to 1
                "satisfaction_prediction": int,  # 1 to 5
                "key_phrases": List[str],
                "reasoning": str,
                "method": str
            }
        """
        
        if not text or not text.strip():
            return {
                "sentiment": Sentiment.NEUTRAL.value,
                "score": 0.0,
                "confidence": 0.0,
                "anger_level": 0.0,
                "satisfaction_prediction": 3,
                "key_phrases": [],
                "reasoning": "Empty text",
                "method": "default"
            }
        
        text = text.strip()[:2000]  # Limit length
        
        # Determine method
        if method == "auto":
            method = "openai" if settings.openai_api_key else "rules"
        
        try:
            if method == "openai":
                result = await self._analyze_with_openai(text, language)
                result["method"] = "openai"
                
            elif method == "huggingface" and self.use_huggingface:
                result = self._analyze_with_huggingface(text, language)
                
            else:
                result = self._analyze_with_rules(text, language)
            
            # Validate sentiment
            if result.get("sentiment") not in [s.value for s in Sentiment]:
                result["sentiment"] = Sentiment.NEUTRAL.value
            
            # Override to angry if anger level is high
            if result.get("anger_level", 0) >= 0.7:
                result["sentiment"] = Sentiment.ANGRY.value
            
            logger.info(
                f"Sentiment: {result['sentiment']} "
                f"(score: {result.get('score', 'N/A')}, "
                f"anger: {result.get('anger_level', 'N/A')})"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            
            # Fallback to rules
            return self._analyze_with_rules(text, language)
    
    async def analyze_batch(
        self,
        texts: List[str],
        language: str = "en"
    ) -> List[Dict]:
        """Analyze sentiment for multiple texts."""
        import asyncio
        
        tasks = [self.analyze(text, language) for text in texts]
        return await asyncio.gather(*tasks)


# Singleton instance
_analyzer: Optional[SentimentAnalyzer] = None


def get_sentiment_analyzer() -> SentimentAnalyzer:
    """Get or create sentiment analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentAnalyzer()
    return _analyzer
