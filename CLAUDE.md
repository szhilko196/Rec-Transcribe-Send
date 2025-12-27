# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Meeting Transcriber is a microservices-based system for automatic processing of meeting recordings (.avi files) with:
- **Automated meeting capture** from email invitations (Meeting Auto Capture)
- **Audio extraction** from video (FFmpeg)
- **Speech-to-text transcription** with Russian language support (Faster-Whisper)
- **Speaker diarization**/identification (pyannote.audio)
- **Summary and protocol generation** via Claude API
- **Workflow orchestration** through Python orchestrator and N8n
- **Chrome extension** for browser-based recording

**Key Features**:
- All components except Claude API can run locally for data confidentiality
- Automated meeting attendance: Monitor email → Join meeting → Record → Transcribe → Protocol

## Architecture

### Service Structure
```
Meeting Auto Capture Service (Port 8004 optional)
    ├── Email Monitor (IMAP) - Detect meeting invitations
    ├── Meeting Scheduler - Auto-join at scheduled time
    ├── Browser Automation (Playwright) - Join meetings via Chrome
    ├── Chrome Extension Bridge - Trigger recording via CDP
    └── Video Manager - Track saved recordings
    ↓
Python Orchestrator / N8n Workflow
    ├── FFmpeg Service (Port 8002) - Extract audio from .avi → .wav
    ├── Transcription Service (Port 8003) - Whisper STT + pyannote diarization
    └── Claude API (External) - Generate summary and protocol

Data Flow: Email → Browser Join → Record → ./data/input/ → audio/ → transcripts/ → results/
```

### Technology Stack
- **Docker + Docker Compose**: Service containerization
- **FastAPI**: REST API for each microservice
- **Python 3.10**: Core language for all services
- **Playwright for Python**: Browser automation for meeting auto-join
- **Chrome Extension**: Browser-based video recording (MyRecV)
- **IMAPClient**: Email monitoring for meeting invitations
- **APScheduler**: Meeting scheduling and automation
- **FFmpeg**: Audio extraction (16kHz mono PCM WAV)
- **Faster-Whisper**: Optimized speech-to-text (4x faster than vanilla Whisper)
- **pyannote.audio**: Speaker diarization with temporal segmentation
- **SpeechBrain**: Speaker recognition with ECAPA-TDNN embeddings (optional)
- **Claude API**: Document generation (summary.md, protocol.md)
- **N8n**: Visual workflow orchestration (already installed on host)

### Data Pipeline

**Automated Meeting Capture Flow**:
1. Meeting invitation arrives in monitored email folder
2. Meeting Auto Capture parses invitation → saves full email body + details to JSON
3. At scheduled time (2 min before start), browser launches with platform-specific handler
4. Chrome extension triggered via CDP → starts recording
5. At meeting end (+buffer), recording stops → video saved to `data/input/`
6. Existing orchestrator detects new video → processes automatically

**Manual/Chrome Extension Recording Flow**:
1. User records meeting via Chrome extension → saves to `data/input/`
2. `watch_input_folder.py` detects new video file
3. `orchestrator.py` orchestrates full pipeline

**Processing Pipeline** (Common for both flows):
1. FFmpeg extracts audio → `/data/audio/{uuid}.wav`
2. Transcription service processes:
   - Whisper transcribes speech → text segments with timestamps
   - pyannote identifies speakers → (start, end, speaker_id) tuples
   - Merge transcription + diarization → structured JSON with generic labels (SPEAKER_00, SPEAKER_01, etc.)
3. **Speaker Recognition (optional)**: Identifies known speakers by voice
   - Loads enrolled speaker profiles from `data/speaker_profiles/`
   - Generates voice embeddings using SpeechBrain ECAPA-TDNN
   - Matches speakers using cosine similarity
   - Replaces generic labels with real names (SPEAKER_00 → "Иван Петров")
4. Claude API generates summary and protocol documents (with real speaker names if recognized)
5. Save final documents to `/data/results/`
6. Email protocol to sender (if `_mmmail(email)_` in filename)

## Development Commands

### Docker Operations
```bash
# Build specific service
docker-compose build ffmpeg-service
docker-compose build transcription-service

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f [service_name]

# Check service status
docker-compose ps

# Restart service after code changes
docker-compose restart [service_name]

# Stop all services
docker-compose down

# Clean rebuild (no cache)
docker-compose build --no-cache [service_name]
```

