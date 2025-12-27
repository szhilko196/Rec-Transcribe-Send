"""
Find available DirectShow audio devices for ffmpeg recording
"""
import subprocess

ffmpeg_path = "C:/prj/Rec-Transcribe-Send/tools/ffmpeg-full/bin/ffmpeg.exe"

print("\n" + "=" * 70)
print("Finding DirectShow Audio Devices")
print("=" * 70 + "\n")

try:
    # Run ffmpeg to list devices
    result = subprocess.run(
        [ffmpeg_path, '-list_devices', 'true', '-f', 'dshow', '-i', 'dummy'],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        timeout=10
    )

    # ffmpeg outputs device list to stderr
    output = result.stderr

    # Extract audio devices
    lines = output.split('\n')
    audio_devices = []
    in_audio_section = False

    for line in lines:
        if 'DirectShow audio devices' in line:
            in_audio_section = True
            print("DirectShow Audio Devices Found:\n")
            continue
        elif 'DirectShow video devices' in line:
            in_audio_section = False
            break

        if in_audio_section and '"' in line:
            # Extract device name from line like: [dshow @ ...] "Microphone Array (Realtek Audio)"
            if ']  "' in line:
                device_name = line.split(']  "')[1].split('"')[0]
                audio_devices.append(device_name)
                print(f"  [OK] {device_name}")

    if not audio_devices:
        print("[ERROR] No audio devices found!")
        print("\nFull ffmpeg output:")
        print(output)
    else:
        print("\n" + "=" * 70)
        print("Configuration for .env file:")
        print("=" * 70 + "\n")
        print("Choose one of the devices above and add to your .env file:\n")

        for i, device in enumerate(audio_devices, 1):
            print(f"{i}. MAC_AUDIO_DEVICE=audio=\"{device}\"")

        print("\n" + "=" * 70)
        print("Recommendations:")
        print("=" * 70)
        print("\n* For MICROPHONE recording: Choose 'Microphone' or 'Mic' device")
        print("* For SYSTEM AUDIO (what you hear): Choose 'Stereo Mix' if available")
        print("* For BOTH: You'll need virtual audio cable software\n")

except FileNotFoundError:
    print(f"[ERROR] ffmpeg not found at: {ffmpeg_path}")
    print("Please check if you extracted ffmpeg-full correctly")
except Exception as e:
    print(f"[ERROR] {e}")
