# Problem Statement: LLM-Powered File System Assistant

## 1. Overview

Build an intelligent file system assistant that combines a set of deterministic, well-tested file-operation tools with an LLM-based orchestration layer. The LLM interprets natural-language user queries, decides which tool(s) to invoke and with what arguments, executes them, and returns a coherent, human-readable response. The primary use case is helping a user manage and analyze a folder of resumes (PDF, TXT, DOCX), but the tools should be generic enough to operate on any text-bearing files.

The project consists of two deliverables:

1. **`fs_tools.py`** — a standalone Python module exposing four file-system tool functions.
2. **`llm_file_assistant.py`** — an orchestration layer that registers these tools with an LLM (OpenAI, Anthropic, or equivalent) using function/tool calling, routes user queries to the correct tool(s), and returns a final synthesized answer.

## 2. Goals

- Provide safe, reusable, well-documented file operations that can be called both programmatically and by an LLM via tool/function calling.
- Enable a conversational interface where a user can ask questions in plain English and have the assistant read, list, search, and write files on their behalf.
- Ensure robustness: the system should degrade gracefully on malformed files, missing paths, unsupported formats, and other real-world edge cases rather than crashing.
- Keep the tool layer LLM-agnostic so it can be wired into OpenAI function calling, Anthropic tool use, or any other framework with minimal changes.

## 3. Non-Goals

- Building a full-fledged resume parsing / ATS (Applicant Tracking System) with structured field extraction (name, skills, education, etc.) is out of scope, unless explicitly extended later.
- No persistent database or vector store is required; file content is read and processed on demand.
- No web UI is required; a CLI or simple script-driven interaction is sufficient.
- Authentication, multi-user access control, and networked/remote file systems are out of scope — the assistant operates on the local file system.

## 4. Scope

### 4.1 Module 1 — `fs_tools.py`

A pure-Python module with no LLM dependency, containing four tool functions. Each function must be independently unit-testable and safe to call directly outside of any LLM context.

#### 4.1.1 `read_file(filepath: str) -> dict`

**Purpose:** Read a resume (or any supported document) and extract its text content.

**Requirements:**
- Support at least three formats: `.pdf`, `.txt`, `.docx`.
- Auto-detect format from file extension; raise/return a clear error for unsupported extensions.
- Use appropriate libraries per format:
  - PDF: e.g. `pypdf` / `pdfplumber`.
  - DOCX: e.g. `python-docx`.
  - TXT: native file I/O with encoding detection/fallback (e.g. UTF-8, with a fallback for latin-1 or errors="replace").
- Extract full text content, preserving reasonable paragraph/line structure.
- Return a **structured dictionary**, for example:
  ```python
  {
      "success": True,
      "filepath": "resumes/john_doe.pdf",
      "filename": "john_doe.pdf",
      "extension": ".pdf",
      "content": "<extracted text>",
      "metadata": {
          "size_bytes": 45210,
          "num_pages": 2,          # PDF/DOCX only, where applicable
          "num_words": 812,
          "num_characters": 5230,
          "modified_time": "2025-01-10T14:32:00",
          "read_time": "2026-09-26T10:15:00"
      },
      "error": None
  }
  ```
- On failure (file not found, corrupt file, permission error, unsupported extension, empty file), return the same shape with `"success": False`, `"content": None`, and a descriptive `"error"` message — **never raise an unhandled exception**.

#### 4.1.2 `list_files(directory: str, extension: str = None) -> list`

**Purpose:** Enumerate files in a directory, optionally filtered by extension.

**Requirements:**
- Accept a directory path and an optional extension filter (e.g. `.pdf`, `.txt`, `.docx`; should tolerate input with or without the leading dot, and be case-insensitive).
- Return a list of dictionaries, one per matching file, each containing at least:
  ```python
  {
      "name": "john_doe.pdf",
      "filepath": "resumes/john_doe.pdf",
      "extension": ".pdf",
      "size_bytes": 45210,
      "modified_time": "2025-01-10T14:32:00"
  }
  ```
