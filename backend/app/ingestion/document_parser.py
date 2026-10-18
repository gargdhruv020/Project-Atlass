"""
Document Ingestion & Parser
Loads and chunks research report files from documents/ directory for vector embedding.
"""

from pathlib import Path
from typing import List, Dict, Any

class DocumentChunk:
    def __init__(self, content: str, metadata: Dict[str, Any]):
        self.content = content
        self.metadata = metadata

class DocumentParser:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def parse_text_file(self, file_path: Path) -> List[DocumentChunk]:
        """Read a text or markdown file and split into chunks."""
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        return self.chunk_text(text, metadata={"source": file_path.name, "path": str(file_path)})

    def chunk_text(self, text: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
        """Simple deterministic sliding window chunker."""
        words = text.split()
        chunks = []
        i = 0
        chunk_idx = 0
        while i < len(words):
            chunk_words = words[i:i + self.chunk_size]
            chunk_content = " ".join(chunk_words)
            chunk_meta = dict(metadata)
            chunk_meta["chunk_id"] = chunk_idx
            chunks.append(DocumentChunk(content=chunk_content, metadata=chunk_meta))
            i += (self.chunk_size - self.chunk_overlap)
            chunk_idx += 1
        return chunks
