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

# Add parent directory to path for imports
SCRIPT_DIR = Path(__file__).parent
sys.path.append(str(SCRIPT_DIR))

from contextual_enrichment import ContextualEnricher
from openwebui_client import OpenWebUIClient


# Configuration from environment variables
OPENWEBUI_URL = os.getenv("OPENWEBUI_URL", "http://localhost:3000")
OPENWEBUI_API_KEY = os.getenv("OPENWEBUI_API_KEY")
ENABLE_CONTEXTUAL_RETRIEVAL = os.getenv("ENABLE_CONTEXTUAL_RETRIEVAL", "true").lower() == "true"
SHARED_KB_NAME = "Meetings"


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

    # Step 2: Check OpenWebUI availability
    print("\n[Step 2/6] Checking OpenWebUI API...")

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

    # Step 3: Apply contextual enrichment (if enabled)
    enriched_folder = None

    if ENABLE_CONTEXTUAL_RETRIEVAL:
        print("\n[Step 3/6] Applying Contextual Retrieval enrichment...")
        print("[INFO] This may take 2-5 minutes (calling Claude API for each chunk)")

        try:
            enricher = ContextualEnricher()
            enriched_folder = enricher.enrich_meeting_folder(result_folder)
            print(f"[✓] Contextual enrichment completed")
            print(f"    Enriched files saved to: {enriched_folder.name}/")

            # Use enriched files
            transcript_file = enriched_folder / "transcript_full.json"
            summary_file = enriched_folder / "summary.md"
            protocol_file = enriched_folder / "protocol.md"

        except Exception as e:
            print(f"[WARNING] Contextual enrichment failed: {e}")
            print("[INFO] Falling back to original files (without context)")
            # Continue with original files
    else:
        print("\n[Step 3/6] Contextual enrichment disabled (using original files)")

    # Step 4: Get or create shared Knowledge Base
    print(f"\n[Step 4/6] Setting up Knowledge Base...")
    print(f"[INFO] Looking for Knowledge Base: '{SHARED_KB_NAME}'")

    kb = client.get_knowledge_base_by_name(SHARED_KB_NAME)

    if kb:
        kb_id = kb['id']
        print(f"[✓] Found existing Knowledge Base: '{SHARED_KB_NAME}'")
        print(f"    ID: {kb_id}")
    else:
        print(f"[INFO] Creating new Knowledge Base: '{SHARED_KB_NAME}'")
        try:
            kb_id = client.create_knowledge_base(
                name=SHARED_KB_NAME,
                description="Semantic search across all meeting transcriptions with contextual enrichment"
            )
            print(f"[✓] Created Knowledge Base: '{SHARED_KB_NAME}'")
            print(f"    ID: {kb_id}")
        except Exception as e:
            print(f"[ERROR] Failed to create Knowledge Base: {e}")
            return False

    # Step 5: Upload files
    print(f"\n[Step 5/6] Uploading files to OpenWebUI...")

    uploaded_files = []
    files_to_upload = [
        (transcript_file, "transcript"),
        (summary_file, "summary"),
        (protocol_file, "protocol")
    ]

    for file_path, doc_type in files_to_upload:
        print(f"\n  [{doc_type.upper()}] Processing: {file_path.name}")

        try:
            # Upload file
            print(f"    - Uploading...")
            file_id = client.upload_file(file_path)
            print(f"    ✓ Uploaded (ID: {file_id})")

            # Wait for async processing (embedding generation)
            print(f"    - Waiting for embedding generation...")
            client.wait_for_processing(file_id, timeout=180)
            print(f"    ✓ Processing completed")

            # Add to Knowledge Base
            print(f"    - Adding to Knowledge Base...")
            client.add_file_to_knowledge_base(kb_id, file_id)
            print(f"    ✓ Added to Knowledge Base")

            uploaded_files.append({
                "type": doc_type,
                "file_id": file_id,
                "filename": file_path.name
            })

        except Exception as e:
            print(f"    ✗ Failed to upload {doc_type}: {e}")
            # Continue with other files even if one fails

    if not uploaded_files:
        print("\n[ERROR] No files uploaded successfully")
        return False

    # Step 6: Update metadata.json
    print(f"\n[Step 6/6] Updating metadata...")

    metadata_file = result_folder / "metadata.json"

    if metadata_file.exists():
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            # Add OpenWebUI RAG status
            metadata['openwebui_rag_indexed'] = True
            metadata['openwebui_indexed_at'] = datetime.utcnow().isoformat()
            metadata['openwebui_knowledge_base_id'] = kb_id
            metadata['openwebui_knowledge_base_name'] = SHARED_KB_NAME
            metadata['openwebui_files'] = uploaded_files
            metadata['contextual_enrichment_applied'] = ENABLE_CONTEXTUAL_RETRIEVAL

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
    print(f"  Knowledge Base: {SHARED_KB_NAME}")
    print(f"  Files uploaded: {len(uploaded_files)}")
    for file_info in uploaded_files:
        print(f"    - {file_info['type']}: {file_info['filename']}")
    print(f"  Contextual enrichment: {'Enabled' if ENABLE_CONTEXTUAL_RETRIEVAL else 'Disabled'}")
    print(f"\nQuery this meeting in OpenWebUI UI:")
    print(f"  1. Open: {OPENWEBUI_URL}")
    print(f"  2. In chat, type: #Meetings")
    print(f"  3. Ask questions about: {result_folder.name}")
    print()

    return True


def main():
    """Main entry point"""

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
