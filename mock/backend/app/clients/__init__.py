"""Model clients for the AI Legal Assistant.

This package provides pluggable AI model client implementations with
a common interface for different providers (OpenAI, Anthropic, etc.).
"""

from .base_model_client import BaseModelClient
from .openai_client import OpenAIClient, create_openai_client

__all__ = [
    "BaseModelClient",
    "OpenAIClient", 
    "create_openai_client"
]