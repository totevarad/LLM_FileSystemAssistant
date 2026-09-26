"""
Unit tests for llm_file_assistant.py.

Phase 7: LLM Provider Adapter (connectivity, payload construction, mock tests, error handling).
"""

from unittest.mock import MagicMock
import os
import pytest

from llm_file_assistant import (
    LLMResponse,
    ToolCallRequest,
    LLMProviderError,
    OpenAICompatibleProvider,
    AnthropicProvider,
    get_provider,
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
