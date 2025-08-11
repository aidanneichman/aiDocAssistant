"""Chat routes supporting sessions and streaming responses (SSE)."""

import json
from typing import AsyncIterator, Callable, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.app.clients.openai_client import create_openai_client
from backend.app.clients.streaming_handler import StreamingHandler, get_streaming_handler
from backend.app.config import get_settings
from backend.app.models.chat import ChatMode
from backend.app.services.chat_service import ChatService, get_chat_service
from backend.app.utils.sse_utils import SSEFormatter, SSEStreamManager, get_sse_manager


router = APIRouter(prefix="/api/chat", tags=["chat"])


class CreateSessionRequest(BaseModel):
    mode: ChatMode = ChatMode.REGULAR
    document_ids: List[str] = []


class SessionResponse(BaseModel):
    id: str
    mode: ChatMode
    document_ids: List[str]


class SendMessageRequest(BaseModel):
    message: str
    mode: Optional[ChatMode] = None
    document_ids: Optional[List[str]] = None


class SessionHistoryResponse(BaseModel):
    id: str
    mode: ChatMode
    document_ids: List[str]
    messages: List[Dict]


def _create_model_client_factory():
    settings = get_settings()
    def factory():
        return create_openai_client(api_key=settings.openai_api_key, model="gpt-3.5-turbo")
    return factory


@router.post("/sessions", response_model=SessionResponse)
async def create_session(payload: CreateSessionRequest, chat: ChatService = Depends(get_chat_service)):
    session = chat.create_session(mode=payload.mode, document_ids=payload.document_ids)
    return SessionResponse(id=session.id, mode=session.mode, document_ids=session.document_ids)


@router.get("/sessions", response_model=List[SessionResponse])
async def list_sessions(chat: ChatService = Depends(get_chat_service)):
    sessions = chat.list_sessions()
    return [SessionResponse(id=s.id, mode=s.mode, document_ids=s.document_ids) for s in sessions]


@router.get("/sessions/{session_id}", response_model=SessionHistoryResponse)
async def get_session(session_id: str, chat: ChatService = Depends(get_chat_service)):
    session = chat.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionHistoryResponse(
        id=session.id,
        mode=session.mode,
        document_ids=session.document_ids,
        messages=[m.model_dump(mode="json") for m in session.messages],
    )


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    payload: SendMessageRequest,
    request: Request,
    chat: ChatService = Depends(get_chat_service),
):
    session = chat.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    settings = get_settings()
    sse_manager: SSEStreamManager = get_sse_manager()
    streaming_handler: StreamingHandler = get_streaming_handler()

    # Select mode and document IDs
    mode = payload.mode or session.mode
    document_ids = payload.document_ids if payload.document_ids is not None else session.document_ids

    model_client_factory = _create_model_client_factory()

    async def sse_generator() -> AsyncIterator[str]:
        try:
            # Start streaming from model via chat service
            token_iterator = chat.stream_reply(
                session_id=session_id,
                user_message=payload.message,
                mode=mode,
                document_ids=document_ids,
                create_model_client=model_client_factory,
            )

            async for chunk in sse_manager.stream_chat_response(
                streaming_handler.stream_response(
                    token_iterator,
                    response_id=session_id,
                    session_id=session_id,
                ),
                session_id=session_id,
                response_id=session_id,
            ):
                yield chunk
        except Exception as e:
            yield SSEFormatter.format_error(str(e)).format()

    headers = sse_manager.create_connection_headers()
    return StreamingResponse(sse_generator(), media_type="text/event-stream", headers=headers)


