"""Data contracts for duplicate detection and content fingerprinting."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DuplicateType(str, Enum):
    """Category of detected duplicate."""
    EXACT_FILE = "exact_file"              # Binary byte-for-byte file duplicate
    NORMALIZED_CONTENT = "normalized_content"  # Cleaned text content duplicate
    NONE = "none"                          # Unique content


@dataclass(frozen=True)
class DuplicateResult:
    """Payload summarizing duplicate detection findings."""
    is_duplicate: bool
    duplicate_type: DuplicateType
    fingerprint: str                       # SHA-256 fingerprint hash
    original_source: Optional[str] = None  # Reference to original file path or chunk ID
    reason: str = ""                       # Human-readable explanation of duplicate finding
