"""Unit tests for Task 3.1: Model Client Interface & OpenAI Implementation.

Tests for the abstract model client interface and OpenAI implementation
including chat completion, document context injection, and error handling.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

import pytest
import openai

from backend.app.clients.base_model_client import BaseModelClient
from backend.app.clients.openai_client import OpenAIClient, create_openai_client
from backend.app.models.chat import (
    ChatMessage, 
    ChatMode, 
    MessageRole, 
    TokenUsage,
    ModelClientError,
    ModelClientConnectionError,
    ModelClientRateLimitError,
    ModelClientInvalidRequestError,
    ModelClientAuthenticationError
)
from backend.app.models.document import Document


class MockModelClient(BaseModelClient):
    """Mock implementation of BaseModelClient for testing."""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.model_name = config.get("model", "mock-model")
        self.last_token_usage = None
        self.connection_valid = True
        self.completion_chunks = ["Hello", " ", "world", "!"]
    
    async def chat_completion(self, messages, mode, documents=None, max_tokens=None, temperature=None, **kwargs):
        """Mock streaming completion."""
        for chunk in self.completion_chunks:
            yield chunk
        
        # Set token usage
        self.last_token_usage = TokenUsage(
            prompt_tokens=10,
            completion_tokens=4,
            total_tokens=14
        )
    
    async def get_token_usage(self):
        return self.last_token_usage
    
    async def validate_connection(self):
        return self.connection_valid
    
    def get_model_name(self):
        return self.model_name


@pytest.fixture
def mock_client_config():
    """Mock client configuration."""
    return {
        "api_key": "test-api-key",
        "model": "gpt-4-turbo-preview",
        "max_tokens": 1000,
        "temperature": 0.7
    }


@pytest.fixture
def sample_messages():
    """Sample chat messages for testing."""
    return [
        ChatMessage(role=MessageRole.USER, content="Hello, can you help me?"),
        ChatMessage(role=MessageRole.ASSISTANT, content="Of course! How can I assist you?"),
        ChatMessage(role=MessageRole.USER, content="What are the key points in this contract?")
    ]


@pytest.fixture
def sample_document():
    """Sample document for testing."""
    return Document(
        id="4837479125758add3ba4c99153bb855c8519f86a7f672b26b155bea6adcbb41a",  # 64 char SHA-256
        original_filename="contract.pdf",
        content_type="application/pdf",
        size_bytes=1024000,
        upload_time=datetime.utcnow(),
        file_path=Path("/tmp/test.pdf")
    )


class TestBaseModelClient:
    """Test the abstract base model client interface."""
    
    def test_base_client_initialization(self, mock_client_config):
        """Test base client initialization."""
        client = MockModelClient(mock_client_config)
        
        assert client.config == mock_client_config
        assert client.get_model_name() == "gpt-4-turbo-preview"
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, mock_client_config):
        """Test health check with healthy client."""
        client = MockModelClient(mock_client_config)
        
        health = await client.health_check()
        
        assert health["status"] == "healthy"
        assert health["model"] == "gpt-4-turbo-preview"
        assert health["provider"] == "MockModelClient"
        assert health["connected"] is True
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, mock_client_config):
        """Test health check with unhealthy client."""
        client = MockModelClient(mock_client_config)
        client.connection_valid = False
        
        health = await client.health_check()
        
        assert health["status"] == "unhealthy"
        assert health["connected"] is False
    
    def test_build_system_prompt_regular_mode(self, mock_client_config):
        """Test system prompt building for regular mode."""
        client = MockModelClient(mock_client_config)
        
        prompt = client._build_system_prompt(ChatMode.REGULAR)
        
        assert "AI Legal Assistant" in prompt
        assert "REGULAR MODE" in prompt
        assert "clear, concise responses" in prompt
    
    def test_build_system_prompt_deep_research_mode(self, mock_client_config):
        """Test system prompt building for deep research mode."""
        client = MockModelClient(mock_client_config)
        
        prompt = client._build_system_prompt(ChatMode.DEEP_RESEARCH)
        
        assert "AI Legal Assistant" in prompt
        assert "DEEP RESEARCH MODE" in prompt
        assert "comprehensive, detailed analysis" in prompt
    
    def test_build_system_prompt_with_documents(self, mock_client_config, sample_document):
        """Test system prompt building with document context."""
        client = MockModelClient(mock_client_config)
        
        prompt = client._build_system_prompt(ChatMode.REGULAR, [sample_document])
        
        assert "AVAILABLE DOCUMENTS" in prompt
        assert "contract.pdf" in prompt
        assert sample_document.id[:16] in prompt
        assert "application/pdf" in prompt
    
    def test_sanitize_messages(self, mock_client_config, sample_messages):
        """Test message sanitization for API format."""
        client = MockModelClient(mock_client_config)
        
        api_messages = client._sanitize_messages(sample_messages)
        
        assert len(api_messages) == 3
        assert api_messages[0]["role"] == "user"
        assert api_messages[0]["content"] == "Hello, can you help me?"
        assert api_messages[1]["role"] == "assistant"
        assert api_messages[2]["role"] == "user"
    
    @pytest.mark.asyncio
    async def test_async_context_manager(self, mock_client_config):
        """Test async context manager functionality."""
        async with MockModelClient(mock_client_config) as client:
            assert isinstance(client, MockModelClient)
            health = await client.health_check()
            assert health["status"] == "healthy"


class TestOpenAIClient:
    """Test the OpenAI client implementation."""
    
    def test_openai_client_initialization(self, mock_client_config):
        """Test OpenAI client initialization."""
        client = OpenAIClient(mock_client_config)
        
        assert client.api_key == "test-api-key"
        assert client.model == "gpt-4-turbo-preview"
        assert client.default_max_tokens == 1000
        assert client.default_temperature == 0.7
    
    def test_openai_client_initialization_missing_api_key(self):
        """Test OpenAI client initialization with missing API key."""
        config = {"model": "gpt-4"}
        
        with pytest.raises(ModelClientError, match="OpenAI API key is required"):
            OpenAIClient(config)
    
    def test_openai_client_default_values(self):
        """Test OpenAI client with default configuration values."""
        config = {"api_key": "test-key"}
        client = OpenAIClient(config)
        
        assert client.model == OpenAIClient.DEFAULT_MODEL
        assert client.default_max_tokens == OpenAIClient.DEFAULT_MAX_TOKENS
        assert client.default_temperature == OpenAIClient.DEFAULT_TEMPERATURE
    
    @pytest.mark.asyncio
    @patch('backend.app.clients.openai_client.AsyncOpenAI')
    async def test_chat_completion_success(self, mock_openai, mock_client_config, sample_messages):
        """Test successful chat completion."""
        # Mock streaming response
        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [MagicMock()]
        mock_chunk1.choices[0].delta = MagicMock()
        mock_chunk1.choices[0].delta.content = "Hello"
        mock_chunk1.choices[0].finish_reason = None
        
        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [MagicMock()]
        mock_chunk2.choices[0].delta = MagicMock()
        mock_chunk2.choices[0].delta.content = " world"
        mock_chunk2.choices[0].finish_reason = None
        
        mock_chunk3 = MagicMock()
        mock_chunk3.choices = [MagicMock()]
        mock_chunk3.choices[0].delta = MagicMock()
        mock_chunk3.choices[0].delta.content = None
        mock_chunk3.choices[0].finish_reason = "stop"
        
        # Mock async iterator
        async def mock_stream():
            for chunk in [mock_chunk1, mock_chunk2, mock_chunk3]:
                yield chunk
        
        mock_completion = AsyncMock()
        mock_completion.return_value = mock_stream()
        
        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create = mock_completion
        mock_openai.return_value = mock_client_instance
        
        client = OpenAIClient(mock_client_config)
        
        # Test streaming completion
        chunks = []
        async for chunk in client.chat_completion(sample_messages, ChatMode.REGULAR):
            chunks.append(chunk)
        
        assert chunks == ["Hello", " world"]
        mock_completion.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('backend.app.clients.openai_client.AsyncOpenAI')
    async def test_chat_completion_with_documents(self, mock_openai, mock_client_config, sample_messages, sample_document):
        """Test chat completion with document context."""
        # Mock streaming response
        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock()]
        mock_chunk.choices[0].delta = MagicMock()
        mock_chunk.choices[0].delta.content = "Response with document context"
        mock_chunk.choices[0].finish_reason = "stop"
        
        async def mock_stream():
            yield mock_chunk
        
        mock_completion = AsyncMock()
        mock_completion.return_value = mock_stream()
        
        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create = mock_completion
        mock_openai.return_value = mock_client_instance
        
        client = OpenAIClient(mock_client_config)
        
        # Test with documents
        chunks = []
        async for chunk in client.chat_completion(
            sample_messages, 
            ChatMode.DEEP_RESEARCH, 
            documents=[sample_document]
        ):
            chunks.append(chunk)
        
        # Verify completion was called
        mock_completion.assert_called_once()
        call_args = mock_completion.call_args[1]
        
        # Check that system message includes document context
        system_message = call_args["messages"][0]
        assert system_message["role"] == "system"
        assert "AVAILABLE DOCUMENTS" in system_message["content"]
        assert "contract.pdf" in system_message["content"]
    
    @pytest.mark.asyncio
    @patch('backend.app.clients.openai_client.AsyncOpenAI')
    async def test_chat_completion_with_custom_parameters(self, mock_openai, mock_client_config, sample_messages):
        """Test chat completion with custom parameters."""
        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock()]
        mock_chunk.choices[0].delta = MagicMock()
        mock_chunk.choices[0].delta.content = "Custom response"
        mock_chunk.choices[0].finish_reason = "stop"
        
        async def mock_stream():
            yield mock_chunk
        
        mock_completion = AsyncMock()
        mock_completion.return_value = mock_stream()
        
        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create = mock_completion
        mock_openai.return_value = mock_client_instance
        
        client = OpenAIClient(mock_client_config)
        
        # Test with custom parameters
        async for chunk in client.chat_completion(
            sample_messages,
            ChatMode.REGULAR,
            max_tokens=500,
            temperature=0.3,
            top_p=0.9  # Additional OpenAI parameter
        ):
            pass
        
        # Verify parameters were passed correctly
        call_args = mock_completion.call_args[1]
        assert call_args["max_tokens"] == 500
        assert call_args["temperature"] == 0.3
        assert call_args["top_p"] == 0.9
    
    @pytest.mark.asyncio
    @patch('backend.app.clients.openai_client.AsyncOpenAI')
    async def test_chat_completion_openai_error_handling(self, mock_openai, mock_client_config, sample_messages):
        """Test error handling for OpenAI API errors."""
        mock_completion = AsyncMock()
        mock_completion.side_effect = openai.AuthenticationError("Invalid API key")
        
        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create = mock_completion
        mock_openai.return_value = mock_client_instance
        
        client = OpenAIClient(mock_client_config)
        
        with pytest.raises(ModelClientAuthenticationError, match="OpenAI authentication failed"):
            async for chunk in client.chat_completion(sample_messages, ChatMode.REGULAR):
                pass
    
    @pytest.mark.asyncio
    @patch('backend.app.clients.openai_client.AsyncOpenAI')
    async def test_chat_completion_rate_limit_error(self, mock_openai, mock_client_config, sample_messages):
        """Test rate limit error handling."""
        mock_completion = AsyncMock()
        # Create mock response for rate limit error
        mock_response = MagicMock()
        mock_response.request = MagicMock()
        mock_completion.side_effect = openai.RateLimitError("Rate limit exceeded", response=mock_response, body=None)
        
        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create = mock_completion
        mock_openai.return_value = mock_client_instance
        
        client = OpenAIClient(mock_client_config)
        
        with pytest.raises(ModelClientRateLimitError, match="OpenAI rate limit exceeded"):
            async for chunk in client.chat_completion(sample_messages, ChatMode.REGULAR):
                pass
    
    @pytest.mark.asyncio
    @patch('backend.app.clients.openai_client.AsyncOpenAI')
    async def test_chat_completion_connection_error(self, mock_openai, mock_client_config, sample_messages):
        """Test connection error handling."""
        mock_completion = AsyncMock()
        # APIConnectionError requires message and request as keyword arguments
        mock_request = MagicMock()
        mock_completion.side_effect = openai.APIConnectionError(message="Connection failed", request=mock_request)
        
        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create = mock_completion
        mock_openai.return_value = mock_client_instance
        
        client = OpenAIClient(mock_client_config)
        
        with pytest.raises(ModelClientConnectionError, match="OpenAI connection error"):
            async for chunk in client.chat_completion(sample_messages, ChatMode.REGULAR):
                pass
    
    @pytest.mark.asyncio
    @patch('backend.app.clients.openai_client.AsyncOpenAI')
    async def test_chat_completion_retry_logic(self, mock_openai, mock_client_config, sample_messages):
        """Test retry logic for transient errors."""
        # First two calls fail, third succeeds
        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock()]
        mock_chunk.choices[0].delta = MagicMock()
        mock_chunk.choices[0].delta.content = "Success after retry"
        mock_chunk.choices[0].finish_reason = "stop"
        
        async def mock_stream():
            yield mock_chunk
        
        mock_completion = AsyncMock()
        # APIConnectionError requires message and request as keyword arguments
        mock_request = MagicMock()
        mock_completion.side_effect = [
            openai.APIConnectionError(message="Temporary connection error", request=mock_request),
            openai.APIConnectionError(message="Another temporary error", request=mock_request),
            mock_stream()
        ]
        
        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create = mock_completion
        mock_openai.return_value = mock_client_instance
        
        client = OpenAIClient(mock_client_config)
        
        # Should succeed after retries
        chunks = []
        async for chunk in client.chat_completion(sample_messages, ChatMode.REGULAR):
            chunks.append(chunk)
        
        assert chunks == ["Success after retry"]
        assert mock_completion.call_count == 3
    
    @pytest.mark.asyncio
    @patch('backend.app.clients.openai_client.AsyncOpenAI')
    async def test_validate_connection_success(self, mock_openai, mock_client_config):
        """Test successful connection validation."""
        mock_response = MagicMock()
        mock_completion = AsyncMock(return_value=mock_response)
        
        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create = mock_completion
        mock_openai.return_value = mock_client_instance
        
        client = OpenAIClient(mock_client_config)
        
        result = await client.validate_connection()
        
        assert result is True
        mock_completion.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('backend.app.clients.openai_client.AsyncOpenAI')
    async def test_validate_connection_failure(self, mock_openai, mock_client_config):
        """Test connection validation failure."""
        mock_completion = AsyncMock()
        mock_completion.side_effect = openai.AuthenticationError("Invalid API key")
        
        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create = mock_completion
        mock_openai.return_value = mock_client_instance
        
        client = OpenAIClient(mock_client_config)
        
        result = await client.validate_connection()
        
        assert result is False
    
    @pytest.mark.asyncio
    @patch('backend.app.clients.openai_client.AsyncOpenAI')
    async def test_get_available_models(self, mock_openai, mock_client_config):
        """Test getting available models."""
        mock_model1 = MagicMock()
        mock_model1.id = "gpt-4-turbo-preview"
        mock_model2 = MagicMock()
        mock_model2.id = "gpt-3.5-turbo"
        mock_model3 = MagicMock()
        mock_model3.id = "text-davinci-003"  # Should be filtered out
        
        mock_models_response = MagicMock()
        mock_models_response.data = [mock_model1, mock_model2, mock_model3]
        
        mock_models_list = AsyncMock(return_value=mock_models_response)
        
        mock_client_instance = MagicMock()
        mock_client_instance.models.list = mock_models_list
        mock_openai.return_value = mock_client_instance
        
        client = OpenAIClient(mock_client_config)
        
        models = await client.get_available_models()
        
        assert "gpt-4-turbo-preview" in models
        assert "gpt-3.5-turbo" in models
        assert "text-davinci-003" not in models  # Filtered out (no 'gpt' in name)
    
    def test_estimate_tokens(self, mock_client_config):
        """Test token estimation."""
        client = OpenAIClient(mock_client_config)
        
        text = "This is a test message for token estimation."
        estimated = client.estimate_tokens(text)
        
        # Should be roughly len(text) // 4
        expected = len(text) // 4
        assert estimated == expected
    
    def test_get_model_limits(self, mock_client_config):
        """Test getting model limits."""
        client = OpenAIClient(mock_client_config)
        
        limits = client.get_model_limits()
        
        assert "max_tokens" in limits
        assert "context_window" in limits
        assert limits["max_tokens"] > 0
        assert limits["context_window"] > 0
    
    def test_is_non_retryable_error(self, mock_client_config):
        """Test non-retryable error detection."""
        client = OpenAIClient(mock_client_config)
        
        # Create mock responses for testing
        mock_response = MagicMock()
        mock_response.request = MagicMock()
        
        # These should not be retried
        assert client._is_non_retryable_error(openai.AuthenticationError("Invalid key", response=mock_response, body=None))
        assert client._is_non_retryable_error(openai.BadRequestError("Bad request", response=mock_response, body=None))
        assert client._is_non_retryable_error(openai.PermissionDeniedError("Permission denied", response=mock_response, body=None))
        
        # These should be retried
        mock_request = MagicMock()
        assert not client._is_non_retryable_error(openai.APIConnectionError(message="Connection failed", request=mock_request))
        assert not client._is_non_retryable_error(openai.RateLimitError("Rate limit", response=mock_response, body=None))


class TestFactoryFunction:
    """Test the factory function for creating OpenAI clients."""
    
    def test_create_openai_client(self):
        """Test OpenAI client factory function."""
        client = create_openai_client("test-api-key", model="gpt-4", temperature=0.5)
        
        assert isinstance(client, OpenAIClient)
        assert client.api_key == "test-api-key"
        assert client.model == "gpt-4"
        assert client.default_temperature == 0.5
    
    def test_create_openai_client_minimal(self):
        """Test OpenAI client factory with minimal parameters."""
        client = create_openai_client("test-api-key")
        
        assert isinstance(client, OpenAIClient)
        assert client.api_key == "test-api-key"
        assert client.model == OpenAIClient.DEFAULT_MODEL


class TestTaskSuccessCriteria:
    """Test all success criteria from Task 3.1 specification."""
    
    def test_abstract_interface_allows_swapping_providers(self, mock_client_config):
        """Verify abstract interface allows swapping model providers."""
        # Test that both mock and OpenAI clients implement the same interface
        mock_client = MockModelClient(mock_client_config)
        openai_client = OpenAIClient(mock_client_config)
        
        # Both should have the same interface methods
        interface_methods = [
            'chat_completion', 
            'get_token_usage', 
            'validate_connection', 
            'get_model_name',
            'health_check'
        ]
        
        for method in interface_methods:
            assert hasattr(mock_client, method)
            assert hasattr(openai_client, method)
            assert callable(getattr(mock_client, method))
            assert callable(getattr(openai_client, method))
    
    @pytest.mark.asyncio
    async def test_openai_client_handles_streaming_responses(self, mock_client_config):
        """Verify OpenAI client handles streaming responses."""
        with patch('backend.app.clients.openai_client.AsyncOpenAI') as mock_openai:
            mock_chunk = MagicMock()
            mock_chunk.choices = [MagicMock()]
            mock_chunk.choices[0].delta = MagicMock()
            mock_chunk.choices[0].delta.content = "streaming content"
            mock_chunk.choices[0].finish_reason = "stop"
            
            async def mock_stream():
                yield mock_chunk
            
            mock_completion = AsyncMock(return_value=mock_stream())
            mock_client_instance = MagicMock()
            mock_client_instance.chat.completions.create = mock_completion
            mock_openai.return_value = mock_client_instance
            
            client = OpenAIClient(mock_client_config)
            messages = [ChatMessage(role=MessageRole.USER, content="Test")]
            
            # Should yield streaming content
            chunks = []
            async for chunk in client.chat_completion(messages, ChatMode.REGULAR):
                chunks.append(chunk)
            
            assert chunks == ["streaming content"]
    
    @pytest.mark.asyncio
    async def test_document_context_properly_injected(self, mock_client_config, sample_document):
        """Verify document context is properly injected."""
        with patch('backend.app.clients.openai_client.AsyncOpenAI') as mock_openai:
            mock_chunk = MagicMock()
            mock_chunk.choices = [MagicMock()]
            mock_chunk.choices[0].delta = MagicMock()
            mock_chunk.choices[0].delta.content = "response"
            mock_chunk.choices[0].finish_reason = "stop"
            
            async def mock_stream():
                yield mock_chunk
            
            mock_completion = AsyncMock(return_value=mock_stream())
            mock_client_instance = MagicMock()
            mock_client_instance.chat.completions.create = mock_completion
            mock_openai.return_value = mock_client_instance
            
            client = OpenAIClient(mock_client_config)
            messages = [ChatMessage(role=MessageRole.USER, content="Test")]
            
            # Test with document context
            async for chunk in client.chat_completion(
                messages, 
                ChatMode.DEEP_RESEARCH, 
                documents=[sample_document]
            ):
                pass
            
            # Verify system message includes document context
            call_args = mock_completion.call_args[1]
            system_message = call_args["messages"][0]
            assert system_message["role"] == "system"
            assert "AVAILABLE DOCUMENTS" in system_message["content"]
            assert sample_document.original_filename in system_message["content"]
    
    @pytest.mark.asyncio
    async def test_different_behavior_for_chat_modes(self, mock_client_config):
        """Verify different behavior for chat modes."""
        with patch('backend.app.clients.openai_client.AsyncOpenAI') as mock_openai:
            mock_chunk = MagicMock()
            mock_chunk.choices = [MagicMock()]
            mock_chunk.choices[0].delta = MagicMock()
            mock_chunk.choices[0].delta.content = "response"
            mock_chunk.choices[0].finish_reason = "stop"
            
            async def mock_stream():
                yield mock_chunk
            
            mock_completion = AsyncMock(return_value=mock_stream())
            mock_client_instance = MagicMock()
            mock_client_instance.chat.completions.create = mock_completion
            mock_openai.return_value = mock_client_instance
            
            client = OpenAIClient(mock_client_config)
            messages = [ChatMessage(role=MessageRole.USER, content="Test")]
            
            # Test regular mode
            async for chunk in client.chat_completion(messages, ChatMode.REGULAR):
                pass
            
            regular_call = mock_completion.call_args[1]
            regular_system_msg = regular_call["messages"][0]["content"]
            
            # Reset mock
            mock_completion.reset_mock()
            
            # Test deep research mode
            async for chunk in client.chat_completion(messages, ChatMode.DEEP_RESEARCH):
                pass
            
            research_call = mock_completion.call_args[1]
            research_system_msg = research_call["messages"][0]["content"]
            
            # System messages should be different
            assert "REGULAR MODE" in regular_system_msg
            assert "DEEP RESEARCH MODE" in research_system_msg
            assert "clear, concise responses" in regular_system_msg
            assert "comprehensive, detailed analysis" in research_system_msg
    
    @pytest.mark.asyncio
    async def test_robust_error_handling_and_retries(self, mock_client_config):
        """Verify robust error handling and retries."""
        with patch('backend.app.clients.openai_client.AsyncOpenAI') as mock_openai:
            mock_completion = AsyncMock()
            
            # Test non-retryable error
            mock_response = MagicMock()
            mock_response.request = MagicMock()
            mock_completion.side_effect = openai.AuthenticationError("Invalid API key", response=mock_response, body=None)
            mock_client_instance = MagicMock()
            mock_client_instance.chat.completions.create = mock_completion
            mock_openai.return_value = mock_client_instance
            
            client = OpenAIClient(mock_client_config)
            messages = [ChatMessage(role=MessageRole.USER, content="Test")]
            
            with pytest.raises(ModelClientAuthenticationError):
                async for chunk in client.chat_completion(messages, ChatMode.REGULAR):
                    pass
            
            # Should only be called once (no retry for auth errors)
            assert mock_completion.call_count == 1
