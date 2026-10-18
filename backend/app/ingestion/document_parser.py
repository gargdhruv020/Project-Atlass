"""
Document Extractor & Chunker
Supports PDF, HTML, Markdown, and TXT parsing with page tracking,
metadata validation, and deterministic stable chunk identifiers.
"""

import re
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

class ExtractedPage:
    def __init__(self, page_number: int, text: str):
        self.page_number = page_number
        self.text = text

class DocumentChunk:
    def __init__(self, chunk_id: str, content: str, metadata: Dict[str, Any]):
        self.chunk_id = chunk_id
        self.content = content
        self.metadata = metadata

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "metadata": self.metadata
        }

class DocumentParser:
    """
    Parses PDF, HTML, and Markdown documents into page-aware text representations
    with comprehensive metadata extraction.
    """
    REQUIRED_METADATA = ["report_id", "sector", "region", "year"]

    @classmethod
    def parse_file(cls, file_path: Path) -> Tuple[List[ExtractedPage], Dict[str, Any], List[str]]:
        """
        Parses a file and returns:
        - List of ExtractedPage (page number and text content)
        - Extracted metadata dictionary
        - List of missing metadata field warnings
        """
        ext = file_path.suffix.lower()
        if ext == ".pdf":
            return cls._parse_pdf(file_path)
        elif ext in [".html", ".htm"]:
            return cls._parse_html(file_path)
        elif ext in [".md", ".markdown", ".txt"]:
            return cls._parse_markdown(file_path)
        else:
            raise ValueError(f"Unsupported file format '{ext}' for file: {file_path.name}")

    @classmethod
    def _parse_pdf(cls, file_path: Path) -> Tuple[List[ExtractedPage], Dict[str, Any], List[str]]:
        import pypdf
        reader = pypdf.PdfReader(str(file_path))
        pages = []
        full_text = ""
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            pages.append(ExtractedPage(page_number=i + 1, text=page_text))
            full_text += "\n" + page_text

        metadata = cls._extract_metadata_from_text(full_text, fallback_name=file_path.stem)
        # Check PDF doc info
        if reader.metadata:
            if reader.metadata.title and "title" not in metadata:
                metadata["title"] = reader.metadata.title
            if reader.metadata.author and "publisher" not in metadata:
                metadata["publisher"] = reader.metadata.author

        missing = [f for f in cls.REQUIRED_METADATA if not metadata.get(f)]
        return pages, metadata, missing

    @classmethod
    def _parse_html(cls, file_path: Path) -> Tuple[List[ExtractedPage], Dict[str, Any], List[str]]:
        from bs4 import BeautifulSoup
        raw_html = file_path.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(raw_html, "html.parser")

        metadata: Dict[str, Any] = {}
        # 1. Parse <meta> tags
        for tag in soup.find_all("meta"):
            name = (tag.get("name") or tag.get("property") or "").lower()
            content = tag.get("content")
            if not content:
                continue
            if name in ["report-id", "report_id"]:
                metadata["report_id"] = content.strip().upper()
            elif name == "title":
                metadata["title"] = content.strip()
            elif name == "publisher":
                metadata["publisher"] = content.strip()
            elif name == "published":
                metadata["published"] = content.strip()
            elif name == "sector":
                metadata["sector"] = content.strip()
            elif name == "region":
                metadata["region"] = content.strip()
            elif name == "year":
                metadata["year"] = content.strip()
            elif name == "access":
                metadata["access"] = content.strip()

        # 2. Parse title tag if title not in meta
        if "title" not in metadata and soup.title and soup.title.string:
            metadata["title"] = soup.title.string.strip()

        # Extract text while preserving text content (including any trap instructions)
        text_content = soup.get_text(separator="\n", strip=True)

        # Fallback metadata from text if missing
        fallback_meta = cls._extract_metadata_from_text(text_content, fallback_name=file_path.stem)
        for k, v in fallback_meta.items():
            if k not in metadata:
                metadata[k] = v

        pages = [ExtractedPage(page_number=1, text=text_content)]
        missing = [f for f in cls.REQUIRED_METADATA if not metadata.get(f)]
        return pages, metadata, missing

    @classmethod
    def _parse_markdown(cls, file_path: Path) -> Tuple[List[ExtractedPage], Dict[str, Any], List[str]]:
        raw_text = file_path.read_text(encoding="utf-8", errors="ignore")
        metadata = cls._extract_metadata_from_text(raw_text, fallback_name=file_path.stem)

        # Split into pages by form-feed or explicit pagebreak marker if present
        if "\x0c" in raw_text:
            raw_pages = raw_text.split("\x0c")
        elif "<!-- pagebreak -->" in raw_text:
            raw_pages = raw_text.split("<!-- pagebreak -->")
        else:
            raw_pages = [raw_text]

        pages = [ExtractedPage(page_number=idx + 1, text=p.strip()) for idx, p in enumerate(raw_pages)]
        missing = [f for f in cls.REQUIRED_METADATA if not metadata.get(f)]
        return pages, metadata, missing

    @classmethod
    def _extract_metadata_from_text(cls, text: str, fallback_name: str = "") -> Dict[str, Any]:
        """Extracts structured metadata fields using regex patterns."""
        meta: Dict[str, Any] = {}

        # Report ID (e.g. R-101, R-102)
        match_id = re.search(r"(?:Report\s*ID|report_id)[*\s_]*[:=]\s*(?:[*_]*\s*)(R-\d{3})", text, re.IGNORECASE)
        if match_id:
            meta["report_id"] = match_id.group(1).upper()
        else:
            match_file_id = re.search(r"\b(R-\d{3})\b", fallback_name, re.IGNORECASE)
            if match_file_id:
                meta["report_id"] = match_file_id.group(1).upper()

        # Sector
        match_sector = re.search(r"Sector[*\s_]*[:=]\s*(?:[*_]*\s*)([^\n\r]+)", text, re.IGNORECASE)
        if match_sector:
            meta["sector"] = match_sector.group(1).strip(" *#_`")

        # Region
        match_region = re.search(r"Region[*\s_]*[:=]\s*(?:[*_]*\s*)([^\n\r]+)", text, re.IGNORECASE)
        if match_region:
            meta["region"] = match_region.group(1).strip(" *#_`")

        # Year / Published
        match_year = re.search(r"(?:Year|Published|Publication\s*Date)[*\s_]*[:=]\s*(?:[*_]*\s*)([^\n\r]+)", text, re.IGNORECASE)
        if match_year:
            year_match = re.search(r"\b(20\d{2})\b", match_year.group(1))
            if year_match:
                meta["year"] = year_match.group(1)
        if "year" not in meta:
            year_in_title = re.search(r"\b(20\d{2})\b", text[:300])
            if year_in_title:
                meta["year"] = year_in_title.group(1)

        # Title (first Markdown H1 header or title line)
        match_title = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if match_title:
            meta["title"] = match_title.group(1).strip(" *#_`")

        # Publisher
        match_pub = re.search(r"Publisher[*\s_]*[:=]\s*(?:[*_]*\s*)([^\n\r]+)", text, re.IGNORECASE)
        if match_pub:
            meta["publisher"] = match_pub.group(1).strip(" *#_`")

        return meta

