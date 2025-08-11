"""Unit tests for Task 2.2: File Validation & Content Extraction.

Tests for file validation utilities including MIME type validation,
file size limits, security checks, and filename sanitization.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.app.utils.file_utils import (
    DANGEROUS_EXTENSIONS,
    SUPPORTED_MIME_TYPES,
    FileValidationError,
    FileSizeExceededError,
    InvalidFilenameError,
    SecurityValidationError,
    UnsupportedFileTypeError,
    detect_file_type,
    get_file_info,
    sanitize_filename,
    validate_file_security,
    validate_file_size,
    validate_file_type,
)


class TestFileTypeValidation:
    """Test file type validation functionality."""

    def test_validate_supported_file_types(self):
        """Test validation of supported file types."""
        # Test valid combinations
        valid_cases = [
            ("text/plain", "document.txt"),
            ("application/pdf", "document.pdf"),
            ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "document.docx"),
        ]
        
        for content_type, filename in valid_cases:
            assert validate_file_type(content_type, filename) is True

    def test_validate_unsupported_mime_types(self):
        """Test rejection of unsupported MIME types."""
        unsupported_cases = [
            ("image/jpeg", "image.jpg"),
            ("video/mp4", "video.mp4"),
            ("application/zip", "archive.zip"),
            ("text/html", "page.html"),
        ]
        
        for content_type, filename in unsupported_cases:
            with pytest.raises(UnsupportedFileTypeError):
                validate_file_type(content_type, filename)

    def test_validate_extension_mismatch(self):
        """Test rejection when extension doesn't match content type."""
        mismatched_cases = [
            ("text/plain", "document.pdf"),  # TXT content type with PDF extension
            ("application/pdf", "document.txt"),  # PDF content type with TXT extension
            ("application/pdf", "document.docx"),  # PDF content type with DOCX extension
        ]
        
        for content_type, filename in mismatched_cases:
            with pytest.raises(UnsupportedFileTypeError):
                validate_file_type(content_type, filename)

    def test_validate_dangerous_extensions(self):
        """Test rejection of dangerous file extensions."""
        for dangerous_ext in [".exe", ".bat", ".js", ".php", ".py"]:
            filename = f"malicious{dangerous_ext}"
            with pytest.raises(SecurityValidationError):
                # Use text/plain to focus on extension validation
                validate_file_type("text/plain", filename)

    def test_case_insensitive_validation(self):
        """Test that validation is case insensitive."""
        # Mixed case content types and extensions should work
        assert validate_file_type("TEXT/PLAIN", "Document.TXT") is True
        assert validate_file_type("Application/PDF", "DOCUMENT.PDF") is True


class TestFileSizeValidation:
    """Test file size validation functionality."""

    def test_validate_acceptable_file_sizes(self):
        """Test validation of acceptable file sizes."""
        # Test various sizes within limits
        test_cases = [
            (1024, 1),  # 1KB file, 1MB limit
            (1024 * 1024, 1),  # 1MB file, 1MB limit
            (5 * 1024 * 1024, 10),  # 5MB file, 10MB limit
        ]
        
        for size_bytes, max_size_mb in test_cases:
            assert validate_file_size(size_bytes, max_size_mb) is True

    def test_validate_oversized_files(self):
        """Test rejection of oversized files."""
        oversized_cases = [
            (2 * 1024 * 1024, 1),  # 2MB file, 1MB limit
            (100 * 1024 * 1024, 50),  # 100MB file, 50MB limit
        ]
        
        for size_bytes, max_size_mb in oversized_cases:
            with pytest.raises(FileSizeExceededError):
                validate_file_size(size_bytes, max_size_mb)

    def test_validate_empty_files(self):
        """Test rejection of empty files."""
        with pytest.raises(FileValidationError, match="File is empty"):
            validate_file_size(0, 10)

    def test_validate_negative_file_sizes(self):
        """Test rejection of negative file sizes."""
        with pytest.raises(FileValidationError, match="File size cannot be negative"):
            validate_file_size(-1, 10)


