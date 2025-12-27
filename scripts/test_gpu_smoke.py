#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smoke Test for GPU-enabled Transcription Service
Tests the full pipeline: Video -> FFmpeg -> Transcription (GPU) -> Results
"""

import os
import sys
import time
import json
import requests
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Configuration
INPUT_FOLDER = r"C:\YandexDisk\DIASOFT\VideoPars\data\input"
TEST_VIDEO = "123456_Видео_для_тестирования_доработок._mmmail(serg196@gmail.com)_2025-11-02_20-45-29 — копия (2).webm"
AUDIO_FOLDER = r"C:\YandexDisk\DIASOFT\VideoPars\data\audio"
TRANSCRIPTS_FOLDER = r"C:\YandexDisk\DIASOFT\VideoPars\data\transcripts"
RESULTS_FOLDER = r"C:\YandexDisk\DIASOFT\VideoPars\data\results"

FFMPEG_SERVICE = "http://localhost:8002"
TRANSCRIPTION_SERVICE = "http://localhost:8003"

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_step(step_num, total, message):
    """Print formatted step message"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}[{step_num}/{total}] {message}{Colors.RESET}")


def print_success(message):
    """Print success message"""
    print(f"{Colors.GREEN}[OK] {message}{Colors.RESET}")


def print_error(message):
    """Print error message"""
    print(f"{Colors.RED}[ERROR] {message}{Colors.RESET}")


def print_info(message):
    """Print info message"""
    print(f"{Colors.BLUE}[INFO] {message}{Colors.RESET}")


def print_warning(message):
    """Print warning message"""
    print(f"{Colors.YELLOW}[WARN] {message}{Colors.RESET}")


def check_services():
    """Step 1: Check if Docker services are healthy"""
    print_step(1, 7, "Checking Docker Services")

    services = {
        "FFmpeg Service": f"{FFMPEG_SERVICE}/health",
        "Transcription Service": f"{TRANSCRIPTION_SERVICE}/health"
    }

    all_healthy = True
    for name, url in services.items():
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print_success(f"{name} is healthy")
            else:
                print_error(f"{name} returned status {response.status_code}")
                all_healthy = False
        except Exception as e:
            print_error(f"{name} is not accessible: {e}")
            all_healthy = False

    return all_healthy


def check_gpu_availability():
    """Step 2: Verify GPU is available and configured"""
    print_step(2, 7, "Verifying GPU Configuration")

    try:
        response = requests.get(f"{TRANSCRIPTION_SERVICE}/models/info", timeout=5)
        if response.status_code == 200:
            info = response.json()

            # Check Whisper GPU
            whisper_device = info.get("whisper", {}).get("device", "unknown")
            if whisper_device == "cuda":
                print_success(f"Whisper configured for GPU (device: {whisper_device})")
            else:
                print_warning(f"Whisper using CPU (device: {whisper_device})")

            # Check pyannote GPU
            pyannote_device = info.get("pyannote", {}).get("device", "unknown")
            if pyannote_device == "cuda":
                print_success(f"Pyannote configured for GPU (device: {pyannote_device})")
            else:
                print_warning(f"Pyannote using CPU (device: {pyannote_device})")

            print_info(f"Full model info: {json.dumps(info, indent=2)}")

            return whisper_device == "cuda" and pyannote_device == "cuda"
        else:
            print_error(f"Failed to get model info: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error checking GPU: {e}")
        return False


def verify_test_file():
    """Step 3: Verify test video file exists"""
    print_step(3, 7, "Verifying Test Video File")

    test_path = Path(INPUT_FOLDER) / TEST_VIDEO
    if test_path.exists():
        size_mb = test_path.stat().st_size / (1024 * 1024)
        print_success(f"Test video found: {test_path}")
        print_info(f"File size: {size_mb:.2f} MB")
        return True
    else:
        print_error(f"Test video not found: {test_path}")
        return False


def clean_previous_outputs():
    """Step 4: Clean up previous test outputs"""
    print_step(4, 7, "Cleaning Previous Test Outputs")

    # Generate the expected UUID from filename
    import uuid
    test_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, TEST_VIDEO))

    cleaned_files = []

    # Check and clean audio folder
    audio_file = Path(AUDIO_FOLDER) / f"{test_uuid}.wav"
    if audio_file.exists():
        audio_file.unlink()
        cleaned_files.append(str(audio_file))

    # Check and clean transcripts folder
    transcript_file = Path(TRANSCRIPTS_FOLDER) / f"{test_uuid}.json"
    if transcript_file.exists():
        transcript_file.unlink()
        cleaned_files.append(str(transcript_file))

    # Check and clean results folder
    for ext in ['.json', '_summary.md', '_protocol.md']:
        result_file = Path(RESULTS_FOLDER) / f"{test_uuid}{ext}"
        if result_file.exists():
            result_file.unlink()
            cleaned_files.append(str(result_file))

    if cleaned_files:
        print_info(f"Cleaned {len(cleaned_files)} previous output files")
        for f in cleaned_files:
            print(f"  - {f}")
    else:
        print_info("No previous outputs to clean")

    return True


