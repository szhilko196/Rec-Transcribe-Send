"""
Contextual Enrichment for Meeting Transcriptions
Implements Anthropic's Contextual Retrieval technique

This script:
1. Loads meeting files (transcript, summary, protocol)
2. Chunks documents
3. For each chunk, generates context using Claude API
4. Prepends context to chunk before embedding
5. Saves enriched files for upload to RAGFlow
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
import anthropic

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))


class ContextualEnricher:
    """Enriches document chunks with meeting context using Claude API"""

    def __init__(self, claude_api_key: str = None):
        """
        Initialize enricher with Claude API client

        Args:
            claude_api_key: Claude API key (defaults to CLAUDE_API_KEY env var)
        """
        api_key = claude_api_key or os.getenv("CLAUDE_API_KEY")
        if not api_key:
            raise ValueError("CLAUDE_API_KEY not found in environment")

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = os.getenv("CONTEXT_GENERATION_MODEL", "claude-sonnet-4-5-20250929")

        # Load context generation prompt template
        prompt_path = Path(__file__).parent.parent / "config" / "prompts" / "context_generation.txt"
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.prompt_template = f.read()

    def enrich_meeting_folder(self, result_folder: Path) -> Path:
        """
        Enrich all documents in a meeting folder with contextual information

        Args:
            result_folder: Path to meeting result folder

        Returns:
            Path to enriched folder (result_folder/enriched/)
        """
        result_folder = Path(result_folder)

        # Load meeting metadata
        metadata_path = result_folder / "metadata.json"
        if not metadata_path.exists():
            raise FileNotFoundError(f"metadata.json not found in {result_folder}")

        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        # Extract meeting info
        meeting_info = self._extract_meeting_info(metadata, result_folder)

        # Create enriched folder
        enriched_folder = result_folder / "enriched"
        enriched_folder.mkdir(exist_ok=True)

        print(f"[Contextual Enrichment] Processing meeting: {meeting_info['title']}")

        # Enrich each document type
        enriched_files = []

        # 1. Enrich transcript
        transcript_path = result_folder / "transcript_readable.txt"
        if transcript_path.exists():
            print(f"  - Enriching transcript...")
            enriched_path = self._enrich_transcript(
                transcript_path,
                meeting_info,
                enriched_folder
            )
            enriched_files.append(enriched_path)

        # 2. Enrich summary
        summary_path = result_folder / "summary.md"
        if summary_path.exists():
            print(f"  - Enriching summary...")
            enriched_path = self._enrich_summary(
                summary_path,
                meeting_info,
                enriched_folder
            )
            enriched_files.append(enriched_path)

        # 3. Enrich protocol
        protocol_path = result_folder / "protocol.md"
        if protocol_path.exists():
            print(f"  - Enriching protocol...")
            enriched_path = self._enrich_protocol(
                protocol_path,
                meeting_info,
                enriched_folder
            )
            enriched_files.append(enriched_path)

        print(f"[OK] Contextual enrichment complete: {len(enriched_files)} files enriched")
        return enriched_folder

    def _extract_meeting_info(self, metadata: Dict, result_folder: Path) -> Dict:
        """Extract meeting information from metadata"""
        folder_name = result_folder.name

        # Extract participants from transcript metadata
        speakers = []
        transcript_json_path = result_folder / "transcript_full.json"
        if transcript_json_path.exists():
            with open(transcript_json_path, 'r', encoding='utf-8') as f:
                transcript_data = json.load(f)
                speakers = transcript_data.get("metadata", {}).get("recognized_speakers", [])

        # Calculate duration in minutes
        duration_sec = metadata.get("duration", 0)
        duration_min = round(duration_sec / 60, 1)

        # Extract date from folder name or processed_at
        import re
        date_match = re.search(r'_(\d{8})_\d{6}$', folder_name)
        if date_match:
            date_str = date_match.group(1)
            meeting_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        else:
            meeting_date = datetime.now().strftime("%Y-%m-%d")

        return {
            "title": folder_name,
            "date": meeting_date,
            "duration_minutes": duration_min,
            "speakers": speakers if speakers else ["участники"],
            "speaker_list": ", ".join(speakers) if speakers else "участники встречи"
        }

    def _enrich_transcript(
        self,
        transcript_path: Path,
        meeting_info: Dict,
        output_folder: Path
    ) -> Path:
        """
        Enrich transcript by adding context to speaker turns

        Chunks transcript by speaker turns (natural chunking)
        """
        with open(transcript_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Split into chunks by speaker turns
        chunks = self._chunk_transcript(content)

        # Enrich each chunk with context
        enriched_chunks = []
        for i, chunk in enumerate(chunks):
            if i % 10 == 0 and i > 0:
                print(f"    Enriched {i}/{len(chunks)} chunks...")

            context = self._generate_context(
                chunk_text=chunk,
                meeting_info=meeting_info,
                doc_type="transcript"
            )

            enriched_chunk = f"{context}\n\n{chunk}"
            enriched_chunks.append(enriched_chunk)

        # Save enriched transcript
        output_path = output_folder / "transcript_enriched.txt"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n\n---\n\n".join(enriched_chunks))

        print(f"    Enriched {len(chunks)} transcript chunks")
        return output_path

    def _chunk_transcript(self, content: str) -> List[str]:
        """
        Chunk transcript by speaker turns

        Format expected:
        [SPEAKER_NAME]
          [timestamp] text
        """
        chunks = []
        current_chunk = []

        for line in content.split('\n'):
            # Check if line is a speaker header (starts with [)
            if line.strip().startswith('[') and line.strip().endswith(']'):
                # Save previous chunk
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []

            current_chunk.append(line)

        # Save last chunk
        if current_chunk:
            chunks.append('\n'.join(current_chunk))

        # Filter out very short chunks (< 50 chars)
        chunks = [c for c in chunks if len(c.strip()) > 50]

        return chunks

    def _enrich_summary(
        self,
        summary_path: Path,
        meeting_info: Dict,
        output_folder: Path
    ) -> Path:
        """Enrich summary as a single chunk"""
        with open(summary_path, 'r', encoding='utf-8') as f:
            content = f.read()

        context = self._generate_context(
            chunk_text=content[:500],  # Use first 500 chars for context generation
            meeting_info=meeting_info,
            doc_type="summary"
        )

        enriched_content = f"{context}\n\n{content}"

        output_path = output_folder / "summary_enriched.md"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(enriched_content)

        return output_path

    def _enrich_protocol(
        self,
        protocol_path: Path,
        meeting_info: Dict,
        output_folder: Path
    ) -> Path:
        """
        Enrich protocol by sections

        Chunks by markdown sections (## headers)
        """
        with open(protocol_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Split into sections
        sections = self._chunk_protocol(content)

        # Enrich each section
        enriched_sections = []
        for section_name, section_content in sections:
            context = self._generate_context(
                chunk_text=section_content[:500],
                meeting_info=meeting_info,
                doc_type=f"protocol-{section_name}"
            )

            enriched_section = f"{context}\n\n{section_content}"
            enriched_sections.append(enriched_section)

        # Save enriched protocol
        output_path = output_folder / "protocol_enriched.md"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n\n".join(enriched_sections))

        print(f"    Enriched {len(sections)} protocol sections")
        return output_path

    def _chunk_protocol(self, content: str) -> List[Tuple[str, str]]:
        """
        Chunk protocol by markdown sections

        Returns list of (section_name, section_content) tuples
        """
        import re

        sections = []
        current_section = "OVERVIEW"
        current_content = []

        for line in content.split('\n'):
            # Check for section header (## Number. SECTION_NAME)
            match = re.match(r'^##\s+\d+\.\s+\*?\*?(.+?)\*?\*?\s*$', line)
            if match:
                # Save previous section
                if current_content:
                    sections.append((current_section, '\n'.join(current_content)))

                # Start new section
                current_section = match.group(1).strip().upper()
                current_content = [line]
            else:
                current_content.append(line)

        # Save last section
        if current_content:
            sections.append((current_section, '\n'.join(current_content)))

        return sections

    def _generate_context(
        self,
        chunk_text: str,
        meeting_info: Dict,
        doc_type: str
    ) -> str:
        """
        Generate context for a chunk using Claude API

        Args:
            chunk_text: Text chunk to generate context for
            meeting_info: Meeting metadata
            doc_type: Type of document (transcript/summary/protocol)

        Returns:
            Generated context (1-2 sentences in Russian)
        """
        # Format prompt with meeting info
        prompt = self.prompt_template.format(
            meeting_title=meeting_info['title'],
            meeting_date=meeting_info['date'],
            duration_minutes=meeting_info['duration_minutes'],
            speaker_list=meeting_info['speaker_list'],
            doc_type=doc_type,
            chunk_text=chunk_text[:500]  # Limit chunk text for prompt
        )

        try:
            # Call Claude API
            message = self.client.messages.create(
                model=self.model,
                max_tokens=150,  # Short response
                temperature=0.3,  # Low temperature for consistency
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            context = message.content[0].text.strip()
            return context

        except Exception as e:
            print(f"    [WARNING] Context generation failed: {e}")
            # Fallback: simple context without Claude API
            return f"Встреча: {meeting_info['title']}, {meeting_info['date']}"


def main():
    """CLI entry point"""
    if len(sys.argv) < 2:
        print("Usage: python contextual_enrichment.py <result_folder>")
        print("Example: python contextual_enrichment.py C:/path/to/meeting_2025-01-15_143022")
        sys.exit(1)

    result_folder = Path(sys.argv[1])

    if not result_folder.exists():
        print(f"Error: Folder not found: {result_folder}")
        sys.exit(1)

    # Initialize enricher
    enricher = ContextualEnricher()

    # Enrich documents
    enriched_folder = enricher.enrich_meeting_folder(result_folder)

    print(f"\n[SUCCESS] Enriched files saved to: {enriched_folder}")


if __name__ == "__main__":
    main()
