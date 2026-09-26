"""
File System Tools for LLM-Powered File System Assistant.

This module provides pure, synchronous, dependency-light Python functions
for interacting with the local file system. It is LLM-agnostic and does not
import or depend on any LLM provider SDKs.

Tools provided:
    - read_file(filepath: str) -> dict
    - list_files(directory: str, extension: Optional[str] = None) -> list
    - write_file(filepath: str, content: str) -> dict
    - search_in_file(filepath: str, keyword: str) -> dict
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

import docx
import pypdf

SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx"}


def _read_txt(path: Path) -> Tuple[str, Optional[int]]:
    """Read a .txt file with UTF-8 encoding and latin-1 fallback."""
    raw_bytes = path.read_bytes()
    try:
        content = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        content = raw_bytes.decode("latin-1", errors="replace")
    return content, None


def _read_pdf(path: Path) -> Tuple[str, Optional[int]]:
    """Read a .pdf file and extract text and page count using pypdf."""
    reader = pypdf.PdfReader(str(path))
    if reader.is_encrypted:
        try:
            # Attempt decrypt with empty password for unauthenticated encrypted PDFs
            reader.decrypt("")
        except Exception as exc:
            raise ValueError(f"Encrypted/password-protected PDF: {exc}") from exc

    pages_text = []
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            pages_text.append(extracted)
    content = "\n".join(pages_text)
    num_pages = len(reader.pages)
    return content, num_pages


def _read_docx(path: Path) -> Tuple[str, Optional[int]]:
    """Read a .docx file and extract text from paragraphs and tables using python-docx."""
    doc = docx.Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    table_rows = []
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_text:
                table_rows.append(row_text)

    all_parts = paragraphs + table_rows
    content = "\n".join(all_parts)
    return content, None


def read_file(filepath: str) -> Dict[str, Any]:
    """Read a document (.txt, .pdf, .docx) and return its extracted text content and metadata.

    Parameters:
        filepath (str): Relative or absolute path to the target file.

    Returns:
        dict: Structured dictionary containing:
            - success (bool): True if reading succeeded, False otherwise.
            - filepath (str): Original path provided.
            - filename (str): Name of the file with extension.
            - extension (str): Lowercase file extension (e.g., '.txt', '.pdf', '.docx').
            - content (Optional[str]): Extracted text content, or None on failure.
            - metadata (Optional[dict]): File statistics including size, page count,
              word count, character count, modified time, and read time. None on failure.
            - error (Optional[str]): Error description if failed, None if successful.
    """
    if not filepath or not isinstance(filepath, str):
        return {
            "success": False,
            "filepath": str(filepath) if filepath is not None else "",
            "filename": "",
            "extension": "",
            "content": None,
            "metadata": None,
            "error": "Invalid filepath: filepath must be a non-empty string.",
        }

    path = Path(filepath)
    filename = path.name
    extension = path.suffix.lower()

    try:
        if not path.exists():
            return {
                "success": False,
                "filepath": filepath,
                "filename": filename,
                "extension": extension,
                "content": None,
                "metadata": None,
                "error": f"File not found: '{filepath}'.",
            }

        if path.is_dir():
            return {
                "success": False,
                "filepath": filepath,
                "filename": filename,
                "extension": extension,
                "content": None,
                "metadata": None,
                "error": f"Path is a directory, not a file: '{filepath}'.",
            }

        if extension not in SUPPORTED_EXTENSIONS:
            return {
                "success": False,
                "filepath": filepath,
                "filename": filename,
                "extension": extension,
                "content": None,
                "metadata": None,
                "error": (
                    f"Unsupported file extension '{extension}'. "
                    f"Supported formats are: {', '.join(sorted(SUPPORTED_EXTENSIONS))}."
                ),
            }

        # Extract content and page count based on format
        if extension == ".txt":
            content, num_pages = _read_txt(path)
        elif extension == ".pdf":
            content, num_pages = _read_pdf(path)
        elif extension == ".docx":
            content, num_pages = _read_docx(path)
        else:
            raise ValueError(f"Unhandled extension: {extension}")

        stat = path.stat()
        num_characters = len(content)
        num_words = len(content.split()) if content else 0

        metadata = {
            "size_bytes": stat.st_size,
            "num_pages": num_pages,
            "num_words": num_words,
            "num_characters": num_characters,
            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "read_time": datetime.now().isoformat(),
        }

        return {
            "success": True,
            "filepath": filepath,
            "filename": filename,
            "extension": extension,
            "content": content,
            "metadata": metadata,
            "error": None,
        }

    except Exception as exc:
        return {
            "success": False,
            "filepath": filepath,
            "filename": filename,
            "extension": extension,
            "content": None,
            "metadata": None,
            "error": f"Error reading file '{filepath}': {str(exc)}",
        }


def list_files(directory: str, extension: Optional[str] = None) -> List[Dict[str, Any]]:
    """List files in the specified directory, optionally filtered by extension.

    Parameters:
        directory (str): Path to the target directory.
        extension (Optional[str]): Optional file extension to filter by (e.g. '.pdf', 'txt', 'DOCX').
            Case-insensitive and tolerates with or without leading dot.

    Returns:
        List[Dict[str, Any]]: Deterministically sorted list of dictionaries for matching files.
            Each dictionary contains:
                - name (str): File name including extension.
                - filepath (str): Path to the file.
                - extension (str): Lowercase file extension (e.g. '.pdf').
                - size_bytes (int): Size of the file in bytes.
                - modified_time (str): Last modified timestamp in ISO 8601 format.
            Returns an empty list if directory is missing, empty, invalid, or inaccessible.
    """
    if not directory or not isinstance(directory, str):
        return []

    dir_path = Path(directory)

    try:
        if not dir_path.exists() or not dir_path.is_dir():
            return []

        target_ext = None
        if extension is not None:
            if not isinstance(extension, str):
                return []
            clean_ext = extension.strip().lower()
            if clean_ext:
                target_ext = clean_ext if clean_ext.startswith(".") else f".{clean_ext}"

        matched_files: List[Dict[str, Any]] = []

        for item in dir_path.iterdir():
            # Skip subdirectories, non-files, and hidden files (starting with '.')
            if not item.is_file() or item.name.startswith("."):
                continue

            item_ext = item.suffix.lower()
            if target_ext is not None and item_ext != target_ext:
                continue

            stat = item.stat()
            rel_or_full = str(dir_path / item.name).replace("\\", "/")

            matched_files.append(
                {
                    "name": item.name,
                    "filepath": rel_or_full,
                    "extension": item_ext,
                    "size_bytes": stat.st_size,
                    "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
            )

        # Deterministically sort alphabetically by filename
        matched_files.sort(key=lambda x: x["name"].lower())
        return matched_files

    except Exception:
        return []


def write_file(filepath: str, content: str) -> Dict[str, Any]:
    """Write text content to a file, creating any missing parent directories.

    Overwrites existing files by default. Encodes all written text using UTF-8.

    Parameters:
        filepath (str): Path where the file should be written.
        content (str): Text content to write into the file.

    Returns:
        Dict[str, Any]: Structured status dictionary containing:
            - success (bool): True if write succeeded, False otherwise.
            - filepath (str): Original target path.
            - bytes_written (int): Number of UTF-8 encoded bytes written to disk.
            - error (Optional[str]): Error description if failed, None if successful.
    """
    if not filepath or not isinstance(filepath, str):
        return {
            "success": False,
            "filepath": str(filepath) if filepath is not None else "",
            "bytes_written": 0,
            "error": "Invalid filepath: filepath must be a non-empty string.",
        }

    if not isinstance(content, str):
        return {
            "success": False,
            "filepath": filepath,
            "bytes_written": 0,
            "error": "Invalid content: content must be a string.",
        }

    try:
        path = Path(filepath)

        if path.exists() and path.is_dir():
            return {
                "success": False,
                "filepath": filepath,
                "bytes_written": 0,
                "error": f"Target path '{filepath}' is an existing directory.",
            }

        # Auto-create intermediate parent directories if missing
        if path.parent and not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)

        encoded_bytes = content.encode("utf-8")
        path.write_bytes(encoded_bytes)

        return {
            "success": True,
            "filepath": filepath,
            "bytes_written": len(encoded_bytes),
            "error": None,
        }

    except Exception as exc:
        return {
            "success": False,
            "filepath": filepath,
            "bytes_written": 0,
            "error": f"Error writing file '{filepath}': {str(exc)}",
        }


def _extract_snippet(line: str, keyword: str, window: int = 50) -> str:
    """Extract a concise context snippet around the keyword match."""
    line_clean = line.strip()
    idx = line_clean.lower().find(keyword.lower())
    if idx == -1 or len(line_clean) <= 140:
        return line_clean

    start = max(0, idx - window)
    end = min(len(line_clean), idx + len(keyword) + window)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(line_clean) else ""
    return f"{prefix}{line_clean[start:end]}{suffix}"


def search_in_file(filepath: str, keyword: str) -> Dict[str, Any]:
    """Search for occurrences of a keyword within a file and return context snippets.

    Case-insensitive by default. Automatically handles .txt, .pdf, and .docx formats
    by delegating file extraction to read_file().

    Parameters:
        filepath (str): Path to the target file.
        keyword (str): The keyword or phrase to search for.

    Returns:
        Dict[str, Any]: Structured dictionary containing:
            - success (bool): True if file was read and searched, False if read failed.
            - filepath (str): Original target path.
            - keyword (str): Original keyword queried.
            - match_count (int): Total number of lines containing the keyword.
            - matches (List[Dict[str, Any]]): List of match entries with line_number and context.
            - error (Optional[str]): Error description if reading or input failed, None on success.
    """
    if not filepath or not isinstance(filepath, str):
        return {
            "success": False,
            "filepath": str(filepath) if filepath is not None else "",
            "keyword": str(keyword) if keyword is not None else "",
            "match_count": 0,
            "matches": [],
            "error": "Invalid filepath: filepath must be a non-empty string.",
        }

    if not keyword or not isinstance(keyword, str) or not keyword.strip():
        return {
            "success": False,
            "filepath": filepath,
            "keyword": str(keyword) if keyword is not None else "",
            "match_count": 0,
            "matches": [],
            "error": "Invalid keyword: keyword must be a non-empty string.",
        }

    try:
        read_res = read_file(filepath)
        if not read_res.get("success"):
            return {
                "success": False,
                "filepath": filepath,
                "keyword": keyword,
                "match_count": 0,
                "matches": [],
                "error": read_res.get("error", f"Failed to read file '{filepath}'"),
            }

        content = read_res.get("content") or ""
        clean_keyword = keyword.strip()
        keyword_lower = clean_keyword.lower()

        matches: List[Dict[str, Any]] = []
        for line_idx, line in enumerate(content.splitlines(), start=1):
            if keyword_lower in line.lower():
                matches.append(
                    {
                        "line_number": line_idx,
                        "context": _extract_snippet(line, clean_keyword),
                    }
                )

        return {
            "success": True,
            "filepath": filepath,
            "keyword": keyword,
            "match_count": len(matches),
            "matches": matches,
            "error": None,
        }

    except Exception as exc:
        return {
            "success": False,
            "filepath": filepath,
            "keyword": keyword,
            "match_count": 0,
            "matches": [],
            "error": f"Error searching in file '{filepath}': {str(exc)}",
        }
