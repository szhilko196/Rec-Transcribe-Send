# Meeting Auto Capture

Automated meeting capture service that monitors email for meeting invitations, automatically joins meetings at scheduled time, records using ffmpeg screen capture (SD video + high quality audio), and saves videos for processing.

## Features

- 📧 **Email Monitoring**: IMAP monitoring for meeting invitations
- 📅 **Auto-Scheduling**: Automatically schedule meeting joins
- 🌐 **Browser Automation**: Playwright-based auto-join for 7+ platforms
- 🎥 **ffmpeg Screen Capture**: External screen + audio recording (WebM format, VP9+Opus)
- 🎬 **Quality Settings**: SD video (CRF 33, 15fps) + High audio (128kbps Opus)
- 💾 **Full Email Body**: Saves complete email content to JSON for later stages
- 🔄 **Pipeline Integration**: Auto-triggers existing transcription pipeline

## Supported Platforms

1. **gpb.video** (Priority 1)
2. **meeting.psbank.ru** (Priority 2)
3. **Zoom**
4. **Cisco Webex**
5. **Google Meet**
6. **Yandex Telemost**

## Architecture

```
Email Invitation
    ↓
Email Monitor (IMAP)
    ↓
Meeting Parser (saves full email body to JSON)
    ↓
Scheduler (APScheduler)
    ↓
Browser Joiner (Playwright automation)
    ↓
ffmpeg Screen Capture (VP9 video + Opus audio → WebM)
    ↓
Video Saved to data/input/
    ↓
Existing Pipeline (watch_input_folder.py → orchestrator.py)
```

## Installation

### 1. Create Virtual Environment

```bash
cd services/meeting-autocapture
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Playwright Browsers

```bash
playwright install chromium
```

### 4. Install ffmpeg

**Windows:**
```bash
# Download ffmpeg essentials build
curl -L "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -o ffmpeg.zip

# Extract to tools folder
mkdir C:\prj\Rec-Transcribe-Send\tools
tar -xf ffmpeg.zip -C C:\prj\Rec-Transcribe-Send\tools

# Verify installation
C:\prj\Rec-Transcribe-Send\tools\ffmpeg-8.0-essentials_build\bin\ffmpeg.exe -version
```

**Linux:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Note**: The `browser_joiner.py` is configured to use the Windows path by default. Update `self.ffmpeg_path` in the code if using a different path.

### 5. Configure Environment

```bash
# Copy example config
cp config/.env.example config/.env

# Edit config/.env with your credentials
notepad config/.env  # Windows
nano config/.env     # Linux
```

**Required Settings:**

```env
# Email Settings
MAC_IMAP_HOST=imap.gmail.com
MAC_IMAP_PORT=993
MAC_IMAP_USER=your-email@gmail.com
MAC_IMAP_PASSWORD=your-app-password  # Gmail App Password
MAC_IMAP_FOLDER=Meetings

# Browser Settings
MAC_BROWSER_PROFILES_PATH=./data/browser_profiles

# Video Storage (ffmpeg screen capture → WebM format)
MAC_VIDEO_OUTPUT_FOLDER=../../data/input
```

### 5. First-Time Setup: Browser Profiles

On first run, you'll need to manually log in to each meeting platform **once**:

```bash
# The service will create profile directories:
# data/browser_profiles/gpb_video/
# data/browser_profiles/psbank/
# data/browser_profiles/zoom/
# etc.

# After first manual login, subsequent meetings will auto-join
```

## Running the Service

### Standalone Mode (Development)

```bash
cd services/meeting-autocapture
venv\Scripts\activate  # Windows
python src/main.py
```

You should see:

```
============================================================
Meeting Auto Capture - Starting...
============================================================
✓ Video Manager initialized (output: ../../data/input)
✓ Browser Joiner initialized
✓ Scheduler initialized
✓ Meeting Parser initialized
✓ Email Monitor initialized
============================================================
Meeting Auto Capture is running!
============================================================
Press Ctrl+C to stop
```

### Docker Mode (Production)

```bash
# From project root
docker-compose build meeting-autocapture
docker-compose up -d meeting-autocapture

