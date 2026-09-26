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


# ============================================================================
# Phase 8: Tool Schema Registry & Dispatcher
# ============================================================================

import fs_tools

TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read a document (.pdf, .txt, .docx) from the local filesystem and extract its text content and metadata."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the target document (e.g., 'resumes/john_doe.pdf').",
                    },
                },
                "required": ["filepath"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": (
                "Enumerate files in a directory on the local filesystem, optionally filtered by file extension."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Directory path to inspect (e.g., 'resumes', 'output').",
                    },
                    "extension": {
                        "type": "string",
                        "description": "Optional file extension to filter by (e.g., '.pdf', 'txt', 'docx').",
                    },
                },
                "required": ["directory"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Write text content to a file on the local filesystem, creating any missing parent directories automatically."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Target destination path (e.g., 'output/summary_john_doe.txt').",
                    },
                    "content": {
                        "type": "string",
                        "description": "The text content to write into the file.",
                    },
                },
                "required": ["filepath", "content"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_in_file",
            "description": (
                "Search for occurrences of a keyword or phrase within a document (.pdf, .txt, .docx) and return context snippets."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the document to search within.",
                    },
                    "keyword": {
                        "type": "string",
                        "description": "The keyword or phrase to search for (case-insensitive).",
                    },
                },
                "required": ["filepath", "keyword"],
                "additionalProperties": False,
            },
        },
    },
]

TOOL_REGISTRY: Dict[str, Any] = {
    "read_file": fs_tools.read_file,
    "list_files": fs_tools.list_files,
    "write_file": fs_tools.write_file,
    "search_in_file": fs_tools.search_in_file,
}

REQUIRED_TOOL_ARGS: Dict[str, List[str]] = {
    "read_file": ["filepath"],
    "list_files": ["directory"],
    "write_file": ["filepath", "content"],
    "search_in_file": ["filepath", "keyword"],
}


def get_tool_schemas() -> List[Dict[str, Any]]:
    """Return the registered tool schemas formatted for LLM function calling."""
    return TOOL_SCHEMAS


def serialize_tool_result(result: Any) -> str:
    """Serialize a tool execution result into a JSON string formatted for an LLM response."""
    return json.dumps(result, default=str)


def dispatch_tool_call(name: str, arguments: Dict[str, Any]) -> Any:
    """Validate and dispatch a tool call requested by an LLM to the underlying fs_tools function.

    Catches dispatch-level violations (unknown tool, missing arguments, invalid types)
    and returns structured error dictionaries suitable for LLM self-correction.

    Parameters:
        name (str): The name of the tool to invoke.
        arguments (Dict[str, Any]): Dictionary of arguments passed by the LLM.

    Returns:
        Any: Result dictionary/list returned by the tool, or a structured error dict on failure.
    """
    logger.info("Dispatching tool call: name='%s', args=%s", name, arguments)

    if not name or not isinstance(name, str):
        return {
            "success": False,
            "error": "Dispatch error: tool name must be a non-empty string.",
        }

    if name not in TOOL_REGISTRY:
        available = ", ".join(sorted(TOOL_REGISTRY.keys()))
        err = f"Unknown tool '{name}'. Available tools are: {available}."
        logger.warning("Dispatcher rejected tool name: %s", err)
        return {"success": False, "error": err}

    if not isinstance(arguments, dict):
        err = f"Dispatch error: arguments for '{name}' must be a dictionary, got {type(arguments).__name__}."
        logger.warning(err)
        return {"success": False, "error": err}

    # Validate required arguments
    required = REQUIRED_TOOL_ARGS.get(name, [])
    missing = [param for param in required if param not in arguments or arguments[param] is None]
    if missing:
        err = f"Missing required argument(s) for '{name}': {', '.join(missing)}."
        logger.warning("Dispatcher argument validation failed: %s", err)
        return {"success": False, "error": err}

    # Dispatch to tool function
    target_func = TOOL_REGISTRY[name]
    try:
        # Pass only accepted arguments to prevent unexpected kwargs
        import inspect
        sig = inspect.signature(target_func)
        valid_kwargs = {k: v for k, v in arguments.items() if k in sig.parameters}

        result = target_func(**valid_kwargs)
        return result

    except Exception as exc:
        err = f"Unexpected execution error during dispatch of '{name}': {str(exc)}"
        logger.exception(err)
        return {"success": False, "error": err}


DEFAULT_SYSTEM_PROMPT = """You are an intelligent, reliable File System Assistant specialized in analyzing and managing document repositories (such as resumes in PDF, TXT, and DOCX formats).

You have access to the following filesystem tools:
1. `list_files(directory, extension=None)`: Enumerate files in a directory.
2. `read_file(filepath)`: Extract text content and metadata from a .pdf, .txt, or .docx file.
3. `write_file(filepath, content)`: Persist generated text, reports, or summaries to disk.
4. `search_in_file(filepath, keyword)`: Locate keyword occurrences and context in a document.

Guidelines:
- When asked about files in a folder, inspect the folder first using `list_files`.
- Synthesize clear, human-readable answers from tool outputs.
- Never output raw unformatted JSON dumps unless explicitly requested by the user.
- If a tool reports an error (e.g., file not found), explain the issue helpfully.
"""


