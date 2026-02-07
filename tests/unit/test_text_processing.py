"""
Tests for Text Processing Utilities

Unit tests for text preprocessing and cleaning.
"""

import pytest

from src.utils.text_processing import TextProcessor


class TestTextProcessor:
    """Tests for TextProcessor class."""
    
    def test_normalize_unicode(self):
        """Test Unicode normalization."""
        text = "café"  # Different Unicode representations
        result = TextProcessor.normalize_unicode(text)
        
        assert result == "café"
    
    def test_normalize_turkish_preserve(self):
        """Test Turkish character preservation."""
        text = "Merhaba, nasılsınız?"
        result = TextProcessor.normalize_turkish(text, preserve_turkish=True)
        
        assert result == text
        assert "ı" in result
    
    def test_normalize_turkish_convert(self):
        """Test Turkish character conversion to ASCII."""
        text = "Şüpheli işlem"
        result = TextProcessor.normalize_turkish(text, preserve_turkish=False)
        
        assert "S" in result or "s" in result
        assert "u" in result
        assert "i" in result
    
    def test_remove_html_simple(self):
        """Test simple HTML removal."""
        text = "<p>Hello <b>World</b></p>"
        result = TextProcessor.remove_html(text)
        
        assert "<" not in result
        assert ">" not in result
        assert "Hello" in result
        assert "World" in result
    
    def test_remove_html_with_breaks(self):
        """Test HTML removal preserves line breaks."""
        text = "Line 1<br>Line 2</p>Line 3"
        result = TextProcessor.remove_html(text)
        
        assert "\n" in result
    
    def test_remove_html_entities(self):
        """Test HTML entity decoding."""
        text = "Hello &amp; World &lt;test&gt;"
        result = TextProcessor.remove_html(text)
        
        assert "& World" in result
        assert "<test>" in result
    
    def test_normalize_whitespace(self):
        """Test whitespace normalization."""
        text = "Hello    World\n\n\n\nTest"
        result = TextProcessor.normalize_whitespace(text)
        
        assert "    " not in result
        assert "\n\n\n" not in result
    
    def test_normalize_whitespace_tabs(self):
        """Test tab conversion."""
        text = "Hello\tWorld"
        result = TextProcessor.normalize_whitespace(text)
        
        assert "\t" not in result
    
    def test_remove_signatures_regards(self):
        """Test email signature removal."""
        text = "Please help me.\n\nBest regards,\nJohn Doe\nCompany Inc."
        result = TextProcessor.remove_signatures(text)
        
        assert "Please help me" in result
        assert "John Doe" not in result
    
    def test_remove_signatures_turkish(self):
        """Test Turkish signature removal."""
        text = "Yardım edin lütfen.\n\nSaygılarımla,\nAhmet"
        result = TextProcessor.remove_signatures(text)
        
        assert "Yardım edin" in result
    
    def test_mask_pii_email(self):
        """Test email masking."""
        text = "Contact me at john@example.com"
        result, mappings = TextProcessor.mask_pii(text)
        
        assert "john@example.com" not in result
        assert "[EMAIL_0]" in result
        assert "john@example.com" in mappings["emails"]
    
    def test_mask_pii_phone(self):
        """Test phone number masking."""
        text = "Call me at +90 555 123 4567"
        result, mappings = TextProcessor.mask_pii(text)
        
        assert "555" not in result or "[PHONE" in result
    
    def test_mask_pii_url(self):
        """Test URL masking."""
        text = "Visit https://example.com/page"
        result, mappings = TextProcessor.mask_pii(text)
        
        assert "https://example.com" not in result
        assert "[URL_0]" in result
    
    def test_detect_language_turkish(self):
        """Test Turkish language detection."""
        text = "Merhaba, uygulamanız çalışmıyor. Lütfen yardım edin."
        lang, confidence = TextProcessor.detect_language(text)
        
        assert lang == "tr"
        assert confidence > 0.5
    
    def test_detect_language_english(self):
        """Test English language detection."""
        text = "Hello, your application is not working. Please help me."
        lang, confidence = TextProcessor.detect_language(text)
        
        assert lang == "en"
        assert confidence > 0.5
    
    def test_extract_key_phrases_quoted(self):
        """Test extraction of quoted phrases."""
        text = 'I got error "Connection refused" when trying'
        phrases = TextProcessor.extract_key_phrases(text)
        
        assert "Connection refused" in phrases
    
    def test_extract_key_phrases_caps(self):
        """Test extraction of capitalized phrases."""
        text = "Error code ERR_CONNECTION_TIMEOUT occurred"
        phrases = TextProcessor.extract_key_phrases(text)
        
        assert "ERR_CONNECTION_TIMEOUT" in phrases
    
    def test_clean_for_processing_full(self):
        """Test full cleaning pipeline."""
        text = """
        <p>Hello,</p>
        <p>I have a problem with error   code ABC123.</p>
        <br>
        <p>My email is test@example.com</p>
        
        Best regards,
        John
        """
        
        result = TextProcessor.clean_for_processing(
            text,
            remove_html=True,
            remove_signatures=True,
            mask_pii=True
        )
        
        assert "<p>" not in result
        assert "test@example.com" not in result
        assert "John" not in result
        assert "problem" in result.lower()
    
    def test_clean_for_processing_empty(self):
        """Test cleaning empty text."""
        result = TextProcessor.clean_for_processing("")
        
        assert result == ""
    
    def test_clean_for_processing_none(self):
        """Test cleaning None."""
        result = TextProcessor.clean_for_processing(None)
        
        assert result == ""
    
    def test_truncate_short_text(self):
        """Test truncation of short text."""
        text = "Short text"
        result = TextProcessor.truncate(text, max_length=100)
        
        assert result == text
    
    def test_truncate_long_text(self):
        """Test truncation of long text."""
        text = "A" * 1000
        result = TextProcessor.truncate(text, max_length=100)
        
        assert len(result) == 100
        assert result.endswith("...")
    
    def test_truncate_custom_suffix(self):
        """Test truncation with custom suffix."""
        text = "A" * 1000
        result = TextProcessor.truncate(text, max_length=100, suffix=" [truncated]")
        
        assert result.endswith("[truncated]")
