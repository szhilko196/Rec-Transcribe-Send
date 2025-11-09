"""
Audio transcription module using Faster-Whisper

Faster-Whisper - optimized version of OpenAI Whisper,
using CTranslate2 to speed up inference by 4x.
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Optional

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


class TranscriptionSegment:
    """Transcription segment with timestamps"""

    def __init__(self, start: float, end: float, text: str):
        self.start = start
        self.end = end
        self.text = text

    def to_dict(self) -> dict:
        return {
            "start": round(self.start, 2),
            "end": round(self.end, 2),
            "text": self.text.strip()
        }


class WhisperTranscriber:
    """
    Class for audio transcription using Faster-Whisper

    Attributes:
        model: Loaded Whisper model
        model_size: Model size (tiny/base/small/medium/large)
        device: Device for inference (cpu/cuda)
        compute_type: Computation type (int8/float16/float32)
    """

    def __init__(
        self,
        model_size: str = "medium",
        device: str = "cpu",
        compute_type: str = "int8",
        download_root: Optional[str] = None
    ):
        """
        Initialize transcriber

        Args:
            model_size: Whisper model size
                - tiny: fastest, least accurate (~75MB)
                - base: fast, acceptable accuracy (~145MB)
                - small: medium speed and accuracy (~466MB)
                - medium: good accuracy (~1.5GB) - recommended
                - large-v2: best accuracy, slow (~3GB)
            device: cpu or cuda
            compute_type: Computation type
                - int8: faster, less memory (CPU)
                - float16: faster, requires GPU
                - float32: more accurate, slower
            download_root: Directory for model caching
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type

        if download_root is None:
            download_root = os.getenv("MODELS_PATH", "/app/models/whisper")

        logger.info(
            f"Loading Whisper model: {model_size} "
            f"(device={device}, compute_type={compute_type})"
        )

        try:
            self.model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
                download_root=download_root
            )
            logger.info(f"Whisper model '{model_size}' loaded successfully")
        except Exception as e:
            logger.error(f"Error loading Whisper model: {e}")
            raise

    def transcribe(
        self,
        audio_path: Path,
        language: str = "ru",
        beam_size: int = 5,
        vad_filter: bool = True
    ) -> List[TranscriptionSegment]:
        """
        Transcribe audio file

        Args:
            audio_path: Path to audio file (.wav, .mp3, etc.)
            language: Audio language (ru/en/es etc.)
            beam_size: Beam search size (larger = more accurate but slower)
            vad_filter: Use Voice Activity Detection to filter silence

        Returns:
            List of transcription segments with timestamps

        Raises:
            FileNotFoundError: If audio file not found
            RuntimeError: On transcription error
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"Starting transcription: {audio_path.name}")
        logger.info(f"Parameters: language={language}, beam_size={beam_size}, vad={vad_filter}")

        try:
            # Transcription using Faster-Whisper
            segments, info = self.model.transcribe(
                str(audio_path),
                language=language,
                beam_size=beam_size,
                vad_filter=vad_filter,
                word_timestamps=False  # Timestamps at segment level
            )

            logger.info(
                f"Detected language: {info.language} "
                f"(probability: {info.language_probability:.2%})"
            )

            # Convert to list of segments
            transcription_segments = []
            for segment in segments:
                transcription_segments.append(
                    TranscriptionSegment(
                        start=segment.start,
                        end=segment.end,
                        text=segment.text
                    )
                )

            logger.info(
                f"Transcription completed: {len(transcription_segments)} segments"
            )

            return transcription_segments

        except Exception as e:
            logger.error(f"Transcription error: {e}", exc_info=True)
            raise RuntimeError(f"Failed to transcribe audio: {str(e)}")

    def get_model_info(self) -> dict:
        """
        Get information about loaded model

        Returns:
            Dictionary with model information
        """
        return {
            "model_size": self.model_size,
            "device": self.device,
            "compute_type": self.compute_type,
            "framework": "faster-whisper"
        }
