"""End-to-end validation suite for Person 1 Data Ingestion Pipeline."""

import tempfile
from pathlib import Path

from src.ingestion.pipeline import IngestionPipeline, IngestionStatus
from src.ingestion.detectors.base import DetectionStatus
from src.ingestion.extractors.models import ContentType


def test_1_supported_document_end_to_end_flow():
    pipeline = IngestionPipeline()
    content = "Header Document Title\n\nThis is paragraph one of the enterprise security policy.\n\nThis is paragraph two."

    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", encoding="utf-8", delete=False) as f:
        f.write(content)
        path = Path(f.name)

    try:
        res = pipeline.process_file(path)
        assert res.status == IngestionStatus.SUCCESS
        assert res.detected_type == "txt"
        assert len(res.chunks) > 0
        assert res.doc_id != ""
        print("[OK] 1. Supported text document flows through complete pipeline passed")
    finally:
        path.unlink(missing_ok=True)


def test_2_all_layers_connected():
    pipeline = IngestionPipeline()
    csv_content = "ID,Name,Role\n1,Alice,Engineer\n2,Bob,Manager"

    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", encoding="utf-8", delete=False) as f:
        f.write(csv_content)
        path = Path(f.name)

    try:
        res = pipeline.process_file(path)
        assert res.detection_result is not None
        assert res.detection_result.status == DetectionStatus.VALID
        assert res.detected_type == "csv"

        # Verify chunks received metadata and deduplication tracking
        assert len(res.chunks) > 0
        first_chunk = res.chunks[0]
        assert "doc_id" in first_chunk.metadata
        assert "source_name" in first_chunk.metadata
        assert len(res.chunk_duplicate_infos) == len(res.chunks)
        print("[OK] 2. All Person 1 layers connected end-to-end passed")
    finally:
        path.unlink(missing_ok=True)


def test_3_final_output_contains_valid_chunks():
    pipeline = IngestionPipeline()
    text = "Section 1: Data Protection Principles\n\nAll personal data must be processed lawfully, fairly, and in a transparent manner."

    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", encoding="utf-8", delete=False) as f:
        f.write(text)
        path = Path(f.name)

    try:
        res = pipeline.process_file(path)
        for chunk in res.chunks:
            assert len(chunk.text) > 0
            assert chunk.text.strip() == chunk.text  # Text was cleaned
            assert "source_name" in chunk.metadata
            assert "doc_id" in chunk.metadata
        print("[OK] 3. Final output contains non-empty cleaned chunks with metadata passed")
    finally:
        path.unlink(missing_ok=True)


def test_4_content_type_and_structural_context_survival():
    pipeline = IngestionPipeline()
    csv_text = "ColA,ColB\nValA,ValB"

    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", encoding="utf-8", delete=False) as f:
        f.write(csv_text)
        path = Path(f.name)

    try:
        res = pipeline.process_file(path)
        assert len(res.chunks) > 0
        chunk = res.chunks[0]
        assert chunk.content_type == ContentType.SHEET_ROW
        assert "row_index" in chunk.metadata["structural_context"]
        print("[OK] 4. Content type and structural context survive full pipeline passed")
    finally:
        path.unlink(missing_ok=True)


def test_5_duplicate_content_identification():
    pipeline = IngestionPipeline()
    content = "Identical Binary and Content Payload Test"

    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", encoding="utf-8", delete=False) as f1:
        f1.write(content)
        path1 = Path(f1.name)

    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", encoding="utf-8", delete=False) as f2:
        f2.write(content)
        path2 = Path(f2.name)

    try:
        res1 = pipeline.process_file(path1)
        assert res1.status == IngestionStatus.SUCCESS

        res2 = pipeline.process_file(path2)
        assert res2.status == IngestionStatus.SKIPPED_DUPLICATE
        assert res2.file_duplicate_info is not None
        assert res2.file_duplicate_info.is_duplicate
        assert "Exact binary file duplicate" in res2.error_message
        print("[OK] 5. Duplicate content correctly identified and reported passed")
    finally:
        path1.unlink(missing_ok=True)
        path2.unlink(missing_ok=True)


