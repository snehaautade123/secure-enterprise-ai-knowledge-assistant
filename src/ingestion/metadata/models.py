"""Metadata contracts and data models for enterprise document traceability."""

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Union

from src.ingestion.detectors.base import FileType
from src.ingestion.extractors.models import ContentType


@dataclass(frozen=True)
class DocumentMetadata:
    """Standardized metadata payload for document chunks ensuring downstream traceability."""

    doc_id: str                      # Deterministic document identifier
    source_name: str                 # Base filename (e.g. "report.pdf")
    source_path: str                 # Normalized path string
    file_type: str                   # Extension/FileType string (e.g. "pdf")
    chunk_index: int                 # Sequential chunk index
    element_index: int               # Index of origin ExtractedElement
    content_type: str                # ContentType string value
    page_number: Optional[int] = None       # Available for PDF/page-based docs
    slide_number: Optional[int] = None      # Available for PPTX
    slide_title: Optional[str] = None       # Available for PPTX
    sheet_name: Optional[str] = None        # Available for XLSX
    row_index: Optional[int] = None         # Available for CSV/XLSX
    heading_level: Optional[int] = None     # Available for DOCX
    start_line: Optional[int] = None        # Available for TXT
    end_line: Optional[int] = None          # Available for TXT
    structural_context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary representation, excluding None optional fields."""
        data = asdict(self)
        # Return cleaned dict keeping non-None values and non-empty dicts
        return {k: v for k, v in data.items() if v is not None}