- Sort results in a predictable order (e.g. by name) for deterministic output.
- Handle non-existent directories, empty directories, and permission errors gracefully — return an empty list or a list containing a single error-descriptor entry (decide and document one consistent convention), never raise unhandled exceptions.
- Should not recurse into subdirectories by default (document this decision); optionally support a `recursive` flag as a stretch goal.

#### 4.1.3 `write_file(filepath: str, content: str) -> dict`

**Purpose:** Write text content to a file, creating any missing parent directories.

**Requirements:**
- Create intermediate directories automatically if they don't exist (`os.makedirs(..., exist_ok=True)` or equivalent).
- Overwrite existing files by default; document this behavior clearly (an `overwrite: bool` flag or automatic versioning/suffixing is a reasonable stretch enhancement).
- Return a structured status dictionary, e.g.:
  ```python
  {
      "success": True,
      "filepath": "output/summary_john_doe.txt",
      "bytes_written": 512,
      "error": None
  }
  ```
- Handle and report errors such as invalid paths, permission denied, or disk-full conditions without raising unhandled exceptions.

#### 4.1.4 `search_in_file(filepath: str, keyword: str) -> dict`

**Purpose:** Search for a keyword/phrase within a file's text content and return matches with surrounding context.

**Requirements:**
- Internally reuse `read_file` to extract content (so it supports PDF/TXT/DOCX transparently).
- Perform a **case-insensitive** search for the keyword.
- For each match, return a context window (e.g. N characters or the full sentence/line before and after the match) so the user can see how the keyword is used.
- Return a structured result, e.g.:
  ```python
  {
      "success": True,
      "filepath": "resumes/john_doe.pdf",
      "keyword": "python",
      "match_count": 3,
      "matches": [
          {"context": "...5 years of experience with Python and Django...", "position": 214},
          {"context": "...built internal tools using Python scripts...", "position": 980}
      ],
      "error": None
  }
  ```
- Handle the "file unreadable" and "keyword not found" cases explicitly (`match_count: 0`, empty `matches` list, `success: True` since the operation itself succeeded).

### 4.2 Module 2 — `llm_file_assistant.py`

**Purpose:** Wire the four tools above into an LLM using tool/function calling so a user can interact via natural language.

**Requirements:**

1. **LLM Integration**
   - Support at least one LLM provider (OpenAI or Anthropic) via its native tool-calling / function-calling API; design the integration so swapping providers requires minimal changes (e.g. an abstraction layer or clearly isolated provider-specific code).
   - Define a tool/function schema (name, description, parameters with types) for each of the four `fs_tools` functions, following the target provider's expected schema format (OpenAI `tools` / Anthropic `tools` JSON schema).

2. **Orchestration Loop**
   - Accept a natural-language user query as input.
   - Send the query plus tool definitions to the LLM.
   - Parse the LLM's tool-call response(s), execute the corresponding Python function(s) from `fs_tools.py` with the LLM-provided arguments.
   - Feed tool results back to the LLM so it can reason over them (supporting multi-turn / multi-tool-call chains where the LLM may need to call a tool, inspect results, then call another tool).
   - Return a final, synthesized, human-readable answer to the user (not raw JSON dumps).

3. **Example Query Behaviors** (must work end-to-end):
   - **"Read all resumes in the resumes folder"** → calls `list_files("resumes")`, then calls `read_file` for each returned file, then summarizes/confirms what was read.
   - **"Find resumes mentioning Python experience"** → calls `list_files("resumes")`, then `search_in_file(filepath, "Python")` (or `read_file` + in-memory search) for each file, and reports which resumes matched, with brief context snippets.
   - **"Create a summary file for resume_john_doe.pdf"** → calls `read_file` on the target resume, has the LLM generate a summary from the extracted content, then calls `write_file` to persist the summary (e.g. to `summary_resume_john_doe.txt`), and confirms success to the user.

4. **Conversation/Session Handling**
   - Maintain message history within a single session so follow-up queries can reference prior context (e.g. "now do the same for the second one").
   - Provide a simple entry point: either a CLI loop (`while True: input(...)`) or a function `run_query(user_query: str) -> str` that can be called programmatically or wrapped by a UI later.

5. **Prompting / System Instructions**
   - Include a system prompt that describes the assistant's purpose, the tools available, and guidance on when to use each tool (e.g. always list files before reading an entire folder; always confirm before overwriting a file, if that policy is adopted).

