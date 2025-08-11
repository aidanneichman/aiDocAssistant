"""Unit tests for Task 3.2: Streaming Response Handler.

Tests for streaming response processing, SSE formatting, and real-time
token delivery functionality.
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.clients.streaming_handler import (
    StreamingHandler,
    BatchingStreamHandler,
    StreamingError,
    StreamingConnectionError,
    create_streaming_handler,
    get_streaming_handler
)
from backend.app.utils.sse_utils import (
    SSEMessage,
    SSEFormatter,
    SSEStreamManager,
    SSEEventType,
    create_sse_stream_manager,
    get_sse_manager
)
from backend.app.models.chat import StreamingChatChunk


@pytest.fixture
def sample_response_chunks():
    """Sample response chunks for testing."""
    return ["Hello", " ", "world", "!", " How", " can", " I", " help", "?"]


@pytest.fixture
def sample_streaming_chunk():
    """Sample streaming chat chunk."""
    return StreamingChatChunk(
        id="test-response-123",
        content="Hello world",
        session_id="test-session-456"
    )


class TestStreamingHandler:
    """Test the streaming response handler."""
    
    def test_streaming_handler_initialization(self):
        """Test streaming handler initialization."""
        handler = StreamingHandler(
            buffer_size=2048,
            flush_interval=0.2,
            keepalive_interval=60.0,
            max_retries=5
        )
        
        assert handler.buffer_size == 2048
        assert handler.flush_interval == 0.2
        assert handler.keepalive_interval == 60.0
        assert handler.max_retries == 5
        assert not handler._is_streaming
        assert len(handler._buffer) == 0

    @pytest.mark.asyncio
    async def test_stream_response_success(self, sample_response_chunks):
        """Test successful response streaming."""
        handler = StreamingHandler()
        
        # Create async iterator from sample chunks
        async def mock_iterator():
            for chunk in sample_response_chunks:
                yield chunk
        
        # Collect streamed chunks
        chunks = []
        async for chunk in handler.stream_response(
            mock_iterator(),
            response_id="test-123",
            session_id="session-456"
        ):
            chunks.append(chunk)
        
        # Verify chunks
        assert len(chunks) == len(sample_response_chunks) + 1  # +1 for final chunk
        
        # Check content chunks
        for i, chunk in enumerate(chunks[:-1]):
            assert chunk.id == "test-123"
            assert chunk.session_id == "session-456"
            assert chunk.content == sample_response_chunks[i]
            assert not chunk.is_final
        
        # Check final chunk
        final_chunk = chunks[-1]
        assert final_chunk.is_final
        assert final_chunk.content == ""

    @pytest.mark.asyncio
    async def test_stream_response_with_empty_chunks(self):
        """Test streaming with empty chunks (should be filtered)."""
        handler = StreamingHandler()
        
        async def mock_iterator():
            yield "Hello"
            yield ""  # Empty chunk
            yield " "
            yield ""  # Another empty chunk
            yield "world"
        
        chunks = []
        async for chunk in handler.stream_response(
            mock_iterator(),
            response_id="test-123",
            session_id="session-456"
        ):
            chunks.append(chunk)
        
        # Should have 3 content chunks + 1 final chunk
        # Empty chunks should be filtered out
        content_chunks = [c for c in chunks if not c.is_final]
        assert len(content_chunks) == 3
        assert content_chunks[0].content == "Hello"
        assert content_chunks[1].content == " "
        assert content_chunks[2].content == "world"

    @pytest.mark.asyncio
    async def test_stream_response_error_handling(self):
        """Test error handling during streaming."""
        handler = StreamingHandler()
        
        async def failing_iterator():
            yield "Hello"
            raise Exception("Connection failed")
        
        with pytest.raises(StreamingError, match="Failed to stream response"):
            async for chunk in handler.stream_response(
                failing_iterator(),
                response_id="test-123",
                session_id="session-456"
            ):
                pass

    @pytest.mark.asyncio
    async def test_stream_with_retry_success_after_failure(self, sample_response_chunks):
        """Test streaming with retry succeeding after initial failure."""
        handler = StreamingHandler(max_retries=3)
        attempt_count = 0
        
        def mock_iterator_factory():
            nonlocal attempt_count
            attempt_count += 1
            
            async def mock_iterator():
                if attempt_count < 2:  # Fail first attempt
                    yield "Hello"
                    raise StreamingConnectionError("Connection failed")
                else:  # Succeed on second attempt
                    for chunk in sample_response_chunks:
                        yield chunk
            
            return mock_iterator()
        
        chunks = []
        async for chunk in handler.stream_with_retry(
            mock_iterator_factory,
            response_id="test-123",
            session_id="session-456"
        ):
            chunks.append(chunk)
        
        # Should succeed after retry
        assert len(chunks) == len(sample_response_chunks) + 1
        assert attempt_count == 2

    @pytest.mark.asyncio
    async def test_stream_with_retry_all_attempts_fail(self):
        """Test streaming with retry when all attempts fail."""
        handler = StreamingHandler(max_retries=2)
        
        def failing_iterator_factory():
            async def failing_iterator():
                yield "Hello"
                raise StreamingConnectionError("Connection failed")
            return failing_iterator()
        
        with pytest.raises(StreamingError, match="All streaming retries failed"):
            async for chunk in handler.stream_with_retry(
                failing_iterator_factory,
                response_id="test-123",
                session_id="session-456"
            ):
                pass

    def test_streaming_stats(self):
        """Test streaming statistics."""
        handler = StreamingHandler(
            buffer_size=1024,
            flush_interval=0.1,
            keepalive_interval=30.0
        )
        
        stats = handler.get_streaming_stats()
        
        assert stats["is_streaming"] is False
        assert stats["buffer_size"] == 0
        assert stats["buffer_items"] == 0
        assert stats["config"]["buffer_size"] == 1024
        assert stats["config"]["flush_interval"] == 0.1
        assert stats["config"]["keepalive_interval"] == 30.0


class TestBatchingStreamHandler:
    """Test the batching streaming handler."""
    
    def test_batching_handler_initialization(self):
        """Test batching handler initialization."""
        handler = BatchingStreamHandler(
            batch_size=10,
            batch_timeout=1.0,
            buffer_size=2048
        )
        
        assert handler.batch_size == 10
        assert handler.batch_timeout == 1.0
        assert handler.buffer_size == 2048
        assert len(handler._batch_buffer) == 0

    @pytest.mark.asyncio
    async def test_batching_stream_response(self):
        """Test batched streaming response."""
        handler = BatchingStreamHandler(batch_size=3, batch_timeout=0.1)
        
        # Create chunks that will be batched
        chunks = ["A", "B", "C", "D", "E", "F", "G"]
        
        async def mock_iterator():
            for chunk in chunks:
                yield chunk
        
        streamed_chunks = []
        async for chunk in handler.stream_response(
            mock_iterator(),
            response_id="test-123",
            session_id="session-456"
        ):
            streamed_chunks.append(chunk)
        
        # Should have batched chunks + final chunk
        content_chunks = [c for c in streamed_chunks if not c.is_final]
        
        # Verify batching (3 chunks per batch)
        assert len(content_chunks) >= 2  # At least 2 batches
        
        # First batch should contain "ABC"
        if len(content_chunks) > 0:
            assert "A" in content_chunks[0].content
            assert "B" in content_chunks[0].content
            assert "C" in content_chunks[0].content

    @pytest.mark.asyncio
    async def test_batching_timeout(self):
        """Test batching timeout functionality."""
        handler = BatchingStreamHandler(batch_size=10, batch_timeout=0.1)
        
        async def slow_iterator():
            yield "A"
            yield "B"
            await asyncio.sleep(0.2)  # Longer than timeout
            yield "C"
        
        streamed_chunks = []
        async for chunk in handler.stream_response(
            slow_iterator(),
            response_id="test-123",
            session_id="session-456"
        ):
            streamed_chunks.append(chunk)
        
        # Should have multiple chunks due to timeout
        content_chunks = [c for c in streamed_chunks if not c.is_final]
        assert len(content_chunks) >= 1


class TestSSEMessage:
    """Test SSE message formatting."""
    
    def test_sse_message_basic(self):
        """Test basic SSE message formatting."""
        msg = SSEMessage(
            data="Hello world",
            event_type="message",
            event_id="123"
        )
        
        formatted = msg.format()
        
        assert "event: message" in formatted
        assert "id: 123" in formatted
        assert "data: Hello world" in formatted
        assert formatted.endswith("\n\n")

    def test_sse_message_json_data(self):
        """Test SSE message with JSON data."""
        data = {"type": "token", "content": "Hello", "timestamp": "2023-01-01T00:00:00"}
        msg = SSEMessage(data=data, event_type="token")
        
        formatted = msg.format()
        
        assert "event: token" in formatted
        assert "data: {" in formatted
        assert '"type": "token"' in formatted
        assert '"content": "Hello"' in formatted

    def test_sse_message_multiline_data(self):
        """Test SSE message with multiline data."""
        msg = SSEMessage(data="Line 1\nLine 2\nLine 3")
        
        formatted = msg.format()
        
        assert "data: Line 1" in formatted
        assert "data: Line 2" in formatted
        assert "data: Line 3" in formatted

    def test_sse_message_with_retry(self):
        """Test SSE message with retry interval."""
        msg = SSEMessage(
            data="Retry message",
            event_type="retry",
            retry=5000
        )
        
        formatted = msg.format()
        
        assert "retry: 5000" in formatted
        assert "event: retry" in formatted


class TestSSEFormatter:
    """Test SSE message formatting utilities."""
    
    def test_format_token(self):
        """Test token message formatting."""
        msg = SSEFormatter.format_token(
            content="Hello",
            chunk_id="chunk-123",
            metadata={"session_id": "session-456"}
        )
        
        assert msg.event_type == SSEEventType.TOKEN
        assert msg.event_id == "chunk-123"
        
        # Parse data
        data = json.loads(msg._format_data())
        assert data["type"] == SSEEventType.TOKEN
        assert data["content"] == "Hello"
        assert data["session_id"] == "session-456"

    def test_format_error(self):
        """Test error message formatting."""
        msg = SSEFormatter.format_error(
            error_message="Connection failed",
            error_code="CONNECTION_ERROR",
            error_id="error-123"
        )
        
        assert msg.event_type == SSEEventType.ERROR
        assert msg.event_id == "error-123"
        
        data = json.loads(msg._format_data())
        assert data["type"] == SSEEventType.ERROR
        assert data["message"] == "Connection failed"
        assert data["code"] == "CONNECTION_ERROR"

    def test_format_completion(self):
        """Test completion message formatting."""
        metadata = {"token_usage": {"total": 150}}
        msg = SSEFormatter.format_completion(
            message="Stream completed",
            final_metadata=metadata,
            completion_id="completion-123"
        )
        
        assert msg.event_type == SSEEventType.DONE
        assert msg.event_id == "completion-123"
        
        data = json.loads(msg._format_data())
        assert data["type"] == SSEEventType.DONE
        assert data["message"] == "Stream completed"
        assert data["metadata"]["token_usage"]["total"] == 150

    def test_format_keepalive(self):
        """Test keepalive message formatting."""
        msg = SSEFormatter.format_keepalive(keepalive_id="keepalive-123")
        
        assert msg.event_type == SSEEventType.KEEPALIVE
        assert msg.event_id == "keepalive-123"
        
        data = json.loads(msg._format_data())
        assert data["type"] == SSEEventType.KEEPALIVE

    def test_format_chunk_regular(self, sample_streaming_chunk):
        """Test formatting regular streaming chunk."""
        msg = SSEFormatter.format_chunk(sample_streaming_chunk)
        
        assert msg.event_type == SSEEventType.TOKEN
        
        data = json.loads(msg._format_data())
        assert data["content"] == "Hello world"
        assert data["session_id"] == "test-session-456"
        assert data["response_id"] == "test-response-123"

    def test_format_chunk_final(self):
        """Test formatting final streaming chunk."""
        final_chunk = StreamingChatChunk(
            id="test-response-123",
            content="",
            is_final=True,
            session_id="test-session-456"
        )
        
        msg = SSEFormatter.format_chunk(final_chunk)
        
        assert msg.event_type == SSEEventType.DONE
        
        data = json.loads(msg._format_data())
        assert data["message"] == "Chat response completed"


class TestSSEStreamManager:
    """Test SSE stream management."""
    
    def test_sse_manager_initialization(self):
        """Test SSE manager initialization."""
        manager = SSEStreamManager(
            keepalive_interval=45.0,
            retry_interval=5000,
            max_message_size=32768
        )
        
        assert manager.keepalive_interval == 45.0
        assert manager.retry_interval == 5000
        assert manager.max_message_size == 32768

    @pytest.mark.asyncio
    async def test_stream_chat_response(self):
        """Test streaming chat response as SSE."""
        manager = SSEStreamManager()
        
        # Create sample chunks
        chunks = [
            StreamingChatChunk(
                id="response-123",
                content="Hello",
                session_id="session-456"
            ),
            StreamingChatChunk(
                id="response-123",
                content=" world",
                session_id="session-456"
            ),
            StreamingChatChunk(
                id="response-123",
                content="",
                is_final=True,
                session_id="session-456"
            )
        ]
        
        async def mock_chunks():
            for chunk in chunks:
                yield chunk
        
        sse_messages = []
        async for sse_msg in manager.stream_chat_response(
            mock_chunks(),
            session_id="session-456",
            response_id="response-123"
        ):
            sse_messages.append(sse_msg)
        
        # Should have status + content chunks
        assert len(sse_messages) >= len(chunks)
        
        # First message should be status
        first_msg_lines = sse_messages[0].split('\n')
        assert any("streaming_started" in line for line in first_msg_lines)

    @pytest.mark.asyncio
    async def test_stream_large_message_handling(self):
        """Test handling of oversized messages."""
        manager = SSEStreamManager(max_message_size=100)  # Very small limit
        
        # Create chunk with large content
        large_chunk = StreamingChatChunk(
            id="response-123",
            content="A" * 200,  # Larger than limit
            session_id="session-456"
        )
        
        async def mock_chunks():
            yield large_chunk
        
        sse_messages = []
        async for sse_msg in manager.stream_chat_response(
            mock_chunks(),
            session_id="session-456",
            response_id="response-123"
        ):
            sse_messages.append(sse_msg)
        
        # Should contain error message about size
        error_found = any("MESSAGE_TOO_LARGE" in msg for msg in sse_messages)
        assert error_found

    def test_create_connection_headers(self):
        """Test SSE connection headers."""
        manager = SSEStreamManager()
        headers = manager.create_connection_headers()
        
        assert headers["Content-Type"] == "text/event-stream"
        assert headers["Cache-Control"] == "no-cache"
        assert headers["Connection"] == "keep-alive"
        assert "Access-Control-Allow-Origin" in headers

    def test_format_connection_established(self):
        """Test connection established message."""
        manager = SSEStreamManager(retry_interval=3000)
        msg = manager.format_connection_established("conn-123")
        
        assert "connection_established" in msg
        assert "conn-123" in msg
        assert "3000" in msg


class TestFactoryFunctions:
    """Test factory functions for streaming components."""
    
    def test_create_streaming_handler_default(self):
        """Test creating default streaming handler."""
        handler = create_streaming_handler("default", buffer_size=2048)
        
        assert isinstance(handler, StreamingHandler)
        assert not isinstance(handler, BatchingStreamHandler)
        assert handler.buffer_size == 2048

    def test_create_streaming_handler_batching(self):
        """Test creating batching streaming handler."""
        handler = create_streaming_handler(
            "batching",
            batch_size=5,
            batch_timeout=0.5
        )
        
        assert isinstance(handler, BatchingStreamHandler)
        assert handler.batch_size == 5
        assert handler.batch_timeout == 0.5

    def test_create_streaming_handler_invalid_type(self):
        """Test creating handler with invalid type."""
        with pytest.raises(ValueError, match="Unknown handler type"):
            create_streaming_handler("invalid_type")

    def test_create_sse_stream_manager(self):
        """Test creating SSE stream manager."""
        manager = create_sse_stream_manager(
            keepalive_interval=60.0,
            retry_interval=5000
        )
        
        assert isinstance(manager, SSEStreamManager)
        assert manager.keepalive_interval == 60.0
        assert manager.retry_interval == 5000

    def test_get_streaming_handler_singleton(self):
        """Test streaming handler singleton."""
        handler1 = get_streaming_handler()
        handler2 = get_streaming_handler()
        
        assert handler1 is handler2
        assert isinstance(handler1, StreamingHandler)

    def test_get_sse_manager_singleton(self):
        """Test SSE manager singleton."""
        manager1 = get_sse_manager()
        manager2 = get_sse_manager()
        
        assert manager1 is manager2
        assert isinstance(manager1, SSEStreamManager)


class TestTaskSuccessCriteria:
    """Test all success criteria from Task 3.2 specification."""
    
    @pytest.mark.asyncio
    async def test_smooth_real_time_token_streaming(self, sample_response_chunks):
        """Verify smooth real-time token streaming."""
        handler = StreamingHandler(flush_interval=0.01)  # Fast flushing
        
        async def mock_iterator():
            for chunk in sample_response_chunks:
                yield chunk
                await asyncio.sleep(0.001)  # Simulate real-time arrival
        
        start_time = asyncio.get_event_loop().time()
        chunks = []
        
        async for chunk in handler.stream_response(
            mock_iterator(),
            response_id="test-123",
            session_id="session-456"
        ):
            chunks.append(chunk)
        
        end_time = asyncio.get_event_loop().time()
        
        # Should complete quickly and have all chunks
        assert (end_time - start_time) < 1.0  # Should be fast
        assert len(chunks) == len(sample_response_chunks) + 1

    def test_proper_sse_formatting_and_event_handling(self):
        """Verify proper SSE formatting and event handling."""
        # Test all event types
        token_msg = SSEFormatter.format_token("Hello")
        error_msg = SSEFormatter.format_error("Error occurred")
        done_msg = SSEFormatter.format_completion("Complete")
        keepalive_msg = SSEFormatter.format_keepalive()
        
        # All should format properly
        for msg in [token_msg, error_msg, done_msg, keepalive_msg]:
            formatted = msg.format()
            assert formatted.startswith("event:")
            assert "data:" in formatted
            assert formatted.endswith("\n\n")

    @pytest.mark.asyncio
    async def test_connection_error_recovery(self):
        """Verify connection error recovery."""
        handler = StreamingHandler(max_retries=2)
        
        def recovery_factory():
            attempt = getattr(recovery_factory, 'attempt', 0)
            recovery_factory.attempt = attempt + 1
            
            async def iterator():
                if attempt == 0:
                    yield "Hello"
                    raise StreamingConnectionError("Connection lost")
                else:
                    yield "Hello"
                    yield " recovered"
            
            return iterator()
        
        chunks = []
        async for chunk in handler.stream_with_retry(
            recovery_factory,
            response_id="test-123",
            session_id="session-456"
        ):
            chunks.append(chunk)
        
        # Should recover and complete successfully
        assert len(chunks) >= 2
        assert any("recovered" in chunk.content for chunk in chunks)

    @pytest.mark.asyncio
    async def test_clean_stream_termination(self):
        """Verify clean stream termination."""
        handler = StreamingHandler()
        
        async def mock_iterator():
            yield "Hello"
            yield " world"
        
        chunks = []
        async for chunk in handler.stream_response(
            mock_iterator(),
            response_id="test-123",
            session_id="session-456"
        ):
            chunks.append(chunk)
        
        # Last chunk should be final
        final_chunk = chunks[-1]
        assert final_chunk.is_final
        assert final_chunk.content == ""
        
        # Handler should not be streaming after completion
        assert not handler._is_streaming

    def test_frontend_can_consume_stream_easily(self):
        """Verify frontend can easily consume the stream."""
        # Test that SSE messages are properly formatted for frontend consumption
        manager = SSEStreamManager()
        
        # Headers should be correct for browser SSE
        headers = manager.create_connection_headers()
        assert headers["Content-Type"] == "text/event-stream"
        assert headers["Cache-Control"] == "no-cache"
        
        # Messages should be JSON parseable
        token_msg = SSEFormatter.format_token("Hello", metadata={"test": "data"})
        formatted = token_msg.format()
        
        # Extract data line
        data_lines = [line for line in formatted.split('\n') if line.startswith('data:')]
        assert len(data_lines) == 1
        
        # Should be valid JSON
        json_data = data_lines[0].replace('data: ', '')
        parsed = json.loads(json_data)
        
        assert parsed["type"] == "token"
        assert parsed["content"] == "Hello"
        assert parsed["test"] == "data"


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_complete_streaming_workflow(self):
        """Test complete streaming workflow from model to SSE."""
        # Simulate complete workflow
        handler = StreamingHandler()
        manager = SSEStreamManager()
        
        # Mock model response
        async def mock_model_response():
            for token in ["The", " quick", " brown", " fox"]:
                yield token
        
        # Step 1: Stream from model client
        model_chunks = []
        async for chunk in handler.stream_response(
            mock_model_response(),
            response_id="response-123",
            session_id="session-456"
        ):
            model_chunks.append(chunk)
        
        # Step 2: Convert to SSE
        async def chunk_iterator():
            for chunk in model_chunks:
                yield chunk
        
        sse_messages = []
        async for sse_msg in manager.stream_chat_response(
            chunk_iterator(),
            session_id="session-456",
            response_id="response-123"
        ):
            sse_messages.append(sse_msg)
        
        # Should have status + content + completion messages
        assert len(sse_messages) >= len(model_chunks)
        
        # Should contain actual content
        content_found = any("quick" in msg for msg in sse_messages)
        assert content_found

    @pytest.mark.asyncio
    async def test_batched_streaming_with_sse(self):
        """Test batched streaming integrated with SSE."""
        batching_handler = BatchingStreamHandler(batch_size=2, batch_timeout=0.1)
        manager = SSEStreamManager()
        
        async def mock_model_response():
            tokens = ["A", "B", "C", "D", "E"]
            for token in tokens:
                yield token
                await asyncio.sleep(0.01)
        
        # Stream with batching
        batched_chunks = []
        async for chunk in batching_handler.stream_response(
            mock_model_response(),
            response_id="response-123",
            session_id="session-456"
        ):
            batched_chunks.append(chunk)
        
        # Should have fewer chunks due to batching
        content_chunks = [c for c in batched_chunks if not c.is_final]
        assert len(content_chunks) < 5  # Should be batched
        
        # Convert to SSE
        async def chunk_iterator():
            for chunk in batched_chunks:
                yield chunk
        
        sse_messages = []
        async for sse_msg in manager.stream_chat_response(
            chunk_iterator(),
            session_id="session-456",
            response_id="response-123"
        ):
            sse_messages.append(sse_msg)
        
        # Should work with batched content
        assert len(sse_messages) > 0
