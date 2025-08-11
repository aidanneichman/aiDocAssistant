"""Session persistence service for chat sessions.

Stores and retrieves `ChatSession` objects on local disk as JSON.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional

import aiofiles
import aiofiles.os

from backend.app.config import get_settings
from backend.app.models.chat import ChatSession


logger = logging.getLogger(__name__)


class SessionPersistenceError(Exception):
    """Base exception for session persistence errors."""


class SessionService:
    """Persist chat sessions to local disk as JSON files."""

    def __init__(self, session_path: Optional[Path] = None) -> None:
        settings = get_settings()
        self.session_path: Path = (session_path or settings.session_storage_path).resolve()
        self.session_path.mkdir(parents=True, exist_ok=True)

    def _session_file(self, session_id: str) -> Path:
        return self.session_path / f"{session_id}.json"

    async def save_session(self, session: ChatSession) -> None:
        try:
            file_path = self._session_file(session.id)
            async with aiofiles.open(file_path, "w") as f:
                await f.write(json.dumps(session.model_dump(mode="json"), indent=2))
        except Exception as e:
            logger.error(f"Failed to save session {session.id}: {e}")
            raise SessionPersistenceError(f"Failed to save session: {e}") from e

    async def load_session(self, session_id: str) -> Optional[ChatSession]:
        try:
            file_path = self._session_file(session_id)
            if not await aiofiles.os.path.exists(file_path):
                return None
            async with aiofiles.open(file_path, "r") as f:
                data = await f.read()
            payload = json.loads(data)
            return ChatSession(**payload)
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            raise SessionPersistenceError(f"Failed to load session: {e}") from e

    async def delete_session(self, session_id: str) -> bool:
        try:
            file_path = self._session_file(session_id)
            if await aiofiles.os.path.exists(file_path):
                await aiofiles.os.remove(file_path)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            raise SessionPersistenceError(f"Failed to delete session: {e}") from e

    async def list_sessions(self) -> List[ChatSession]:
        sessions: List[ChatSession] = []
        try:
            if not self.session_path.exists():
                return sessions
            for file in self.session_path.glob("*.json"):
                try:
                    async with aiofiles.open(file, "r") as f:
                        data = await f.read()
                    payload = json.loads(data)
                    sessions.append(ChatSession(**payload))
                except Exception as e:
                    logger.warning(f"Skipping invalid session file {file}: {e}")
                    continue
            return sessions
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            raise SessionPersistenceError(f"Failed to list sessions: {e}") from e


