# Speaker Profiles for Recognition

This directory contains speaker voice profiles for automatic speaker recognition during meeting transcription.

## Overview

The speaker recognition system uses voice embeddings to identify known speakers and replace generic labels (SPEAKER_00, SPEAKER_01) with real names in transcripts.

## System Requirements

### Python Environment
- **Python 3.11** 64-bit (required for PyTorch/SpeechBrain compatibility)
- Virtual environment setup via `services/transcription_orchestrator/setup.bat`

### Required Packages
- `speechbrain>=1.0.0` - Voice embedding model
- `torch>=2.1.0,<2.5.0` - Deep learning framework
- `torchaudio>=2.1.0,<2.5.0` - Audio processing
- `soundfile>=0.12.1` - Audio file I/O backend
- `numpy>=1.24.0` - Numerical computing

### Environment Variables (.env)
```env
ENABLE_SPEAKER_RECOGNITION=true
RECOGNITION_THRESHOLD=0.75           # 0.65=lenient, 0.75=balanced, 0.85=strict
SPEAKER_RECOGNITION_DEVICE=cpu       # or "cuda" for GPU
SPEAKER_PROFILES_PATH=C:/path/to/data/speaker_profiles
```

### First-Time Setup
On first run, SpeechBrain will download the ECAPA-TDNN model (~500MB). This is a one-time download and will be cached locally.

## Audio Sample Requirements

For best recognition accuracy, speaker audio samples should meet these criteria:

- **Format**: WAV, 16kHz mono (same as transcription input)
- **Duration**: 3-10 seconds per sample
- **Quality**: Clean speech with minimal background noise
- **Quantity**: 3-5 samples per speaker (more samples = better accuracy)
- **Content**: Natural speech, ideally from previous meeting recordings
- **Variety**: Include different speaking styles (formal, casual, questions, statements)

## Directory Structure

```
speaker_profiles/
├── speakers.json              # Speaker metadata and configuration
├── embeddings/                # Cached speaker embeddings (auto-generated)
│   ├── ivan_petrov_embed.npy
│   └── maria_ivanova_embed.npy
├── ivan_petrov/              # Audio samples for Ivan
│   ├── sample_01.wav
│   ├── sample_02.wav
│   └── sample_03.wav
└── maria_ivanova/            # Audio samples for Maria
    ├── sample_01.wav
    ├── sample_02.wav
    └── sample_03.wav
```

## Enrollment Process

### 1. Prepare Audio Samples

Extract 3-5 clean speech segments from previous meetings:

```bash
# Example using ffmpeg to extract a 5-second segment
ffmpeg -i meeting.wav -ss 00:05:30 -t 5 -ar 16000 -ac 1 sample_01.wav
```

### 2. Create Speaker Directory

```bash
mkdir speaker_profiles/ivan_petrov
```

### 3. Add Audio Samples

Copy your extracted audio samples to the speaker directory:

```bash
cp sample_01.wav speaker_profiles/ivan_petrov/
cp sample_02.wav speaker_profiles/ivan_petrov/
cp sample_03.wav speaker_profiles/ivan_petrov/
```

### 4. Update speakers.json

Create or update `speakers.json` with speaker metadata:

```json
{
  "version": "1.0",
  "speakers": [
    {
      "id": "ivan_petrov",
      "name": "Иван Петров",
      "audio_samples": [
        "ivan_petrov/sample_01.wav",
        "ivan_petrov/sample_02.wav",
        "ivan_petrov/sample_03.wav"
      ],
      "embedding_file": "embeddings/ivan_petrov_embed.npy",
      "created_at": "2025-01-18T10:00:00Z",
      "metadata": {
        "role": "Project Manager",
        "department": "Engineering",
        "email": "ivan.petrov@company.com"
      }
    }
  ],
  "settings": {
    "min_segment_duration": 1.0,
    "embedding_aggregation": "mean",
    "normalization": "cosine"
  }
}
```

### 5. Enable Speaker Recognition

Update your `.env` file:

```env
ENABLE_SPEAKER_RECOGNITION=true
RECOGNITION_THRESHOLD=0.75
SPEAKER_PROFILES_PATH=./data/speaker_profiles
```

