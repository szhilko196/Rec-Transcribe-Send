#!/usr/bin/env python3
"""
OpenWebUI Uploader

Uploads meeting transcripts to OpenWebUI Knowledge Base with Contextual Retrieval.
Called by orchestrator.py after meeting processing completes.

Usage:
    python openwebui_uploader.py <result_folder>

Environment Variables:
    OPENWEBUI_URL: OpenWebUI service URL (default: http://localhost:3000)
    OPENWEBUI_API_KEY: API key for authentication (required)
    ENABLE_CONTEXTUAL_RETRIEVAL: Enable contextual enrichment (default: true)
    CONTEXT_GENERATION_MODEL: Claude model for context generation
    CLAUDE_API_KEY: Anthropic API key (required if contextual enrichment enabled)
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import json

# Load .env from project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"
if ENV_FILE.exists():
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE)

# Add parent directory to path for imports
SCRIPT_DIR = Path(__file__).parent
sys.path.append(str(SCRIPT_DIR))

from contextual_enrichment import ContextualEnricher
from openwebui_client import OpenWebUIClient
from bank_kb_resolver import BankKBResolver


# Configuration from environment variables
OPENWEBUI_URL = os.getenv("OPENWEBUI_URL", "http://localhost:3000")
OPENWEBUI_API_KEY = os.getenv("OPENWEBUI_API_KEY")
ENABLE_CONTEXTUAL_RETRIEVAL = os.getenv("ENABLE_CONTEXTUAL_RETRIEVAL", "true").lower() == "true"
ENABLE_BANK_SPECIFIC_KBS = os.getenv("ENABLE_BANK_SPECIFIC_KBS", "true").lower() == "true"

# Initialize bank KB resolver
try:
    BANK_KB_RESOLVER = BankKBResolver()
    BANK_KB_ENABLED = BANK_KB_RESOLVER.is_enabled() and ENABLE_BANK_SPECIFIC_KBS
except Exception as e:
    print(f"[WARNING] Bank KB resolver disabled: {e}")
    BANK_KB_RESOLVER = None
    BANK_KB_ENABLED = False

DEFAULT_KB_NAME = "Meetings"

# Chunking configuration
TRANSCRIPT_SIZE_THRESHOLD_KB = 50  # Chunk if file larger than this
SEGMENTS_PER_CHUNK = 100  # Number of transcript segments per chunk
LINES_PER_CHUNK = 150  # Number of lines per chunk for text files


def chunk_text_file(text_file: Path, output_dir: Path, meeting_id: str = None) -> list:
    """
    Split large text file into smaller chunks for efficient embedding.

    Args:
        text_file: Path to text file (e.g., transcript_enriched.txt)
        output_dir: Directory to save chunk files
        meeting_id: Unique identifier for the meeting (to avoid duplicate content)

    Returns:
        List of paths to chunk files
    """
    # Check file size
    file_size_kb = text_file.stat().st_size / 1024

    if file_size_kb < TRANSCRIPT_SIZE_THRESHOLD_KB:
        # File is small enough, no chunking needed
        return [text_file]

    # Read text file
    with open(text_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    if len(lines) <= LINES_PER_CHUNK:
        return [text_file]

    # Extract header (everything before first timestamp line)
    header_lines = []
    content_start = 0
    for i, line in enumerate(lines):
        if line.strip().startswith('[') and ':' in line[:10]:
            content_start = i
            break
        header_lines.append(line)

    header = ''.join(header_lines)
    content_lines = lines[content_start:]

    # Create chunks directory with unique name using timestamp
    import time
    chunk_timestamp = int(time.time())
    chunks_dir = output_dir / f"transcript_chunks_{chunk_timestamp}"
    chunks_dir.mkdir(exist_ok=True)

    # Use meeting ID or folder name for unique identification
    if not meeting_id:
        meeting_id = output_dir.name

    chunk_files = []
    total_chunks = (len(content_lines) + LINES_PER_CHUNK - 1) // LINES_PER_CHUNK

    for i in range(0, len(content_lines), LINES_PER_CHUNK):
        chunk_num = i // LINES_PER_CHUNK + 1
        chunk_lines = content_lines[i:i + LINES_PER_CHUNK]

        # Build chunk with header and unique identifier
        chunk_text = f"<!-- Meeting ID: {meeting_id} | Chunk: {chunk_num}/{total_chunks} | TS: {chunk_timestamp} -->\n\n"
        chunk_text += header
        if "Part " not in header:
            chunk_text += f"\nTranscript Part {chunk_num}/{total_chunks}\n\n"
        chunk_text += ''.join(chunk_lines)

        # Save chunk with unique filename
        chunk_file = chunks_dir / f"{meeting_id[:50]}_part_{chunk_num:02d}.txt"
        with open(chunk_file, 'w', encoding='utf-8') as f:
            f.write(chunk_text)

        chunk_files.append(chunk_file)

    return chunk_files


def chunk_transcript(transcript_file: Path, output_dir: Path, meeting_id: str = None) -> list:
    """
    Split large transcript into smaller chunks for efficient embedding.
    Handles both JSON (transcript_full.json) and text (transcript_enriched.txt) files.

    Args:
        transcript_file: Path to transcript file
        output_dir: Directory to save chunk files
        meeting_id: Unique identifier for the meeting (to avoid duplicate content)

    Returns:
        List of paths to chunk files
    """
    # Check file size
    file_size_kb = transcript_file.stat().st_size / 1024

    if file_size_kb < TRANSCRIPT_SIZE_THRESHOLD_KB:
        # File is small enough, no chunking needed
        return [transcript_file]

    # Check if it's a text file (enriched) or JSON file (original)
    if transcript_file.suffix.lower() == '.txt':
        return chunk_text_file(transcript_file, output_dir, meeting_id)

    # Handle JSON file
    import time
    chunk_timestamp = int(time.time())

    with open(transcript_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    metadata = data.get('metadata', {})
    segments = data.get('transcript', [])

    if not segments:
        return [transcript_file]

    # Create chunks directory with unique timestamp
    chunks_dir = output_dir / f"transcript_chunks_{chunk_timestamp}"
    chunks_dir.mkdir(exist_ok=True)

    # Use meeting ID or folder name for unique identification
    if not meeting_id:
        meeting_id = output_dir.name

    # Meeting info header
    meeting_name = metadata.get('original_filename', 'Unknown Meeting')
    meeting_date = metadata.get('processed_at', '')[:10] if metadata.get('processed_at') else ''
    num_speakers = metadata.get('num_speakers', 'unknown')
    duration = metadata.get('duration_seconds', 0)
    duration_str = f"{int(duration // 60)}:{int(duration % 60):02d}" if duration else 'unknown'

    header = f"""Meeting: {meeting_name}
