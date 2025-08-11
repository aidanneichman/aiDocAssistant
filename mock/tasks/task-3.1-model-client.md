# Task 3.1: Model Client Interface & OpenAI Implementation

## Objective
Create pluggable model client interface with OpenAI implementation supporting different chat modes and document context.

## Files to Create
- `backend/app/clients/base_model_client.py` - Abstract base class
- `backend/app/clients/openai_client.py` - OpenAI implementation
- `backend/app/models/chat.py` - Chat request/response models

## Model Client Interface
```python
class BaseModelClient(ABC):
    @abstractmethod
    async def chat_completion(
        self, 
        messages: List[ChatMessage], 
        mode: ChatMode,
        documents: List[Document] = None
    ) -> AsyncIterator[str]:
        pass
```

## Chat Models
- `ChatMessage` - Individual message with role and content
- `ChatMode` - Enum for Deep Research vs Regular modes
- `ChatRequest` - Request payload for chat endpoint
- `ChatResponse` - Response payload with streaming support

## OpenAI Client Features
- Async streaming chat completions
- Document context injection into system prompts
- Different prompts for Deep Research vs Regular modes
- Retry logic with exponential backoff
- Error handling and logging
- Token usage tracking

## Chat Modes
- **Regular Mode**: Standard conversational responses
- **Deep Research Mode**: Detailed analysis with document citations

## Success Criteria
- Abstract interface allows swapping model providers
- OpenAI client handles streaming responses
- Document context properly injected
- Different behavior for chat modes
- Robust error handling and retries

## Tests
- `tests/unit/test_model_clients.py`
  - Test interface compliance
  - Test OpenAI client with mocked responses
  - Test document context injection
  - Test different chat modes
  - Test error handling and retries
