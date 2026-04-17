"""Tests for RSS ingest pipeline."""

import asyncio
import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.data_pipeline import _compute_sha256, _extract_locations, _process_entry
from app.feeds import FeedSource


def test_sha256_deterministic():
    assert _compute_sha256("title", "link") == _compute_sha256("title", "link")


def test_sha256_unique():
    a = _compute_sha256("title A", "link A")
    b = _compute_sha256("title B", "link B")
    assert a != b


def test_sha256_format():
    result = _compute_sha256("t", "l")
    assert len(result) == 64
    assert all(c in "0123456789abcdef" for c in result)


def test_extract_locations_no_model():
    """Stub test: ensure function handles empty doc gracefully."""
    nlp_mock = MagicMock()
    doc_mock = MagicMock()
    doc_mock.ents = []
    nlp_mock.return_value = doc_mock

    from app import geo
    original_resolve = geo.resolve
    geo.resolve = lambda _: None

    result = _extract_locations(nlp_mock, "Hello world")
    assert result == []

    geo.resolve = original_resolve


def test_feed_registry_count():
    from app.feeds import FEEDS
    assert len(FEEDS) >= 55


def test_feed_registry_categories():
    from app.feeds import FEEDS
    cats = {f.category for f in FEEDS}
    expected = {"world", "geopolitics", "conflict", "cyber", "energy", "finance",
                "regional_asia", "regional_europe", "regional_americas", "tech"}
    assert expected.issubset(cats)


def test_feed_sources_have_urls():
    from app.feeds import FEEDS
    for feed in FEEDS:
        assert feed.url.startswith("http"), f"Bad URL for {feed.name}"
        assert feed.name
        assert feed.category