def test_6_empty_meaningless_input_handling():
    pipeline = IngestionPipeline()
    content = "   \n\t   \n   "

    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", encoding="utf-8", delete=False) as f:
        f.write(content)
        path = Path(f.name)

    try:
        res = pipeline.process_file(path)
        assert res.status == IngestionStatus.SUCCESS
        assert len(res.chunks) == 0  # No fake chunks created
        print("[OK] 6. Empty/meaningless input creates 0 fake chunks passed")
    finally:
        path.unlink(missing_ok=True)


def test_7_unsupported_invalid_input_fails_safely():
    pipeline = IngestionPipeline()

    # Invalid non-existent file path
    missing_path = Path("C:/invalid_non_existent_folder/missing.pdf")
    res1 = pipeline.process_file(missing_path)
    assert res1.status == IngestionStatus.FAILED
    assert "Detection failed" in res1.error_message

    # Unsupported file extension (e.g. .exe file signature/extension)
    with tempfile.NamedTemporaryFile(suffix=".exe", mode="wb", delete=False) as f:
        f.write(b"MZ1234567890")
        exe_path = Path(f.name)

    try:
        res2 = pipeline.process_file(exe_path)
        assert res2.status == IngestionStatus.FAILED
        assert "Detection failed" in res2.error_message
        print("[OK] 7. Unsupported/invalid input fails safely passed")
    finally:
        exe_path.unlink(missing_ok=True)


def test_8_deterministic_repeated_execution():
    pipeline1 = IngestionPipeline()
    pipeline2 = IngestionPipeline()
    content = "Deterministic Execution Verification Text"

    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", encoding="utf-8", delete=False) as f:
        f.write(content)
        path = Path(f.name)

    try:
        res1 = pipeline1.process_file(path)
        res2 = pipeline2.process_file(path)

        assert res1.doc_id == res2.doc_id
        assert len(res1.chunks) == len(res2.chunks)
        assert res1.chunks[0].text == res2.chunks[0].text
        assert res1.chunks[0].metadata["doc_id"] == res2.chunks[0].metadata["doc_id"]
        print("[OK] 8. Deterministic repeated execution produces consistent results passed")
    finally:
        path.unlink(missing_ok=True)


def test_9_contracts_not_bypassed():
    pipeline = IngestionPipeline()
    content = "Contract integrity check paragraph."

    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", encoding="utf-8", delete=False) as f:
        f.write(content)
        path = Path(f.name)

    try:
        res = pipeline.process_file(path)
        # Verify detection object contract is present
        assert res.detection_result.detected_type.value == res.detected_type
        # Verify chunk model contract matches expected fields
        chunk = res.chunks[0]
        assert hasattr(chunk, "chunk_index")
        assert hasattr(chunk, "text")
        assert hasattr(chunk, "content_type")
        assert hasattr(chunk, "metadata")
        print("[OK] 9. Existing layer contracts are strictly preserved passed")
    finally:
        path.unlink(missing_ok=True)


def run_all():
    print("=== STARTING END-TO-END PIPELINE VALIDATION SUITE ===")
    test_1_supported_document_end_to_end_flow()
    test_2_all_layers_connected()
    test_3_final_output_contains_valid_chunks()
    test_4_content_type_and_structural_context_survival()
    test_5_duplicate_content_identification()
    test_6_empty_meaningless_input_handling()
    test_7_unsupported_invalid_input_fails_safely()
    test_8_deterministic_repeated_execution()
    test_9_contracts_not_bypassed()
    print("\n=== ALL 9 END-TO-END PIPELINE TESTS PASSED SUCCESSFULLY ===")


if __name__ == "__main__":
    run_all()
