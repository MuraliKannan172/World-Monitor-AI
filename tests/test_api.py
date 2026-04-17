"""Smoke tests for FastAPI endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.fixture
async def client():
    with (
        patch("app.db.init_db", new=AsyncMock()),
        patch("app.geo.ensure_gazetteer", new=AsyncMock()),
        patch("app.geo.build_index", return_value=None),
        patch("spacy.load", return_value=MagicMock()),
        patch("app.scheduler.start", return_value=None),
        patch("app.scheduler.stop", return_value=None),
        patch("app.main.data_pipeline_first_run", new=AsyncMock()),
    ):
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_events_endpoint(client):
    with patch("app.db.fetch_events", new=AsyncMock(return_value=[])):
        resp = await client.get("/api/events")
    assert resp.status_code == 200
    data = resp.json()
    assert "events" in data
    assert "count" in data


@pytest.mark.asyncio
async def test_models_endpoint_ollama_down(client):
    with patch("app.ollama_client.ollama.list_models", new=AsyncMock(return_value=[])):
        resp = await client.get("/api/models")
    assert resp.status_code == 200
    data = resp.json()
    assert "models" in data
    assert isinstance(data["models"], list)


@pytest.mark.asyncio
async def test_events_filter_params(client):
    with patch("app.db.fetch_events", new=AsyncMock(return_value=[])) as mock_fetch:
        resp = await client.get("/api/events?categories=cyber&min_severity=5")
    assert resp.status_code == 200
