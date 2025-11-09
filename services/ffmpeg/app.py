"""
FFmpeg Service - Audio extraction from video files

This microservice accepts video files (.avi) and extracts audio
in WAV format (16kHz, mono, PCM) for subsequent transcription.

Endpoints:
    POST /extract-audio - Extract audio from video file
    GET /health - Health check for monitoring
"""

import asyncio
import logging
import os
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI initialization
app = FastAPI(
    title="FFmpeg Audio Extraction Service",
    description="Service for extracting audio from video files",
    version="1.0.0"
)

# Path configuration
DATA_DIR = Path("/app/data")
INPUT_DIR = DATA_DIR / "input"
AUDIO_DIR = DATA_DIR / "audio"

# Create directories if they don't exist
INPUT_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    service: str
    timestamp: str
    ffmpeg_version: Optional[str] = None


class AudioExtractionResponse(BaseModel):
    """Audio extraction response model"""
    status: str
    audio_path: str
    duration: Optional[float] = None
    sample_rate: int
    channels: int
    format: str
    original_filename: str
    processing_time: float


class ErrorResponse(BaseModel):
    """Error response model"""
    status: str
    error: str
    details: Optional[str] = None


def get_ffmpeg_version() -> Optional[str]:
    """
    Get FFmpeg version

    Returns:
        String with FFmpeg version or None if unable to determine
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        # Extract first line with version
        version_line = result.stdout.split('\n')[0]
        return version_line
    except Exception as e:
        logger.warning(f"Failed to get FFmpeg version: {e}")
        return None


async def get_audio_duration(audio_path: Path) -> Optional[float]:
    """
    Get audio file duration using ffprobe

    Args:
        audio_path: Path to audio file

    Returns:
        Duration in seconds or None if unable to determine
    """
    try:
        process = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            duration = float(stdout.decode().strip())
            return round(duration, 2)
        else:
            logger.warning(f"ffprobe failed to determine duration: {stderr.decode()}")
            return None
    except Exception as e:
        logger.warning(f"Error determining duration: {e}")
        return None


async def extract_audio_from_video(
    input_path: Path,
    output_path: Path,
    sample_rate: int = 16000,
    channels: int = 1
) -> bool:
    """
    Extract audio from video file using FFmpeg

    Args:
        input_path: Path to input video file
        output_path: Path to save audio file
        sample_rate: Sample rate (default 16kHz for Whisper)
        channels: Number of channels (1 = mono, 2 = stereo)

    Returns:
        True if successful, False on error

    Raises:
        RuntimeError: On FFmpeg execution error
    """
    logger.info(f"Starting audio extraction: {input_path.name} -> {output_path.name}")

    # FFmpeg command for audio extraction
    # -i: input file
    # -vn: no video
    # -acodec pcm_s16le: PCM 16-bit little-endian (uncompressed WAV)
    # -ar: sample rate
    # -ac: number of channels
    # -y: overwrite output file if exists
    cmd = [
        "ffmpeg",
        "-i", str(input_path),
        "-vn",  # No video
        "-acodec", "pcm_s16le",  # PCM 16-bit
        "-ar", str(sample_rate),  # Sample rate
        "-ac", str(channels),  # Channels (mono)
        "-y",  # Overwrite
        str(output_path)
    ]

    try:
        # Launch FFmpeg asynchronously
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode()
            logger.error(f"FFmpeg error: {error_msg}")
            raise RuntimeError(f"FFmpeg failed with error: {error_msg}")

        logger.info(f"Audio successfully extracted: {output_path.name}")
        return True

    except Exception as e:
        logger.error(f"Error extracting audio: {e}")
        raise RuntimeError(f"Failed to extract audio: {str(e)}")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint to verify service operability

    Returns:
        Service status and FFmpeg version information
    """
    ffmpeg_version = get_ffmpeg_version()

    return HealthResponse(
        status="healthy",
        service="ffmpeg-audio-extraction",
        timestamp=datetime.utcnow().isoformat(),
        ffmpeg_version=ffmpeg_version
    )


@app.post("/extract-audio", response_model=AudioExtractionResponse)
async def extract_audio(
    file: UploadFile = File(..., description="Video file (.avi, .mp4, .mov, etc.)")
):
    """
    Extract audio from video file

    Accepts video file and extracts audio in WAV format:
    - Sample rate: 16kHz (optimal for Whisper)
    - Channels: 1 (mono)
    - Format: PCM 16-bit little-endian

    Args:
        file: Uploaded video file

    Returns:
        Information about extracted audio file

    Raises:
        HTTPException: On validation or processing errors
    """
    start_time = datetime.utcnow()

    # File validation
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename not specified")

    # Extension check (optional, FFmpeg can handle many formats)
    allowed_extensions = {'.avi', '.mp4', '.mov', '.mkv', '.flv', '.wmv', '.webm'}
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        logger.warning(f"Unusual file extension: {file_ext}, attempting to process...")

    # Generate unique filenames
    file_id = str(uuid.uuid4())
    input_filename = f"{file_id}_{file.filename}"
    output_filename = f"{file_id}.wav"

    input_path = INPUT_DIR / input_filename
    output_path = AUDIO_DIR / output_filename

    try:
        # Save uploaded file
        logger.info(f"Saving file: {file.filename} ({file.size} bytes)")
        async with aiofiles.open(input_path, 'wb') as f:
            content = await file.read()
            await f.write(content)

        # Extract audio
        await extract_audio_from_video(
            input_path=input_path,
            output_path=output_path,
            sample_rate=16000,
            channels=1
        )

        # Get audio duration
        duration = await get_audio_duration(output_path)

        # Delete original video file (save space)
        try:
            input_path.unlink()
            logger.info(f"Original file deleted: {input_filename}")
        except Exception as e:
            logger.warning(f"Failed to delete original file: {e}")

        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()

        # Form response
        response = AudioExtractionResponse(
            status="success",
            audio_path=f"/app/data/audio/{output_filename}",
            duration=duration,
            sample_rate=16000,
            channels=1,
            format="wav",
            original_filename=file.filename,
            processing_time=round(processing_time, 2)
        )

        logger.info(
            f"Processing completed: {file.filename} -> {output_filename} "
            f"({processing_time:.2f}s)"
        )

        return response

    except RuntimeError as e:
        # FFmpeg errors
        logger.error(f"Processing error: {e}")

        # Cleanup files on error
        if input_path.exists():
            input_path.unlink()
        if output_path.exists():
            output_path.unlink()

        raise HTTPException(
            status_code=500,
            detail=f"Audio extraction error: {str(e)}"
        )

    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error: {e}", exc_info=True)

        # Cleanup files on error
        if input_path.exists():
            input_path.unlink()
        if output_path.exists():
            output_path.unlink()

        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/")
async def root():
    """
    Root endpoint with service information
    """
    return {
        "service": "FFmpeg Audio Extraction Service",
        "version": "1.0.0",
        "description": "Audio extraction from video files for transcription",
        "endpoints": {
            "POST /extract-audio": "Extract audio from video file",
            "GET /health": "Service health check",
            "GET /docs": "Swagger UI documentation",
            "GET /redoc": "ReDoc documentation"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
