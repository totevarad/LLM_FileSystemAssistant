"""
Unit tests for fs_tools.py.

Phase 1 & Phase 2: read_file (TXT, PDF, DOCX, corrupt files, error contract, metadata accuracy).
"""

from pathlib import Path
from datetime import datetime
import pytest

from fs_tools import read_file


FIXTURES_DIR = Path(__file__).parent / "fixtures"
EXPECTED_TOP_LEVEL_KEYS = {
    "success",
    "filepath",
    "filename",
    "extension",
    "content",
    "metadata",
    "error",
}
EXPECTED_METADATA_KEYS = {
    "size_bytes",
    "num_pages",
    "num_words",
    "num_characters",
    "modified_time",
    "read_time",
}


def test_read_file_txt_success():
    """Verify successful reading of a valid UTF-8 .txt resume fixture."""
    sample_path = str(FIXTURES_DIR / "sample.txt")
    result = read_file(sample_path)

    assert set(result.keys()) == EXPECTED_TOP_LEVEL_KEYS
    assert result["success"] is True
    assert result["filepath"] == sample_path
    assert result["filename"] == "sample.txt"
    assert result["extension"] == ".txt"
    assert result["error"] is None

    assert isinstance(result["content"], str)
    assert "John Doe" in result["content"]
    assert "Python" in result["content"]

    meta = result["metadata"]
    assert set(meta.keys()) == EXPECTED_METADATA_KEYS
    assert meta["size_bytes"] > 0
    assert meta["num_pages"] is None
    assert meta["num_words"] > 50
    assert meta["num_characters"] > 200
    assert meta["num_characters"] == len(result["content"])

    assert datetime.fromisoformat(meta["modified_time"]) is not None
    assert datetime.fromisoformat(meta["read_time"]) is not None


def test_read_file_pdf_success():
    """Verify successful reading of a valid .pdf resume fixture."""
    pdf_path = str(FIXTURES_DIR / "sample.pdf")
    result = read_file(pdf_path)

    assert set(result.keys()) == EXPECTED_TOP_LEVEL_KEYS
    assert result["success"] is True
    assert result["filepath"] == pdf_path
    assert result["filename"] == "sample.pdf"
    assert result["extension"] == ".pdf"
    assert result["error"] is None

    assert isinstance(result["content"], str)
    assert "Alex Johnson" in result["content"]
    assert "Python" in result["content"]

    meta = result["metadata"]
    assert set(meta.keys()) == EXPECTED_METADATA_KEYS
    assert meta["size_bytes"] > 0
    assert meta["num_pages"] == 1
    assert meta["num_words"] > 5
    assert meta["num_characters"] == len(result["content"])

    assert datetime.fromisoformat(meta["modified_time"]) is not None
    assert datetime.fromisoformat(meta["read_time"]) is not None


def test_read_file_docx_success():
    """Verify successful reading of a valid .docx resume fixture."""
    docx_path = str(FIXTURES_DIR / "sample.docx")
    result = read_file(docx_path)

    assert set(result.keys()) == EXPECTED_TOP_LEVEL_KEYS
    assert result["success"] is True
    assert result["filepath"] == docx_path
    assert result["filename"] == "sample.docx"
    assert result["extension"] == ".docx"
    assert result["error"] is None

    assert isinstance(result["content"], str)
    assert "Jane Smith" in result["content"]
    assert "Python" in result["content"]

    meta = result["metadata"]
    assert set(meta.keys()) == EXPECTED_METADATA_KEYS
    assert meta["size_bytes"] > 0
    assert meta["num_pages"] is None
    assert meta["num_words"] > 10
    assert meta["num_characters"] == len(result["content"])

    assert datetime.fromisoformat(meta["modified_time"]) is not None
    assert datetime.fromisoformat(meta["read_time"]) is not None


def test_read_file_corrupt_pdf():
    """Verify that a malformed/corrupt PDF returns success: False without raising."""
    corrupt_pdf_path = str(FIXTURES_DIR / "corrupt.pdf")
    result = read_file(corrupt_pdf_path)

    assert set(result.keys()) == EXPECTED_TOP_LEVEL_KEYS
    assert result["success"] is False
    assert result["filepath"] == corrupt_pdf_path
    assert result["filename"] == "corrupt.pdf"
    assert result["extension"] == ".pdf"
    assert result["content"] is None
    assert result["metadata"] is None
    assert result["error"] is not None
    assert "error" in result["error"].lower() or "pdf" in result["error"].lower()


