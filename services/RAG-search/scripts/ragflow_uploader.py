"""
RAGFlow Uploader
Main script for uploading meetings to RAGFlow with contextual enrichment

Called by orchestrator.py after meeting processing completes.

Usage:
    python ragflow_uploader.py <result_folder>

Output:
    Prints dataset_id to stdout for orchestrator to capture
"""

import sys
import os
from pathlib import Path
import json

# Add scripts directory to path
sys.path.append(str(Path(__file__).parent))

from contextual_enrichment import ContextualEnricher
from ragflow_client import RAGFlowClient


def upload_meeting_to_ragflow(result_folder: Path) -> str:
    """
    Upload a meeting to RAGFlow with contextual enrichment

    Steps:
    1. Apply contextual enrichment (Anthropic technique)
    2. Create dataset in RAGFlow
    3. Upload enriched files
    4. Trigger parsing
    5. Wait for completion
    6. Update metadata.json

    Args:
        result_folder: Path to meeting result folder

    Returns:
        dataset_id: RAGFlow dataset ID

    Raises:
        Exception: If upload fails
    """
    result_folder = Path(result_folder)

    if not result_folder.exists():
        raise FileNotFoundError(f"Result folder not found: {result_folder}")

    print(f"\n[RAGFlow Upload] Starting upload for: {result_folder.name}")

    # Check if contextual retrieval is enabled
    enable_contextual = os.getenv("ENABLE_CONTEXTUAL_RETRIEVAL", "true").lower() == "true"

    # Step 1: Apply contextual enrichment (if enabled)
    if enable_contextual:
        print("[Step 1/5] Applying contextual enrichment...")
        try:
            enricher = ContextualEnricher()
            enriched_folder = enricher.enrich_meeting_folder(result_folder)
        except Exception as e:
            print(f"[WARNING] Contextual enrichment failed: {e}")
            print("[INFO] Falling back to original files without enrichment")
            enriched_folder = result_folder
            enable_contextual = False
    else:
        print("[Step 1/5] Contextual enrichment disabled (using original files)")
        enriched_folder = result_folder

    # Step 2: Create dataset in RAGFlow
    print("[Step 2/5] Creating dataset in RAGFlow...")
    client = RAGFlowClient()

    # Check RAGFlow health
    if not client.health_check():
        raise ConnectionError(
            "RAGFlow API is not accessible. "
            "Make sure RAGFlow is running: "
            "docker-compose -f services/RAG-search/docker-compose.ragflow.yml up -d"
        )

    # Load metadata for description
    metadata_path = result_folder / "metadata.json"
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    dataset_name = result_folder.name
    dataset_description = (
        f"Meeting: {dataset_name}\n"
        f"Duration: {metadata.get('duration', 0) / 60:.1f} minutes\n"
        f"Speakers: {metadata.get('num_speakers', 'unknown')}\n"
        f"Contextual Enrichment: {enable_contextual}"
    )

    dataset_id = client.create_dataset(
        name=dataset_name,
        description=dataset_description,
        embedding_model="BAAI/bge-m3"
    )

    # Step 3: Upload files
    print("[Step 3/5] Uploading documents to RAGFlow...")

    # Determine which files to upload
    if enable_contextual and enriched_folder != result_folder:
        # Upload enriched files
        files_to_upload = [
            (enriched_folder / "transcript_enriched.txt", "transcript.txt"),
            (enriched_folder / "summary_enriched.md", "summary.md"),
            (enriched_folder / "protocol_enriched.md", "protocol.md"),
        ]
    else:
        # Upload original files
        files_to_upload = [
            (result_folder / "transcript_readable.txt", "transcript.txt"),
            (result_folder / "summary.md", "summary.md"),
            (result_folder / "protocol.md", "protocol.md"),
        ]

    document_ids = []
    for file_path, display_name in files_to_upload:
        if file_path.exists():
            try:
                doc_id = client.upload_document(
                    dataset_id=dataset_id,
                    file_path=file_path,
                    filename=display_name
                )
                document_ids.append(doc_id)
            except Exception as e:
                print(f"[WARNING] Failed to upload {file_path.name}: {e}")

    if not document_ids:
        raise Exception("No documents uploaded successfully")

    print(f"[OK] Uploaded {len(document_ids)} documents")

    # Step 4: Trigger parsing
    print("[Step 4/5] Triggering document parsing...")
    client.parse_documents(dataset_id, document_ids)

    # Step 5: Wait for parsing to complete
    print("[Step 5/5] Waiting for parsing to complete...")
    for doc_id in document_ids:
        success = client.wait_for_parsing(
            dataset_id=dataset_id,
            document_id=doc_id,
            timeout=180,  # 3 minutes per document
            check_interval=5
        )
        if not success:
            print(f"[WARNING] Parsing may have failed for document {doc_id}")

    # Update metadata.json with RAGFlow info
    metadata["rag_indexed"] = True
    metadata["rag_indexed_at"] = __import__('datetime').datetime.utcnow().isoformat()
    metadata["ragflow_dataset_id"] = dataset_id
    metadata["ragflow_dataset_name"] = dataset_name
    metadata["ragflow_documents_count"] = len(document_ids)
    metadata["contextual_enrichment_applied"] = enable_contextual

    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"\n[SUCCESS] Meeting uploaded to RAGFlow!")
    print(f"  Dataset ID: {dataset_id}")
    print(f"  Dataset Name: {dataset_name}")
    print(f"  Documents: {len(document_ids)}")
    print(f"  Contextual Enrichment: {enable_contextual}")
    print(f"\n  Access via RAGFlow UI: http://localhost:9380")

    return dataset_id


def main():
    """CLI entry point"""
    if len(sys.argv) < 2:
        print("Usage: python ragflow_uploader.py <result_folder>", file=sys.stderr)
        print("Example: python ragflow_uploader.py C:/path/to/meeting_2025-01-15_143022", file=sys.stderr)
        sys.exit(1)

    result_folder = Path(sys.argv[1])

    try:
        dataset_id = upload_meeting_to_ragflow(result_folder)

        # Print dataset_id to stdout for orchestrator to capture
        print(dataset_id)
        sys.exit(0)

    except Exception as e:
        print(f"\n[ERROR] RAGFlow upload failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