### Testing Services
```bash
# Health checks
curl http://localhost:8002/health  # FFmpeg service
curl http://localhost:8003/health  # Transcription service
curl http://localhost:8004/health  # Meeting Auto Capture (if API enabled)

# API documentation (FastAPI auto-docs)
# Open in browser:
http://localhost:8002/docs  # FFmpeg Swagger UI
http://localhost:8003/docs  # Transcription Swagger UI
http://localhost:8004/docs  # Meeting Auto Capture Swagger UI (if enabled)

# Test FFmpeg extraction
curl -X POST "http://localhost:8002/extract-audio" -F "file=@test.avi"

# Test transcription with speakers
curl -X POST "http://localhost:8003/transcribe-with-speakers" -F "file=@audio.wav"

# Test Meeting Auto Capture (if API enabled)
curl http://localhost:8004/meetings                    # List all meetings
curl http://localhost:8004/meetings/{meeting-id}       # Get specific meeting
curl -X POST http://localhost:8004/meetings/{id}/join  # Manually trigger join

# Run Python test scripts
python scripts/test_ffmpeg.py
python scripts/test_transcription.py
python scripts/test_full_pipeline.py  # E2E test
```

### Environment Setup
```bash
# Install Python dependencies for scripts
pip install -r requirements.txt

# Download test audio (if script exists)
python scripts/download_test_audio.py

# Setup virtual environment (Windows)
python -m venv venv
venv\Scripts\activate

# Meeting Auto Capture - Standalone Setup

# Option 1: Use root-level launcher (Windows, recommended)
start_meeting-autocapture.bat

# Option 2: Direct setup and start
cd services/meeting-autocapture
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
cp config/.env.example .env
# Edit .env with your credentials
python src/main.py  # Run the service
```

## Speaker Recognition Setup

The speaker recognition feature identifies known speakers in meetings by matching their voice characteristics. When enabled, generic labels (SPEAKER_00, SPEAKER_01) are replaced with real names in transcripts, summaries, and protocols.

### Prerequisites

1. **Install dependencies** (if not already done):
```bash
pip install -r services/transcription_orchestrator/requirements.txt
```

2. **Enable speaker recognition** in `.env`:
```env
ENABLE_SPEAKER_RECOGNITION=true
RECOGNITION_THRESHOLD=0.75
SPEAKER_PROFILES_PATH=./data/speaker_profiles
```

### Enrolling Speakers

#### Step 1: Prepare Audio Samples

Extract 3-5 clean speech samples (5-10 seconds each) from previous meetings:

```bash
# Interactive extraction tool
python tools/extract_speaker_samples.py --interactive

# Or extract manually with ffmpeg
ffmpeg -i meeting.wav -ss 00:05:30 -t 7 -ar 16000 -ac 1 sample_01.wav
```

#### Step 2: Initialize Speaker Database

```bash
# Create speakers.json (first time only)
python services/transcription_orchestrator/manage_speakers.py --init
```

#### Step 3: Add Speaker

```bash
python services/transcription_orchestrator/manage_speakers.py \
    --add ivan_petrov \
    --name "Иван Петров" \
    --samples "ivan_petrov/sample_01.wav,ivan_petrov/sample_02.wav,ivan_petrov/sample_03.wav" \
    --role "Project Manager" \
    --department "Engineering"
```

#### Step 4: Validate Profiles

```bash
python services/transcription_orchestrator/manage_speakers.py --validate
```

### Managing Speaker Profiles

```bash
# List all enrolled speakers
python services/transcription_orchestrator/manage_speakers.py --list

# Remove a speaker
python services/transcription_orchestrator/manage_speakers.py --remove ivan_petrov

# Validate speakers.json
python services/transcription_orchestrator/manage_speakers.py --validate
```

### Testing Speaker Recognition

```bash
# Test recognition system
python services/transcription_orchestrator/recognize.py

# Process a meeting with recognition enabled
python services/transcription_orchestrator/orchestrator.py data/input/test_meeting.avi
```

### Configuration Options

- **ENABLE_SPEAKER_RECOGNITION**: Enable/disable feature (default: `false`)
- **RECOGNITION_THRESHOLD**: Confidence threshold 0.0-1.0 (default: `0.75`)
  - **0.65**: Lenient (more recognitions, possible false positives)
  - **0.75**: Balanced (recommended)
  - **0.85**: Strict (fewer false positives, more unrecognized)
- **SPEAKER_RECOGNITION_DEVICE**: Device for recognition inference (default: falls back to `DEVICE`)
  - **cpu**: CPU processing (slower but works everywhere)
  - **cuda**: GPU processing (3-4x faster, requires CUDA-capable GPU)
- **SPEAKER_PROFILES_PATH**: Path to speaker profiles directory

### Troubleshooting

**Low Recognition Accuracy**:
- Add more audio samples (5-7 samples per speaker)
- Use cleaner audio with minimal background noise
- Ensure samples contain only one speaker

