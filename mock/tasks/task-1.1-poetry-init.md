# Task 1.1: Initialize Poetry Project

## Objective
Set up Poetry project with proper dependencies, configuration, and development scripts.

## Files to Create
- `pyproject.toml` - Poetry configuration with dependencies and scripts
- `.env.example` - Environment variable template  
- `.gitignore` - Ignore patterns for Python/Node projects

## Dependencies

### Runtime Dependencies
- `fastapi` - Web framework
- `uvicorn[standard]` - ASGI server
- `python-multipart` - File upload support
- `aiofiles` - Async file operations
- `openai` - OpenAI API client
- `pydantic` - Data validation
- `python-dotenv` - Environment variable loading

### Development Dependencies
- `pytest` - Testing framework
- `pytest-asyncio` - Async testing support
- `pytest-watch` - Test watching
- `ruff` - Linting and formatting
- `mypy` - Type checking

## Poetry Scripts to Add
- `dev` - Start backend development server: `uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000`
- `test` - Run tests: `pytest -v`
- `watch` - Watch tests: `ptw --runner "pytest -v"`
- `fmt` - Format code: `ruff check --fix . && ruff format .`
- `typecheck` - Type check: `mypy backend/`

## Environment Variables (.env.example)
```
OPENAI_API_KEY=your_openai_api_key_here
UPLOAD_MAX_SIZE_MB=50
STORAGE_PATH=./storage/documents
SESSION_STORAGE_PATH=./storage/sessions
```

## Success Criteria
- Poetry project initialized with Python 3.11+ requirement
- All dependencies installed successfully
- Scripts work with `poetry run <script>`
- Environment template created
- Git ignore patterns set up

## Tests
None required (setup task)
