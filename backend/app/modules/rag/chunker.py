import re
from dataclasses import dataclass
from typing import List, Optional

from app.modules.rag.document_processor import DocumentSection


@dataclass
class DocumentChunk:
    chunk_index: int
    text: str
    page_number: Optional[int] = None
    slide_number: Optional[int] = None


def clean_text(text: str) -> str:
    """
    Clean extracted text:
    - Normalizes line breaks (\r\n -> \n, \r -> \n)
    - Removes repeated whitespace while keeping paragraph structure
    - Reduces 3+ consecutive newlines to 2
    """
    if not text:
        return ""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    # Replace tabs with spaces
    normalized = normalized.replace("\t", " ")
    # Replace repeated spaces (2+) with a single space
    normalized = re.sub(r"[ ]{2,}", " ", normalized)
    # Replace 3+ consecutive newlines with 2 newlines
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


class DocumentChunker:
    """
    Splits extracted document sections into deterministic, overlapping chunks
    while preserving page and slide metadata.
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        if chunk_overlap >= chunk_size:
            chunk_overlap = max(0, chunk_size // 5)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_sections(self, sections: List[DocumentSection]) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        global_chunk_idx = 0

        for sec in sections:
            cleaned = clean_text(sec.text)
            if not cleaned:
                continue

            sec_chunks = self._chunk_single_text(cleaned)
            for chunk_str in sec_chunks:
                if chunk_str.strip():
                    chunks.append(
                        DocumentChunk(
                            chunk_index=global_chunk_idx,
                            text=chunk_str.strip(),
                            page_number=sec.page_number,
                            slide_number=sec.slide_number
                        )
                    )
                    global_chunk_idx += 1

        return chunks

    def _chunk_single_text(self, text: str) -> List[str]:
        if len(text) <= self.chunk_size:
            return [text]

        chunks: List[str] = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + self.chunk_size, text_len)
            
            # If not at the very end, try to find a natural break point (newline or period)
            if end < text_len:
                # Look backwards up to chunk_overlap for a paragraph or sentence break
                break_point = -1
                for sep in ("\n\n", "\n", ". ", "? ", "! ", " "):
                    last_pos = text.rfind(sep, start + (self.chunk_size // 2), end)
                    if last_pos != -1:
                        break_point = last_pos + len(sep)
                        break
                if break_point != -1 and break_point > start:
                    end = break_point

            chunk_content = text[start:end].strip()
            if chunk_content:
                chunks.append(chunk_content)

            if end >= text_len:
                break

            # Advance with overlap
            next_start = end - self.chunk_overlap
            if next_start <= start:
                next_start = start + max(1, self.chunk_size - self.chunk_overlap)
            start = next_start

        return chunks
