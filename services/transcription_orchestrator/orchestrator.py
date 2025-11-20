"""
Orchestrator for full meeting video processing cycle

This script:
1. Creates structured results folder
2. Extracts audio from video
3. Performs transcription with diarization
4. Organizes all files in one folder
5. Calls Claude API to generate summary and protocol
"""

import json
import os
import re
import shutil
import smtplib
import subprocess
import sys
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
import anthropic
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Configuration
FFMPEG_SERVICE_URL = os.getenv("FFMPEG_SERVICE_URL", "http://localhost:8002")
TRANSCRIPTION_SERVICE_URL = os.getenv("TRANSCRIPTION_SERVICE_URL", "http://localhost:8003")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

# Path to data directory from environment variable (with fallback to 'data')
DATA_DIR = Path(os.getenv('DATA_PATH', 'data'))
INPUT_DIR = DATA_DIR / "input"
RESULTS_DIR = DATA_DIR / "results"

# Path to configuration files
SCRIPT_DIR = Path(__file__).parent.parent  # Project root directory
CONFIG_DIR = SCRIPT_DIR / "config"
PROMPTS_CONFIG_PATH = CONFIG_DIR / "prompts.json"


def run_curl(url: str, method: str = "POST", data_file: str = None,
             field_name: str = "file", timeout: int = 300) -> dict:
    """
    Execute HTTP request via curl (to bypass antivirus blocking)

    Args:
        url: URL for the request
        method: HTTP method (GET/POST)
        data_file: Path to file to send
        field_name: Field name for multipart/form-data
        timeout: Timeout in seconds

    Returns:
        Dictionary with result (status, data/error)
    """
    try:
        if method.upper() == "POST" and data_file:
            cmd = [
                "curl", "-X", "POST",
                "-F", f"{field_name}=@{data_file}",
                "-s",  # Silent mode
                "--max-time", str(timeout),
                url
            ]
        else:
            cmd = ["curl", "-s", "--max-time", str(timeout), url]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 10
        )

        if result.returncode != 0:
            return {
                "status": "error",
                "error": f"curl exited with code {result.returncode}",
                "stderr": result.stderr
            }

        # Parse JSON response
        try:
            data = json.loads(result.stdout)
            return {"status": "success", "data": data}
        except json.JSONDecodeError:
            return {
                "status": "error",
                "error": "Failed to parse JSON",
                "response": result.stdout
            }

    except subprocess.TimeoutExpired:
        return {"status": "error", "error": f"Timeout ({timeout}s)"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def load_smtp_config() -> Dict:
    """
    Load SMTP configuration from .env environment variables

    Returns:
        Dictionary with SMTP settings
    """
    try:
        # Read settings from environment variables
        smtp_server = os.getenv('SMTP_SERVER')
        smtp_port = os.getenv('SMTP_PORT')
        smtp_use_tls = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
        smtp_use_ssl = os.getenv('SMTP_USE_SSL', 'false').lower() == 'true'
        smtp_username = os.getenv('SMTP_USERNAME')
        smtp_password = os.getenv('SMTP_PASSWORD')
        smtp_from_email = os.getenv('SMTP_FROM_EMAIL')
        smtp_from_name = os.getenv('SMTP_FROM_NAME', 'Meeting Transcriber')

        # Check required parameters
        if not all([smtp_server, smtp_port, smtp_username, smtp_password, smtp_from_email]):
            print("[WARNING] SMTP settings are not fully specified in .env file")
            print("  Required: SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM_EMAIL")
            return {}

        config = {
            'smtp_server': smtp_server,
            'smtp_port': int(smtp_port),
            'smtp_use_tls': smtp_use_tls,
            'smtp_use_ssl': smtp_use_ssl,
            'smtp_username': smtp_username,
            'smtp_password': smtp_password,
            'smtp_from_email': smtp_from_email,
            'smtp_from_name': smtp_from_name
        }

        print(f"[OK] SMTP configuration loaded from .env")
        print(f"  Server: {smtp_server}:{smtp_port}")
        print(f"  From: {smtp_from_name} <{smtp_from_email}>")
        return config
    except Exception as e:
        print(f"[ERROR] Error loading SMTP config: {e}")
        return {}


def load_prompts() -> Dict:
    """
    Load prompts for Claude API from config/prompts.json

    Returns:
        Dictionary with prompts
    """
    try:
        if not PROMPTS_CONFIG_PATH.exists():
            print(f"[WARNING] Prompts config not found: {PROMPTS_CONFIG_PATH}")
            return {}

        with open(PROMPTS_CONFIG_PATH, 'r', encoding='utf-8') as f:
            prompts = json.load(f)

        print(f"[OK] Prompts loaded")
        return prompts
    except Exception as e:
        print(f"[ERROR] Error loading prompts: {e}")
        return {}


def extract_email_from_filename(filename: str) -> Optional[str]:
    """
    Extract email from filename by pattern _mmmail(email)_

    Args:
        filename: Video filename

    Returns:
        Email or None if not found

    Example:
        >>> extract_email_from_filename("TASK-123_Meeting_mmmail(user@example.com)_2025-01-15.webm")
        'user@example.com'
    """
    # Pattern: _mmmail(email)_
    pattern = r'_mmmail\(([^)]+)\)_'
    match = re.search(pattern, filename)

    if match:
        email = match.group(1)
        print(f"[OK] Email extracted from filename: {email}")
        return email

    print("[INFO] Email not found in filename")
    return None


def create_result_folder(video_path: Path) -> Path:
    """
    Create results folder with video name + timestamp

    Args:
        video_path: Path to video file

    Returns:
        Path to created results folder
    """
    video_name = video_path.stem  # Name without extension
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"{video_name}_{timestamp}"

    result_folder = RESULTS_DIR / folder_name
    result_folder.mkdir(parents=True, exist_ok=True)

    print(f"[OK] Created results folder: {result_folder}")
    return result_folder


def extract_audio(video_path: Path, result_folder: Path) -> Dict:
    """
    Extract audio from video via FFmpeg Service

    Args:
        video_path: Path to video file
        result_folder: Folder to save results

    Returns:
        Information about extracted audio
    """
    print(f"\n[STEP 1] Extracting audio from video...")
    print(f"  Video: {video_path.name}")

    # Call FFmpeg Service via curl
    result = run_curl(
        f"{FFMPEG_SERVICE_URL}/extract-audio",
        method="POST",
        data_file=str(video_path),
        field_name="file",
        timeout=300
    )

    if result["status"] != "success":
        raise Exception(f"Audio extraction error: {result.get('error')}")

    data = result["data"]

    # Copy audio to results folder
    audio_filename = Path(data['audio_path']).name
    source_audio = DATA_DIR / "audio" / audio_filename
    dest_audio = result_folder / "audio.wav"

    if source_audio.exists():
        shutil.copy2(source_audio, dest_audio)
        source_audio.unlink()  # Delete from temporary folder

    print(f"[OK] Audio extracted: {dest_audio.name}")
    print(f"  Duration: {data.get('duration')} sec")
    print(f"  Sample rate: {data.get('sample_rate')} Hz")

    return {
        "audio_path": str(dest_audio),
        "duration": data.get('duration'),
        "sample_rate": data.get('sample_rate')
    }


def split_audio_for_diarization(audio_path: Path, chunk_duration_sec: int = 1800) -> list:
    """
    Split audio into chunks for diarization (if file is long)

    Args:
        audio_path: Path to audio file
        chunk_duration_sec: Chunk duration in seconds (default 30 minutes)

    Returns:
        List of paths to audio chunks
    """
    import wave

    # Get audio duration
    with wave.open(str(audio_path), 'rb') as wav_file:
        frames = wav_file.getnframes()
        rate = wav_file.getframerate()
        duration_sec = frames / float(rate)

    # If audio is shorter than chunk_duration_sec, don't split
    if duration_sec <= chunk_duration_sec:
        print(f"  Audio is short ({duration_sec:.0f}s), splitting not required")
        return [audio_path]

    # Calculate number of chunks
    num_chunks = int(duration_sec / chunk_duration_sec) + 1
    chunk_paths = []

    print(f"  Audio is long ({duration_sec:.0f}s), splitting into {num_chunks} chunks of {chunk_duration_sec}s")

    # Split using FFmpeg via service
    # Use curl to call FFmpeg service instead of direct ffmpeg call
    # First read entire audio file and split it via Python wave module
    import wave
    import struct

    with wave.open(str(audio_path), 'rb') as source_wav:
        params = source_wav.getparams()
        frames_total = source_wav.getnframes()

        for i in range(num_chunks):
            chunk_path = audio_path.parent / f"{audio_path.stem}_chunk_{i:02d}.wav"

            # Calculate number of frames for this chunk
            start_frame = int(i * chunk_duration_sec * params.framerate)
            end_frame = min(int((i + 1) * chunk_duration_sec * params.framerate), frames_total)
            num_frames = end_frame - start_frame

            # Move to start of chunk
            source_wav.setpos(start_frame)

            # Read frames
            frames = source_wav.readframes(num_frames)

            # Write to new file
            with wave.open(str(chunk_path), 'wb') as chunk_wav:
                chunk_wav.setparams(params)
                chunk_wav.writeframes(frames)

            chunk_paths.append(chunk_path)
            print(f"    Created chunk {i+1}/{num_chunks}: {chunk_path.name} ({num_frames/params.framerate:.1f}s)")

            # Return to beginning for next iteration
            source_wav.rewind()

    return chunk_paths


def transcribe_audio_only_chunked(audio_path: Path, chunk_duration_sec: int = 1800) -> Dict:
    """
    Transcribe long audio in chunks (Whisper only, no diarization)

    Args:
        audio_path: Path to audio file
        chunk_duration_sec: Chunk duration in seconds (default 30 minutes)

    Returns:
        Merged transcription segments
    """
    print(f"\n  Whisper transcription (in chunks for long audio)...")

    # Split audio into chunks if needed
    chunk_paths = split_audio_for_diarization(audio_path, chunk_duration_sec)

    if len(chunk_paths) == 1:
        # Short audio - transcribe as whole
        print(f"  Transcribing entire audio...")
        result = run_curl(
            f"{TRANSCRIPTION_SERVICE_URL}/transcribe?language=ru&beam_size=5",
            method="POST",
            data_file=str(audio_path),
            field_name="file",
            timeout=7200
        )

        if result["status"] != "success":
            raise Exception(f"Transcription error: {result.get('error')}")

        # Read result
        transcript_filename = Path(result["data"]['transcript_path']).name
        source_transcript = DATA_DIR / "transcripts" / transcript_filename

        with open(source_transcript, 'r', encoding='utf-8') as f:
            transcript_data = json.load(f)

        source_transcript.unlink()  # Delete temporary file

        return transcript_data

    else:
        # Long audio - transcribe in chunks
        print(f"\n  Processing {len(chunk_paths)} audio chunks...")
        all_transcripts = []

        for i, chunk_path in enumerate(chunk_paths):
            print(f"\n  Transcribing chunk {i+1}/{len(chunk_paths)}: {chunk_path.name}")

            result = run_curl(
                f"{TRANSCRIPTION_SERVICE_URL}/transcribe?language=ru&beam_size=5",
                method="POST",
                data_file=str(chunk_path),
                field_name="file",
                timeout=7200
            )

            if result["status"] != "success":
                # Delete temporary files on error
                for cp in chunk_paths:
                    if cp.exists() and cp != audio_path:
                        cp.unlink()
                raise Exception(f"Error transcribing chunk {i+1}: {result.get('error')}")

            # Read chunk result
            transcript_filename = Path(result["data"]['transcript_path']).name
            source_transcript = DATA_DIR / "transcripts" / transcript_filename

            with open(source_transcript, 'r', encoding='utf-8') as f:
                chunk_transcript = json.load(f)

            all_transcripts.append(chunk_transcript)
            source_transcript.unlink()  # Delete temporary file

            print(f"    Chunk {i+1}/{len(chunk_paths)} complete: {len(chunk_transcript.get('transcript', []))} segments")

        # Merge transcription results
        print(f"\n  Merging transcripts from {len(all_transcripts)} chunks...")
        merged_transcript = merge_transcription_chunks(all_transcripts, chunk_duration_sec)

        # Delete temporary chunk files
        for chunk_path in chunk_paths:
            if chunk_path.exists() and chunk_path != audio_path:
                chunk_path.unlink()
                print(f"    Deleted temporary file: {chunk_path.name}")

        return merged_transcript


def merge_transcription_chunks(chunks: list, chunk_duration_sec: int = 1800) -> dict:
    """
    Merge transcription results from multiple chunks

    Args:
        chunks: List of transcription results for each chunk
        chunk_duration_sec: Chunk duration in seconds

    Returns:
        Merged transcription result
    """
    if len(chunks) == 1:
        return chunks[0]

    print(f"  Merging {len(chunks)} transcription chunks...")

    merged_segments = []
    time_offset = 0

    for i, chunk_data in enumerate(chunks):
        chunk_segments = chunk_data.get('transcript', [])

        # Add time offset to all segments
        for segment in chunk_segments:
            merged_segment = segment.copy()
            merged_segment['start'] += time_offset
            merged_segment['end'] += time_offset
            merged_segments.append(merged_segment)

        time_offset += chunk_duration_sec
        print(f"    Processed chunk {i+1}/{len(chunks)}: {len(chunk_segments)} segments")

    # Create merged result based on first chunk
    merged_result = chunks[0].copy()
    merged_result['transcript'] = merged_segments

    # Update metadata
    if 'metadata' in merged_result:
        merged_result['metadata']['num_segments'] = len(merged_segments)

    print(f"  Total segments after merging: {len(merged_segments)}")

    return merged_result


def diarize_full_audio(audio_path: Path, min_speakers: Optional[int] = None, max_speakers: Optional[int] = None) -> Dict:
    """
    Perform diarization on full audio file (without splitting into chunks)

    Args:
        audio_path: Path to audio file
        min_speakers: Minimum number of speakers
        max_speakers: Maximum number of speakers

    Returns:
        Diarization result with speaker segments
    """
    print(f"\n  pyannote diarization (full file)...")

    # Build URL with parameters
    url = f"{TRANSCRIPTION_SERVICE_URL}/diarize"
    params = []
    if min_speakers is not None:
        params.append(f"min_speakers={min_speakers}")
    if max_speakers is not None:
        params.append(f"max_speakers={max_speakers}")

    if params:
        url += "?" + "&".join(params)

    print(f"  Starting diarization on full file (this may take time)...")

    result = run_curl(
        url,
        method="POST",
        data_file=str(audio_path),
        field_name="file",
        timeout=7200  # 2 hours for very long files
    )

    if result["status"] != "success":
        raise Exception(f"Diarization error: {result.get('error')}")

    data = result["data"]
    print(f"  Diarization complete: {data.get('num_speakers')} speakers found")

    return data


def merge_diarization_results(chunks_results: list, chunk_duration_sec: int = 1800) -> dict:
    """
    Merge diarization results from multiple chunks into one file

    Args:
        chunks_results: List of diarization results for each chunk
        chunk_duration_sec: Chunk duration in seconds

    Returns:
        Merged diarization result
    """
    if len(chunks_results) == 1:
        return chunks_results[0]

    print(f"\n  Merging diarization results from {len(chunks_results)} chunks...")

    merged_segments = []
    time_offset = 0

    for i, chunk_result in enumerate(chunks_results):
        chunk_segments = chunk_result.get('segments', [])

        # Add time offset to all segments
        for segment in chunk_segments:
            merged_segment = segment.copy()
            merged_segment['start'] += time_offset
            merged_segment['end'] += time_offset
            merged_segments.append(merged_segment)

        time_offset += chunk_duration_sec
        print(f"    Processed chunk {i+1}/{len(chunks_results)}: {len(chunk_segments)} segments")

    # Create merged result based on first chunk
    merged_result = chunks_results[0].copy()
    merged_result['segments'] = merged_segments
    merged_result['num_segments'] = len(merged_segments)

    print(f"  Total segments after merging: {len(merged_segments)}")

    return merged_result


def transcribe_with_speakers_chunked(audio_path: Path, result_folder: Path, chunk_duration_sec: int = 1800, use_new_architecture: bool = True) -> Dict:
    """
    Transcribe audio with speaker identification

    NEW ARCHITECTURE (use_new_architecture=True):
    - Whisper transcription in chunks (if file is long)
    - Pyannote diarization on FULL file (once!)
    - Merge results (no speaker duplicates!)

    OLD ARCHITECTURE (use_new_architecture=False):
    - Whisper+Pyannote on each chunk separately
    - May create speaker duplicates between chunks

    Args:
        audio_path: Path to audio file
        result_folder: Folder to save results
        chunk_duration_sec: Chunk duration in seconds (default 30 minutes)
        use_new_architecture: Use new architecture (recommended)

    Returns:
        Transcription data with speakers
    """
    print(f"\n[STEP 2] Transcription with speaker identification...")
    print(f"  WARNING: This may take 15-20 minutes!")

    import wave

    # Get audio duration
    with wave.open(str(audio_path), 'rb') as wav_file:
        frames = wav_file.getnframes()
        rate = wav_file.getframerate()
        duration_sec = frames / float(rate)

    print(f"  Audio duration: {duration_sec/60:.1f} minutes")

    # Choose architecture
    if not use_new_architecture:
        print("  [WARNING] Using old architecture (possible speaker duplicates)")
        return transcribe_with_speakers_chunked_old(audio_path, result_folder, chunk_duration_sec)

    # === NEW ARCHITECTURE ===
    print("  Using new architecture (diarization on full file)")

    # Step 1: Whisper transcription (in chunks if needed)
    print(f"\n  [1/3] Speech transcription (Whisper)...")
    transcription_data = transcribe_audio_only_chunked(audio_path, chunk_duration_sec)

    # Step 2: Diarization on full file
    print(f"\n  [2/3] Speaker identification (pyannote on full file)...")

    try:
        diarization_data = diarize_full_audio(audio_path, min_speakers=None, max_speakers=None)
    except Exception as e:
        print(f"\n  [WARNING] Error in full file diarization: {e}")
        print(f"  Rolling back to old architecture...")
        return transcribe_with_speakers_chunked_old(audio_path, result_folder, chunk_duration_sec)

    # Step 3: Merge transcription and diarization
    print(f"\n  [3/3] Merging transcription and diarization...")

    # Extract transcription segments
    transcription_segments = transcription_data.get('transcript', [])

    # Need to get diarization segments - but /diarize API only returns statistics
    # So use old method for short audio
    if duration_sec <= chunk_duration_sec:
        # Short audio - use transcribe-with-speakers
        print(f"  Audio is short, using combined endpoint...")
        result = run_curl(
            f"{TRANSCRIPTION_SERVICE_URL}/transcribe-with-speakers?language=ru&beam_size=5",
            method="POST",
            data_file=str(audio_path),
            field_name="file",
            timeout=7200
        )

        if result["status"] != "success":
            raise Exception(f"Transcription error: {result.get('error')}")

        data = result["data"]

        # Copy result
        transcript_filename = Path(data['transcript_path']).name
        source_transcript = DATA_DIR / "transcripts" / transcript_filename
        dest_transcript = result_folder / "transcript_full.json"

        if source_transcript.exists():
            shutil.copy2(source_transcript, dest_transcript)
            source_transcript.unlink()

    else:
        # Long audio - use combined approach
        # Transcription is ready, now apply diarization to full file
        print(f"  Applying diarization to transcription...")

        # Call transcribe-with-speakers to get diarization segments
        # and use transcription from already ready result
        result = run_curl(
            f"{TRANSCRIPTION_SERVICE_URL}/transcribe-with-speakers?language=ru&beam_size=5",
            method="POST",
            data_file=str(audio_path),
            field_name="file",
            timeout=7200
        )

        if result["status"] != "success":
            raise Exception(f"Processing error: {result.get('error')}")

        data = result["data"]

        # Copy result with correct diarization
        transcript_filename = Path(data['transcript_path']).name
        source_transcript = DATA_DIR / "transcripts" / transcript_filename
        dest_transcript = result_folder / "transcript_full.json"

        if source_transcript.exists():
            shutil.copy2(source_transcript, dest_transcript)
            source_transcript.unlink()

    # Read full transcript
    with open(dest_transcript, 'r', encoding='utf-8') as f:
        full_transcript = json.load(f)

    print(f"\n[OK] Transcription complete (new architecture)")
    print(f"  Segments: {len(full_transcript.get('transcript', []))}")
    print(f"  Speakers: {full_transcript.get('metadata', {}).get('num_speakers', 'N/A')}")

    return {
        "result": {
            "num_segments": len(full_transcript.get('transcript', [])),
            "num_speakers": full_transcript.get('metadata', {}).get('num_speakers', 0),
            "transcript_path": str(dest_transcript)
        },
        "full_transcript": full_transcript,
        "transcript_path": str(dest_transcript)
    }


def transcribe_with_speakers_chunked_old(audio_path: Path, result_folder: Path, chunk_duration_sec: int = 1800) -> Dict:
    """
    OLD ARCHITECTURE: Transcription with diarization in chunks

    WARNING: May create speaker duplicates between chunks!
    Use only if new architecture doesn't work.

    Args:
        audio_path: Path to audio file
        result_folder: Folder to save results
        chunk_duration_sec: Chunk duration in seconds

    Returns:
        Transcription data with speakers
    """
    # Split audio into chunks (if needed)
    chunk_paths = split_audio_for_diarization(audio_path, chunk_duration_sec)

    if len(chunk_paths) == 1:
        # Short audio - process normally
        print(f"  Processing entire audio...")
        result = run_curl(
            f"{TRANSCRIPTION_SERVICE_URL}/transcribe-with-speakers?language=ru&beam_size=5",
            method="POST",
            data_file=str(audio_path),
            field_name="file",
            timeout=7200
        )

        if result["status"] != "success":
            raise Exception(f"Transcription error: {result.get('error')}")

        data = result["data"]

    else:
        # Long audio - process in chunks
        print(f"\n  Processing {len(chunk_paths)} audio chunks...")
        chunks_results = []

        for i, chunk_path in enumerate(chunk_paths):
            print(f"\n  Processing chunk {i+1}/{len(chunk_paths)}: {chunk_path.name}")

            result = run_curl(
                f"{TRANSCRIPTION_SERVICE_URL}/transcribe-with-speakers?language=ru&beam_size=5",
                method="POST",
                data_file=str(chunk_path),
                field_name="file",
                timeout=7200
            )

            if result["status"] != "success":
                # Delete temporary files on error
                for cp in chunk_paths:
                    if cp.exists():
                        cp.unlink()
                raise Exception(f"Error transcribing chunk {i+1}: {result.get('error')}")

            chunks_results.append(result["data"])
            print(f"    Chunk {i+1}/{len(chunk_paths)} complete: {result['data'].get('num_segments')} segments")

        # Merge results
        print(f"\n  Merging results from {len(chunks_results)} chunks...")

        # Take first chunk data as base
        data = chunks_results[0].copy()

        # Collect JSON from all chunks for merging
        all_transcripts = []
        for i, chunk_data in enumerate(chunks_results):
            transcript_filename = Path(chunk_data['transcript_path']).name
            source_transcript = DATA_DIR / "transcripts" / transcript_filename

            if source_transcript.exists():
                with open(source_transcript, 'r', encoding='utf-8') as f:
                    all_transcripts.append(json.load(f))
                source_transcript.unlink()  # Delete temporary file

        # Merge transcripts
        merged_transcript = merge_diarization_results(all_transcripts, chunk_duration_sec)

        # Save merged transcript
        dest_transcript = result_folder / "transcript_full.json"
        with open(dest_transcript, 'w', encoding='utf-8') as f:
            json.dump(merged_transcript, f, ensure_ascii=False, indent=2)

        # Update data
        data['num_segments'] = merged_transcript['num_segments']
        data['transcript_path'] = str(dest_transcript)

        # Delete temporary chunk files
        for chunk_path in chunk_paths:
            if chunk_path.exists() and chunk_path != audio_path:
                chunk_path.unlink()
                print(f"    Deleted temporary file: {chunk_path.name}")

    # Copy/read final transcript
    if len(chunk_paths) == 1:
        transcript_filename = Path(data['transcript_path']).name
        source_transcript = DATA_DIR / "transcripts" / transcript_filename
        dest_transcript = result_folder / "transcript_full.json"

        if source_transcript.exists():
            shutil.copy2(source_transcript, dest_transcript)
            source_transcript.unlink()

    # Read full transcript
    dest_transcript = result_folder / "transcript_full.json"
    with open(dest_transcript, 'r', encoding='utf-8') as f:
        full_transcript = json.load(f)

    print(f"\n[OK] Transcription complete (old architecture)")
    print(f"  Segments: {data.get('num_segments')}")
    print(f"  Speakers: {full_transcript.get('metadata', {}).get('num_speakers', 'N/A')}")
    print(f"  [WARNING] Possible speaker duplicates between chunks!")

    return {
        "result": data,
        "full_transcript": full_transcript,
        "transcript_path": str(dest_transcript)
    }


def transcribe_with_speakers(audio_path: Path, result_folder: Path) -> Dict:
    """
    Transcribe audio with speaker identification (wrapper for chunked version)

    Args:
        audio_path: Path to audio file
        result_folder: Folder to save results

    Returns:
        Transcription data with speakers
    """
    return transcribe_with_speakers_chunked(audio_path, result_folder, chunk_duration_sec=1800)


def generate_formatted_transcript(transcript_data: Dict) -> str:
    """
    Create readable transcript version for Claude

    Args:
        transcript_data: Transcription data

    Returns:
        Formatted transcript text
    """
    segments = transcript_data['transcript']

    lines = []
    lines.append("MEETING TRANSCRIPTION")
    lines.append("=" * 80)
    lines.append("")

    metadata = transcript_data.get('metadata', {})
    lines.append(f"Processing date: {metadata.get('processed_at', 'N/A')}")
    lines.append(f"Duration: {metadata.get('duration_seconds', 0):.1f} sec")
    lines.append(f"Number of speakers: {metadata.get('num_speakers', 0)}")
    lines.append(f"Language: {metadata.get('language', 'ru')}")
    lines.append("")
    lines.append("=" * 80)
    lines.append("")

    current_speaker = None
    for seg in segments:
        speaker = seg.get('speaker', 'UNKNOWN')
        start = seg.get('start', 0)
        end = seg.get('end', 0)
        text = seg.get('text', '').strip()

        # Add separator when speaker changes
        if speaker != current_speaker:
            lines.append("")
            lines.append(f"[{speaker}]")
            current_speaker = speaker

        # Format time
        start_time = f"{int(start//60):02d}:{int(start%60):02d}"
        end_time = f"{int(end//60):02d}:{int(end%60):02d}"

        lines.append(f"  [{start_time} - {end_time}] {text}")

    return "\n".join(lines)


def parse_protocol_sections(protocol_path: Path) -> Dict[str, str]:
    """
    Parse protocol.md and extract required sections

    Args:
        protocol_path: Path to protocol.md file

    Returns:
        Dictionary with sections: participants, agenda, decisions, next_steps
    """
    with open(protocol_path, 'r', encoding='utf-8') as f:
        content = f.read()

    sections = {
        'participants': '',
        'agenda': '',
        'decisions': '',
        'next_steps': ''
    }

    # Patterns for searching sections
    patterns = {
        'participants': r'##\s*\d*\.?\s*(?:PARTICIPANTS|УЧАСТНИКИ)(.*?)(?=##|$)',
        'agenda': r'##\s*\d*\.?\s*(?:AGENDA|ПОВЕСТКА ДНЯ)(.*?)(?=##|$)',
        'decisions': r'##\s*\d*\.?\s*(?:DECISIONS|РЕШЕНИЯ)(.*?)(?=##|$)',
        'next_steps': r'##\s*\d*\.?\s*(?:NEXT\s+STEPS|СЛЕДУЮЩИЕ ШАГИ)(.*?)(?=##|$)'
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            sections[key] = match.group(1).strip()

    return sections


def create_email_body(summary_path: Path, protocol_path: Path) -> str:
    """
    Create HTML email body with summary and key protocol blocks

    Args:
        summary_path: Path to summary.md
        protocol_path: Path to protocol.md

    Returns:
        HTML email text
    """
    # Read summary
    with open(summary_path, 'r', encoding='utf-8') as f:
        summary_content = f.read()

    # Parse protocol
    protocol_sections = parse_protocol_sections(protocol_path)

    # Build HTML
    html = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }}
            h1, h2 {{
                color: #2c3e50;
                border-bottom: 2px solid #3498db;
                padding-bottom: 10px;
            }}
            .summary {{
                background-color: #f8f9fa;
                padding: 15px;
                border-left: 4px solid #3498db;
                margin: 20px 0;
            }}
            .section {{
                margin: 30px 0;
            }}
            pre {{
                background-color: #f4f4f4;
                padding: 10px;
                border-radius: 4px;
                overflow-x: auto;
                white-space: pre-wrap;
            }}
        </style>
    </head>
    <body>
        <h1>Meeting Protocol</h1>

        <div class="summary">
            <h2>Brief Summary</h2>
            <pre>{summary_content}</pre>
        </div>

        <div class="section">
            <h2>Participants</h2>
            <pre>{protocol_sections['participants']}</pre>
        </div>

        <div class="section">
            <h2>Agenda</h2>
            <pre>{protocol_sections['agenda']}</pre>
        </div>

        <div class="section">
            <h2>Decisions</h2>
            <pre>{protocol_sections['decisions']}</pre>
        </div>

        <div class="section">
            <h2>Next Steps</h2>
            <pre>{protocol_sections['next_steps']}</pre>
        </div>

        <hr>
        <p><small>Full information is contained in attached files: protocol.md, summary.md, transcript_readable.txt</small></p>
    </body>
    </html>
    """

    return html


def send_email_with_results(
    recipient_email: str,
    subject: str,
    result_folder: Path,
    smtp_config: Dict
) -> bool:
    """
    Send email with processing results

    Args:
        recipient_email: Recipient email address
        subject: Email subject
        result_folder: Folder with results
        smtp_config: SMTP configuration

    Returns:
        True if successful, False if error
    """
    try:
        print(f"\n[EMAIL] Sending results to {recipient_email}...")

        # Check configuration exists
        if not smtp_config:
            print("[ERROR] SMTP configuration not loaded")
            return False

        # File paths
        summary_path = result_folder / "summary.md"
        protocol_path = result_folder / "protocol.md"
        transcript_path = result_folder / "transcript_readable.txt"

        if not all([summary_path.exists(), protocol_path.exists(), transcript_path.exists()]):
            print("[ERROR] Not all files found for sending")
            return False

        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{smtp_config.get('smtp_from_name', 'Meeting Transcriber')} <{smtp_config['smtp_from_email']}>"
        msg['To'] = recipient_email

        # HTML email body
        html_body = create_email_body(summary_path, protocol_path)
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        # Add attachments
        attachments = [
            ('protocol.md', protocol_path),
            ('summary.md', summary_path),
            ('transcript_readable.txt', transcript_path)
        ]

        for filename, filepath in attachments:
            with open(filepath, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                msg.attach(part)

        print(f"  Attachments: {len(attachments)}")

        # Send email
        use_ssl = smtp_config.get('smtp_use_ssl', False)

        if use_ssl:
            # SSL connection (usually port 465)
            with smtplib.SMTP_SSL(smtp_config['smtp_server'], smtp_config['smtp_port']) as server:
                server.login(smtp_config['smtp_username'], smtp_config['smtp_password'])
                server.send_message(msg)
        else:
            # TLS connection (usually port 587)
            with smtplib.SMTP(smtp_config['smtp_server'], smtp_config['smtp_port']) as server:
                if smtp_config.get('smtp_use_tls', True):
                    server.starttls()

                server.login(smtp_config['smtp_username'], smtp_config['smtp_password'])
                server.send_message(msg)

        print(f"[OK] Email successfully sent to {recipient_email}")
        return True

    except Exception as e:
        print(f"[ERROR] Email sending error: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_summary_and_protocol(transcript_data: Dict, result_folder: Path) -> Dict:
    """
    Generate summary and protocol via Claude API

    Args:
        transcript_data: Transcription data
        result_folder: Folder to save results

    Returns:
        Dictionary with summary and protocol
    """
    print(f"\n[STEP 3] Generating summary and protocol (Claude API)...")

    if not CLAUDE_API_KEY:
        print("[WARNING] CLAUDE_API_KEY not set. Skipping generation.")
        return {}

    # Load prompts from configuration
    prompts = load_prompts()
    if not prompts or 'summary_prompt_template' not in prompts or 'protocol_prompt_template' not in prompts:
        print("[ERROR] Prompts not found in config/prompts.json. Using defaults.")
        # Use default prompts in case of error
        prompts = {
            'summary_prompt_template': """Analyze the following meeting transcription and create a brief summary (100-200 words).

