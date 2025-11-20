"""
Speaker Profile Validator and Manager

This module provides utilities for validating and managing speaker profiles
used by the speaker recognition system.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class SpeakerProfileValidator:
    """Validator for speaker profile JSON files"""

    REQUIRED_FIELDS = ["version", "speakers"]
    SPEAKER_REQUIRED_FIELDS = ["id", "name", "audio_samples"]

    def __init__(self, profiles_path: str):
        """
        Initialize validator

        Args:
            profiles_path: Path to speaker_profiles directory
        """
        self.profiles_path = Path(profiles_path)
        self.speakers_json_path = self.profiles_path / "speakers.json"

    def validate_speaker_id(self, speaker_id: str) -> Tuple[bool, Optional[str]]:
        """
        Validate speaker ID format

        Args:
            speaker_id: Speaker identifier

        Returns:
            (is_valid, error_message)
        """
        if not speaker_id:
            return False, "Speaker ID cannot be empty"

        if not speaker_id.islower():
            return False, f"Speaker ID '{speaker_id}' must be lowercase"

        if " " in speaker_id:
            return False, f"Speaker ID '{speaker_id}' cannot contain spaces"

        # Check for valid characters (alphanumeric and underscore)
        if not all(c.isalnum() or c == "_" for c in speaker_id):
            return False, f"Speaker ID '{speaker_id}' contains invalid characters (use only letters, numbers, and underscores)"

        return True, None

    def validate_audio_samples(self, speaker_id: str, audio_samples: List[str]) -> Tuple[bool, List[str]]:
        """
        Validate that audio sample files exist

        Args:
            speaker_id: Speaker identifier
            audio_samples: List of relative paths to audio samples

        Returns:
            (is_valid, list_of_errors)
        """
        errors = []

        if not audio_samples:
            errors.append(f"Speaker '{speaker_id}' has no audio samples")
            return False, errors

        if len(audio_samples) < 2:
            errors.append(f"Speaker '{speaker_id}' should have at least 2 audio samples (found {len(audio_samples)})")

        for sample_path in audio_samples:
            full_path = self.profiles_path / sample_path

            if not full_path.exists():
                errors.append(f"Audio sample not found: {sample_path}")
            elif not full_path.is_file():
                errors.append(f"Audio sample is not a file: {sample_path}")
            elif full_path.suffix.lower() != ".wav":
                errors.append(f"Audio sample must be WAV format: {sample_path}")

        return len(errors) == 0, errors

    def validate_speaker(self, speaker: Dict, all_speaker_ids: List[str]) -> Tuple[bool, List[str]]:
        """
        Validate a single speaker entry

        Args:
            speaker: Speaker dictionary
            all_speaker_ids: List of all speaker IDs (for duplicate checking)

        Returns:
            (is_valid, list_of_errors)
        """
        errors = []

        # Check required fields
        for field in self.SPEAKER_REQUIRED_FIELDS:
            if field not in speaker:
                errors.append(f"Missing required field: '{field}'")

        if errors:
            return False, errors

        # Validate speaker ID
        speaker_id = speaker["id"]
        is_valid, error = self.validate_speaker_id(speaker_id)
        if not is_valid:
            errors.append(error)

        # Check for duplicate IDs
        if all_speaker_ids.count(speaker_id) > 1:
            errors.append(f"Duplicate speaker ID: '{speaker_id}'")

        # Validate audio samples
        audio_samples = speaker.get("audio_samples", [])
        samples_valid, sample_errors = self.validate_audio_samples(speaker_id, audio_samples)
        errors.extend(sample_errors)

        # Validate embedding file path if specified
        if "embedding_file" in speaker:
            embedding_path = self.profiles_path / speaker["embedding_file"]
            # Only warn if file doesn't exist (it will be created on first run)
            if not embedding_path.parent.exists():
                errors.append(f"Embedding directory does not exist: {embedding_path.parent}")

        return len(errors) == 0, errors

    def validate_speakers_json(self, data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate the entire speakers.json structure

        Args:
            data: Parsed JSON data

        Returns:
            (is_valid, list_of_errors)
        """
        errors = []

        # Check required top-level fields
        for field in self.REQUIRED_FIELDS:
            if field not in data:
                errors.append(f"Missing required field: '{field}'")
                return False, errors

        # Validate version
        version = data.get("version")
        if not isinstance(version, str):
            errors.append("Version must be a string")

        # Validate speakers array
        speakers = data.get("speakers", [])
        if not isinstance(speakers, list):
            errors.append("'speakers' must be an array")
            return False, errors

        if len(speakers) == 0:
            errors.append("At least one speaker must be defined")

        # Collect all speaker IDs for duplicate checking
        all_speaker_ids = [s.get("id", "") for s in speakers]

        # Validate each speaker
        for idx, speaker in enumerate(speakers):
            is_valid, speaker_errors = self.validate_speaker(speaker, all_speaker_ids)
            if not is_valid:
                errors.append(f"Speaker #{idx + 1} ('{speaker.get('id', 'unknown')}'):")
                errors.extend([f"  - {e}" for e in speaker_errors])

        return len(errors) == 0, errors

    def load_and_validate(self) -> Tuple[bool, Optional[Dict], List[str]]:
        """
        Load and validate speakers.json file

        Returns:
            (is_valid, data, list_of_errors)
        """
        errors = []

        # Check if file exists
        if not self.speakers_json_path.exists():
            errors.append(f"speakers.json not found at: {self.speakers_json_path}")
            return False, None, errors

        # Load JSON
        try:
            with open(self.speakers_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON format: {e}")
            return False, None, errors
        except Exception as e:
            errors.append(f"Error reading file: {e}")
            return False, None, errors

        # Validate structure
        is_valid, validation_errors = self.validate_speakers_json(data)
        errors.extend(validation_errors)

        return is_valid, data, errors

    def get_summary(self, data: Dict) -> Dict:
        """
        Get summary statistics for speaker profiles

        Args:
            data: Parsed speakers.json data

        Returns:
            Dictionary with summary information
        """
        speakers = data.get("speakers", [])

        summary = {
            "total_speakers": len(speakers),
            "speaker_names": [s.get("name", "Unknown") for s in speakers],
            "speaker_ids": [s.get("id", "unknown") for s in speakers],
            "total_audio_samples": sum(len(s.get("audio_samples", [])) for s in speakers),
            "avg_samples_per_speaker": 0
        }

        if summary["total_speakers"] > 0:
            summary["avg_samples_per_speaker"] = summary["total_audio_samples"] / summary["total_speakers"]

        return summary


def main():
    """Test/demo the validator"""
    import sys

    print("=" * 80)
    print("Speaker Profile Validator")
    print("=" * 80)
    print()

    # Determine profiles path
    if len(sys.argv) > 1:
        profiles_path = sys.argv[1]
    else:
        profiles_path = "data/speaker_profiles"

    validator = SpeakerProfileValidator(profiles_path)

    print(f"Validating speakers.json at: {validator.speakers_json_path}")
    print()

    # Load and validate
    is_valid, data, errors = validator.load_and_validate()

    if is_valid:
        print("[SUCCESS] speakers.json is valid!")
        print()

        # Show summary
        summary = validator.get_summary(data)
        print("Summary:")
        print(f"  Total speakers: {summary['total_speakers']}")
        print(f"  Speaker names: {', '.join(summary['speaker_names'])}")
        print(f"  Total audio samples: {summary['total_audio_samples']}")
        print(f"  Avg samples per speaker: {summary['avg_samples_per_speaker']:.1f}")
        print()

        return 0
    else:
        print("[ERROR] Validation failed!")
        print()
        print("Errors found:")
        for error in errors:
            print(f"  - {error}")
        print()

        return 1


if __name__ == "__main__":
    exit(main())
