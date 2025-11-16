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
   - Merge transcription + diarization → structured JSON
3. Claude API generates summary and protocol documents
4. Save final documents to `/data/results/`
5. Email protocol to sender (if `_mmmail(email)_` in filename)

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
cd services/meeting-autocapture
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
cp config/.env.example .env
# Edit .env with your credentials
python src/main.py  # Run the service
```

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
