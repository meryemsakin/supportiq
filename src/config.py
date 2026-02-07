"""
Configuration management using Pydantic Settings.

This module provides centralized configuration for the application,
loading values from environment variables with sensible defaults.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings can be overridden by setting the corresponding
    environment variable (case-insensitive).
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # -------------------------------------------------------------------------
    # Application Settings
    # -------------------------------------------------------------------------
    app_name: str = Field(
        default="Intelligent Support Router",
        description="Application name"
    )
    app_env: str = Field(
        default="development",
        description="Environment (development, staging, production, testing)"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    secret_key: str = Field(
        default="change-me-in-production",
        description="Secret key for JWT and sessions"
    )
    
    # -------------------------------------------------------------------------
    # API Settings
    # -------------------------------------------------------------------------
    api_v1_prefix: str = Field(
        default="/api/v1",
        description="API version 1 prefix"
    )
    allowed_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        description="Comma-separated list of allowed CORS origins"
    )
    
    @property
    def cors_origins(self) -> List[str]:
        """Parse allowed origins into a list."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]
    
    # -------------------------------------------------------------------------
    # Database Settings
    # -------------------------------------------------------------------------
    database_url: str = Field(
        default="postgresql://support_user:support_password@localhost:5432/support_router",
        description="PostgreSQL connection string"
    )
    database_pool_size: int = Field(
        default=10,
        description="Database connection pool size"
    )
    database_max_overflow: int = Field(
        default=20,
        description="Maximum overflow connections"
    )
    
    # -------------------------------------------------------------------------
    # Redis Settings
    # -------------------------------------------------------------------------
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string"
    )
    redis_cache_ttl: int = Field(
        default=3600,
        description="Default cache TTL in seconds"
    )
    
    # -------------------------------------------------------------------------
    # Celery Settings
    # -------------------------------------------------------------------------
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1",
        description="Celery broker URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2",
        description="Celery result backend URL"
    )
    
    # -------------------------------------------------------------------------
    # OpenAI Settings
    # -------------------------------------------------------------------------
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key"
    )
    openai_model: str = Field(
        default="gpt-4-turbo-preview",
        description="OpenAI model for classification"
    )
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI model for embeddings"
    )
    
    # -------------------------------------------------------------------------
    # Language Settings
    # -------------------------------------------------------------------------
    default_language: str = Field(
        default="en",
        description="Default language for processing (tr, en)"
    )
    supported_languages: List[str] = Field(
        default=["tr", "en"],
        description="List of supported languages"
    )
    
    # -------------------------------------------------------------------------
    # Classification Settings
    # -------------------------------------------------------------------------
    classification_confidence_threshold: float = Field(
        default=0.7,
        description="Minimum confidence for classification"
    )
    default_categories: List[str] = Field(
        default=[
            "technical_issue",
            "billing_question",
            "feature_request",
            "bug_report",
            "account_management",
            "return_refund",
            "general_inquiry",
            "complaint"
        ],
        description="Default ticket categories"
    )
    
    # -------------------------------------------------------------------------
    # Vector Database Settings
    # -------------------------------------------------------------------------
    chroma_persist_directory: str = Field(
        default="./data/chroma",
        description="ChromaDB persistence directory"
    )
    chroma_collection_name: str = Field(
        default="knowledge_base",
        description="ChromaDB collection name"
    )
    
    # -------------------------------------------------------------------------
    # HuggingFace Settings (Optional)
    # -------------------------------------------------------------------------
    huggingface_token: Optional[str] = Field(
        default=None,
        description="HuggingFace API token"
    )
    sentiment_model_tr: str = Field(
        default="savasy/bert-base-turkish-sentiment-cased",
        description="Turkish sentiment model"
    )
    sentiment_model_en: str = Field(
        default="cardiffnlp/twitter-roberta-base-sentiment",
        description="English sentiment model"
    )
    
    # -------------------------------------------------------------------------
    # Integration Settings - Zendesk
    # -------------------------------------------------------------------------
    zendesk_subdomain: Optional[str] = Field(
        default=None,
        description="Zendesk subdomain"
    )
    zendesk_email: Optional[str] = Field(
        default=None,
        description="Zendesk account email"
    )
    zendesk_api_token: Optional[str] = Field(
        default=None,
        description="Zendesk API token"
    )
    zendesk_webhook_secret: Optional[str] = Field(
        default=None,
        description="Zendesk webhook secret"
    )
    
    # -------------------------------------------------------------------------
    # Integration Settings - Freshdesk
    # -------------------------------------------------------------------------
    freshdesk_domain: Optional[str] = Field(
        default=None,
        description="Freshdesk domain"
    )
    freshdesk_api_key: Optional[str] = Field(
        default=None,
        description="Freshdesk API key"
    )
    
    # -------------------------------------------------------------------------
    # Integration Settings - Email
    # -------------------------------------------------------------------------
    imap_server: Optional[str] = Field(default=None)
    imap_port: int = Field(default=993)
    imap_username: Optional[str] = Field(default=None)
    imap_password: Optional[str] = Field(default=None)
    smtp_server: Optional[str] = Field(default=None)
    smtp_port: int = Field(default=587)
    smtp_username: Optional[str] = Field(default=None)
    smtp_password: Optional[str] = Field(default=None)
    
    # -------------------------------------------------------------------------
    # Monitoring Settings
    # -------------------------------------------------------------------------
    sentry_dsn: Optional[str] = Field(
        default=None,
        description="Sentry DSN for error tracking"
    )
    prometheus_enabled: bool = Field(
        default=True,
        description="Enable Prometheus metrics"
    )
    prometheus_port: int = Field(
        default=9090,
        description="Prometheus metrics port"
    )
    
    # -------------------------------------------------------------------------
    # Rate Limiting
    # -------------------------------------------------------------------------
    rate_limit_requests: int = Field(
        default=100,
        description="Maximum requests per window"
    )
    rate_limit_window: int = Field(
        default=60,
        description="Rate limit window in seconds"
    )
    
    # -------------------------------------------------------------------------
    # Validators
    # -------------------------------------------------------------------------
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v
    
    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        """Validate application environment."""
        valid_envs = ["development", "staging", "production", "testing"]
        v = v.lower()
        if v not in valid_envs:
            raise ValueError(f"App env must be one of: {valid_envs}")
        return v


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses lru_cache to ensure settings are only loaded once.
    
    Returns:
        Settings: Application settings instance
    """
    return Settings()


# Export settings instance for convenience
settings = get_settings()