class Session:
    """Maintains multi-turn conversational message history for the file assistant."""

    def __init__(self, system_prompt: Optional[str] = None):
        self.system_prompt: str = system_prompt or DEFAULT_SYSTEM_PROMPT
        self.messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt}
        ]

    def clear(self) -> None:
        """Reset conversation history back to the initial system prompt."""
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def add_user_message(self, content: str) -> None:
        """Append a user message to the session history."""
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(
        self,
        content: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Append an assistant response (text or tool calls) to the session history."""
        msg: Dict[str, Any] = {"role": "assistant", "content": content}
        if tool_calls is not None:
            msg["tool_calls"] = tool_calls
        self.messages.append(msg)

    def add_tool_message(
        self, tool_call_id: str, name: str, content: str
    ) -> None:
        """Append a tool execution result to the session history."""
        self.messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": name,
                "content": content,
            }
        )


MAX_TOOL_ITERATIONS: int = int(os.environ.get("MAX_TOOL_ITERATIONS", 10))


def run_query(
    user_query: str,
    provider: Optional[LLMProvider] = None,
    system_prompt: Optional[str] = None,
    max_iterations: Optional[int] = None,
    session: Optional[Session] = None,
) -> str:
    """Execute a query through the LLM assistant using a multi-turn tool calling loop.

    Iterates until the LLM produces a final answer or reaches max_iterations.
    Supports chained sequential tool calls and parallel tool calls in a single turn.
    Maintains conversational context across turns if a Session instance is provided.

    Parameters:
        user_query (str): The natural language query from the user.
        provider (Optional[LLMProvider]): Specific provider adapter instance to use.
            If None, defaults to the environment-configured provider.
        system_prompt (Optional[str]): Custom system prompt to guide assistant behavior.
        max_iterations (Optional[int]): Maximum number of tool iterations before aborting.
        session (Optional[Session]): Optional Session object to preserve multi-turn history.

    Returns:
        str: Final natural language answer generated by the LLM.
    """
    if not user_query or not isinstance(user_query, str):
        return "Please provide a valid, non-empty query."

    active_provider = provider or get_provider()
    limit = max_iterations if max_iterations is not None else MAX_TOOL_ITERATIONS

    if session is not None:
        if not session.messages:
            session.messages.append(
                {
                    "role": "system",
                    "content": system_prompt or session.system_prompt or DEFAULT_SYSTEM_PROMPT,
                }
            )
        session.add_user_message(user_query)
        messages = session.messages
    else:
        prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_query},
        ]

    schemas = get_tool_schemas()
    logger.info("Starting tool-call loop for query: '%s' (max_iterations=%d)", user_query, limit)

    iteration = 0
    while iteration < limit:
        iteration += 1
        logger.info("Executing tool loop iteration %d/%d", iteration, limit)

        response = active_provider.send(messages=list(messages), tools=schemas)

        # If no tool calls requested, we have reached convergence / final answer
        if not response.has_tool_calls:
            logger.info("Loop converged on iteration %d with final answer.", iteration)
            final_content = response.content or ""
            if session is not None:
                session.add_assistant_message(content=final_content)
            return final_content

        assert response.tool_calls is not None
        logger.info(
            "Iteration %d: LLM requested %d tool call(s): %s",
            iteration,
            len(response.tool_calls),
            [tc.name for tc in response.tool_calls],
        )

        formatted_tool_calls = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.name,
                    "arguments": json.dumps(tc.arguments),
                },
            }
            for tc in response.tool_calls
        ]

        # Append assistant's tool-call request to message history
        if session is not None:
            session.add_assistant_message(
                content=response.content or None,
                tool_calls=formatted_tool_calls,
            )
        else:
            messages.append(
                {
                    "role": "assistant",
                    "content": response.content or None,
                    "tool_calls": formatted_tool_calls,
                }
            )

        # Dispatch each tool call and append results
        for tc in response.tool_calls:
            tool_result = dispatch_tool_call(tc.name, tc.arguments)
            serialized = serialize_tool_result(tool_result)
            if session is not None:
                session.add_tool_message(
                    tool_call_id=tc.id,
                    name=tc.name,
                    content=serialized,
                )
            else:
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tc.name,
                        "content": serialized,
                    }
                )

    # Cutoff guard reached
    cutoff_msg = (
        f"The assistant reached the maximum allowed tool iterations ({limit}) "
        "without completing the request. Please refine or break down your query."
    )
    logger.warning("Tool loop terminated: %s", cutoff_msg)
    if session is not None:
        session.add_assistant_message(content=cutoff_msg)
    return cutoff_msg


def run_cli() -> None:
    """Run the interactive Command Line Interface (CLI) REPL."""
    print("=" * 60)
    print("🤖 LLM File System Assistant CLI")
    print("Commands: 'exit' or 'quit' to terminate, 'clear' to reset history.")
    print("=" * 60)

    session = Session()

    while True:
        try:
            user_input = input("\nYou > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting. Goodbye!")
            break

        if not user_input:
            continue

        cmd = user_input.lower()
        if cmd in ("exit", "quit"):
            print("Goodbye!")
            break
        elif cmd == "clear":
            session.clear()
            print("Conversation history cleared.")
            continue

        print("\nAssistant > ", end="", flush=True)
        try:
            response = run_query(user_input, session=session)
            print(response)
        except Exception as exc:
            logger.exception("Error processing query in CLI")
            print(f"An error occurred: {exc}")


if __name__ == "__main__":
    run_cli()
