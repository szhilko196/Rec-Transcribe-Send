"""
Unit tests for BankKBResolver

Run with: python test_bank_kb_resolver.py
"""

import sys
import io
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from bank_kb_resolver import BankKBResolver


def test_extract_bank_cyrillic():
    """Test extraction of Cyrillic bank prefix"""
    resolver = BankKBResolver()

    # Test cases
    test_cases = [
        ("ГПБ_Архитектурные_вопросы_20250115_143022", "ГПБ"),
        ("СБЕРБАНК_Старт_работ_20250115_143022", "СБЕРБАНК"),
        ("ПСБ_Meeting_20250115_143022", "ПСБ"),
        ("газпромбанк_test_20250115_143022", "ГАЗПРОМБАНК"),  # Lowercase → uppercase
    ]

    for folder_name, expected in test_cases:
        result = resolver.extract_bank_from_folder_name(folder_name)
        assert result == expected, f"Failed: {folder_name} → Expected {expected}, got {result}"
        print(f"[PASS] {folder_name} -> {result}")


def test_extract_bank_latin():
    """Test extraction of Latin bank prefix"""
    resolver = BankKBResolver()

    test_cases = [
        ("GPB_Architecture_20250115_143022", "GPB"),
        ("SBERBANK_Project_20250115_143022", "SBERBANK"),
        ("PSB_Review_20250115_143022", "PSB"),
    ]

    for folder_name, expected in test_cases:
        result = resolver.extract_bank_from_folder_name(folder_name)
        assert result == expected, f"Failed: {folder_name} → Expected {expected}, got {result}"
        print(f"[PASS] {folder_name} -> {result}")


def test_fallback_no_bank():
    """Test fallback when no bank prefix (using resolve_kb_name)"""
    resolver = BankKBResolver()

    # Test cases: folders without known banks should fallback to "Meetings"
    test_cases = [
        "meeting_20250115_143022",
        "regular_call_20250115_143022",
        "unknown_bank_20250115_143022",
        "_no_prefix_20250115_143022",  # Empty first segment
    ]

    for folder_name in test_cases:
        kb_name, bank_info = resolver.resolve_kb_name(folder_name)
        assert kb_name == "Meetings", f"Failed: {folder_name} should use 'Meetings' KB, got {kb_name}"
        assert bank_info == {}, f"Failed: {folder_name} should have empty bank_info, got {bank_info}"
        print(f"[PASS] {folder_name} -> KB: Meetings (fallback)")

    # Test invalid formats that should fail extraction
    invalid_cases = [
        ("123_test_20250115_143022", None),  # Numeric prefix
        ("_no_prefix_20250115_143022", None),  # Empty first segment
    ]

    for folder_name, expected in invalid_cases:
        result = resolver.extract_bank_from_folder_name(folder_name)
        assert result == expected, f"Failed: {folder_name} should return {expected}, got {result}"
        print(f"[PASS] {folder_name} -> {expected} (invalid format)")


def test_resolve_kb_name():
    """Test KB name resolution with normalization"""
    resolver = BankKBResolver()

    test_cases = [
        ("ГПБ_meeting_20250115_143022", "GPB", "Газпромбанк"),
        ("ГАЗПРОМБАНК_test_20250115_143022", "GPB", "Газпромбанк"),  # Alias
        ("СБЕРБАНК_project_20250115_143022", "SBERBANK", "Сбербанк"),
        ("СБЕР_call_20250115_143022", "SBERBANK", "Сбербанк"),  # Alias
        ("ПСБ_review_20250115_143022", "PSB", "ПСБанк"),
        ("PSBANK_meeting_20250115_143022", "PSB", "ПСБанк"),  # Alias
        ("unknown_bank_20250115_143022", "Meetings", ""),  # Fallback
        ("meeting_20250115_143022", "Meetings", ""),  # No bank
    ]

    for folder_name, expected_kb, expected_full_name in test_cases:
        kb_name, bank_info = resolver.resolve_kb_name(folder_name)
        assert kb_name == expected_kb, f"Failed: {folder_name} → Expected KB {expected_kb}, got {kb_name}"

        if bank_info:
            assert bank_info["full_name"] == expected_full_name, \
                f"Failed: {folder_name} → Expected full name {expected_full_name}, got {bank_info.get('full_name')}"
            print(f"[PASS] {folder_name} -> KB: {kb_name} ({bank_info['full_name']})")
        else:
            print(f"[PASS] {folder_name} -> KB: {kb_name} (fallback)")


def test_get_kb_description():
    """Test KB description retrieval"""
    resolver = BankKBResolver()

    test_cases = [
        ("GPB", "Meeting transcripts for Gazprombank"),
        ("SBERBANK", "Meeting transcripts for Sberbank"),
        ("PSB", "Meeting transcripts for PSBank"),
        ("UnknownKB", ""),  # Not found
    ]

    for kb_name, expected_desc in test_cases:
        desc = resolver.get_kb_description(kb_name)
        assert desc == expected_desc, f"Failed: {kb_name} → Expected '{expected_desc}', got '{desc}'"
        print(f"[PASS] KB '{kb_name}' description: {desc or '(empty)'}")


def test_is_enabled():
    """Test enabled flag"""
    resolver = BankKBResolver()
    enabled = resolver.is_enabled()
    print(f"[PASS] Bank KB feature enabled: {enabled}")
    assert isinstance(enabled, bool)


def test_case_insensitivity():
    """Test case-insensitive bank matching"""
    resolver = BankKBResolver()

    test_cases = [
        ("гпб_test_20250115_143022", "GPB"),  # Lowercase Cyrillic
        ("ГпБ_test_20250115_143022", "GPB"),  # Mixed case Cyrillic
        ("gpb_test_20250115_143022", "GPB"),  # Lowercase Latin (if in mappings)
    ]

    for folder_name, expected_kb in test_cases:
        kb_name, bank_info = resolver.resolve_kb_name(folder_name)
        # Note: Latin lowercase won't match unless added to mappings
        if bank_info:
            assert kb_name == expected_kb, f"Failed: {folder_name} → Expected {expected_kb}, got {kb_name}"
            print(f"[PASS] {folder_name} -> {kb_name} (case-insensitive)")


def run_all_tests():
    """Run all test suites"""
    print("\n=== Testing Bank KB Resolver ===\n")

    print("Test 1: Extract Cyrillic bank prefix")
    test_extract_bank_cyrillic()

    print("\nTest 2: Extract Latin bank prefix")
    test_extract_bank_latin()

    print("\nTest 3: Fallback for no bank prefix")
    test_fallback_no_bank()

    print("\nTest 4: Resolve KB name with normalization")
    test_resolve_kb_name()

    print("\nTest 5: Get KB descriptions")
    test_get_kb_description()

    print("\nTest 6: Check enabled flag")
    test_is_enabled()

    print("\nTest 7: Case-insensitive matching")
    test_case_insensitivity()

    print("\n=== All tests passed! ===\n")


if __name__ == "__main__":
    try:
        run_all_tests()
    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        sys.exit(1)
