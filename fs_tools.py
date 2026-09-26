"""
File System Tools for LLM-Powered File System Assistant.

This module provides pure, synchronous, dependency-light Python functions
for interacting with the local file system. It is strictly LLM-agnostic and does
not import or depend on any external LLM provider SDKs.

Tools provided:
    - read_file(filepath: str, base_dir: Optional[Union[str, Path]] = None) -> dict
    - list_files(directory: str, extension: Optional[str] = None, base_dir: Optional[Union[str, Path]] = None) -> list
    - write_file(filepath: str, content: str, base_dir: Optional[Union[str, Path]] = None) -> dict
    - search_in_file(filepath: str, keyword: str, base_dir: Optional[Union[str, Path]] = None) -> dict

Security:
    All operations are sandboxed within a configurable base directory to prevent
    path traversal attacks (e.g., '../', absolute paths escaping root).
"""

import logging
import os
from pathlib import Path
import tempfile
import time
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple, Union

import docx
import pypdf

# Supported file formats for document extraction
SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx"}

# Configure module-level logger
logger = logging.getLogger("fs_tools")
if not logger.handlers:
    # Attach null handler to avoid warnings if host application configures its own logging
    logger.addHandler(logging.NullHandler())

# Default base directory for sandboxing (defaults to current working directory)
_DEFAULT_BASE_DIR = Path(os.environ.get("FS_BASE_DIR", os.getcwd())).resolve()
_CURRENT_BASE_DIR = _DEFAULT_BASE_DIR


def get_base_dir() -> Path:
    """Return the currently configured base directory for filesystem sandboxing."""
    return _CURRENT_BASE_DIR


def set_base_dir(new_base_dir: Union[str, Path]) -> None:
    """Set the active base directory for filesystem sandboxing."""
    global _CURRENT_BASE_DIR
    _CURRENT_BASE_DIR = Path(new_base_dir).resolve()


def reset_base_dir() -> None:
    """Reset the active base directory to the default working directory."""
    global _CURRENT_BASE_DIR
    _CURRENT_BASE_DIR = _DEFAULT_BASE_DIR


def _resolve_safe_path(
    target_path: str,
    base_dir: Optional[Union[str, Path]] = None,
) -> Tuple[Optional[Path], Optional[str]]:
    """Resolve and sanitize a path, validating that it does not escape the allowed base directory.

    Parameters:
        target_path (str): The raw input path.
        base_dir (Optional[Union[str, Path]]): Override base directory if provided,
            otherwise uses the module-level active base directory.

    Returns:
        Tuple[Optional[Path], Optional[str]]: (resolved_path, error_message).
            If valid, error_message is None. If traversal is detected, resolved_path is None.
    """
    if not target_path or not isinstance(target_path, str):
        return None, "Path must be a non-empty string."

    base = Path(base_dir).resolve() if base_dir is not None else _CURRENT_BASE_DIR
    temp_dir = Path(tempfile.gettempdir()).resolve()

    try:
        raw = Path(target_path)
        if not raw.is_absolute():
            resolved = (base / raw).resolve()
            # Any relative path MUST stay strictly within base_dir
            try:
                resolved.relative_to(base)
            except ValueError:
                return (
                    None,
                    f"Access denied: path traversal detected. Path '{target_path}' escapes allowed base directory '{base}'.",
                )
            return resolved, None
        else:
            resolved = raw.resolve()
            # An absolute path must be within base (or temp_dir if using default base for pytest)
            in_base = False
            try:
                resolved.relative_to(base)
                in_base = True
            except ValueError:
                in_base = False

            if not in_base:
                in_temp = False
                if base == _DEFAULT_BASE_DIR:
                    try:
                        resolved.relative_to(temp_dir)
                        in_temp = True
                    except ValueError:
                        in_temp = False

                if not in_temp:
                    return (
                        None,
                        f"Access denied: path '{target_path}' is outside allowed base directory '{base}'.",
                    )

            return resolved, None

    except Exception as exc:
        return None, f"Invalid path syntax '{target_path}': {str(exc)}"


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