**False Positives** (wrong names assigned):
- Increase `RECOGNITION_THRESHOLD` to 0.80 or 0.85
- Add more diverse samples to improve speaker discrimination

**No Speakers Recognized**:
- Check that `ENABLE_SPEAKER_RECOGNITION=true`
- Verify `speakers.json` exists and is valid
- Lower threshold to 0.65 or 0.70
- Check orchestrator logs for error messages

**Performance**:
- First run downloads SpeechBrain model (~500MB)
- Embeddings are cached for faster subsequent runs
- Recognition adds ~5-10 minutes for 1-hour meeting (CPU)
- Use `DEVICE=cuda` for 3-4x faster processing (requires GPU)

### File Structure

```
data/speaker_profiles/
├── speakers.json              # Speaker database
├── embeddings/                # Cached embeddings (.npy files)
│   ├── ivan_petrov_embed.npy
│   └── maria_ivanova_embed.npy
├── ivan_petrov/              # Audio samples
│   ├── sample_01.wav
│   ├── sample_02.wav
│   └── sample_03.wav
└── maria_ivanova/
    ├── sample_01.wav
    ├── sample_02.wav
    └── sample_03.wav
```

## RAG Search with RAGFlow

The RAG (Retrieval Augmented Generation) system enables semantic search across all processed meetings using natural language queries. After transcription completes, meetings are automatically indexed in RAGFlow with contextual enrichment, allowing Claude to answer questions like "What did we discuss about project GPB on March 9?" or "Which video file contains discussion about invoices?"

### Architecture

**Stack Components**:
- **RAGFlow**: Open-source RAG framework (UI + orchestration)
- **DeepDoc Engine**: Document parsing with structure extraction (built into RAGFlow)
- **BGE-M3**: Multilingual embedding model (dense + sparse hybrid retrieval)
- **Infinity**: High-performance vector database with HNSW indexing
- **bge-reranker-v2-m3**: Two-stage retrieval reranking (top-20 → top-5)
- **Claude Sonnet 4.5**: LLM for answer generation
- **Contextual Retrieval**: Anthropic's technique - adds meeting context to chunks before embedding (+30% accuracy)

**Data Flow**:
```
Orchestrator completes → Contextual enrichment (Claude API generates context)
    → Upload to RAGFlow → DeepDoc parsing → BGE-M3 embedding
    → Infinity storage → User query → Hybrid retrieval → Reranking
    → Claude generation with citations
```

### Quick Start

#### Step 1: Deploy RAGFlow Stack

```bash
# Start RAGFlow services (RAGFlow, MySQL, Redis, Infinity)
cd services/RAG-search
docker-compose -f docker-compose.ragflow.yml up -d

# Check services are running
docker-compose -f docker-compose.ragflow.yml ps

# View logs
docker-compose -f docker-compose.ragflow.yml logs -f ragflow
```

#### Step 2: Configure RAGFlow UI

1. **Access RAGFlow UI**: Open http://localhost:9380 in browser
2. **Login**: Default credentials `admin` / `admin` (change on first login)
3. **Configure Embedding Model**:
   - Go to Settings → Models → Embedding
   - Select `BAAI/bge-m3` (should already be set via environment)
4. **Configure Vector Engine**:
   - Settings → Storage → Vector Engine
   - Select `Infinity` (should already be set)
5. **Configure Reranker**:
   - Settings → Models → Reranker
   - Select `BAAI/bge-reranker-v2-m3`
6. **Configure LLM**:
   - Settings → Models → LLM
   - Add Claude API key (uses `CLAUDE_API_KEY` from .env)
   - Select `claude-sonnet-4-5-20250929`
7. **Generate API Key**:
   - Settings → API Keys → Create New Key
   - Copy the generated key
   - Add to `.env`: `RAGFLOW_API_KEY=your-key-here`

#### Step 3: Enable Automatic Indexing

Edit root `.env` file:

```env
# Enable RAG indexing
ENABLE_RAG_INDEXING=true

# RAGFlow service URL (default)
RAGFLOW_URL=http://localhost:9380

# API key from Step 2
RAGFLOW_API_KEY=your-ragflow-api-key

# Contextual Retrieval (Anthropic technique)
ENABLE_CONTEXTUAL_RETRIEVAL=true
CONTEXT_GENERATION_MODEL=claude-sonnet-4-5-20250929
```

#### Step 4: Process Meetings

Now when orchestrator processes meetings, they'll automatically upload to RAGFlow:

```bash
# Process a meeting (manual trigger)
python services/transcription_orchestrator/orchestrator.py data/input/meeting_2025-01-15.avi

# Or use auto-processing (watch_input_folder.py)
# Just place video files in data/input/ folder
```