Date: {meeting_date}
Duration: {duration_str}
Speakers: {num_speakers}

---

"""

    chunk_files = []
    total_chunks = (len(segments) + SEGMENTS_PER_CHUNK - 1) // SEGMENTS_PER_CHUNK

    for i in range(0, len(segments), SEGMENTS_PER_CHUNK):
        chunk_num = i // SEGMENTS_PER_CHUNK + 1
        chunk_segments = segments[i:i + SEGMENTS_PER_CHUNK]

        # Format segments as readable text with unique identifier
        chunk_text = f"<!-- Meeting ID: {meeting_id} | Chunk: {chunk_num}/{total_chunks} | TS: {chunk_timestamp} -->\n\n"
        chunk_text += header
        chunk_text += f"Transcript Part {chunk_num}/{total_chunks}\n\n"

        for seg in chunk_segments:
            speaker = seg.get('speaker', 'UNKNOWN')
            start = seg.get('start', 0)
            text = seg.get('text', '')

            # Format timestamp
            minutes = int(start // 60)
            seconds = int(start % 60)
            timestamp = f"[{minutes:02d}:{seconds:02d}]"

            chunk_text += f"{timestamp} {speaker}: {text}\n"

        # Save chunk with unique filename
        chunk_file = chunks_dir / f"{meeting_id[:50]}_part_{chunk_num:02d}.txt"
        with open(chunk_file, 'w', encoding='utf-8') as f:
            f.write(chunk_text)

        chunk_files.append(chunk_file)

    return chunk_files


def resolve_knowledge_base(result_folder: Path) -> tuple:
    """
    Resolve Knowledge Base name from result folder.

    Args:
        result_folder: Path to meeting result folder

    Returns:
        Tuple of (kb_name, bank_info_dict)
        - kb_name: Knowledge Base name (e.g., "GPB", "Meetings")
        - bank_info: Bank information dict (or empty dict if no bank detected)
    """

    if not BANK_KB_ENABLED or not BANK_KB_RESOLVER:
        return DEFAULT_KB_NAME, {}

    # Extract KB name from folder name
    folder_name = result_folder.name
    kb_name, bank_info = BANK_KB_RESOLVER.resolve_kb_name(folder_name)

    if bank_info:
        print(f"[INFO] Bank detected: {bank_info.get('full_name')} → KB: '{kb_name}'")
    else:
        print(f"[INFO] No bank prefix detected → Using default KB: '{kb_name}'")

    return kb_name, bank_info


def upload_meeting_to_openwebui(result_folder: Path) -> bool:
    """
    Upload meeting files to OpenWebUI Knowledge Base

    Args:
        result_folder: Path to meeting result folder (e.g., data/results/meeting_20250115_143022)

    Returns:
        bool: True if upload successful, False otherwise
    """

    print(f"\n{'='*60}")
    print(f"[OpenWebUI] Starting upload: {result_folder.name}")
    print(f"{'='*60}\n")

    # Step 1: Validate result folder
    print("[Step 1/6] Validating result folder...")

    if not result_folder.exists():
        print(f"[ERROR] Result folder not found: {result_folder}")
        return False

    transcript_file = result_folder / "transcript_full.json"
    summary_file = result_folder / "summary.md"
    protocol_file = result_folder / "protocol.md"

    if not all([transcript_file.exists(), summary_file.exists(), protocol_file.exists()]):
        print("[ERROR] Missing required files (transcript_full.json, summary.md, or protocol.md)")
        return False

    print(f"[✓] Result folder validated")
    print(f"    - Transcript: {transcript_file.name}")
    print(f"    - Summary: {summary_file.name}")
    print(f"    - Protocol: {protocol_file.name}")

    # Step 2: Resolve Knowledge Base from folder name
    print("\n[Step 2/7] Resolving Knowledge Base...")

    kb_name, bank_info = resolve_knowledge_base(result_folder)
    print(f"[✓] Knowledge Base resolved: '{kb_name}'")

    if bank_info:
        print(f"    - Bank: {bank_info.get('full_name')}")
        print(f"    - Description: {bank_info.get('description')}")

    # Step 3: Check OpenWebUI availability
    print("\n[Step 3/7] Checking OpenWebUI API...")

    if not OPENWEBUI_API_KEY:
        print("[ERROR] OPENWEBUI_API_KEY environment variable not set")
        print("[INFO] Generate API key in OpenWebUI UI: Settings > Account > API Keys")
        return False

    client = OpenWebUIClient(OPENWEBUI_URL, OPENWEBUI_API_KEY)

    if not client.health_check():
        print(f"[ERROR] OpenWebUI API not accessible at {OPENWEBUI_URL}")
        print("[INFO] Make sure OpenWebUI is running:")
        print("       cd services/OpenWebUi && docker-compose up -d")
        return False

    print(f"[✓] OpenWebUI API accessible at {OPENWEBUI_URL}")

    # Step 4: Apply contextual enrichment (if enabled)
    enriched_folder = None

    if ENABLE_CONTEXTUAL_RETRIEVAL:
        print("\n[Step 4/7] Applying Contextual Retrieval enrichment...")

        # Check if enriched files already exist
        enriched_folder = result_folder / "enriched"
        enriched_transcript = enriched_folder / "transcript_enriched.txt"
        enriched_summary = enriched_folder / "summary_enriched.md"
        enriched_protocol = enriched_folder / "protocol_enriched.md"

        if all([enriched_transcript.exists(), enriched_summary.exists(), enriched_protocol.exists()]):
            print("[INFO] Found existing enriched files, skipping enrichment")
            transcript_file = enriched_transcript
            summary_file = enriched_summary
            protocol_file = enriched_protocol
            print(f"[✓] Using existing enriched files from: {enriched_folder.name}/")
        else:
            print("[INFO] This may take 2-5 minutes (calling Claude API for each chunk)")

            try:
                enricher = ContextualEnricher()
                enriched_folder = enricher.enrich_meeting_folder(result_folder)
                print(f"[✓] Contextual enrichment completed")
                print(f"    Enriched files saved to: {enriched_folder.name}/")

                # Use enriched files (with _enriched suffix)
                transcript_file = enriched_folder / "transcript_enriched.txt"
                summary_file = enriched_folder / "summary_enriched.md"
                protocol_file = enriched_folder / "protocol_enriched.md"

            except Exception as e:
                print(f"[WARNING] Contextual enrichment failed: {e}")
                print("[INFO] Falling back to original files (without context)")
                # Continue with original files
    else:
        print("\n[Step 4/7] Contextual enrichment disabled (using original files)")

    # Step 5: Get or create Knowledge Base
    print(f"\n[Step 5/7] Setting up Knowledge Base...")
    print(f"[INFO] Looking for Knowledge Base: '{kb_name}'")

    kb = client.get_knowledge_base_by_name(kb_name)

    if kb and kb.get('write_access', False):
        kb_id = kb['id']
        print(f"[✓] Found existing Knowledge Base: '{kb_name}'")
        print(f"    ID: {kb_id}")
    elif kb and not kb.get('write_access', False):
        print(f"[INFO] Found KB '{kb_name}' but no write access, creating new one...")
        try:
            # Use bank-specific description if available
            description = bank_info.get('description',
                "Semantic search across all meeting transcriptions with contextual enrichment")

            kb_id = client.create_knowledge_base(
                name=kb_name,
                description=description
            )
            print(f"[✓] Created new Knowledge Base: '{kb_name}'")
            print(f"    ID: {kb_id}")
        except Exception as e:
            print(f"[ERROR] Failed to create Knowledge Base: {e}")
            return False
    else:
        print(f"[INFO] Creating new Knowledge Base: '{kb_name}'")
        try:
            # Use bank-specific description if available
            description = bank_info.get('description',
                "Semantic search across all meeting transcriptions with contextual enrichment")

            kb_id = client.create_knowledge_base(
                name=kb_name,
                description=description
            )
            print(f"[✓] Created Knowledge Base: '{kb_name}'")
            print(f"    ID: {kb_id}")
        except Exception as e:
            print(f"[ERROR] Failed to create Knowledge Base: {e}")
            return False

    # Step 6: Upload files
    print(f"\n[Step 6/7] Uploading files to OpenWebUI...")

    uploaded_files = []

    # Helper function to upload a single file
    def upload_single_file(file_path: Path, doc_type: str, timeout: int = 180) -> bool:
        try:
            print(f"    - Uploading {file_path.name}...")
            file_id = client.upload_file(file_path)
            print(f"      ✓ Uploaded (ID: {file_id})")

            print(f"    - Waiting for embedding generation...")
            client.wait_for_processing(file_id, timeout=timeout)
            print(f"      ✓ Processing completed")

            print(f"    - Adding to Knowledge Base...")
            client.add_file_to_knowledge_base(kb_id, file_id)
            print(f"      ✓ Added to Knowledge Base")

            uploaded_files.append({
                "type": doc_type,
                "file_id": file_id,
                "filename": file_path.name
            })
            return True
        except Exception as e:
            print(f"      ✗ Failed: {e}")
            return False

    # Upload transcript (with chunking for large files)
    print(f"\n  [TRANSCRIPT] Processing: {transcript_file.name}")
    transcript_size_kb = transcript_file.stat().st_size / 1024
    print(f"    File size: {transcript_size_kb:.1f} KB")

    if transcript_size_kb > TRANSCRIPT_SIZE_THRESHOLD_KB:
        print(f"    Large file detected, splitting into chunks...")
        meeting_id = result_folder.name
        chunk_files = chunk_transcript(transcript_file, result_folder, meeting_id)
        print(f"    Created {len(chunk_files)} chunk(s)")

        chunk_success = 0
        for i, chunk_file in enumerate(chunk_files, 1):
            print(f"\n    [Chunk {i}/{len(chunk_files)}]")
            if upload_single_file(chunk_file, f"transcript_part_{i}", timeout=120):
                chunk_success += 1

        print(f"\n    Transcript chunks uploaded: {chunk_success}/{len(chunk_files)}")
    else:
        upload_single_file(transcript_file, "transcript")

    # Upload summary
    print(f"\n  [SUMMARY] Processing: {summary_file.name}")
    upload_single_file(summary_file, "summary")

    # Upload protocol
    print(f"\n  [PROTOCOL] Processing: {protocol_file.name}")
    upload_single_file(protocol_file, "protocol")

    if not uploaded_files:
        print("\n[ERROR] No files uploaded successfully")
        return False

    # Step 6: Update metadata.json
    print(f"\n[Step 7/7] Updating metadata...")

    metadata_file = result_folder / "metadata.json"

    if metadata_file.exists():
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            # Add OpenWebUI RAG status
            metadata['openwebui_rag_indexed'] = True
            metadata['openwebui_indexed_at'] = datetime.utcnow().isoformat()
            metadata['openwebui_knowledge_base_id'] = kb_id
            metadata['openwebui_knowledge_base_name'] = kb_name
            metadata['openwebui_files'] = uploaded_files
            metadata['contextual_enrichment_applied'] = ENABLE_CONTEXTUAL_RETRIEVAL

            # Add bank information if detected
            if bank_info:
                metadata['bank_name'] = bank_info.get('kb_name')
                metadata['bank_full_name'] = bank_info.get('full_name')
                metadata['bank_detected_from'] = 'folder_name'

            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            print(f"[✓] Updated {metadata_file.name}")

        except Exception as e:
            print(f"[WARNING] Failed to update metadata.json: {e}")
            # Not critical, continue
    else:
        print(f"[INFO] metadata.json not found, skipping update")

    # Success summary
    print(f"\n{'='*60}")
    print(f"[✓] Upload completed successfully!")
    print(f"{'='*60}")
    print(f"\nSummary:")
    print(f"  Knowledge Base: {kb_name}")
    if bank_info:
        print(f"  Bank: {bank_info.get('full_name')}")
    print(f"  Files uploaded: {len(uploaded_files)}")
    for file_info in uploaded_files:
        print(f"    - {file_info['type']}: {file_info['filename']}")
    print(f"  Contextual enrichment: {'Enabled' if ENABLE_CONTEXTUAL_RETRIEVAL else 'Disabled'}")
    print(f"\nQuery this meeting in OpenWebUI UI:")
    print(f"  1. Open: {OPENWEBUI_URL}")
    print(f"  2. In chat, type: #{kb_name}")
    print(f"  3. Ask questions about: {result_folder.name}")
    print()

    return True


def main():
    """Main entry point"""
    # Fix Windows console encoding for Unicode characters
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    if len(sys.argv) < 2:
        print("Usage: python openwebui_uploader.py <result_folder>")
        print()
        print("Example:")
        print("  python openwebui_uploader.py data/results/meeting_20250115_143022")
        sys.exit(1)

    result_folder = Path(sys.argv[1])

    if not result_folder.is_absolute():
        result_folder = result_folder.absolute()

    success = upload_meeting_to_openwebui(result_folder)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
