"""Multi-format file type detector using magic bytes, OOXML OPC structure, and text heuristics."""

import csv
import mimetypes
from pathlib import Path
import zipfile
from typing import Dict, Optional, Tuple, Union

from src.ingestion.detectors.base import (
    BaseDetector,
    DetectionResult,
    DetectionStatus,
    FileType,
)

EXTENSION_MAP: Dict[str, FileType] = {
    ".pdf": FileType.PDF,
    ".docx": FileType.DOCX,
    ".pptx": FileType.PPTX,
    ".txt": FileType.TXT,
    ".csv": FileType.CSV,
    ".xlsx": FileType.XLSX,
}

# Open Packaging Conventions (OPC ISO/IEC 29500-2) root entry markers
OOXML_MARKERS: Dict[FileType, str] = {
    FileType.DOCX: "word/document.xml",
    FileType.PPTX: "ppt/presentation.xml",
    FileType.XLSX: "xl/workbook.xml",
}


class FileDetector(BaseDetector):
    """Detects and validates file format identity and basic structural integrity."""

    def detect(self, file_path: Union[str, Path]) -> DetectionResult:
        path = Path(file_path)

        # 1. Existence and directory validation
        if not path.exists():
            return DetectionResult(
                status=DetectionStatus.INVALID,
                detected_type=FileType.UNKNOWN,
                extension_type=FileType.UNKNOWN,
                mime_type=None,
                is_valid=False,
                details=f"Path does not exist: '{path}'",
            )

        if path.is_dir():
            return DetectionResult(
                status=DetectionStatus.INVALID,
                detected_type=FileType.UNKNOWN,
                extension_type=FileType.UNKNOWN,
                mime_type=None,
                is_valid=False,
                details=f"Path points to a directory, not a regular file: '{path}'",
            )

        if path.stat().st_size == 0:
            return DetectionResult(
                status=DetectionStatus.INVALID,
                detected_type=FileType.UNKNOWN,
                extension_type=self._get_extension_type(path),
                mime_type=None,
                is_valid=False,
                details=f"File is empty (0 bytes): '{path}'",
            )

        ext_type = self._get_extension_type(path)
        mime_type, _ = mimetypes.guess_type(path)

        if ext_type == FileType.UNKNOWN:
            return DetectionResult(
                status=DetectionStatus.UNSUPPORTED,
                detected_type=FileType.UNKNOWN,
                extension_type=FileType.UNKNOWN,
                mime_type=mime_type,
                is_valid=False,
                details=f"Unsupported file extension: '{path.suffix}'",
            )

        # 2. Content signature and structural validation
        detected_type, error_msg = self._analyze_content(path, ext_type)

        if error_msg:
            return DetectionResult(
                status=DetectionStatus.INVALID,
                detected_type=FileType.UNKNOWN,
                extension_type=ext_type,
                mime_type=mime_type,
                is_valid=False,
                details=f"Invalid file structure: {error_msg}",
            )

        # 3. Check for format mismatch
        if detected_type != ext_type:
            return DetectionResult(
                status=DetectionStatus.MISMATCH,
                detected_type=detected_type,
                extension_type=ext_type,
                mime_type=mime_type,
                is_valid=False,
                details=(
                    f"Format mismatch: Extension claims '{ext_type.value}', "
                    f"but content analysis detected '{detected_type.value}'."
                ),
            )

        # 4. Valid result
        return DetectionResult(
            status=DetectionStatus.VALID,
            detected_type=detected_type,
            extension_type=ext_type,
            mime_type=mime_type,
            is_valid=True,
            details="File extension and content signature match successfully.",
        )

    def _get_extension_type(self, path: Path) -> FileType:
        """Map extension to FileType enum."""
        return EXTENSION_MAP.get(path.suffix.lower(), FileType.UNKNOWN)

    def _analyze_content(self, path: Path, expected_ext_type: FileType) -> Tuple[FileType, Optional[str]]:
        """Inspect byte signatures, OOXML OPC structure, or text heuristics."""
        try:
            with open(path, "rb") as f:
                header = f.read(2048)

            # PDF binary signature check
            if header.startswith(b"%PDF-"):
                return FileType.PDF, None

            # ZIP binary signature check for OOXML
            if header.startswith(b"PK\x03\x04"):
                return self._validate_ooxml_format(path)

            # Text / CSV heuristic check
            return self._validate_text_or_csv(path, header, expected_ext_type)

        except Exception as e:
            return FileType.UNKNOWN, f"Read error: {str(e)}"

    def _validate_ooxml_format(self, path: Path) -> Tuple[FileType, Optional[str]]:
        """Validate OOXML (DOCX, PPTX, XLSX) ZIP structure & OPC manifest."""
        try:
            with zipfile.ZipFile(path, "r") as zf:
                file_list = set(zf.namelist())

                if "[Content_Types].xml" not in file_list:
                    return FileType.UNKNOWN, "ZIP archive missing OPC [Content_Types].xml manifest."

                for file_type, marker in OOXML_MARKERS.items():
                    if marker in file_list:
                        return file_type, None

                return FileType.UNKNOWN, "Valid ZIP container, but missing OOXML package markers."

        except zipfile.BadZipFile:
            return FileType.UNKNOWN, "Starts with ZIP header but is a corrupted archive."

    def _validate_text_or_csv(
        self, path: Path, sample_bytes: bytes, expected_ext_type: FileType
    ) -> Tuple[FileType, Optional[str]]:
        """Validate plain text and CSV formats via non-binary & encoding checks + CSV heuristics."""
        if b"\x00" in sample_bytes:
            return FileType.UNKNOWN, "Binary data detected (null bytes present)."

        decoded_text = None
        for encoding in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                decoded_text = sample_bytes.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if decoded_text is None:
            return FileType.UNKNOWN, "Unable to decode text content."

        # If extension expects CSV, run delimiter heuristic check
        if expected_ext_type == FileType.CSV:
            lines = [line.strip() for line in decoded_text.splitlines() if line.strip()][:10]
            if lines:
                try:
                    sniffer = csv.Sniffer()
                    dialect = sniffer.sniff("\n".join(lines), delimiters=",;\t|")
                    if dialect.delimiter:
                        return FileType.CSV, None
                except csv.Error:
                    pass
            return FileType.CSV, None

        return FileType.TXT, None
