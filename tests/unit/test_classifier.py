"""
Tests for Ticket Classifier Service

Unit tests for AI classification functionality.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.services.classifier import TicketClassifier, get_classifier


class TestTicketClassifier:
    """Tests for TicketClassifier class."""
    
    def test_init_default_categories(self):
        """Test classifier initializes with default categories."""
        classifier = TicketClassifier()
        
        assert len(classifier.categories) == 8
        assert "technical_issue" in classifier.categories
        assert "billing_question" in classifier.categories
        assert "complaint" in classifier.categories
    
    def test_init_custom_categories(self):
        """Test classifier with custom categories."""
        custom = ["support", "sales", "other"]
        classifier = TicketClassifier(categories=custom)
        
        assert classifier.categories == custom
    
    def test_rule_based_fallback_technical(self):
        """Test rule-based fallback for technical issues."""
        classifier = TicketClassifier()
        
        result = classifier._rule_based_fallback(
            "Uygulamanız çalışmıyor, sürekli hata veriyor"
        )
        
        assert result["primary_category"] == "technical_issue"
        assert result["method"] == "rule_based"
        assert result["confidence"] > 0
    
    def test_rule_based_fallback_billing(self):
        """Test rule-based fallback for billing questions."""
        classifier = TicketClassifier()
        
        result = classifier._rule_based_fallback(
            "Faturamda yanlışlık var, fazla ücret kesilmiş"
        )
        
        assert result["primary_category"] == "billing_question"
    
    def test_rule_based_fallback_complaint(self):
        """Test rule-based fallback for complaints."""
        classifier = TicketClassifier()
        
        result = classifier._rule_based_fallback(
            "Bu bir rezalet, hizmetinizden çok memnuniyetsizim, şikayet ediyorum"
        )
        
        assert result["primary_category"] == "complaint"
    
    def test_rule_based_fallback_feature_request(self):
        """Test rule-based fallback for feature requests."""
        classifier = TicketClassifier()
        
        result = classifier._rule_based_fallback(
            "It would be nice if you could add a new feature for exporting data"
        )
        
        assert result["primary_category"] == "feature_request"
    
    def test_rule_based_fallback_general_inquiry(self):
        """Test rule-based fallback defaults to general inquiry."""
        classifier = TicketClassifier()
        
        result = classifier._rule_based_fallback(
            "Merhaba, size bir sorum var"
        )
        
        assert result["primary_category"] == "general_inquiry"
    
    @pytest.mark.asyncio
    async def test_classify_empty_text(self):
        """Test classification of empty text."""
        classifier = TicketClassifier()
        
        result = await classifier.classify("")
        
        assert result["primary_category"] == "general_inquiry"
        assert result["confidence"] == 0.0
        assert result["method"] == "default"
    
    @pytest.mark.asyncio
    async def test_classify_whitespace_text(self):
        """Test classification of whitespace-only text."""
        classifier = TicketClassifier()
        
        result = await classifier.classify("   \n\t  ")
        
        assert result["primary_category"] == "general_inquiry"
        assert result["confidence"] == 0.0
    
    @pytest.mark.asyncio
    async def test_classify_uses_fallback_on_api_error(self):
        """Test that classifier falls back to rules on API error."""
        classifier = TicketClassifier()
        
        with patch.object(classifier, '_call_openai', side_effect=Exception("API Error")):
            result = await classifier.classify(
                "Uygulamanız çalışmıyor",
                use_cache=False
            )
        
        assert result["method"] == "rule_based"
        assert result["primary_category"] is not None
    
    @pytest.mark.asyncio
    async def test_classify_with_mock_openai(self, mock_openai_response):
        """Test classification with mocked OpenAI response."""
        classifier = TicketClassifier()
        
        with patch.object(classifier, '_call_openai', return_value=mock_openai_response):
            result = await classifier.classify(
                "Uygulamanız çalışmıyor, sürekli hata veriyor",
                use_cache=False
            )
        
        assert result["primary_category"] == "technical_issue"
        assert result["confidence"] == 0.92
        assert result["method"] == "ai"
    
    def test_build_system_prompt_turkish(self):
        """Test system prompt generation for Turkish."""
        classifier = TicketClassifier()
        
        prompt = classifier._build_system_prompt("tr")
        
        assert "müşteri destek" in prompt.lower()
        assert "kategoriler" in prompt.lower()
        assert "türkçe" in prompt.lower()
    
    def test_build_system_prompt_english(self):
        """Test system prompt generation for English."""
        classifier = TicketClassifier()
        
        prompt = classifier._build_system_prompt("en")
        
        assert "customer support" in prompt.lower()
        assert "categories" in prompt.lower()


class TestGetClassifier:
    """Tests for classifier singleton."""
    
    def test_returns_classifier_instance(self):
        """Test that get_classifier returns a TicketClassifier."""
        classifier = get_classifier()
        
        assert isinstance(classifier, TicketClassifier)
    
    def test_returns_same_instance(self):
        """Test that get_classifier returns singleton."""
        c1 = get_classifier()
        c2 = get_classifier()
        
        assert c1 is c2
