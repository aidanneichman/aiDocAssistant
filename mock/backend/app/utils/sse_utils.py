"""Server-Sent Events (SSE) utilities for real-time streaming.

This module provides utilities for formatting and managing Server-Sent Events
for real-time communication between the backend and frontend.
"""

import json
import logging
from typing import Dict, Any, Optional, AsyncIterator, Union
from datetime import datetime
from enum import Enum

from backend.app.models.chat import StreamingChatChunk

logger = logging.getLogger(__name__)


class SSEEventType(str, Enum):
    """SSE event types for different message categories."""
    TOKEN = "token"
    ERROR = "error"
    DONE = "done"
    KEEPALIVE = "keepalive"
    METADATA = "metadata"
    STATUS = "status"


class SSEMessage:
    """Represents a Server-Sent Event message."""
    
    def __init__(
        self,
        data: Union[str, Dict[str, Any]],
        event_type: Optional[str] = None,
        event_id: Optional[str] = None,
        retry: Optional[int] = None
    ):
        """Initialize SSE message.
        
        Args:
            data: Message data (string or dict)
            event_type: Event type identifier
            event_id: Unique event ID
            retry: Retry interval in milliseconds
        """
        self.data = data
        self.event_type = event_type
        self.event_id = event_id
        self.retry = retry
        self.timestamp = datetime.utcnow()

    def format(self) -> str:
        """Format message as SSE string.
        
        Returns:
            str: Formatted SSE message
        """
        lines = []
        
        # Add event type
        if self.event_type:
            lines.append(f"event: {self.event_type}")
        
        # Add event ID
        if self.event_id:
            lines.append(f"id: {self.event_id}")
        
        # Add retry interval
        if self.retry is not None:
            lines.append(f"retry: {self.retry}")
        
        # Add data
        data_str = self._format_data()
        for line in data_str.split('\n'):
            lines.append(f"data: {line}")
        
        # Add empty line to complete the event (SSE requires double newline)
        lines.append("")
        
        return '\n'.join(lines) + '\n'

    def _format_data(self) -> str:
        """Format data for SSE transmission.
        
        Returns:
            str: Formatted data string
        """
        if isinstance(self.data, str):
            return self.data
        elif isinstance(self.data, dict):
            return json.dumps(self.data, ensure_ascii=False)
        else:
            return json.dumps({"value": self.data}, ensure_ascii=False)

    def __str__(self) -> str:
        return self.format()


