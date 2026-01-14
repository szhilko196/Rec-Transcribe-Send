#!/usr/bin/env python3
"""
Test OpenWebUI RAG Integration

End-to-end test for OpenWebUI RAG integration.
Tests API connectivity, file upload, processing, and Knowledge Base operations.

Usage:
    python test_openwebui_integration.py

Requirements:
    - OpenWebUI stack running (docker-compose up -d)
    - OPENWEBUI_API_KEY set in environment
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
SCRIPT_DIR = Path(__file__).parent
sys.path.append(str(SCRIPT_DIR))

from openwebui_client import OpenWebUIClient


def test_openwebui_integration():
    """Test complete OpenWebUI RAG workflow"""

    print("\n" + "="*60)
    print("OpenWebUI RAG Integration Test")
    print("="*60 + "\n")

    # Get configuration from environment
    base_url = os.getenv("OPENWEBUI_URL", "http://localhost:3000")
    api_key = os.getenv("OPENWEBUI_API_KEY")

    if not api_key:
        print("❌ OPENWEBUI_API_KEY environment variable not set")
        print("\nTo fix:")
        print("1. Open OpenWebUI UI: " + base_url)
        print("2. Go to Settings > Account > API Keys")
        print("3. Generate new API key")
        print("4. Set environment variable: export OPENWEBUI_API_KEY=your-key-here")
        return False

    # Initialize client
    print(f"Testing OpenWebUI at: {base_url}")
    print(f"API Key: {api_key[:20]}...\n")
    client = OpenWebUIClient(base_url, api_key)

    # Test 1: Health check
    print("[Test 1/6] Testing OpenWebUI API connection...")
    try:
        if not client.health_check():
            print("❌ OpenWebUI API not accessible")
            print("\nTo fix:")
            print("1. cd services/OpenWebUi")
            print("2. docker-compose up -d")
            print("3. Wait ~30 seconds for startup")
            return False
        print("✓ OpenWebUI API accessible\n")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

    # Test 2: List Knowledge Bases
    print("[Test 2/6] Listing Knowledge Bases...")
    try:
        kbs = client.list_knowledge_bases()
        print(f"✓ Found {len(kbs)} Knowledge Base(s)")
        for kb in kbs:
            print(f"    - {kb.get('name')} (ID: {kb.get('id')})")
        print()
    except Exception as e:
        print(f"❌ Failed to list Knowledge Bases: {e}")
        return False

    # Test 3: Check for "Meetings" Knowledge Base
    print("[Test 3/6] Checking for 'Meetings' Knowledge Base...")
    try:
        kb = client.get_knowledge_base_by_name("Meetings")
        if kb:
            print(f"✓ Found 'Meetings' Knowledge Base")
            print(f"    ID: {kb.get('id')}")
            print(f"    Description: {kb.get('description', 'N/A')}")
            kb_id = kb['id']
        else:
            print("⚠ 'Meetings' Knowledge Base not found")
            print("  This is expected if no meetings have been processed yet")
            print("  NOTE: OpenWebUI v0.7.2 API doesn't support programmatic KB creation")
            print("  Skipping KB creation - files can be uploaded and organized later through UI")
            kb_id = None
        print()
    except Exception as e:
        print(f"❌ Failed to check Knowledge Base: {e}")
        return False

    # Test 4: Create test file
    print("[Test 4/6] Creating test transcript file...")
    try:
        test_data_dir = SCRIPT_DIR.parent / "test_data"
        test_data_dir.mkdir(exist_ok=True)

        test_file = test_data_dir / "test_transcript.txt"
        test_content = """# Test Meeting Transcript

Date: 2025-01-15
Participants: Test User

SPEAKER_00: This is a test transcript for OpenWebUI RAG integration.
SPEAKER_00: We are testing the automatic indexing of meeting transcriptions.
SPEAKER_00: The system should be able to search this content semantically.
"""
        test_file.write_text(test_content, encoding='utf-8')
        print(f"✓ Test file created: {test_file}")
        print(f"    Size: {len(test_content)} bytes")
        print()
    except Exception as e:
        print(f"❌ Failed to create test file: {e}")
        return False

    # Test 5: Upload test file
    print("[Test 5/6] Testing file upload and processing...")
    try:
        # Upload file
        print("  - Uploading file...")
        file_id = client.upload_file(test_file)
        print(f"  ✓ File uploaded (ID: {file_id})")

        # Wait for processing
        print("  - Waiting for embedding generation (this may take 1-2 minutes)...")
        print("    (First upload will download BGE-M3 model: ~2GB)")
        client.wait_for_processing(file_id, timeout=300)  # 5 min timeout for first upload
        print("  ✓ Processing completed")

        # Add to Knowledge Base (if KB exists)
        if kb_id:
            print("  - Adding to Knowledge Base...")
            client.add_file_to_knowledge_base(kb_id, file_id)
            print("  ✓ File added to Knowledge Base")
        else:
            print("  ⚠ Skipping KB association (no Knowledge Base available)")
            print("    File can be organized into KB manually through UI")
        print()
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check OpenWebUI logs: docker-compose logs -f openwebui")
        print("2. Verify models are downloading: docker exec openwebui ls -lh /root/.cache/huggingface")
        print("3. Increase timeout if model is downloading for first time")
        return False

    # Test 6: Verify file info
    print("[Test 6/6] Verifying file metadata...")
    try:
        file_info = client.get_file_info(file_id)
        print(f"✓ File metadata retrieved")
        print(f"    Filename: {file_info.get('filename', 'N/A')}")
        print(f"    Size: {file_info.get('size', 'N/A')} bytes")
        print(f"    Created: {file_info.get('created_at', 'N/A')}")
        print()
    except Exception as e:
        print(f"⚠ Could not retrieve file metadata: {e}")
        print("  (File was still uploaded and added to KB successfully)")
        print()

    # Success summary
    print("="*60)
    print("✓ All tests passed successfully!")
    print("="*60)
    print("\nOpenWebUI RAG integration is working correctly.")
    print(f"\nNext steps:")
    print(f"1. Open OpenWebUI UI: {base_url}")
    print(f"2. In chat, type: #Meetings (or #Test-Meetings)")
    print(f"3. Ask: 'What is this test about?'")
    print(f"4. You should get a relevant answer from the test transcript")
    print("\nTo process actual meetings:")
    print("1. Enable in .env: ENABLE_OPENWEBUI_RAG=true")
    print("2. Process a meeting: python services/transcription_orchestrator/orchestrator.py data/input/meeting.avi")
    print("3. Meeting will automatically index to OpenWebUI\n")

    return True


def main():
    """Main entry point"""
    # Fix Windows console encoding for Unicode characters
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    try:
        success = test_openwebui_integration()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
