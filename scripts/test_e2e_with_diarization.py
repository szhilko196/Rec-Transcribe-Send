"""
E2E testing: FFmpeg + Transcription with diarization (Whisper + pyannote)

This script:
1. Extracts audio from video (FFmpeg Service)
2. Transcribes speech AND detects speakers (Transcription Service)
3. Saves the result with speaker-labeled text
"""

import json
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

# Configuration
FFMPEG_SERVICE_URL = "http://127.0.0.1:8002"
TRANSCRIPTION_SERVICE_URL = "http://127.0.0.1:8003"
DATA_DIR = Path("data")
INPUT_DIR = DATA_DIR / "input"
AUDIO_DIR = DATA_DIR / "audio"
TRANSCRIPTS_DIR = DATA_DIR / "transcripts"


def run_curl(url: str, method: str = "GET", data_file: str = None, field_name: str = "file", timeout: int = 1800) -> dict:
    """
    Execute an HTTP request via curl

    Args:
        url: URL for the request
        method: HTTP method (GET, POST)
        data_file: Path to file for upload (for POST)
        field_name: Form field name for the file
        timeout: Timeout in seconds (default 30 minutes)

    Returns:
        Dictionary with results
    """
    cmd = ["curl", "-s", "-w", "\\n%{http_code}"]

    if method == "POST" and data_file:
        cmd.extend(["-X", "POST", "-F", f"{field_name}=@{data_file}"])

    cmd.append(url)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=timeout)
        output_lines = result.stdout.strip().split('\n')

        # Last line is the HTTP status code
        http_code = int(output_lines[-1])
        # Everything else is the response body
        response_body = '\n'.join(output_lines[:-1])

        return {
            "status_code": http_code,
            "body": response_body,
            "json": json.loads(response_body) if response_body else None
        }
    except subprocess.TimeoutExpired:
        return {
            "status_code": 0,
            "body": f"Request timeout (>{timeout}s)",
            "json": None
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
    print("="*70)
    print("E2E TESTING: TRANSCRIPTION WITH DIARIZATION")
    print("="*70)

    # Step 1: Check services
    print("\n[STEP 1] Checking service availability")
    print("-" * 70)

    # FFmpeg Service
    result = run_curl(f"{FFMPEG_SERVICE_URL}/health")
    if result["status_code"] == 200:
        print(f"[OK] FFmpeg Service available")
    else:
        print(f"[ERROR] FFmpeg Service unavailable (HTTP {result['status_code']})")
        sys.exit(1)

    # Transcription Service
    result = run_curl(f"{TRANSCRIPTION_SERVICE_URL}/health")
    if result["status_code"] == 200:
        print(f"[OK] Transcription Service available")
        data = result["json"]
        if data:
            print(f"  Status: {data.get('status')}")
            print(f"  Models loaded: {data.get('models_loaded')}")

            if not data.get('models_loaded'):
                print("[ERROR] Models are not loaded! Diarization unavailable.")
                sys.exit(1)
    else:
        print(f"[ERROR] Transcription Service unavailable (HTTP {result['status_code']})")
        sys.exit(1)

    # Step 2: Locate a test video
    print("\n[STEP 2] Searching for a test video")
    print("-" * 70)

    video_extensions = ['.avi', '.mp4', '.mov', '.mkv', '.webm']
    video_files = []

    for ext in video_extensions:
        video_files.extend(INPUT_DIR.glob(f"*{ext}"))

    if not video_files:
        print("[WARNING] No video files found in data/input/")
        print("  Place a test video file into data/input/ and run again")
        sys.exit(0)

    video_file = video_files[0]
    file_size_mb = video_file.stat().st_size / (1024 * 1024)

    print(f"[OK] Found video file: {video_file.name}")
    print(f"  Size: {file_size_mb:.2f} MB")

    # Step 3: Extract audio
    print("\n[STEP 3] Extracting audio from the video")
    print("-" * 70)
    print(f"  Processing file: {video_file.name}")

    start_time = time.time()
    result = run_curl(
        f"{FFMPEG_SERVICE_URL}/extract-audio",
        method="POST",
        data_file=str(video_file)
    )
    extraction_time = time.time() - start_time

    if result["status_code"] != 200:
        print(f"[ERROR] Audio extraction failed (HTTP {result['status_code']})")
        print(f"  Response: {result['body']}")
        sys.exit(1)

    data = result["json"]
    audio_filename = Path(data.get('audio_path')).name
    audio_file = AUDIO_DIR / audio_filename

    print(f"[OK] Audio extracted successfully")
    print(f"  File: {audio_filename}")
    print(f"  Duration: {data.get('duration')} sec")
    print(f"  Sample rate: {data.get('sample_rate')} Hz")
    print(f"  Processing time: {extraction_time:.2f} sec")

    if not audio_file.exists():
        print(f"[ERROR] Audio file not found: {audio_file}")
        sys.exit(1)

    audio_size_mb = audio_file.stat().st_size / (1024 * 1024)
    print(f"  Audio size: {audio_size_mb:.2f} MB")

    # Step 4: Transcription with diarization
    print("\n[STEP 4] Transcription with diarization (Whisper + pyannote)")
    print("-" * 70)
    print(f"  Processing file: {audio_filename}")
    print("  WARNING: This may take 10-20 minutes for a 12-minute audio clip!")
    print("  The process includes:")
    print("    1. Speech transcription (Whisper)")
    print("    2. Speaker diarization (pyannote)")
    print("    3. Merging the results")

    start_time = time.time()
    result = run_curl(
        f"{TRANSCRIPTION_SERVICE_URL}/transcribe-with-speakers",
        method="POST",
        data_file=str(audio_file),
        field_name="file",
        timeout=1800  # 30 minutes
    )
    transcription_time = time.time() - start_time

    if result["status_code"] != 200:
        print(f"[ERROR] Transcription with diarization failed (HTTP {result['status_code']})")
        print(f"  Response: {result['body'][:500]}")
        sys.exit(1)

    transcript_data = result["json"]

    print(f"[OK] Transcription with diarization completed")
    print(f"  Processing time: {transcription_time:.2f} sec ({transcription_time/60:.1f} min)")
    print(f"  Number of segments: {transcript_data.get('num_segments', 0)}")
    print(f"  Number of speakers: {transcript_data.get('num_speakers', 0)}")

    # Step 5: Retrieve detailed transcript
    print("\n[STEP 5] Downloading detailed transcript")
    print("-" * 70)

    # Path to the transcript file inside the container
    transcript_path = transcript_data.get('transcript_path')
    if transcript_path:
        # Extract filename from path
        transcript_filename = Path(transcript_path).name
        # Host path (via volume mapping)
        local_transcript_file = TRANSCRIPTS_DIR / transcript_filename

        if local_transcript_file.exists():
            with open(local_transcript_file, 'r', encoding='utf-8') as f:
                full_transcript = json.load(f)

            print(f"[OK] Detailed transcript loaded")
            print(f"  File: {transcript_filename}")
        else:
            print(f"[WARNING] Transcript file not found: {local_transcript_file}")
            full_transcript = None
    else:
        print(f"[WARNING] Transcript path not provided")
        full_transcript = None

    # Step 6: Save consolidated result
    print("\n[STEP 6] Saving consolidated result")
    print("-" * 70)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = video_file.stem
    result_file = TRANSCRIPTS_DIR / f"{base_name}_{timestamp}_with_speakers.json"

    result_data = {
        "metadata": {
            "source_video": video_file.name,
            "audio_file": audio_filename,
            "processed_at": datetime.now().isoformat(),
            "extraction_time_sec": round(extraction_time, 2),
            "transcription_time_sec": round(transcription_time, 2),
            "total_time_sec": round(extraction_time + transcription_time, 2),
            "audio_duration_sec": data.get('duration'),
            "num_segments": transcript_data.get('num_segments', 0),
            "num_speakers": transcript_data.get('num_speakers', 0)
        },
        "summary": transcript_data,
        "full_transcript": full_transcript
    }

    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    print(f"[OK] Result saved: {result_file.name}")
    print(f"  Path: {result_file.absolute()}")

    # Step 7: Preview
    print("\n[STEP 7] Preview transcript with speakers")
    print("-" * 70)

    if full_transcript and 'transcript' in full_transcript:
        segments = full_transcript['transcript']
        preview_count = min(10, len(segments))

        print(f"  First {preview_count} segments:\n")

        for i, segment in enumerate(segments[:preview_count], 1):
            start = segment.get('start', 0)
            end = segment.get('end', 0)
            speaker = segment.get('speaker', 'UNKNOWN')
            text = segment.get('text', '').strip()

            print(f"  [{i}] {start:.1f}s - {end:.1f}s | {speaker}")
            print(f"      {text}\n")

        if len(segments) > preview_count:
            print(f"  ... and {len(segments) - preview_count} more segments")

        # Speaker statistics
        print("\n  Speaker statistics:")
        speakers_stats = {}
        for seg in segments:
            speaker = seg.get('speaker', 'UNKNOWN')
            if speaker not in speakers_stats:
                speakers_stats[speaker] = {'count': 0, 'duration': 0}
            speakers_stats[speaker]['count'] += 1
            speakers_stats[speaker]['duration'] += seg.get('end', 0) - seg.get('start', 0)

        for speaker, stats in sorted(speakers_stats.items()):
            print(f"    {speaker}: {stats['count']} segments, {stats['duration']:.1f} sec")
    else:
        print("  (Detailed transcript unavailable)")

    # Final report
    print("\n" + "="*70)
    print("FINAL REPORT")
    print("="*70)
    print(f"[OK] All stages completed successfully!")
    print(f"\nStatistics:")
    print(f"  Source video: {video_file.name} ({file_size_mb:.2f} MB)")
    print(f"  Audio file: {audio_filename} ({audio_size_mb:.2f} MB)")
    print(f"  Audio duration: {data.get('duration')} sec")
    print(f"  Segment count: {transcript_data.get('num_segments', 0)}")
    print(f"  Speaker count: {transcript_data.get('num_speakers', 0)}")
    print(f"\nProcessing time:")
    print(f"  Audio extraction: {extraction_time:.2f} sec")
    print(f"  Transcription + diarization: {transcription_time:.2f} sec ({transcription_time/60:.1f} min)")
    print(f"  Total time: {extraction_time + transcription_time:.2f} sec ({(extraction_time + transcription_time)/60:.1f} min)")
    print(f"\nResult saved at:")
    print(f"  {result_file.absolute()}")
    print("\n[OK] E2E testing with diarization finished successfully!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Testing interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n[ERROR] Critical failure: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
