"""
Tests for Priority Scorer Service

Unit tests for priority calculation functionality.
"""

import pytest

from src.services.priority_scorer import PriorityScorer, get_priority_scorer


class TestPriorityScorer:
    """Tests for PriorityScorer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.scorer = PriorityScorer()
    
    def test_default_priority(self):
        """Test default priority is medium (3)."""
        result = self.scorer.calculate(
            text="Bir sorum var",
            sentiment="neutral"
        )
        
        assert result["score"] == 3
        assert result["level"] == "medium"
    
    def test_urgent_keyword_boost(self):
        """Test urgent keywords increase priority."""
        result = self.scorer.calculate(
            text="Bu çok ACİL, hemen çözülmesi lazım!",
            sentiment="neutral"
        )
        
        assert result["score"] >= 4
        assert "urgent_keyword" in result["factors"]
    
    def test_high_keyword_boost(self):
        """Test high priority keywords."""
        result = self.scorer.calculate(
            text="Sistem çalışmıyor, hiçbir şey yapamıyorum",
            sentiment="neutral"
        )
        
        assert result["score"] >= 3
        assert "high_priority_keyword" in result["factors"]
    
    def test_negative_sentiment_boost(self):
        """Test negative sentiment increases priority."""
        result = self.scorer.calculate(
            text="Bir sorunum var",
            sentiment="negative"
        )
        
        base_result = self.scorer.calculate(
            text="Bir sorunum var",
            sentiment="neutral"
        )
        
        assert result["score"] > base_result["score"]
        assert any("sentiment" in f for f in result["factors"])
    
    def test_angry_sentiment_boost(self):
        """Test angry sentiment increases priority more."""
        result = self.scorer.calculate(
            text="Bir sorunum var",
            sentiment="angry"
        )
        
        negative_result = self.scorer.calculate(
            text="Bir sorunum var",
            sentiment="negative"
        )
        
        assert result["score"] >= negative_result["score"]
    
    def test_vip_customer_boost(self):
        """Test VIP customers get priority boost."""
        result = self.scorer.calculate(
            text="Bir sorum var",
            sentiment="neutral",
            customer_tier="vip"
        )
        
        standard_result = self.scorer.calculate(
            text="Bir sorum var",
            sentiment="neutral",
            customer_tier="standard"
        )
        
        assert result["score"] > standard_result["score"]
        assert "customer_tier_vip" in result["factors"]
    
    def test_free_customer_reduction(self):
        """Test free tier customers may get lower priority."""
        result = self.scorer.calculate(
            text="Bir sorum var",
            sentiment="neutral",
            customer_tier="free"
        )
        
        standard_result = self.scorer.calculate(
            text="Bir sorum var",
            sentiment="neutral",
            customer_tier="standard"
        )
        
        assert result["score"] <= standard_result["score"]
    
    def test_critical_category_boost(self):
        """Test critical categories increase priority."""
        result = self.scorer.calculate(
            text="Bir sorunum var",
            sentiment="neutral",
            category="complaint"
        )
        
        assert result["score"] >= 4
        assert "critical_category_complaint" in result["factors"]
    
    def test_feature_request_no_boost(self):
        """Test feature requests don't get extra priority."""
        result = self.scorer.calculate(
            text="Yeni bir özellik ekleseniz",
            sentiment="positive",
            category="feature_request"
        )
        
        assert result["score"] <= 3
    
    def test_high_anger_level_boost(self):
        """Test high anger level increases priority."""
        result = self.scorer.calculate(
            text="Bir sorunum var",
            sentiment="neutral",
            anger_level=0.8
        )
        
        base_result = self.scorer.calculate(
            text="Bir sorunum var",
            sentiment="neutral",
            anger_level=0.2
        )
        
        assert result["score"] > base_result["score"]
        assert "high_anger" in result["factors"]
    
    def test_caps_text_boost(self):
        """Test excessive caps increases priority."""
        result = self.scorer.calculate(
            text="BU ÇOK ÖNEMLİ BİR SORUN!!!",
            sentiment="neutral"
        )
        
        assert "excessive_caps" in result["factors"] or "multiple_exclamations" in result["factors"]
    
    def test_priority_capped_at_5(self):
        """Test priority cannot exceed 5."""
        result = self.scorer.calculate(
            text="ACİL! Kritik hata! Çalışmıyor!",
            sentiment="angry",
            anger_level=1.0,
            customer_tier="vip",
            category="complaint"
        )
        
        assert result["score"] == 5
        assert result["level"] == "critical"
    
    def test_priority_minimum_is_1(self):
        """Test priority cannot go below 1."""
        result = self.scorer.calculate(
            text="Teşekkürler",
            sentiment="positive",
            customer_tier="free",
            category="general_inquiry"
        )
        
        assert result["score"] >= 1
    
    def test_breakdown_included(self):
        """Test that breakdown is included in result."""
        result = self.scorer.calculate(
            text="Bir sorum var",
            sentiment="neutral"
        )
        
        assert "breakdown" in result
        assert "base_score" in result["breakdown"]
        assert "total_adjustment" in result["breakdown"]
        assert "final_score" in result["breakdown"]
    
    def test_factor_details_included(self):
        """Test that factor details are included."""
        result = self.scorer.calculate(
            text="ACİL sorun!",
            sentiment="negative",
            customer_tier="premium"
        )
        
        assert "factor_details" in result
        assert len(result["factor_details"]) > 0
        
        for detail in result["factor_details"]:
            assert "name" in detail
            assert "weight" in detail
            assert "description" in detail
    
    def test_recalculate_with_override_up(self):
        """Test manual priority override upward."""
        result = self.scorer.recalculate_with_override(
            current_score=3,
            override_factors=["VIP customer request"],
            direction="up"
        )
        
        assert result["score"] == 4
        assert result["breakdown"]["override"] == True
    
    def test_recalculate_with_override_down(self):
        """Test manual priority override downward."""
        result = self.scorer.recalculate_with_override(
            current_score=4,
            override_factors=["Not urgent"],
            direction="down"
        )
        
        assert result["score"] == 3


class TestGetPriorityScorer:
    """Tests for priority scorer singleton."""
    
    def test_returns_priority_scorer_instance(self):
        """Test that get_priority_scorer returns a PriorityScorer."""
        scorer = get_priority_scorer()
        
        assert isinstance(scorer, PriorityScorer)
    
    def test_accepts_custom_rules(self):
        """Test that custom rules can be passed."""
        custom_rules = [
            {
                "type": "keyword",
                "keywords": ["test"],
                "weight": 1,
                "name": "test_rule"
            }
        ]
        
        scorer = get_priority_scorer(custom_rules=custom_rules)
        
        assert len(scorer.custom_rules) == 1
