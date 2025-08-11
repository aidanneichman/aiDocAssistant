# AI Legal Assistant

A production-ready AI legal assistant that allows users to upload legal documents and chat with an AI model in two modes: Regular and Deep Research. Built with FastAPI, React, and OpenAI integration.

## 🚀 Features

- **Document Management**: Upload, store, and manage legal documents (PDF, DOCX, TXT)
- **AI Chat Interface**: Interactive chat with two distinct modes:
  - **Regular Mode**: Standard AI responses
  - **Deep Research Mode**: Enhanced analysis with document context
- **Real-time Streaming**: Server-Sent Events (SSE) for live token streaming
- **Content-Addressed Storage**: Secure file storage with SHA-256 hashing
- **Session Persistence**: Chat session history and management
- **Modern UI**: Responsive React frontend with Tailwind CSS

## 🏗️ Architecture

### Backend (FastAPI)
- **FastAPI**: Modern, fast web framework for building APIs
- **Poetry**: Dependency management and packaging
- **Uvicorn**: ASGI server for production deployment
- **Pydantic**: Data validation and settings management
- **aiofiles**: Asynchronous file I/O operations

### Frontend (React + Vite)
- **React 18**: Modern React with hooks and functional components
- **Vite**: Fast build tool and dev server
- **TypeScript**: Type-safe JavaScript development
- **Tailwind CSS**: Utility-first CSS framework
- **Headless UI**: Accessible UI components

### AI Integration
- **OpenAI API**: GPT model integration with streaming
- **Pluggable Architecture**: Base model client interface for easy model switching
- **Retry Logic**: Exponential backoff and error handling
- **Token Usage Tracking**: Monitor API usage and costs

## 📁 Project Structure

```
mock/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── clients/           # AI model clients
│   │   ├── models/            # Pydantic data models
│   │   ├── routes/            # API endpoints
│   │   ├── services/          # Business logic
│   │   ├── utils/             # Utility functions
│   │   ├── config.py          # Configuration management
│   │   └── main.py            # FastAPI application
│   └── tests/                 # Backend test suite
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── hooks/             # Custom React hooks
│   │   ├── api/               # API client
│   │   ├── types/             # TypeScript type definitions
│   │   └── utils/             # Frontend utilities
│   └── tests/                 # Frontend test suite
├── storage/                    # Document storage (auto-created)
├── tasks/                      # Development task specifications
├── pyproject.toml             # Poetry configuration
├── .env.example               # Environment variables template
└── README.md                  # This file
```

## 🛠️ Setup & Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- Poetry (Python package manager)
- OpenAI API key

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd mock
   ```

2. **Install Python dependencies**
   ```bash
   poetry install
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API key and other settings
   ```

4. **Start the backend server**
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   poetry run uvicorn backend.app.main:app --reload
   ```

### Frontend Setup

1. **Install Node.js dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Start the development server**
   ```bash
   npm run dev
   ```

3. **Access the application**
   - Frontend: http://localhost:5173
   - Backend: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## 🔧 Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key

# File Upload Settings
UPLOAD_MAX_SIZE_MB=50

# Storage Paths
STORAGE_PATH=./storage/documents
SESSION_STORAGE_PATH=./storage/sessions

# Server Configuration
ENVIRONMENT=development
DEBUG=true
HOST=127.0.0.1
PORT=8000

# CORS Settings
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

### API Endpoints

- `POST /api/documents/upload` - Upload documents
- `GET /api/documents` - List uploaded documents
- `DELETE /api/documents/{document_id}` - Delete document
- `POST /api/chat/sessions` - Create chat session
- `POST /api/chat/sessions/{session_id}/messages` - Send message
- `GET /api/chat/sessions/{session_id}` - Get session history

## 🧪 Testing

### Backend Tests
```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=backend

# Run specific test file
poetry run pytest backend/tests/unit/test_task_1_1_poetry_init.py
```

### Frontend Tests
```bash
cd frontend

# Run tests once
npm run test

# Run tests in watch mode
npm run test:watch
```

## 🚀 Development Workflow

### Task-Based Development
This project follows a structured task-based development approach:

1. **Phase 1**: Project Setup & Infrastructure
2. **Phase 2**: Document Storage System
3. **Phase 3**: Pluggable AI Model Client
4. **Phase 4**: FastAPI Backend
5. **Phase 5**: React Frontend
6. **Phase 6**: Integration & Polish

Each task includes:
- Detailed specifications
- Unit tests
- Success criteria
- Implementation files

### Code Quality
- **Ruff**: Python linting and formatting
- **MyPy**: Type checking
- **Prettier**: Frontend code formatting
- **ESLint**: JavaScript/TypeScript linting

## 📚 API Documentation

Once the backend is running, visit http://localhost:8000/docs for interactive API documentation powered by FastAPI's automatic OpenAPI generation.

## 🔒 Security Features

- **File Validation**: MIME type and content validation
- **Dangerous Extension Blocking**: Prevents execution of malicious files
- **Content-Addressed Storage**: Tamper-evident file storage
- **Environment Variable Management**: Secure configuration handling
- **CORS Configuration**: Controlled cross-origin access

## 🚀 Deployment

### Production Considerations
- Set `ENVIRONMENT=production`
- Configure proper CORS origins
- Use environment variables for all secrets
- Set up proper logging and monitoring
- Configure reverse proxy (nginx) for production
- Use process manager (systemd, supervisor) for backend
- Build and serve frontend from static files

### Docker Support
```bash
# Build backend image
docker build -t ai-legal-assistant-backend ./backend

# Build frontend image
docker build -t ai-legal-assistant-frontend ./frontend

# Run with docker-compose
docker-compose up
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Follow the task-based development approach
4. Add comprehensive tests
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

This project is part of a mock interview exercise. Please refer to the original interview brief for usage terms.

## 🆘 Troubleshooting

### Common Issues

1. **OpenAI API Key Error**
   - Ensure `OPENAI_API_KEY` is set in environment
   - Check API key validity and quota

2. **Port Already in Use**
   - Kill existing processes: `lsof -ti:8000 | xargs kill -9`
   - Use different ports in configuration

3. **File Upload Failures**
   - Check file size limits
   - Verify file type support
   - Ensure storage directory permissions

4. **Frontend Build Issues**
   - Clear node_modules: `rm -rf node_modules && npm install`
   - Check Node.js version compatibility

## 🔮 Future Enhancements

- **Vector Database Integration**: Document similarity search
- **Multi-Model Support**: Anthropic, Google, local models
- **Advanced Document Processing**: OCR, table extraction
- **User Authentication**: Multi-user support
- **Audit Logging**: Comprehensive activity tracking
- **Performance Monitoring**: Metrics and alerting
- **Mobile App**: React Native or PWA
- **API Rate Limiting**: Request throttling and quotas

---

**Built with ❤️ for AI-powered legal assistance**
