"""Metadata enrichment engine for attaching deterministic trace metadata to Chunks."""

import hashlib
from pathlib import Path
from typing import Any, Dict, Generator, Iterable, Optional, Union

from src.ingestion.chunkers.models import Chunk
from src.ingestion.detectors.base import FileType
from src.ingestion.extractors.models import ContentType
from src.ingestion.metadata.models import DocumentMetadata


def generate_doc_id(file_path: Union[str, Path]) -> str:
    """Generate a deterministic 16-character SHA-256 document identifier from file path."""
    normalized_path = Path(file_path).resolve().as_posix().lower()
    return hashlib.sha256(normalized_path.encode("utf-8")).hexdigest()[:16]


class MetadataEnricher:
    """Enriches chunk objects with standardized enterprise metadata for traceability."""

    @classmethod
    def build_metadata(
        cls,
        chunk: Chunk,
        file_path: Union[str, Path],
        file_type: Union[FileType, str],
        doc_id: Optional[str] = None,
    ) -> DocumentMetadata:
        """Extract and map available structural metadata into a DocumentMetadata contract."""
        path = Path(file_path)
        resolved_doc_id = doc_id if doc_id else generate_doc_id(path)
        file_type_str = file_type.value if isinstance(file_type, FileType) else str(file_type)
        content_type_str = chunk.content_type.value if isinstance(chunk.content_type, ContentType) else str(chunk.content_type)

        raw_meta = chunk.metadata if chunk.metadata else {}
        struct_ctx: Dict[str, Any] = raw_meta.get("structural_context", {})
        element_idx = raw_meta.get("element_index", 0)

        # Extract optional format-specific attributes from structural_context if present
        page_number = struct_ctx.get("page_number")
        slide_number = struct_ctx.get("slide_number")
        slide_title = struct_ctx.get("slide_title")
        sheet_name = struct_ctx.get("sheet_name")
        row_index = struct_ctx.get("row_index")
        heading_level = struct_ctx.get("heading_level")
        start_line = struct_ctx.get("start_line")
        end_line = struct_ctx.get("end_line")

        return DocumentMetadata(
            doc_id=resolved_doc_id,
            source_name=path.name,
            source_path=path.as_posix(),
            file_type=file_type_str,
            chunk_index=chunk.chunk_index,
            element_index=element_idx,
            content_type=content_type_str,
            page_number=page_number,
            slide_number=slide_number,
            slide_title=slide_title,
            sheet_name=sheet_name,
            row_index=row_index,
            heading_level=heading_level,
            start_line=start_line,
            end_line=end_line,
            structural_context=struct_ctx,
        )

    @classmethod
    def enrich_chunk(
        cls,
        chunk: Chunk,
        file_path: Union[str, Path],
        file_type: Union[FileType, str],
        doc_id: Optional[str] = None,
    ) -> Chunk:
        """Return a new Chunk with standardized, enriched metadata dictionary."""
        doc_meta = cls.build_metadata(chunk, file_path, file_type, doc_id=doc_id)
        enriched_meta_dict = doc_meta.to_dict()

        return Chunk(
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            content_type=chunk.content_type,
            metadata=enriched_meta_dict,
        )

    @classmethod
    def enrich_chunk_stream(
        cls,
        chunks: Iterable[Chunk],
        file_path: Union[str, Path],
        file_type: Union[FileType, str],
        doc_id: Optional[str] = None,
    ) -> Generator[Chunk, None, None]:
        """Lazy generator to enrich a stream of Chunk objects."""
        resolved_doc_id = doc_id if doc_id else generate_doc_id(file_path)

        for chunk in chunks:
            yield cls.enrich_chunk(chunk, file_path, file_type, doc_id=resolved_doc_id)