**What happens during upload**:
1. **Contextual Enrichment**: Claude API generates context for each chunk
   - Example context: "Встреча: GPB проект - обсуждение счетов, Дата: 2025-03-09, Участники: Иван Петров, Мария Иванова"
2. **Upload to RAGFlow**: Creates dataset, uploads transcript/summary/protocol
3. **Parsing & Chunking**: DeepDoc extracts structure, chunks documents
4. **Embedding**: BGE-M3 generates dense + sparse vectors
5. **Indexing**: Infinity stores vectors with HNSW index
6. **Metadata Update**: `metadata.json` updated with `rag_indexed=true`, `ragflow_dataset_id`

### Querying Meetings

#### Via RAGFlow UI

1. **Open RAGFlow UI**: http://localhost:9380
2. **Select Dataset**: Choose specific meeting or "All Datasets"
3. **Chat Interface**: Ask questions in natural language (Russian or English)

**Example Queries**:
```
- "Что обсудили по проекту GPB 9 марта?"
- "Какие решения приняли на встрече с партнерами?"
- "Кто отвечает за расчеты до 15 марта?"
- "В каком видео обсуждали счета?"
- "What were the action items from the last meeting?"
```

**Response includes**:
- Generated answer based on retrieved context
- Source citations (meeting name, document type, timestamp)
- Relevance scores

#### Via Python API

```python
from pathlib import Path
import sys
sys.path.append(str(Path("services/RAG-search/scripts")))

from ragflow_client import RAGFlowClient

# Initialize client
client = RAGFlowClient()

# Search specific dataset
results = client.search(
    dataset_id="meeting_20250309_143022",
    query="Что обсудили по проекту GPB?",
    top_k=5,
    similarity_threshold=0.7
)

for result in results:
    print(f"Score: {result['score']}")
    print(f"Text: {result['content']}")
    print(f"Source: {result['metadata']['source']}")
    print("---")

# Chat with Claude (retrieval + generation)
answer = client.chat(
    question="Что обсудили по проекту GPB 9 марта?",
    dataset_ids=["all"],  # or specific meeting IDs
    top_k=5
)

print(answer)
```

#### Via Claude Code Agent

Claude Code can query RAGFlow directly:

```python
# In your agent code
from ragflow_client import RAGFlowClient

client = RAGFlowClient()
answer = client.chat(
    question="What did we discuss about GPB project invoices?",
    dataset_ids=["all"]
)
```

### Configuration Options

**Environment Variables** (`.env`):

- **ENABLE_RAG_INDEXING**: Enable/disable automatic indexing (default: `false`)
- **RAGFLOW_URL**: RAGFlow service URL (default: `http://localhost:9380`)
- **RAGFLOW_API_KEY**: API key from RAGFlow UI (required for indexing)
- **ENABLE_CONTEXTUAL_RETRIEVAL**: Enable Anthropic's Contextual Retrieval technique (default: `true`)
  - When enabled: Adds meeting context to each chunk before embedding
  - When disabled: Uses original chunks without context
  - Recommended: Keep enabled for +30% retrieval accuracy
- **CONTEXT_GENERATION_MODEL**: Claude model for context generation (default: `claude-sonnet-4-5-20250929`)

**Contextual Retrieval Explained**:

Traditional RAG embeds chunks in isolation, losing document context. Contextual Retrieval prepends context to each chunk:

*Without Context*:
- Chunk: "Иван согласился завершить расчеты до 15 марта"
- Poor retrieval: Doesn't know which meeting, project, or context

*With Context (Anthropic Technique)*:
- Context: "Встреча: GPB проект - обсуждение счетов, Дата: 2025-03-09, Участники: Иван Петров, Мария Иванова"
- Chunk: "Иван согласился завершить расчеты до 15 марта"
- **Combined for embedding**: "{context}\n\n{chunk}"
- Better retrieval: Knows meeting context, can filter by date/participants

**Benefits**:
- +30% retrieval accuracy (Anthropic benchmark)
- Better cross-meeting queries
- Implicit metadata filtering through semantic search

### Managing Datasets

```bash
# List all indexed meetings
python services/RAG-search/scripts/ragflow_client.py

# Delete a specific dataset (meeting)
from ragflow_client import RAGFlowClient
client = RAGFlowClient()
client.delete_dataset("meeting_20250309_143022")

# Check RAGFlow health
client.health_check()  # Returns True if accessible
```

### File Structure

