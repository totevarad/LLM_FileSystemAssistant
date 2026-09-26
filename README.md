# LLM File System Assistant 🤖📂

An intelligent, multi-format file system assistant that combines safe, sandboxed file-operation tools (`fs_tools.py`) with an autonomous LLM orchestration layer (`llm_file_assistant.py`) to inspect, analyze, search, and synthesize document repositories (such as PDF, DOCX, and TXT resumes) using natural language.

---

## 🌟 Key Features

- **Multi-Format Document Parsing**: Safe in-process extraction of text and metadata from `.pdf` (via `pypdf`), `.docx` (via `python-docx`), and plain `.txt` files with non-UTF-8 encoding fallback.
- **Strict Decoupling**: Pure file tools (`fs_tools.py`) have **zero dependencies** on LLM SDKs or network access, making them independently testable, fast, and secure.
- **Path Traversal Sandboxing**: All operations are restricted to a configurable base directory (`FS_BASE_DIR`), rejecting relative `../` escapes and drive-jumping attacks.
- **Pluggable LLM Provider Adapter**: Native tool-calling support for **Groq**, **OpenAI**, and **Anthropic** via a unified `LLMProvider` abstraction.
- **Multi-Tool Autonomous Loop**: General-purpose tool loop bounded by `MAX_TOOL_ITERATIONS` supporting sequential tool chaining, parallel tool calls per turn, and graceful error recovery.
- **Conversational Memory & REPL**: `Session` state tracks dialogue history across turns, accessible via both an interactive CLI REPL and a programmatic Python API.
- **Structured Audit Logging**: Every tool dispatch records duration, arguments, success status, and timestamps to `logs/app.log`.

---

## 🏗️ Repository Layout

```text
LLM_FileSystemAssistant/
├── fs_tools.py                 # Core file tools (read_file, list_files, write_file, search_in_file)
├── llm_file_assistant.py       # Orchestration layer, provider adapters, tool loop, Session, CLI
├── requirements.txt            # Strictly pinned production dependencies
├── pytest.ini                  # Pytest configuration and marker definitions
├── .env.example                # Template for environment configuration
├── resumes/                    # Sample resume document repository (.txt, .pdf, .docx)
├── output/                     # Destination directory for generated summaries and reports
├── logs/                       # Application execution and tool audit logs (app.log)
├── docs/                       # Specifications and architecture docs
│   ├── ProblemStatement.md
│   ├── architecture.md
│   ├── ImplementationPlan.md
│   └── evaluations.md
└── tests/                      # Automated test suite
    ├── fixtures/               # Test fixtures (valid, empty, corrupt, and non-UTF8 files)
    ├── test_scaffolding.py     # Environment and fixture smoke tests
    ├── test_fs_tools.py        # Comprehensive tool layer contract and edge-case tests
    ├── test_llm_file_assistant.py # Provider, schema, loop, session, and CLI tests
    └── test_e2e_scenarios.py   # Live E2E tests validating the 3 canonical queries
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10 to 3.14
- Git

### 2. Installation
Clone the repository and set up a virtual environment:

```bash
git clone https://github.com/totevarad/LLM_FileSystemAssistant.git
cd LLM_FileSystemAssistant

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

# Install strictly pinned dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env` (or create `.env`) and supply your API key:

```env
# Provider Selection (openai, groq, anthropic)
LLM_PROVIDER=openai

# Model Selection
# Groq Example:
GROQ_API_KEY=gsk_your_groq_api_key_here
OPENAI_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-120b

# OpenAI Example:
# OPENAI_API_KEY=sk-proj-your_key_here
# LLM_MODEL=gpt-4o

# Anthropic Example:
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-your_key_here
# LLM_MODEL=claude-3-5-sonnet-20241022

# Operational Settings
MAX_TOOL_ITERATIONS=10
FS_BASE_DIR=.
```

---

## 💻 Usage

### 1. Interactive CLI REPL
Launch the assistant in interactive conversation mode:

```bash
python llm_file_assistant.py
```

**Commands available in REPL:**
- `exit` or `quit`: Terminate the assistant.
- `clear`: Reset conversation history and start a fresh session.

