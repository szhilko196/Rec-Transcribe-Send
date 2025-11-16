"""
Detailed Telemost Test - Shows all button clicks
"""
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
import logging

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,  # Show all debug messages
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add src to path
sys.path.insert(0, 'src')

from models import MeetingInvitation
from browser_joiner import BrowserJoiner

def load_meeting_from_file(filepath: str) -> MeetingInvitation:
    """Load meeting from JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Convert ISO datetime strings back to datetime objects
    for key in ['start_time', 'end_time', 'created_at', 'processed_at']:
        if key in data and data[key]:
            data[key] = datetime.fromisoformat(data[key])

    return MeetingInvitation(**data)

def main():
    load_dotenv('config/.env')

    print("=" * 70)
    print("DETAILED TELEMOST TEST")
    print("=" * 70)

    meeting_file = "data/meetings/completed/3b2bfe5c-aa80-4784-b93a-a74f7fe9ce2d.json"
    meeting = load_meeting_from_file(meeting_file)

    print(f"\nMeeting Info:")
    print(f"  sender_name: {meeting.sender_name}")
    print(f"  sender_email: {meeting.sender_email}")
    print(f"  Link: {meeting.meeting_link}")

    extension_path = os.path.abspath(os.getenv('MAC_CHROME_EXTENSION_PATH'))
    profiles_path = os.path.abspath(os.getenv('MAC_BROWSER_PROFILES_PATH', './data/browser_profiles'))

    print(f"\nLaunching browser...")
    print("WATCH for these steps:")
    print("  1. Click 'Prodolzhit v brauzere' (Continue in browser)")
    print("  2. Enter name in field")
    print("  3. Click 'Podklyuchitsya' (Connect)")
    print("  4. Start recording")
    print()

    joiner = BrowserJoiner(
        extension_path=extension_path,
        profiles_path=profiles_path
    )

    try:
        context = joiner.join_meeting(meeting)

        if context:
            print("\n" + "=" * 70)
            print("SUCCESS - Check the browser window!")
            print("=" * 70)
            print("Browser will stay open for 45 seconds...")

            import time
            time.sleep(45)

            print("\nClosing browser...")
            joiner.stop_recording(context)
            context.close()
            joiner.cleanup()
        else:
            print("\nERROR - Failed to join")
            joiner.cleanup()

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
