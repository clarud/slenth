"""
Pytest configuration for SLENTH test suite.
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure pytest
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (require real services)"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests (use mocks)"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
