"""Abstract base interface for format-specific extractors with strict boundary checks."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union

from src.ingestion.detectors.base import DetectionResult, DetectionStatus, FileType
from src.ingestion.extractors.models import ExtractedStream, ExtractionStatus


class BaseExtractor(ABC):
    """Abstract base interface enforcing strict detection boundary validation."""

    def __init__(self, target_file_type: FileType):
        self.target_file_type = target_file_type

    def extract(self, file_path: Union[str, Path], detection_result: DetectionResult) -> ExtractedStream:
        """
        Public entrypoint. Validates detection boundary before delegating to implementation.

        Args:
            file_path: Path to the target file.
            detection_result: Pre-validated DetectionResult from FileDetector.

        Returns:
            ExtractedStream payload wrapping lazy element generator and status.
        """
        path = Path(file_path)

        # 1. Enforce Detection Boundary Guard - Status check
        if detection_result.status != DetectionStatus.VALID:
            return ExtractedStream(
                file_path=str(path),
                file_type=self.target_file_type,
                element_generator=iter([]),
                status=ExtractionStatus.FAILED,
                error_message=(
                    f"Refusing extraction: DetectionResult status is '{detection_result.status.value}', "
                    f"expected '{DetectionStatus.VALID.value}'."
                ),
            )

        # 2. Enforce Detection Boundary Guard - File type match check
        if detection_result.detected_type != self.target_file_type:
            return ExtractedStream(
                file_path=str(path),
                file_type=self.target_file_type,
                element_generator=iter([]),
                status=ExtractionStatus.FAILED,
                error_message=(
                    f"Refusing extraction: Extractor '{self.__class__.__name__}' expects '{self.target_file_type.value}', "
                    f"but DetectionResult detected '{detection_result.detected_type.value}'."
                ),
            )

        # 3. Delegate to concrete format implementation
        return self._extract_implementation(path, detection_result)

    @abstractmethod
    def _extract_implementation(self, path: Path, detection_result: DetectionResult) -> ExtractedStream:
        """Format-specific extraction implementation returning an ExtractedStream."""
        pass
