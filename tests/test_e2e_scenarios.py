"""
End-to-End integration tests for LLM File System Assistant.

Phase 12: Scenario Validation against real LLM Provider and real fixture resumes.
Tests the three canonical queries from ProblemStatement.md §4.2.3.
"""

import os
import pytest
from llm_file_assistant import run_query

has_api_key = bool(
    os.environ.get("GROQ_API_KEY")
    or os.environ.get("OPENAI_API_KEY")
    or os.environ.get("ANTHROPIC_API_KEY")
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not has_api_key, reason="No LLM API key configured in environment"),
]


def test_e2e_scenario1_read_all_resumes():
    """Scenario 1: Read all resumes in resumes/ and provide brief summary of each candidate."""
    query = "Read all the resumes in the resumes folder and give me a brief summary of each candidate."
    response = run_query(query)

    assert isinstance(response, str)
    assert len(response.strip()) > 50

    lower_resp = response.lower()
    # Check that all candidate resumes were identified and summarized
    assert "john" in lower_resp or "doe" in lower_resp
    assert "jane" in lower_resp or "smith" in lower_resp
    assert "alex" in lower_resp or "johnson" in lower_resp


def test_e2e_scenario2_find_python_resumes():
    """Scenario 2: Find all resumes mentioning Python and extract employment details."""
    query = "Find all resumes that mention Python and tell me where they worked."
    response = run_query(query)

    assert isinstance(response, str)
    assert len(response.strip()) > 50

    lower_resp = response.lower()
    # At least John Doe (Acme Tech Solutions / Innovate Corp) or Jane Smith (AI Solutions)
    assert "john" in lower_resp or "acme" in lower_resp or "innovate" in lower_resp


def test_e2e_scenario3_create_summary_file():
    """Scenario 3: Create a summary of John Doe's resume and save it to output/summary_john_doe.txt."""
    target_output_file = os.path.join("output", "summary_john_doe.txt")

    # Clean up prior to test run if existing
    if os.path.exists(target_output_file):
        os.remove(target_output_file)

    query = "Create a summary of John Doe's resume and save it to output/summary_john_doe.txt."
    response = run_query(query)

    try:
        assert os.path.exists(target_output_file), f"Expected {target_output_file} to be created by the tool loop."
        file_size = os.path.getsize(target_output_file)
        assert file_size > 20, f"Expected non-empty output file, got size {file_size} bytes."

        with open(target_output_file, "r", encoding="utf-8") as f:
            written_content = f.read()

        assert "John Doe" in written_content or "john doe" in written_content.lower()

    finally:
        # Clean up output file after test assertion to keep test runs idempotent
        if os.path.exists(target_output_file):
            os.remove(target_output_file)


def test_e2e_keyword_not_found_explicit():
    """Verify that searching for a non-existent skill explicitly states it was not found."""
    query = "Find all resumes that mention Rust and tell me where they worked."
    response = run_query(query)

    assert isinstance(response, str)
    lower = response.lower()
    assert "not found" in lower or "no resumes" in lower or "none of the resumes" in lower or "no candidate" in lower


def test_e2e_keyword_spelling_mistake_corrected():
    """Verify that a misspelled keyword ('Pythn') is recognized, corrected, and matching candidates are returned."""
    query = "Find all resumes that mention Pythn and tell me where they worked."
    response = run_query(query)

    assert isinstance(response, str)
    lower = response.lower()
    # Check that Python was recognized / searched and candidates returned
    assert "python" in lower or "pythn" in lower
    assert "john" in lower or "michael" in lower or "chang" in lower or "acme" in lower

