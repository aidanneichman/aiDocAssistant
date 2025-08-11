"""Unit tests for Task 4.2: Chat endpoint with streaming."""

import asyncio
import json

import pytest
import httpx

from backend.app.main import app


@pytest.mark.asyncio
async def test_create_session_and_list():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Create
        resp = await client.post("/api/chat/sessions", json={"mode": "regular", "document_ids": []})
        assert resp.status_code == 200
        session = resp.json()
        assert "id" in session

        # List
        resp2 = await client.get("/api/chat/sessions")
        assert resp2.status_code == 200
        sessions = resp2.json()
        assert any(s["id"] == session["id"] for s in sessions)


@pytest.mark.asyncio
async def test_session_history_not_found():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/chat/sessions/doesnotexist")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_send_message_streams_sse(monkeypatch):
    # Patch model client factory to yield a small stream
    from backend.app.routes import chat as chat_routes

    async def fake_stream(messages, mode, documents=None, **kwargs):
        for t in ["Hello", " ", "world"]:
            yield t

    class FakeClient:
        def __init__(self):
            self._used = True

        async def chat_completion(self, messages, mode, documents=None, **kwargs):
            async for t in fake_stream(messages, mode, documents, **kwargs):
                yield t

    def fake_factory():
        return FakeClient()

    monkeypatch.setattr(chat_routes, "_create_model_client_factory", lambda: fake_factory)

    # Create session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/chat/sessions", json={})
        assert resp.status_code == 200
        session = resp.json()
        sid = session["id"]

        # Send message and get stream
        resp2 = await client.post(f"/api/chat/sessions/{sid}/messages", json={"message": "Hi"})
        assert resp2.status_code == 200
        # Collect stream by reading as text
        text = resp2.text
        assert "event:" in text
        assert "data:" in text
        assert "Hello" in text


