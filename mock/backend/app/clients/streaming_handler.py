"""Streaming response handler for real-time AI model responses.

This module provides utilities for processing streaming responses from AI model
clients and formatting them for Server-Sent Events (SSE) transmission to the frontend.
"""

import asyncio
import json
import logging
from typing import AsyncIterator, Dict, Any, Optional, List
from datetime import datetime

from backend.app.models.chat import StreamingChatChunk, ModelClientError

logger = logging.getLogger(__name__)


class StreamingError(Exception):
    """Base exception for streaming errors."""
    pass


class StreamingConnectionError(StreamingError):
    """Exception raised when streaming connection fails."""
    pass


class StreamingBufferError(StreamingError):
    """Exception raised when streaming buffer encounters issues."""
    pass


class StreamingHandler:
    """Handles streaming responses from AI model clients.
    
    This class processes async streaming responses from model clients,
    manages buffering, handles errors, and formats output for SSE transmission.
    """

    def __init__(
        self,
        buffer_size: int = 1024,
        flush_interval: float = 0.1,
        keepalive_interval: float = 30.0,
        max_retries: int = 3
    ):
        """Initialize streaming handler.
        
        Args:
            buffer_size: Maximum buffer size before forced flush
            flush_interval: Time interval between buffer flushes (seconds)
            keepalive_interval: Interval for keepalive messages (seconds)
            max_retries: Maximum number of retry attempts
        """
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        self.keepalive_interval = keepalive_interval
        self.max_retries = max_retries
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        
        # Streaming state
        self._buffer: List[str] = []
        self._buffer_length = 0
        self._is_streaming = False
        self._last_activity = datetime.utcnow()

    async def stream_response(
        self,
        response_iterator: AsyncIterator[str],
        response_id: str,
        session_id: str,
        **metadata
    ) -> AsyncIterator[StreamingChatChunk]:
        """Stream and process model response chunks.
        
        Args:
            response_iterator: Async iterator of response chunks from model client
            response_id: Unique identifier for this response
            session_id: Chat session identifier
            **metadata: Additional metadata to include in chunks
            
        Yields:
            StreamingChatChunk: Formatted streaming chunks
            
        Raises:
            StreamingError: If streaming fails
        """
        self._is_streaming = True
        self._last_activity = datetime.utcnow()
        chunk_count = 0
        
        try:
            self.logger.info(f"Starting stream for response {response_id}")
            
            # Start keepalive task
            keepalive_task = asyncio.create_task(
                self._keepalive_loop(response_id, session_id)
            )
            
            try:
                async for content in response_iterator:
                    if content:  # Skip empty chunks
                        chunk_count += 1
                        self._last_activity = datetime.utcnow()
                        
                        # Create streaming chunk
                        chunk = StreamingChatChunk(
                            id=response_id,
                            content=content,
                            session_id=session_id,
                            **metadata
                        )
                        
                        self.logger.debug(f"Streaming chunk {chunk_count}: {len(content)} chars")
                        yield chunk
                        
                        # Add to buffer for potential batching
                        self._add_to_buffer(content)
                        
                        # Flush buffer if needed
                        if self._should_flush_buffer():
                            await self._flush_buffer()
                
                # Send final chunk
                final_chunk = StreamingChatChunk(
                    id=response_id,
                    content="",
                    is_final=True,
                    session_id=session_id,
                    **metadata
                )
                
                self.logger.info(f"Stream completed: {chunk_count} chunks")
                yield final_chunk
                
            finally:
                # Cancel keepalive task
                keepalive_task.cancel()
                try:
                    await keepalive_task
                except asyncio.CancelledError:
                    pass
                
        except Exception as e:
            self.logger.error(f"Streaming error: {e}")
            raise StreamingError(f"Failed to stream response: {e}") from e
        
        finally:
            self._is_streaming = False
            self._clear_buffer()

    async def stream_with_retry(
        self,
        response_iterator_factory,
        response_id: str,
        session_id: str,
        **metadata
    ) -> AsyncIterator[StreamingChatChunk]:
        """Stream with automatic retry on connection errors.
        
        Args:
            response_iterator_factory: Function that creates response iterator
            response_id: Unique identifier for this response
            session_id: Chat session identifier
            **metadata: Additional metadata to include in chunks
            
        Yields:
            StreamingChatChunk: Formatted streaming chunks
            
        Raises:
            StreamingError: If all retries fail
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                response_iterator = response_iterator_factory()
                
                async for chunk in self.stream_response(
                    response_iterator, response_id, session_id, **metadata
                ):
                    yield chunk
                
                return  # Success, exit retry loop
                
            except (StreamingConnectionError, ModelClientError) as e:
                last_error = e
                self.logger.warning(f"Streaming attempt {attempt + 1} failed: {e}")

                if attempt < self.max_retries - 1:
                    delay = 2 ** attempt  # Exponential backoff
                    self.logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    break
                    
            except StreamingError as e:
                # StreamingError wraps connection errors, check inner cause
                if isinstance(e.__cause__, (StreamingConnectionError, ModelClientError)):
                    last_error = e
                    self.logger.warning(f"Streaming attempt {attempt + 1} failed: {e}")
                    
                    if attempt < self.max_retries - 1:
                        delay = 2 ** attempt  # Exponential backoff
                        self.logger.info(f"Retrying in {delay} seconds...")
                        await asyncio.sleep(delay)
                    else:
                        break
                else:
                    # Non-retryable StreamingError
                    raise
                    
            except Exception as e:
                # Non-retryable errors
                self.logger.error(f"Non-retryable streaming error: {e}")
                raise StreamingError(f"Streaming failed: {e}") from e
        
        # All retries failed
        raise StreamingError(f"All streaming retries failed. Last error: {last_error}")

    async def _keepalive_loop(self, response_id: str, session_id: str):
        """Send periodic keepalive messages during streaming.
        
        Args:
            response_id: Response identifier
            session_id: Session identifier
        """
        try:
            while self._is_streaming:
                await asyncio.sleep(self.keepalive_interval)
                
                # Check if we need to send keepalive
                time_since_activity = (datetime.utcnow() - self._last_activity).total_seconds()
                
                if time_since_activity >= self.keepalive_interval:
                    self.logger.debug("Sending keepalive message")
                    # Note: Keepalive implementation would depend on the specific SSE setup
                    # This is a placeholder for the keepalive logic
                    
        except asyncio.CancelledError:
            self.logger.debug("Keepalive loop cancelled")
            raise

    def _add_to_buffer(self, content: str):
        """Add content to the streaming buffer.
        
        Args:
            content: Content to add to buffer
        """
        self._buffer.append(content)
        self._buffer_length += len(content)

    def _should_flush_buffer(self) -> bool:
        """Check if buffer should be flushed.
        
        Returns:
            bool: True if buffer should be flushed
        """
        return self._buffer_length >= self.buffer_size

    async def _flush_buffer(self):
        """Flush the streaming buffer."""
        if self._buffer:
            self.logger.debug(f"Flushing buffer: {self._buffer_length} chars")
            self._clear_buffer()

    def _clear_buffer(self):
        """Clear the streaming buffer."""
        self._buffer.clear()
        self._buffer_length = 0

    def get_streaming_stats(self) -> Dict[str, Any]:
        """Get current streaming statistics.
        
        Returns:
            dict: Streaming statistics
        """
        return {
            "is_streaming": self._is_streaming,
            "buffer_size": self._buffer_length,
            "buffer_items": len(self._buffer),
            "last_activity": self._last_activity.isoformat() if self._last_activity else None,
            "config": {
                "buffer_size": self.buffer_size,
                "flush_interval": self.flush_interval,
                "keepalive_interval": self.keepalive_interval,
                "max_retries": self.max_retries
            }
        }


class BatchingStreamHandler(StreamingHandler):
    """Streaming handler with intelligent batching for better performance.
    
    This handler batches small chunks together to reduce the number of
    messages sent to the client while maintaining responsiveness.
    """

    def __init__(
        self,
        batch_size: int = 5,
        batch_timeout: float = 0.5,
        **kwargs
    ):
        """Initialize batching stream handler.
        
        Args:
            batch_size: Number of chunks to batch together
            batch_timeout: Maximum time to wait for batch completion
            **kwargs: Additional arguments for base StreamingHandler
        """
        super().__init__(**kwargs)
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self._batch_buffer: List[str] = []
        self._batch_timer: Optional[asyncio.Task] = None

    async def stream_response(
        self,
        response_iterator: AsyncIterator[str],
        response_id: str,
        session_id: str,
        **metadata
    ) -> AsyncIterator[StreamingChatChunk]:
        """Stream response with intelligent batching.
        
        Args:
            response_iterator: Async iterator of response chunks
            response_id: Unique identifier for this response
            session_id: Chat session identifier
            **metadata: Additional metadata
            
        Yields:
            StreamingChatChunk: Batched streaming chunks
        """
        self._is_streaming = True
        self._last_activity = datetime.utcnow()
        
        try:
            self.logger.info(f"Starting batched stream for response {response_id}")
            
            async for content in response_iterator:
                if content:
                    self._batch_buffer.append(content)
                    self._last_activity = datetime.utcnow()
                    
                    # Check if we should flush the batch
                    if len(self._batch_buffer) >= self.batch_size:
                        yield await self._flush_batch(response_id, session_id, **metadata)
                    else:
                        # Start batch timer if not already running
                        if not self._batch_timer or self._batch_timer.done():
                            self._batch_timer = asyncio.create_task(
                                self._batch_timeout_handler(response_id, session_id, **metadata)
                            )
            
            # Flush any remaining content
            if self._batch_buffer:
                yield await self._flush_batch(response_id, session_id, **metadata)
            
            # Send final chunk
            final_chunk = StreamingChatChunk(
                id=response_id,
                content="",
                is_final=True,
                session_id=session_id,
                **metadata
            )
            
            self.logger.info("Batched stream completed")
            yield final_chunk
            
        except Exception as e:
            self.logger.error(f"Batched streaming error: {e}")
            raise StreamingError(f"Failed to stream batched response: {e}") from e
        
        finally:
            self._is_streaming = False
            if self._batch_timer and not self._batch_timer.done():
                self._batch_timer.cancel()
            self._batch_buffer.clear()

    async def _batch_timeout_handler(
        self,
        response_id: str,
        session_id: str,
        **metadata
    ) -> StreamingChatChunk:
        """Handle batch timeout by flushing current batch.
        
        Args:
            response_id: Response identifier
            session_id: Session identifier
            **metadata: Additional metadata
            
        Returns:
            StreamingChatChunk: Batched chunk
        """
        try:
            await asyncio.sleep(self.batch_timeout)
            if self._batch_buffer and self._is_streaming:
                return await self._flush_batch(response_id, session_id, **metadata)
        except asyncio.CancelledError:
            pass

    async def _flush_batch(
        self,
        response_id: str,
        session_id: str,
        **metadata
    ) -> StreamingChatChunk:
        """Flush the current batch buffer.
        
        Args:
            response_id: Response identifier
            session_id: Session identifier
            **metadata: Additional metadata
            
        Returns:
            StreamingChatChunk: Batched chunk
        """
        if not self._batch_buffer:
            return
            
        # Combine all chunks in batch
        batched_content = "".join(self._batch_buffer)
        self._batch_buffer.clear()
        
        # Cancel timer if running
        if self._batch_timer and not self._batch_timer.done():
            self._batch_timer.cancel()
        
        self.logger.debug(f"Flushing batch: {len(batched_content)} chars")
        
        return StreamingChatChunk(
            id=response_id,
            content=batched_content,
            session_id=session_id,
            **metadata
        )


def create_streaming_handler(
    handler_type: str = "default",
    **config
) -> StreamingHandler:
    """Factory function to create streaming handlers.
    
    Args:
        handler_type: Type of handler ("default" or "batching")
        **config: Configuration options for the handler
        
    Returns:
        StreamingHandler: Configured streaming handler
    """
    if handler_type == "batching":
        return BatchingStreamHandler(**config)
    elif handler_type == "default":
        return StreamingHandler(**config)
    else:
        raise ValueError(f"Unknown handler type: {handler_type}")


# Global streaming handler instance
_default_handler: Optional[StreamingHandler] = None


def get_streaming_handler() -> StreamingHandler:
    """Get the default streaming handler instance.
    
    Returns:
        StreamingHandler: Default streaming handler
    """
    global _default_handler
    if _default_handler is None:
        _default_handler = StreamingHandler()
    return _default_handler
