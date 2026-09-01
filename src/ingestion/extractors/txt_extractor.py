"""Text document content extractor using standard library streaming and multi-encoding fallback."""

from pathlib import Path
from typing import Generator, List, Tuple, Union

from src.ingestion.detectors.base import DetectionResult, FileType
from src.ingestion.extractors.base import BaseExtractor
from src.ingestion.extractors.models import ContentType, ExtractedElement, ExtractedStream, ExtractionStatus

SUPPORTED_ENCODINGS = ("utf-8", "utf-8-sig", "latin-1", "cp1252")
DEFAULT_BLOCK_SIZE = 50  # Number of lines per line-block element


class TXTExtractor(BaseExtractor):
    """Extracts text content in streaming line-block units with robust encoding fallback."""

    def __init__(self, block_size: int = DEFAULT_BLOCK_SIZE):
        super().__init__(target_file_type=FileType.TXT)
        self.block_size = block_size

    def _extract_implementation(self, path: Path, detection_result: DetectionResult) -> ExtractedStream:
        encoding_used, read_error = self._detect_encoding(path)
        if not encoding_used:
            return ExtractedStream(
                file_path=str(path),
                file_type=FileType.TXT,
                element_generator=iter([]),
                status=ExtractionStatus.FAILED,
                error_message=f"Failed to decode text file: {read_error}",
            )

        metadata = {
            "encoding_used": encoding_used,
            "block_size": self.block_size,
        }

        generator = self._block_generator(path, encoding_used)
        return ExtractedStream(
            file_path=str(path),
            file_type=FileType.TXT,
            element_generator=generator,
            metadata=metadata,
        )

    def _detect_encoding(self, path: Path) -> Tuple[str, str]:
        """Attempt to read initial bytes under candidate encodings."""
        last_error = ""
        for encoding in SUPPORTED_ENCODINGS:
            try:
                with open(path, "r", encoding=encoding) as f:
                    f.read(4096)
                return encoding, ""
            except UnicodeDecodeError as e:
                last_error = str(e)
                continue
            except Exception as e:
                return "", str(e)
        return "", last_error

    def _block_generator(self, path: Path, encoding: str) -> Generator[ExtractedElement, None, None]:
        element_idx = 0
        current_lines: List[str] = []
        start_line = 1
        current_line_num = 0

        with open(path, "r", encoding=encoding, errors="replace") as f:
            for line in f:
                current_line_num += 1
                current_lines.append(line)

                if len(current_lines) >= self.block_size:
                    block_text = "".join(current_lines).strip()
                    if block_text:
                        yield ExtractedElement(
                            element_index=element_idx,
                            content_type=ContentType.LINE_BLOCK,
                            text_content=block_text,
                            structural_context={
                                "start_line": start_line,
                                "end_line": current_line_num,
                                "line_count": len(current_lines),
                                "encoding": encoding,
                            },
                        )
                        element_idx += 1
                    current_lines = []
                    start_line = current_line_num + 1

            # Yield remaining lines
            if current_lines:
                block_text = "".join(current_lines).strip()
                if block_text:
                    yield ExtractedElement(
                        element_index=element_idx,
                        content_type=ContentType.LINE_BLOCK,
                        text_content=block_text,
                        structural_context={
                            "start_line": start_line,
                            "end_line": current_line_num,
                            "line_count": len(current_lines),
                            "encoding": encoding,
                        },
                    )
