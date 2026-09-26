"""
Unit tests for fs_tools.py.

Phase 1 & Phase 2: read_file (TXT, PDF, DOCX, corrupt files, error contract, metadata accuracy).
"""

from pathlib import Path
from datetime import datetime
import pytest

from fs_tools import (
    read_file,
    list_files,
    write_file,
    search_in_file,
    get_base_dir,
    set_base_dir,
    reset_base_dir,
)


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
        "in*valid?name",
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


# ============================================================================
# Phase 3: list_files tests
# ============================================================================

EXPECTED_LIST_FILES_KEYS = {
    "name",
    "filepath",
    "extension",
    "size_bytes",
    "modified_time",
}


def test_list_files_all():
    """Verify listing all files in a directory returns structured entries with expected keys."""
    res = list_files("resumes")
    assert isinstance(res, list)
    assert len(res) >= 3  # sample.docx, sample.pdf, sample.txt

    for entry in res:
        assert set(entry.keys()) == EXPECTED_LIST_FILES_KEYS
        assert entry["name"] in {"sample.docx", "sample.pdf", "sample.txt"}
        assert entry["size_bytes"] > 0
        assert entry["extension"].startswith(".")
        assert datetime.fromisoformat(entry["modified_time"]) is not None


def test_list_files_filtered_by_extension():
    """Verify filtering files by extension returns only matching files."""
    res_pdf = list_files("resumes", extension=".pdf")
    assert len(res_pdf) >= 1
    assert all(item["extension"] == ".pdf" for item in res_pdf)
    assert any(item["name"] == "sample.pdf" for item in res_pdf)

    res_txt = list_files("resumes", extension=".txt")
    assert len(res_txt) >= 1
    assert all(item["extension"] == ".txt" for item in res_txt)
    assert any(item["name"] == "sample.txt" for item in res_txt)


def test_list_files_case_insensitive_and_no_dot():
    """Verify extension filtering works with or without leading dot and regardless of case."""
    dot_lower = list_files("resumes", extension=".pdf")
    no_dot_lower = list_files("resumes", extension="pdf")
    dot_upper = list_files("resumes", extension=".PDF")
    no_dot_upper = list_files("resumes", extension="PDF")

    assert dot_lower == no_dot_lower == dot_upper == no_dot_upper


def test_list_files_empty_directory(tmp_path):
    """Verify listing an empty directory returns an empty list."""
    empty_dir = tmp_path / "empty_dir"
    empty_dir.mkdir()
    res = list_files(str(empty_dir))
    assert res == []


def test_list_files_missing_directory():
    """Verify listing a non-existent directory returns an empty list without raising."""
    res = list_files("path/to/definitely/missing/dir_12345")
    assert res == []


def test_list_files_ignores_subdirectories(tmp_path):
    """Verify subdirectories and nested files are excluded from the top-level list."""
    root_dir = tmp_path / "scan_test"
    root_dir.mkdir()

    # Create root files
    (root_dir / "file_a.txt").write_text("aaa")
    (root_dir / "file_b.pdf").write_text("bbb")

    # Create nested subdirectory with an internal file
    nested_dir = root_dir / "subdir"
    nested_dir.mkdir()
    (nested_dir / "nested_file.txt").write_text("ccc")

    res = list_files(str(root_dir))
    names = [item["name"] for item in res]

    assert "file_a.txt" in names
    assert "file_b.pdf" in names
    assert "subdir" not in names
    assert "nested_file.txt" not in names
    assert len(res) == 2


def test_list_files_deterministic_sorting(tmp_path):
    """Verify that listed files are always sorted alphabetically by filename."""
    test_dir = tmp_path / "sort_test"
    test_dir.mkdir()

    # Create files in arbitrary order
    (test_dir / "zebra.txt").write_text("z")
    (test_dir / "apple.txt").write_text("a")
    (test_dir / "banana.txt").write_text("b")
    (test_dir / "mango.txt").write_text("m")

    res = list_files(str(test_dir))
    names = [item["name"] for item in res]

    assert names == ["apple.txt", "banana.txt", "mango.txt", "zebra.txt"]


def test_list_files_file_passed_as_directory(tmp_path):
    """Verify passing a file path instead of a directory returns an empty list without raising."""
    some_file = tmp_path / "regular_file.txt"
    some_file.write_text("content")

    res = list_files(str(some_file))
    assert res == []


@pytest.mark.parametrize("invalid_input", ["", None, 12345, [], {}])
def test_list_files_invalid_inputs(invalid_input):
    """Verify non-string or empty directory arguments return empty list without raising."""
    res = list_files(invalid_input)
    assert res == []


