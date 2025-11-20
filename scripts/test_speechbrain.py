"""
Test script to verify SpeechBrain installation and model loading
"""

import sys
import torch
import torchaudio

print("=" * 80)
print("Testing SpeechBrain Installation")
print("=" * 80)
print()

# Workaround for torchaudio backend compatibility issue
print("[0/4] Applying compatibility patches...")
try:
    # Monkey-patch the list_audio_backends function if it doesn't exist
    if not hasattr(torchaudio, 'list_audio_backends'):
        def list_audio_backends():
            return ["ffmpeg", "sox", "sox_io"]
        torchaudio.list_audio_backends = list_audio_backends
        print("[OK] Applied torchaudio compatibility patch")
    print()
except Exception as e:
    print(f"[WARNING] Could not apply patch: {e}")
    print()

# Test 1: Import SpeechBrain
print("[1/4] Testing SpeechBrain import...")
try:
    import speechbrain
    from speechbrain.inference.speaker import EncoderClassifier
    print(f"[OK] SpeechBrain version: {speechbrain.__version__}")
    print()
except ImportError as e:
    print(f"[ERROR] Failed to import SpeechBrain: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Check PyTorch
print("[2/4] Checking PyTorch...")
print(f"[OK] PyTorch version: {torch.__version__}")
print(f"[OK] CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"[OK] CUDA device: {torch.cuda.get_device_name(0)}")
print()

# Test 3: Load ECAPA-TDNN model
print("[3/4] Loading ECAPA-TDNN speaker recognition model...")
print("  This may take a few minutes on first run (downloading model)...")
try:
    from speechbrain.utils.fetching import LocalStrategy

    # Use COPY strategy instead of SYMLINK to avoid Windows permission issues
    classifier = EncoderClassifier.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        savedir="models/speechbrain/spkrec-ecapa-voxceleb",
        run_opts={"device": "cpu"},
        local_strategy=LocalStrategy.COPY
    )
    print("[OK] Model loaded successfully")
    print(f"[OK] Model cache location: models/speechbrain/spkrec-ecapa-voxceleb")
    print()
except Exception as e:
    print(f"[ERROR] Failed to load model: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Test embedding generation
print("[4/4] Testing embedding generation...")
try:
    # Create a dummy audio signal (1 second at 16kHz)
    import numpy as np
    sample_rate = 16000
    duration = 1.0
    dummy_audio = torch.randn(1, int(sample_rate * duration))

    # Generate embedding
    embedding = classifier.encode_batch(dummy_audio)

    print(f"[OK] Generated embedding shape: {embedding.shape}")
    print(f"[OK] Embedding dimension: {embedding.shape[-1]}")
    print()
except Exception as e:
    print(f"[ERROR] Failed to generate embedding: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Success!
print("=" * 80)
print("SUCCESS: SpeechBrain is properly installed and working!")
print("=" * 80)
print()
print("Next steps:")
print("1. Add speaker audio samples to data/speaker_profiles/{speaker_name}/")
print("2. Create speakers.json with speaker metadata")
print("3. Set ENABLE_SPEAKER_RECOGNITION=true in .env")
print("4. Run orchestrator to process a meeting with speaker recognition")
