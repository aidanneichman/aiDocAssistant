"""Chat models for the AI Legal Assistant.

This module defines the data models for chat functionality including
messages, modes, requests, and responses.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from pydantic_settings import SettingsConfigDict


class ChatMode(str, Enum):
    """Chat modes for different types of interactions."""
    REGULAR = "regular"
    DEEP_RESEARCH = "deep_research"


class MessageRole(str, Enum):
    """Roles for chat messages."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    """Individual chat message with role and content."""
    
    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique message ID")
    role: MessageRole = Field(..., description="Message role (system, user, assistant)")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    
    model_config = SettingsConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class DocumentReference(BaseModel):
    """Reference to a document used in chat context."""
    
    document_id: str = Field(..., description="Document ID (SHA-256 hash)")
    filename: str = Field(..., description="Original filename")
    relevance_score: Optional[float] = Field(None, description="Relevance score (0-1)")
    excerpt: Optional[str] = Field(None, description="Relevant excerpt from document")


class ChatRequest(BaseModel):
    """Request payload for chat endpoint."""
    
    message: str = Field(..., description="User message content", min_length=1)
    mode: ChatMode = Field(default=ChatMode.REGULAR, description="Chat mode")
    session_id: Optional[str] = Field(None, description="Chat session ID")
    document_ids: List[str] = Field(default_factory=list, description="Document IDs to include in context")
    max_tokens: Optional[int] = Field(default=None, description="Maximum tokens for response", ge=1, le=4096)
    temperature: Optional[float] = Field(default=None, description="Response randomness (0-1)", ge=0.0, le=1.0)
    
    model_config = SettingsConfigDict(
        json_schema_extra={
            "example": {
                "message": "What are the key points in the contract?",
                "mode": "deep_research",
                "document_ids": ["abc123def456"],
                "max_tokens": 1000,
                "temperature": 0.7
            }
        }
    )


class TokenUsage(BaseModel):
    """Token usage information for a chat completion."""
    
    prompt_tokens: int = Field(..., description="Tokens used in prompt")
    completion_tokens: int = Field(..., description="Tokens used in completion")
    total_tokens: int = Field(..., description="Total tokens used")


class ChatResponse(BaseModel):
    """Response payload for chat endpoint."""
    
    id: str = Field(default_factory=lambda: str(uuid4()), description="Response ID")
    message: ChatMessage = Field(..., description="Assistant's response message")
    mode: ChatMode = Field(..., description="Chat mode used")
    session_id: str = Field(..., description="Chat session ID")
    document_references: List[DocumentReference] = Field(
        default_factory=list, 
        description="Documents referenced in response"
    )
    token_usage: Optional[TokenUsage] = Field(None, description="Token usage information")
    model: str = Field(..., description="Model used for completion")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    
    model_config = SettingsConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class StreamingChatChunk(BaseModel):
    """Individual chunk in a streaming chat response."""
    
    id: str = Field(..., description="Response ID")
    chunk_id: str = Field(default_factory=lambda: str(uuid4()), description="Chunk ID")
    content: str = Field(..., description="Content chunk")
    is_final: bool = Field(default=False, description="Whether this is the final chunk")
    session_id: str = Field(..., description="Chat session ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Chunk timestamp")
    
    model_config = SettingsConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class ChatSession(BaseModel):
    """Chat session containing message history."""
    
    id: str = Field(default_factory=lambda: str(uuid4()), description="Session ID")
    messages: List[ChatMessage] = Field(default_factory=list, description="Message history")
    mode: ChatMode = Field(default=ChatMode.REGULAR, description="Session chat mode")
    document_ids: List[str] = Field(default_factory=list, description="Documents available in session")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Session creation time")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional session metadata")
    
    model_config = SettingsConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )
    
    def add_message(self, role: MessageRole, content: str) -> ChatMessage:
        """Add a message to the session."""
        message = ChatMessage(role=role, content=content)
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
        return message
    
    def get_context_messages(self, max_messages: int = 20) -> List[ChatMessage]:
        """Get recent messages for context, excluding system messages."""
        # Get non-system messages for context
        context_messages = [msg for msg in self.messages if msg.role != MessageRole.SYSTEM]
        
        # Return the most recent messages
        return context_messages[-max_messages:] if max_messages else context_messages
    
    def get_system_message(self) -> Optional[ChatMessage]:
        """Get the current system message."""
        system_messages = [msg for msg in self.messages if msg.role == MessageRole.SYSTEM]
        return system_messages[-1] if system_messages else None


class ModelClientError(Exception):
    """Base exception for model client errors."""
    pass


class ModelClientConnectionError(ModelClientError):
    """Exception raised when model client cannot connect."""
    pass


class ModelClientRateLimitError(ModelClientError):
    """Exception raised when model client hits rate limits."""
    pass


class ModelClientInvalidRequestError(ModelClientError):
    """Exception raised when request is invalid."""
    pass


class ModelClientAuthenticationError(ModelClientError):
    """Exception raised when authentication fails."""
    pass
