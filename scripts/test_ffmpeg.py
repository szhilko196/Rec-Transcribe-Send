"""
Test script for the FFmpeg Service

Validates the audio extraction service:
1. Health check endpoint
2. Uploading and processing a test video file
3. Verifying the generated audio file

Usage:
    python scripts/test_ffmpeg.py
    python scripts/test_ffmpeg.py --file path/to/test.avi
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import requests

# Configuration
SERVICE_URL = "http://127.0.0.1:8002"  # Use IPv4 instead of localhost
DATA_DIR = Path("data")
INPUT_DIR = DATA_DIR / "input"
AUDIO_DIR = DATA_DIR / "audio"

# Terminal colors (optional)
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(message: str):
    """Print a formatted header message."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{message}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")


def print_success(message: str):
    """Print a formatted success message."""
    print(f"{Colors.OKGREEN}[OK] {message}{Colors.ENDC}")


def print_error(message: str):
    """Print a formatted error message."""
    print(f"{Colors.FAIL}[ERROR] {message}{Colors.ENDC}")


def print_warning(message: str):
    """Print a formatted warning message."""
    print(f"{Colors.WARNING}[WARNING] {message}{Colors.ENDC}")


def print_info(message: str):
    """Print a formatted info message."""
    print(f"{Colors.OKCYAN}[INFO] {message}{Colors.ENDC}")