def test_list_files_never_raises():
    """Verify that list_files never raises an unhandled exception for pathological inputs."""
    bad_inputs = [
        "",
        None,
        "in*valid?name",
        "invalid://path??",
        "C:/non_existent_drive_z:/folder",
    ]
    for inp in bad_inputs:
        try:
            res = list_files(inp)
            assert isinstance(res, list)
        except Exception as exc:
            pytest.fail(f"list_files({inp!r}) raised unhandled exception: {exc}")


# ============================================================================
# Phase 4: write_file tests
# ============================================================================

EXPECTED_WRITE_KEYS = {"success", "filepath", "bytes_written", "error"}


def test_write_file_creates_new_dirs(tmp_path):
    """Verify write_file automatically creates missing parent directories and writes content."""
    nested_path = tmp_path / "deep" / "nested" / "directory" / "summary.txt"
    target_str = str(nested_path)
    content = "Summary of candidates:\n1. John Doe\n2. Jane Smith"

    res = write_file(target_str, content)

    assert set(res.keys()) == EXPECTED_WRITE_KEYS
    assert res["success"] is True
    assert res["filepath"] == target_str
    assert res["bytes_written"] == len(content.encode("utf-8"))
    assert res["error"] is None

    assert nested_path.is_file()
    assert nested_path.read_text(encoding="utf-8") == content


def test_write_file_overwrites_existing(tmp_path):
    """Verify write_file overwrites existing file content by default."""
    target_file = tmp_path / "existing.txt"
    target_str = str(target_file)

    first_write = write_file(target_str, "Initial version")
    assert first_write["success"] is True
    assert target_file.read_text(encoding="utf-8") == "Initial version"

    second_write = write_file(target_str, "Updated version with more details")
    assert second_write["success"] is True
    assert second_write["bytes_written"] == len("Updated version with more details".encode("utf-8"))
    assert target_file.read_text(encoding="utf-8") == "Updated version with more details"


def test_write_file_empty_content(tmp_path):
    """Verify writing empty string creates a 0-byte file successfully."""
    target_file = tmp_path / "empty_output.txt"
    target_str = str(target_file)

    res = write_file(target_str, "")

    assert set(res.keys()) == EXPECTED_WRITE_KEYS
    assert res["success"] is True
    assert res["bytes_written"] == 0
    assert res["error"] is None
    assert target_file.is_file()
    assert target_file.stat().st_size == 0


def test_write_file_utf8_special_characters(tmp_path):
    """Verify writing multilingual text and Unicode characters correctly encodes to UTF-8."""
    target_file = tmp_path / "unicode.txt"
    content = "Candidate: Renée Müller 🚀\nSkills: AI/ML, Python, C++\nNotes: Zürich based."

    res = write_file(str(target_file), content)

    assert res["success"] is True
    assert res["bytes_written"] == len(content.encode("utf-8"))
    assert target_file.read_text(encoding="utf-8") == content


def test_write_file_target_is_existing_directory(tmp_path):
    """Verify attempting to write to an existing directory path returns structured failure."""
    res = write_file(str(tmp_path), "content")

    assert set(res.keys()) == EXPECTED_WRITE_KEYS
    assert res["success"] is False
    assert res["bytes_written"] == 0
    assert "directory" in res["error"].lower()


@pytest.mark.parametrize("invalid_path", ["", None, 12345, [], {}])
def test_write_file_invalid_filepath(invalid_path):
    """Verify non-string or empty filepath arguments return structured error without raising."""
    res = write_file(invalid_path, "sample content")

    assert set(res.keys()) == EXPECTED_WRITE_KEYS
    assert res["success"] is False
    assert res["bytes_written"] == 0
    assert "Invalid filepath" in res["error"]


@pytest.mark.parametrize("invalid_content", [None, 12345, [], {}])
def test_write_file_invalid_content(tmp_path, invalid_content):
    """Verify non-string content arguments return structured error without raising."""
    target_file = str(tmp_path / "invalid_content.txt")
    res = write_file(target_file, invalid_content)

    assert set(res.keys()) == EXPECTED_WRITE_KEYS
    assert res["success"] is False
    assert res["bytes_written"] == 0
    assert "Invalid content" in res["error"]


def test_write_file_never_raises():
    """Verify write_file never raises unhandled exceptions for pathological inputs."""
    bad_calls = [
        ("", ""),
        (None, None),
        ("in*valid?name", "Windows device"),
        ("invalid://path/file.txt", "content"),
    ]
    for path, content in bad_calls:
        try:
            res = write_file(path, content)
            assert isinstance(res, dict)
            assert "success" in res
        except Exception as exc:
            pytest.fail(f"write_file({path!r}, {content!r}) raised unhandled exception: {exc}")


