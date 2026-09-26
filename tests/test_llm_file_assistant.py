"""
Unit tests for llm_file_assistant.py.

Phase 7: LLM Provider Adapter (connectivity, payload construction, mock tests, error handling).
"""

from unittest.mock import MagicMock, patch
import os
import pytest

from llm_file_assistant import (
    LLMResponse,
    ToolCallRequest,
    LLMProviderError,
    OpenAICompatibleProvider,
    AnthropicProvider,
    get_provider,
    get_tool_schemas,
    dispatch_tool_call,
    serialize_tool_result,
    TOOL_REGISTRY,
    TOOL_SCHEMAS,
    run_query,
    DEFAULT_SYSTEM_PROMPT,
    Session,
    run_cli,
)


def test_llm_response_container():
    """Verify LLMResponse properties and tool call presence checking."""
    text_only = LLMResponse(content="Hello world")
    assert text_only.content == "Hello world"
    assert text_only.tool_calls is None
    assert text_only.has_tool_calls is False

    tc = ToolCallRequest(id="call_123", name="list_files", arguments={"directory": "resumes"})
    with_tools = LLMResponse(content="", tool_calls=[tc])
    assert with_tools.has_tool_calls is True
    assert len(with_tools.tool_calls) == 1
    assert with_tools.tool_calls[0].name == "list_files"
    assert with_tools.tool_calls[0].arguments == {"directory": "resumes"}


def test_openai_provider_sends_expected_payload():
    """Verify OpenAICompatibleProvider formats messages and calls client correctly without network."""
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "I can help with that."
    mock_choice.message.tool_calls = None
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    provider = OpenAICompatibleProvider(
        client=mock_client,
        model="custom-test-model",
    )

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
    ]

    response = provider.send(messages)

    assert response.content == "I can help with that."
    assert response.has_tool_calls is False

    mock_client.chat.completions.create.assert_called_once_with(
        model="custom-test-model",
        messages=messages,
    )


def test_openai_provider_parses_tool_calls():
    """Verify OpenAICompatibleProvider correctly parses tool call JSON arguments into dictionaries."""
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = ""

    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_abc987"
    mock_tool_call.function.name = "read_file"
    mock_tool_call.function.arguments = '{"filepath": "resumes/sample.pdf"}'
    mock_choice.message.tool_calls = [mock_tool_call]

    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    provider = OpenAICompatibleProvider(client=mock_client)
    response = provider.send([{"role": "user", "content": "Read sample.pdf"}])

    assert response.has_tool_calls is True
    assert len(response.tool_calls) == 1
    tc = response.tool_calls[0]
    assert tc.id == "call_abc987"
    assert tc.name == "read_file"
    assert tc.arguments == {"filepath": "resumes/sample.pdf"}


def test_openai_provider_raises_provider_error_on_failure():
    """Verify client exceptions are caught and wrapped into LLMProviderError."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("Connection timeout")

    provider = OpenAICompatibleProvider(client=mock_client)
    with pytest.raises(LLMProviderError) as exc_info:
        provider.send([{"role": "user", "content": "Hi"}])

    assert "Connection timeout" in str(exc_info.value)


def test_anthropic_provider_sends_expected_payload():
    """Verify AnthropicProvider separates system prompt and formats messages."""
    mock_client = MagicMock()
    mock_block = MagicMock()
    mock_block.text = "Hello from Claude"
    mock_client.messages.create.return_value = MagicMock(content=[mock_block])

    provider = AnthropicProvider(client=mock_client, model="claude-3-5-sonnet")

    messages = [
        {"role": "system", "content": "System prompt instructions"},
        {"role": "user", "content": "User question"},
    ]

    response = provider.send(messages)
    assert response.content == "Hello from Claude"

    mock_client.messages.create.assert_called_once_with(
        model="claude-3-5-sonnet",
        messages=[{"role": "user", "content": "User question"}],
        system="System prompt instructions",
        max_tokens=1024,
    )


def test_missing_api_keys_raises_provider_error(monkeypatch):
    """Verify initializing a provider with no configured API keys raises LLMProviderError."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(LLMProviderError) as exc_info:
        _ = OpenAICompatibleProvider()

    assert "Missing API key" in str(exc_info.value)


