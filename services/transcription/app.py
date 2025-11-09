"""
Transcription Service - Transcription and speaker identification

This microservice combines Faster-Whisper (STT) and pyannote.audio (diarization)
to create full transcription with speaker identification.

Endpoints:
    POST /transcribe - Transcription only
    POST /diarize - Diarization only
    POST /transcribe-with-speakers - Full process (transcription + diarization)
    GET /health - Health check
    GET /models/info - Model information
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List

import aiofiles
from fastapi import FastAPI, File, HTTPException, UploadFile, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from transcribe import WhisperTranscriber, TranscriptionSegment
from diarize import SpeakerDiarizer, merge_transcription_diarization

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/app/logs/transcription.log')
    ]
)
logger = logging.getLogger(__name__)

# FastAPI initialization
app = FastAPI(
    title="Transcription & Diarization Service",
    description="Speech transcription and speaker identification service",
    version="1.0.0"
)

# Path configuration
DATA_DIR = Path("/app/data")
AUDIO_DIR = DATA_DIR / "audio"
TRANSCRIPTS_DIR = DATA_DIR / "transcripts"
MODELS_DIR = Path("/app/models")

# Create directories
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Global variables for models (loaded at startup)
whisper_transcriber: Optional[WhisperTranscriber] = None
speaker_diarizer: Optional[SpeakerDiarizer] = None
models_loaded = False


# Pydantic models
class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    service: str
    timestamp: str
    models_loaded: bool
    models_info: Optional[dict] = None


class TranscriptionResponse(BaseModel):
    """Transcription response model"""
    status: str
    transcript_path: str
    num_segments: int
    duration: Optional[float] = None
    language: Optional[str] = None
    processing_time: float


class DiarizationResponse(BaseModel):
    """Diarization response model"""
    status: str
    num_segments: int
    num_speakers: int
    processing_time: float


class TranscriptionWithSpeakersResponse(BaseModel):
    """Full transcription with speakers response model"""
    status: str
    transcript_path: str
    num_segments: int
    num_speakers: int
    duration: Optional[float] = None
    language: Optional[str] = None
    processing_time: float


class ModelsInfoResponse(BaseModel):
    """Model information response"""
    whisper: dict
    pyannote: dict


@app.on_event("startup")
async def startup_event():
    """
    Load models at application startup
    """
    global whisper_transcriber, speaker_diarizer, models_loaded

    logger.info("="*60)
    logger.info("STARTING TRANSCRIPTION SERVICE")
    logger.info("="*60)

    # Get configuration from environment variables
    whisper_model = os.getenv("WHISPER_MODEL", "medium")
    device = os.getenv("DEVICE", "cpu")
    language = os.getenv("LANGUAGE", "ru")
    hf_token = os.getenv("HF_TOKEN")

    logger.info(f"Configuration:")
    logger.info(f"  - Whisper model: {whisper_model}")
    logger.info(f"  - Device: {device}")
    logger.info(f"  - Language: {language}")
    logger.info(f"  - HF token: {'***' + hf_token[-4:] if hf_token else 'NOT SET'}")

    try:
        # Load Whisper
        logger.info("Loading Whisper model...")
        whisper_transcriber = WhisperTranscriber(
            model_size=whisper_model,
            device=device,
            compute_type="int8" if device == "cpu" else "float16"
        )
        logger.info("✓ Whisper model loaded")

        # Load pyannote.audio
        logger.info("Loading pyannote.audio model...")
        speaker_diarizer = SpeakerDiarizer(
            device=device,
            use_auth_token=hf_token
        )
        logger.info("✓ pyannote.audio model loaded")

        models_loaded = True
        logger.info("="*60)
        logger.info("ALL MODELS SUCCESSFULLY LOADED")
        logger.info("="*60)

    except Exception as e:
        logger.error(f"MODEL LOADING ERROR: {e}", exc_info=True)
        logger.warning("Service started but models not loaded!")
        models_loaded = False


async def get_audio_duration(audio_path: Path) -> Optional[float]:
    """
    Get audio duration using ffprobe

    Args:
        audio_path: Path to audio file

    Returns:
        Duration in seconds or None
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
            return round(float(stdout.decode().strip()), 2)
        return None
    except Exception as e:
        logger.warning(f"Failed to determine duration: {e}")
        return None


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    """
    models_info = None
    if models_loaded:
        models_info = {
            "whisper": whisper_transcriber.get_model_info(),
            "pyannote": speaker_diarizer.get_model_info()
        }

    return HealthResponse(
        status="healthy" if models_loaded else "degraded",
        service="transcription-diarization",
        timestamp=datetime.utcnow().isoformat(),
        models_loaded=models_loaded,
        models_info=models_info
    )


@app.get("/models/info", response_model=ModelsInfoResponse)
async def get_models_info():
    """
    Get information about loaded models
    """
    if not models_loaded:
        raise HTTPException(
            status_code=503,
            detail="Models not loaded. Check service logs."
        )

    return ModelsInfoResponse(
        whisper=whisper_transcriber.get_model_info(),
        pyannote=speaker_diarizer.get_model_info()
    )


@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(..., description="Audio file (.wav, .mp3, etc.)"),
    language: str = Query("ru", description="Audio language (ru/en, etc.)"),
    beam_size: int = Query(5, ge=1, le=10, description="Beam size for Whisper")
):
    """
    Transcribe audio file (without diarization)

    Args:
        file: Audio file
        language: Audio language
        beam_size: Beam search size

    Returns:
        Transcription with timestamps
    """
    if whisper_transcriber is None:
        raise HTTPException(
            status_code=503,
            detail="Whisper model not loaded. Service unavailable."
        )

    start_time = datetime.utcnow()
    file_id = str(uuid.uuid4())

    try:
        # Save audio file
        audio_filename = f"{file_id}_{file.filename}"
        audio_path = AUDIO_DIR / audio_filename

        async with aiofiles.open(audio_path, 'wb') as f:
            content = await file.read()
            await f.write(content)

        logger.info(f"Starting transcription: {file.filename}")

        # Transcription (runs synchronously in executor)
        loop = asyncio.get_event_loop()
        segments = await loop.run_in_executor(
            None,
            whisper_transcriber.transcribe,
            audio_path,
            language,
            beam_size
        )

        # Get duration
        duration = await get_audio_duration(audio_path)

        # Save result to JSON
        transcript_filename = f"{file_id}_transcript.json"
        transcript_path = TRANSCRIPTS_DIR / transcript_filename

        transcript_data = {
            "metadata": {
                "original_filename": file.filename,
                "duration_seconds": duration,
                "language": language,
                "processed_at": datetime.utcnow().isoformat()
            },
            "transcript": [seg.to_dict() for seg in segments]
        }

        async with aiofiles.open(transcript_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(transcript_data, ensure_ascii=False, indent=2))

        # Delete audio file
        audio_path.unlink()

        processing_time = (datetime.utcnow() - start_time).total_seconds()

        logger.info(
            f"Transcription completed: {len(segments)} segments, "
            f"{processing_time:.2f}s"
        )

        return TranscriptionResponse(
            status="success",
            transcript_path=f"/app/data/transcripts/{transcript_filename}",
            num_segments=len(segments),
            duration=duration,
            language=language,
            processing_time=round(processing_time, 2)
        )

    except Exception as e:
        logger.error(f"Transcription error: {e}", exc_info=True)
        # Cleanup
        if audio_path.exists():
            audio_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/diarize", response_model=DiarizationResponse)
async def diarize_audio(
    file: UploadFile = File(..., description="Audio file"),
    num_speakers: Optional[int] = Query(None, ge=1, le=20, description="Exact number of speakers"),
    min_speakers: Optional[int] = Query(None, ge=1, le=20, description="Minimum number"),
    max_speakers: Optional[int] = Query(None, ge=1, le=20, description="Maximum number")
):
    """
    Identify speakers in audio file (without transcription)
    """
    if not models_loaded:
        raise HTTPException(status_code=503, detail="Models not loaded")

    start_time = datetime.utcnow()
    file_id = str(uuid.uuid4())

    try:
        # Save audio
        audio_filename = f"{file_id}_{file.filename}"
        audio_path = AUDIO_DIR / audio_filename

        async with aiofiles.open(audio_path, 'wb') as f:
            content = await file.read()
            await f.write(content)

        logger.info(f"Starting diarization: {file.filename}")

        # Diarization
        loop = asyncio.get_event_loop()
        segments = await loop.run_in_executor(
            None,
            speaker_diarizer.diarize,
            audio_path,
            num_speakers,
            min_speakers,
            max_speakers
        )

        # Count unique speakers
        unique_speakers = len(set(seg.speaker for seg in segments))

        # Delete audio
        audio_path.unlink()

        processing_time = (datetime.utcnow() - start_time).total_seconds()

        logger.info(
            f"Diarization completed: {len(segments)} segments, "
            f"{unique_speakers} speakers, {processing_time:.2f}s"
        )

        return DiarizationResponse(
            status="success",
            num_segments=len(segments),
            num_speakers=unique_speakers,
            processing_time=round(processing_time, 2)
        )

    except Exception as e:
        logger.error(f"Diarization error: {e}", exc_info=True)
        if audio_path.exists():
            audio_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/transcribe-with-speakers", response_model=TranscriptionWithSpeakersResponse)
async def transcribe_with_speakers(
    file: UploadFile = File(..., description="Audio file"),
    language: str = Query("ru", description="Audio language"),
    beam_size: int = Query(5, ge=1, le=10, description="Beam size"),
    num_speakers: Optional[int] = Query(None, ge=1, le=20, description="Number of speakers"),
    min_speakers: Optional[int] = Query(None, ge=1, le=20, description="Min. speakers"),
    max_speakers: Optional[int] = Query(None, ge=1, le=20, description="Max. speakers")
):
    """
    Full process: transcription + diarization

    Performs speech transcription and speaker identification,
    then merges the results.
    """
    if not models_loaded:
        raise HTTPException(status_code=503, detail="Models not loaded")

    start_time = datetime.utcnow()
    file_id = str(uuid.uuid4())

    try:
        # Save audio
        audio_filename = f"{file_id}_{file.filename}"
        audio_path = AUDIO_DIR / audio_filename

        async with aiofiles.open(audio_path, 'wb') as f:
            content = await file.read()
            await f.write(content)

        logger.info(f"Starting full processing: {file.filename}")

        # Get duration
        duration = await get_audio_duration(audio_path)

        loop = asyncio.get_event_loop()

        # Run transcription and diarization in parallel
        logger.info("Launching transcription and diarization in parallel...")

        transcription_task = loop.run_in_executor(
            None,
            whisper_transcriber.transcribe,
            audio_path,
            language,
            beam_size
        )

        diarization_task = loop.run_in_executor(
            None,
            speaker_diarizer.diarize,
            audio_path,
            num_speakers,
            min_speakers,
            max_speakers
        )

        # Wait for both tasks to complete
        transcription_segments, diarization_segments = await asyncio.gather(
            transcription_task,
            diarization_task
        )

        logger.info("Transcription and diarization completed, starting merge...")

        # Merge results
        merged_segments = merge_transcription_diarization(
            transcription_segments,
            diarization_segments
        )

        # Count unique speakers
        unique_speakers = len(set(seg["speaker"] for seg in merged_segments))

        # Save result
        transcript_filename = f"{file_id}_full_transcript.json"
        transcript_path = TRANSCRIPTS_DIR / transcript_filename

        transcript_data = {
            "metadata": {
                "original_filename": file.filename,
                "duration_seconds": duration,
                "num_speakers": unique_speakers,
                "language": language,
                "processed_at": datetime.utcnow().isoformat()
            },
            "transcript": merged_segments
        }

        async with aiofiles.open(transcript_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(transcript_data, ensure_ascii=False, indent=2))

        # Delete audio
        audio_path.unlink()

        processing_time = (datetime.utcnow() - start_time).total_seconds()

        logger.info(
            f"Full processing completed: {len(merged_segments)} segments, "
            f"{unique_speakers} speakers, {processing_time:.2f}s"
        )

        return TranscriptionWithSpeakersResponse(
            status="success",
            transcript_path=f"/app/data/transcripts/{transcript_filename}",
            num_segments=len(merged_segments),
            num_speakers=unique_speakers,
            duration=duration,
            language=language,
            processing_time=round(processing_time, 2)
        )

    except Exception as e:
        logger.error(f"Full processing error: {e}", exc_info=True)
        if audio_path.exists():
            audio_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """
    Root endpoint with service information
    """
    return {
        "service": "Transcription & Diarization Service",
        "version": "1.0.0",
        "description": "Speech transcription (Faster-Whisper) + speaker identification (pyannote.audio)",
        "models_loaded": models_loaded,
        "endpoints": {
            "POST /transcribe": "Transcription only",
            "POST /diarize": "Diarization only",
            "POST /transcribe-with-speakers": "Transcription + diarization",
            "GET /health": "Health check",
            "GET /models/info": "Model information",
            "GET /docs": "Swagger UI",
            "GET /redoc": "ReDoc"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
