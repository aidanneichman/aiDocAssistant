"""Unit tests for Task 2.2: Content Extraction.

Tests for text extraction from PDF, DOCX, and TXT files with proper
error handling and encoding detection.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.utils.content_extraction import (
    ContentExtractionError,
    CorruptedFileError,
    UnsupportedFormatError,
    extract_text_content,
    extract_text_content_sync,
    get_document_summary,
)


@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        yield Path(tmp.name)
    # Cleanup
    Path(tmp.name).unlink(missing_ok=True)


@pytest.fixture
def sample_text_content():
    """Sample text content for testing."""
    return "This is a sample document.\nIt contains multiple lines.\nWith various content."


@pytest.fixture
def sample_pdf_bytes():
    """Sample PDF bytes for testing."""
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Hello World!) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000010 00000 n\n0000000079 00000 n\n0000000173 00000 n\n0000000301 00000 n\n0000000380 00000 n\ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n492\n%%EOF"


class TestTextExtraction:
    """Test text extraction from TXT files."""

    @pytest.mark.asyncio
    async def test_extract_text_from_utf8_file(self, temp_file, sample_text_content):
        """Test extracting text from UTF-8 encoded file."""
        # Write UTF-8 content
        temp_file.write_text(sample_text_content, encoding='utf-8')
        
        # Extract text
        extracted_text = await extract_text_content(temp_file, "text/plain")
        
        assert extracted_text == sample_text_content

    @pytest.mark.asyncio
    async def test_extract_text_from_different_encodings(self, temp_file):
        """Test extracting text from files with different encodings."""
        test_text = "Hello, World! Special chars: àáâãäå"
        
        # Test different encodings
        encodings = ['utf-8', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            # Write with specific encoding
            temp_file.write_text(test_text, encoding=encoding)
            
            # Should be able to extract regardless of encoding
            extracted_text = await extract_text_content(temp_file, "text/plain")
            
            # Content should be readable (may have some encoding differences)
            assert len(extracted_text) > 0
            assert "Hello" in extracted_text

    @pytest.mark.asyncio
    async def test_extract_text_with_bom(self, temp_file):
        """Test extracting text from file with BOM (Byte Order Mark)."""
        test_text = "Content with BOM"
        
        # Write with UTF-8 BOM
        with open(temp_file, 'wb') as f:
            f.write('\ufeff'.encode('utf-8'))  # BOM
            f.write(test_text.encode('utf-8'))
        
        extracted_text = await extract_text_content(temp_file, "text/plain")
        
        # BOM should be handled correctly
        assert test_text in extracted_text

    @pytest.mark.asyncio
    async def test_extract_text_from_empty_file(self, temp_file):
        """Test extracting text from empty file."""
        # Create empty file
        temp_file.write_text("")
        
        extracted_text = await extract_text_content(temp_file, "text/plain")
        
        assert extracted_text == ""

    @pytest.mark.asyncio
    async def test_extract_text_with_binary_content(self, temp_file):
        """Test extracting text from file with binary content mixed in."""
        # Write text with some binary bytes
        with open(temp_file, 'wb') as f:
            f.write(b"Text content\x00\x01\x02 More text")
        
        extracted_text = await extract_text_content(temp_file, "text/plain")
        
        # Should handle binary content gracefully
        assert "Text content" in extracted_text
        assert "More text" in extracted_text


class TestPDFExtraction:
    """Test text extraction from PDF files."""

    @pytest.mark.asyncio
    @patch('backend.app.utils.content_extraction.PdfReader')
    async def test_extract_text_from_pdf_success(self, mock_pdf_reader, temp_file):
        """Test successful PDF text extraction."""
        # Mock PDF reader
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "PDF content text"
        
        mock_reader_instance = MagicMock()
        mock_reader_instance.is_encrypted = False
        mock_reader_instance.pages = [mock_page]
        
        mock_pdf_reader.return_value = mock_reader_instance
        
        # Write dummy PDF data
        temp_file.write_bytes(b"%PDF-1.4 dummy content")
        
        extracted_text = await extract_text_content(temp_file, "application/pdf")
        
        assert extracted_text == "PDF content text"
        mock_pdf_reader.assert_called_once()
        mock_page.extract_text.assert_called_once()

    @pytest.mark.asyncio
    @patch('backend.app.utils.content_extraction.PdfReader')
    async def test_extract_text_from_encrypted_pdf(self, mock_pdf_reader, temp_file):
        """Test extracting text from encrypted PDF."""
        # Mock encrypted PDF
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Decrypted PDF content"
        
        mock_reader_instance = MagicMock()
        mock_reader_instance.is_encrypted = True
        mock_reader_instance.pages = [mock_page]
        mock_reader_instance.decrypt.return_value = True
        
        mock_pdf_reader.return_value = mock_reader_instance
        
        temp_file.write_bytes(b"%PDF-1.4 encrypted content")
        
        extracted_text = await extract_text_content(temp_file, "application/pdf")
        
        assert extracted_text == "Decrypted PDF content"
        mock_reader_instance.decrypt.assert_called_once_with("")

    @pytest.mark.asyncio
    @patch('backend.app.utils.content_extraction.PdfReader')
    async def test_extract_text_from_multi_page_pdf(self, mock_pdf_reader, temp_file):
        """Test extracting text from multi-page PDF."""
        # Mock multi-page PDF
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page 1 content"
        
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Page 2 content"
        
        mock_reader_instance = MagicMock()
        mock_reader_instance.is_encrypted = False
        mock_reader_instance.pages = [mock_page1, mock_page2]
        
        mock_pdf_reader.return_value = mock_reader_instance
        
        temp_file.write_bytes(b"%PDF-1.4 multi-page content")
        
        extracted_text = await extract_text_content(temp_file, "application/pdf")
        
        assert "Page 1 content" in extracted_text
        assert "Page 2 content" in extracted_text
        assert extracted_text == "Page 1 content\n\nPage 2 content"

    @pytest.mark.asyncio
    @patch('backend.app.utils.content_extraction.PdfReader')
    async def test_extract_text_from_corrupted_pdf(self, mock_pdf_reader, temp_file):
        """Test handling of corrupted PDF files."""
        # Mock PDF reader to raise exception
        mock_pdf_reader.side_effect = Exception("Corrupted PDF")
        
        temp_file.write_bytes(b"corrupted pdf content")
        
        with pytest.raises(CorruptedFileError, match="Cannot read PDF file"):
            await extract_text_content(temp_file, "application/pdf")

    @pytest.mark.asyncio
    @patch('backend.app.utils.content_extraction.PdfReader')
    async def test_extract_text_from_empty_pdf(self, mock_pdf_reader, temp_file):
        """Test extracting text from PDF with no pages."""
        # Mock empty PDF
        mock_reader_instance = MagicMock()
        mock_reader_instance.is_encrypted = False
        mock_reader_instance.pages = []
        
        mock_pdf_reader.return_value = mock_reader_instance
        
        temp_file.write_bytes(b"%PDF-1.4 empty")
        
        with pytest.raises(CorruptedFileError, match="PDF file contains no pages"):
            await extract_text_content(temp_file, "application/pdf")


class TestDOCXExtraction:
    """Test text extraction from DOCX files."""

    @pytest.mark.asyncio
    @patch('backend.app.utils.content_extraction.DocxDocument')
    async def test_extract_text_from_docx_success(self, mock_docx_doc, temp_file):
        """Test successful DOCX text extraction."""
        # Mock DOCX document
        mock_paragraph1 = MagicMock()
        mock_paragraph1.text = "First paragraph"
        
        mock_paragraph2 = MagicMock()
        mock_paragraph2.text = "Second paragraph"
        
        mock_doc_instance = MagicMock()
        mock_doc_instance.paragraphs = [mock_paragraph1, mock_paragraph2]
        mock_doc_instance.tables = []
        
        mock_docx_doc.return_value = mock_doc_instance
        
        # Write dummy DOCX data (ZIP signature)
        temp_file.write_bytes(b"PK\x03\x04 dummy docx content")
        
        extracted_text = await extract_text_content(temp_file, 
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        
        assert "First paragraph" in extracted_text
        assert "Second paragraph" in extracted_text

    @pytest.mark.asyncio
    @patch('backend.app.utils.content_extraction.DocxDocument')
    async def test_extract_text_from_docx_with_tables(self, mock_docx_doc, temp_file):
        """Test extracting text from DOCX with tables."""
        # Mock paragraph
        mock_paragraph = MagicMock()
        mock_paragraph.text = "Document text"
        
        # Mock table
        mock_cell1 = MagicMock()
        mock_cell1.text = "Cell 1"
        mock_cell2 = MagicMock()
        mock_cell2.text = "Cell 2"
        
        mock_row = MagicMock()
        mock_row.cells = [mock_cell1, mock_cell2]
        
        mock_table = MagicMock()
        mock_table.rows = [mock_row]
        
        mock_doc_instance = MagicMock()
        mock_doc_instance.paragraphs = [mock_paragraph]
        mock_doc_instance.tables = [mock_table]
        
        mock_docx_doc.return_value = mock_doc_instance
        
        temp_file.write_bytes(b"PK\x03\x04 docx with table")
        
        extracted_text = await extract_text_content(temp_file,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        
        assert "Document text" in extracted_text
        assert "Cell 1 | Cell 2" in extracted_text

    @pytest.mark.asyncio
    @patch('backend.app.utils.content_extraction.DocxDocument')
    async def test_extract_text_from_corrupted_docx(self, mock_docx_doc, temp_file):
        """Test handling of corrupted DOCX files."""
        # Mock DOCX to raise exception
        mock_docx_doc.side_effect = Exception("Corrupted DOCX")
        
        temp_file.write_bytes(b"corrupted docx content")
        
        with pytest.raises(CorruptedFileError, match="Cannot read DOCX file"):
            await extract_text_content(temp_file,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    @pytest.mark.asyncio
    @patch('backend.app.utils.content_extraction.DocxDocument')
    async def test_extract_text_from_empty_docx(self, mock_docx_doc, temp_file):
        """Test extracting text from DOCX with no content."""
        # Mock empty DOCX
        mock_doc_instance = MagicMock()
        mock_doc_instance.paragraphs = []
        mock_doc_instance.tables = []
        
        mock_docx_doc.return_value = mock_doc_instance
        
        temp_file.write_bytes(b"PK\x03\x04 empty docx")
        
        extracted_text = await extract_text_content(temp_file,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        
        assert extracted_text == ""


class TestUnsupportedFormats:
    """Test handling of unsupported file formats."""

    @pytest.mark.asyncio
    async def test_extract_text_from_unsupported_format(self, temp_file):
        """Test extraction from unsupported file format."""
        temp_file.write_bytes(b"some content")
        
        with pytest.raises(UnsupportedFormatError, match="Text extraction not supported"):
            await extract_text_content(temp_file, "image/jpeg")

    @pytest.mark.asyncio
    async def test_extract_text_with_empty_content_type(self, temp_file):
        """Test extraction with empty content type."""
        temp_file.write_text("content")
        
        with pytest.raises(UnsupportedFormatError):
            await extract_text_content(temp_file, "")


class TestSynchronousExtraction:
    """Test synchronous text extraction functions."""

    def test_extract_text_content_sync_txt(self, temp_file, sample_text_content):
        """Test synchronous text extraction from TXT file."""
        temp_file.write_text(sample_text_content, encoding='utf-8')
        
        extracted_text = extract_text_content_sync(temp_file, "text/plain")
        
        assert extracted_text == sample_text_content

    @patch('backend.app.utils.content_extraction.PdfReader')
    def test_extract_text_content_sync_pdf(self, mock_pdf_reader, temp_file):
        """Test synchronous text extraction from PDF file."""
        # Mock PDF reader
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "PDF content"
        
        mock_reader_instance = MagicMock()
        mock_reader_instance.is_encrypted = False
        mock_reader_instance.pages = [mock_page]
        
        mock_pdf_reader.return_value = mock_reader_instance
        
        temp_file.write_bytes(b"%PDF-1.4 content")
        
        extracted_text = extract_text_content_sync(temp_file, "application/pdf")
        
        assert extracted_text == "PDF content"

    @patch('backend.app.utils.content_extraction.DocxDocument')
    def test_extract_text_content_sync_docx(self, mock_docx_doc, temp_file):
        """Test synchronous text extraction from DOCX file."""
        # Mock DOCX document
        mock_paragraph = MagicMock()
        mock_paragraph.text = "DOCX content"
        
        mock_doc_instance = MagicMock()
        mock_doc_instance.paragraphs = [mock_paragraph]
        mock_doc_instance.tables = []
        
        mock_docx_doc.return_value = mock_doc_instance
        
        temp_file.write_bytes(b"PK\x03\x04 docx content")
        
        extracted_text = extract_text_content_sync(temp_file,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        
        assert extracted_text == "DOCX content"


class TestDocumentSummary:
    """Test document summary functionality."""

    @pytest.mark.asyncio
    async def test_get_document_summary_success(self, temp_file, sample_text_content):
        """Test successful document summary generation."""
        temp_file.write_text(sample_text_content)
        
        summary = await get_document_summary(temp_file, "text/plain")
        
        assert summary["content_type"] == "text/plain"
        assert summary["extraction_successful"] is True
        assert summary["text_length"] == len(sample_text_content)
        assert summary["word_count"] > 0
        assert summary["line_count"] > 0
        assert summary["has_content"] is True
        assert sample_text_content[:50] in summary["preview"]
        assert summary["error"] is None

    @pytest.mark.asyncio
    async def test_get_document_summary_long_content(self, temp_file):
        """Test document summary with long content (preview truncation)."""
        long_content = "A" * 1000  # 1000 characters
        temp_file.write_text(long_content)
        
        summary = await get_document_summary(temp_file, "text/plain")
        
        assert summary["text_length"] == 1000
        assert len(summary["preview"]) <= 503  # 500 chars + "..."
        assert summary["preview"].endswith("...")

    @pytest.mark.asyncio
    async def test_get_document_summary_empty_content(self, temp_file):
        """Test document summary with empty content."""
        temp_file.write_text("")
        
        summary = await get_document_summary(temp_file, "text/plain")
        
        assert summary["extraction_successful"] is True
        assert summary["text_length"] == 0
        assert summary["word_count"] == 0
        assert summary["has_content"] is False
        assert summary["preview"] == ""

    @pytest.mark.asyncio
    async def test_get_document_summary_extraction_error(self, temp_file):
        """Test document summary when extraction fails."""
        temp_file.write_bytes(b"content")
        
        # Use unsupported format to trigger error
        summary = await get_document_summary(temp_file, "image/jpeg")
        
        assert summary["extraction_successful"] is False
        assert summary["text_length"] == 0
        assert summary["has_content"] is False
        assert summary["error"] is not None


class TestTaskSuccessCriteria:
    """Test all success criteria from Task 2.2 specification."""

    @pytest.mark.asyncio
    async def test_text_extraction_works_for_all_supported_formats(self, temp_file):
        """Verify text extraction works for all supported formats."""
        # Test TXT
        temp_file.write_text("Text content")
        txt_result = await extract_text_content(temp_file, "text/plain")
        assert txt_result == "Text content"
        
        # Test PDF (mocked)
        with patch('backend.app.utils.content_extraction.PdfReader') as mock_pdf:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "PDF content"
            mock_reader = MagicMock()
            mock_reader.is_encrypted = False
            mock_reader.pages = [mock_page]
            mock_pdf.return_value = mock_reader
            
            temp_file.write_bytes(b"%PDF-1.4")
            pdf_result = await extract_text_content(temp_file, "application/pdf")
            assert pdf_result == "PDF content"
        
        # Test DOCX (mocked)
        with patch('backend.app.utils.content_extraction.DocxDocument') as mock_docx:
            mock_para = MagicMock()
            mock_para.text = "DOCX content"
            mock_doc = MagicMock()
            mock_doc.paragraphs = [mock_para]
            mock_doc.tables = []
            mock_docx.return_value = mock_doc
            
            temp_file.write_bytes(b"PK\x03\x04")
            docx_result = await extract_text_content(temp_file,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            assert docx_result == "DOCX content"

    @pytest.mark.asyncio
    async def test_graceful_error_handling_for_corrupted_files(self, temp_file):
        """Verify graceful error handling for corrupted files."""
        # Test corrupted PDF
        with patch('backend.app.utils.content_extraction.PdfReader') as mock_pdf:
            mock_pdf.side_effect = Exception("Corrupted")
            temp_file.write_bytes(b"bad pdf")
            
            with pytest.raises(CorruptedFileError):
                await extract_text_content(temp_file, "application/pdf")
        
        # Test corrupted DOCX
        with patch('backend.app.utils.content_extraction.DocxDocument') as mock_docx:
            mock_docx.side_effect = Exception("Corrupted")
            temp_file.write_bytes(b"bad docx")
            
            with pytest.raises(CorruptedFileError):
                await extract_text_content(temp_file,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        
        # Test unsupported format
        temp_file.write_bytes(b"content")
        with pytest.raises(UnsupportedFormatError):
            await extract_text_content(temp_file, "unsupported/format")

    @pytest.mark.asyncio
    async def test_encoding_detection_and_handling(self, temp_file):
        """Verify encoding detection and handling for text files."""
        test_cases = [
            ("utf-8", "Hello, World! 🌍"),
            ("latin-1", "Hello, café"),
            ("cp1252", "Hello, résumé"),
        ]
        
        for encoding, text in test_cases:
            # Write with specific encoding
            with open(temp_file, 'w', encoding=encoding) as f:
                f.write(text)
            
            # Should extract successfully regardless of encoding
            extracted = await extract_text_content(temp_file, "text/plain")
            
            # Content should be readable (exact match depends on encoding handling)
            assert len(extracted) > 0
            assert "Hello" in extracted

    def test_both_sync_and_async_interfaces_available(self, temp_file):
        """Verify both synchronous and asynchronous interfaces work."""
        content = "Test content for both interfaces"
        temp_file.write_text(content)
        
        # Test async interface
        import asyncio
        async_result = asyncio.run(extract_text_content(temp_file, "text/plain"))
        assert async_result == content
        
        # Test sync interface
        sync_result = extract_text_content_sync(temp_file, "text/plain")
        assert sync_result == content
        
        # Results should be identical
        assert async_result == sync_result