**Sample CLI Session:**
```text
============================================================
🤖 LLM File System Assistant CLI
Commands: 'exit' or 'quit' to terminate, 'clear' to reset history.
============================================================

You > Read all the resumes in the resumes folder and give me a brief summary of each candidate.

Assistant > I found 3 candidate resumes in the 'resumes' directory:
1. John Doe (sample.txt): Senior Backend Engineer with 6+ years in Python, FastAPI, and AWS.
2. Jane Smith (sample.docx): Senior Machine Learning Engineer specializing in Computer Vision and PyTorch.
3. Alex Johnson (sample.pdf): DevOps Engineer skilled in Kubernetes, Terraform, and CI/CD pipelines.

You > Tell me more about the first candidate's work at Acme Tech.

Assistant > At Acme Tech Solutions (2021–Present), John Doe architected microservices handling 50M+ requests daily and reduced database query latency by 40% with Redis caching.
```

### 2. Programmatic Python API
Use the assistant directly as a Python library:

```python
from llm_file_assistant import run_query, Session

# 1. Stateless one-off query
response = run_query("Find all resumes that mention Python and tell me where they worked.")
print(response)

# 2. Multi-turn conversation preserving context
session = Session()
ans1 = run_query("List files in resumes folder", session=session)
ans2 = run_query("Create a summary of John Doe's resume and save it to output/summary_john_doe.txt.", session=session)
```

---

## 🛠️ Tool Layer Specification (`fs_tools.py`)

All tool functions return standard Python dictionaries or lists and never raise unhandled exceptions:

| Tool | Signature | Return Schema | Description |
|---|---|---|---|
| `read_file` | `(filepath: str)` | `{"success", "filepath", "filename", "extension", "content", "metadata", "error"}` | Extracts text and metadata (`page_count`, `author`, `created_date`, `modified_date`, `file_size_bytes`). |
| `list_files` | `(directory: str, extension: Optional[str] = None)` | `List[{"name", "filepath", "extension", "size", "modified_time"}]` | Enumerates files, filtered by extension, sorted deterministically. |
| `write_file` | `(filepath: str, content: str)` | `{"success", "filepath", "bytes_written", "error"}` | Atomically creates missing parent directories and writes UTF-8 content. |
| `search_in_file` | `(filepath: str, keyword: str)` | `{"success", "filepath", "keyword", "match_count", "matches", "error"}` | Performs case-insensitive search returning ±50 character context snippets. |

---

## 🧪 Testing & Verification

The test suite follows the Testing Pyramid: fast unit tests run locally offline without cost or API keys, while live integration tests validate real end-to-end LLM behavior.

### Fast Unit Tests (Offline / CI)
Executes 103 unit tests validating tool sandboxing, provider schemas, loop control, session state, and error handling in ~3 seconds:

```bash
pytest tests/ -m "not integration" -v
```

### Live End-to-End Scenarios (Requires API Key)
Executes the three canonical real-world scenarios from `ProblemStatement.md` against the configured LLM:

```bash
pytest tests/test_e2e_scenarios.py -m integration -v -s
```

**Scenarios Validated:**
1. `test_e2e_scenario1_read_all_resumes`: Discovers all files and extracts candidate summaries.
2. `test_e2e_scenario2_find_python_resumes`: Discovers, searches, and extracts past employment details.
3. `test_e2e_scenario3_create_summary_file`: Reads resume, generates summary, and persists it via `write_file` to `output/summary_john_doe.txt`.

---

## 📊 Structured Audit Logging

All system operations and tool invocations are logged with millisecond execution timing in `logs/app.log`:

```text
2026-09-26 16:04:30 [INFO] [llm_file_assistant] tool_call: name='list_files' success=True duration_ms=1.20 args={'directory': 'resumes'}
2026-09-26 16:04:31 [INFO] [llm_file_assistant] tool_call: name='read_file' success=True duration_ms=4.85 args={'filepath': 'resumes/sample.txt'}
```

---

## 🛡️ License

MIT License. Designed for safe, transparent, and autonomous file management.