@pytest.mark.integration
def test_live_groq_or_openai_connectivity_smoke():
    """Live smoke test verifying actual LLM completion against configured provider (requires API key)."""
    api_key = os.environ.get("GROQ_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("No live API key found in environment (.env)")

    provider = get_provider()
    response = provider.send(
        messages=[
            {"role": "system", "content": "You are a concise assistant."},
            {"role": "user", "content": "Say 'OK' in one word."},
        ]
    )

    assert response is not None
    assert isinstance(response.content, str)
    assert len(response.content.strip()) > 0


# ============================================================================
# Phase 8: Tool Schema Registry & Dispatcher Tests
# ============================================================================

def test_schemas_conform_to_provider_spec():
    """Verify that all four tool schemas follow standard OpenAI function schema specs."""
    schemas = get_tool_schemas()
    assert len(schemas) == 4

    names = {s["function"]["name"] for s in schemas}
    assert names == {"read_file", "list_files", "write_file", "search_in_file"}

    for s in schemas:
        assert s["type"] == "function"
        fn = s["function"]
        assert "name" in fn and isinstance(fn["name"], str)
        assert "description" in fn and len(fn["description"]) > 10
        assert "parameters" in fn
        params = fn["parameters"]
        assert params["type"] == "object"
        assert "properties" in params
        assert "required" in params and isinstance(params["required"], list)


def test_dispatch_known_tools(tmp_path):
    """Verify dispatch_tool_call invokes each tool correctly and returns expected results."""
    # 1. list_files
    list_res = dispatch_tool_call("list_files", {"directory": "resumes"})
    assert isinstance(list_res, list)
    assert len(list_res) >= 3

    # 2. read_file
    read_res = dispatch_tool_call("read_file", {"filepath": "tests/fixtures/sample.txt"})
    assert isinstance(read_res, dict)
    assert read_res["success"] is True
    assert "John Doe" in read_res["content"]

    # 3. write_file
    out_file = str(tmp_path / "dispatch_out.txt")
    write_res = dispatch_tool_call("write_file", {"filepath": out_file, "content": "Dispatched content"})
    assert isinstance(write_res, dict)
    assert write_res["success"] is True
    assert write_res["bytes_written"] > 0

    # 4. search_in_file
    search_res = dispatch_tool_call("search_in_file", {"filepath": "tests/fixtures/sample.txt", "keyword": "python"})
    assert isinstance(search_res, dict)
    assert search_res["success"] is True
    assert search_res["match_count"] >= 1


def test_dispatch_unknown_tool():
    """Verify unknown tool names return structured error without raising an exception."""
    res = dispatch_tool_call("non_existent_tool_123", {"arg": "val"})
    assert isinstance(res, dict)
    assert res["success"] is False
    assert "Unknown tool" in res["error"]
    assert "Available tools are" in res["error"]


def test_dispatch_missing_required_arguments():
    """Verify missing required arguments are caught and returned as structured errors."""
    # Missing filepath for read_file
    res1 = dispatch_tool_call("read_file", {})
    assert res1["success"] is False
    assert "Missing required argument" in res1["error"]
    assert "filepath" in res1["error"]

    # Missing content for write_file
    res2 = dispatch_tool_call("write_file", {"filepath": "out.txt"})
    assert res2["success"] is False
    assert "Missing required argument" in res2["error"]
    assert "content" in res2["error"]

    # Missing directory for list_files
    res3 = dispatch_tool_call("list_files", {})
    assert res3["success"] is False
    assert "Missing required argument" in res3["error"]
    assert "directory" in res3["error"]


def test_dispatch_invalid_arguments_type():
    """Verify non-dictionary arguments return structured dispatch error."""
    res = dispatch_tool_call("read_file", "invalid_string_args")  # type: ignore
    assert isinstance(res, dict)
    assert res["success"] is False
    assert "arguments for 'read_file' must be a dictionary" in res["error"]


def test_serialize_tool_result():
    """Verify serialize_tool_result produces valid, parseable JSON strings."""
    data = {"success": True, "files": ["a.txt", "b.pdf"], "count": 2}
    serialized = serialize_tool_result(data)
    assert isinstance(serialized, str)
    import json
    parsed = json.loads(serialized)
    assert parsed == data


# ============================================================================
# Phase 9: Single Tool-Call Loop Tests
# ============================================================================

def test_single_tool_loop_mocked():
    """Verify run_query executes a single tool call round trip using a mocked provider."""
    mock_provider = MagicMock()

    # Turn 1: LLM requests list_files tool call
    turn1_response = LLMResponse(
        content="",
        tool_calls=[
            ToolCallRequest(
                id="call_list_resumes",
                name="list_files",
                arguments={"directory": "resumes"},
            )
        ],
    )

    # Turn 2: LLM receives tool output and returns final synthesis
    turn2_response = LLMResponse(
        content="I found 3 resumes in the resumes folder: sample.docx, sample.pdf, and sample.txt.",
        tool_calls=None,
    )

    mock_provider.send.side_effect = [turn1_response, turn2_response]

    answer = run_query("List all resumes", provider=mock_provider)

    assert "sample.pdf" in answer
    assert "sample.docx" in answer
    assert mock_provider.send.call_count == 2

    # Verify that the second call received the tool response message
    second_call_messages = mock_provider.send.call_args_list[1][1]["messages"]
    tool_messages = [m for m in second_call_messages if m.get("role") == "tool"]
    assert len(tool_messages) == 1
    assert tool_messages[0]["tool_call_id"] == "call_list_resumes"
    assert "sample.txt" in tool_messages[0]["content"]


def test_single_tool_loop_direct_answer_no_tools():
    """Verify run_query returns directly when the LLM provides an answer without tools."""
    mock_provider = MagicMock()
    mock_provider.send.return_value = LLMResponse(
        content="Hello! How can I assist you with your files today?",
        tool_calls=None,
    )

    answer = run_query("Hi there", provider=mock_provider)
    assert answer == "Hello! How can I assist you with your files today?"
    assert mock_provider.send.call_count == 1


def test_single_tool_loop_invalid_query():
    """Verify run_query handles empty or invalid queries gracefully."""
    assert "Please provide a valid" in run_query("")
    assert "Please provide a valid" in run_query(None)  # type: ignore


@pytest.mark.integration
def test_single_tool_loop_live_integration():
    """Verify real single tool-call execution against configured LLM provider and live filesystem."""
    api_key = os.environ.get("GROQ_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("No live API key found in environment (.env)")

    answer = run_query("List the files in the resumes directory")
    assert isinstance(answer, str)
    assert len(answer) > 10
    # The answer should mention the files discovered by list_files
    lower_answer = answer.lower()
    assert "sample" in lower_answer or "resume" in lower_answer or ".pdf" in lower_answer


# ============================================================================
# Phase 10: Multi-Tool-Call Loop Tests
# ============================================================================

def test_loop_two_sequential_tool_calls():
    """Verify loop handles sequential chained tool calls across multiple turns."""
    mock_provider = MagicMock()

    # Turn 1: LLM requests list_files
    turn1 = LLMResponse(
        content="",
        tool_calls=[ToolCallRequest(id="tc_list", name="list_files", arguments={"directory": "resumes"})],
    )
    # Turn 2: LLM receives file list, requests read_file on sample.txt
    turn2 = LLMResponse(
        content="",
        tool_calls=[ToolCallRequest(id="tc_read", name="read_file", arguments={"filepath": "tests/fixtures/sample.txt"})],
    )
    # Turn 3: LLM receives content, outputs final answer
    turn3 = LLMResponse(
        content="Candidate John Doe has 6 years of experience in Python and FastAPI.",
        tool_calls=None,
    )

    mock_provider.send.side_effect = [turn1, turn2, turn3]

    ans = run_query("Find and read John Doe resume", provider=mock_provider)

    assert "John Doe" in ans
    assert "FastAPI" in ans
    assert mock_provider.send.call_count == 3


def test_loop_parallel_tool_calls_in_one_turn():
    """Verify loop dispatches multiple tool calls issued in a single LLM response turn."""
    mock_provider = MagicMock()

    # Turn 1: LLM issues two parallel tool calls
    turn1 = LLMResponse(
        content="",
        tool_calls=[
            ToolCallRequest(id="tc_p1", name="read_file", arguments={"filepath": "tests/fixtures/sample.txt"}),
            ToolCallRequest(id="tc_p2", name="read_file", arguments={"filepath": "tests/fixtures/sample.docx"}),
        ],
    )
    # Turn 2: LLM receives both results and summarizes
    turn2 = LLMResponse(
        content="Summary: Both John Doe and Jane Smith possess Python expertise.",
        tool_calls=None,
    )

    mock_provider.send.side_effect = [turn1, turn2]

    ans = run_query("Compare candidates", provider=mock_provider)

    assert "John Doe" in ans
    assert "Jane Smith" in ans
    assert mock_provider.send.call_count == 2

    # Verify both tool results were passed to turn 2
    turn2_messages = mock_provider.send.call_args_list[1][1]["messages"]
    tool_results = [m for m in turn2_messages if m.get("role") == "tool"]
    assert len(tool_results) == 2
    assert tool_results[0]["tool_call_id"] == "tc_p1"
    assert tool_results[1]["tool_call_id"] == "tc_p2"


def test_loop_max_iterations_exceeded():
    """Verify loop safely terminates and warns user when max_iterations limit is reached."""
    mock_provider = MagicMock()

    # Model perpetually calls tool without converging
    mock_provider.send.return_value = LLMResponse(
        content="",
        tool_calls=[ToolCallRequest(id="tc_loop", name="list_files", arguments={"directory": "resumes"})],
    )

    result = run_query("Infinite task", provider=mock_provider, max_iterations=3)

    assert "maximum allowed tool iterations (3)" in result
    assert mock_provider.send.call_count == 3


def test_loop_tool_error_is_relayed_not_fatal():
    """Verify tool failures are relayed as tool responses without crashing the loop."""
    mock_provider = MagicMock()

    # Turn 1: LLM attempts to read missing file
    turn1 = LLMResponse(
        content="",
        tool_calls=[ToolCallRequest(id="tc_err", name="read_file", arguments={"filepath": "missing_file_99.txt"})],
    )
    # Turn 2: LLM observes error in tool response and reports it helpfully
    turn2 = LLMResponse(
        content="I attempted to read missing_file_99.txt, but the file was not found.",
        tool_calls=None,
    )

    mock_provider.send.side_effect = [turn1, turn2]

    ans = run_query("Read missing_file_99.txt", provider=mock_provider)

    assert "missing_file_99.txt" in ans
    assert "not found" in ans.lower()
    assert mock_provider.send.call_count == 2

    # Verify the error was in the tool message content
    turn2_messages = mock_provider.send.call_args_list[1][1]["messages"]
    tool_msg = [m for m in turn2_messages if m.get("role") == "tool"][0]
    assert "File not found" in tool_msg["content"]


# ============================================================================
# Phase 11: Session State & CLI REPL Tests
# ============================================================================

def test_session_initialization_and_clear():
    """Verify Session initializes with system prompt and clear() restores it."""
    session = Session(system_prompt="Custom instructions.")
    assert len(session.messages) == 1
    assert session.messages[0] == {"role": "system", "content": "Custom instructions."}

    session.add_user_message("Hello")
    session.add_assistant_message("Hi there!")
    assert len(session.messages) == 3

    session.clear()
    assert len(session.messages) == 1
    assert session.messages[0] == {"role": "system", "content": "Custom instructions."}


def test_session_maintains_history_across_calls():
    """Verify session maintains conversation history across successive run_query calls."""
    mock_provider = MagicMock()

    # Response 1: answering turn 1
    resp1 = LLMResponse(content="I found 3 candidate resumes: Alice, Bob, Charlie.")
    # Response 2: answering follow-up turn 2
    resp2 = LLMResponse(content="Alice has 5 years of Python experience.")

    mock_provider.send.side_effect = [resp1, resp2]

    session = Session()

    # Turn 1
    ans1 = run_query("List the candidates", provider=mock_provider, session=session)
    assert "Alice, Bob, Charlie" in ans1

    # Turn 2: Follow-up question referencing turn 1 context
    ans2 = run_query("Tell me more about the first candidate", provider=mock_provider, session=session)
    assert "Alice has 5 years" in ans2

    # Assert mock_provider received conversation history in turn 2
    turn2_call_messages = mock_provider.send.call_args_list[1][1]["messages"]
    assert len(turn2_call_messages) == 4
    assert turn2_call_messages[0]["role"] == "system"
    assert turn2_call_messages[1] == {"role": "user", "content": "List the candidates"}
    assert turn2_call_messages[2] == {"role": "assistant", "content": "I found 3 candidate resumes: Alice, Bob, Charlie."}
    assert turn2_call_messages[3] == {"role": "user", "content": "Tell me more about the first candidate"}

    # Assert session.messages contains complete history including turn 2 assistant response
    assert len(session.messages) == 5
    assert session.messages[-1] == {"role": "assistant", "content": "Alice has 5 years of Python experience."}


def test_run_query_importable_without_cli():
    """Verify run_query can be called standalone as a library function without entering the CLI REPL."""
    mock_provider = MagicMock()
    mock_provider.send.return_value = LLMResponse(content="Standalone library response.")

    result = run_query("Test library usage", provider=mock_provider)
    assert result == "Standalone library response."


def test_cli_repl_commands_exit_and_clear(capsys):
    """Verify CLI REPL responds to exit, quit, and clear commands."""
    with patch("builtins.input", side_effect=["clear", "exit"]):
        run_cli()

    captured = capsys.readouterr().out
    assert "LLM File System Assistant CLI" in captured
    assert "Conversation history cleared." in captured
    assert "Goodbye!" in captured


def test_cli_repl_handles_keyboard_interrupt(capsys):
    """Verify CLI REPL exits gracefully on KeyboardInterrupt (Ctrl+C)."""
    with patch("builtins.input", side_effect=KeyboardInterrupt):
        run_cli()

    captured = capsys.readouterr().out
    assert "Exiting. Goodbye!" in captured


def test_cli_repl_processes_query_and_prints_response(capsys):
    """Verify CLI REPL handles a valid query turn and then exits cleanly."""
    mock_provider = MagicMock()
    mock_provider.send.return_value = LLMResponse(content="Candidate resume summary.")

    with patch("llm_file_assistant.get_provider", return_value=mock_provider):
        with patch("builtins.input", side_effect=["Summarize John Doe", "quit"]):
            run_cli()

# ============================================================================
# Phase 13: Structured Audit Logging Tests
# ============================================================================

def test_dispatch_logs_structured_audit_record(caplog):
    """Verify tool dispatch logs structured audit records with duration and arguments."""
    with caplog.at_level("INFO", logger="llm_file_assistant"):
        res = dispatch_tool_call("list_files", {"directory": "resumes"})

    assert isinstance(res, list)

    log_messages = [r.message for r in caplog.records if r.name == "llm_file_assistant"]
    tool_call_logs = [m for m in log_messages if "tool_call:" in m]

    assert len(tool_call_logs) >= 1
    log_entry = tool_call_logs[0]
    assert "name='list_files'" in log_entry
    assert "success=True" in log_entry
    assert "duration_ms=" in log_entry
    assert "args=" in log_entry


def test_audit_log_file_written_to_disk():
    """Verify logs/app.log exists and contains tool invocation logs."""
    # Trigger a tool dispatch to ensure a log entry is written
    dispatch_tool_call("list_files", {"directory": "resumes"})

    log_file = os.path.join("logs", "app.log")
    assert os.path.exists(log_file), f"Expected log file {log_file} to exist."

    with open(log_file, "r", encoding="utf-8") as f:
        content = f.read()

    assert "tool_call:" in content or "list_files" in content


# ============================================================================
# Feedback 1 Tests: Keyword Not Found & Typo Correction
# ============================================================================

def test_system_prompt_contains_typo_correction_and_not_found_rules():
    """Verify DEFAULT_SYSTEM_PROMPT includes rules for typo correction and explicit not-found status."""
    assert "Typo and Spelling Correction" in DEFAULT_SYSTEM_PROMPT
    assert "Explicit Not-Found Status" in DEFAULT_SYSTEM_PROMPT
    assert "No resumes were found" in DEFAULT_SYSTEM_PROMPT


def test_loop_handles_keyword_not_found_explicitly():
    """Verify assistant produces explicit not-found answer when tool search finds 0 matches."""
    mock_provider = MagicMock()

    # Turn 1: Model requests search_in_file for a non-existent skill 'Cobol'
    turn1 = LLMResponse(
        content="",
        tool_calls=[
            ToolCallRequest(
                id="tc_search",
                name="search_in_file",
                arguments={"filepath": "resumes/sample.txt", "keyword": "Cobol"},
            )
        ],
    )
    # Turn 2: Model receives 0 matches and explicitly responds that Cobol was not found
    turn2 = LLMResponse(
        content="No resumes were found mentioning 'Cobol'. Checked candidate resumes and found 0 occurrences.",
        tool_calls=None,
    )

    mock_provider.send.side_effect = [turn1, turn2]

    response = run_query("Find all resumes mentioning Cobol", provider=mock_provider)

    assert "No resumes were found" in response or "not found" in response.lower()
    assert "Cobol" in response
    assert mock_provider.send.call_count == 2


def test_turn_lifecycle_logging_markers(caplog):
    """Verify turn lifecycle logs emit visual markers: [TURN START], [STEP 1], and [TURN COMPLETE]."""
    mock_provider = MagicMock()
    mock_provider.send.return_value = LLMResponse(content="Final synthesized result.")

    with caplog.at_level("INFO", logger="llm_file_assistant"):
        ans = run_query("Test lifecycle logging", provider=mock_provider)

    assert ans == "Final synthesized result."
    messages = [r.message for r in caplog.records if r.name == "llm_file_assistant"]

    assert any("[TURN START]" in m for m in messages)
    assert any("[STEP 1] LLM INVOCATION" in m for m in messages)
    assert any("[TURN COMPLETE] Status: CONVERGED" in m for m in messages)







