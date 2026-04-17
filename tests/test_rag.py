"""Tests for RAG retrieval."""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_build_context_empty_db():
    """When DB is empty, context should be empty string."""
    with patch("app.db.fts_search", new=AsyncMock(return_value=[])):
        from app.rag import build_context
        ctx, sources = await build_context("test query")
    assert ctx == ""
    assert sources == []


@pytest.mark.asyncio
async def test_build_context_with_snippets():
    """Context block should include snippet text."""
    snippets = [
        {
            "id": 1,
            "title": "Major earthquake in Turkey",
            "summary": "A powerful earthquake struck eastern Turkey",
            "link": "https://example.com/1",
            "source_name": "Reuters",
            "published_at": "2025-01-01T00:00:00",
            "country": "TR",
        }
    ]
    with patch("app.db.fts_search", new=AsyncMock(return_value=snippets)):
        from app.rag import build_context
        ctx, sources = await build_context("earthquake")
    assert "earthquake" in ctx.lower() or "turkey" in ctx.lower()
    assert len(sources) == 1


@pytest.mark.asyncio
async def test_build_context_numbering():
    """Each snippet should be numbered in the context block."""
    snippets = [
        {"id": i, "title": f"Event {i}", "summary": "Summary", "link": f"http://x.com/{i}",
         "source_name": "Test", "published_at": None, "country": "US"}
        for i in range(1, 4)
    ]
    with patch("app.db.fts_search", new=AsyncMock(return_value=snippets)):
        from app.rag import build_context
        ctx, _ = await build_context("world events")
    assert "[1]" in ctx
    assert "[2]" in ctx
    assert "[3]" in ctx
