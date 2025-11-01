"""
Test configuration and fixtures for crawler tests.
"""

import json
import os
import sys
from pathlib import Path

import pytest
from unittest.mock import Mock, AsyncMock

# Ensure project root is on sys.path so `import crawlers` works when running tests directly
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


@pytest.fixture(scope="session")
def output_dir() -> Path:
    """Directory to store crawler outputs for inspection during tests."""
    out = Path("tests/crawlers/output")
    out.mkdir(parents=True, exist_ok=True)
    return out


@pytest.fixture(scope="function")
def clean_output_files(output_dir):
    """Clean output files before each test to avoid duplicate data."""
    for file in output_dir.glob("*.jsonl"):
        file.unlink()
    yield
    # Keep files after test for inspection


class _FileSaver:
    """Helper to save items to a JSONL file with basic duplicate handling."""

    def __init__(self, output_dir: Path):
        self._seen = set()
        self._output_dir = output_dir

    def save(self, items, filename: str):
        """Save items to output directory with given filename."""
        path = self._output_dir / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        saved = 0
        with path.open("a", encoding="utf-8") as f:
            for it in items:
                key = (it.get("source"), it.get("title"), it.get("url"))
                if key in self._seen:
                    continue
                self._seen.add(key)
                # Create a clean dict with proper formatting
                output_item = {
                    "title": it.get("title", ""),
                    "url": it.get("url", ""),
                    "date": str(it.get("date", "")),
                    "content": it.get("content", "")[:500] + "..." if len(it.get("content", "")) > 500 else it.get("content", ""),
                    "source": it.get("source", ""),
                    "jurisdiction": it.get("jurisdiction", ""),
                    "rule_type": it.get("rule_type", ""),
                }
                f.write(json.dumps(output_item, default=str, ensure_ascii=False) + "\n")
                saved += 1
        return saved


@pytest.fixture(scope="function")
def file_saver(output_dir) -> _FileSaver:
    """Function-scoped file saver for each test."""
    return _FileSaver(output_dir)