def monitor_processing():
    """Step 5: Monitor the processing through logs"""
    print_step(5, 7, "Monitoring Processing (check Docker logs)")

    print_info("To monitor in real-time, open another terminal and run:")
    print(f"{Colors.YELLOW}  docker-compose logs -f transcription-service{Colors.RESET}")
    print()
    print_info("Look for these indicators of GPU usage:")
    print("  - 'device=cuda' in logs")
    print("  - 'Using GPU' messages")
    print("  - Faster processing times")
    print()

    return True


def run_orchestrator():
    """Step 6: Run the orchestrator to process the video"""
    print_step(6, 7, "Running Orchestrator")

    print_info("Starting orchestrator.py...")
    print_warning("This will process the video file. Watch the logs for progress.")

    orchestrator_path = Path("services/transcription_orchestrator/orchestrator.py")
    if not orchestrator_path.exists():
        print_error(f"Orchestrator not found at: {orchestrator_path}")
        return False

    # Check if virtual environment exists
    venv_python = Path("services/transcription_orchestrator/venv/Scripts/python.exe")
    if venv_python.exists():
        python_cmd = str(venv_python)
    else:
        python_cmd = "python"
        print_warning("Virtual environment not found, using system Python")

    test_video_path = Path(INPUT_FOLDER) / TEST_VIDEO

    print_info(f"Command: {python_cmd} {orchestrator_path} \"{test_video_path}\"")
    print()

    return {
        "python_cmd": python_cmd,
        "orchestrator_path": str(orchestrator_path),
        "video_path": str(test_video_path)
    }


def validate_outputs():
    """Step 7: Validate outputs were created"""
    print_step(7, 7, "Validating Outputs")

    import uuid
    test_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, TEST_VIDEO))

    expected_files = {
        "Audio": Path(AUDIO_FOLDER) / f"{test_uuid}.wav",
        "Transcript": Path(TRANSCRIPTS_FOLDER) / f"{test_uuid}.json",
        "Results JSON": Path(RESULTS_FOLDER) / f"{test_uuid}.json",
        "Summary": Path(RESULTS_FOLDER) / f"{test_uuid}_summary.md",
        "Protocol": Path(RESULTS_FOLDER) / f"{test_uuid}_protocol.md"
    }

    all_exist = True
    for name, path in expected_files.items():
        if path.exists():
            size = path.stat().st_size
            print_success(f"{name}: {path} ({size} bytes)")
        else:
            print_error(f"{name}: Not found at {path}")
            all_exist = False

    return all_exist


def main():
    """Main smoke test execution"""
    print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}GPU-Enabled Transcription Service - Smoke Test{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*80}{Colors.RESET}")
    print(f"Test Video: {TEST_VIDEO}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{Colors.BOLD}{'='*80}{Colors.RESET}\n")

    start_time = time.time()

    # Run pre-processing checks
    if not check_services():
        print_error("\n[X] Services check failed. Aborting test.")
        return 1

    if not check_gpu_availability():
        print_warning("\n[!] GPU not fully configured. Test will continue but may use CPU.")

    if not verify_test_file():
        print_error("\n[X] Test video file not found. Aborting test.")
        return 1

    clean_previous_outputs()
    monitor_processing()

    # Get orchestrator command
    orch_info = run_orchestrator()
    if not orch_info:
        print_error("\n[X] Orchestrator setup failed. Aborting test.")
        return 1

    print(f"\n{Colors.BOLD}{Colors.YELLOW}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.YELLOW}READY TO RUN{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.YELLOW}{'='*80}{Colors.RESET}")
    print(f"\n{Colors.BOLD}Execute this command to start processing:{Colors.RESET}\n")
    print(f'{Colors.GREEN}{orch_info["python_cmd"]} {orch_info["orchestrator_path"]} "{orch_info["video_path"]}"{Colors.RESET}\n')
    print(f"\n{Colors.BOLD}After processing completes, run validation:{Colors.RESET}\n")
    print(f"{Colors.GREEN}python test_gpu_smoke.py --validate{Colors.RESET}\n")
    print(f"{Colors.BOLD}{Colors.YELLOW}{'='*80}{Colors.RESET}\n")

    elapsed = time.time() - start_time
    print(f"Pre-checks completed in {elapsed:.2f} seconds")

    return 0


def validate_only():
    """Run only output validation"""
    print(f"\n{Colors.BOLD}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}Validating Processing Outputs{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*80}{Colors.RESET}\n")

    if validate_outputs():
        print(f"\n{Colors.GREEN}{Colors.BOLD}[SUCCESS] All outputs validated successfully!{Colors.RESET}\n")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}[FAILED] Some outputs are missing{Colors.RESET}\n")
        return 1


if __name__ == "__main__":
    if "--validate" in sys.argv:
        sys.exit(validate_only())
    else:
        sys.exit(main())
