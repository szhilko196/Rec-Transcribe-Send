"""
Test different ffmpeg capture methods to find what works on this system
"""
import subprocess
import os

ffmpeg_path = "C:/prj/Rec-Transcribe-Send/tools/ffmpeg-8.0-essentials_build/bin/ffmpeg.exe"

print("\n" + "=" * 70)
print("Testing ffmpeg Capture Methods")
print("=" * 70 + "\n")

# Test 1: Check ffmpeg version and build configuration
print("1. Checking ffmpeg build configuration...")
print("-" * 70)
result = subprocess.run(
    [ffmpeg_path, '-version'],
    capture_output=True,
    text=True,
    encoding='utf-8',
    errors='replace'
)
print(result.stdout)

# Test 2: List available input devices
print("\n2. Listing available input devices...")
print("-" * 70)
result = subprocess.run(
    [ffmpeg_path, '-devices'],
    capture_output=True,
    text=True,
    encoding='utf-8',
    errors='replace'
)
print(result.stdout)

# Test 3: Try gdigrab (Windows screen capture)
print("\n3. Testing gdigrab (Windows GDI screen capture)...")
print("-" * 70)
print("Command: ffmpeg -f gdigrab -i desktop -t 1 test_video.mp4")
result = subprocess.run(
    [ffmpeg_path, '-f', 'gdigrab', '-i', 'desktop', '-t', '1', '-y', 'test_video_only.mp4'],
    capture_output=True,
    text=True,
    encoding='utf-8',
    errors='replace',
    timeout=10
)
if os.path.exists('test_video_only.mp4'):
    print("✓ SUCCESS - gdigrab works for screen capture")
    print(f"  Created test file: {os.path.getsize('test_video_only.mp4')} bytes")
    os.remove('test_video_only.mp4')
else:
    print("✗ FAILED - gdigrab does not work")
    print("STDERR:", result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)

# Test 4: Check for DirectShow support
print("\n4. Testing DirectShow (dshow) support...")
print("-" * 70)
result = subprocess.run(
    [ffmpeg_path, '-list_devices', 'true', '-f', 'dshow', '-i', 'dummy'],
    capture_output=True,
    text=True,
    encoding='utf-8',
    errors='replace',
    timeout=10
)
if 'DirectShow audio devices' in result.stderr or 'DirectShow video devices' in result.stderr:
    print("✓ DirectShow is available")
    print(result.stderr)
else:
    print("✗ DirectShow not available or no devices found")
    print("This is common with 'essentials' ffmpeg builds")
    print("STDERR:", result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)

# Test 5: Check if we need full build instead of essentials
print("\n" + "=" * 70)
print("RECOMMENDATIONS:")
print("=" * 70)
print("\nYour ffmpeg build: 'essentials' (minimal features)")
print("\nFor audio recording, you need ONE of these solutions:\n")
print("Solution 1 (Recommended): Download ffmpeg 'full' build")
print("  - Go to: https://www.gyan.dev/ffmpeg/builds/")
print("  - Download: ffmpeg-release-full.7z")
print("  - Extract and update MAC_FFMPEG_PATH in .env")
print("  - This includes DirectShow support for audio capture\n")
print("Solution 2 (Alternative): Use screen+system audio capture")
print("  - Modify ffmpeg command to use audio loopback")
print("  - Captures 'what you hear' instead of microphone")
print("  - Requires different audio input method\n")
print("Solution 3 (Workaround): Video-only for now")
print("  - Disable audio capture temporarily")
print("  - Process videos without audio")
print("  - Transcription will work but no speaker audio\n")
print("=" * 70)
