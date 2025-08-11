"""Unit tests for Task 1.2: Project Structure Creation.

Tests to verify that all directories and packages were created correctly
and that the basic FastAPI application is functional.
"""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


class TestProjectStructure:
    """Test that project directory structure is created correctly."""

    def test_backend_directories_exist(self) -> None:
        """Test that all backend directories were created."""
        base_path = Path("backend")
        
        expected_dirs = [
            "app",
            "app/routes", 
            "app/services",
            "app/clients",
            "app/models", 
            "app/utils",
            "storage",
            "storage/documents",
            "storage/sessions", 
            "tests",
            "tests/unit",
            "tests/integration",
        ]
        
        for dir_path in expected_dirs:
            full_path = base_path / dir_path
            assert full_path.exists(), f"Directory {full_path} should exist"
            assert full_path.is_dir(), f"{full_path} should be a directory"

    def test_frontend_directories_exist(self) -> None:
        """Test that basic frontend directories were created."""
        base_path = Path("frontend")
        
        expected_dirs = ["src", "public"]
        
        for dir_path in expected_dirs:
            full_path = base_path / dir_path
            assert full_path.exists(), f"Directory {full_path} should exist"
            assert full_path.is_dir(), f"{full_path} should be a directory"

    def test_python_packages_initialized(self) -> None:
        """Test that all Python packages have __init__.py files."""
        base_path = Path("backend")
        
        expected_packages = [
            "",  # backend/__init__.py
            "app",
            "app/routes",
            "app/services", 
            "app/clients",
            "app/models",
            "app/utils",
            "tests",
            "tests/unit",
            "tests/integration",
        ]
        
        for package_path in expected_packages:
            init_file = base_path / package_path / "__init__.py"
            assert init_file.exists(), f"__init__.py should exist in {base_path / package_path}"
            assert init_file.is_file(), f"{init_file} should be a file"

    def test_main_py_exists(self) -> None:
        """Test that main.py exists and contains FastAPI app."""
        main_file = Path("backend/app/main.py")
        assert main_file.exists(), "main.py should exist"
        assert main_file.is_file(), "main.py should be a file"
        
        # Check that it contains FastAPI app creation
        content = main_file.read_text()
        assert "FastAPI" in content, "main.py should contain FastAPI import"
        assert "app = FastAPI" in content, "main.py should create FastAPI app instance"

    def test_storage_directories_ready(self) -> None:
        """Test that storage directories are ready for file operations."""
        documents_dir = Path("backend/storage/documents")
        sessions_dir = Path("backend/storage/sessions")
        
        # Directories should exist and be writable
        assert documents_dir.exists() and documents_dir.is_dir()
        assert sessions_dir.exists() and sessions_dir.is_dir()
        
        # Test write permissions by creating temporary files
        test_doc_file = documents_dir / "test_write.tmp"
        test_session_file = sessions_dir / "test_write.tmp"
        
        try:
            test_doc_file.write_text("test")
            test_session_file.write_text("test")
            assert test_doc_file.exists()
            assert test_session_file.exists()
        finally:
            # Clean up test files
            test_doc_file.unlink(missing_ok=True)
            test_session_file.unlink(missing_ok=True)


class TestFastAPIApplication:
    """Test that the basic FastAPI application is functional."""

    def test_app_can_be_imported(self) -> None:
        """Test that the FastAPI app can be imported successfully."""
        from backend.app.main import app
        
        assert app is not None
        assert hasattr(app, 'title')
        assert hasattr(app, 'version')

    def test_app_configuration(self) -> None:
        """Test that the FastAPI app is configured correctly."""
        assert app.title == "AI Legal Assistant"
        assert app.version == "0.1.0"
        assert "ai legal assistant" in app.description.lower()

    def test_cors_middleware_configured(self) -> None:
        """Test that CORS middleware is properly configured."""
        # Check that CORS middleware is in the middleware stack
        # FastAPI wraps middleware, so we check that user_middleware was configured
        assert len(app.user_middleware) > 0, "CORS middleware should be configured"

    def test_root_endpoint_exists(self) -> None:
        """Test that the root endpoint is defined."""
        # Check that root endpoint is defined in the app routes
        routes = [route.path for route in app.routes]
        assert "/" in routes, "Root endpoint should be defined"

    def test_health_endpoint_exists(self) -> None:
        """Test that the health check endpoint is defined."""
        # Check that health endpoint is defined in the app routes
        routes = [route.path for route in app.routes]
        assert "/health" in routes, "Health endpoint should be defined"


class TestTaskSuccessCriteria:
    """Test all success criteria from Task 1.2 specification."""

    def test_all_directories_created_with_proper_structure(self) -> None:
        """Verify all directories created with proper structure."""
        # This combines several structure tests
        backend_structure = [
            "backend/app",
            "backend/app/routes",
            "backend/app/services", 
            "backend/app/clients",
            "backend/app/models",
            "backend/app/utils",
            "backend/storage/documents",
            "backend/storage/sessions",
            "backend/tests/unit",
            "backend/tests/integration",
        ]
        
        frontend_structure = [
            "frontend/src",
            "frontend/public",
        ]
        
        all_paths = backend_structure + frontend_structure
        
        for path_str in all_paths:
            path = Path(path_str)
            assert path.exists(), f"Directory {path} should exist"
            assert path.is_dir(), f"{path} should be a directory"

    def test_python_packages_properly_initialized(self) -> None:
        """Verify Python packages are properly initialized."""
        # Test that we can import from each package
        import backend
        import backend.app
        import backend.app.routes
        import backend.app.services
        import backend.app.clients
        import backend.app.models
        import backend.app.utils
        import backend.tests
        import backend.tests.unit
        import backend.tests.integration
        
        # All imports should succeed without error

    def test_storage_directories_ready_for_file_operations(self) -> None:
        """Verify storage directories are ready for file operations."""
        # Test creating and deleting files in storage directories
        import tempfile
        
        docs_dir = Path("backend/storage/documents")
        sessions_dir = Path("backend/storage/sessions")
        
        # Test documents directory
        with tempfile.NamedTemporaryFile(dir=docs_dir, delete=False) as tmp:
            tmp.write(b"test document")
            temp_path = Path(tmp.name)
        
        assert temp_path.exists()
        temp_path.unlink()
        
        # Test sessions directory  
        with tempfile.NamedTemporaryFile(dir=sessions_dir, delete=False) as tmp:
            tmp.write(b"test session")
            temp_path = Path(tmp.name)
            
        assert temp_path.exists()
        temp_path.unlink()

    def test_basic_fastapi_app_can_be_imported(self) -> None:
        """Verify basic FastAPI app can be imported."""
        from backend.app.main import app
        
        # Should be able to import without errors
        assert app is not None
        
        # Should be a FastAPI instance
        from fastapi import FastAPI
        assert isinstance(app, FastAPI)
        
        # Should have basic endpoints defined
        routes = [route.path for route in app.routes]
        assert "/" in routes, "Root endpoint should be defined"
        assert "/health" in routes, "Health endpoint should be defined"
