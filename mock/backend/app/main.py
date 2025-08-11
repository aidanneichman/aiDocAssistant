"""AI Legal Assistant FastAPI Application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.routes.documents import router as documents_router
from backend.app.routes.chat import router as chat_router

# Create FastAPI application instance
app = FastAPI(
    title="AI Legal Assistant",
    description="A production-style AI legal assistant with document upload and chat capabilities",
    version="0.1.0",
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(documents_router)
app.include_router(chat_router)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint returning basic API information."""
    return {
        "message": "AI Legal Assistant API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