def test_read_file_corrupt_docx():
    """Verify that a malformed/corrupt DOCX returns success: False without raising."""
    corrupt_docx_path = str(FIXTURES_DIR / "corrupt.docx")
    result = read_file(corrupt_docx_path)

    assert set(result.keys()) == EXPECTED_TOP_LEVEL_KEYS
    assert result["success"] is False
    assert result["filepath"] == corrupt_docx_path
    assert result["filename"] == "corrupt.docx"
    assert result["extension"] == ".docx"
    assert result["content"] is None
    assert result["metadata"] is None
    assert result["error"] is not None


def test_read_file_contract_uniformity():
    """Verify that all supported formats return identical dictionary schema shapes."""
    paths = [
        str(FIXTURES_DIR / "sample.txt"),
        str(FIXTURES_DIR / "sample.pdf"),
        str(FIXTURES_DIR / "sample.docx"),
    ]

    for p in paths:
        res = read_file(p)
        assert set(res.keys()) == EXPECTED_TOP_LEVEL_KEYS
        assert res["success"] is True
        assert res["metadata"] is not None
        assert set(res["metadata"].keys()) == EXPECTED_METADATA_KEYS


def test_read_file_empty_file():
    """Verify reading an empty 0-byte .txt file."""
    empty_path = str(FIXTURES_DIR / "empty.txt")
    result = read_file(empty_path)

    assert set(result.keys()) == EXPECTED_TOP_LEVEL_KEYS
    assert result["success"] is True
    assert result["filepath"] == empty_path
    assert result["filename"] == "empty.txt"
    assert result["extension"] == ".txt"
    assert result["content"] == ""
    assert result["error"] is None

    meta = result["metadata"]
    assert meta["size_bytes"] == 0
    assert meta["num_words"] == 0
    assert meta["num_characters"] == 0
    assert meta["num_pages"] is None


def test_read_file_missing_file():
    """Verify non-existent file path returns structured failure without raising."""
    missing_path = str(FIXTURES_DIR / "non_existent_file_98765.txt")
    result = read_file(missing_path)

    assert set(result.keys()) == EXPECTED_TOP_LEVEL_KEYS
    assert result["success"] is False
    assert result["filepath"] == missing_path
    assert result["filename"] == "non_existent_file_98765.txt"
    assert result["extension"] == ".txt"
    assert result["content"] is None
    assert result["metadata"] is None
    assert result["error"] is not None
    assert "File not found" in result["error"]


def test_read_file_unsupported_extension(tmp_path):
    """Verify unsupported file extension on existing file returns structured failure without raising."""
    unsupported_file = tmp_path / "document.xyz"
    unsupported_file.write_text("Hello world", encoding="utf-8")
    result = read_file(str(unsupported_file))

    assert set(result.keys()) == EXPECTED_TOP_LEVEL_KEYS
    assert result["success"] is False
    assert result["extension"] == ".xyz"
    assert result["content"] is None
    assert result["metadata"] is None
    assert "Unsupported file extension" in result["error"]


def test_read_file_non_utf8_fallback():
    """Verify latin-1 encoded file decodes gracefully without crashing."""
    latin1_path = str(FIXTURES_DIR / "latin1.txt")
    result = read_file(latin1_path)

    assert set(result.keys()) == EXPECTED_TOP_LEVEL_KEYS
    assert result["success"] is True
    assert result["content"] is not None
    assert "René Müller" in result["content"] or "Müller" in result["content"]
    assert result["metadata"]["num_words"] > 0


def test_read_file_directory_as_filepath():
    """Verify passing a directory path returns structured failure instead of raising."""
    dir_path = str(FIXTURES_DIR)
    result = read_file(dir_path)

    assert set(result.keys()) == EXPECTED_TOP_LEVEL_KEYS
    assert result["success"] is False
    assert result["content"] is None
    assert "directory" in result["error"].lower()


@pytest.mark.parametrize("invalid_input", ["", None, 12345, [], {}])
def test_read_file_invalid_inputs(invalid_input):
    """Verify non-string or empty filepath arguments return structured error without crashing."""
    result = read_file(invalid_input)

    assert set(result.keys()) == EXPECTED_TOP_LEVEL_KEYS
    assert result["success"] is False
    assert result["content"] is None
    assert result["metadata"] is None
    assert "Invalid filepath" in result["error"]


def test_read_file_never_raises():
    """Verify that read_file never raises an unhandled exception under various bad inputs."""
    bad_inputs = [
        "fixtures/does_not_exist.txt",
        "",
        "/invalid/root/path/to/nowhere.pdf",
        "CON",  # Windows reserved device name
        str(FIXTURES_DIR / "corrupt.pdf"),
        str(FIXTURES_DIR / "corrupt.docx"),
    ]
    for inp in bad_inputs:
        try:
            res = read_file(inp)
            assert isinstance(res, dict)
            assert "success" in res
        except Exception as exc:
            pytest.fail(f"read_file({inp!r}) raised unhandled exception: {exc}")
