"""
List available DirectShow audio devices for ffmpeg recording
"""
import subprocess
import sys

ffmpeg_path = "C:/prj/Rec-Transcribe-Send/tools/ffmpeg-8.0-essentials_build/bin/ffmpeg.exe"

print("\n" + "=" * 60)
print("Listing DirectShow Audio Devices for ffmpeg")
print("=" * 60 + "\n")

try:
    # Run ffmpeg to list devices
    result = subprocess.run(
        [ffmpeg_path, '-list_devices', 'true', '-f', 'dshow', '-i', 'dummy'],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )

    # ffmpeg outputs device list to stderr
    output = result.stderr

    # Print the full output
    print(output)

    print("\n" + "=" * 60)
    print("Configuration Instructions:")
    print("=" * 60)
    print("\n1. Find your audio device name from the list above")
    print("   (Look for lines starting with 'DirectShow audio devices')")
    print("\n2. Copy the EXACT device name (in quotes)")
    print("\n3. Add to services/meeting-autocapture/config/.env:")
    print("   MAC_AUDIO_DEVICE=audio=\"Your Device Name Here\"")
    print("\n4. Or edit browser_joiner.py line 255 directly")
    print("\n" + "=" * 60 + "\n")

except FileNotFoundError:
    print(f"[ERROR] ffmpeg not found at: {ffmpeg_path}")
    print("Please update the path in this script.")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] Failed to list devices: {e}")
    sys.exit(1)
