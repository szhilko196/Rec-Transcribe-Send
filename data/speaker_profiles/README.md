# Speaker Profiles for Recognition

This directory contains speaker voice profiles for automatic speaker recognition during meeting transcription.

## Overview

The speaker recognition system uses voice embeddings to identify known speakers and replace generic labels (SPEAKER_00, SPEAKER_01) with real names in transcripts.

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

### 6. Test Recognition

Process a new video or manually run the orchestrator to test:

```bash
python services/transcription_orchestrator/orchestrator.py data/input/test_meeting.avi
```

## speakers.json Schema

### Required Fields

- `id`: Unique identifier (lowercase, no spaces, e.g., "ivan_petrov")
- `name`: Display name (can be in any language, e.g., "Иван Петров")
- `audio_samples`: Array of relative paths to audio sample files

### Optional Fields

- `embedding_file`: Path to cached embedding (auto-generated if not specified)
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

**Symptom**: Recognition is slow, embeddings regenerated every time

**Solutions**:
- Check write permissions on `embeddings/` directory
- Verify `embedding_file` path in `speakers.json` is correct
- Check disk space availability

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