# ============================================================================
# Phase 5: search_in_file tests
# ============================================================================

EXPECTED_SEARCH_KEYS = {
    "success",
    "filepath",
    "keyword",
    "match_count",
    "matches",
    "error",
}


def test_search_case_insensitive():
    """Verify case-insensitive search finds uppercase and lowercase occurrences."""
    sample_txt = str(FIXTURES_DIR / "sample.txt")
    res = search_in_file(sample_txt, "python")

    assert set(res.keys()) == EXPECTED_SEARCH_KEYS
    assert res["success"] is True
    assert res["filepath"] == sample_txt
    assert res["keyword"] == "python"
    assert res["match_count"] >= 3
    assert len(res["matches"]) == res["match_count"]
    assert res["error"] is None

    # Verify structure of matches
    for match in res["matches"]:
        assert "line_number" in match
        assert "context" in match
        assert "python" in match["context"].lower()


def test_search_no_match():
    """Verify searching for a non-existent keyword returns success: True with 0 matches."""
    sample_txt = str(FIXTURES_DIR / "sample.txt")
    res = search_in_file(sample_txt, "non_existent_keyword_xyz_999")

    assert set(res.keys()) == EXPECTED_SEARCH_KEYS
    assert res["success"] is True
    assert res["match_count"] == 0
    assert res["matches"] == []
    assert res["error"] is None


def test_search_in_pdf():
    """Verify search_in_file delegates correctly to read_file on PDF documents."""
    sample_pdf = str(FIXTURES_DIR / "sample.pdf")
    res = search_in_file(sample_pdf, "Kubernetes")

    assert res["success"] is True
    assert res["match_count"] >= 1
    assert any("Kubernetes" in m["context"] for m in res["matches"])


def test_search_in_docx():
    """Verify search_in_file delegates correctly to read_file on DOCX documents."""
    sample_docx = str(FIXTURES_DIR / "sample.docx")
    res = search_in_file(sample_docx, "PyTorch")

    assert res["success"] is True
    assert res["match_count"] >= 1
    assert any("PyTorch" in m["context"] for m in res["matches"])


def test_search_unreadable_missing_file():
    """Verify search on a non-existent file returns success: False propagating read error."""
    missing_path = str(FIXTURES_DIR / "non_existent_file_54321.txt")
    res = search_in_file(missing_path, "python")

    assert set(res.keys()) == EXPECTED_SEARCH_KEYS
    assert res["success"] is False
    assert res["match_count"] == 0
    assert res["matches"] == []
    assert "File not found" in res["error"]


def test_search_corrupt_file():
    """Verify search on a corrupt file returns success: False without raising."""
    corrupt_path = str(FIXTURES_DIR / "corrupt.pdf")
    res = search_in_file(corrupt_path, "python")

    assert set(res.keys()) == EXPECTED_SEARCH_KEYS
    assert res["success"] is False
    assert res["match_count"] == 0
    assert res["matches"] == []
    assert res["error"] is not None


def test_search_context_window_snippet(tmp_path):
    """Verify snippet truncation handles long lines cleanly with ellipsis."""
    long_line = "PrefixText " + ("word " * 60) + "TARGET_KEYWORD" + (" word" * 60) + " SuffixText"
    test_file = tmp_path / "long_line.txt"
    test_file.write_text(long_line, encoding="utf-8")

    res = search_in_file(str(test_file), "TARGET_KEYWORD")
    assert res["success"] is True
    assert res["match_count"] == 1
    context = res["matches"][0]["context"]
    assert "TARGET_KEYWORD" in context
    assert context.startswith("...") or context.endswith("...")


@pytest.mark.parametrize("invalid_kw", ["", "   ", None, 12345, [], {}])
def test_search_invalid_keyword(invalid_kw):
    """Verify empty or non-string keywords return structured failure without raising."""
    sample_txt = str(FIXTURES_DIR / "sample.txt")
    res = search_in_file(sample_txt, invalid_kw)

    assert set(res.keys()) == EXPECTED_SEARCH_KEYS
    assert res["success"] is False
    assert res["match_count"] == 0
    assert res["matches"] == []
    assert "Invalid keyword" in res["error"]


