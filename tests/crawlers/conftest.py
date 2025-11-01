"""
Test configuration and fixtures for crawler tests.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from db.database import Base


@pytest.fixture
def mock_db_session():
    """Create a mock database session for testing"""
    # Use in-memory SQLite for testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    
    yield session
    
    session.close()


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service"""
    mock = Mock()
    mock.embed_text = Mock(return_value=[0.1] * 1536)  # OpenAI embedding size
    mock.embed_batch = Mock(return_value=[[0.1] * 1536])
    return mock


@pytest.fixture
def mock_vector_db():
    """Mock vector database service"""
    mock = Mock()
    mock.upsert_vectors = Mock(return_value=True)
    mock.hybrid_search = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def sample_hkma_html():
    """Sample HKMA HTML page for testing"""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>HKMA Circulars</title></head>
    <body>
        <div class="circular-list">
            <div class="circular-item">
                <h3><a href="/circular/2024/aml-cdd-guidelines">Customer Due Diligence Guidelines</a></h3>
                <span class="date">15 January 2024</span>
                <p class="summary">Updated guidelines on customer due diligence for AML compliance...</p>
            </div>
            <div class="circular-item">
                <h3><a href="/circular/2024/str-reporting">Suspicious Transaction Reporting</a></h3>
                <span class="date">20 March 2024</span>
                <p class="summary">Requirements for suspicious transaction reporting...</p>
            </div>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def sample_mas_html():
    """Sample MAS HTML page for testing"""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>MAS Notices</title></head>
    <body>
        <div class="notice-list">
            <article class="notice">
                <h2><a href="/notice/PSN02-AML">Prevention of Money Laundering</a></h2>
                <time datetime="2024-02-01">1 February 2024</time>
                <div class="content">Notice on prevention of money laundering and countering financing of terrorism...</div>
            </article>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def sample_finma_html():
    """Sample FINMA HTML page for testing"""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>FINMA Circulars</title></head>
    <body>
        <div class="circulars">
            <div class="circular">
                <a href="/circular/2024-01-aml" class="title">Anti-Money Laundering Circular 2024/1</a>
                <span class="date">20.01.2024</span>
                <div class="abstract">This circular sets out requirements for anti-money laundering compliance...</div>
            </div>
        </div>
    </body>
    </html>
    """
