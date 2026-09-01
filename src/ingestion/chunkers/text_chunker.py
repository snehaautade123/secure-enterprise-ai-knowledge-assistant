"""Text and tabular chunker module for ingestion layer."""

from typing import Any, Dict, Generator, Iterable, List

from src.ingestion.cleaners.text_cleaner import clean_text, is_meaningful_text
from src.ingestion.extractors.models import ContentType, ExtractedElement
from src.ingestion.chunkers.models import Chunk


class TextChunker:
    """Chunks ExtractedElement streams into retrieval-ready Chunk objects."""

    def __init__(
        self,
        max_chunk_size: int = 1000,
        chunk_overlap: int = 100,
        min_chunk_size: int = 1,
    ):
        if max_chunk_size <= 0:
            raise ValueError(f"max_chunk_size must be positive, got {max_chunk_size}")
        if chunk_overlap < 0:
            raise ValueError(f"chunk_overlap must be non-negative (>= 0), got {chunk_overlap}")
        if chunk_overlap >= max_chunk_size:
            raise ValueError(
                f"chunk_overlap ({chunk_overlap}) must be strictly less than max_chunk_size ({max_chunk_size})"
            )
        if min_chunk_size < 1:
            raise ValueError(f"min_chunk_size must be at least 1, got {min_chunk_size}")

        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_element(
        self, element: ExtractedElement, start_chunk_index: int = 0
    ) -> List[Chunk]:
        """Chunk a single ExtractedElement into a list of Chunk objects."""
        return list(self.chunk_element_stream([element], start_chunk_index=start_chunk_index))

    def chunk_element_stream(
        self, elements: Iterable[ExtractedElement], start_chunk_index: int = 0
    ) -> Generator[Chunk, None, None]:
        """Generator converting an iterable of ExtractedElements into Chunks deterministically."""
        chunk_idx = start_chunk_index

        for element in elements:
            cleaned = clean_text(element.text_content)
            if not is_meaningful_text(cleaned) or len(cleaned) < self.min_chunk_size:
                continue

            # Short content: fits in a single chunk
            if len(cleaned) <= self.max_chunk_size:
                metadata = self._build_metadata(element, sub_chunk_index=0, total_sub_chunks=1)
                yield Chunk(
                    chunk_index=chunk_idx,
                    text=cleaned,
                    content_type=element.content_type,
                    metadata=metadata,
                )
                chunk_idx += 1
            else:
                # Exceeds max_chunk_size -> split with overlap
                sub_texts = self._split_text(cleaned, element.content_type)
                total_sub = len(sub_texts)

                for sub_idx, sub_text in enumerate(sub_texts):
                    sub_cleaned = clean_text(sub_text)
                    if not is_meaningful_text(sub_cleaned):
                        continue

                    metadata = self._build_metadata(
                        element, sub_chunk_index=sub_idx, total_sub_chunks=total_sub
                    )
                    yield Chunk(
                        chunk_index=chunk_idx,
                        text=sub_cleaned,
                        content_type=element.content_type,
                        metadata=metadata,
                    )
                    chunk_idx += 1

    def _split_text(self, text: str, content_type: ContentType) -> List[str]:
        """Split text into sub-chunks respecting boundary conditions and overlap."""
        # For tabular/multiline structured elements (TABLE / SHEET_ROW), attempt row boundary splits
        if content_type in (ContentType.TABLE, ContentType.SHEET_ROW) and "\n" in text:
            lines = text.split("\n")
            chunks: List[str] = []
            current_lines: List[str] = []
            current_len = 0

            for line in lines:
                line_len = len(line) + 1
                if current_lines and (current_len + line_len > self.max_chunk_size):
                    chunks.append("\n".join(current_lines))
                    overlap_lines: List[str] = []
                    overlap_len = 0
                    for prev in reversed(current_lines):
                        if overlap_len + len(prev) + 1 <= self.chunk_overlap:
                            overlap_lines.insert(0, prev)
                            overlap_len += len(prev) + 1
                        else:
                            break
                    current_lines = overlap_lines
                    current_len = overlap_len

                current_lines.append(line)
                current_len += line_len

            if current_lines:
                chunks.append("\n".join(current_lines))
            return chunks

        # Sliding window text splitting for unstructured text
        chunks = []
        step = self.max_chunk_size - self.chunk_overlap
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + self.max_chunk_size
            if end >= text_len:
                chunk_str = text[start:].strip()
                if chunk_str:
                    chunks.append(chunk_str)
                break

            # Try to break at word boundary
            break_pos = text.rfind(" ", start + step, end)
            if break_pos == -1:
                break_pos = text.rfind("\n", start + step, end)
            if break_pos == -1 or break_pos <= start:
                break_pos = end

            chunk_str = text[start:break_pos].strip()
            if chunk_str:
                chunks.append(chunk_str)

            start = break_pos - self.chunk_overlap if break_pos > start + self.chunk_overlap else break_pos

        return chunks

    def _build_metadata(
        self, element: ExtractedElement, sub_chunk_index: int, total_sub_chunks: int
    ) -> Dict[str, Any]:
        """Build chunk metadata preserving original structural_context."""
        meta: Dict[str, Any] = {
            "element_index": element.element_index,
            "sub_chunk_index": sub_chunk_index,
            "total_sub_chunks": total_sub_chunks,
        }
        if element.structural_context:
            meta["structural_context"] = dict(element.structural_context)
        return meta