### 6. Generate Embeddings

After updating `speakers.json` with `embedding_file` paths, generate the embeddings by running the orchestrator once or using a test script:

**Option A: Process a video** (embeddings will be generated automatically):
```bash
python services/transcription_orchestrator/orchestrator.py data/input/test_meeting.avi
```

**Option B: Generate embeddings without processing** (faster, recommended for initial setup):
```python
# Create a test script: test_generate_embeddings.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'services' / 'transcription_orchestrator'))

from dotenv import load_dotenv
import os

# Load .env
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env', override=True)

from recognize import SpeakerRecognizer

# Initialize recognizer
recognizer = SpeakerRecognizer(
    profiles_path=os.getenv('SPEAKER_PROFILES_PATH', './data/speaker_profiles'),
    device=os.getenv('SPEAKER_RECOGNITION_DEVICE', 'cpu'),
    threshold=float(os.getenv('RECOGNITION_THRESHOLD', '0.75'))
)

# Load profiles and generate embeddings
print("Generating embeddings...")
loaded_count = recognizer.load_profiles()
print(f"Successfully generated embeddings for {loaded_count} speakers!")

# Verify embeddings were saved
embeddings_dir = Path(os.getenv('SPEAKER_PROFILES_PATH', './data/speaker_profiles')) / 'embeddings'
npy_files = list(embeddings_dir.glob('*.npy'))
print(f"\nEmbedding files created: {len(npy_files)}")
for f in npy_files:
    print(f"  - {f.name}")
```

Run the script:
```bash
python test_generate_embeddings.py
```

**What happens**:
1. SpeechBrain ECAPA-TDNN model is loaded (~500MB download on first run)
2. For each speaker:
   - Audio samples are loaded
   - Voice embeddings are extracted (192-dimensional vectors)
   - Embeddings are averaged across samples
   - Result is saved to `embeddings/{speaker_id}_embed.npy`
3. Files are cached for fast loading in future runs

**Expected output**:
```
Generating embeddings...
2025-11-29 22:55:05,086 - recognize - INFO - Model loaded successfully (1.0s)
2025-11-29 22:55:06,197 - recognize - INFO - Loaded speaker: Юлия Рублева (ID: yuliya_rubleva)
2025-11-29 22:55:14,884 - recognize - INFO - Loaded speaker: Мария Егорова (ID: mariya_egorova)
...
Successfully generated embeddings for 10 speakers!

Embedding files created: 10
  - yuliya_rubleva_embed.npy
  - mariya_egorova_embed.npy
  ...
```

### 7. Test Recognition

Process a new video to test speaker recognition:

```bash
python services/transcription_orchestrator/orchestrator.py data/input/test_meeting.avi
```

## speakers.json Schema

### Required Fields

- `id`: Unique identifier (lowercase, no spaces, e.g., "ivan_petrov")
- `name`: Display name (can be in any language, e.g., "Иван Петров")
- `audio_samples`: Array of relative paths to audio sample files

### Optional Fields

- `embedding_file`: **IMPORTANT** - Path to cached embedding file (relative to speaker_profiles directory)
  - **Without this field**: Embeddings are generated in memory but NOT saved to disk (slow on every run)
  - **With this field**: Embeddings are cached to disk and loaded instantly on subsequent runs
  - **Format**: `"embeddings/{speaker_id}_embed.npy"`
  - **Example**: `"embedding_file": "embeddings/ivan_petrov_embed.npy"`
- `created_at`: ISO 8601 timestamp
- `metadata`: Custom metadata (role, department, email, etc.)

### Settings

- `min_segment_duration`: Minimum segment duration for recognition (default: 1.0 seconds)
- `embedding_aggregation`: Method to combine multiple embeddings (default: "mean")
- `normalization`: Similarity metric (default: "cosine")

## Troubleshooting

### Low Recognition Accuracy

**Symptom**: Speakers not being recognized or frequent misidentifications

**Solutions**:
- Add more audio samples (aim for 5-7 samples)
- Use cleaner audio with less background noise
- Ensure samples contain only one speaker
- Extract samples from similar recording conditions (same microphone, environment)

### False Positives

**Symptom**: Wrong speaker names assigned

