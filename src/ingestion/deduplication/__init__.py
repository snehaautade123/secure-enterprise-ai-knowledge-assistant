"""Deduplication and content fingerprinting subpackage."""

from src.ingestion.deduplication.detector import DuplicateDetector
from src.ingestion.deduplication.hasher import compute_content_hash, compute_file_hash
from src.ingestion.deduplication.models import DuplicateResult, DuplicateType

__all__ = [
    "DuplicateDetector",
    "DuplicateResult",
    "DuplicateType",
    "compute_content_hash",
    "compute_file_hash",
]