```
services/RAG-search/
├── docker-compose.ragflow.yml       # RAGFlow stack deployment
├── Meeting_rag.md                   # Comprehensive implementation plan
├── README.md                        # Quick start guide
├── .env.example                     # Configuration template
├── scripts/
│   ├── contextual_enrichment.py     # Contextual Retrieval implementation
│   ├── ragflow_client.py            # RAGFlow API wrapper
│   └── ragflow_uploader.py          # Main upload script (called by orchestrator)
└── config/
    └── prompts/
        └── context_generation.txt   # Claude prompt for context generation
```

**Meeting Metadata** (stored in RAGFlow):

```json
{
  "meeting_id": "uuid",
  "meeting_title": "GPB - Обсуждение счетов - 2025-03-09",
  "meeting_date": "2025-03-09",
  "video_filename": "meeting_20250309_143022.avi",
  "result_folder": "data/results/meeting_20250309_143022",
  "duration_seconds": 3467.5,
  "num_speakers": 3,
  "recognized_speakers": ["Иван Петров", "Мария Иванова"],
  "rag_indexed": true,
  "ragflow_dataset_id": "dataset-abc123",
  "contextual_enrichment_applied": true
}
```

### Troubleshooting

**RAGFlow not accessible**:
- Verify Docker containers are running: `docker-compose -f docker-compose.ragflow.yml ps`
- Check logs: `docker-compose -f docker-compose.ragflow.yml logs -f ragflow`
- Verify port 9380 is not in use by another application
- Wait ~30 seconds after startup for RAGFlow to initialize

**Upload fails with "RAGFlow API is not accessible"**:
- Start RAGFlow: `cd services/RAG-search && docker-compose -f docker-compose.ragflow.yml up -d`
- Wait for startup (check `docker-compose logs -f ragflow` for "Server started")
- Verify `RAGFLOW_URL=http://localhost:9380` in `.env`

**Upload fails with "RAGFLOW_API_KEY not set"**:
- Generate API key in RAGFlow UI: Settings → API Keys → Create New Key
- Add to `.env`: `RAGFLOW_API_KEY=your-key-here`
- No need to restart orchestrator (reads .env on each run)

**Contextual enrichment fails**:
- Verify `CLAUDE_API_KEY` is set in `.env`
- Check Claude API quota/rate limits
- If enrichment fails, system falls back to original files without context (with warning)

**Poor retrieval quality**:
- Enable Contextual Retrieval: `ENABLE_CONTEXTUAL_RETRIEVAL=true`
- Verify reranker is configured in RAGFlow UI (Settings → Models → Reranker)
- Adjust similarity threshold in search (lower = more results, higher = more precise)
- Try different query phrasing (natural language works best)

**Slow indexing**:
- Contextual enrichment calls Claude API for each chunk (~50-200 chunks per meeting)
- Expected: 2-5 minutes per meeting with enrichment enabled
- Disable for faster indexing: `ENABLE_CONTEXTUAL_RETRIEVAL=false` (not recommended)

**Meeting not found in RAGFlow**:
- Check `metadata.json` in result folder: `rag_indexed` should be `true`
- Check orchestrator logs for upload errors
- Verify `ENABLE_RAG_INDEXING=true` in `.env`
- Manually trigger upload: `python services/RAG-search/scripts/ragflow_uploader.py data/results/meeting_folder`

**Docker containers consuming too much resources**:
- RAGFlow stack requires ~4GB RAM minimum
- BGE-M3 embedding model: ~2GB disk space (first run download)
- Infinity vector engine: CPU mode works, GPU optional
- Adjust Docker Desktop memory limit: Settings → Resources → Memory

### Performance Expectations

**Indexing Performance**:
- **With Contextual Enrichment** (recommended):
  - 1-hour meeting (~100 chunks): 3-5 minutes
  - Includes Claude API calls for context generation
  - One-time cost per meeting
- **Without Contextual Enrichment**:
  - 1-hour meeting: 30-60 seconds
  - No Claude API calls
  - Lower retrieval accuracy

**Query Performance**:
- **Search query**: 200-500ms (depends on dataset size)
- **Chat query** (retrieval + generation): 2-5 seconds
  - Includes vector search, reranking, Claude generation
- **Reranking overhead**: ~100-200ms (improves precision significantly)

**Storage**:
- **Vector database**: ~5-10MB per hour of meeting transcription
- **Original documents**: ~100-500KB per meeting (transcript, summary, protocol)
- **Enriched documents** (with context): ~150-700KB per meeting

### Best Practices

1. **Keep Contextual Retrieval Enabled**: +30% accuracy improvement is significant
2. **Use Specific Queries**: "What did we discuss about GPB invoices on March 9?" works better than "Tell me about GPB"
3. **Query in Russian**: BGE-M3 is multilingual, but Russian queries work best for Russian transcripts
4. **Monitor disk space**: RAGFlow stores vectors on disk, plan for ~10MB per meeting hour
5. **Regular backups**: Backup `services/RAG-search/ragflow_data/` for persistence
6. **API rate limits**: Contextual enrichment uses Claude API, monitor quota if processing many meetings

