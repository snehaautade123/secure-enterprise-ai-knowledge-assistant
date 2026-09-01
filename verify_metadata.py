"""Validation suite for the Metadata enrichment layer."""

from pathlib import Path
from src.ingestion.chunkers.models import Chunk
from src.ingestion.detectors.base import FileType
from src.ingestion.extractors.models import ContentType
from src.ingestion.metadata import DocumentMetadata, MetadataEnricher, generate_doc_id


def test_1_required_source_file_metadata():
    chunk = Chunk(chunk_index=0, text="Sample text", content_type=ContentType.PARAGRAPH, metadata={"element_index": 2})
    path = "C:/docs/report.pdf"
    enriched = MetadataEnricher.enrich_chunk(chunk, file_path=path, file_type=FileType.PDF)

    meta = enriched.metadata
    assert meta["source_name"] == "report.pdf"
    assert meta["source_path"] == "C:/docs/report.pdf"
    assert meta["file_type"] == "pdf"
    assert "doc_id" in meta
    print("[OK] 1. Required source/file metadata passed")


def test_2_content_type_preservation():
    for ctype in (ContentType.PARAGRAPH, ContentType.HEADING, ContentType.TABLE, ContentType.SHEET_ROW, ContentType.SLIDE):
        chunk = Chunk(chunk_index=1, text="Content text", content_type=ctype, metadata={})
        enriched = MetadataEnricher.enrich_chunk(chunk, file_path="doc.txt", file_type="txt")
        assert enriched.metadata["content_type"] == ctype.value
        assert enriched.content_type == ctype
    print("[OK] 2. Content type preservation passed")


def test_3_element_chunk_index_preservation():
    chunk = Chunk(chunk_index=42, text="Data content", content_type=ContentType.LINE_BLOCK, metadata={"element_index": 7})
    enriched = MetadataEnricher.enrich_chunk(chunk, file_path="data.txt", file_type=FileType.TXT)

    assert enriched.chunk_index == 42
    assert enriched.metadata["chunk_index"] == 42
    assert enriched.metadata["element_index"] == 7
    print("[OK] 3. Element and chunk index preservation passed")


def test_4_structural_context_preservation():
    raw_struct = {"page_number": 3, "custom_tag": "tag123", "bbox": [0, 0, 100, 100]}
    chunk = Chunk(
        chunk_index=0,
        text="Page 3 content",
        content_type=ContentType.PAGE_TEXT,
        metadata={"element_index": 1, "structural_context": raw_struct},
    )
    enriched = MetadataEnricher.enrich_chunk(chunk, file_path="file.pdf", file_type=FileType.PDF)

    assert enriched.metadata["structural_context"] == raw_struct
    assert enriched.metadata["structural_context"]["custom_tag"] == "tag123"
    print("[OK] 4. Structural context preservation passed")


def test_5_page_slide_sheet_metadata():
    # PDF page
    chunk_pdf = Chunk(0, "PDF text", ContentType.PAGE_TEXT, {"structural_context": {"page_number": 12}})
    en_pdf = MetadataEnricher.enrich_chunk(chunk_pdf, "doc.pdf", FileType.PDF)
    assert en_pdf.metadata["page_number"] == 12

    # PPTX slide
    chunk_pptx = Chunk(1, "Slide text", ContentType.SLIDE, {"structural_context": {"slide_number": 4, "slide_title": "Summary"}})
    en_pptx = MetadataEnricher.enrich_chunk(chunk_pptx, "pres.pptx", FileType.PPTX)
    assert en_pptx.metadata["slide_number"] == 4
    assert en_pptx.metadata["slide_title"] == "Summary"

    # XLSX sheet
    chunk_xlsx = Chunk(2, "Cell row", ContentType.SHEET_ROW, {"structural_context": {"sheet_name": "Q3_Sales", "row_index": 50}})
    en_xlsx = MetadataEnricher.enrich_chunk(chunk_xlsx, "data.xlsx", FileType.XLSX)
    assert en_xlsx.metadata["sheet_name"] == "Q3_Sales"
    assert en_xlsx.metadata["row_index"] == 50
    print("[OK] 5. Page/slide/sheet metadata when available passed")


def test_6_deterministic_metadata_generation():
    path_str = "C:/enterprise/secure_doc.docx"
    id1 = generate_doc_id(path_str)
    id2 = generate_doc_id(path_str)
    assert id1 == id2
    assert len(id1) == 16

    chunk = Chunk(0, "Test text", ContentType.PARAGRAPH, {})
    en1 = MetadataEnricher.enrich_chunk(chunk, path_str, FileType.DOCX)
    en2 = MetadataEnricher.enrich_chunk(chunk, path_str, FileType.DOCX)
    assert en1.metadata["doc_id"] == en2.metadata["doc_id"] == id1
    print("[OK] 6. Deterministic metadata generation passed")


def test_7_no_fabricated_metadata():
    # A TXT chunk with no page/slide/sheet context
    chunk = Chunk(0, "Plain txt line", ContentType.LINE_BLOCK, {"structural_context": {"start_line": 1, "end_line": 10}})
    enriched = MetadataEnricher.enrich_chunk(chunk, "notes.txt", FileType.TXT)
    meta = enriched.metadata

    # Absent fields must NOT be fabricated or present in dict if None
    assert "page_number" not in meta
    assert "slide_number" not in meta
    assert "sheet_name" not in meta
    assert "row_index" not in meta
    assert meta["start_line"] == 1
    assert meta["end_line"] == 10
    print("[OK] 7. No fabricated metadata passed")


def test_8_handling_missing_optional_metadata():
    # Bare chunk with completely empty metadata dict
    chunk = Chunk(0, "Bare text", ContentType.PARAGRAPH, metadata={})
    enriched = MetadataEnricher.enrich_chunk(chunk, "plain.txt", FileType.TXT)

    meta = enriched.metadata
    assert meta["source_name"] == "plain.txt"
    assert meta["file_type"] == "txt"
    assert meta["chunk_index"] == 0
    assert meta["element_index"] == 0
    assert meta["structural_context"] == {}
    print("[OK] 8. Handling of missing optional metadata passed")


def run_all():
    print("=== STARTING METADATA LAYER VALIDATION SUITE ===")
    test_1_required_source_file_metadata()
    test_2_content_type_preservation()
    test_3_element_chunk_index_preservation()
    test_4_structural_context_preservation()
    test_5_page_slide_sheet_metadata()
    test_6_deterministic_metadata_generation()
    test_7_no_fabricated_metadata()
    test_8_handling_missing_optional_metadata()
    print("\n=== ALL 8 METADATA TESTS PASSED SUCCESSFULLY ===")


if __name__ == "__main__":
    run_all()
