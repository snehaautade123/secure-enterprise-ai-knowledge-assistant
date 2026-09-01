"""End-to-end ingestion pipeline orchestrator connecting Person 1 components."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from src.ingestion.chunkers import Chunk, TextChunker
from src.ingestion.deduplication import DuplicateDetector, DuplicateResult
from src.ingestion.detectors.base import DetectionResult, DetectionStatus
from src.ingestion.detectors.file_detector import FileDetector
from src.ingestion.extractors import ExtractorFactory, ExtractionStatus
from src.ingestion.metadata import MetadataEnricher, generate_doc_id


class IngestionStatus(str, Enum):
    """Overall status of end-to-end ingestion processing for a document."""
    SUCCESS = "success"                      # Pipeline completed and chunks generated
    SKIPPED_DUPLICATE = "skipped_duplicate"  # File binary content was identified as exact duplicate
    FAILED = "failed"                        # Detection, extraction, or file access failure


@dataclass
class IngestionResult:
    """Final structured output produced by end-to-end ingestion pipeline."""
    file_path: str
    status: IngestionStatus
    doc_id: str
    detected_type: str
    detection_result: Optional[DetectionResult] = None
    chunks: List[Chunk] = field(default_factory=list)
    file_duplicate_info: Optional[DuplicateResult] = None
    chunk_duplicate_infos: List[DuplicateResult] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


class IngestionPipeline:
    """Orchestrates end-to-end file ingestion: Detection -> Extraction -> Cleaning -> Chunking -> Metadata -> Deduplication."""

    def __init__(
        self,
        detector: Optional[FileDetector] = None,
        chunker: Optional[TextChunker] = None,
        duplicate_detector: Optional[DuplicateDetector] = None,
    ):
        self.detector = detector if detector is not None else FileDetector()
        self.chunker = chunker if chunker is not None else TextChunker()
        self.duplicate_detector = (
            duplicate_detector if duplicate_detector is not None else DuplicateDetector()
        )

    def process_file(
        self,
        file_path: Union[str, Path],
        check_duplicate_file: bool = True,
        check_duplicate_chunks: bool = True,
    ) -> IngestionResult:
        """
        Execute full end-to-end ingestion pipeline on a target file.

        Args:
            file_path: Target file path.
            check_duplicate_file: Whether to check binary file-level duplication.
            check_duplicate_chunks: Whether to check chunk-level content duplication.

        Returns:
            IngestionResult payload containing processed chunks, metadata, and duplicate findings.
        """
        path = Path(file_path)
        doc_id = generate_doc_id(path) if path.exists() else ""

        # 1. File Type & Format Detection
        detection_res = self.detector.detect(path)
        if detection_res.status != DetectionStatus.VALID:
            return IngestionResult(
                file_path=str(path),
                status=IngestionStatus.FAILED,
                doc_id=doc_id,
                detected_type=detection_res.detected_type.value,
                detection_result=detection_res,
                error_message=f"Detection failed: {detection_res.details}",
            )

        detected_type = detection_res.detected_type

        # 2. File-Level Binary Deduplication Check
        file_dup_info: Optional[DuplicateResult] = None
        if check_duplicate_file:
            file_dup_info = self.duplicate_detector.check_and_register_file(path)
            if file_dup_info.is_duplicate:
                return IngestionResult(
                    file_path=str(path),
                    status=IngestionStatus.SKIPPED_DUPLICATE,
                    doc_id=doc_id,
                    detected_type=detected_type.value,
                    detection_result=detection_res,
                    file_duplicate_info=file_dup_info,
                    error_message=file_dup_info.reason,
                )

        # 3. Format-Specific Content Extraction
        try:
            extractor = ExtractorFactory.get_extractor(detected_type)
        except ValueError as e:
            return IngestionResult(
                file_path=str(path),
                status=IngestionStatus.FAILED,
                doc_id=doc_id,
                detected_type=detected_type.value,
                detection_result=detection_res,
                error_message=str(e),
            )

        extracted_stream = extractor.extract(path, detection_res)
        if extracted_stream.status == ExtractionStatus.FAILED:
            return IngestionResult(
                file_path=str(path),
                status=IngestionStatus.FAILED,
                doc_id=doc_id,
                detected_type=detected_type.value,
                detection_result=detection_res,
                error_message=f"Extraction failed: {extracted_stream.error_message}",
            )

        # 4 & 5. Chunking & Text Cleaning
        # TextChunker internally cleans text via clean_text() & filters empty content
        raw_chunks = self.chunker.chunk_element_stream(extracted_stream)

        # 6. Metadata Enrichment
        enriched_chunks = MetadataEnricher.enrich_chunk_stream(
            raw_chunks, file_path=path, file_type=detected_type, doc_id=doc_id
        )

        # 7. Chunk-Level Content Deduplication & Pipeline Assembly
        final_chunks: List[Chunk] = []
        chunk_dup_infos: List[DuplicateResult] = []

        for chunk in enriched_chunks:
            if check_duplicate_chunks:
                chunk_dup = self.duplicate_detector.check_and_register_chunk(
                    chunk, source_file_name=path.name
                )
                chunk_dup_infos.append(chunk_dup)
                if chunk_dup.is_duplicate:
                    # Tag metadata with duplicate tracking info
                    chunk.metadata["is_duplicate"] = True
                    chunk.metadata["duplicate_original_source"] = chunk_dup.original_source

            final_chunks.append(chunk)

        pipeline_metadata = {
            "source_name": path.name,
            "source_path": path.as_posix(),
            "detected_type": detected_type.value,
            "mime_type": detection_res.mime_type,
            "total_chunks": len(final_chunks),
            "duplicate_chunks_count": sum(1 for d in chunk_dup_infos if d.is_duplicate),
            "extractor_metadata": extracted_stream.metadata,
        }

        return IngestionResult(
            file_path=str(path),
            status=IngestionStatus.SUCCESS,
            doc_id=doc_id,
            detected_type=detected_type.value,
            detection_result=detection_res,
            chunks=final_chunks,
            file_duplicate_info=file_dup_info,
            chunk_duplicate_infos=chunk_dup_infos,
            metadata=pipeline_metadata,
        )