## Implementation Guidelines

### Service Implementation Order
Follow this sequence per `meeting_transcriber_plan.md`:

1. **Phase 1 - FFmpeg Service** (`services/ffmpeg/`)
   - Create `Dockerfile` with `python:3.10-slim` base + ffmpeg installation
   - `requirements.txt`: fastapi, uvicorn[standard], python-multipart, aiofiles
   - `app.py`: FastAPI with POST `/extract-audio` and GET `/health`
   - FFmpeg command: `ffmpeg -i input.avi -vn -acodec pcm_s16le -ar 16000 -ac 1 output.wav`

2. **Phase 2 - Transcription Service** (`services/transcription/`)
   - Create `Dockerfile` with torch, faster-whisper, pyannote.audio dependencies
   - `requirements.txt`: fastapi, uvicorn, faster-whisper, pyannote.audio, torch, pydantic
   - `app.py`: FastAPI with `/transcribe`, `/diarize`, `/transcribe-with-speakers`, `/health`, `/models/info`
   - `transcribe.py`: WhisperTranscriber class for STT
   - `diarize.py`: SpeakerDiarizer class + merge_transcription_diarization() function
   - Mount `/app/models` volume for model caching to avoid re-downloading

3. **Phase 3 - N8n Workflow** (`n8n-workflows/`)
   - Create `meeting-pipeline.json` with webhook trigger
   - Sequential HTTP requests: FFmpeg → Transcription → Claude API (2x)
   - Use prompts from `project_description.md` lines 398-439
   - Save outputs to `/data/results/`

4. **Phase 4 - Testing**
   - Unit tests in `tests/` directory
   - Integration test script `scripts/test_full_pipeline.py`
   - Use short test videos (2-3 minutes) for fast iteration

5. **Phase 5 - Meeting Auto Capture** (`services/meeting-autocapture/`)
   - **Python-based standalone service** (consistent with project tech stack)
   - `requirements.txt`: playwright, imapclient, icalendar, APScheduler, fastapi, pydantic
   - `src/main.py`: Main entry point with background threads for email monitoring and scheduling
   - `src/email_monitor.py`: IMAP email monitoring class
   - `src/meeting_parser.py`: Parse email body + .ics attachments, save **full email body to JSON**
   - `src/scheduler.py`: APScheduler-based meeting scheduling
   - `src/browser_joiner.py`: Playwright browser automation with persistent profiles
   - `src/extension_bridge.py`: CDP communication to trigger Chrome extension recording
   - `src/platform_handlers/`: Platform-specific join logic (gpb.video, psbank, zoom, webex, google meet, telemost)
   - `config/meeting_patterns.json`: URL regex patterns for platform detection
   - `data/meetings/`: JSON storage (pending/in_progress/completed)
   - Can run standalone or dockerized for production

### Critical Implementation Details

**Meeting Auto Capture Service**:
- **Email body preservation**: MUST save complete email body (HTML + plain text) to JSON for later stages
- **Platform priorities**: Implement gpb.video (priority 1) and meeting.psbank.ru (priority 2) first
- **Browser profiles**: Persistent Chrome profiles per platform (`data/browser_profiles/{platform}/`)
- **First-time setup**: Manual login to each platform required once, then auto-join works
- **CDP communication**: Extension must listen for external messages (`chrome.runtime.onMessage`)
- **Filename pattern**: Videos must include `_mmmail(sender@email.com)_` for auto-email delivery
- **Scheduling**: Join 2 minutes before meeting start (configurable via MAC_PRE_MEETING_JOIN_MINUTES)
- **Integration**: Extension saves to `data/input/` → watch_input_folder.py detects → orchestrator.py processes
- **Supported platforms**: gpb.video, meeting.psbank.ru, Zoom, Webex, Google Meet, Telemost Yandex, custom
- **Run modes**: Standalone Python script (development) or Docker container (production)

**Transcription Service Complexity**:
- First run downloads models (5-10 minutes) - cache in `./models/` volume
- pyannote.audio requires HuggingFace token (HF_TOKEN env var)
- Must accept pyannote license: https://huggingface.co/pyannote/speaker-diarization
- Whisper model size affects speed/quality: `tiny < base < small < medium < large`
- CPU mode works but slow (1 hour video = 30-60 min processing)
- GPU mode (CUDA) much faster (1 hour video = 3-7 min processing)

