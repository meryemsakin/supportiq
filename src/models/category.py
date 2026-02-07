"""
Category Model

Represents ticket categories and their configuration.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Integer, Float, Text, DateTime, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid

from src.database import Base


class Category(Base):
    """
    Category model for ticket classification.
    
    Attributes:
        id: Unique category identifier
        name: Category slug/key (e.g., "technical_issue")
        display_name: Human-readable name
        description: Category description
        
        # Configuration
        is_active: Whether category is active
        priority_boost: Default priority boost for this category
        sla_hours: Default SLA hours for this category
        
        # AI configuration
        keywords: Keywords that indicate this category
        negative_keywords: Keywords that exclude this category
        examples: Example tickets for few-shot learning
        
        # Routing
        default_team: Default team to route to
        escalation_team: Team for escalations
        requires_senior: Whether requires senior agent
    """
    
    __tablename__ = "categories"
    
    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    
    # Basic info
    name = Column(String(100), nullable=False, unique=True, index=True)
    display_name = Column(String(200), nullable=False)
    display_name_tr = Column(String(200), nullable=True)  # Turkish name
    description = Column(Text, nullable=True)
    description_tr = Column(Text, nullable=True)  # Turkish description
    icon = Column(String(50), nullable=True)  # Icon name/emoji
    color = Column(String(20), nullable=True)  # Hex color code
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    is_default = Column(Boolean, default=False)  # Fallback category
    
    # Priority configuration
    priority_boost = Column(Integer, default=0)  # Added to calculated priority
    min_priority = Column(Integer, default=1)
    max_priority = Column(Integer, default=5)
    
    # SLA configuration
    sla_first_response_hours = Column(Float, default=4.0)
    sla_resolution_hours = Column(Float, default=24.0)
    
    # AI configuration
    keywords = Column(JSON, default=list)  # Keywords indicating this category
    keywords_tr = Column(JSON, default=list)  # Turkish keywords
    negative_keywords = Column(JSON, default=list)  # Keywords excluding this category
    
    # Few-shot examples for AI
    examples = Column(JSON, default=list)  # [{"text": "...", "explanation": "..."}]
    
    # Routing configuration
    default_team = Column(String(100), nullable=True)
    escalation_team = Column(String(100), nullable=True)
    requires_senior = Column(Boolean, default=False)
    requires_specialist = Column(Boolean, default=False)
    auto_assign = Column(Boolean, default=True)
    
    # Response templates
    auto_reply_enabled = Column(Boolean, default=False)
    auto_reply_template_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Statistics (cached)
    ticket_count = Column(Integer, default=0)
    avg_resolution_time = Column(Integer, nullable=True)  # seconds
    
    # Ordering
    sort_order = Column(Integer, default=0)
    
    # Extra data
    extra_data = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    def __repr__(self) -> str:
        return f"<Category(name={self.name}, display_name={self.display_name})>"
    
    def get_display_name(self, language: str = "en") -> str:
        """Get display name in specified language."""
        if language == "tr" and self.display_name_tr:
            return self.display_name_tr
        return self.display_name
    
    def get_description(self, language: str = "en") -> Optional[str]:
        """Get description in specified language."""
        if language == "tr" and self.description_tr:
            return self.description_tr
        return self.description
    
    def get_keywords(self, language: str = "en") -> list:
        """Get keywords for specified language."""
        keywords = self.keywords or []
        if language == "tr":
            keywords.extend(self.keywords_tr or [])
        return keywords


# Default categories to seed
DEFAULT_CATEGORIES = [
    {
        "name": "technical_issue",
        "display_name": "Technical Issue",
        "display_name_tr": "Teknik Sorun",
        "description": "Technical problems, errors, and system issues",
        "description_tr": "Teknik problemler, hatalar ve sistem sorunları",
        "icon": "🔧",
        "color": "#EF4444",
        "priority_boost": 1,
        "keywords": ["error", "bug", "crash", "not working", "broken", "issue", "problem"],
        "keywords_tr": ["hata", "çalışmıyor", "bozuk", "sorun", "problem", "arıza"],
        "sla_first_response_hours": 2.0,
        "sla_resolution_hours": 8.0,
    },
    {
        "name": "billing_question",
        "display_name": "Billing Question",
        "display_name_tr": "Fatura Sorusu",
        "description": "Payment, invoice, and billing inquiries",
        "description_tr": "Ödeme, fatura ve faturalandırma soruları",
        "icon": "💳",
        "color": "#F59E0B",
        "keywords": ["invoice", "payment", "charge", "bill", "refund", "price"],
        "keywords_tr": ["fatura", "ödeme", "ücret", "hesap", "iade", "fiyat"],
        "sla_first_response_hours": 4.0,
        "sla_resolution_hours": 24.0,
    },
    {
        "name": "feature_request",
        "display_name": "Feature Request",
        "display_name_tr": "Özellik İsteği",
        "description": "Suggestions for new features or improvements",
        "description_tr": "Yeni özellik veya iyileştirme önerileri",
        "icon": "💡",
        "color": "#10B981",
        "keywords": ["feature", "suggestion", "improvement", "add", "would be nice"],
        "keywords_tr": ["özellik", "öneri", "iyileştirme", "ekle", "iyi olur"],
        "priority_boost": -1,
        "sla_first_response_hours": 24.0,
        "sla_resolution_hours": 168.0,
    },
    {
        "name": "bug_report",
        "display_name": "Bug Report",
        "display_name_tr": "Hata Bildirimi",
        "description": "Software bugs and defect reports",
        "description_tr": "Yazılım hataları ve kusur bildirimleri",
        "icon": "🐛",
        "color": "#DC2626",
        "priority_boost": 1,
        "requires_senior": True,
        "keywords": ["bug", "defect", "glitch", "malfunction", "unexpected behavior"],
        "keywords_tr": ["bug", "kusur", "hata", "arıza", "beklenmedik davranış"],
        "sla_first_response_hours": 2.0,
        "sla_resolution_hours": 24.0,
    },
    {
        "name": "account_management",
        "display_name": "Account Management",
        "display_name_tr": "Hesap Yönetimi",
        "description": "Account settings, password, and profile issues",
        "description_tr": "Hesap ayarları, şifre ve profil sorunları",
        "icon": "👤",
        "color": "#6366F1",
        "keywords": ["account", "password", "login", "profile", "settings", "access"],
        "keywords_tr": ["hesap", "şifre", "giriş", "profil", "ayarlar", "erişim"],
        "sla_first_response_hours": 4.0,
        "sla_resolution_hours": 12.0,
    },
    {
        "name": "return_refund",
        "display_name": "Return/Refund",
        "display_name_tr": "İade/Geri Ödeme",
        "description": "Product returns and refund requests",
        "description_tr": "Ürün iadesi ve geri ödeme talepleri",
        "icon": "↩️",
        "color": "#8B5CF6",
        "keywords": ["return", "refund", "money back", "cancel", "exchange"],
        "keywords_tr": ["iade", "geri ödeme", "iptal", "değişim", "para iade"],
        "sla_first_response_hours": 4.0,
        "sla_resolution_hours": 48.0,
    },
    {
        "name": "general_inquiry",
        "display_name": "General Inquiry",
        "display_name_tr": "Genel Soru",
        "description": "General questions and information requests",
        "description_tr": "Genel sorular ve bilgi talepleri",
        "icon": "❓",
        "color": "#3B82F6",
        "is_default": True,
        "keywords": ["question", "how", "what", "when", "where", "information"],
        "keywords_tr": ["soru", "nasıl", "ne", "ne zaman", "nerede", "bilgi"],
        "sla_first_response_hours": 8.0,
        "sla_resolution_hours": 48.0,
    },
    {
        "name": "complaint",
        "display_name": "Complaint",
        "display_name_tr": "Şikayet",
        "description": "Customer complaints and negative feedback",
        "description_tr": "Müşteri şikayetleri ve olumsuz geri bildirim",
        "icon": "😠",
        "color": "#BE185D",
        "priority_boost": 2,
        "requires_senior": True,
        "keywords": ["complaint", "unhappy", "disappointed", "terrible", "worst", "unacceptable"],
        "keywords_tr": ["şikayet", "mutsuz", "hayal kırıklığı", "berbat", "kabul edilemez", "memnuniyetsiz"],
        "sla_first_response_hours": 1.0,
        "sla_resolution_hours": 8.0,
    },
]