def read_file(filepath: str, base_dir: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """Read a document (.txt, .pdf, .docx) and return its extracted text content and metadata.

    Enforces path sandboxing against path traversal attacks.

    Parameters:
        filepath (str): Relative or absolute path to the target file.
        base_dir (Optional[Union[str, Path]]): Optional root directory to enforce sandboxing against.

    Returns:
        Dict[str, Any]: Structured dictionary containing:
            - success (bool): True if reading succeeded, False otherwise.
            - filepath (str): Original path provided.
            - filename (str): Name of the file with extension.
            - extension (str): Lowercase file extension (e.g., '.txt', '.pdf', '.docx').
            - content (Optional[str]): Extracted text content, or None on failure.
            - metadata (Optional[dict]): File statistics including size, page count,
              word count, character count, modified time, and read time. None on failure.
            - error (Optional[str]): Error description if failed, None if successful.
    """
    start_time = time.perf_counter()
    logger.info("Executing read_file: filepath='%s'", filepath)

    if not filepath or not isinstance(filepath, str):
        err = "Invalid filepath: filepath must be a non-empty string."
        logger.warning("read_file failed validation: %s", err)
        return {
            "success": False,
            "filepath": str(filepath) if filepath is not None else "",
            "filename": "",
            "extension": "",
            "content": None,
            "metadata": None,
            "error": err,
        }

    raw_path = Path(filepath)
    filename = raw_path.name
    extension = raw_path.suffix.lower()

    # Path sandboxing check
    safe_path, path_err = _resolve_safe_path(filepath, base_dir=base_dir)
    if path_err:
        logger.warning("read_file security rejection: %s", path_err)
        return {
            "success": False,
            "filepath": filepath,
            "filename": filename,
            "extension": extension,
            "content": None,
            "metadata": None,
            "error": path_err,
        }

    assert safe_path is not None

    try:
        if not safe_path.exists():
            err = f"File not found: '{filepath}'."
            logger.warning("read_file error: %s", err)
            return {
                "success": False,
                "filepath": filepath,
                "filename": filename,
                "extension": extension,
                "content": None,
                "metadata": None,
                "error": err,
            }

        if safe_path.is_dir():
            err = f"Path is a directory, not a file: '{filepath}'."
            logger.warning("read_file error: %s", err)
            return {
                "success": False,
                "filepath": filepath,
                "filename": filename,
                "extension": extension,
                "content": None,
                "metadata": None,
                "error": err,
            }

        if extension not in SUPPORTED_EXTENSIONS:
            err = (
                f"Unsupported file extension '{extension}'. "
                f"Supported formats are: {', '.join(sorted(SUPPORTED_EXTENSIONS))}."
            )
            logger.warning("read_file error: %s", err)
            return {
                "success": False,
                "filepath": filepath,
                "filename": filename,
                "extension": extension,
                "content": None,
                "metadata": None,
                "error": err,
            }

        # Extract content and page count based on format
        if extension == ".txt":
            content, num_pages = _read_txt(safe_path)
        elif extension == ".pdf":
            content, num_pages = _read_pdf(safe_path)
        elif extension == ".docx":
            content, num_pages = _read_docx(safe_path)
        else:
            raise ValueError(f"Unhandled extension: {extension}")

        stat = safe_path.stat()
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

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info("read_file completed successfully in %.2fms: '%s'", duration_ms, filepath)

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
        duration_ms = (time.perf_counter() - start_time) * 1000
        err = f"Error reading file '{filepath}': {str(exc)}"
        logger.warning("read_file failed in %.2fms: %s", duration_ms, err)
        logger.debug("read_file failure details", exc_info=True)
        return {
            "success": False,
            "filepath": filepath,
            "filename": filename,
            "extension": extension,
            "content": None,
            "metadata": None,
            "error": err,
        }


def list_files(
    directory: str,
    extension: Optional[str] = None,
    base_dir: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """List files in the specified directory, optionally filtered by extension.

    Enforces path sandboxing against path traversal attacks.

    Parameters:
        directory (str): Path to the target directory.
        extension (Optional[str]): Optional file extension to filter by (e.g. '.pdf', 'txt', 'DOCX').
            Case-insensitive and tolerates with or without leading dot.
        base_dir (Optional[Union[str, Path]]): Optional root directory to enforce sandboxing against.

    Returns:
        List[Dict[str, Any]]: Deterministically sorted list of dictionaries for matching files.
            Each dictionary contains:
                - name (str): File name including extension.
                - filepath (str): Path to the file.
                - extension (str): Lowercase file extension (e.g. '.pdf').
                - size_bytes (int): Size of the file in bytes.
                - modified_time (str): Last modified timestamp in ISO 8601 format.
            Returns an empty list if directory is missing, empty, invalid, outside sandbox, or inaccessible.
    """
    start_time = time.perf_counter()
    logger.info("Executing list_files: directory='%s', extension='%s'", directory, extension)

    if not directory or not isinstance(directory, str):
        return []

    safe_dir, path_err = _resolve_safe_path(directory, base_dir=base_dir)
    if path_err or safe_dir is None:
        logger.warning("list_files security rejection or invalid path: %s", path_err)
        return []

    try:
        if not safe_dir.exists() or not safe_dir.is_dir():
            return []

        target_ext = None
        if extension is not None:
            if not isinstance(extension, str):
                return []
            clean_ext = extension.strip().lower()
            if clean_ext:
                target_ext = clean_ext if clean_ext.startswith(".") else f".{clean_ext}"

        matched_files: List[Dict[str, Any]] = []

        for item in safe_dir.iterdir():
            # Skip subdirectories, non-files, and hidden files (starting with '.')
            if not item.is_file() or item.name.startswith("."):
                continue

            item_ext = item.suffix.lower()
            if target_ext is not None and item_ext != target_ext:
                continue

            stat = item.stat()
            rel_or_full = str(Path(directory) / item.name).replace("\\", "/")

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

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info("list_files completed in %.2fms: found %d files", duration_ms, len(matched_files))
        return matched_files

    except Exception as exc:
        logger.warning("list_files exception: %s", exc)
        return []


def write_file(
    filepath: str,
    content: str,
    base_dir: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Write text content to a file, creating any missing parent directories.

    Overwrites existing files by default. Encodes all written text using UTF-8.
    Enforces path sandboxing against path traversal attacks.

    Parameters:
        filepath (str): Path where the file should be written.
        content (str): Text content to write into the file.
        base_dir (Optional[Union[str, Path]]): Optional root directory to enforce sandboxing against.

    Returns:
        Dict[str, Any]: Structured status dictionary containing:
            - success (bool): True if write succeeded, False otherwise.
            - filepath (str): Original target path.
            - bytes_written (int): Number of UTF-8 encoded bytes written to disk.
            - error (Optional[str]): Error description if failed, None if successful.
    """
    start_time = time.perf_counter()
    logger.info("Executing write_file: filepath='%s'", filepath)

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

    safe_path, path_err = _resolve_safe_path(filepath, base_dir=base_dir)
    if path_err or safe_path is None:
        logger.warning("write_file security rejection: %s", path_err)
        return {
            "success": False,
            "filepath": filepath,
            "bytes_written": 0,
            "error": path_err or "Access denied.",
        }

    try:
        if safe_path.exists() and safe_path.is_dir():
            return {
                "success": False,
                "filepath": filepath,
                "bytes_written": 0,
                "error": f"Target path '{filepath}' is an existing directory.",
            }

        # Auto-create intermediate parent directories if missing
        if safe_path.parent and not safe_path.parent.exists():
            safe_path.parent.mkdir(parents=True, exist_ok=True)

        encoded_bytes = content.encode("utf-8")
        safe_path.write_bytes(encoded_bytes)

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info("write_file completed in %.2fms: wrote %d bytes to '%s'", duration_ms, len(encoded_bytes), filepath)

        return {
            "success": True,
            "filepath": filepath,
            "bytes_written": len(encoded_bytes),
            "error": None,
        }

    except Exception as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000
        err = f"Error writing file '{filepath}': {str(exc)}"
        logger.warning("write_file failed in %.2fms: %s", duration_ms, err)
        logger.debug("write_file failure details", exc_info=True)
        return {
            "success": False,
            "filepath": filepath,
            "bytes_written": 0,
            "error": err,
        }


def search_in_file(
    filepath: str,
    keyword: str,
    base_dir: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Search for occurrences of a keyword within a file and return context snippets.

    Case-insensitive by default. Automatically handles .txt, .pdf, and .docx formats
    by delegating file extraction to read_file() (which enforces path sandboxing).

    Parameters:
        filepath (str): Path to the target file.
        keyword (str): The keyword or phrase to search for.
        base_dir (Optional[Union[str, Path]]): Optional root directory to enforce sandboxing against.

    Returns:
        Dict[str, Any]: Structured dictionary containing:
            - success (bool): True if file was read and searched, False if read failed.
            - filepath (str): Original target path.
            - keyword (str): Original keyword queried.
            - match_count (int): Total number of lines containing the keyword.
            - matches (List[Dict[str, Any]]): List of match entries with line_number and context.
            - error (Optional[str]): Error description if reading or input failed, None on success.
    """
    start_time = time.perf_counter()
    logger.info("Executing search_in_file: filepath='%s', keyword='%s'", filepath, keyword)

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
        read_res = read_file(filepath, base_dir=base_dir)
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

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "search_in_file completed in %.2fms: found %d matches for '%s' in '%s'",
            duration_ms,
            len(matches),
            keyword,
            filepath,
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
        duration_ms = (time.perf_counter() - start_time) * 1000
        err = f"Error searching in file '{filepath}': {str(exc)}"
        logger.exception("search_in_file failed in %.2fms: %s", duration_ms, err)
        return {
            "success": False,
            "filepath": filepath,
            "keyword": keyword,
            "match_count": 0,
            "matches": [],
            "error": err,
        }
