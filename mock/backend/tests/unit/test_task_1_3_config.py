"""Unit tests for Task 1.3: Environment Configuration.

Tests for the Pydantic-based configuration management system.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from backend.app.config import Settings, get_settings


class TestConfigurationLoading:
    """Test configuration loading from environment variables."""

    def test_configuration_with_valid_environment(self) -> None:
        """Test configuration loading with all valid environment variables."""
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-api-key-12345",
            "UPLOAD_MAX_SIZE_MB": "100",
            "STORAGE_PATH": "./test/storage/docs",
            "SESSION_STORAGE_PATH": "./test/storage/sessions",
            "ENVIRONMENT": "production",
            "DEBUG": "false",
            "HOST": "127.0.0.1",
            "PORT": "9000",
            "ALLOWED_ORIGINS": "http://example.com,https://app.example.com"
        }):
            settings = Settings()
            
            assert settings.openai_api_key == "test-api-key-12345"
            assert settings.upload_max_size_mb == 100
            assert settings.environment == "production"
            assert settings.debug is False
            assert settings.host == "127.0.0.1"
            assert settings.port == 9000
            origins_list = settings.get_allowed_origins_list()
            assert "http://example.com" in origins_list
            assert "https://app.example.com" in origins_list

    def test_configuration_with_missing_required_field(self) -> None:
        """Test that missing required fields raise validation errors."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            
            # Should complain about missing openai_api_key
            error_msg = str(exc_info.value)
            assert "openai_api_key" in error_msg.lower()

    def test_configuration_with_invalid_openai_key(self) -> None:
        """Test validation of OpenAI API key."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            
            error_msg = str(exc_info.value)
            assert "openai_api_key" in error_msg.lower()


class TestDefaultValues:
    """Test that default values are applied correctly."""

    def test_default_value_application(self) -> None:
        """Test that default values are applied when env vars not set."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            settings = Settings()
            
            # Test defaults
            assert settings.upload_max_size_mb == 50
            assert settings.environment == "development"
            assert settings.debug is True
            assert settings.host == "0.0.0.0"
            assert settings.port == 8000
            origins_list = settings.get_allowed_origins_list()
            assert "http://localhost:3000" in origins_list
            assert "http://localhost:5173" in origins_list

    def test_default_storage_paths(self) -> None:
        """Test that default storage paths are set correctly."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            settings = Settings()
            
            # Default paths should be set
            assert "backend/storage/documents" in str(settings.storage_path)
            assert "backend/storage/sessions" in str(settings.session_storage_path)
            
            # Paths should be absolute after validation
            assert settings.storage_path.is_absolute()
            assert settings.session_storage_path.is_absolute()


class TestValidation:
    """Test validation of configuration fields."""

    def test_upload_size_validation(self) -> None:
        """Test upload size validation."""
        # Test invalid upload size (too small)
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
            "UPLOAD_MAX_SIZE_MB": "0"
        }):
            with pytest.raises(ValidationError):
                Settings()
        
        # Test invalid upload size (too large)
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key", 
            "UPLOAD_MAX_SIZE_MB": "2000"
        }):
            with pytest.raises(ValidationError):
                Settings()

    def test_port_validation(self) -> None:
        """Test port number validation."""
        # Test invalid port (too small)
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
            "PORT": "0"
        }):
            with pytest.raises(ValidationError):
                Settings()
        
        # Test invalid port (too large)
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
            "PORT": "70000"
        }):
            with pytest.raises(ValidationError):
                Settings()

    def test_environment_validation(self) -> None:
        """Test environment validation."""
        # Test invalid environment
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
            "ENVIRONMENT": "invalid_env"
        }):
            with pytest.raises(ValidationError):
                Settings()
        
        # Test valid environments
        valid_envs = ["development", "production", "testing"]
        for env in valid_envs:
            with patch.dict(os.environ, {
                "OPENAI_API_KEY": "test-key",
                "ENVIRONMENT": env
            }):
                settings = Settings()
                assert settings.environment == env

    def test_cors_origins_parsing(self) -> None:
        """Test CORS origins parsing from string."""
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
            "ALLOWED_ORIGINS": "http://example.com, https://app.com ,http://test.com"
        }):
            settings = Settings()
            
            origins_list = settings.get_allowed_origins_list()
            expected_origins = ["http://example.com", "https://app.com", "http://test.com"]
            assert all(origin in origins_list for origin in expected_origins)


class TestPathResolution:
    """Test path resolution and validation."""

    def test_storage_path_creation(self) -> None:
        """Test that storage paths are created if they don't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            docs_path = temp_path / "test_docs"
            sessions_path = temp_path / "test_sessions"
            
            # Paths don't exist yet
            assert not docs_path.exists()
            assert not sessions_path.exists()
            
            with patch.dict(os.environ, {
                "OPENAI_API_KEY": "test-key",
                "STORAGE_PATH": str(docs_path),
                "SESSION_STORAGE_PATH": str(sessions_path)
            }):
                settings = Settings()
                
                # Paths should be created and absolute
                assert settings.storage_path.exists()
                assert settings.session_storage_path.exists()
                assert settings.storage_path.is_absolute()
                assert settings.session_storage_path.is_absolute()

    def test_path_write_permissions(self) -> None:
        """Test that storage paths are writable."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {
                "OPENAI_API_KEY": "test-key",
                "STORAGE_PATH": temp_dir,
                "SESSION_STORAGE_PATH": temp_dir
            }):
                settings = Settings()
                
                # Should be able to create test files
                test_file = settings.storage_path / "test.txt"
                test_file.write_text("test")
                assert test_file.exists()
                test_file.unlink()


class TestSettingsHelperMethods:
    """Test helper methods on Settings class."""

    def test_get_upload_max_size_bytes(self) -> None:
        """Test conversion of MB to bytes."""
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
            "UPLOAD_MAX_SIZE_MB": "50"
        }):
            settings = Settings()
            
            expected_bytes = 50 * 1024 * 1024  # 50 MB in bytes
            assert settings.get_upload_max_size_bytes() == expected_bytes

    def test_environment_check_methods(self) -> None:
        """Test environment checking helper methods."""
        # Test development environment
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
            "ENVIRONMENT": "development"
        }):
            settings = Settings()
            assert settings.is_development() is True
            assert settings.is_production() is False
            assert settings.is_testing() is False
        
        # Test production environment
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
            "ENVIRONMENT": "production"
        }):
            settings = Settings()
            assert settings.is_development() is False
            assert settings.is_production() is True
            assert settings.is_testing() is False
        
        # Test testing environment
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
            "ENVIRONMENT": "testing"
        }):
            settings = Settings()
            assert settings.is_development() is False
            assert settings.is_production() is False
            assert settings.is_testing() is True


class TestSettingsImportability:
    """Test that settings can be imported and used across the app."""

    def test_settings_import(self) -> None:
        """Test that settings can be imported successfully."""
        # This will fail if there are import issues
        from backend.app.config import settings, get_settings
        
        # Both should be accessible
        assert settings is not None
        assert get_settings is not None

    def test_get_settings_function(self) -> None:
        """Test the get_settings function."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            settings_instance = get_settings()
            assert isinstance(settings_instance, Settings)
            assert settings_instance.openai_api_key == "test-key"


