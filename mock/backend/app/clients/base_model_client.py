"""Abstract base class for model clients.

This module defines the interface that all model clients must implement,
allowing for pluggable AI model providers.
"""

import logging
from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Optional, Dict, Any

from backend.app.models.chat import ChatMessage, ChatMode, TokenUsage
from backend.app.models.document import Document

logger = logging.getLogger(__name__)


class BaseModelClient(ABC):
    """Abstract base class for AI model clients.
    
    This interface defines the contract that all model clients must implement,
    enabling easy swapping between different AI providers (OpenAI, Anthropic, etc.).
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize the model client with configuration.
        
        Args:
            config: Configuration dictionary containing API keys, endpoints, etc.
        """
        self.config = config
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")

    @abstractmethod
    async def chat_completion(
        self,
        messages: List[ChatMessage],
        mode: ChatMode,
        documents: Optional[List[Document]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate a streaming chat completion.
        
        Args:
            messages: List of chat messages for context
            mode: Chat mode (regular or deep_research)
            documents: Optional list of documents to include in context
            max_tokens: Maximum tokens for response
            temperature: Response randomness (0-1)
            **kwargs: Additional provider-specific parameters
            
        Yields:
            str: Content chunks as they are generated
            
        Raises:
            ModelClientError: If completion fails
        """
        pass

    @abstractmethod
    async def get_token_usage(self) -> Optional[TokenUsage]:
        """Get token usage information from the last completion.
        
        Returns:
            TokenUsage: Token usage information, or None if not available
        """
        pass

    @abstractmethod
    async def validate_connection(self) -> bool:
        """Validate that the client can connect to the model provider.
        
        Returns:
            bool: True if connection is valid, False otherwise
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Get the name/identifier of the model being used.
        
        Returns:
            str: Model name/identifier
        """
        pass

    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check of the model client.
        
        Returns:
            dict: Health check results including status and metadata
        """
        try:
            is_connected = await self.validate_connection()
            return {
                "status": "healthy" if is_connected else "unhealthy",
                "model": self.get_model_name(),
                "provider": self.__class__.__name__,
                "connected": is_connected
            }
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "model": self.get_model_name(),
                "provider": self.__class__.__name__,
                "connected": False,
                "error": str(e)
            }

    def _build_system_prompt(
        self,
        mode: ChatMode,
        documents: Optional[List[Document]] = None
    ) -> str:
        """Build system prompt based on chat mode and available documents.
        
        Args:
            mode: Chat mode (regular or deep_research)
            documents: Optional list of documents for context
            
        Returns:
            str: System prompt
        """
        base_prompt = self._get_base_system_prompt()
        mode_prompt = self._get_mode_specific_prompt(mode)
        document_context = self._build_document_context(documents) if documents else ""
        
        prompt_parts = [base_prompt, mode_prompt]
        if document_context:
            prompt_parts.append(document_context)
            
        return "\n\n".join(prompt_parts)

    def _get_base_system_prompt(self) -> str:
        """Get the base system prompt for the AI legal assistant.
        
        Returns:
            str: Base system prompt
        """
        return """You are an AI Legal Assistant designed to help with legal document analysis and research. You provide accurate, helpful, and professional assistance with legal matters.

Key capabilities:
- Analyze legal documents and contracts
- Provide summaries and key point extraction
- Answer questions about legal concepts and procedures
- Offer research assistance and document review

Important guidelines:
- Always maintain professional tone and accuracy
- Cite specific document sections when referencing uploaded documents
- Clearly distinguish between factual information and legal interpretation
- Recommend consulting with qualified legal professionals for specific legal advice
- Never provide definitive legal conclusions without proper qualification"""

    def _get_mode_specific_prompt(self, mode: ChatMode) -> str:
        """Get mode-specific prompt additions.
        
        Args:
            mode: Chat mode
            
        Returns:
            str: Mode-specific prompt
        """
        if mode == ChatMode.DEEP_RESEARCH:
            return """DEEP RESEARCH MODE: Provide comprehensive, detailed analysis with:
- Thorough examination of all relevant document sections
- Multiple perspectives and considerations
- Detailed citations with specific page/section references
- Comprehensive background context and legal principles
- Step-by-step reasoning for complex issues
- Identification of potential risks, opportunities, and alternatives"""
        
        elif mode == ChatMode.REGULAR:
            return """REGULAR MODE: Provide clear, concise responses that:
- Address the user's question directly and efficiently
- Include key relevant information from documents when applicable
- Use accessible language while maintaining accuracy
- Provide practical guidance and next steps when appropriate"""
        
        else:
            return ""

    def _build_document_context(self, documents: List[Document]) -> str:
        """Build document context for the system prompt.
        
        Args:
            documents: List of documents to include in context
            
        Returns:
            str: Document context string
        """
        if not documents:
            return ""
        
        context_parts = ["AVAILABLE DOCUMENTS:"]
        
        for i, doc in enumerate(documents, 1):
            doc_info = f"{i}. **{doc.original_filename}** (ID: {doc.id[:16]}...)"
            doc_info += f"\n   - Type: {doc.content_type}"
            doc_info += f"\n   - Size: {doc.get_size_mb():.2f} MB"
            doc_info += f"\n   - Uploaded: {doc.upload_time.strftime('%Y-%m-%d %H:%M')}"
            context_parts.append(doc_info)
        
        context_parts.append(
            "\nWhen referencing these documents, use the filename and document ID. "
            "Provide specific citations where possible."
        )
        
        return "\n".join(context_parts)

    def _sanitize_messages(self, messages: List[ChatMessage]) -> List[Dict[str, str]]:
        """Convert ChatMessage objects to the format expected by model APIs.
        
        Args:
            messages: List of ChatMessage objects
            
        Returns:
            List[Dict[str, str]]: Messages in API format
        """
        api_messages = []
        
        for message in messages:
            api_messages.append({
                "role": message.role.value,
                "content": message.content
            })
        
        return api_messages

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Override in subclasses if cleanup is needed
        pass