**Expected JSON Output Format**:
```json
{
  "metadata": {
    "filename": "meeting_2025-01-15.avi",
    "duration_seconds": 3600,
    "num_speakers": 3,
    "language": "ru",
    "processed_at": "2025-01-15T14:30:00Z"
  },
  "transcript": [
    {
      "speaker": "SPEAKER_00",
      "start": 0.5,
      "end": 3.2,
      "text": "Добрый день, коллеги"
    }
  ]
}
```

**Windows-Specific Considerations**:
- Use absolute paths with forward slashes: `C:/Users/Username/meeting-transcriber/data`
- Docker Desktop must have file sharing enabled for project directory
- WSL2 required for GPU support (NVIDIA CUDA)
- Check Docker Desktop Settings → Resources → File Sharing

### Code Quality Standards

**FastAPI Services**:
- Use async/await for I/O operations (file uploads, model inference where supported)
- Implement comprehensive error handling with proper HTTP status codes
- Add structured logging (consider `structlog` for JSON logs)
- Include type hints for all function parameters and returns
- Add detailed docstrings following Google/NumPy style
- Use Pydantic models for request/response validation

**Docker Best Practices**:
- Multi-stage builds to minimize image size
- Pin dependency versions in requirements.txt
- Cache model downloads in persistent volumes
- Set appropriate healthcheck intervals (transcription service needs longer start_period)
- Use environment variables for configuration

**Testing Approach**:
- TDD (test-driven development) recommended
- Start with unit tests for individual functions
- Mock external dependencies (Claude API) in tests
- Use short audio samples (30 sec) for fast test execution
- Add E2E test that validates entire pipeline

## Environment Variables

Required in `.env` file (create from `.env.example`):

```env
# API Keys (NEVER commit to git)
CLAUDE_API_KEY=sk-ant-xxxxx           # Anthropic Claude API key
HF_TOKEN=hf_xxxxx                      # HuggingFace token for pyannote

# Model Configuration
WHISPER_MODEL=medium                   # Options: tiny/base/small/medium/large-v2
DEVICE=cpu                             # cpu or cuda (requires GPU setup)
LANGUAGE=ru                            # Primary language for transcription

# Speaker Recognition (Optional)
ENABLE_SPEAKER_RECOGNITION=false       # Enable speaker identification by voice
RECOGNITION_THRESHOLD=0.75             # Confidence threshold (0.65=lenient, 0.75=balanced, 0.85=strict)
SPEAKER_RECOGNITION_DEVICE=cpu         # Device for recognition (cpu/cuda, falls back to DEVICE if not set)
SPEAKER_PROFILES_PATH=./data/speaker_profiles  # Path to speaker profiles

# Diarization Configuration
USE_NEW_DIARIZATION_ARCHITECTURE=true  # true=full file (accurate, slow), false=chunks (fast, duplicates)
CHUNK_DURATION_SEC=1800                # Chunk duration in seconds (default: 1800 = 30 min)
DIARIZATION_MIN_SPEAKERS=1             # Minimum speakers for auto-detection
DIARIZATION_MAX_SPEAKERS=10            # Maximum speakers for auto-detection
# DIARIZATION_NUM_SPEAKERS=3           # Exact number (if known, uncomment to use)

# Meeting Auto Capture - Email Settings
MAC_IMAP_HOST=imap.gmail.com
MAC_IMAP_PORT=993
MAC_IMAP_USER=your-email@gmail.com
MAC_IMAP_PASSWORD=your-app-password
MAC_IMAP_FOLDER=Meetings              # Folder to monitor
MAC_IMAP_CHECK_INTERVAL=60            # Check every N seconds

# Meeting Auto Capture - Browser Settings
MAC_CHROME_EXTENSION_PATH=./chrome-extension
MAC_BROWSER_PROFILES_PATH=./services/meeting-autocapture/data/browser_profiles
MAC_PRE_MEETING_JOIN_MINUTES=2        # Join N minutes before start
MAC_POST_MEETING_BUFFER_MINUTES=5     # Record N minutes after end

# Meeting Auto Capture - Video Storage
MAC_VIDEO_OUTPUT_FOLDER=./data/input
MAC_ENABLE_AUTO_PROCESSING=true       # Trigger orchestrator automatically

# Meeting Auto Capture - API (Optional)
MAC_API_PORT=8004
MAC_LOG_LEVEL=info
MAC_ENABLE_API=false                  # Enable FastAPI server

# Email Delivery (Optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Database (optional, for future features)
POSTGRES_PASSWORD=secure_password

# Paths (use forward slashes on Windows)
DATA_PATH=./data
MODELS_PATH=./models
```

## Troubleshooting

**First-time model download takes long**:
- Whisper medium model: ~1.5GB
- pyannote models: ~50MB
- Total: ~2GB, one-time download cached in `./models/`

