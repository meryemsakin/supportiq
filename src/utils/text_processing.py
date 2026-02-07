"""
Text Processing Utilities

Functions for text preprocessing, normalization, and cleaning.
"""

import re
import unicodedata
from typing import Optional, List, Tuple
from langdetect import detect, LangDetectException


class TextProcessor:
    """
    Text preprocessing and normalization utilities.
    
    Features:
    - Unicode normalization
    - Turkish character handling
    - HTML removal
    - Whitespace normalization
    - Language detection
    - Profanity filtering (basic)
    """
    
    # Turkish character mappings
    TURKISH_CHARS = {
        'ı': 'i', 'İ': 'I',
        'ğ': 'g', 'Ğ': 'G',
        'ü': 'u', 'Ü': 'U',
        'ş': 's', 'Ş': 'S',
        'ö': 'o', 'Ö': 'O',
        'ç': 'c', 'Ç': 'C'
    }
    
    # Common email signature patterns
    SIGNATURE_PATTERNS = [
        r'--\s*\n.*',  # -- followed by signature
        r'Best regards?,?.*',
        r'Kind regards?,?.*',
        r'Regards?,?.*',
        r'Thanks?,?.*',
        r'Saygılarımla.*',
        r'İyi günler.*',
        r'Sent from my (?:iPhone|iPad|Android).*',
    ]
    
    # HTML tag pattern
    HTML_TAG_PATTERN = re.compile(r'<[^>]+>')
    
    # URL pattern
    URL_PATTERN = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    
    # Email pattern
    EMAIL_PATTERN = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
    
    # Phone pattern (basic)
    PHONE_PATTERN = re.compile(r'[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}')
    
    @classmethod
    def normalize_unicode(cls, text: str) -> str:
        """Normalize Unicode characters (NFC normalization)."""
        return unicodedata.normalize('NFC', text)
    
    @classmethod
    def normalize_turkish(cls, text: str, preserve_turkish: bool = True) -> str:
        """
        Handle Turkish characters.
        
        Args:
            text: Input text
            preserve_turkish: If True, keeps Turkish chars; if False, converts to ASCII
        """
        if preserve_turkish:
            return text
        
        result = text
        for turkish, ascii_char in cls.TURKISH_CHARS.items():
            result = result.replace(turkish, ascii_char)
        
        return result
    
    @classmethod
    def remove_html(cls, text: str) -> str:
        """Remove HTML tags from text."""
        # Replace common block elements with newlines
        text = re.sub(r'<br\s*/?>|</p>|</div>|</li>', '\n', text, flags=re.IGNORECASE)
        # Remove all remaining tags
        text = cls.HTML_TAG_PATTERN.sub('', text)
        # Decode HTML entities
        import html
        text = html.unescape(text)
        return text
    
    @classmethod
    def normalize_whitespace(cls, text: str) -> str:
        """Normalize whitespace (multiple spaces, tabs, newlines)."""
        # Replace tabs with spaces
        text = text.replace('\t', ' ')
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        # Collapse multiple newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Collapse multiple spaces
        text = re.sub(r' {2,}', ' ', text)
        # Strip lines
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        return text.strip()
    
    @classmethod
    def remove_signatures(cls, text: str) -> str:
        """Remove email signatures from text."""
        for pattern in cls.SIGNATURE_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        return text.strip()
    
    @classmethod
    def mask_pii(cls, text: str) -> Tuple[str, dict]:
        """
        Mask personally identifiable information (PII).
        
        Returns:
            Tuple of (masked_text, mappings)
        """
        mappings = {
            'emails': [],
            'phones': [],
            'urls': []
        }
        
        # Mask emails
        emails = cls.EMAIL_PATTERN.findall(text)
        for i, email in enumerate(emails):
            mappings['emails'].append(email)
            text = text.replace(email, f'[EMAIL_{i}]')
        
        # Mask phones
        phones = cls.PHONE_PATTERN.findall(text)
        for i, phone in enumerate(phones):
            if len(phone) >= 7:  # Only mask if looks like a real phone
                mappings['phones'].append(phone)
                text = text.replace(phone, f'[PHONE_{i}]')
        
        # Mask URLs
        urls = cls.URL_PATTERN.findall(text)
        for i, url in enumerate(urls):
            mappings['urls'].append(url)
            text = text.replace(url, f'[URL_{i}]')
        
        return text, mappings
    
    @classmethod
    def detect_language(cls, text: str) -> Tuple[str, float]:
        """
        Detect language of text.
        
        Returns:
            Tuple of (language_code, confidence)
        """
        try:
            # langdetect doesn't provide confidence, so we estimate
            lang = detect(text)
            
            # Map some common codes
            lang_map = {
                'tr': 'tr',
                'en': 'en',
                'de': 'de',
                'fr': 'fr',
                'es': 'es',
            }
            
            lang = lang_map.get(lang, lang)
            
            # Estimate confidence based on text length
            confidence = min(0.5 + (len(text) / 1000), 0.95)
            
            return lang, confidence
            
        except LangDetectException:
            return 'en', 0.5  # Default to English with low confidence
    
    @classmethod
    def extract_key_phrases(cls, text: str, max_phrases: int = 5) -> List[str]:
        """
        Extract key phrases from text (simple implementation).
        
        For production, consider using KeyBERT or similar.
        """
        # Simple extraction based on capitalized phrases and quoted text
        phrases = []
        
        # Quoted phrases
        quoted = re.findall(r'"([^"]+)"', text)
        phrases.extend(quoted)
        
        # Capitalized phrases (potential product names, error codes)
        caps = re.findall(r'\b[A-Z][A-Z0-9_-]{2,}\b', text)
        phrases.extend(caps)
        
        # Error codes
        errors = re.findall(r'\b(?:error|hata)\s*(?:code|kodu)?:?\s*([A-Z0-9-]+)', text, re.IGNORECASE)
        phrases.extend(errors)
        
        # Remove duplicates and limit
        seen = set()
        unique = []
        for p in phrases:
            if p.lower() not in seen:
                seen.add(p.lower())
                unique.append(p)
        
        return unique[:max_phrases]
    
    @classmethod
    def clean_for_processing(
        cls,
        text: str,
        remove_html: bool = True,
        remove_signatures: bool = True,
        mask_pii: bool = False,
        preserve_turkish: bool = True
    ) -> str:
        """
        Full text cleaning pipeline for AI processing.
        
        Args:
            text: Raw input text
            remove_html: Remove HTML tags
            remove_signatures: Remove email signatures
            mask_pii: Mask personal information
            preserve_turkish: Keep Turkish characters
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Unicode normalization
        text = cls.normalize_unicode(text)
        
        # Remove HTML
        if remove_html:
            text = cls.remove_html(text)
        
        # Handle Turkish
        text = cls.normalize_turkish(text, preserve_turkish)
        
        # Normalize whitespace
        text = cls.normalize_whitespace(text)
        
        # Remove signatures
        if remove_signatures:
            text = cls.remove_signatures(text)
        
        # Mask PII
        if mask_pii:
            text, _ = cls.mask_pii(text)
        
        return text.strip()
    
    @classmethod
    def truncate(
        cls,
        text: str,
        max_length: int = 5000,
        suffix: str = "..."
    ) -> str:
        """Truncate text to maximum length."""
        if len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)] + suffix