def check_service_availability() -> bool:
    """
    Check whether the FFmpeg service is available.

    Returns:
        True if the service is available, False otherwise.
    """
    print_header("TEST 1: Service availability")

    try:
        print_info(f"Connecting to {SERVICE_URL}...")
        response = requests.get(f"{SERVICE_URL}/health", timeout=5)

        if response.status_code == 200:
            data = response.json()
            print_success(f"Service is available (HTTP {response.status_code})")
            print_info(f"Status: {data.get('status')}")
            print_info(f"Service: {data.get('service')}")
            print_info(f"Timestamp: {data.get('timestamp')}")

            if 'ffmpeg_version' in data and data['ffmpeg_version']:
                print_info(f"FFmpeg: {data['ffmpeg_version']}")

            return True
        else:
            print_error(f"Unexpected status code: {response.status_code}")
            print_error(f"Response: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print_error(f"Failed to connect to {SERVICE_URL}")
        print_warning("Make sure the Docker container is running:")
        print_warning("  docker-compose up -d ffmpeg-service")
        return False

    except requests.exceptions.Timeout:
        print_error("Timed out waiting for response")
        return False

    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False


def find_test_video() -> Optional[Path]:
    """
    Locate a test video file in data/input/.

    Returns:
        Path to the video file or None if nothing was found.
    """
    print_header("TEST 2: Locate test video file")

    if not INPUT_DIR.exists():
        print_warning(f"Directory {INPUT_DIR} does not exist")
        INPUT_DIR.mkdir(parents=True, exist_ok=True)
        print_info(f"Created directory {INPUT_DIR}")

    # Search for video files
    video_extensions = ['.avi', '.mp4', '.mov', '.mkv', '.flv', '.wmv']
    video_files = []

    for ext in video_extensions:
        video_files.extend(INPUT_DIR.glob(f"*{ext}"))

    if not video_files:
        print_warning(f"No video files found in {INPUT_DIR}")
        print_info("Place a test video file (.avi, .mp4, etc.) into data/input/")
        return None

    # Use the first file found
    video_file = video_files[0]
    file_size_mb = video_file.stat().st_size / (1024 * 1024)

    print_success(f"Found video file: {video_file.name}")
    print_info(f"Size: {file_size_mb:.2f} MB")
    print_info(f"Path: {video_file}")

    if len(video_files) > 1:
        print_info(f"Found {len(video_files) - 1} more video files (the first will be used)")

    return video_file


def extract_audio(video_path: Path) -> Optional[dict]:
    """
    Send the video to the service to extract audio.

    Args:
        video_path: Path to the video file

    Returns:
        Dictionary with results or None on error
    """
    print_header("TEST 3: Extract audio from video")

    try:
        print_info(f"Uploading file {video_path.name}...")
        print_info(f"Endpoint: POST {SERVICE_URL}/extract-audio")

        # Open the file and send the request
        with open(video_path, 'rb') as f:
            files = {'file': (video_path.name, f, 'video/x-msvideo')}

            start_time = time.time()
            response = requests.post(
                f"{SERVICE_URL}/extract-audio",
                files=files,
                timeout=300  # Maximum 5 minutes
            )
            elapsed_time = time.time() - start_time

        if response.status_code == 200:
            data = response.json()
            print_success(f"Audio extracted successfully (HTTP {response.status_code})")
            print_info(f"Processing time: {elapsed_time:.2f} seconds")
            print_info(f"Status: {data.get('status')}")
            print_info(f"Audio path: {data.get('audio_path')}")

            if 'duration' in data and data['duration']:
                print_info(f"Duration: {data['duration']} seconds")

            print_info(f"Sample rate: {data.get('sample_rate')} Hz")
            print_info(f"Channels: {data.get('channels')} (mono)")
            print_info(f"Format: {data.get('format')}")
            print_info(f"Original file: {data.get('original_filename')}")
            print_info(f"Service processing time: {data.get('processing_time')} sec")

            return data

        else:
            print_error(f"Processing error (HTTP {response.status_code})")
            try:
                error_data = response.json()
                print_error(f"Details: {error_data.get('detail', 'No description')}")
            except:
                print_error(f"Response: {response.text}")
            return None

    except requests.exceptions.Timeout:
        print_error("Request timed out (300 seconds)")
        print_warning("Larger files may require more time")
        return None

    except requests.exceptions.ConnectionError:
        print_error("Connection to the service was lost")
        return None

    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return None


def verify_audio_file(audio_path: str) -> bool:
    """
    Ensure the generated audio file exists and is accessible.

    Args:
        audio_path: Audio file path returned by the API

    Returns:
        True if the file exists and is valid
    """
    print_header("TEST 4: Verify generated audio file")

    # Extract file name from path
    # Path is usually: /app/data/audio/filename.wav
    filename = Path(audio_path).name
    local_audio_path = AUDIO_DIR / filename

    print_info(f"Checking file: {local_audio_path}")

    if not local_audio_path.exists():
        print_error(f"File not found: {local_audio_path}")
        print_warning("Ensure the volume is mounted correctly in docker-compose.yml")
        return False

    # Validate file size
    file_size = local_audio_path.stat().st_size
    file_size_mb = file_size / (1024 * 1024)

    if file_size == 0:
        print_error("File is empty (0 bytes)")
        return False

    print_success("Audio file created successfully")
    print_info(f"Size: {file_size_mb:.2f} MB ({file_size:,} bytes)")
    print_info(f"Location: {local_audio_path.absolute()}")

    # Validate extension
    if local_audio_path.suffix.lower() != '.wav':
        print_warning(f"Unexpected file extension: {local_audio_path.suffix}")

    return True


def cleanup_test_files(audio_path: Optional[str] = None):
    """
    Optional cleanup of generated test files.

    Args:
        audio_path: Path to the generated audio file
    """
    print_header("CLEANUP")

    response = input("Delete the generated audio file? (y/n): ").lower().strip()

    if response == 'y' and audio_path:
        filename = Path(audio_path).name
        local_audio_path = AUDIO_DIR / filename

        if local_audio_path.exists():
            try:
                local_audio_path.unlink()
                print_success(f"File deleted: {filename}")
            except Exception as e:
                print_error(f"Failed to delete file: {e}")
        else:
            print_warning("File no longer exists")
    else:
        print_info("Cleanup skipped")


def main():
    """
    Main testing entry point.
    """
    parser = argparse.ArgumentParser(
        description="FFmpeg Service testing"
    )
    parser.add_argument(
        '--file',
        type=str,
        help='Path to a specific video file for testing'
    )
    parser.add_argument(
        '--no-cleanup',
        action='store_true',
        help='Skip cleanup prompt after the test'
    )

    args = parser.parse_args()

    print_header("FFmpeg SERVICE TESTING")
    print_info(f"Service URL: {SERVICE_URL}")
    print_info(f"Data directory: {DATA_DIR.absolute()}")

    # Test 1: Health check
    if not check_service_availability():
        print_error("\nTEST FAILED: Service unavailable")
        sys.exit(1)

    # Test 2: Locate video file
    if args.file:
        video_path = Path(args.file)
        if not video_path.exists():
            print_error(f"File not found: {video_path}")
            sys.exit(1)
        print_success(f"Using provided file: {video_path}")
    else:
        video_path = find_test_video()

    if not video_path:
        print_warning("\nTEST SKIPPED: No video file available")
        print_info("Place a test .avi or .mp4 file into data/input/ and rerun")
        sys.exit(0)

    # Test 3: Extract audio
    result = extract_audio(video_path)

    if not result:
        print_error("\nTEST FAILED: Audio extraction unsuccessful")
        sys.exit(1)

    # Test 4: Verify file
    audio_path = result.get('audio_path')
    if not verify_audio_file(audio_path):
        print_error("\nTEST FAILED: Audio file invalid")
        sys.exit(1)

    # Success!
    print_header("TEST RESULTS")
    print_success("All tests completed successfully!")
    print_success("FFmpeg service operates correctly")
    print_success("Audio extraction functions properly")
    print_success("Files are saved to the correct directory")

    # Cleanup
    if not args.no_cleanup:
        cleanup_test_files(audio_path)

    print_info("\nTesting completed successfully!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_warning("\n\nTesting interrupted by user")
        sys.exit(130)
    except Exception as e:
        print_error(f"\nCritical error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
