"""
Dry-run test for openwebui_uploader.py bank KB integration

Simulates the bank resolution step without actually uploading to OpenWebUI
"""

import sys
import io
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add parent directory to path
SCRIPT_DIR = Path(__file__).parent
sys.path.append(str(SCRIPT_DIR))

# Import the resolver (simulate uploader import)
from bank_kb_resolver import BankKBResolver
import os

# Simulate environment variable check
ENABLE_BANK_SPECIFIC_KBS = os.getenv("ENABLE_BANK_SPECIFIC_KBS", "true").lower() == "true"

# Initialize resolver (same as uploader)
try:
    BANK_KB_RESOLVER = BankKBResolver()
    BANK_KB_ENABLED = BANK_KB_RESOLVER.is_enabled() and ENABLE_BANK_SPECIFIC_KBS
except Exception as e:
    print(f"[WARNING] Bank KB resolver disabled: {e}")
    BANK_KB_RESOLVER = None
    BANK_KB_ENABLED = False

DEFAULT_KB_NAME = "Meetings"


def resolve_knowledge_base(result_folder: Path) -> tuple:
    """Same function as in openwebui_uploader.py"""

    if not BANK_KB_ENABLED or not BANK_KB_RESOLVER:
        return DEFAULT_KB_NAME, {}

    folder_name = result_folder.name
    kb_name, bank_info = BANK_KB_RESOLVER.resolve_kb_name(folder_name)

    if bank_info:
        print(f"[INFO] Bank detected: {bank_info.get('full_name')} → KB: '{kb_name}'")
    else:
        print(f"[INFO] No bank prefix detected → Using default KB: '{kb_name}'")

    return kb_name, bank_info


def test_uploader_integration():
    """Test the uploader's bank resolution logic"""

    print("="*70)
    print("OpenWebUI Uploader - Bank KB Resolution Test (Dry Run)")
    print("="*70)

    print(f"\nEnvironment:")
    print(f"  ENABLE_BANK_SPECIFIC_KBS: {ENABLE_BANK_SPECIFIC_KBS}")
    print(f"  BANK_KB_ENABLED: {BANK_KB_ENABLED}")
    print(f"  DEFAULT_KB_NAME: {DEFAULT_KB_NAME}")

    # Simulate result folders
    test_folders = [
        Path("data/results/ГПБ_Архитектурные_вопросы_20250115_143022"),
        Path("data/results/СБЕРБАНК_Старт_работ_по_Сберу_20250116_101530"),
        Path("data/results/ПСБ_Встреча_команды_20250117_153000"),
        Path("data/results/meeting_20250118_120000"),
        Path("data/results/weekly_sync_20250119_140000"),
    ]

    print("\n" + "="*70)
    print("Testing folder → KB resolution (uploader simulation):")
    print("="*70 + "\n")

    for folder in test_folders:
        print(f"\n[Step 2/7] Resolving Knowledge Base...")
        print(f"Result folder: {folder.name}")

        kb_name, bank_info = resolve_knowledge_base(folder)

        print(f"[✓] Knowledge Base resolved: '{kb_name}'")

        if bank_info:
            print(f"    - Bank: {bank_info.get('full_name')}")
            print(f"    - Description: {bank_info.get('description')}")

        # Simulate metadata update
        print("\n[Metadata that would be saved]:")
        print(f"  openwebui_knowledge_base_name: '{kb_name}'")

        if bank_info:
            print(f"  bank_name: '{bank_info.get('kb_name')}'")
            print(f"  bank_full_name: '{bank_info.get('full_name')}'")
            print(f"  bank_detected_from: 'folder_name'")

        # Simulate success message
        print("\n[Success message that would be shown]:")
        print(f"  Knowledge Base: {kb_name}")
        if bank_info:
            print(f"  Bank: {bank_info.get('full_name')}")
        print(f"  Query command: #{kb_name}")

        print("\n" + "-"*70)

    print("\n" + "="*70)
    print("✓ Dry-run completed successfully!")
    print("="*70)
    print("\nNext steps:")
    print("  1. Ensure ENABLE_BANK_SPECIFIC_KBS=true in .env")
    print("  2. Process a test video with bank prefix (e.g., ГПБ_test.avi)")
    print("  3. Check OpenWebUI for separate Knowledge Bases")
    print("  4. Test Telegram bot: /kb GPB")
    print()


if __name__ == "__main__":
    try:
        test_uploader_integration()
    except Exception as e:
        print(f"\n✗ Test failed: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
