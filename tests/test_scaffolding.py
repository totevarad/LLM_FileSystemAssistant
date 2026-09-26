"""
Phase 0 Scaffolding Tests.

Validates project layout, dependency imports, directory structure,
and test fixture presence and integrity.
"""

from pathlib import Path
import os
import pytest


def test_core_module_imports():
    """Verify core project modules can be imported without error."""
    import fs_tools
    import llm_file_assistant

    assert hasattr(fs_tools, "read_file")
    assert hasattr(fs_tools, "list_files")
    assert hasattr(fs_tools, "write_file")
    assert hasattr(fs_tools, "search_in_file")
    assert hasattr(llm_file_assistant, "run_query")


def test_third_party_dependency_imports():
    """Verify required third-party libraries are installed and importable."""
    import pypdf
    import docx
    import openai
    import anthropic
    import dotenv

    assert pypdf is not None
    assert docx is not None
    assert openai is not None
    assert anthropic is not None
    assert dotenv is not None


def test_directory_structure():
    """Verify that expected project directories exist."""
    base_dir = Path(__file__).parent.parent
    assert (base_dir / "resumes").is_dir(), "resumes/ directory missing"
    assert (base_dir / "output").is_dir(), "output/ directory missing"
    assert (base_dir / "logs").is_dir(), "logs/ directory missing"
    assert (base_dir / "tests" / "fixtures").is_dir(), "tests/fixtures/ directory missing"


def test_fixtures_present_and_valid():
    """Verify all required test fixtures are present with correct baseline content."""
    fixtures_dir = Path(__file__).parent / "fixtures"

    # 1. empty.txt
    empty_txt = fixtures_dir / "empty.txt"
    assert empty_txt.is_file(), "empty.txt fixture missing"
    assert empty_txt.stat().st_size == 0, "empty.txt must be 0 bytes"

    # 2. sample.txt
    sample_txt = fixtures_dir / "sample.txt"
    assert sample_txt.is_file(), "sample.txt fixture missing"
    assert sample_txt.stat().st_size > 0, "sample.txt must not be empty"
    content = sample_txt.read_text(encoding="utf-8")
    assert "John Doe" in content
    assert "Python" in content

    # 3. sample.pdf
    sample_pdf = fixtures_dir / "sample.pdf"
    assert sample_pdf.is_file(), "sample.pdf fixture missing"
    import pypdf
    reader = pypdf.PdfReader(str(sample_pdf))
    assert len(reader.pages) >= 1
    assert "Alex Johnson" in reader.pages[0].extract_text()

    # 4. sample.docx
    sample_docx = fixtures_dir / "sample.docx"
    assert sample_docx.is_file(), "sample.docx fixture missing"
    import docx
    doc = docx.Document(str(sample_docx))
    full_text = " ".join([p.text for p in doc.paragraphs])
    assert "Jane Smith" in full_text

    # 5. corrupt.pdf
    corrupt_pdf = fixtures_dir / "corrupt.pdf"
    assert corrupt_pdf.is_file(), "corrupt.pdf fixture missing"
    assert corrupt_pdf.stat().st_size > 0
    with pytest.raises(Exception):
        bad_reader = pypdf.PdfReader(str(corrupt_pdf))
        # Accessing pages or trailer should raise an exception on malformed PDF
        _ = bad_reader.pages[0]
