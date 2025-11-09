"""
Debug script to test file upload to FFmpeg service
"""
import requests
from pathlib import Path

video_path = Path("data/input/Cisco Meeting - 2025-05-12 09-34-03.mp4")

print(f"Testing upload of: {video_path}")
print(f"File exists: {video_path.exists()}")
print(f"File size: {video_path.stat().st_size / (1024*1024):.2f} MB")

try:
    print("\nOpening file and creating request...")
    with open(video_path, 'rb') as f:
        files = {'file': (video_path.name, f, 'video/mp4')}

        print("Sending POST request...")
        response = requests.post(
            "http://localhost:8002/extract-audio",
            files=files,
            timeout=300
        )

    print(f"\nResponse status: {response.status_code}")
    print(f"Response headers: {response.headers}")
    print(f"Response text: {response.text}")

    if response.status_code == 200:
        data = response.json()
        print(f"\nSuccess!")
        print(f"Audio path: {data.get('audio_path')}")
        print(f"Duration: {data.get('duration')} sec")
    else:
        print(f"\nError: {response.status_code}")

except Exception as e:
    print(f"\nException: {e}")
    import traceback
    traceback.print_exc()
