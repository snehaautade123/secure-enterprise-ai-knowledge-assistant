"""Validation suite for the TextChunker component."""

import sys
from src.ingestion.chunkers.models import Chunk
from src.ingestion.chunkers.text_chunker import TextChunker
from src.ingestion.extractors.models import ContentType, ExtractedElement


def test_1_normal_text_chunking():
    chunker = TextChunker(max_chunk_size=100, chunk_overlap=20)
    elem = ExtractedElement(
        element_index=0,
        content_type=ContentType.PARAGRAPH,
        text_content="This is a standard text paragraph that should fit within max_chunk_size.",
        structural_context={"paragraph_index": 1},
    )
    chunks = chunker.chunk_element(elem)
    assert len(chunks) == 1
    assert chunks[0].text == "This is a standard text paragraph that should fit within max_chunk_size."
    assert chunks[0].chunk_index == 0
    print("[OK] 1. Normal text chunking passed")


def test_2_overlap_behavior():
    chunker = TextChunker(max_chunk_size=50, chunk_overlap=15)
    long_text = "Word One Word Two Word Three Word Four Word Five Word Six Word Seven Word Eight Word Nine Word Ten"
    elem = ExtractedElement(
        element_index=1,
        content_type=ContentType.PAGE_TEXT,
        text_content=long_text,
        structural_context={"page_number": 2},
    )
    chunks = chunker.chunk_element(elem)
    assert len(chunks) > 1
    # Check that overlap words exist between chunk 0 and chunk 1
    chunk0_tail = chunks[0].text[-10:]
    chunk1_head = chunks[1].text[:25]
    assert any(word in chunk1_head for word in chunk0_tail.split())
    print("[OK] 2. Overlap behavior passed")


def test_3_empty_whitespace_filtering():
    chunker = TextChunker(max_chunk_size=100, chunk_overlap=10)
    elements = [
        ExtractedElement(0, ContentType.PARAGRAPH, "   \n\t   ", {}),
        ExtractedElement(1, ContentType.PARAGRAPH, "", {}),
        ExtractedElement(2, ContentType.PARAGRAPH, "Valid content here.", {}),
    ]
    chunks = list(chunker.chunk_element_stream(elements))
    assert len(chunks) == 1
    assert chunks[0].text == "Valid content here."
    print("[OK] 3. Empty/whitespace filtering passed")


def test_4_short_content_handling():
    chunker = TextChunker(max_chunk_size=500, chunk_overlap=50)
    elem = ExtractedElement(
        element_index=3,
        content_type=ContentType.PARAGRAPH,
        text_content="Short text.",
        structural_context={"page_number": 1},
    )
    chunks = chunker.chunk_element(elem)
    assert len(chunks) == 1
    assert chunks[0].text == "Short text."
    assert chunks[0].metadata["total_sub_chunks"] == 1
    print("[OK] 4. Short content handling passed")


def test_5_content_type_preservation():
    chunker = TextChunker(max_chunk_size=100, chunk_overlap=10)
    types_to_test = (ContentType.HEADING, ContentType.SLIDE, ContentType.TABLE, ContentType.SHEET_ROW)
    for ctype in types_to_test:
        elem = ExtractedElement(0, ctype, f"Sample content for {ctype.value}", {"context": 123})
        chunks = chunker.chunk_element(elem)
        assert len(chunks) == 1
        assert chunks[0].content_type == ctype
    print("[OK] 5. Content type preservation passed")


def test_6_structural_metadata_preservation():
    chunker = TextChunker(max_chunk_size=100, chunk_overlap=10)
    context = {"sheet_name": "SalesData", "row_index": 105, "col_count": 4}
    elem = ExtractedElement(10, ContentType.SHEET_ROW, "105 | Q3 Sales | $50000 | Confirmed", context)
    chunks = chunker.chunk_element(elem)
    assert len(chunks) == 1
    meta = chunks[0].metadata
    assert meta["element_index"] == 10
    assert meta["structural_context"]["sheet_name"] == "SalesData"
    assert meta["structural_context"]["row_index"] == 105
    assert meta["structural_context"]["col_count"] == 4
    print("[OK] 6. Structural metadata preservation passed")


def test_7_tabular_sheet_row_handling():
    chunker = TextChunker(max_chunk_size=45, chunk_overlap=10)
    table_text = "Row 1 | Cell A | Cell B\nRow 2 | Cell C | Cell D\nRow 3 | Cell E | Cell F"
    elem = ExtractedElement(0, ContentType.TABLE, table_text, {"table_index": 1})
    chunks = chunker.chunk_element(elem)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert chunk.content_type == ContentType.TABLE
    print("[OK] 7. Tabular / SHEET_ROW handling passed")


def test_8_deterministic_chunk_indices():
    chunker = TextChunker(max_chunk_size=30, chunk_overlap=5)
    elements = [
        ExtractedElement(0, ContentType.PARAGRAPH, "First paragraph text that is long.", {}),
        ExtractedElement(1, ContentType.PARAGRAPH, "Second paragraph text that is long.", {}),
    ]
    chunks1 = list(chunker.chunk_element_stream(elements, start_chunk_index=0))
    chunks2 = list(chunker.chunk_element_stream(elements, start_chunk_index=0))

    assert len(chunks1) == len(chunks2)
    indices = [c.chunk_index for c in chunks1]
    assert indices == list(range(len(chunks1)))
    for c1, c2 in zip(chunks1, chunks2):
        assert c1.chunk_index == c2.chunk_index
        assert c1.text == c2.text
    print("[OK] 8. Deterministic chunk indices passed")


def test_9_invalid_overlap_configuration():
    # Test overlap >= max_chunk_size
    try:
        TextChunker(max_chunk_size=100, chunk_overlap=100)
        assert False, "Should have raised ValueError for chunk_overlap == max_chunk_size"
    except ValueError as e:
        assert "strictly less than max_chunk_size" in str(e)

    try:
        TextChunker(max_chunk_size=100, chunk_overlap=150)
        assert False, "Should have raised ValueError for chunk_overlap > max_chunk_size"
    except ValueError as e:
        assert "strictly less than max_chunk_size" in str(e)

    # Test negative overlap
    try:
        TextChunker(max_chunk_size=100, chunk_overlap=-5)
        assert False, "Should have raised ValueError for chunk_overlap < 0"
    except ValueError as e:
        assert "non-negative" in str(e)

    # Test non-positive max_chunk_size
    try:
        TextChunker(max_chunk_size=0, chunk_overlap=0)
        assert False, "Should have raised ValueError for max_chunk_size <= 0"
    except ValueError as e:
        assert "must be positive" in str(e)

    print("[OK] 9. Invalid overlap configuration validation passed")


def run_all():
    print("=== STARTING CHUNKER VALIDATION SUITE ===")
    test_1_normal_text_chunking()
    test_2_overlap_behavior()
    test_3_empty_whitespace_filtering()
    test_4_short_content_handling()
    test_5_content_type_preservation()
    test_6_structural_metadata_preservation()
    test_7_tabular_sheet_row_handling()
    test_8_deterministic_chunk_indices()
    test_9_invalid_overlap_configuration()
    print("\n=== ALL 9 CHUNKER TESTS PASSED SUCCESSFULLY ===")


if __name__ == "__main__":
    run_all()