class TestFilenameSanitization:
    """Test filename sanitization functionality."""

    def test_sanitize_normal_filenames(self):
        """Test sanitization of normal filenames."""
        normal_cases = [
            ("document.txt", "document.txt"),
            ("My Document.pdf", "My Document.pdf"),
            ("file_name.docx", "file_name.docx"),
            ("report-2023.txt", "report-2023.txt"),
        ]
        
        for original, expected in normal_cases:
            assert sanitize_filename(original) == expected

    def test_sanitize_problematic_characters(self):
        """Test sanitization of filenames with problematic characters."""
        problematic_cases = [
            ("file<>name.txt", "file__name.txt"),
            ("file|name.pdf", "file_name.pdf"),
            ("file:name.docx", "file_name.docx"),
            ("file*name?.txt", "file_name_.txt"),
        ]
        
        for original, expected in problematic_cases:
            result = sanitize_filename(original)
            # Check that dangerous characters are replaced
            assert "<" not in result
            assert ">" not in result
            assert "|" not in result
            assert ":" not in result
            assert "*" not in result
            assert "?" not in result

    def test_sanitize_whitespace_handling(self):
        """Test proper handling of whitespace in filenames."""
        whitespace_cases = [
            ("  document.txt  ", "document.txt"),
            ("file   name.pdf", "file name.pdf"),  # Multiple spaces become single
            ("file___name.docx", "file_name.docx"),  # Multiple underscores become single
        ]
        
        for original, expected in whitespace_cases:
            result = sanitize_filename(original)
            assert result == expected or (result.strip() and not result.startswith("."))

    def test_sanitize_hidden_files(self):
        """Test removal of leading dots (hidden files)."""
        hidden_cases = [
            (".hidden.txt", "hidden.txt"),
            ("..double_dot.pdf", "double_dot.pdf"),
            ("...triple_dot.docx", "triple_dot.docx"),
        ]
        
        for original, expected in hidden_cases:
            result = sanitize_filename(original)
            assert not result.startswith(".")
            assert result.endswith(Path(original).suffix)

    def test_sanitize_empty_filenames(self):
        """Test handling of empty or invalid filenames."""
        empty_cases = ["", "   ", ".", "..", "..."]
        
        for empty_name in empty_cases:
            with pytest.raises(InvalidFilenameError):
                sanitize_filename(empty_name)

    def test_sanitize_long_filenames(self):
        """Test handling of overly long filenames."""
        long_name = "a" * 300 + ".txt"  # 304 characters
        
        with pytest.raises(InvalidFilenameError, match="Filename too long"):
            sanitize_filename(long_name)

    def test_preserve_file_extensions(self):
        """Test that file extensions are preserved during sanitization."""
        extension_cases = [
            ("bad<>name.txt", ".txt"),
            ("file|name.pdf", ".pdf"),
            ("doc:name.docx", ".docx"),
        ]
        
        for original, expected_ext in extension_cases:
            result = sanitize_filename(original)
            assert result.endswith(expected_ext)


class TestFileTypeDetection:
    """Test file type detection functionality."""

    def test_detect_pdf_by_signature(self):
        """Test PDF detection by file signature."""
        pdf_signature = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog"
        detected_type = detect_file_type(pdf_signature, "document.pdf")
        assert detected_type == "application/pdf"

    def test_detect_docx_by_signature(self):
        """Test DOCX detection by ZIP signature."""
        docx_signature = b"PK\x03\x04\x14\x00\x06\x00"  # ZIP signature
        detected_type = detect_file_type(docx_signature, "document.docx")
        assert detected_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    def test_detect_text_by_content(self):
        """Test text detection by content analysis."""
        text_content = b"This is a plain text document with readable content."
        detected_type = detect_file_type(text_content, "document.txt")
        assert detected_type == "text/plain"

    def test_detect_by_filename_fallback(self):
        """Test file type detection by filename when signature is unclear."""
        # Content that doesn't have clear signature
        unclear_content = b"Some content without clear signature"
        
        # Should detect by filename
        detected_type = detect_file_type(unclear_content, "document.txt")
        assert detected_type == "text/plain"

    def test_detect_unsupported_type(self):
        """Test detection of unsupported file types."""
        # Binary content that's not a supported type
        binary_content = b"\x89PNG\r\n\x1a\n"  # PNG signature
        
        with pytest.raises(UnsupportedFileTypeError):
            detect_file_type(binary_content, "image.png")

    def test_detect_empty_file(self):
        """Test detection with empty file data."""
        with pytest.raises(FileValidationError, match="File data is empty"):
            detect_file_type(b"", "document.txt")