@pytest.mark.parametrize("invalid_path", ["", None, 12345, [], {}])
def test_search_invalid_filepath(invalid_path):
    """Verify empty or non-string filepaths return structured failure without raising."""
    res = search_in_file(invalid_path, "python")

    assert set(res.keys()) == EXPECTED_SEARCH_KEYS
    assert res["success"] is False
    assert res["match_count"] == 0
    assert res["matches"] == []
    assert "Invalid filepath" in res["error"]


def test_search_never_raises():
    """Verify search_in_file never raises unhandled exceptions for pathological inputs."""
    bad_calls = [
        ("", ""),
        (None, None),
        ("in*valid?name", "Windows device"),
        ("invalid://path/file.txt", "search_term"),
        (str(FIXTURES_DIR / "corrupt.docx"), "keyword"),
    ]
    for path, kw in bad_calls:
        try:
            res = search_in_file(path, kw)
            assert isinstance(res, dict)
            assert "success" in res
        except Exception as exc:
            pytest.fail(f"search_in_file({path!r}, {kw!r}) raised unhandled exception: {exc}")


# ============================================================================
# Phase 6: Tool Layer Hardening (Path Sandboxing & Security Tests)
# ============================================================================

def test_read_file_path_traversal_rejected():
    """Verify read_file rejects attempts to access files outside the base directory."""
    traversal_paths = [
        "../../etc/passwd",
        "..\\..\\..\\Windows\\System32\\cmd.exe",
        "C:/Windows/System32/drivers/etc/hosts",
    ]
    for p in traversal_paths:
        res = read_file(p)
        assert res["success"] is False
        assert res["content"] is None
        assert "traversal" in res["error"].lower() or "outside allowed" in res["error"].lower()


def test_write_file_path_traversal_rejected():
    """Verify write_file rejects attempts to write files outside the base directory."""
    traversal_paths = [
        "../../evil.txt",
        "..\\..\\..\\Windows\\Temp\\evil.txt",
        "C:/Windows/evil.txt",
    ]
    for p in traversal_paths:
        res = write_file(p, "malicious payload")
        assert res["success"] is False
        assert res["bytes_written"] == 0
        assert "traversal" in res["error"].lower() or "outside allowed" in res["error"].lower()


def test_list_files_path_traversal_rejected():
    """Verify list_files rejects attempts to list directories outside the base directory."""
    traversal_paths = [
        "../../",
        "..\\..\\..\\Windows",
        "C:/Windows",
    ]
    for p in traversal_paths:
        res = list_files(p)
        assert res == []


def test_search_in_file_path_traversal_rejected():
    """Verify search_in_file rejects attempts to search files outside the base directory."""
    traversal_paths = [
        "../../etc/passwd",
        "..\\..\\..\\Windows\\System32\\cmd.exe",
    ]
    for p in traversal_paths:
        res = search_in_file(p, "password")
        assert res["success"] is False
        assert res["match_count"] == 0
        assert "traversal" in res["error"].lower() or "outside allowed" in res["error"].lower()


def test_base_dir_configuration_and_isolation(tmp_path):
    """Verify set_base_dir strictly restricts operations to the configured subfolder."""
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("classified data", encoding="utf-8")

    allowed_file = sandbox / "allowed.txt"
    allowed_file.write_text("public data", encoding="utf-8")

    try:
        set_base_dir(sandbox)
        assert get_base_dir() == sandbox.resolve()

        # Access inside sandbox succeeds
        allowed_res = read_file("allowed.txt")
        assert allowed_res["success"] is True
        assert allowed_res["content"] == "public data"

        # Attempt to escape sandbox via relative path fails
        escape_res = read_file("../secret.txt")
        assert escape_res["success"] is False
        assert "traversal" in escape_res["error"].lower() or "outside allowed" in escape_res["error"].lower()

    finally:
        reset_base_dir()


def test_zero_llm_imports_static_check():
    """Enforce architectural invariant: fs_tools.py has zero dependencies on LLM provider SDKs."""
    fs_tools_file = Path(__file__).parent.parent / "fs_tools.py"
    content = fs_tools_file.read_text(encoding="utf-8").lower()
    for forbidden in ["import openai", "from openai", "import anthropic", "from anthropic", "langchain"]:
        assert forbidden not in content, f"Architectural violation: {forbidden} found in fs_tools.py"


def test_logging_emits_records(caplog):
    """Verify tool invocations produce structured log messages via logging framework."""
    import logging
    with caplog.at_level(logging.INFO, logger="fs_tools"):
        _ = list_files("resumes")
        _ = read_file(str(FIXTURES_DIR / "sample.txt"))

    records = [rec.message for rec in caplog.records if rec.name == "fs_tools"]
    assert any("list_files" in msg for msg in records)
    assert any("read_file" in msg for msg in records)