class SSEFormatter:
    """Formats various message types as SSE messages."""
    
    @staticmethod
    def format_token(
        content: str,
        chunk_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SSEMessage:
        """Format token content as SSE message.
        
        Args:
            content: Token content
            chunk_id: Chunk identifier
            metadata: Additional metadata
            
        Returns:
            SSEMessage: Formatted token message
        """
        data = {
            "type": SSEEventType.TOKEN,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if metadata:
            data.update(metadata)
        
        return SSEMessage(
            data=data,
            event_type=SSEEventType.TOKEN,
            event_id=chunk_id
        )

    @staticmethod
    def format_error(
        error_message: str,
        error_code: Optional[str] = None,
        error_id: Optional[str] = None
    ) -> SSEMessage:
        """Format error as SSE message.
        
        Args:
            error_message: Error message
            error_code: Error code identifier
            error_id: Error event ID
            
        Returns:
            SSEMessage: Formatted error message
        """
        data = {
            "type": SSEEventType.ERROR,
            "message": error_message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if error_code:
            data["code"] = error_code
        
        return SSEMessage(
            data=data,
            event_type=SSEEventType.ERROR,
            event_id=error_id
        )

    @staticmethod
    def format_completion(
        message: str = "Stream completed",
        final_metadata: Optional[Dict[str, Any]] = None,
        completion_id: Optional[str] = None
    ) -> SSEMessage:
        """Format stream completion as SSE message.
        
        Args:
            message: Completion message
            final_metadata: Final metadata (e.g., token usage)
            completion_id: Completion event ID
            
        Returns:
            SSEMessage: Formatted completion message
        """
        data = {
            "type": SSEEventType.DONE,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if final_metadata:
            data["metadata"] = final_metadata
        
        return SSEMessage(
            data=data,
            event_type=SSEEventType.DONE,
            event_id=completion_id
        )

    @staticmethod
    def format_keepalive(keepalive_id: Optional[str] = None) -> SSEMessage:
        """Format keepalive message.
        
        Args:
            keepalive_id: Keepalive event ID
            
        Returns:
            SSEMessage: Formatted keepalive message
        """
        data = {
            "type": SSEEventType.KEEPALIVE,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return SSEMessage(
            data=data,
            event_type=SSEEventType.KEEPALIVE,
            event_id=keepalive_id
        )

    @staticmethod
    def format_status(
        status: str,
        details: Optional[Dict[str, Any]] = None,
        status_id: Optional[str] = None
    ) -> SSEMessage:
        """Format status update as SSE message.
        
        Args:
            status: Status message
            details: Additional status details
            status_id: Status event ID
            
        Returns:
            SSEMessage: Formatted status message
        """
        data = {
            "type": SSEEventType.STATUS,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if details:
            data["details"] = details
        
        return SSEMessage(
            data=data,
            event_type=SSEEventType.STATUS,
            event_id=status_id
        )

    @staticmethod
    def format_chunk(chunk: StreamingChatChunk) -> SSEMessage:
        """Format StreamingChatChunk as SSE message.
        
        Args:
            chunk: Streaming chat chunk
            
        Returns:
            SSEMessage: Formatted chunk message
        """
        if chunk.is_final:
            return SSEFormatter.format_completion(
                message="Chat response completed",
                completion_id=chunk.chunk_id
            )
        else:
            return SSEFormatter.format_token(
                content=chunk.content,
                chunk_id=chunk.chunk_id,
                metadata={
                    "session_id": chunk.session_id,
                    "response_id": chunk.id
                }
            )


class SSEStreamManager:
    """Manages SSE streaming connections and message delivery."""
    
    def __init__(
        self,
        keepalive_interval: float = 30.0,
        retry_interval: int = 3000,
        max_message_size: int = 65536
    ):
        """Initialize SSE stream manager.
        
        Args:
            keepalive_interval: Interval for keepalive messages (seconds)
            retry_interval: Client retry interval (milliseconds)
            max_message_size: Maximum message size in bytes
        """
        self.keepalive_interval = keepalive_interval
        self.retry_interval = retry_interval
        self.max_message_size = max_message_size
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")

    async def stream_chat_response(
        self,
        chunks: AsyncIterator[StreamingChatChunk],
        session_id: str,
        response_id: str
    ) -> AsyncIterator[str]:
        """Stream chat response chunks as SSE messages.
        
        Args:
            chunks: Async iterator of streaming chat chunks
            session_id: Chat session ID
            response_id: Response ID
            
        Yields:
            str: Formatted SSE messages
        """
        try:
            self.logger.info(f"Starting SSE stream for response {response_id}")
            
            # Send initial status
            status_msg = SSEFormatter.format_status(
                "streaming_started",
                details={
                    "session_id": session_id,
                    "response_id": response_id
                }
            )
            yield status_msg.format()
            
            chunk_count = 0
            async for chunk in chunks:
                chunk_count += 1
                
                # Format chunk as SSE message
                sse_message = SSEFormatter.format_chunk(chunk)
                formatted_message = sse_message.format()
                
                # Check message size
                if len(formatted_message) > self.max_message_size:
                    self.logger.warning(f"Message size ({len(formatted_message)}) exceeds limit")
                    # Split large messages or send error
                    error_msg = SSEFormatter.format_error(
                        "Message too large",
                        error_code="MESSAGE_TOO_LARGE"
                    )
                    yield error_msg.format()
                    continue
                
                yield formatted_message
                
                self.logger.debug(f"Sent SSE chunk {chunk_count}")
            
            self.logger.info(f"SSE stream completed: {chunk_count} chunks")
            
        except Exception as e:
            self.logger.error(f"SSE streaming error: {e}")
            
            # Send error message
            error_msg = SSEFormatter.format_error(
                f"Streaming failed: {str(e)}",
                error_code="STREAMING_ERROR"
            )
            yield error_msg.format()

    async def stream_with_keepalive(
        self,
        message_iterator: AsyncIterator[str],
        connection_id: Optional[str] = None
    ) -> AsyncIterator[str]:
        """Stream messages with periodic keepalive.
        
        Args:
            message_iterator: Iterator of SSE messages
            connection_id: Connection identifier
            
        Yields:
            str: SSE messages with keepalive
        """
        import asyncio
        from datetime import datetime, timedelta
        
        last_message_time = datetime.utcnow()
        
        try:
            async for message in message_iterator:
                yield message
                last_message_time = datetime.utcnow()
                
                # Check if we need keepalive
                if (datetime.utcnow() - last_message_time).total_seconds() >= self.keepalive_interval:
                    keepalive_msg = SSEFormatter.format_keepalive(connection_id)
                    yield keepalive_msg.format()
                    last_message_time = datetime.utcnow()
                    
        except Exception as e:
            self.logger.error(f"Keepalive streaming error: {e}")
            raise

    def create_connection_headers(self) -> Dict[str, str]:
        """Create headers for SSE connection.
        
        Returns:
            dict: HTTP headers for SSE response
        """
        return {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }

    def format_connection_established(self, connection_id: str) -> str:
        """Format connection established message.
        
        Args:
            connection_id: Connection identifier
            
        Returns:
            str: Formatted connection message
        """
        msg = SSEFormatter.format_status(
            "connection_established",
            details={
                "connection_id": connection_id,
                "retry_interval": self.retry_interval
            }
        )
        
        return msg.format()


def create_sse_stream_manager(**config) -> SSEStreamManager:
    """Factory function to create SSE stream manager.
    
    Args:
        **config: Configuration options
        
    Returns:
        SSEStreamManager: Configured stream manager
    """
    return SSEStreamManager(**config)


# Global SSE manager instance
_default_sse_manager: Optional[SSEStreamManager] = None


def get_sse_manager() -> SSEStreamManager:
    """Get the default SSE stream manager.
    
    Returns:
        SSEStreamManager: Default SSE manager
    """
    global _default_sse_manager
    if _default_sse_manager is None:
        _default_sse_manager = SSEStreamManager()
    return _default_sse_manager
