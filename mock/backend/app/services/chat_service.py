"""Chat service providing session management and streaming replies."""

import asyncio
import uuid
from typing import AsyncIterator, Callable, Dict, List, Optional

from backend.app.models.chat import (
    ChatMessage,
    ChatMode,
    ChatSession,
    MessageRole,
)
from backend.app.models.document import Document
from backend.app.services.document_service import DocumentService, get_document_service


class ChatService:
    """In-memory chat service managing sessions and streaming replies."""

    def __init__(self, document_service: Optional[DocumentService] = None):
        self._sessions: Dict[str, ChatSession] = {}
        self._document_service = document_service or get_document_service()

    def create_session(self, mode: ChatMode = ChatMode.REGULAR, document_ids: Optional[List[str]] = None) -> ChatSession:
        session = ChatSession(mode=mode, document_ids=document_ids or [])
        self._sessions[session.id] = session
        return session

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        return self._sessions.get(session_id)

    def list_sessions(self) -> List[ChatSession]:
        return list(self._sessions.values())

    async def _get_documents(self, document_ids: List[str]) -> List[Document]:
        documents: List[Document] = []
        for doc_id in document_ids:
            doc = await self._document_service.get_document(doc_id)
            if doc is not None:
                documents.append(doc)
        return documents

    async def stream_reply(
        self,
        session_id: str,
        user_message: str,
        mode: ChatMode,
        document_ids: Optional[List[str]],
        create_model_client: Callable[[], any],
    ) -> AsyncIterator[str]:
        """Stream a model reply as a sequence of content chunks.

        Accumulates assistant content into the session after completion.
        """
        session = self.get_session(session_id)
        if session is None:
            raise ValueError("Session not found")

        # Record user message
        session.add_message(MessageRole.USER, user_message)

        # Get documents for context if provided
        documents: List[Document] = []
        if document_ids:
            documents = await self._get_documents(document_ids)

        # Create model client
        model_client = create_model_client()

        # Build message context (exclude system messages)
        context_messages: List[ChatMessage] = session.get_context_messages(max_messages=20)

        # Stream reply
        accumulated: List[str] = []
        async for token in model_client.chat_completion(messages=context_messages, mode=mode, documents=documents):
            if token:
                accumulated.append(token)
                yield token

        # Save assistant message
        assistant_text = "".join(accumulated)
        session.add_message(MessageRole.ASSISTANT, assistant_text)


# Singleton instance
_chat_service: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service