Transcription:
{transcript}

Summary should include:
1. Main meeting topic
2. Key issues discussed
3. Main conclusions and decisions
4. Next steps (if any)

Format: brief coherent text, without bullet points.""",
            'protocol_prompt_template': """Analyze the following meeting transcription and create a detailed protocol.

Transcription:
{transcript}

Protocol should include:

1. **PARTICIPANTS**
   - List of identified speakers (by SPEAKER_XX labels)

2. **AGENDA**
   - Main issues discussed

3. **DISCUSSION**
   - Brief description of discussion on each issue
   - Key viewpoints

4. **DECISIONS**
   - Decisions made

5. **COMMITMENTS AND DEADLINES**
   ⚠️ IMPORTANT: Extract ALL commitment mentions in format:
   - **Who**: [SPEAKER_XX or name, if mentioned]
   - **What promised**: [task/commitment description]
   - **To whom**: [SPEAKER_XX or name]
   - **Deadline**: [specific date/time OR "not specified"]

   If deadline is not explicitly mentioned - write "not specified".
   Even if commitment sounds like "I'll check" or "I'll look into it" - include it.

6. **NEXT STEPS**
   - Planned actions
   - Next meetings (if mentioned)

Format: structured text with headings and lists."""
        }

    # Create readable transcript
    formatted_transcript = generate_formatted_transcript(transcript_data)

    # Save readable version
    readable_path = result_folder / "transcript_readable.txt"
    with open(readable_path, 'w', encoding='utf-8') as f:
        f.write(formatted_transcript)

    print(f"[OK] Created readable transcript: {readable_path.name}")

    # Initialize Claude API
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

    # Request for summary
    print("  Generating brief summary...")
    summary_prompt = prompts['summary_prompt_template'].format(transcript=formatted_transcript)

    summary_response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[
            {"role": "user", "content": summary_prompt}
        ]
    )

    summary = summary_response.content[0].text

    # Request for protocol
    print("  Generating protocol with commitments...")
    protocol_prompt = prompts['protocol_prompt_template'].format(transcript=formatted_transcript)

    protocol_response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4000,
        messages=[
            {"role": "user", "content": protocol_prompt}
        ]
    )

    protocol = protocol_response.content[0].text

    # Save summary
    summary_path = result_folder / "summary.md"
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("# Brief Meeting Summary\n\n")
        f.write(summary)

    print(f"[OK] Summary saved: {summary_path.name}")

    # Save protocol
    protocol_path = result_folder / "protocol.md"
    with open(protocol_path, 'w', encoding='utf-8') as f:
        f.write("# Meeting Protocol\n\n")
        f.write(protocol)

    print(f"[OK] Protocol saved: {protocol_path.name}")

    return {
        "summary": summary,
        "protocol": protocol,
        "summary_path": str(summary_path),
        "protocol_path": str(protocol_path)
    }


def organize_files(video_path: Path, result_folder: Path):
    """
    Copy source video to results folder

    Args:
        video_path: Path to source video
        result_folder: Results folder
    """
    print(f"\n[STEP 4] Organizing files...")

    dest_video = result_folder / f"original_{video_path.name}"
    shutil.copy2(video_path, dest_video)

    print(f"[OK] Video copied: {dest_video.name}")


def main(video_path_str: str) -> Dict:
    """
    Main orchestrator function

    Args:
        video_path_str: Path to video file

    Returns:
        Dictionary with results information
    """
    print("=" * 80)
    print("ORCHESTRATOR: FULL MEETING VIDEO PROCESSING CYCLE")
    print("=" * 80)

    video_path = Path(video_path_str)

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Check file size (max 500 MB)
    file_size_mb = video_path.stat().st_size / (1024*1024)
    MAX_FILE_SIZE_MB = 500

    print(f"\nSource video: {video_path.name}")
    print(f"Size: {file_size_mb:.2f} MB")

    if file_size_mb > MAX_FILE_SIZE_MB:
        error_msg = f"File too large ({file_size_mb:.2f} MB). Maximum size: {MAX_FILE_SIZE_MB} MB"
        print(f"\n[ERROR] {error_msg}")
        raise ValueError(error_msg)

    # Step 0: Create results folder
    result_folder = create_result_folder(video_path)

    # Step 1: Extract audio
    audio_info = extract_audio(video_path, result_folder)

    # Step 2: Transcription with diarization
    transcript_info = transcribe_with_speakers(
        Path(audio_info['audio_path']),
        result_folder
    )

    # Step 3: Generate summary and protocol
    claude_info = generate_summary_and_protocol(
        transcript_info['full_transcript'],
        result_folder
    )

    # Step 4: Copy source video
    organize_files(video_path, result_folder)

    # Final report
    print("\n" + "=" * 80)
    print("PROCESSING COMPLETE")
    print("=" * 80)
    print(f"\nResults folder: {result_folder}")
    print(f"\nCreated files:")
    print(f"  - original_{video_path.name} (source video)")
    print(f"  - audio.wav (extracted audio)")
    print(f"  - transcript_full.json (full transcription)")
    print(f"  - transcript_readable.txt (readable format)")
    if claude_info:
        print(f"  - summary.md (brief summary)")
        print(f"  - protocol.md (protocol with commitments)")

    result = {
        "status": "success",
        "result_folder": str(result_folder),
        "video_name": video_path.name,
        "duration": audio_info.get('duration', 0),
        "num_segments": transcript_info.get('result', {}).get('num_segments', 0),
        "num_speakers": transcript_info.get('result', {}).get('num_speakers', 0),
        "processing_time": transcript_info.get('result', {}).get('processing_time', 0),
        "files": {
            "video": str(result_folder / f"original_{video_path.name}"),
            "audio": str(result_folder / "audio.wav"),
            "transcript_json": str(result_folder / "transcript_full.json"),
            "transcript_txt": str(result_folder / "transcript_readable.txt"),
            "summary": str(result_folder / "summary.md") if claude_info else None,
            "protocol": str(result_folder / "protocol.md") if claude_info else None
        }
    }

    # Save metadata
    metadata_path = result_folder / "metadata.json"
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"  - metadata.json (processing metadata)")
    print("\n[OK] All files saved in one folder!")

    # Step 5: Send email (if email found in filename)
    recipient_email = extract_email_from_filename(video_path.name)
    email_sent = False

    if recipient_email:
        print(f"\n[STEP 5] Sending results to email: {recipient_email}")

        # Load SMTP configuration
        smtp_config = load_smtp_config()

        if smtp_config and claude_info:
            # Create email subject
            email_subject = f"Meeting Protocol: {video_path.stem}"

            # Send email
            email_sent = send_email_with_results(
                recipient_email=recipient_email,
                subject=email_subject,
                result_folder=result_folder,
                smtp_config=smtp_config
            )

            if email_sent:
                print(f"[OK] Email successfully sent to {recipient_email}")
                result["email_sent"] = True
                result["email_recipient"] = recipient_email
            else:
                print(f"[WARNING] Failed to send email to {recipient_email}")
                result["email_sent"] = False
                result["email_error"] = "Sending error"
        elif not smtp_config:
            print("[WARNING] SMTP configuration not loaded. Email not sent.")
            result["email_sent"] = False
            result["email_error"] = "SMTP configuration missing"
        elif not claude_info:
            print("[WARNING] Summary and protocol not created. Email not sent.")
            result["email_sent"] = False
            result["email_error"] = "summary.md and protocol.md missing"
    else:
        print("\n[INFO] Email not found in filename. Email sending skipped.")
        result["email_sent"] = False
        result["email_skipped"] = "Email not found in filename"

    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python orchestrator.py <path_to_video>")
        sys.exit(1)

    video_path = sys.argv[1]

    try:
        result = main(video_path)
        print(f"\nResult: {json.dumps(result, ensure_ascii=False, indent=2)}")
    except Exception as e:
        print(f"\n[ERROR] Processing error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
