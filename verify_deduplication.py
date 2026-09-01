"""Validation suite for the Deduplication / Content Duplicate Detection layer."""

import tempfile
from pathlib import Path

from src.ingestion.chunkers.models import Chunk
from src.ingestion.extractors.models import ContentType
from src.ingestion.deduplication import (
    DuplicateDetector,
    DuplicateResult,
    DuplicateType,
    compute_content_hash,
    compute_file_hash,
)


def test_1_identical_content_same_fingerprint():
    text1 = "Enterprise Security Policy 2026"
    text2 = "Enterprise Security Policy 2026"
    hash1, is_valid1 = compute_content_hash(text1)
    hash2, is_valid2 = compute_content_hash(text2)

    assert is_valid1 and is_valid2
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 length
    print("[OK] 1. Identical content produces same fingerprint passed")


def test_2_different_content_different_fingerprint():
    text1 = "Enterprise Security Policy 2026"
    text2 = "Enterprise Compliance Overview 2026"
    hash1, _ = compute_content_hash(text1)
    hash2, _ = compute_content_hash(text2)

    assert hash1 != hash2
    print("[OK] 2. Different content produces different fingerprint passed")


def test_3_different_filenames_identical_content():
    detector = DuplicateDetector()

    with tempfile.NamedTemporaryFile(suffix=".txt", mode="wb", delete=False) as f1:
        f1.write(b"Binary Content Test Data 12345")
        path1 = Path(f1.name)

    with tempfile.NamedTemporaryFile(suffix=".pdf", mode="wb", delete=False) as f2:
        f2.write(b"Binary Content Test Data 12345")
        path2 = Path(f2.name)

    try:
        res1 = detector.check_and_register_file(path1, source_reference="original_file.txt")
        assert not res1.is_duplicate
        assert res1.duplicate_type == DuplicateType.NONE

        res2 = detector.check_and_register_file(path2, source_reference="copied_file.pdf")
        assert res2.is_duplicate
        assert res2.duplicate_type == DuplicateType.EXACT_FILE
        assert res2.original_source == "original_file.txt"
        assert res1.fingerprint == res2.fingerprint
        print("[OK] 3. Different filenames with identical content detected passed")
    finally:
        path1.unlink(missing_ok=True)
        path2.unlink(missing_ok=True)


def test_4_normalized_text_duplicates():
    detector = DuplicateDetector()
    text_raw = "  Data Ingestion \t Pipeline \n\n Security  "
    text_variant = "Data Ingestion Pipeline\n\nSecurity"

    res1 = detector.check_and_register_content(text_raw, source_reference="chunk_0")
    assert not res1.is_duplicate

    res2 = detector.check_and_register_content(text_variant, source_reference="chunk_1")
    assert res2.is_duplicate
    assert res2.duplicate_type == DuplicateType.NORMALIZED_CONTENT
    assert res2.original_source == "chunk_0"
    print("[OK] 4. Normalized text duplicates detected passed")


def test_5_meaningful_different_text_not_duplicate():
    detector = DuplicateDetector()
    res1 = detector.check_and_register_content("Section 1: Data Models", "chunk_0")
    res2 = detector.check_and_register_content("Section 2: Deduplication Engine", "chunk_1")

    assert not res1.is_duplicate
    assert not res2.is_duplicate
    assert res1.fingerprint != res2.fingerprint
    print("[OK] 5. Meaningful different text not marked duplicate passed")


def test_6_empty_content_handling():
    detector = DuplicateDetector()
    res1 = detector.check_and_register_content("   \n\t   ", "chunk_empty")
    assert not res1.is_duplicate
    assert res1.fingerprint == ""
    assert "Empty or whitespace-only" in res1.reason

    res2 = detector.check_and_register_content(None, "chunk_null")
    assert not res2.is_duplicate
    assert res2.fingerprint == ""
    print("[OK] 6. Empty content handling passed")


def test_7_deterministic_repeated_execution():
    detector1 = DuplicateDetector()
    detector2 = DuplicateDetector()

    text = "Deterministic Verification Standard"
    r1 = detector1.check_and_register_content(text, "ref1")
    r2 = detector2.check_and_register_content(text, "ref1")

    assert r1.fingerprint == r2.fingerprint
    print("[OK] 7. Deterministic repeated execution passed")


def test_8_explainable_reason_and_source_reference():
    detector = DuplicateDetector()
    chunk1 = Chunk(0, "Identical chunk text payload.", ContentType.PARAGRAPH, {})
    chunk2 = Chunk(1, "Identical chunk text payload.", ContentType.PARAGRAPH, {})

    res1 = detector.check_and_register_chunk(chunk1, source_file_name="doc_a.txt")
    assert not res1.is_duplicate

    res2 = detector.check_and_register_chunk(chunk2, source_file_name="doc_b.txt")
    assert res2.is_duplicate
    assert res2.duplicate_type == DuplicateType.NORMALIZED_CONTENT
    assert res2.original_source == "doc_a.txt#chunk_0"
    assert "doc_a.txt#chunk_0" in res2.reason
    print("[OK] 8. Duplicate result contains explainable reason/source reference passed")


def test_9_invalid_missing_input_handled_safely():
    detector = DuplicateDetector()
    missing_path = Path("C:/non_existent_directory_12345/missing_file.pdf")
    res = detector.check_and_register_file(missing_path)

    assert not res.is_duplicate
    assert res.duplicate_type == DuplicateType.NONE
    assert res.fingerprint == ""
    assert "File does not exist" in res.reason
    print("[OK] 9. Invalid/missing input handled safely passed")


def run_all():
    print("=== STARTING DEDUPLICATION VALIDATION SUITE ===")
    test_1_identical_content_same_fingerprint()
    test_2_different_content_different_fingerprint()
    test_3_different_filenames_identical_content()
    test_4_normalized_text_duplicates()
    test_5_meaningful_different_text_not_duplicate()
    test_6_empty_content_handling()
    test_7_deterministic_repeated_execution()
    test_8_explainable_reason_and_source_reference()
    test_9_invalid_missing_input_handled_safely()
    print("\n=== ALL 9 DEDUPLICATION TESTS PASSED SUCCESSFULLY ===")


if __name__ == "__main__":
    run_all()
