"""Deterministic fingerprint hashing utilities for files and text content."""

import hashlib
from pathlib import Path
from typing import Optional, Tuple, Union

from src.ingestion.cleaners.text_cleaner import clean_text, is_meaningful_text

CHUNK_READ_SIZE = 65536  # 64KB read buffer for streaming file hashes


def compute_file_hash(file_path: Union[str, Path]) -> Tuple[str, Optional[str]]:
    """
    Compute deterministic SHA-256 hash over raw file binary bytes in 64KB chunks.

    Args:
        file_path: Path to target file.

    Returns:
        Tuple of (sha256_hex_string, error_message_if_failed).
    """
    path = Path(file_path)

    if not path.exists():
        return "", f"File does not exist: '{path}'"
    if path.is_dir():
        return "", f"Path is a directory, not a file: '{path}'"

    try:
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(CHUNK_READ_SIZE):
                hasher.update(chunk)
        return hasher.hexdigest(), None
    except Exception as e:
        return "", f"Read error during file hashing: {str(e)}"


def compute_content_hash(text: Optional[str]) -> Tuple[str, bool]:
    """
    Compute deterministic SHA-256 hash over normalized text content.

    Args:
        text: Raw text string to normalize and hash.

    Returns:
        Tuple of (sha256_hex_string, is_meaningful_content).
    """
    cleaned = clean_text(text)
    if not is_meaningful_text(cleaned):
        return "", False

    hasher = hashlib.sha256()
    hasher.update(cleaned.encode("utf-8"))
    return hasher.hexdigest(), True
