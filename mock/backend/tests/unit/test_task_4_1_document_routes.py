"""Unit tests for Task 4.1: Document Upload Endpoint."""

import io
import json
from pathlib import Path

import pytest
import httpx

from backend.app.main import app


def create_file(content: bytes, filename: str, content_type: str):
    return (
        filename,
        content,
        content_type,
    )


@pytest.mark.asyncio
async def test_upload_single_text_file(tmp_path, monkeypatch):
    # Prepare file
    content = b"Hello world from a text file"
    files = {
        "files": ("hello.txt", content, "text/plain"),
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/documents/upload", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert "documents" in data
    assert len(data["documents"]) == 1
    assert data["documents"][0]["original_filename"].endswith("hello.txt")


@pytest.mark.asyncio
async def test_upload_rejects_unsupported_type():
    content = b"\x89PNG\r\n\x1a\nFakePNG"
    files = {
        "files": ("image.png", content, "image/png"),
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/documents/upload", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["documents"]) == 0
    assert len(data["errors"]) == 1
    assert data["errors"][0]["code"] in ("INVALID_FILE", "STORAGE_ERROR", "UNKNOWN_ERROR")


@pytest.mark.asyncio
async def test_list_documents():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/documents")
    assert resp.status_code == 200
    data = resp.json()
    assert "documents" in data
    assert isinstance(data["documents"], list)


@pytest.mark.asyncio
async def test_delete_nonexistent_document():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.delete("/api/documents/doesnotexist")
    assert resp.status_code == 404


