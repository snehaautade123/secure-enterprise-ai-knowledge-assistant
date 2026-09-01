"""Metadata extraction and enrichment subpackage."""

from src.ingestion.metadata.enricher import MetadataEnricher, generate_doc_id
from src.ingestion.metadata.models import DocumentMetadata

__all__ = [
    "DocumentMetadata",
    "MetadataEnricher",
    "generate_doc_id",
]
