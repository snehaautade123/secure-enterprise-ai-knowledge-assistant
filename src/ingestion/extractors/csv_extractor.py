"""CSV tabular content extractor using standard library csv.reader and heuristic header sniffing."""

import csv
from pathlib import Path
from typing import Generator, List, Tuple, Union

from src.ingestion.detectors.base import DetectionResult, FileType
from src.ingestion.extractors.base import BaseExtractor
from src.ingestion.extractors.models import ContentType, ExtractedElement, ExtractedStream, ExtractionStatus

SUPPORTED_ENCODINGS = ("utf-8", "utf-8-sig", "latin-1", "cp1252")


class CSVExtractor(BaseExtractor):
    """Extracts CSV rows in streaming fashion with heuristic header detection."""

    def __init__(self):
        super().__init__(target_file_type=FileType.CSV)

    def _extract_implementation(self, path: Path, detection_result: DetectionResult) -> ExtractedStream:
        encoding_used, read_error = self._detect_encoding(path)
        if not encoding_used:
            return ExtractedStream(
                file_path=str(path),
                file_type=FileType.CSV,
                element_generator=iter([]),
                status=ExtractionStatus.FAILED,
                error_message=f"Failed to decode CSV file: {read_error}",
            )

        has_header_heuristic, delimiter = self._sniff_csv_properties(path, encoding_used)

        metadata = {
            "encoding_used": encoding_used,
            "has_header_heuristic": has_header_heuristic,
            "delimiter": delimiter,
        }

        generator = self._row_generator(path, encoding_used, delimiter, has_header_heuristic, metadata)
        return ExtractedStream(
            file_path=str(path),
            file_type=FileType.CSV,
            element_generator=generator,
            metadata=metadata,
        )

    def _detect_encoding(self, path: Path) -> Tuple[str, str]:
        """Attempt to read initial bytes under candidate encodings."""
        last_error = ""
        for encoding in SUPPORTED_ENCODINGS:
            try:
                with open(path, "r", encoding=encoding) as f:
                    f.read(2048)
                return encoding, ""
            except UnicodeDecodeError as e:
                last_error = str(e)
                continue
            except Exception as e:
                return "", str(e)
        return "", last_error

    def _sniff_csv_properties(self, path: Path, encoding: str) -> Tuple[bool, str]:
        """Run heuristic CSV sniffer for header presence and delimiter."""
        has_header_heuristic = False
        delimiter = ","

        try:
            with open(path, "r", encoding=encoding) as f:
                sample = f.read(4096)
                if sample.strip():
                    sniffer = csv.Sniffer()
                    try:
                        has_header_heuristic = sniffer.has_header(sample)
                    except csv.Error:
                        has_header_heuristic = False

                    try:
                        dialect = sniffer.sniff(sample, delimiters=",;\t|")
                        delimiter = dialect.delimiter
                    except csv.Error:
                        delimiter = ","
        except Exception:
            pass

        return has_header_heuristic, delimiter

    def _row_generator(
        self,
        path: Path,
        encoding: str,
        delimiter: str,
        has_header_heuristic: bool,
        metadata: dict,
    ) -> Generator[ExtractedElement, None, None]:
        element_idx = 0

        with open(path, "r", encoding=encoding, errors="replace") as f:
            reader = csv.reader(f, delimiter=delimiter)
            headers: List[str] = []

            for row_idx, row in enumerate(reader):
                if not row or not any(field.strip() for field in row):
                    continue

                if row_idx == 0 and has_header_heuristic:
                    headers = [field.strip() for field in row]
                    metadata["header_row"] = headers
                    continue

                row_str = " | ".join(field.strip() for field in row)

                column_context = {}
                if headers:
                    column_context = {
                        headers[i]: row[i].strip()
                        for i in range(min(len(headers), len(row)))
                    }

                yield ExtractedElement(
                    element_index=element_idx,
                    content_type=ContentType.SHEET_ROW,
                    text_content=row_str,
                    structural_context={
                        "row_index": row_idx,
                        "col_count": len(row),
                        "header_detected_by_heuristic": has_header_heuristic,
                        "columns": column_context if headers else None,
                    },
                )
                element_idx += 1
