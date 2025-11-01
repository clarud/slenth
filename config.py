"""
Configuration management for SLENTH AML Monitoring System.
Loads environment variables and provides typed configuration objects.
"""
from pydantic_settings import BaseSettings
from pydantic import Field, PostgresDsn, RedisDsn
from pathlib import Path
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Main application settings."""
    
    # Application
    app_env: str = Field(default="development", env="APP_ENV")
    app_name: str = Field(default="SLENTH AML Monitor", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=True, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    secret_key: str = Field(..., env="SECRET_KEY")
    
    # API
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_reload: bool = Field(default=True, env="API_RELOAD")
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="CORS_ORIGINS"
    )
    
    # Database
    database_url: PostgresDsn = Field(..., env="DATABASE_URL")
    database_pool_size: int = Field(default=20, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, env="DATABASE_MAX_OVERFLOW")
    
    # Redis
    redis_url: RedisDsn = Field(..., env="REDIS_URL")
    redis_max_connections: int = Field(default=50, env="REDIS_MAX_CONNECTIONS")
    
    # Celery
    celery_broker_url: RedisDsn = Field(..., env="CELERY_BROKER_URL")
    celery_result_backend: RedisDsn = Field(..., env="CELERY_RESULT_BACKEND")
    celery_worker_concurrency: int = Field(default=4, env="CELERY_WORKER_CONCURRENCY")
    
    # Pinecone (for vector storage)
    pinecone_api_key: str = Field(..., env="PINECONE_API_KEY")
    pinecone_internal_index_host: str = Field(..., env="PINECONE_INTERNAL_INDEX_HOST")
    pinecone_external_index_host: str = Field(..., env="PINECONE_EXTERNAL_INDEX_HOST")

    # Vector DB provider selection (default to pinecone)
    vector_db_provider: str = Field(default="pinecone", env="VECTOR_DB_PROVIDER")
    
    # GROQ
    groq_api_key: Optional[str] = Field(default=None, env="GROQ_API_KEY")
    
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-3-opus-20240229", env="ANTHROPIC_MODEL")

    # Unified LLM selector used by services/llm.py (prefer Groq)
    llm_provider: str = Field(default="groq", env="LLM_PROVIDER")
    llm_model: str = Field(default="llama3-70b-8192", env="LLM_MODEL")
    
    # Embeddings
    embeddings_provider: str = Field(default="openai", env="EMBEDDINGS_PROVIDER")
    embedding_model: str = Field(default="text-embedding-3-large", env="EMBEDDING_MODEL")
    embedding_dimension: int = Field(default=3072, env="EMBEDDING_DIMENSION")
    embedding_batch_size: int = Field(default=100, env="EMBEDDING_BATCH_SIZE")
    
    # OCR
    tesseract_path: str = Field(default="/usr/local/bin/tesseract", env="TESSERACT_PATH")
    tesseract_lang: str = Field(default="eng+chi_sim", env="TESSERACT_LANG")
    ocr_dpi: int = Field(default=300, env="OCR_DPI")
    
    # Crawler
    crawler_user_agent: str = Field(
        default="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        env="CRAWLER_USER_AGENT"
    )
    crawler_rate_limit: int = Field(default=2, env="CRAWLER_RATE_LIMIT")
    crawler_max_retries: int = Field(default=3, env="CRAWLER_MAX_RETRIES")
    crawler_timeout: int = Field(default=30, env="CRAWLER_TIMEOUT")
    crawler_headless: bool = Field(default=True, env="CRAWLER_HEADLESS")
    
    hkma_circulars_url: str = Field(
        default="https://www.hkma.gov.hk/eng/regulatory-resources/regulatory-guides/circulars/",
        env="HKMA_CIRCULARS_URL"
    )
    mas_circulars_url: str = Field(
        default="https://www.mas.gov.sg/regulation/regulations-and-guidance",
        env="MAS_CIRCULARS_URL"
    )
    finma_circulars_url: str = Field(
        default="https://www.finma.ch/en/documentation/circulars/",
        env="FINMA_CIRCULARS_URL"
    )
    
    # World-Check One
    worldcheck_api_key: Optional[str] = Field(default=None, env="WORLDCHECK_API_KEY")
    worldcheck_api_secret: Optional[str] = Field(default=None, env="WORLDCHECK_API_SECRET")
    worldcheck_group_id: Optional[str] = Field(default=None, env="WORLDCHECK_GROUP_ID")
    worldcheck_base_url: str = Field(
        default="https://api-worldcheck.refinitiv.com/v2",
        env="WORLDCHECK_BASE_URL"
    )
    worldcheck_timeout: int = Field(default=30, env="WORLDCHECK_TIMEOUT")
    worldcheck_max_retries: int = Field(default=3, env="WORLDCHECK_MAX_RETRIES")
    
    # File Storage
    upload_dir: str = Field(default="data/uploaded_docs", env="UPLOAD_DIR")
    ocr_output_dir: str = Field(default="data/ocr_output", env="OCR_OUTPUT_DIR")
    reports_dir: str = Field(default="data/reports", env="REPORTS_DIR")
    evidence_dir: str = Field(default="data/evidence", env="EVIDENCE_DIR")
    external_docs_dir: str = Field(default="data/external_docs", env="EXTERNAL_DOCS_DIR")
    max_upload_size_mb: int = Field(default=50, env="MAX_UPLOAD_SIZE_MB")
    
    # Alerts
    alert_sla_hours_front: int = Field(default=24, env="ALERT_SLA_HOURS_FRONT")
    alert_sla_hours_compliance: int = Field(default=48, env="ALERT_SLA_HOURS_COMPLIANCE")
    alert_sla_hours_legal: int = Field(default=72, env="ALERT_SLA_HOURS_LEGAL")
    alert_websocket_enabled: bool = Field(default=True, env="ALERT_WEBSOCKET_ENABLED")
    
    # Bayesian
    bayesian_prior_suspicious: float = Field(default=0.05, env="BAYESIAN_PRIOR_SUSPICIOUS")
    bayesian_update_threshold: float = Field(default=0.7, env="BAYESIAN_UPDATE_THRESHOLD")
    
    # Transactions
    transaction_batch_size: int = Field(default=100, env="TRANSACTION_BATCH_SIZE")
    transaction_timeout_seconds: int = Field(default=60, env="TRANSACTION_TIMEOUT_SECONDS")
    transaction_max_retries: int = Field(default=3, env="TRANSACTION_MAX_RETRIES")
    
    # Documents
    document_processing_timeout: int = Field(default=300, env="DOCUMENT_PROCESSING_TIMEOUT")
    document_max_pages: int = Field(default=100, env="DOCUMENT_MAX_PAGES")
    image_max_size_mb: int = Field(default=20, env="IMAGE_MAX_SIZE_MB")
    
    # Feature Flags
    enable_background_check: bool = Field(default=True, env="ENABLE_BACKGROUND_CHECK")
    enable_image_forensics: bool = Field(default=True, env="ENABLE_IMAGE_FORENSICS")
    enable_reverse_image_search: bool = Field(default=False, env="ENABLE_REVERSE_IMAGE_SEARCH")
    enable_ai_detection: bool = Field(default=True, env="ENABLE_AI_DETECTION")
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_per_minute: int = Field(default=100, env="RATE_LIMIT_PER_MINUTE")
    rate_limit_burst: int = Field(default=20, env="RATE_LIMIT_BURST")
    
    # Security
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_minutes: int = Field(default=60, env="JWT_EXPIRATION_MINUTES")
    jwt_refresh_expiration_days: int = Field(default=7, env="JWT_REFRESH_EXPIRATION_DAYS")
    
    # Monitoring
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    enable_tracing: bool = Field(default=False, env="ENABLE_TRACING")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    flower_port: int = Field(default=5555, env="FLOWER_PORT")
    
    class Config:
        # Resolve .env relative to this file so it works regardless of CWD
        env_file = str(Path(__file__).with_name(".env"))
        env_file_encoding = "utf-8"
        case_sensitive = False


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
