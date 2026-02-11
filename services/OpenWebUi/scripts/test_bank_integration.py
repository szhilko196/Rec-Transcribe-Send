"""
Integration test for bank KB resolver with uploader

Tests the full flow: folder name → bank resolution → KB assignment
"""

import sys
import io
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from bank_kb_resolver import BankKBResolver


def test_integration():
    """Test integration with real folder name patterns"""

    print("="*60)
    print("Bank KB Integration Test")
    print("="*60)

    resolver = BankKBResolver()

    # Test cases matching real result folder patterns
    test_cases = [
        # Bank-prefixed folders
        ("ГПБ_Архитектурные_вопросы_20250115_143022", "GPB", "Газпромбанк"),
        ("ГАЗПРОМБАНК_Старт_проекта_20250115_143022", "GPB", "Газпромбанк"),
        ("СБЕРБАНК_Технический_обзор_20250115_143022", "SBERBANK", "Сбербанк"),
        ("СБЕР_Еженедельная_встреча_20250115_143022", "SBERBANK", "Сбербанк"),
        ("ПСБ_Планирование_спринта_20250115_143022", "PSB", "ПСБанк"),
        ("PSBANK_Development_sync_20250115_143022", "PSB", "ПСБанк"),

        # Non-bank folders (should fallback to "Meetings")
        ("meeting_20250115_143022", "Meetings", None),
        ("weekly_standup_20250115_143022", "Meetings", None),
        ("tech_review_20250115_143022", "Meetings", None),
        ("UnknownBank_test_20250115_143022", "Meetings", None),
    ]

    print("\nTesting folder name → KB resolution:\n")

    passed = 0
    failed = 0

    for folder_name, expected_kb, expected_bank in test_cases:
        kb_name, bank_info = resolver.resolve_kb_name(folder_name)

        success = kb_name == expected_kb

        if expected_bank:
            success = success and bank_info.get('full_name') == expected_bank

        if success:
            status = "[PASS]"
            passed += 1
            if bank_info:
                print(f"{status} {folder_name}")
                print(f"       → KB: '{kb_name}' (Bank: {bank_info.get('full_name')})")
            else:
                print(f"{status} {folder_name}")
                print(f"       → KB: '{kb_name}' (No bank detected)")
        else:
            status = "[FAIL]"
            failed += 1
            print(f"{status} {folder_name}")
            print(f"       Expected KB: '{expected_kb}', Got: '{kb_name}'")
            if expected_bank:
                print(f"       Expected Bank: '{expected_bank}', Got: '{bank_info.get('full_name', 'None')}'")

    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)

    if failed > 0:
        sys.exit(1)


def test_telegram_bot_compatibility():
    """Test that KB names work with Telegram bot /kb command"""

    print("\n\nTelegram Bot Compatibility Test")
    print("="*60)

    resolver = BankKBResolver()

    # Get all configured banks
    all_banks = resolver.get_all_banks()

    # Get unique KB names
    kb_names = set()
    for bank_info in all_banks.values():
        kb_name = bank_info.get('kb_name')
        if kb_name:
            kb_names.add(kb_name)

    print("\nConfigured Knowledge Bases (for /kb command):")
    print(f"  - Meetings (default)")

    for kb_name in sorted(kb_names):
        description = resolver.get_kb_description(kb_name)
        print(f"  - {kb_name}")
        if description:
            print(f"    Description: {description}")

    print("\nTelegram bot commands:")
    print("  /kb                  # List all available KBs")
    print("  /kb Meetings         # Search default KB")

    for kb_name in sorted(kb_names):
        print(f"  /kb {kb_name:12}  # Search {kb_name} KB")

    print("\n" + "="*60)


if __name__ == "__main__":
    try:
        test_integration()
        test_telegram_bot_compatibility()
        print("\n✓ All integration tests passed!\n")
    except Exception as e:
        print(f"\n✗ Integration test failed: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
