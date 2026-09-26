# LLM-Powered File System Assistant

An intelligent file system assistant that combines safe, deterministic file-operation tools (`fs_tools.py`) with an LLM-based orchestration layer (`llm_file_assistant.py`) to manage, inspect, and analyze document repositories (such as resumes in PDF, TXT, and DOCX formats) using natural language.

---

## Project Structure

```text
fsAssistant/
├── fs_tools.py             # Pure-Python file operations (read, list, write, search)
├── llm_file_assistant.py   # LLM orchestration, schema registry, tool-call loop
├── resumes/                # Input resume files (.pdf, .txt, .docx)
├── output/                 # Generated reports and summaries
├── logs/                   # Application and tool-call execution logs
├── docs/                   # Specifications, architecture, and evaluations
│   ├── ProblemStatement.md
│   ├── architecture.md
│   ├── ImplementationPlan.md
│   └── evaluations.md
├── tests/                  # Automated pytest test suites
│   ├── fixtures/           # Sample fixtures for testing
│   ├── test_scaffolding.py
│   ├── test_fs_tools.py
│   └── test_llm_file_assistant.py
├── requirements.txt        # Python dependencies
└── README.md               # Setup and usage guide
```

---

## Getting Started

### 1. Prerequisites
- Python 3.10+
- Virtual environment recommended (`venv`)

### 2. Installation
```bash
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1    # Windows PowerShell
# source .venv/bin/activate     # macOS / Linux

# Install dependencies
pip install -r requirements.txt
```

### 3. Running Tests
```bash
# Run the fast unit test suite
pytest tests/ -v
```
