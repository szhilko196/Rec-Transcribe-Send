"""
Bank Knowledge Base Resolver

Extracts bank names from meeting folder names and resolves them to normalized Knowledge Base names.
Supports Cyrillic-to-Latin normalization and multiple bank name aliases.

Pattern: {video_name}_{YYYYMMDD_HHMMSS} → Extract bank from video_name
Example: "ГПБ_Архитектурные_вопросы_20250115_143022" → KB "GPB"
"""

import json
import re
from pathlib import Path
from typing import Optional, Dict, Tuple


class BankKBResolver:
    """Resolve bank Knowledge Base from result folder name"""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize resolver with bank mapping configuration.

        Args:
            config_path: Path to bank_kb_mapping.json (default: same directory as this script)

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config JSON is invalid
        """
        if config_path is None:
            config_path = Path(__file__).parent / "bank_kb_mapping.json"

        self.config_path = config_path
        self.config = self._load_config()
        self.enabled = self.config.get("enabled", True)
        self.fallback_kb = self.config.get("fallback_kb", "Meetings")
        self.mappings = self._normalize_mappings(self.config.get("mappings", {}))

    def _load_config(self) -> dict:
        """Load and validate configuration file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Bank KB mapping config not found: {self.config_path}")

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in bank KB mapping config: {e}")

    def _normalize_mappings(self, mappings: dict) -> dict:
        """
        Normalize mapping keys to uppercase for case-insensitive lookup.

        Args:
            mappings: Original mappings dict

        Returns:
            Dict with uppercase keys
        """
        normalized = {}
        for bank_name, bank_info in mappings.items():
            # Normalize key to uppercase
            normalized_key = bank_name.upper()
            normalized[normalized_key] = bank_info
        return normalized

    def extract_bank_from_folder_name(self, folder_name: str) -> Optional[str]:
        """
        Extract potential bank prefix from result folder name.

        NOTE: This method extracts the first segment WITHOUT validating if it's a known bank.
        Use resolve_kb_name() for validation and KB name resolution.

        Pattern: {video_name}_{YYYYMMDD_HHMMSS}

        Examples:
        - "ГПБ_Архитектурные_вопросы_20250115_143022" → "ГПБ"
        - "СБЕРБАНК_Старт_работ_20250115_143022" → "СБЕРБАНК"
        - "meeting_20250115_143022" → "MEETING" (extracted but not a known bank)
        - "123_test_20250115_143022" → None (numeric, invalid)
        - "no_timestamp_folder" → "NO" (extracted if valid format)

        Algorithm:
        1. Remove timestamp suffix (regex: _\d{8}_\d{6}$)
        2. Extract first segment before underscore
        3. Validate alphanumeric (Cyrillic or Latin)
        4. Return uppercase prefix or None

        Args:
            folder_name: Result folder name

        Returns:
            Uppercase prefix (not validated as bank) or None if invalid format
        """
        # Remove timestamp suffix (format: _YYYYMMDD_HHMMSS)
        timestamp_pattern = r'_\d{8}_\d{6}$'
        video_name = re.sub(timestamp_pattern, '', folder_name)

        # No timestamp found - check if this is the video name itself
        if video_name == folder_name:
            # Try to extract first segment anyway (might be processing a video filename directly)
            pass

        # Extract first segment before underscore
        parts = video_name.split('_')
        if not parts or not parts[0]:
            return None

        bank_prefix = parts[0].strip().upper()

        # Validate: must be alphanumeric (Cyrillic or Latin) but NOT purely numeric
        # Must contain at least one letter
        if not bank_prefix or not re.match(r'^[A-ZА-ЯЁ0-9]+$', bank_prefix):
            return None

        # Reject purely numeric prefixes (e.g., "123")
        if bank_prefix.isdigit():
            return None

        return bank_prefix

    def resolve_kb_name(self, folder_name: str) -> Tuple[str, dict]:
        """
        Resolve Knowledge Base name from folder name.

        Returns: (kb_name, bank_info_dict)

        Examples:
        - "ГПБ_meeting_20250115_143022" → ("GPB", {"kb_name": "GPB", "full_name": "Газпромбанк", ...})
        - "unknown_bank_20250115_143022" → ("Meetings", {})
        - "meeting_20250115_143022" → ("Meetings", {})

        Args:
            folder_name: Result folder name

        Returns:
            Tuple of (kb_name, bank_info_dict)
            - kb_name: Normalized KB name (e.g., "GPB")
            - bank_info_dict: Full bank info or empty dict if not found
        """
        # Extract bank prefix
        bank_prefix = self.extract_bank_from_folder_name(folder_name)

        if not bank_prefix:
            # No bank prefix found
            return self.fallback_kb, {}

        # Lookup in mappings (already normalized to uppercase)
        bank_info = self.mappings.get(bank_prefix)

        if not bank_info:
            # Unknown bank - use fallback
            return self.fallback_kb, {}

        # Return resolved KB name
        kb_name = bank_info.get("kb_name", self.fallback_kb)
        return kb_name, bank_info

    def get_kb_description(self, kb_name: str) -> str:
        """
        Get description for Knowledge Base.

        Args:
            kb_name: Knowledge Base name (e.g., "GPB")

        Returns:
            Description string or empty string if not found
        """
        # Search mappings for matching kb_name
        for bank_info in self.mappings.values():
            if bank_info.get("kb_name") == kb_name:
                return bank_info.get("description", "")

        return ""

    def is_enabled(self) -> bool:
        """Check if bank KB feature is enabled"""
        return self.enabled

    def get_all_banks(self) -> Dict[str, dict]:
        """
        Get all configured banks.

        Returns:
            Dict mapping bank prefixes to bank info
        """
        return self.mappings.copy()