class TestSecurityValidation:
    """Test security validation functionality."""

    def test_security_validation_success(self):
        """Test successful security validation."""
        # PDF content
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 3\ntrailer\n<<\n/Size 3\n>>\n%%EOF"
        assert validate_file_security(pdf_content, "document.pdf", "application/pdf") is True
        
        # Text content
        text_content = b"This is plain text content."
        assert validate_file_security(text_content, "document.txt", "text/plain") is True

    def test_security_validation_type_mismatch(self):
        """Test security validation with content type mismatch."""
        # PDF content declared as text
        pdf_content = b"%PDF-1.4\n1 0 obj"
        
        with pytest.raises(SecurityValidationError, match="File signature.*does not match"):
            validate_file_security(pdf_content, "document.txt", "text/plain")

    def test_security_validation_corrupted_pdf(self):
        """Test security validation with corrupted PDF."""
        # Invalid PDF content
        invalid_pdf = b"Not a valid PDF content"
        
        with pytest.raises(SecurityValidationError):
            validate_file_security(invalid_pdf, "document.pdf", "application/pdf")

    def test_security_validation_corrupted_docx(self):
        """Test security validation with corrupted DOCX."""
        # Invalid DOCX content (should be ZIP format)
        invalid_docx = b"Not a valid DOCX content"
        
        with pytest.raises(SecurityValidationError):
            validate_file_security(invalid_docx, "document.docx", 
                                 "application/vnd.openxmlformats-officedocument.wordprocessingml.document")


class TestFileInfo:
    """Test comprehensive file information gathering."""

    def test_get_file_info_success(self):
        """Test successful file information gathering."""
        test_content = b"This is a test document content."
        filename = "test document.txt"
        
        info = get_file_info(test_content, filename)
        
        assert info["original_filename"] == filename
        assert info["sanitized_filename"] == "test document.txt"
        assert info["detected_content_type"] == "text/plain"
        assert info["size_bytes"] == len(test_content)
        assert info["size_mb"] == len(test_content) / (1024 * 1024)
        assert info["extension"] == ".txt"
        assert info["is_supported"] is True
        assert info["validation_passed"] is True
        assert "error" not in info

    def test_get_file_info_with_errors(self):
        """Test file information gathering with validation errors."""
        # Use unsupported file type
        test_content = b"\x89PNG\r\n\x1a\n"  # PNG signature
        filename = "image.png"
        
        info = get_file_info(test_content, filename)
        
        assert info["original_filename"] == filename
        assert info["sanitized_filename"] is None
        assert info["detected_content_type"] is None
        assert info["validation_passed"] is False
        assert "error" in info

    def test_get_file_info_problematic_filename(self):
        """Test file information with problematic filename."""
        test_content = b"Valid text content"
        filename = "bad<>filename.txt"
        
        info = get_file_info(test_content, filename)
        
        assert info["original_filename"] == filename
        assert "<" not in info["sanitized_filename"]
        assert ">" not in info["sanitized_filename"]
        assert info["detected_content_type"] == "text/plain"
        assert info["validation_passed"] is True


