"""
Speaker Recognition Module

This module provides speaker recognition functionality using SpeechBrain.
It identifies speakers by matching their voice characteristics against a
database of known speaker profiles.

Uses ECAPA-TDNN embeddings for speaker verification and identification.
"""

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torchaudio

# Apply compatibility patch for torchaudio
if not hasattr(torchaudio, 'list_audio_backends'):
    def list_audio_backends():
        return ["ffmpeg", "sox", "sox_io"]
    torchaudio.list_audio_backends = list_audio_backends

from speechbrain.inference.speaker import EncoderClassifier
from speechbrain.utils.fetching import LocalStrategy

from speaker_profile_validator import SpeakerProfileValidator


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SpeakerRecognizer:
    """
    Speaker recognition using SpeechBrain ECAPA-TDNN embeddings

    This class handles:
    - Loading speaker profiles from speakers.json
    - Generating voice embeddings from audio samples
    - Identifying speakers in audio segments
    - Caching embeddings for faster subsequent runs
    """

    def __init__(self, profiles_path: str, device: str = "cpu", threshold: float = 0.75):
        """
        Initialize speaker recognizer

        Args:
            profiles_path: Path to speaker_profiles directory
            device: Device for inference ("cpu" or "cuda")
            threshold: Similarity threshold for positive identification (0.0-1.0)
        """
        self.profiles_path = Path(profiles_path)
        self.device = device
        self.threshold = threshold

        # Validate threshold
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"Threshold must be between 0.0 and 1.0, got {threshold}")

        # Storage for speaker embeddings
        self.speaker_embeddings: Dict[str, np.ndarray] = {}
        self.speaker_names: Dict[str, str] = {}  # id -> display name mapping

        # SpeechBrain model (lazy loaded)
        self.model: Optional[EncoderClassifier] = None

        logger.info(f"Initialized SpeakerRecognizer (device={device}, threshold={threshold})")

    def _load_model(self) -> EncoderClassifier:
        """
        Load SpeechBrain ECAPA-TDNN model

        Returns:
            Loaded EncoderClassifier model
        """
        if self.model is not None:
            return self.model

        logger.info("Loading ECAPA-TDNN speaker recognition model...")
        start_time = time.time()

        try:
            # Use COPY strategy to avoid Windows symlink permission issues
            self.model = EncoderClassifier.from_hparams(
                source="speechbrain/spkrec-ecapa-voxceleb",
                savedir="models/speechbrain/spkrec-ecapa-voxceleb",
                run_opts={"device": self.device},
                local_strategy=LocalStrategy.COPY
            )

            elapsed = time.time() - start_time
            logger.info(f"Model loaded successfully ({elapsed:.1f}s)")

            return self.model

        except Exception as e:
            logger.error(f"Failed to load SpeechBrain model: {e}")
            raise

    def load_profiles(self) -> int:
        """
        Load speaker profiles from speakers.json

        Returns:
            Number of speakers loaded
        """
        logger.info(f"Loading speaker profiles from: {self.profiles_path}")

        # Validate speakers.json
        validator = SpeakerProfileValidator(str(self.profiles_path))
        is_valid, data, errors = validator.load_and_validate()

        if not is_valid:
            logger.error("Speaker profiles validation failed:")
            for error in errors:
                logger.error(f"  - {error}")
            raise ValueError("Invalid speaker profiles")

        # Load or generate embeddings for each speaker
        speakers = data.get("speakers", [])
        loaded_count = 0

        for speaker in speakers:
            speaker_id = speaker["id"]
            speaker_name = speaker["name"]

            try:
                # Load or generate embedding
                embedding = self._load_speaker_embedding(speaker)

                self.speaker_embeddings[speaker_id] = embedding
                self.speaker_names[speaker_id] = speaker_name
                loaded_count += 1

                logger.info(f"Loaded speaker: {speaker_name} (ID: {speaker_id})")

            except Exception as e:
                logger.error(f"Failed to load speaker '{speaker_name}': {e}")
                continue

        logger.info(f"Loaded {loaded_count} speaker profile(s)")
        return loaded_count

    def _load_speaker_embedding(self, speaker: Dict) -> np.ndarray:
        """
        Load or generate speaker embedding

        Args:
            speaker: Speaker dictionary from speakers.json

        Returns:
            Speaker embedding (192-dimensional vector)
        """
        speaker_id = speaker["id"]
        embedding_file = speaker.get("embedding_file")

        # Try to load cached embedding
        if embedding_file:
            embedding_path = self.profiles_path / embedding_file

            if embedding_path.exists():
                try:
                    embedding = np.load(embedding_path)
                    logger.debug(f"Loaded cached embedding for '{speaker_id}' from {embedding_path}")
                    return embedding
                except Exception as e:
                    logger.warning(f"Failed to load cached embedding: {e}, regenerating...")

        # Generate embedding from audio samples
        logger.info(f"Generating embedding for '{speaker_id}'...")
        embedding = self._generate_speaker_embedding(speaker)

        # Cache embedding
        if embedding_file:
            embedding_path = self.profiles_path / embedding_file
            embedding_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                np.save(embedding_path, embedding)
                logger.debug(f"Cached embedding to {embedding_path}")
            except Exception as e:
                logger.warning(f"Failed to cache embedding: {e}")

        return embedding

    def _generate_speaker_embedding(self, speaker: Dict) -> np.ndarray:
        """
        Generate speaker embedding from audio samples

        Args:
            speaker: Speaker dictionary with audio_samples

        Returns:
            Mean embedding across all samples
        """
        model = self._load_model()
        audio_samples = speaker["audio_samples"]
        embeddings = []

        for sample_path in audio_samples:
            full_path = self.profiles_path / sample_path

            try:
                # Load audio
                waveform, sample_rate = torchaudio.load(str(full_path))

                # Resample to 16kHz if needed
                if sample_rate != 16000:
                    resampler = torchaudio.transforms.Resample(sample_rate, 16000)
                    waveform = resampler(waveform)

                # Convert to mono if stereo
                if waveform.shape[0] > 1:
                    waveform = torch.mean(waveform, dim=0, keepdim=True)

                # Generate embedding
                with torch.no_grad():
                    embedding = model.encode_batch(waveform)
                    # Shape: (1, 1, 192) -> (192,)
                    embedding_np = embedding.squeeze().cpu().numpy()
                    embeddings.append(embedding_np)

            except Exception as e:
                logger.error(f"Failed to process audio sample {sample_path}: {e}")
                continue

        if not embeddings:
            raise ValueError(f"No valid audio samples for speaker '{speaker['id']}'")

        # Compute mean embedding across all samples
        mean_embedding = np.mean(embeddings, axis=0)

        # Normalize
        mean_embedding = mean_embedding / np.linalg.norm(mean_embedding)

        logger.debug(f"Generated embedding from {len(embeddings)} sample(s)")
        return mean_embedding

    def extract_audio_segment(self, audio_path: str, start: float, end: float) -> torch.Tensor:
        """
        Extract audio segment between timestamps

        Args:
            audio_path: Path to audio file
            start: Start time in seconds
            end: End time in seconds

        Returns:
            Audio waveform tensor (1, samples)
        """
        # Load full audio
        waveform, sample_rate = torchaudio.load(str(audio_path))

        # Resample to 16kHz if needed
        if sample_rate != 16000:
            resampler = torchaudio.transforms.Resample(sample_rate, 16000)
            waveform = resampler(waveform)
            sample_rate = 16000

        # Convert to mono if stereo
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)

        # Extract segment
        start_sample = int(start * sample_rate)
        end_sample = int(end * sample_rate)

        segment = waveform[:, start_sample:end_sample]

        return segment

    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings

        Args:
            embedding1: First embedding
            embedding2: Second embedding

        Returns:
            Similarity score (0.0 to 1.0)
        """
        # Cosine similarity
        similarity = np.dot(embedding1, embedding2) / (
            np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
        )

        # Convert to 0-1 range (cosine similarity is -1 to 1)
        similarity = (similarity + 1) / 2

        return float(similarity)

    def identify_speaker(self, audio_segment: torch.Tensor) -> Tuple[Optional[str], float]:
        """
        Identify speaker from audio segment

        Args:
            audio_segment: Audio waveform tensor

        Returns:
            (speaker_name, confidence) or (None, 0.0) if unrecognized
        """
        if len(self.speaker_embeddings) == 0:
            logger.warning("No speaker profiles loaded")
            return None, 0.0

        # Generate embedding for segment
        model = self._load_model()

        try:
            with torch.no_grad():
                segment_embedding = model.encode_batch(audio_segment)
                segment_embedding_np = segment_embedding.squeeze().cpu().numpy()

                # Normalize
                segment_embedding_np = segment_embedding_np / np.linalg.norm(segment_embedding_np)

        except Exception as e:
            logger.error(f"Failed to generate embedding for segment: {e}")
            return None, 0.0

        # Compare against all enrolled speakers
        best_match = None
        best_score = 0.0

        for speaker_id, speaker_embedding in self.speaker_embeddings.items():
            similarity = self.compute_similarity(segment_embedding_np, speaker_embedding)

            if similarity > best_score:
                best_score = similarity
                best_match = speaker_id

        # Check if best match exceeds threshold
        if best_score >= self.threshold:
            speaker_name = self.speaker_names[best_match]
            logger.debug(f"Identified: {speaker_name} (confidence: {best_score:.3f})")
            return speaker_name, best_score
        else:
            logger.debug(f"No match above threshold (best: {best_score:.3f})")
            return None, best_score

    def recognize_speakers(self, audio_path: str, transcript_segments: List[Dict]) -> Dict[str, str]:
        """
        Recognize speakers in a full meeting transcript

        Args:
            audio_path: Path to audio file
            transcript_segments: List of transcript segments with speaker labels

        Returns:
            Mapping of generic labels to speaker names {SPEAKER_00: "Иван", ...}
        """
        logger.info(f"Recognizing speakers in: {audio_path}")

        # Group segments by speaker label
        speaker_segments = {}
        for segment in transcript_segments:
            speaker_label = segment.get("speaker", "UNKNOWN")

            if speaker_label not in speaker_segments:
                speaker_segments[speaker_label] = []

            speaker_segments[speaker_label].append(segment)

        logger.info(f"Found {len(speaker_segments)} unique speaker label(s)")

        # Identify each speaker
        speaker_map = {}

        for speaker_label, segments in speaker_segments.items():
            # Aggregate audio from multiple segments for better accuracy
            # Use longest segments first
            segments_sorted = sorted(segments, key=lambda s: s.get("end", 0) - s.get("start", 0), reverse=True)

            # Try up to 5 longest segments
            votes = []

            for segment in segments_sorted[:5]:
                start = segment.get("start", 0)
                end = segment.get("end", 0)
                duration = end - start

                # Skip very short segments
                if duration < 1.0:
                    continue

                try:
                    # Extract audio segment
                    audio_segment = self.extract_audio_segment(audio_path, start, end)

                    # Identify speaker
                    speaker_name, confidence = self.identify_speaker(audio_segment)

                    if speaker_name:
                        votes.append((speaker_name, confidence))

                except Exception as e:
                    logger.error(f"Failed to process segment {start}-{end}: {e}")
                    continue

            # Determine final speaker by majority vote (weighted by confidence)
            if votes:
                # Group by speaker name and sum confidences
                speaker_scores = {}
                for name, conf in votes:
                    speaker_scores[name] = speaker_scores.get(name, 0) + conf

                # Get speaker with highest total confidence
                best_speaker = max(speaker_scores.items(), key=lambda x: x[1])
                final_name = best_speaker[0]
                avg_confidence = best_speaker[1] / len([v for v in votes if v[0] == final_name])

                speaker_map[speaker_label] = final_name
                logger.info(f"{speaker_label} -> {final_name} (confidence: {avg_confidence:.3f}, votes: {len(votes)})")
            else:
                # No identification
                speaker_map[speaker_label] = speaker_label
                logger.info(f"{speaker_label} -> unrecognized")

        return speaker_map


def main():
    """Test/demo the recognizer"""
    print("=" * 80)
    print("Speaker Recognizer Test")
    print("=" * 80)
    print()

    # Initialize recognizer
    profiles_path = "data/speaker_profiles"
    recognizer = SpeakerRecognizer(
        profiles_path=profiles_path,
        device="cpu",
        threshold=0.75
    )

    # Load profiles
    try:
        count = recognizer.load_profiles()
        print(f"[OK] Loaded {count} speaker profile(s)")
        print()

        # Show loaded speakers
        print("Enrolled speakers:")
        for speaker_id, speaker_name in recognizer.speaker_names.items():
            embedding = recognizer.speaker_embeddings[speaker_id]
            print(f"  - {speaker_name} (ID: {speaker_id}, embedding shape: {embedding.shape})")

        print()
        print("[SUCCESS] Speaker recognition system ready!")

    except Exception as e:
        print(f"[ERROR] Failed to load profiles: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
