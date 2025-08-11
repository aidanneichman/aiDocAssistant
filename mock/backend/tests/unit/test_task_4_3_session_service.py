"""Unit tests for Task 4.3: Session persistence service."""

import asyncio
from pathlib import Path

import pytest

from backend.app.models.chat import ChatMode, ChatSession, ChatMessage, MessageRole
from backend.app.services.session_service import SessionService


@pytest.mark.asyncio
async def test_save_and_load_session(tmp_path: Path):
    service = SessionService(session_path=tmp_path)

    session = ChatSession(mode=ChatMode.REGULAR)
    session.add_message(MessageRole.USER, "Hello")
    session.add_message(MessageRole.ASSISTANT, "Hi there")

    await service.save_session(session)

    loaded = await service.load_session(session.id)
    assert loaded is not None
    assert loaded.id == session.id
    assert len(loaded.messages) == 2


@pytest.mark.asyncio
async def test_list_and_delete_sessions(tmp_path: Path):
    service = SessionService(session_path=tmp_path)

    s1 = ChatSession(mode=ChatMode.REGULAR)
    s2 = ChatSession(mode=ChatMode.DEEP_RESEARCH)
    await service.save_session(s1)
    await service.save_session(s2)

    sessions = await service.list_sessions()
    ids = {s.id for s in sessions}
    assert s1.id in ids and s2.id in ids

    deleted = await service.delete_session(s1.id)
    assert deleted is True

    still = await service.load_session(s1.id)
    assert still is None


