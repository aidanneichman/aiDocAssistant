"""Configuration management for AI Legal Assistant.

This module provides type-safe environment variable loading using Pydantic.
All application configuration should be accessed through the Settings class.
"""

import os
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.
    
    Uses Pydantic BaseSettings for type-safe environment variable handling
    with validation and default values.
    """
    
    # OpenAI Configuration
    openai_api_key: str = Field(
        ..., 
        description="OpenAI API key for model access",
        min_length=1
    )
    
    # File Upload Configuration  
    upload_max_size_mb: int = Field(
        default=50,
        description="Maximum file upload size in megabytes",
        ge=1,
        le=1000
    )
    
    # Storage Configuration
    storage_path: Path = Field(
        default=Path("./backend/storage/documents"),
        description="Directory path for document storage"
    )
    
    session_storage_path: Path = Field(
        default=Path("./backend/storage/sessions"),
        description="Directory path for session storage"
    )
    
    # Application Configuration
    environment: str = Field(
        default="development",
        description="Application environment (development, production, testing)"
    )
    
    debug: bool = Field(
        default=True,
        description="Enable debug mode"
    )
    
    # Server Configuration
    host: str = Field(
        default="0.0.0.0",
        description="Server host address"
    )
    
    port: int = Field(
        default=8000,
        description="Server port number",
        ge=1,
        le=65535
    )
    
    # CORS Configuration
    allowed_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        description="Comma-separated list of allowed CORS origins"
    )

    @field_validator("storage_path", "session_storage_path")
    @classmethod
    def validate_storage_paths(cls, v: Path) -> Path:
        """Validate and create storage directories if they don't exist."""
        # Convert to absolute path for consistency
        abs_path = v.resolve()
        
        # Create directory if it doesn't exist
        abs_path.mkdir(parents=True, exist_ok=True)
        
        # Verify directory is writable
        if not os.access(abs_path, os.W_OK):
            raise ValueError(f"Storage path {abs_path} is not writable")
            
        return abs_path

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        allowed_envs = {"development", "production", "testing"}
        if v.lower() not in allowed_envs:
            raise ValueError(f"Environment must be one of: {allowed_envs}")
        return v.lower()

    def get_allowed_origins_list(self) -> List[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    def get_upload_max_size_bytes(self) -> int:
        """Get maximum upload size in bytes."""
        return self.upload_max_size_mb * 1024 * 1024

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment == "testing"


def get_settings() -> Settings:
    """Get application settings instance.
    
    This function can be used for dependency injection in FastAPI
    or when you need a fresh settings instance.
    """
    try:
        return Settings()
    except Exception as e:
        # Provide helpful error message for missing configuration
        if "openai_api_key" in str(e).lower():
            raise ValueError(
                "OPENAI_API_KEY environment variable is required. "
                "Please set it in your .env file or environment."
            ) from e
        raise


# Global settings instance
# This will be imported throughout the application
settings = get_settings()
