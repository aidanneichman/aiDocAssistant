"""OpenAI client implementation for the AI Legal Assistant.

This module provides a concrete implementation of the BaseModelClient
interface using OpenAI's GPT models with streaming support, retry logic,
and comprehensive error handling.
"""

import asyncio
import logging
from typing import AsyncIterator, List, Optional, Dict, Any

import openai
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionChunk

from backend.app.clients.base_model_client import BaseModelClient
from backend.app.models.chat import (
    ChatMessage, 
    ChatMode, 
    TokenUsage,
    ModelClientError,
    ModelClientConnectionError,
    ModelClientRateLimitError,
    ModelClientInvalidRequestError,
    ModelClientAuthenticationError
)
from backend.app.models.document import Document

logger = logging.getLogger(__name__)


class OpenAIClient(BaseModelClient):
    """OpenAI implementation of the model client interface.
    
    Provides streaming chat completions using OpenAI's GPT models with
    robust error handling, retry logic, and document context injection.
    """

    # Default model configurations
    DEFAULT_MODEL = "gpt-4-turbo-preview"
    DEFAULT_MAX_TOKENS = 2048
    DEFAULT_TEMPERATURE = 0.7
    
    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0
    BACKOFF_MULTIPLIER = 2.0

    def __init__(self, config: Dict[str, Any]):
        """Initialize OpenAI client.
        
        Args:
            config: Configuration dictionary containing:
                - api_key: OpenAI API key
                - model: Model name (optional, defaults to gpt-4-turbo-preview)
                - max_tokens: Default max tokens (optional)
                - temperature: Default temperature (optional)
                - timeout: Request timeout in seconds (optional)
        """
        super().__init__(config)
        
        # Extract configuration
        self.api_key = config.get("api_key")
        if not self.api_key:
            raise ModelClientError("OpenAI API key is required")
        
        self.model = config.get("model", self.DEFAULT_MODEL)
        self.default_max_tokens = config.get("max_tokens", self.DEFAULT_MAX_TOKENS)
        self.default_temperature = config.get("temperature", self.DEFAULT_TEMPERATURE)
        self.timeout = config.get("timeout", 60.0)
        
        # Initialize OpenAI client
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            timeout=self.timeout
        )
        
        # Track last completion for token usage
        self._last_token_usage: Optional[TokenUsage] = None
        
        self.logger.info(f"OpenAI client initialized with model: {self.model}")

    async def chat_completion(
        self,
        messages: List[ChatMessage],
        mode: ChatMode,
        documents: Optional[List[Document]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate a streaming chat completion using OpenAI.
        
        Args:
            messages: List of chat messages for context
            mode: Chat mode (regular or deep_research)
            documents: Optional list of documents to include in context
            max_tokens: Maximum tokens for response
            temperature: Response randomness (0-1)
            **kwargs: Additional OpenAI-specific parameters
            
        Yields:
            str: Content chunks as they are generated
            
        Raises:
            ModelClientError: If completion fails
        """
        try:
            # Build system message with document context
            system_prompt = self._build_system_prompt(mode, documents)
            
            # Prepare messages for API
            api_messages = [{"role": "system", "content": system_prompt}]
            api_messages.extend(self._sanitize_messages(messages))
            
            # Set parameters
            completion_params = {
                "model": self.model,
                "messages": api_messages,
                "max_tokens": max_tokens or self.default_max_tokens,
                "temperature": temperature or self.default_temperature,
                "stream": True,
                **kwargs
            }
            
            self.logger.info(f"Starting streaming completion with {len(api_messages)} messages")
            
            # Make streaming request with retry logic
            async for chunk_content in self._stream_with_retry(completion_params):
                yield chunk_content
                
        except Exception as e:
            self.logger.error(f"Chat completion failed: {e}")
            raise self._handle_openai_error(e)

    async def _stream_with_retry(self, params: Dict[str, Any]) -> AsyncIterator[str]:
        """Stream completion with retry logic and error handling.
        
        Args:
            params: Completion parameters
            
        Yields:
            str: Content chunks
            
        Raises:
            ModelClientError: If all retries fail
        """
        last_error = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                async for chunk_content in self._stream_completion(params):
                    yield chunk_content
                return  # Success, exit retry loop
                
            except Exception as e:
                last_error = e
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}")
                
                # Don't retry on certain errors
                if self._is_non_retryable_error(e):
                    break
                
                # Wait before retry (exponential backoff)
                if attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_DELAY * (self.BACKOFF_MULTIPLIER ** attempt)
                    self.logger.info(f"Retrying in {delay:.1f} seconds...")
                    await asyncio.sleep(delay)
        
        # All retries failed
        raise self._handle_openai_error(last_error)

    async def _stream_completion(self, params: Dict[str, Any]) -> AsyncIterator[str]:
        """Stream a single completion attempt.
        
        Args:
            params: Completion parameters
            
        Yields:
            str: Content chunks
        """
        prompt_tokens = 0
        completion_tokens = 0
        
        try:
            stream = await self.client.chat.completions.create(**params)
            
            async for chunk in stream:
                # Handle different chunk types
                if hasattr(chunk, 'choices') and chunk.choices:
                    choice = chunk.choices[0]
                    
                    # Extract content
                    if hasattr(choice, 'delta') and choice.delta:
                        if hasattr(choice.delta, 'content') and choice.delta.content:
                            yield choice.delta.content
                            completion_tokens += 1
                    
                    # Handle finish reason
                    if hasattr(choice, 'finish_reason') and choice.finish_reason:
                        self.logger.debug(f"Completion finished: {choice.finish_reason}")
                
                # Track usage if available
                if hasattr(chunk, 'usage') and chunk.usage:
                    prompt_tokens = chunk.usage.prompt_tokens
                    completion_tokens = chunk.usage.completion_tokens
                    
        except Exception as e:
            self.logger.error(f"Streaming completion failed: {e}")
            raise
        
        finally:
            # Store token usage
            if prompt_tokens or completion_tokens:
                self._last_token_usage = TokenUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens
                )

    def _is_non_retryable_error(self, error: Exception) -> bool:
        """Check if an error should not be retried.
        
        Args:
            error: The error to check
            
        Returns:
            bool: True if error should not be retried
        """
        # Authentication errors should not be retried
        if isinstance(error, openai.AuthenticationError):
            return True
        
        # Invalid request errors should not be retried
        if isinstance(error, openai.BadRequestError):
            return True
        
        # Permission errors should not be retried
        if isinstance(error, openai.PermissionDeniedError):
            return True
        
        return False

    def _handle_openai_error(self, error: Exception) -> ModelClientError:
        """Convert OpenAI errors to model client errors.
        
        Args:
            error: OpenAI error
            
        Returns:
            ModelClientError: Converted error
        """
        if isinstance(error, openai.AuthenticationError):
            return ModelClientAuthenticationError(f"OpenAI authentication failed: {error}")
        
        elif isinstance(error, openai.RateLimitError):
            return ModelClientRateLimitError(f"OpenAI rate limit exceeded: {error}")
        
        elif isinstance(error, openai.BadRequestError):
            return ModelClientInvalidRequestError(f"Invalid OpenAI request: {error}")
        
        elif isinstance(error, (openai.APIConnectionError, openai.APITimeoutError)):
            return ModelClientConnectionError(f"OpenAI connection error: {error}")
        
        else:
            return ModelClientError(f"OpenAI error: {error}")

    async def get_token_usage(self) -> Optional[TokenUsage]:
        """Get token usage information from the last completion.
        
        Returns:
            TokenUsage: Token usage information, or None if not available
        """
        return self._last_token_usage

    async def validate_connection(self) -> bool:
        """Validate that the client can connect to OpenAI.
        
        Returns:
            bool: True if connection is valid, False otherwise
        """
        try:
            # Make a minimal request to test connection
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1,
                stream=False
            )
            
            return response is not None
            
        except Exception as e:
            self.logger.warning(f"Connection validation failed: {e}")
            return False

    def get_model_name(self) -> str:
        """Get the name/identifier of the model being used.
        
        Returns:
            str: Model name/identifier
        """
        return self.model

    async def get_available_models(self) -> List[str]:
        """Get list of available OpenAI models.
        
        Returns:
            List[str]: Available model names
        """
        try:
            models = await self.client.models.list()
            return [model.id for model in models.data if 'gpt' in model.id.lower()]
        except Exception as e:
            self.logger.error(f"Failed to get available models: {e}")
            return [self.model]  # Return current model as fallback

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for a given text.
        
        This is a rough estimation based on character count.
        For precise token counting, consider using tiktoken library.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            int: Estimated token count
        """
        # Rough estimation: ~4 characters per token for English text
        return len(text) // 4

    def get_model_limits(self) -> Dict[str, int]:
        """Get model-specific limits.
        
        Returns:
            dict: Model limits including max_tokens, context_window, etc.
        """
        # Model-specific limits (these are approximate and may change)
        limits = {
            "gpt-4-turbo-preview": {"max_tokens": 4096, "context_window": 128000},
            "gpt-4": {"max_tokens": 4096, "context_window": 8192},
            "gpt-3.5-turbo": {"max_tokens": 4096, "context_window": 16384},
        }
        
        return limits.get(self.model, {"max_tokens": 4096, "context_window": 8192})

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        if hasattr(self.client, 'close'):
            await self.client.close()


def create_openai_client(api_key: str, **kwargs) -> OpenAIClient:
    """Factory function to create an OpenAI client.
    
    Args:
        api_key: OpenAI API key
        **kwargs: Additional configuration options
        
    Returns:
        OpenAIClient: Configured OpenAI client
    """
    config = {"api_key": api_key, **kwargs}
    return OpenAIClient(config)
