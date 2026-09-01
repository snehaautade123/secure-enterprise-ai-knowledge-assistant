"""Factory for resolving format-specific extractor instances using lazy imports."""

from src.ingestion.detectors.base import FileType
from src.ingestion.extractors.base import BaseExtractor


class ExtractorFactory:
    """Factory to retrieve format extractor instances dynamically without circular imports."""

    @classmethod
    def get_extractor(cls, file_type: FileType) -> BaseExtractor:
        """
        Instantiate and return the BaseExtractor implementation for the specified FileType.

        Args:
            file_type: Target FileType enum.

        Returns:
            Instance of concrete BaseExtractor subclass.

        Raises:
            ValueError: If file_type is unsupported or UNKNOWN.
        """
        if file_type == FileType.PDF:
            from src.ingestion.extractors.pdf_extractor import PDFExtractor
            return PDFExtractor()

        elif file_type == FileType.DOCX:
            from src.ingestion.extractors.docx_extractor import DOCXExtractor
            return DOCXExtractor()

        elif file_type == FileType.PPTX:
            from src.ingestion.extractors.pptx_extractor import PPTXExtractor
            return PPTXExtractor()

        elif file_type == FileType.TXT:
            from src.ingestion.extractors.txt_extractor import TXTExtractor
            return TXTExtractor()

        elif file_type == FileType.CSV:
            from src.ingestion.extractors.csv_extractor import CSVExtractor
            return CSVExtractor()

        elif file_type == FileType.XLSX:
            from src.ingestion.extractors.xlsx_extractor import XLSXExtractor
            return XLSXExtractor()

        else:
            raise ValueError(f"No extractor implementation available for FileType: '{file_type}'")