class TestTaskSuccessCriteria:
    """Test all success criteria from Task 1.3 specification."""

    def test_configuration_loads_from_environment_variables(self) -> None:
        """Verify configuration loads from environment variables."""
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "env-test-key",
            "UPLOAD_MAX_SIZE_MB": "75",
            "ENVIRONMENT": "production"
        }):
            settings = Settings()
            
            # Should load from environment
            assert settings.openai_api_key == "env-test-key"
            assert settings.upload_max_size_mb == 75
            assert settings.environment == "production"

    def test_type_validation_works_correctly(self) -> None:
        """Verify type validation works correctly."""
        # Test that invalid types are rejected
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
            "UPLOAD_MAX_SIZE_MB": "not_a_number"
        }):
            with pytest.raises(ValidationError):
                Settings()

    def test_default_values_applied(self) -> None:
        """Verify default values are applied."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            settings = Settings()
            
            # Check that defaults are applied
            assert settings.upload_max_size_mb == 50  # default
            assert settings.environment == "development"  # default
            assert settings.debug is True  # default

    def test_configuration_easily_importable(self) -> None:
        """Verify configuration is easily importable across the app."""
        # Test multiple import patterns
        from backend.app.config import settings
        from backend.app.config import Settings
        from backend.app.config import get_settings
        
        # All should be importable without error
        assert settings is not None
        assert Settings is not None
        assert get_settings is not None

    def test_missing_required_variables_raise_clear_errors(self) -> None:
        """Verify missing required variables raise clear errors."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises((ValidationError, ValueError)) as exc_info:
                Settings()
            
            # Error message should mention the missing field
            error_msg = str(exc_info.value).lower()
            assert "openai_api_key" in error_msg or "openai" in error_msg
