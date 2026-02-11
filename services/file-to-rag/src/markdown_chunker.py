"""
Markdown Chunker

Splits markdown files into chunks for RAG processing.
Two strategies:
- By headers: Split on ## (H2) headers, keeping header with content
- By lines: Split every N lines (fallback for unstructured text)
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class Chunk:
    """A chunk of markdown content"""
    content: str
    index: int
    total: int
    source_file: str
    header: Optional[str] = None

    def with_metadata(self) -> str:
        """Return content with metadata comment prepended"""
        meta = f"<!-- File: {self.source_file} | Chunk: {self.index}/{self.total} -->\n\n"
        return meta + self.content


class MarkdownChunker:
    """Splits markdown files into chunks"""

    def __init__(self, chunk_by_headers: bool = True, chunk_size_lines: int = 150):
        """
        Initialize chunker

        Args:
            chunk_by_headers: If True, split on ## headers. If False, split by lines.
            chunk_size_lines: Number of lines per chunk (used when chunk_by_headers=False
                            or as max size for header-based chunks)
        """
        self.chunk_by_headers = chunk_by_headers
        self.chunk_size_lines = chunk_size_lines

    def chunk_file(self, file_path: Path) -> List[Chunk]:
        """
        Split markdown file into chunks

        Args:
            file_path: Path to markdown file

        Returns:
            List of Chunk objects
        """
        content = file_path.read_text(encoding='utf-8')
        source_name = file_path.name

        if self.chunk_by_headers:
            chunks = self._chunk_by_headers(content, source_name)
            # If only one chunk or headers didn't work well, fall back to lines
            if len(chunks) <= 1 and len(content.split('\n')) > self.chunk_size_lines:
                chunks = self._chunk_by_lines(content, source_name)
        else:
            chunks = self._chunk_by_lines(content, source_name)

        return chunks

    def _chunk_by_headers(self, content: str, source_name: str) -> List[Chunk]:
        """
        Split content by ## (H2) headers

        Each section becomes a chunk with its header included.
        Sections smaller than 20 lines are merged with the next section.
        """
        # Split on H2 headers (##), keeping the header
        # Pattern matches ## at start of line
        sections = re.split(r'(?=^## )', content, flags=re.MULTILINE)

        # Filter empty sections and strip whitespace
        sections = [s.strip() for s in sections if s.strip()]

        if not sections:
            return [Chunk(
                content=content,
                index=1,
                total=1,
                source_file=source_name
            )]

        # Merge small sections with the next one
        merged_sections = []
        buffer = ""

        for section in sections:
            if buffer:
                # Check if adding this section would exceed limit
                combined = buffer + "\n\n" + section
                if len(combined.split('\n')) > self.chunk_size_lines:
                    # Buffer is big enough, save it
                    merged_sections.append(buffer)
                    buffer = section
                else:
                    buffer = combined
            else:
                buffer = section

            # If buffer is large enough on its own, save it
            if len(buffer.split('\n')) >= self.chunk_size_lines:
                merged_sections.append(buffer)
                buffer = ""

        # Don't forget the last buffer
        if buffer:
            # If buffer is too small and we have previous sections, merge with last
            if len(buffer.split('\n')) < 20 and merged_sections:
                merged_sections[-1] = merged_sections[-1] + "\n\n" + buffer
            else:
                merged_sections.append(buffer)

        # Create Chunk objects
        total = len(merged_sections)
        chunks = []
        for i, section in enumerate(merged_sections, 1):
            # Extract header if present
            header = None
            header_match = re.match(r'^(## .+)$', section, re.MULTILINE)
            if header_match:
                header = header_match.group(1)

            chunks.append(Chunk(
                content=section,
                index=i,
                total=total,
                source_file=source_name,
                header=header
            ))

        return chunks

    def _chunk_by_lines(self, content: str, source_name: str) -> List[Chunk]:
        """
        Split content by number of lines

        Simple line-based splitting with optional overlap.
        """
        lines = content.split('\n')
        total_lines = len(lines)

        if total_lines <= self.chunk_size_lines:
            return [Chunk(
                content=content,
                index=1,
                total=1,
                source_file=source_name
            )]

        chunks = []
        chunk_index = 1

        for i in range(0, total_lines, self.chunk_size_lines):
            chunk_lines = lines[i:i + self.chunk_size_lines]
            chunk_content = '\n'.join(chunk_lines)

            # Calculate total chunks
            total_chunks = (total_lines + self.chunk_size_lines - 1) // self.chunk_size_lines

            chunks.append(Chunk(
                content=chunk_content,
                index=chunk_index,
                total=total_chunks,
                source_file=source_name
            ))
            chunk_index += 1

        return chunks


if __name__ == "__main__":
    # Simple test
    import sys

    if len(sys.argv) < 2:
        print("Usage: python markdown_chunker.py <file.md>")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"File not found: {file_path}")
        sys.exit(1)

    chunker = MarkdownChunker(chunk_by_headers=True, chunk_size_lines=150)
    chunks = chunker.chunk_file(file_path)

    print(f"File: {file_path.name}")
    print(f"Total chunks: {len(chunks)}")
    print("-" * 40)

    for chunk in chunks:
        lines = len(chunk.content.split('\n'))
        header_info = f" - {chunk.header}" if chunk.header else ""
        print(f"Chunk {chunk.index}/{chunk.total}: {lines} lines{header_info}")
