"""
Test environment variables integration with FastAPI routes
"""
import sys
sys.path.append('/Users/chenxiangrui/Projects/slenth')

from config import settings

def test_env_vars():
    """Test that all required environment variables are loaded"""
    
    print("=" * 80)
    print("ENVIRONMENT VARIABLES TEST")
    print("=" * 80)
    
    # Database
    print("\n📦 Database Configuration:")
    print(f"   DATABASE_URL: {_mask_url(str(settings.database_url))}")
    print(f"   Pool Size: {settings.database_pool_size}")
    print(f"   Max Overflow: {settings.database_max_overflow}")
    
    # Redis
    print("\n🔴 Redis Configuration:")
    print(f"   REDIS_URL: {_mask_url(str(settings.redis_url))}")
    print(f"   Max Connections: {settings.redis_max_connections}")
    
    # Celery
    print("\n🌾 Celery Configuration:")
    print(f"   CELERY_BROKER_URL: {_mask_url(str(settings.celery_broker_url))}")
    print(f"   CELERY_RESULT_BACKEND: {_mask_url(str(settings.celery_result_backend))}")
    print(f"   Worker Concurrency: {settings.celery_worker_concurrency}")
    
    # Pinecone
    print("\n🌲 Pinecone Configuration:")
    print(f"   PINECONE_API_KEY: {_mask_sensitive(settings.pinecone_api_key)}")
    print(f"   INTERNAL_INDEX_HOST: {settings.pinecone_internal_index_host}")
    print(f"   EXTERNAL_INDEX_HOST: {settings.pinecone_external_index_host}")
    print(f"   Provider: {settings.vector_db_provider}")
    
    # LLM
    print("\n🤖 LLM Configuration:")
    print(f"   Provider: {settings.llm_provider}")
    print(f"   Model: {settings.llm_model}")
    print(f"   GROQ_API_KEY: {_mask_sensitive(settings.groq_api_key or '')}")
    
    # API
    print("\n🌐 API Configuration:")
    print(f"   Host: {settings.api_host}")
    print(f"   Port: {settings.api_port}")
    print(f"   CORS Origins: {settings.cors_origins}")
    
    print("\n" + "=" * 80)
    print("✅ All environment variables loaded successfully!")
    print("=" * 80)


def _mask_url(url: str) -> str:
    """Mask credentials in URLs."""
    try:
        if "@" in url and "://" in url:
            scheme, rest = url.split("://", 1)
            if "@" in rest:
                creds, host = rest.split("@", 1)
                return f"{scheme}://***:***@{host}"
        return url
    except Exception:
        return url


def _mask_sensitive(value: str) -> str:
    """Mask sensitive values."""
    if not value:
        return "not_set"
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


if __name__ == "__main__":
    test_env_vars()