# View logs
docker-compose logs -f meeting-autocapture
```

## Usage

### 1. Email Setup

Create a dedicated folder in your email (e.g., "Meetings") and configure `MAC_IMAP_FOLDER`.

**Gmail Setup:**
- Enable IMAP: Settings → Forwarding and POP/IMAP → Enable IMAP
- Create App Password: Google Account → Security → 2-Step Verification → App Passwords
- Create "Meetings" label/folder
- Set up filter to auto-move meeting invitations to "Meetings" folder

### 2. Send/Forward Meeting Invitations

Forward meeting invitations to your monitored email folder. The service will:
1. Detect new email
2. Parse meeting details + **save full email body to JSON**
3. Extract meeting URL, time, participants
4. Schedule auto-join

### 3. Automatic Meeting Join

At scheduled time (2 minutes before by default):
1. Browser launches with platform-specific profile
2. Platform handler navigates and joins meeting
3. ffmpeg screen capture starts (VP9 + Opus → WebM)
4. Recording continues (SD video @ 15fps, high audio @ 128kbps)
5. Browser stays open until meeting ends (+5 min buffer)
6. ffmpeg stopped gracefully, WebM video finalized and saved

### 4. Video Processing

Video automatically saved to `data/input/` with naming pattern:
```
MEETING-{id}_{subject}_{datetime}_mmmail({sender-email})_.webm
```

Existing `watch_input_folder.py` detects it → `orchestrator.py` processes → sender gets protocol email.

## Configuration

### Timing Settings

```env
MAC_PRE_MEETING_JOIN_MINUTES=2   # Join 2 min before start
MAC_POST_MEETING_BUFFER_MINUTES=5  # Record 5 min after end
MAC_IMAP_CHECK_INTERVAL=60      # Check email every 60 seconds
```

### Platform Priorities

Edit `config/meeting_patterns.json` to adjust platform detection order:

```json
{
  "patterns": [
    {
      "name": "gpb.video",
      "regex": "gpb\\.video\\/[\\w\\-]+",
      "priority": 1
    }
  ]
}
```

Lower priority number = checked first.

## Data Storage

### Meeting JSONs

```
data/meetings/
├── pending/       # Scheduled meetings waiting to join
├── in_progress/   # Currently recording
└── completed/     # Finished meetings
```

**Example Meeting JSON:**

```json
{
  "id": "abc-123-def",
  "platform": "gpb.video",
  "meeting_link": "https://gpb.video/meeting123",
  "subject": "Q1 Review Meeting",
  "sender_email": "boss@company.com",
  "sender_name": "John Doe",
  "start_time": "2025-01-15T14:00:00",
  "end_time": "2025-01-15T15:00:00",
  "duration_minutes": 60,
  "status": "completed",
  "email_body_html": "<html>...</html>",
  "email_body_text": "Meeting details...",
  "video_file_path": "../../data/input/MEETING-abc-123-def_..."
}
```

### Browser Profiles

```
data/browser_profiles/
├── gpb_video/      # Persistent Chrome profile for gpb.video
├── psbank/         # Persistent Chrome profile for psbank
├── zoom/           # Persistent Chrome profile for Zoom
└── ...
```

## Troubleshooting

### IMAP Connection Failed

```
Error: Login credentials invalid
```

**Solution:**
- Use App Password (not regular password)
- Gmail: Enable "Less secure app access" or create App Password
- Outlook: Enable IMAP in settings

### Browser Not Launching

```
Error: Executable doesn't exist at /path/to/chromium
```

**Solution:**
```bash
playwright install chromium
```

### Recording Not Starting

```
Error: ffmpeg process failed to start
```

**Solution:**
- Verify ffmpeg is installed: `ffmpeg -version`
- Check ffmpeg path in `browser_joiner.py` (line ~42)
- Windows: Verify path `C:/prj/Rec-Transcribe-Send/tools/ffmpeg-8.0-essentials_build/bin/ffmpeg.exe`
- Verify `MAC_VIDEO_OUTPUT_FOLDER` has write permissions
- Check disk space is available
- Check audio device name: Run `ffmpeg -list_devices true -f dshow -i dummy` to list available audio devices
- Update audio device in `browser_joiner.py` if needed
- Check logs: `logs/autocapture.log`

### Meeting Not Joining

```
Error: Failed to join meeting
```

**Solution:**
- Platform UI may have changed (selectors need update)
- Check platform_handlers/{platform}.py
- Update selectors to match current page structure
- Use browser DevTools to find correct selectors

### Video File Not Detected / Corrupted

```
Warning: Video file not found or cannot be played
```

**Solution:**
- Verify `MAC_VIDEO_OUTPUT_FOLDER` path is correct
- Check ffmpeg process stopped gracefully (sends 'q' command to stdin)
- WebM file may be incomplete if ffmpeg crashed - check logs
- Verify video file exists: `ls -lh {output_folder}/*.webm`
- Test file playback: `ffprobe {video_path}` (should show VP9 + Opus streams)
- Check disk space during recording
- Verify disk permissions for output folder

## Testing

### Test Email Monitoring

```bash
cd src
python -c "
from email_monitor import EmailMonitor
config = {
    'host': 'imap.gmail.com',
    'port': 993,
    'username': 'your-email@gmail.com',
    'password': 'your-app-password',
    'folder': 'INBOX',
    'check_interval': 60
}
monitor = EmailMonitor(config)
client = monitor.connect()
print('✓ Connected to IMAP')
"
```

### Test Meeting Parser

Send yourself a test email with meeting link, then:

```bash
# Service will parse it automatically
# Check: data/meetings/pending/
ls data/meetings/pending/
```

### Test Browser Join (Manual)

Create a test meeting JSON in `data/meetings/pending/`, then start service.

## Development

### Project Structure

```
services/meeting-autocapture/
├── src/
│   ├── main.py                  # Entry point
│   ├── email_monitor.py         # IMAP monitoring
│   ├── meeting_parser.py        # Email → Meeting JSON
│   ├── scheduler.py             # APScheduler
│   ├── browser_joiner.py        # Playwright automation + ffmpeg screen capture
│   ├── video_manager.py         # Video tracking
│   ├── models.py                # Pydantic models
│   └── platform_handlers/
│       ├── base_handler.py
│       ├── gpb_video.py
│       ├── psbank_meeting.py
│       ├── zoom.py
│       ├── webex.py
│       ├── google_meet.py
│       └── telemost_yandex.py
├── config/
│   ├── meeting_patterns.json    # Platform detection
│   └── .env.example
├── data/
│   ├── meetings/
│   └── browser_profiles/
├── logs/
├── requirements.txt
├── test_auto.py                 # Automated test script
└── README.md
```

### Adding New Platform

1. Add pattern to `config/meeting_patterns.json`
2. Create handler: `src/platform_handlers/my_platform.py`
3. Extend `BasePlatformHandler`
4. Implement `join()` method
5. Register in `platform_handlers/__init__.py`

Example:

```python
from platform_handlers.base_handler import BasePlatformHandler

class MyPlatformHandler(BasePlatformHandler):
    def join(self, page, meeting):
        page.goto(meeting.meeting_link)
        page.fill('input[name="name"]', meeting.sender_name)
        page.click('button:has-text("Join")')
        return True
```

## Integration with Existing Pipeline

### File Naming Convention

Videos are automatically saved with this pattern:
```
{platform}_{timestamp}_mmmail({sender_email})_{meeting_id}.webm
```

Example: `telemost.yandex_20251115_232759_mmmail(user@example.com)_3b2bfe5c.webm`

This triggers:
1. `watch_input_folder.py` detects new video
2. `orchestrator.py` processes (transcribe + diarize + Claude protocol)
3. Email sent to `{sender_email}` with protocol (via `_mmmail()_` pattern)

### Workflow

```
Meeting Invitation Email
    ↓
Meeting Auto Capture (this service)
    ├── Parses email
    ├── Saves full body to JSON
    ├── Schedules join
    ├── Auto-joins meeting (Playwright)
    ├── Records screen + audio (ffmpeg → WebM)
    └── Saves video → data/input/
    ↓
Existing Pipeline
    ├── watch_input_folder.py (detects)
    ├── orchestrator.py (processes)
    ├── FFmpeg (audio extraction from WebM)
    ├── Whisper (transcription)
    ├── pyannote (diarization)
    ├── Claude API (protocol)
    └── SMTP (email results)
```

## Performance

- **Email Check**: Every 60 seconds (configurable)
- **Browser Launch**: ~3-5 seconds
- **Meeting Join**: ~5-10 seconds (platform-dependent)
- **Recording Start**: ~2-3 seconds (CDP)
- **Memory**: ~200-500 MB per browser instance
- **CPU**: Low (<5%) when idle, moderate during join

## Security

- **Credentials**: Stored in `.env` (not committed to git)
- **Browser Profiles**: Isolated per platform
- **Email Body**: Stored locally in JSON (confidential)
- **Video Files**: Saved locally, not uploaded anywhere
- **IMAP**: SSL/TLS connection

## Known Limitations

- **Manual Admission**: Meetings with waiting rooms may require host approval
- **CAPTCHAs**: Some platforms may show CAPTCHAs (not auto-solvable)
- **Platform Changes**: UI changes require handler updates
- **Concurrent Meetings**: Service handles one meeting at a time
- **Time Zones**: All times in UTC (ensure email parser handles timezone conversion)

## Future Enhancements

- [ ] Multi-meeting support (parallel browser instances)
- [ ] Web UI for monitoring
- [ ] Email notification on join failures
- [ ] Platform selector auto-update via ML
- [ ] Calendar API integration (Google Calendar, Outlook)
- [ ] Waiting room detection & retry
- [ ] Screenshot capture on errors

## License

Internal project - see main repository LICENSE

## Support

For issues or questions:
1. Check logs: `logs/autocapture.log`
2. Verify configuration: `.env` settings
3. Test components individually (see Testing section)
4. Review platform handler selectors
5. Check existing issues in repository

## Related Documentation

- Main Project: `../../CLAUDE.md`
- Implementation Plan: `../../MeetingAutoCapture_plan.md`
- ffmpeg Documentation: https://ffmpeg.org/documentation.html
- WebM Format: https://www.webmproject.org/
- Orchestrator: `../../scripts/orchestrator.py`

## Recent Updates

### v3.0 - ffmpeg Screen Capture (2025-11-16)

**Major Change**: Migrated from Playwright's built-in video recording to ffmpeg external screen capture.

**Benefits**:
- ✅ **Better Quality**: SD video (CRF 33) + High audio (128kbps Opus)
- ✅ **More Robust**: WebM format writes incrementally (no moov atom issues)
- ✅ **Better Compression**: VP9 codec more efficient than H.264
- ✅ **Superior Audio**: Opus codec at 128kbps (better than AAC)
- ✅ **No Recording Indicator**: Browser doesn't show "recording" badge on screen
- ✅ **Smaller Files**: Better compression = smaller file sizes

**Technical Details**:
- Video: VP9 codec, CRF 33 quality, 15 fps
- Audio: Opus codec, 128 kbps, 48kHz stereo
- Format: WebM (more robust than MP4 for live recording)
- Capture: Full desktop screen + audio via DirectShow (Windows)

**Configuration**:
- ffmpeg path: `C:/prj/Rec-Transcribe-Send/tools/ffmpeg-8.0-essentials_build/bin/ffmpeg.exe`
- Audio device: Configured in `browser_joiner.py` line 228
- Output format: `.webm` (VP9+Opus)

**Installation**: See section "4. Install ffmpeg" above.

**Testing**: Send test meeting invitation email to verify end-to-end flow.
