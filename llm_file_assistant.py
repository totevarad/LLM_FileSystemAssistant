"""
LLM Orchestration Layer for File System Assistant.

This module provides the conversational orchestration, tool schema registry,
LLM provider abstraction, and tool-call execution loop.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import json
import logging
import os
from typing import Optional, List, Dict, Any

import dotenv

# Load environment variables from .env
dotenv.load_dotenv()

logger = logging.getLogger("llm_file_assistant")
if not logger.handlers:
    logger.addHandler(logging.NullHandler())


class LLMProviderError(Exception):
    """Raised when an LLM provider encounters an authentication, network, or API failure."""
    pass


@dataclass
class ToolCallRequest:
    """Represents a standardized tool invocation requested by an LLM."""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class LLMResponse:
    """Standardized response container across all LLM providers."""
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCallRequest]] = None
    raw_response: Optional[Any] = None

    @property
    def has_tool_calls(self) -> bool:
        """Return True if the response contains one or more tool calls."""
        return bool(self.tool_calls)


class LLMProvider(ABC):
    """Abstract base class for all LLM provider adapters."""

    @abstractmethod
    def send(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        """Send messages and optional tool definitions to the LLM and return a standardized response."""
        raise NotImplementedError


class OpenAICompatibleProvider(LLMProvider):
    """Provider adapter for OpenAI and OpenAI-compatible endpoints (Groq, vLLM, Ollama, etc.)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        client: Optional[Any] = None,
    ):
        from openai import OpenAI

        if client is not None:
            self.client = client
            self.model = model or "openai/gpt-oss-120b"
            return

        groq_key = os.environ.get("GROQ_API_KEY")
        openai_key = os.environ.get("OPENAI_API_KEY")

        # Determine effective API key and base URL
        resolved_key = api_key or groq_key or openai_key
        if not resolved_key:
            raise LLMProviderError(
                "Missing API key: Neither GROQ_API_KEY nor OPENAI_API_KEY is configured."
            )

        if base_url:
            resolved_base_url = base_url
        elif groq_key and not openai_key:
            resolved_base_url = "https://api.groq.com/openai/v1"
        else:
            resolved_base_url = os.environ.get("LLM_BASE_URL")

        self.model = (
            model
            or os.environ.get("LLM_MODEL")
            or ("openai/gpt-oss-120b" if groq_key else "gpt-4o-mini")
        )

        try:
            self.client = OpenAI(api_key=resolved_key, base_url=resolved_base_url)
        except Exception as exc:
            raise LLMProviderError(f"Failed to initialize OpenAI client: {exc}") from exc

    def send(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        """Send messages and optional tools to OpenAI-compatible endpoint."""
        logger.info("OpenAIProvider sending %d messages to model '%s'", len(messages), self.model)

        params: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            params["tools"] = tools

        try:
            response = self.client.chat.completions.create(**params)
            choice = response.choices[0]
            msg = choice.message

            tool_calls = None
            if msg.tool_calls:
                tool_calls = []
                for tc in msg.tool_calls:
                    # Parse arguments JSON safely
                    args = tc.function.arguments
                    if isinstance(args, str):
                        try:
                            args_dict = json.loads(args)
                        except json.JSONDecodeError:
                            args_dict = {"raw_arguments": args}
                    else:
                        args_dict = dict(args) if args else {}

                    tool_calls.append(
                        ToolCallRequest(
                            id=tc.id,
                            name=tc.function.name,
                            arguments=args_dict,
                        )
                    )

            return LLMResponse(
                content=msg.content or "",
                tool_calls=tool_calls,
                raw_response=response,
            )

        except Exception as exc:
            logger.exception("OpenAIProvider request failed: %s", exc)
            raise LLMProviderError(f"OpenAIProvider error: {str(exc)}") from exc


class AnthropicProvider(LLMProvider):
    """Provider adapter for Anthropic Messages API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        client: Optional[Any] = None,
    ):
        import anthropic

        if client is not None:
            self.client = client
            self.model = model or "claude-3-5-sonnet-latest"
            return

        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise LLMProviderError("Missing API key: ANTHROPIC_API_KEY is not configured.")

        self.model = model or os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
        try:
            self.client = anthropic.Anthropic(api_key=resolved_key)
        except Exception as exc:
            raise LLMProviderError(f"Failed to initialize Anthropic client: {exc}") from exc

    def send(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        """Send messages and optional tools to Anthropic Messages API."""
        logger.info("AnthropicProvider sending %d messages to model '%s'", len(messages), self.model)

        # Anthropic separates system prompt from conversation messages
        system_content = ""
        conversation = []
        for m in messages:
            if m.get("role") == "system":
                system_content = m.get("content", "")
            else:
                conversation.append(m)

        params: Dict[str, Any] = {
            "model": self.model,
            "messages": conversation,
            "max_tokens": 1024,
        }
        if system_content:
            params["system"] = system_content

        try:
            response = self.client.messages.create(**params)
            content_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    content_text += block.text

            return LLMResponse(
                content=content_text,
                tool_calls=None,
                raw_response=response,
            )
        except Exception as exc:
            logger.exception("AnthropicProvider request failed: %s", exc)
            raise LLMProviderError(f"AnthropicProvider error: {str(exc)}") from exc


def get_provider(
    provider_type: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> LLMProvider:
    """Factory to retrieve the appropriate configured LLM provider."""
    # Explicit provider choice
    if provider_type:
        ptype = provider_type.lower()
        if ptype in {"openai", "groq", "openai-compatible"}:
            return OpenAICompatibleProvider(api_key=api_key, base_url=base_url, model=model)
        elif ptype == "anthropic":
            return AnthropicProvider(api_key=api_key, model=model)
        raise ValueError(f"Unknown provider_type: '{provider_type}'")

    # Auto-detection from environment variables
    if os.environ.get("GROQ_API_KEY") or os.environ.get("OPENAI_API_KEY"):
        return OpenAICompatibleProvider(api_key=api_key, base_url=base_url, model=model)
    elif os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicProvider(api_key=api_key, model=model)

    # Fallback default: attempt OpenAICompatibleProvider
    return OpenAICompatibleProvider(api_key=api_key, base_url=base_url, model=model)


def run_query(user_query: str) -> str:
    """Execute a single query through the LLM assistant and return the final synthesized answer."""
    raise NotImplementedError("Phase 9 / Phase 11 implementation pending")


if __name__ == "__main__":
    print("LLM File System Assistant CLI (Phase 11 implementation pending)")
