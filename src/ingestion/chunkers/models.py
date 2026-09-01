"""Data contracts for ingestion chunking."""

from dataclasses import dataclass, field
from typing import Any, Dict

from src.ingestion.extractors.models import ContentType


@dataclass(frozen=True)
class Chunk:
    """Immutable retrieval-ready chunk produced from extracted content."""
    chunk_index: int
    text: str
    content_type: ContentType
    metadata: Dict[str, Any] = field(default_factory=dict)
