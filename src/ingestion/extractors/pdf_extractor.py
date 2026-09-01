"""PDF document content extractor using pypdf."""

from pathlib import Path
from typing import Generator, Union

import pypdf

from src.ingestion.detectors.base import DetectionResult, FileType
from src.ingestion.extractors.base import BaseExtractor
from src.ingestion.extractors.models import ContentType, ExtractedElement, ExtractedStream, ExtractionStatus


class PDFExtractor(BaseExtractor):
    """Extracts page text and metadata from PDF files using pypdf."""

    def __init__(self):
        super().__init__(target_file_type=FileType.PDF)

    def _extract_implementation(self, path: Path, detection_result: DetectionResult) -> ExtractedStream:
        try:
            reader = pypdf.PdfReader(path)
            if reader.is_encrypted:
                # Attempt to decrypt with empty password for partially locked PDFs
                try:
                    reader.decrypt("")
                except Exception:
                    return ExtractedStream(
                        file_path=str(path),
                        file_type=FileType.PDF,
                        element_generator=iter([]),
                        status=ExtractionStatus.FAILED,
                        error_message="PDF is password-protected or encrypted.",
                    )

            total_pages = len(reader.pages)
            metadata = {
                "total_pages": total_pages,
                "pdf_header": reader.pdf_header if hasattr(reader, "pdf_header") else None,
            }

            generator = self._page_generator(reader, total_pages)
            return ExtractedStream(
                file_path=str(path),
                file_type=FileType.PDF,
                element_generator=generator,
                metadata=metadata,
            )

        except Exception as e:
            return ExtractedStream(
                file_path=str(path),
                file_type=FileType.PDF,
                element_generator=iter([]),
                status=ExtractionStatus.FAILED,
                error_message=f"Failed to open PDF document: {str(e)}",
            )

    def _page_generator(
        self, reader: pypdf.PdfReader, total_pages: int
    ) -> Generator[ExtractedElement, None, None]:
        element_idx = 0
        for page_idx in range(total_pages):
            page = reader.pages[page_idx]
            text = page.extract_text() or ""
            text = text.strip()

            if not text:
                continue

            yield ExtractedElement(
                element_index=element_idx,
                content_type=ContentType.PAGE_TEXT,
                text_content=text,
                structural_context={
                    "page_number": page_idx + 1,
                    "total_pages": total_pages,
                },
            )
            element_idx += 1