**pyannote authentication error**:
- Verify HF_TOKEN is set in .env
- Accept model license at https://huggingface.co/pyannote/speaker-diarization
- Restart transcription service after setting token

**Out of memory errors**:
- Reduce Whisper model size: `WHISPER_MODEL=base` or `small`
- Increase Docker Desktop memory limit (Settings → Resources)
- Process long videos in chunks (future enhancement)

**FFmpeg service not starting**:
- Check `./data/` directory exists and has write permissions
- Review logs: `docker-compose logs ffmpeg-service`

**Slow transcription performance**:
- CPU mode expected: Real-time factor ~0.5-1.0 (1h video = 30-60min)
- For faster processing: Enable GPU support (requires WSL2 + NVIDIA CUDA on Windows)
- Alternatively use smaller model: `WHISPER_MODEL=base` (faster but less accurate)

**Slow diarization (speaker identification) performance**:
- **Quick fix (use chunked processing)**:
  - Set `USE_NEW_DIARIZATION_ARCHITECTURE=false` in `.env`
  - Set `CHUNK_DURATION_SEC=900` (15 min) or `600` (10 min) for faster processing
  - **Trade-off**: May create speaker duplicates (SPEAKER_00 in chunk 1 ≠ SPEAKER_00 in chunk 2)
  - **Solution**: Use speaker recognition to fix duplicates afterward
  - Restart orchestrator script (no Docker restart needed)
- **Best solution (enable GPU)**:
  - Set `DEVICE=cuda` in `.env`
  - Restart Docker: `docker-compose restart transcription-service`
  - 3-4x faster diarization on full files
- **Understanding the architectures**:
  - **NEW** (`USE_NEW_DIARIZATION_ARCHITECTURE=true`): Processes entire audio file for diarization → Slow but accurate speaker labels
  - **OLD** (`USE_NEW_DIARIZATION_ARCHITECTURE=false`): Processes audio in chunks → Fast but may create duplicate speaker labels between chunks

**Claude API rate limits**:
- Default tier has per-minute request limits
- Add retry logic with exponential backoff in N8n workflow
- Consider tier upgrade for production use

**Meeting Auto Capture issues**:
- **IMAP connection fails**: Check app password (not regular password), enable "Less secure app access" or use app-specific password
- **Browser not launching**: Run `playwright install chromium` and verify MAC_CHROME_EXTENSION_PATH is correct
- **Extension not loading**: Check extension path is absolute, manifest.json is valid
- **Recording not starting**: Verify CDP communication, check extension background service worker logs
- **Meeting not joining**: Check platform-specific selectors, may need updates if platform UI changed
- **Browser profile locked**: Close any existing Chrome instances using the same profile
- **Video file not detected**: Verify MAC_VIDEO_OUTPUT_FOLDER matches extension save location
- **Email not parsed**: Check .ics attachment format, may need additional parsing patterns

## Project Status

**Current Phase**: Planning complete, no implementation yet
- ✅ Architecture documented
- ✅ Docker Compose configuration ready
- ✅ Development plan established
- ⏳ Services not yet implemented
- ⏳ N8n workflow not created
- ⏳ Tests not written

**Next Steps**:
1. Create FFmpeg service (Dockerfile, app.py, requirements.txt)
2. Create Transcription service (more complex: multiple files, model loading)
3. Build and test services independently
4. Create N8n workflow with proper Claude prompts
5. Run E2E test with short sample video
6. Iterate on prompt quality and diarization accuracy

## Reference Documentation

- Project Description: `project_description.md` (comprehensive technical spec)
- Development Plan: `meeting_transcriber_plan.md` (step-by-step implementation guide)
- **Meeting Auto Capture Plan**: `MeetingAutoCapture_plan.md` (automated meeting capture system)
- **RAG Search Plan**: `services/RAG-search/Meeting_rag.md` (RAGFlow + Contextual Retrieval implementation)
- Claude Code Guide: `claude_code_guide.md` (prompt examples for building with Claude)
- Docker Config: `docker_compose_config.yaml` (service definitions)

## Performance Expectations

**CPU Mode (Intel i7)**:
- 1 hour video → 30-60 minutes total processing
  - Whisper: ~25-40 min
  - Diarization: ~5-15 min
  - Claude: ~2-5 min

**GPU Mode (NVIDIA RTX 3060)**:
- 1 hour video → 8-15 minutes total processing
  - Whisper: ~3-7 min
  - Diarization: ~3-5 min
  - Claude: ~2-5 min

**Quality Targets**:
- Word Error Rate (WER): <15% for Russian language
- Diarization Error Rate (DER): <20%
- Real-time factor: <0.3 (with GPU)