**Solutions**:
- Increase `RECOGNITION_THRESHOLD` in `.env` (try 0.80 or 0.85)
- Ensure audio samples are from the correct speaker
- Add more diverse samples to improve discrimination

### No Speakers Recognized

**Symptom**: All speakers remain as SPEAKER_00, SPEAKER_01, etc.

**Solutions**:
- Check that `ENABLE_SPEAKER_RECOGNITION=true` in `.env`
- Verify `speakers.json` is properly formatted (validate JSON syntax)
- Ensure audio sample files exist at the specified paths
- Check orchestrator logs for error messages
- Lower `RECOGNITION_THRESHOLD` (try 0.65 or 0.70)

### Embeddings Not Cached

**Symptom**: Recognition is slow, embeddings regenerated every time, no `.npy` files in `embeddings/` folder

**Solutions**:
- **Add `embedding_file` field to each speaker in `speakers.json`**:
  ```json
  {
    "id": "ivan_petrov",
    "name": "Иван Петров",
    "audio_samples": [...],
    "embedding_file": "embeddings/ivan_petrov_embed.npy"  // ← ADD THIS LINE
  }
  ```
- Check write permissions on `embeddings/` directory
- Verify `embedding_file` path in `speakers.json` is correct
- Check disk space availability
- Run embedding generation script (see Step 6 in Enrollment Process above)

### Model Download Fails

**Symptom**: Error during SpeechBrain model download

**Solutions**:
- Check internet connection
- Verify firewall allows HuggingFace Hub access
- Pre-download models manually (see Advanced Configuration below)

## Advanced Configuration

### Pre-downloading Models

To avoid downloading models on first run:

```python
from speechbrain.inference.speaker import EncoderClassifier

# This will download and cache the model
classifier = EncoderClassifier.from_hparams(
    source="speechbrain/spkrec-ecapa-voxceleb",
    savedir="~/.cache/huggingface/hub/"
)
```

### Custom Cache Directory

Set the HuggingFace cache directory:

```env
HF_HOME=C:/path/to/cache
```

### GPU Acceleration

If you have a CUDA-capable GPU:

```env
DEVICE=cuda
```

This will speed up embedding generation significantly.

## Performance Notes

**Recognition Overhead** (CPU mode):
- Embedding extraction per speaker: ~1-3 seconds
- Similarity comparison: <0.1 seconds per speaker
- Total for 3 speakers in 1-hour meeting: ~5-10 minutes

**Expected Accuracy**:
- >85% recognition accuracy with good quality samples
- <5% false positive rate with appropriate threshold

## Examples

### Example 1: Adding a New Speaker

```bash
# 1. Create directory
mkdir data/speaker_profiles/maria_ivanova

# 2. Extract audio samples from a meeting
ffmpeg -i meeting.wav -ss 00:10:15 -t 7 -ar 16000 -ac 1 data/speaker_profiles/maria_ivanova/sample_01.wav
ffmpeg -i meeting.wav -ss 00:25:40 -t 5 -ar 16000 -ac 1 data/speaker_profiles/maria_ivanova/sample_02.wav
ffmpeg -i meeting.wav -ss 00:45:10 -t 6 -ar 16000 -ac 1 data/speaker_profiles/maria_ivanova/sample_03.wav

# 3. Update speakers.json (add entry to "speakers" array)

# 4. Process a new meeting
python services/transcription_orchestrator/orchestrator.py data/input/new_meeting.avi
```

### Example 2: Testing Recognition

Create a test script to verify speaker profiles:

```python
from services.transcription_orchestrator.recognize import SpeakerRecognizer

recognizer = SpeakerRecognizer(
    profiles_path="data/speaker_profiles",
    device="cpu",
    threshold=0.75
)

recognizer.load_profiles()
print(f"Loaded {len(recognizer.speaker_embeddings)} speaker profiles:")
for speaker_name in recognizer.speaker_embeddings.keys():
    print(f"  - {speaker_name}")
```

## References

- **SpeechBrain Documentation**: https://speechbrain.github.io/
- **ECAPA-TDNN Model**: https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb
- **Speaker Recognition Tutorial**: https://speechbrain.readthedocs.io/en/latest/tutorials/speaker_recognition.html
