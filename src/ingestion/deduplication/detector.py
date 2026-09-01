"""Duplicate detector maintaining deterministic fingerprint registries for files and chunks."""

from pathlib import Path
from typing import Dict, Optional, Union

from src.ingestion.chunkers.models import Chunk
from src.ingestion.deduplication.hasher import compute_content_hash, compute_file_hash
from src.ingestion.deduplication.models import DuplicateResult, DuplicateType


class DuplicateDetector:
    """Detects exact file and normalized content duplicates using deterministic hash tracking."""

    def __init__(self):
        # Maps SHA-256 fingerprint -> source_reference string
        self._file_registry: Dict[str, str] = {}
        self._content_registry: Dict[str, str] = {}

    def reset(self) -> None:
        """Clear all registered fingerprints."""
        self._file_registry.clear()
        self._content_registry.clear()

    def check_and_register_file(
        self, file_path: Union[str, Path], source_reference: Optional[str] = None
    ) -> DuplicateResult:
        """
        Check if file binary content is a duplicate. Registers unique files.

        Args:
            file_path: Path to target file.
            source_reference: Optional caller reference (defaults to normalized path string).

        Returns:
            DuplicateResult indicating whether file is duplicate and explaining why.
        """
        path = Path(file_path)
        ref_name = source_reference if source_reference else path.as_posix()

        file_hash, error_msg = compute_file_hash(path)
        if error_msg:
            return DuplicateResult(
                is_duplicate=False,
                duplicate_type=DuplicateType.NONE,
                fingerprint="",
                original_source=None,
                reason=f"Invalid file input: {error_msg}",
            )

        if file_hash in self._file_registry:
            orig = self._file_registry[file_hash]
            return DuplicateResult(
                is_duplicate=True,
                duplicate_type=DuplicateType.EXACT_FILE,
                fingerprint=file_hash,
                original_source=orig,
                reason=f"Exact binary file duplicate of original source '{orig}'",
            )

        # Register new unique file
        self._file_registry[file_hash] = ref_name
        return DuplicateResult(
            is_duplicate=False,
            duplicate_type=DuplicateType.NONE,
            fingerprint=file_hash,
            original_source=ref_name,
            reason="Unique file content registered successfully",
        )

    def check_and_register_content(
        self, text: Optional[str], source_reference: str = ""
    ) -> DuplicateResult:
        """
        Check if normalized text content is a duplicate. Registers unique text.

        Args:
            text: Text content string.
            source_reference: Caller reference label (e.g. "doc.txt#chunk_0").

        Returns:
            DuplicateResult indicating whether content is duplicate.
        """
        content_hash, is_meaningful = compute_content_hash(text)
        if not is_meaningful:
            return DuplicateResult(
                is_duplicate=False,
                duplicate_type=DuplicateType.NONE,
                fingerprint="",
                original_source=None,
                reason="Empty or whitespace-only content (skipped duplication check)",
            )

        if content_hash in self._content_registry:
            orig = self._content_registry[content_hash]
            return DuplicateResult(
                is_duplicate=True,
                duplicate_type=DuplicateType.NORMALIZED_CONTENT,
                fingerprint=content_hash,
                original_source=orig,
                reason=f"Normalized text content duplicate of original source '{orig}'",
            )

        # Register new unique content
        self._content_registry[content_hash] = source_reference
        return DuplicateResult(
            is_duplicate=False,
            duplicate_type=DuplicateType.NONE,
            fingerprint=content_hash,
            original_source=source_reference,
            reason="Unique text content registered successfully",
        )

    def check_and_register_chunk(
        self, chunk: Chunk, source_file_name: str = ""
    ) -> DuplicateResult:
        """
        Convenience method to check and register a Chunk object.

        Args:
            chunk: Chunk contract object.
            source_file_name: Optional filename prefix for source reference labeling.

        Returns:
            DuplicateResult indicating whether chunk text is duplicate.
        """
        ref_label = (
            f"{source_file_name}#chunk_{chunk.chunk_index}"
            if source_file_name
            else f"chunk_{chunk.chunk_index}"
        )
        return self.check_and_register_content(chunk.text, source_reference=ref_label)
