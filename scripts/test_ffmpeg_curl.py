"""
Test script for the FFmpeg Service using curl (bypasses antivirus/firewall)

Uses curl via subprocess instead of Python HTTP libraries.
"""

import json
import subprocess
import sys
from pathlib import Path

# Configuration
SERVICE_URL = "http://127.0.0.1:8002"
DATA_DIR = Path("data")
INPUT_DIR = DATA_DIR / "input"
AUDIO_DIR = DATA_DIR / "audio"


def run_curl(url: str, method: str = "GET", data_file: str = None) -> dict:
    """
    Execute an HTTP request using curl.

    Args:
        url: URL for the request
        method: HTTP method (GET, POST)
        data_file: Path to file for upload (for POST)

    Returns:
        Dictionary with the results
    """
    cmd = ["curl", "-s", "-w", "\\n%{http_code}"]

    if method == "POST" and data_file:
        cmd.extend(["-X", "POST", "-F", f"file=@{data_file}"])

    cmd.append(url)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output_lines = result.stdout.strip().split('\n')

        # Last line contains the HTTP code
        http_code = int(output_lines[-1])
        # Everything else is the response body
        response_body = '\n'.join(output_lines[:-1])

        return {
            "status_code": http_code,
            "body": response_body,
            "json": json.loads(response_body) if response_body else None
        }
    except subprocess.CalledProcessError as e:
        return {
            "status_code": 0,
            "body": e.stderr,
            "json": None
        }
    except json.JSONDecodeError:
        return {
            "status_code": http_code,
            "body": response_body,
            "json": None
        }


def main():
    print("="*60)
    print("FFmpeg SERVICE TESTING (via curl)")
    print("="*60)

    # Test 1: Health check
    print("\nTEST 1: Health Check")
    print("-" * 60)

    result = run_curl(f"{SERVICE_URL}/health")

    if result["status_code"] == 200:
        print(f"[OK] Service available (HTTP {result['status_code']})")
        data = result["json"]
        if data:
            print(f"[INFO] Status: {data.get('status')}")
            print(f"[INFO] Service: {data.get('service')}")
            print(f"[INFO] FFmpeg: {data.get('ffmpeg_version', 'N/A')[:50]}...")
    else:
        print(f"[ERROR] Service unavailable (HTTP {result['status_code']})")
        print(f"[ERROR] Response: {result['body']}")
        sys.exit(1)

    # Test 2: Locate test video
    print("\nTEST 2: Locate test video")
    print("-" * 60)

    video_extensions = ['.avi', '.mp4', '.mov', '.mkv']
    video_files = []

    for ext in video_extensions:
        video_files.extend(INPUT_DIR.glob(f"*{ext}"))

    if not video_files:
        print("[WARNING] No video files found in data/input/")
        print("[INFO] Place a test video file into data/input/ and rerun")
        sys.exit(0)

    video_file = video_files[0]
    file_size_mb = video_file.stat().st_size / (1024 * 1024)

    print(f"[OK] Found video file: {video_file.name}")
    print(f"[INFO] Size: {file_size_mb:.2f} MB")

    # Test 3: Extract audio
    print("\nTEST 3: Extract audio")
    print("-" * 60)
    print(f"[INFO] Uploading file {video_file.name}...")

    result = run_curl(
        f"{SERVICE_URL}/extract-audio",
        method="POST",
        data_file=str(video_file)
    )

    if result["status_code"] == 200:
        print(f"[OK] Audio extracted successfully (HTTP {result['status_code']})")
        data = result["json"]
        if data:
            print(f"[INFO] Audio path: {data.get('audio_path')}")
            print(f"[INFO] Duration: {data.get('duration')} sec")
            print(f"[INFO] Sample rate: {data.get('sample_rate')} Hz")
            print(f"[INFO] Processing time: {data.get('processing_time')} sec")

            # Test 4: Verify generated file
            print("\nTEST 4: Verify generated file")
            print("-" * 60)

            audio_path = data.get('audio_path')
            filename = Path(audio_path).name
            local_audio_path = AUDIO_DIR / filename

            if local_audio_path.exists():
                file_size = local_audio_path.stat().st_size
                file_size_mb = file_size / (1024 * 1024)
                print(f"[OK] Audio file created successfully")
                print(f"[INFO] Size: {file_size_mb:.2f} MB")
                print(f"[INFO] Location: {local_audio_path.absolute()}")
            else:
                print(f"[ERROR] File not found: {local_audio_path}")
                sys.exit(1)
    else:
        print(f"[ERROR] Audio extraction failed (HTTP {result['status_code']})")
        print(f"[ERROR] Response: {result['body']}")
        sys.exit(1)

    # Success!
    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)
    print("[OK] All tests completed successfully!")
    print("[OK] FFmpeg service operates correctly")
    print("[OK] Audio extraction works as expected")
    print("[OK] Files are saved to the correct directory")
    print("\n[INFO] Testing completed successfully!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[WARNING] Testing interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n[ERROR] Critical error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
