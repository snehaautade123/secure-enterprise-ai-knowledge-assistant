"""Data models and contract structures for the document extraction layer."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, Iterator, Optional
from src.ingestion.detectors.base import FileType


class ContentType(str, Enum):
    """Structural type of extracted content element."""
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    TABLE = "table"
    SLIDE = "slide"
    SHEET_ROW = "sheet_row"
    PAGE_TEXT = "page_text"
    LINE_BLOCK = "line_block"


class ExtractionStatus(str, Enum):
    """Lifecycle status of the extraction stream."""
    PENDING = "pending"              # Generator created, stream iteration in progress
    SUCCESS = "success"              # Complete extraction without unhandled errors
    PARTIAL_SUCCESS = "partial"      # Elements yielded, but stream encountered mid-read non-fatal error
    FAILED = "failed"                # Boundary validation failure or fatal error before any element was yielded


@dataclass(frozen=True)
class ExtractedElement:
    """Immutable structural element yielded by extraction stream."""
    element_index: int               # Sequential element index within file (0, 1, 2...)
    content_type: ContentType
    text_content: str                # Extracted raw text content
    structural_context: Dict[str, Any]  # Contextual metadata (page, slide, sheet, row, heading info)


class ExtractedStream:
    """Lazy element stream wrapper with real-time lifecycle status tracking."""

    def __init__(
        self,
        file_path: str,
        file_type: FileType,
        element_generator: Iterable[ExtractedElement],
        status: ExtractionStatus = ExtractionStatus.PENDING,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.file_path = file_path
        self.file_type = file_type
        self.status = status
        self.metadata: Dict[str, Any] = metadata if metadata is not None else {}
        self.error_message = error_message
        self._generator = element_generator
        self.elements_yielded = 0

    def __iter__(self) -> Iterator[ExtractedElement]:
        """Wrap generator to update status dynamically as caller consumes items."""
        if self.status == ExtractionStatus.FAILED:
            return

        try:
            for element in self._generator:
                self.elements_yielded += 1
                yield element

            if self.status == ExtractionStatus.PENDING:
                self.status = ExtractionStatus.SUCCESS

        except Exception as e:
            self.error_message = f"Stream interrupted: {str(e)}"
            if self.elements_yielded > 0:
                self.status = ExtractionStatus.PARTIAL_SUCCESS
            else:
                self.status = ExtractionStatus.FAILED
