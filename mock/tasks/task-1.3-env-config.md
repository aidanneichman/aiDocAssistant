# Task 1.3: Environment Configuration

## Objective
Create configuration management system using Pydantic for type-safe environment variable handling.

## Files to Create
- `backend/app/config.py` - Configuration management with Pydantic
- Update `.env.example` if needed

## Configuration Features
- Type-safe environment variable loading
- Default values for development
- Validation of required variables
- Support for different environments (dev, prod)

## Environment Variables
- `OPENAI_API_KEY` - OpenAI API key (required)
- `UPLOAD_MAX_SIZE_MB` - Maximum file upload size (default: 50)
- `STORAGE_PATH` - Document storage path (default: ./storage/documents)
- `SESSION_STORAGE_PATH` - Session storage path (default: ./storage/sessions)
- `ENVIRONMENT` - Environment name (default: development)

## Configuration Class Structure
```python
class Settings(BaseSettings):
    openai_api_key: str
    upload_max_size_mb: int = 50
    storage_path: Path = Path("./storage/documents")
    session_storage_path: Path = Path("./storage/sessions")
    environment: str = "development"
    
    class Config:
        env_file = ".env"
```

## Success Criteria
- Configuration loads from environment variables
- Type validation works correctly
- Default values are applied
- Configuration is easily importable across the app
- Missing required variables raise clear errors

## Tests
- `tests/unit/test_config.py`
  - Test configuration loading with valid environment
  - Test default value application
  - Test validation of required fields
  - Test path resolution