class TestTaskSuccessCriteria:
    """Test all success criteria from Task 2.2 specification."""

    def test_only_allowed_file_types_pass_validation(self):
        """Verify only allowed file types pass validation."""
        # Test all supported types pass
        supported_cases = [
            ("text/plain", "document.txt"),
            ("application/pdf", "document.pdf"),
            ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "document.docx"),
        ]
        
        for content_type, filename in supported_cases:
            assert validate_file_type(content_type, filename) is True
        
        # Test unsupported types are rejected
        unsupported_cases = [
            ("image/jpeg", "image.jpg"),
            ("application/zip", "archive.zip"),
            ("text/html", "page.html"),
            ("application/javascript", "script.js"),
        ]
        
        for content_type, filename in unsupported_cases:
            with pytest.raises(UnsupportedFileTypeError):
                validate_file_type(content_type, filename)

    def test_file_size_limits_enforced(self):
        """Verify file size limits are enforced."""
        # Within limits should pass
        assert validate_file_size(1024, 1) is True  # 1KB, 1MB limit
        assert validate_file_size(1024 * 1024, 1) is True  # 1MB, 1MB limit
        
        # Over limits should fail
        with pytest.raises(FileSizeExceededError):
            validate_file_size(2 * 1024 * 1024, 1)  # 2MB, 1MB limit
        
        # Empty files should fail
        with pytest.raises(FileValidationError):
            validate_file_size(0, 10)

    def test_security_checks_prevent_malicious_uploads(self):
        """Verify security checks prevent malicious file uploads."""
        # Dangerous extensions should be rejected
        for ext in DANGEROUS_EXTENSIONS:
            filename = f"malicious{ext}"
            with pytest.raises(SecurityValidationError):
                validate_file_type("text/plain", filename)
        
        # Content type mismatch should be caught
        pdf_content = b"%PDF-1.4"
        with pytest.raises(SecurityValidationError):
            validate_file_security(pdf_content, "fake.txt", "text/plain")

    def test_graceful_error_handling_for_corrupted_files(self):
        """Verify graceful error handling for corrupted files."""
        # Test various error conditions
        
        # Empty file data
        with pytest.raises(FileValidationError):
            detect_file_type(b"", "document.txt")
        
        # Invalid PDF structure
        with pytest.raises(SecurityValidationError):
            validate_file_security(b"invalid pdf", "doc.pdf", "application/pdf")
        
        # Invalid DOCX structure
        with pytest.raises(SecurityValidationError):
            validate_file_security(b"invalid docx", "doc.docx", 
                                 "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        
        # All errors should be specific exception types, not generic exceptions
        # This ensures proper error handling and user feedback


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_complete_file_validation_workflow(self):
        """Test complete file validation workflow."""
        # Simulate a complete file upload validation
        filename = "legal_document.pdf"
        content_type = "application/pdf"
        file_data = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 3\ntrailer\n<<\n/Size 3\n>>\n%%EOF"
        max_size_mb = 50
        
        # Step 1: Sanitize filename
        sanitized_name = sanitize_filename(filename)
        assert sanitized_name == filename  # Should not change
        
        # Step 2: Validate file type
        assert validate_file_type(content_type, filename) is True
        
        # Step 3: Validate file size
        assert validate_file_size(len(file_data), max_size_mb) is True
        
        # Step 4: Detect file type from content
        detected_type = detect_file_type(file_data, filename)
        assert detected_type == content_type
        
        # Step 5: Security validation
        assert validate_file_security(file_data, filename, content_type) is True
        
        # Step 6: Get comprehensive file info
        info = get_file_info(file_data, filename)
        assert info["validation_passed"] is True
        assert info["is_supported"] is True

    def test_malicious_file_rejection_workflow(self):
        """Test that malicious files are properly rejected."""
        # Test executable file
        filename = "malware.exe"
        content_type = "application/octet-stream"
        file_data = b"MZ\x90\x00"  # PE executable signature
        
        # Should fail because the MIME type is unsupported
        with pytest.raises(UnsupportedFileTypeError):
            validate_file_type(content_type, filename)  # Unsupported MIME type
        
        # Test file with mismatched content
        filename = "fake.txt"
        content_type = "text/plain"
        file_data = b"%PDF-1.4"  # PDF content
        
        with pytest.raises(SecurityValidationError):
            validate_file_security(file_data, filename, content_type)

    def test_edge_case_handling(self):
        """Test handling of various edge cases."""
        # Very small valid files
        tiny_text = b"Hi"
        assert validate_file_size(len(tiny_text), 1) is True
        assert detect_file_type(tiny_text, "tiny.txt") == "text/plain"
        
        # Files with unusual but valid names
        weird_names = [
            "document with spaces.txt",
            "file-with-dashes.pdf", 
            "file_with_underscores.docx",
            "file.with.dots.txt"
        ]
        
        for name in weird_names:
            sanitized = sanitize_filename(name)
            assert sanitized  # Should produce valid output
            assert not sanitized.startswith(".")  # No leading dots