class DocumentChunker:
    """
    Splits document text into retrieval-friendly chunks with configurable size and overlap.
    Generates stable, deterministic identifiers to prevent duplicate vector entries.
    """
    def __init__(self, chunk_size: int = 400, chunk_overlap: int = 40):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_pages(
        self,
        pages: List[ExtractedPage],
        report_metadata: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """
        Chunks text while tracking exact page numbers and generating stable chunk IDs.
        """
        report_id = report_metadata.get("report_id", "UNKNOWN")
        chunks: List[DocumentChunk] = []

        global_chunk_idx = 0
        for page in pages:
            words = page.text.split()
            if not words:
                continue

            i = 0
            page_chunk_idx = 0
            while i < len(words):
                chunk_words = words[i:i + self.chunk_size]
                chunk_text = " ".join(chunk_words)

                # Generate stable, deterministic chunk ID
                content_hash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()[:8]
                chunk_id = f"{report_id}_p{page.page_number}_c{page_chunk_idx}_{content_hash}"

                chunk_meta = {
                    "report_id": report_id,
                    "title": report_metadata.get("title", ""),
                    "publisher": report_metadata.get("publisher", ""),
                    "sector": report_metadata.get("sector", "Unspecified"),
                    "region": report_metadata.get("region", "Global"),
                    "year": report_metadata.get("year", "2025"),
                    "page": page.page_number,
                    "chunk_index": page_chunk_idx,
                    "is_synthetic": "synthetic" in (report_metadata.get("title", "") + report_id).lower()
                }

                chunks.append(DocumentChunk(
                    chunk_id=chunk_id,
                    content=chunk_text,
                    metadata=chunk_meta
                ))

                page_chunk_idx += 1
                global_chunk_idx += 1
                if i + self.chunk_size >= len(words):
                    break
                i += (self.chunk_size - self.chunk_overlap)

        return chunks
