"""
Speaker Diarization module using pyannote.audio

Diarization - the process of dividing audio into segments by speakers,
answering the question "who speaks when?"
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import torch
from pyannote.audio import Pipeline

logger = logging.getLogger(__name__)


class DiarizationSegment:
    """Diarization segment with speaker identifier"""

    def __init__(self, start: float, end: float, speaker: str):
        self.start = start
        self.end = end
        self.speaker = speaker

    def to_dict(self) -> dict:
        return {
            "start": round(self.start, 2),
            "end": round(self.end, 2),
            "speaker": self.speaker
        }


class SpeakerDiarizer:
    """
    Class for speaker identification using pyannote.audio

    Attributes:
        pipeline: Loaded pyannote.audio pipeline
        device: Device for inference (cpu/cuda)
    """

    def __init__(
        self,
        model_name: str = "pyannote/speaker-diarization-3.1",
        device: str = "cpu",
        use_auth_token: Optional[str] = None
    ):
        """
        Initialize diarizer

        Args:
            model_name: Model name on HuggingFace
            device: cpu or cuda
            use_auth_token: HuggingFace token for model access
                Can be obtained at https://huggingface.co/settings/tokens
                License must be accepted at:
                https://huggingface.co/pyannote/speaker-diarization

        Raises:
            ValueError: If HuggingFace token not provided
            RuntimeError: On model loading error
        """
        self.device = torch.device(device)

        # Get token from environment variables if not specified
        if use_auth_token is None:
            use_auth_token = os.getenv("HF_TOKEN")

        if not use_auth_token:
            raise ValueError(
                "HuggingFace token not found. "
                "Specify it in use_auth_token parameter or HF_TOKEN environment variable. "
                "Get token at: https://huggingface.co/settings/tokens"
            )

        logger.info(f"Loading pyannote model: {model_name} (device={device})")

        try:
            self.pipeline = Pipeline.from_pretrained(
                model_name,
                use_auth_token=use_auth_token
            )

            # Move to device
            self.pipeline.to(self.device)

            logger.info(f"pyannote model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading pyannote model: {e}")
            logger.error(
                "Make sure that:\n"
                "1. HF_TOKEN is valid\n"
                "2. License accepted: https://huggingface.co/pyannote/speaker-diarization\n"
                "3. License accepted: https://huggingface.co/pyannote/segmentation"
            )
            raise RuntimeError(f"Failed to load pyannote model: {str(e)}")

    def diarize(
        self,
        audio_path: Path,
        num_speakers: Optional[int] = None,
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None
    ) -> List[DiarizationSegment]:
        """
        Perform diarization on audio file

        Args:
            audio_path: Path to audio file
            num_speakers: Exact number of speakers (if known)
            min_speakers: Minimum number of speakers
            max_speakers: Maximum number of speakers

        Returns:
            List of segments with speaker identifiers

        Raises:
            FileNotFoundError: If audio file not found
            RuntimeError: On diarization error
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"Starting diarization: {audio_path.name}")
        logger.info(
            f"Parameters: num_speakers={num_speakers}, "
            f"min={min_speakers}, max={max_speakers}"
        )

        try:
            # Perform diarization
            diarization = self.pipeline(
                str(audio_path),
                num_speakers=num_speakers,
                min_speakers=min_speakers,
                max_speakers=max_speakers
            )

            # Convert to list of segments
            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segments.append(
                    DiarizationSegment(
                        start=turn.start,
                        end=turn.end,
                        speaker=speaker
                    )
                )

            # Count unique speakers
            unique_speakers = len(set(seg.speaker for seg in segments))

            logger.info(
                f"Diarization completed: {len(segments)} segments, "
                f"{unique_speakers} speakers"
            )

            return segments

        except Exception as e:
            logger.error(f"Diarization error: {e}", exc_info=True)
            raise RuntimeError(f"Failed to perform diarization: {str(e)}")

    def get_model_info(self) -> dict:
        """
        Get information about loaded model

        Returns:
            Dictionary with model information
        """
        return {
            "framework": "pyannote.audio",
            "device": str(self.device)
        }


def merge_transcription_diarization(
    transcription_segments: List,
    diarization_segments: List[DiarizationSegment]
) -> List[Dict]:
    """
    Merge transcription and diarization

    Matches text segments with speakers based on timestamps.

    Args:
        transcription_segments: List of transcription segments
        diarization_segments: List of diarization segments

    Returns:
        List of dictionaries with merged information:
        [{
            "start": float,
            "end": float,
            "text": str,
            "speaker": str
        }]
    """
    logger.info("Starting merge of transcription and diarization")

    merged = []

    for trans_seg in transcription_segments:
        # Convert TranscriptionSegment to dict if necessary
        if hasattr(trans_seg, 'to_dict'):
            trans_dict = trans_seg.to_dict()
        else:
            trans_dict = trans_seg

        trans_start = trans_dict["start"]
        trans_end = trans_dict["end"]
        trans_mid = (trans_start + trans_end) / 2

        # Find speaker for this segment
        # Using middle of transcription segment
        speaker = "UNKNOWN"

        for diar_seg in diarization_segments:
            if diar_seg.start <= trans_mid <= diar_seg.end:
                speaker = diar_seg.speaker
                break

        merged.append({
            "start": trans_dict["start"],
            "end": trans_dict["end"],
            "text": trans_dict["text"],
            "speaker": speaker
        })

    logger.info(f"Merge completed: {len(merged)} segments")

    return merged
