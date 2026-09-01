"""Base interfaces and data contracts for file format detection."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Union


class FileType(str, Enum):
    """Supported file types in the ingestion pipeline."""
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    TXT = "txt"
    CSV = "csv"
    XLSX = "xlsx"
    UNKNOWN = "unknown"


class DetectionStatus(str, Enum):
    """Result status of format detection."""
    VALID = "valid"                    # Extension and content signatures/heuristics match
    MISMATCH = "mismatch"              # Extension claims format X, but content analysis proves format Y
    UNSUPPORTED = "unsupported"        # Extension or content format is not supported by pipeline
    INVALID = "invalid"                # Path is a directory, missing, empty, or file is corrupted


@dataclass(frozen=True)
class DetectionResult:
    """Immutable payload containing file detection outcome."""
    status: DetectionStatus
    detected_type: FileType
    extension_type: FileType
    mime_type: Optional[str]
    is_valid: bool
    details: str


class BaseDetector(ABC):
    """Abstract base interface for file format detectors."""

    @abstractmethod
    def detect(self, file_path: Union[str, Path]) -> DetectionResult:
        """
        Detect and validate file type against extension and content characteristics.

        Args:
            file_path: Path to the target file.

        Returns:
            DetectionResult describing format validity, detected type, and details.
        """
        pass