## 5. Functional Requirements Summary

| # | Requirement | Priority |
|---|-------------|----------|
| 1 | `read_file` supports PDF, TXT, DOCX with structured output | Must |
| 2 | `read_file` handles errors gracefully (no unhandled exceptions) | Must |
| 3 | `list_files` filters by extension and returns metadata | Must |
| 4 | `write_file` auto-creates directories and reports status | Must |
| 5 | `search_in_file` is case-insensitive and returns contextual matches | Must |
| 6 | Tools are exposed to an LLM via function/tool calling | Must |
| 7 | LLM can chain multiple tool calls to satisfy a single query | Must |
| 8 | Assistant produces natural-language, synthesized final answers | Must |
| 9 | Support for at least one LLM provider (OpenAI/Anthropic) | Must |
| 10 | Multi-turn conversation/session support | Should |
| 11 | Recursive directory listing | Could |
| 12 | Overwrite protection / file versioning on write | Could |
| 13 | Support for additional file types (e.g. `.rtf`, `.md`, `.html`) | Could |

## 6. Non-Functional Requirements

- **Robustness:** No tool function should ever raise an unhandled exception; all errors are caught and returned in the structured response.
- **Modularity:** `fs_tools.py` must have zero dependency on any LLM SDK, so it can be tested, reused, or swapped independently of the LLM layer.
- **Testability:** Each tool function should be unit-testable in isolation with sample fixture files (sample PDF/DOCX/TXT resumes).
- **Extensibility:** Adding a new tool (e.g. `delete_file`, `rename_file`) should require only (a) a new function in `fs_tools.py` and (b) a new schema entry/registration in `llm_file_assistant.py`.
- **Security:** Validate/sanitize file paths to avoid path traversal outside intended working directories; avoid executing arbitrary code from file content.
- **Performance:** Reading and searching should handle typical resume-sized documents (a few pages) in well under a second; directory listings should handle folders with hundreds of files without noticeable delay.
- **Logging:** Provide basic logging (tool name, arguments, success/failure) for observability and debugging of the LLM's tool-use decisions.

## 7. Suggested Tool Schema (Example — OpenAI-style)

```json
{
  "name": "read_file",
  "description": "Read a resume file (PDF, TXT, or DOCX) and return its extracted text content along with metadata.",
  "parameters": {
    "type": "object",
    "properties": {
      "filepath": {
        "type": "string",
        "description": "Path to the file to read."
      }
    },
    "required": ["filepath"]
  }
}
```

Analogous schemas should be defined for `list_files`, `write_file`, and `search_in_file`.

## 8. Assumptions

- The assistant runs in a trusted local environment where the user has legitimate access to the target directories/files.
- Resume files are reasonably well-formed (not password-protected or intentionally obfuscated).
- An API key for the chosen LLM provider is available via environment variable or config file.
- "Summary" generation quality depends on the underlying LLM and is not separately validated beyond "a summary file is created with non-empty, relevant content."

## 9. Deliverables

1. `fs_tools.py` — implementation of the four tool functions with docstrings and inline error handling.
2. `llm_file_assistant.py` — LLM orchestration layer with tool registration, execution loop, and an example CLI or `run_query()` entry point.
3. (Recommended) A `requirements.txt` listing dependencies (e.g. `pypdf`, `python-docx`, `openai` or `anthropic`).
4. (Recommended) A small set of sample resume files (`.pdf`, `.txt`, `.docx`) in a `resumes/` folder for manual/automated testing.
5. (Recommended) Basic unit tests for `fs_tools.py`.

## 10. Success Criteria

- All three example queries in Section 4.2.3 produce correct, sensible end-to-end results when run against a sample `resumes/` folder.
- No tool call crashes the process on bad input (missing file, wrong extension, empty directory, etc.).
- The LLM correctly selects and sequences tool calls without hardcoded query-to-tool mapping (i.e., genuine LLM-driven tool selection, not a simple keyword `if/else` router).
- Code is readable, documented, and organized into the two specified modules with a clean separation of concerns (tools vs. orchestration).