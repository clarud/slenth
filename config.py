"""
Configuration management for SLENTH AML Monitoring System.
Loads environment variables and provides typed configuration objects.
"""
from pydantic_settings import BaseSettings
from pydantic import Field, PostgresDsn, RedisDsn, ConfigDict
from pathlib import Path
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Main application settings."""
    
    model_config = ConfigDict(
        env_file=str(Path(__file__).with_name(".env")),
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Application
    app_env: str = Field(default="development")
    app_name: str = Field(default="SLENTH AML Monitor")
    app_version: str = Field(default="1.0.0")
    debug: bool = Field(default=True)
    log_level: str = Field(default="INFO")
    secret_key: str
    
    # API
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_reload: bool = Field(default=True)
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"]
    )
    
    # Database
    database_url: PostgresDsn = Field(...)
    database_pool_size: int = Field(default=20)
    database_max_overflow: int = Field(default=10)
    
    # Redis
    redis_url: RedisDsn = Field(...)
    redis_max_connections: int = Field(default=50)
    
    # Celery
    celery_broker_url: RedisDsn = Field(...)
    celery_result_backend: RedisDsn = Field(...)
    celery_worker_concurrency: int = Field(default=4)
    
    # Pinecone (for vector storage)
    pinecone_api_key: str = Field(...)
    pinecone_internal_index_host: str = Field(...)
    pinecone_external_index_host: str = Field(...)

    # Vector DB provider selection (default to pinecone)
    vector_db_provider: str = Field(default="pinecone")
    
    # LLM Providers
    llm_provider: str = Field(default="groq")  # "openai", "anthropic", or "groq"
    llm_model: str = Field(default="openai/gpt-oss-20b")
    
    # OpenAI
    openai_api_key: Optional[str] = Field(default=None)
    openai_model: str = Field(default="gpt-4")
    
    # Groq
    groq_api_key: Optional[str] = Field(default=None)
    groq_base_url: str = Field(default="https://api.groq.com/openai/v1")
    groq_model: str = Field(default="openai/gpt-oss-20b")
    
    # Anthropic
    anthropic_api_key: Optional[str] = Field(default=None)
    anthropic_model: str = Field(default="claude-3-opus-20240229")

    # Unified LLM selector used by services/llm.py (prefer Groq)
    llm_provider: str = Field(default="groq")
    llm_model: str = Field(default="llama3-70b-8192")
    
    # Embeddings
    embeddings_provider: str = Field(default="openai")
    embedding_model: str = Field(default="text-embedding-3-large")
    embedding_dimension: int = Field(default=3072)
    embedding_batch_size: int = Field(default=100)
    
    # OCR
    tesseract_path: str = Field(default="/usr/local/bin/tesseract")
    tesseract_lang: str = Field(default="eng+chi_sim")
    ocr_dpi: int = Field(default=300)
    
    # Crawler
    crawler_user_agent: str = Field(
        default="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    )
    crawler_rate_limit: int = Field(default=2)
    crawler_max_retries: int = Field(default=3)
    crawler_timeout: int = Field(default=30)
    crawler_headless: bool = Field(default=True)
    
    hkma_circulars_url: str = Field(
        default="https://www.hkma.gov.hk/eng/regulatory-resources/regulatory-guides/circulars/"
    )
    mas_circulars_url: str = Field(
        default="https://www.mas.gov.sg/regulation/regulations-and-guidance"
    )
    finma_circulars_url: str = Field(
        default="https://www.finma.ch/en/documentation/circulars/"
    )
    
    # World-Check One
    worldcheck_api_key: Optional[str] = Field(default=None)
    worldcheck_api_secret: Optional[str] = Field(default=None)
    worldcheck_group_id: Optional[str] = Field(default=None)
    worldcheck_base_url: str = Field(
        default="https://api-worldcheck.refinitiv.com/v2"
    )
    worldcheck_timeout: int = Field(default=30)
    worldcheck_max_retries: int = Field(default=3)
    
    # File Storage
    upload_dir: str = Field(default="data/uploaded_docs")
    ocr_output_dir: str = Field(default="data/ocr_output")
    reports_dir: str = Field(default="data/reports")
    evidence_dir: str = Field(default="data/evidence")
    external_docs_dir: str = Field(default="data/external_docs")
    max_upload_size_mb: int = Field(default=50)
    
    # Alerts
    alert_sla_hours_front: int = Field(default=24)
    alert_sla_hours_compliance: int = Field(default=48)
    alert_sla_hours_legal: int = Field(default=72)
    alert_websocket_enabled: bool = Field(default=True)
    
    # Bayesian
    bayesian_prior_suspicious: float = Field(default=0.05)
    bayesian_update_threshold: float = Field(default=0.7)
    
    # Transactions
    transaction_batch_size: int = Field(default=100)
    transaction_timeout_seconds: int = Field(default=60)
    transaction_max_retries: int = Field(default=3)
    
    # Documents
    document_processing_timeout: int = Field(default=300)
    document_max_pages: int = Field(default=100)
    image_max_size_mb: int = Field(default=20)
    
    # Feature Flags
    enable_background_check: bool = Field(default=True)
    enable_image_forensics: bool = Field(default=True)
    enable_reverse_image_search: bool = Field(default=False)
    enable_ai_detection: bool = Field(default=True)
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True)
    rate_limit_per_minute: int = Field(default=100)
    rate_limit_burst: int = Field(default=20)
    
    # Security
    jwt_algorithm: str = Field(default="HS256")
    jwt_expiration_minutes: int = Field(default=60)
    jwt_refresh_expiration_days: int = Field(default=7)
    
    # Monitoring
    enable_metrics: bool = Field(default=True)
    enable_tracing: bool = Field(default=False)
    metrics_port: int = Field(default=9090)
    flower_port: int = Field(default=5555)
    



# Global settings instance
settings = Settings()


# Ensure directories exist
def ensure_directories():
    """Create necessary directories if they don't exist."""
    directories = [
        settings.upload_dir,
        settings.ocr_output_dir,
        settings.reports_dir,
        settings.evidence_dir,
        settings.external_docs_dir,
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


# Create directories on import
ensure_directories()
