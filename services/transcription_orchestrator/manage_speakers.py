"""
Speaker Profile Management Utility

This script helps manage speaker profiles for the speaker recognition system.
It provides commands to:
- Initialize speakers.json
- Add new speakers
- List existing speakers
- Remove speakers
- Validate profiles
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from speaker_profile_validator import SpeakerProfileValidator


class SpeakerProfileManager:
    """Manager for speaker profiles"""

    def __init__(self, profiles_path: str):
        """
        Initialize manager

        Args:
            profiles_path: Path to speaker_profiles directory
        """
        self.profiles_path = Path(profiles_path)
        self.speakers_json_path = self.profiles_path / "speakers.json"
        self.validator = SpeakerProfileValidator(profiles_path)

    def initialize_speakers_json(self) -> bool:
        """
        Create a new speakers.json file with default structure

        Returns:
            True if successful
        """
        if self.speakers_json_path.exists():
            print(f"[ERROR] speakers.json already exists at: {self.speakers_json_path}")
            print("Use --force to overwrite")
            return False

        default_data = {
            "version": "1.0",
            "speakers": [],
            "settings": {
                "min_segment_duration": 1.0,
                "embedding_aggregation": "mean",
                "normalization": "cosine"
            }
        }

        try:
            with open(self.speakers_json_path, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, ensure_ascii=False, indent=2)

            print(f"[SUCCESS] Created speakers.json at: {self.speakers_json_path}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to create speakers.json: {e}")
            return False

    def load_speakers_json(self) -> Dict:
        """
        Load speakers.json file

        Returns:
            Parsed JSON data
        """
        if not self.speakers_json_path.exists():
            print(f"[ERROR] speakers.json not found at: {self.speakers_json_path}")
            print("Run with --init to create it")
            sys.exit(1)

        try:
            with open(self.speakers_json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to load speakers.json: {e}")
            sys.exit(1)

    def save_speakers_json(self, data: Dict) -> bool:
        """
        Save speakers.json file

        Args:
            data: Data to save

        Returns:
            True if successful
        """
        try:
            with open(self.speakers_json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to save speakers.json: {e}")
            return False

    def add_speaker(self, speaker_id: str, name: str, audio_samples: List[str],
                   role: str = None, department: str = None, email: str = None) -> bool:
        """
        Add a new speaker to speakers.json

        Args:
            speaker_id: Unique identifier (lowercase, no spaces)
            name: Display name (can be in any language)
            audio_samples: List of audio sample paths (relative to speaker_profiles/)
            role: Optional role
            department: Optional department
            email: Optional email

        Returns:
            True if successful
        """
        # Validate speaker ID
        is_valid, error = self.validator.validate_speaker_id(speaker_id)
        if not is_valid:
            print(f"[ERROR] {error}")
            return False

        # Load existing data
        data = self.load_speakers_json()

        # Check for duplicate ID
        if any(s["id"] == speaker_id for s in data["speakers"]):
            print(f"[ERROR] Speaker with ID '{speaker_id}' already exists")
            return False

        # Create speaker entry
        speaker = {
            "id": speaker_id,
            "name": name,
            "audio_samples": audio_samples,
            "embedding_file": f"embeddings/{speaker_id}_embed.npy",
            "created_at": datetime.now().isoformat()
        }

        # Add optional metadata
        if role or department or email:
            speaker["metadata"] = {}
            if role:
                speaker["metadata"]["role"] = role
            if department:
                speaker["metadata"]["department"] = department
            if email:
                speaker["metadata"]["email"] = email

        # Add to speakers list
        data["speakers"].append(speaker)

        # Validate before saving
        is_valid, errors = self.validator.validate_speakers_json(data)
        if not is_valid:
            print("[ERROR] Validation failed:")
            for error in errors:
                print(f"  - {error}")
            return False

        # Save
        if self.save_speakers_json(data):
            print(f"[SUCCESS] Added speaker '{name}' (ID: {speaker_id})")
            print(f"  Audio samples: {len(audio_samples)}")
            return True

        return False

    def list_speakers(self) -> None:
        """List all speakers"""
        data = self.load_speakers_json()
        speakers = data.get("speakers", [])

        if not speakers:
            print("No speakers found in speakers.json")
            return

        print(f"Found {len(speakers)} speaker(s):")
        print()

        for speaker in speakers:
            print(f"ID: {speaker['id']}")
            print(f"  Name: {speaker['name']}")
            print(f"  Audio samples: {len(speaker.get('audio_samples', []))}")

            if "metadata" in speaker:
                metadata = speaker["metadata"]
                if "role" in metadata:
                    print(f"  Role: {metadata['role']}")
                if "department" in metadata:
                    print(f"  Department: {metadata['department']}")

            print(f"  Created: {speaker.get('created_at', 'Unknown')}")
            print()

    def remove_speaker(self, speaker_id: str) -> bool:
        """
        Remove a speaker from speakers.json

        Args:
            speaker_id: Speaker identifier to remove

        Returns:
            True if successful
        """
        data = self.load_speakers_json()

        # Find speaker
        speaker = next((s for s in data["speakers"] if s["id"] == speaker_id), None)

        if not speaker:
            print(f"[ERROR] Speaker '{speaker_id}' not found")
            return False

        # Remove speaker
        data["speakers"] = [s for s in data["speakers"] if s["id"] != speaker_id]

        # Save
        if self.save_speakers_json(data):
            print(f"[SUCCESS] Removed speaker '{speaker['name']}' (ID: {speaker_id})")
            print(f"[INFO] Audio files and embeddings were not deleted. Remove manually if needed.")
            return True

        return False

    def validate(self) -> bool:
        """
        Validate speakers.json

        Returns:
            True if valid
        """
        is_valid, data, errors = self.validator.load_and_validate()

        if is_valid:
            print("[SUCCESS] speakers.json is valid!")
            print()

            # Show summary
            summary = self.validator.get_summary(data)
            print("Summary:")
            print(f"  Total speakers: {summary['total_speakers']}")
            print(f"  Speaker names: {', '.join(summary['speaker_names'])}")
            print(f"  Total audio samples: {summary['total_audio_samples']}")
            print(f"  Avg samples per speaker: {summary['avg_samples_per_speaker']:.1f}")
            return True
        else:
            print("[ERROR] Validation failed!")
            print()
            print("Errors found:")
            for error in errors:
                print(f"  - {error}")
            return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Manage speaker profiles for speaker recognition system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initialize speakers.json
  python manage_speakers.py --init

  # Add a new speaker
  python manage_speakers.py --add ivan_petrov --name "Иван Петров" \\
      --samples "ivan_petrov/sample_01.wav,ivan_petrov/sample_02.wav,ivan_petrov/sample_03.wav" \\
      --role "Project Manager" --department "Engineering"

  # List all speakers
  python manage_speakers.py --list

  # Validate speakers.json
  python manage_speakers.py --validate

  # Remove a speaker
  python manage_speakers.py --remove ivan_petrov
        """
    )

    parser.add_argument('--profiles-path', default='data/speaker_profiles',
                       help='Path to speaker_profiles directory (default: data/speaker_profiles)')

    # Commands
    parser.add_argument('--init', action='store_true',
                       help='Initialize speakers.json')
    parser.add_argument('--add', metavar='SPEAKER_ID',
                       help='Add a new speaker (provide speaker ID)')
    parser.add_argument('--remove', metavar='SPEAKER_ID',
                       help='Remove a speaker (provide speaker ID)')
    parser.add_argument('--list', action='store_true',
                       help='List all speakers')
    parser.add_argument('--validate', action='store_true',
                       help='Validate speakers.json')

    # Speaker details (for --add)
    parser.add_argument('--name', help='Speaker display name (required with --add)')
    parser.add_argument('--samples', help='Comma-separated list of audio sample paths (required with --add)')
    parser.add_argument('--role', help='Speaker role (optional)')
    parser.add_argument('--department', help='Speaker department (optional)')
    parser.add_argument('--email', help='Speaker email (optional)')

    args = parser.parse_args()

    # Create manager
    manager = SpeakerProfileManager(args.profiles_path)

    # Execute command
    if args.init:
        success = manager.initialize_speakers_json()
        return 0 if success else 1

    elif args.add:
        if not args.name or not args.samples:
            print("[ERROR] --add requires --name and --samples")
            return 1

        audio_samples = [s.strip() for s in args.samples.split(',')]
        success = manager.add_speaker(
            speaker_id=args.add,
            name=args.name,
            audio_samples=audio_samples,
            role=args.role,
            department=args.department,
            email=args.email
        )
        return 0 if success else 1

    elif args.remove:
        success = manager.remove_speaker(args.remove)
        return 0 if success else 1

    elif args.list:
        manager.list_speakers()
        return 0

    elif args.validate:
        success = manager.validate()
        return 0 if success else 1

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
