# Meeting Auto Capture - Quick Start Guide

Complete guide to get the Meeting Auto Capture service running.

## 📋 Prerequisites

- Python 3.10 or higher
- Windows 10/11 (or Linux/Mac with adjustments)
- Gmail/Outlook account with IMAP enabled
- ffmpeg 8.0 or higher (will be installed by setup.bat)

## 🚀 Quick Setup (Windows)

### Step 1: Run Setup Script

```bash
cd C:\prj\Rec-Transcribe-Send\services\meeting-autocapture
setup.bat
```

This will:
- ✅ Create virtual environment
- ✅ Install all Python dependencies
- ✅ Install Playwright Chromium browser
- ✅ Install ffmpeg for screen + audio capture
- ✅ Create data directories
- ✅ Generate config/.env from template
- ✅ Run installation tests

### Step 2: Configure Environment

Edit `config\.env` with your credentials:

```env
# Email Settings (REQUIRED)
MAC_IMAP_HOST=imap.gmail.com
MAC_IMAP_PORT=993
MAC_IMAP_USER=your-email@gmail.com
MAC_IMAP_PASSWORD=your-app-password        # Gmail App Password!
MAC_IMAP_FOLDER=Meetings

# Video Output (REQUIRED)
MAC_VIDEO_OUTPUT_FOLDER=../../data/input

# Timing (Optional)
MAC_PRE_MEETING_JOIN_MINUTES=2
MAC_POST_MEETING_BUFFER_MINUTES=5
MAC_IMAP_CHECK_INTERVAL=60
```

**Audio Device Configuration:**

After setup, configure your audio device in `src\browser_joiner.py` line 231:

1. List available audio devices:
   ```bash
   C:\prj\Rec-Transcribe-Send\tools\ffmpeg-8.0-essentials_build\bin\ffmpeg.exe -list_devices true -f dshow -i dummy
   ```

2. Update line 231 with your device name:
   ```python
   '-i', 'audio=YOUR DEVICE NAME HERE',
   ```

**Gmail App Password Setup:**
1. Go to Google Account → Security
2. Enable 2-Step Verification
3. App Passwords → Generate new password
4. Copy password to `MAC_IMAP_PASSWORD`

### Step 3: Verify ffmpeg Installation

Check that ffmpeg was installed correctly:

```bash
..\..\tools\ffmpeg-8.0-essentials_build\bin\ffmpeg.exe -version
```

Should show:
```
ffmpeg version 8.0-essentials_build
...
configuration: --enable-gpl --enable-version3 ...
libavcodec    61. 19.100
libavformat   61.  7.100
...
```

If not installed, run `setup.bat` again and select "Y" for automatic ffmpeg installation.

### Step 4: Test Installation

```bash
test.bat
```

Should show:
```
✓ PASS     Python Version
✓ PASS     Python Dependencies
✓ PASS     Playwright Browsers
✓ PASS     ffmpeg Installation
✓ PASS     Directory Structure
✓ PASS     Required Files
✓ PASS     Module Imports
✓ PASS     Configuration

TOTAL: 8/8 tests passed
🎉 All tests passed! Installation is complete.
```

### Step 5: Start Service

```bash
start.bat
```

You should see:
```
============================================================
  Meeting Auto Capture - Starting...
============================================================
✓ Video Manager initialized (output: ../../data/input)
✓ Browser Joiner initialized (ffmpeg screen capture, WebM format)
  Profiles: ./data/browser_profiles
  Video output: ../../data/input
✓ Scheduler initialized
✓ Meeting Parser initialized
✓ Email Monitor initialized
  Server: imap.gmail.com:993
  Folder: Meetings
============================================================
Meeting Auto Capture is running!
============================================================
Services:
  • Email monitoring: Meetings (every 60s)
  • Meeting scheduling: Check every minute
  • Auto-join: 2 min before meeting
  • Auto-stop: 5 min after meeting
============================================================
Press Ctrl+C to stop
```

## 📧 Email Setup

### Gmail

1. **Enable IMAP:**
   - Settings → Forwarding and POP/IMAP
   - Enable IMAP
   - Save

2. **Create "Meetings" Label:**
   - Left sidebar → More → Create new label
   - Name: "Meetings"

3. **Create Filter (Optional):**
   - Settings → Filters and Blocked Addresses
   - Create filter for meeting invitations
   - Auto-apply label "Meetings"

4. **Set in config:**
   ```env
   MAC_IMAP_HOST=imap.gmail.com
   MAC_IMAP_FOLDER=Meetings
   ```

### Outlook

1. **Enable IMAP:**
   - Settings → View all Outlook settings
   - Mail → Sync email → IMAP
   - Enable

2. **Create "Meetings" Folder:**
   - Right-click Inbox → New folder
   - Name: "Meetings"

3. **Set in config:**
   ```env
   MAC_IMAP_HOST=outlook.office365.com
   MAC_IMAP_PORT=993
   MAC_IMAP_FOLDER=Meetings
   ```

## 🎬 First Meeting Test

### 1. Send Test Meeting Invitation

Forward a meeting invitation to your email in the "Meetings" folder.

Example email:
```
Subject: Test Meeting

Join meeting: https://zoom.us/j/1234567890
Time: Today at 3:00 PM
Duration: 30 minutes
```

### 2. Check Logs

```bash
type logs\autocapture.log
```

Should show:
```
[INFO] New email received: Test Meeting
[INFO] Parsed meeting: Test Meeting (zoom) at 2025-01-15T15:00:00
[INFO] Saved meeting: data/meetings/pending/{id}.json
```

### 3. Verify Meeting JSON

```bash
dir data\meetings\pending
type data\meetings\pending\{meeting-id}.json
```

Should contain:
```json
{
  "id": "abc-123...",
  "platform": "zoom",
  "meeting_link": "https://zoom.us/j/1234567890",
  "subject": "Test Meeting",
  "email_body_html": "...",
  "email_body_text": "..."
}
```

### 4. Test Auto-Join (Scheduled Meeting)

For a meeting scheduled in the future:
1. Service will auto-join 2 minutes before start
2. Browser opens with platform-specific profile
3. Platform handler navigates and joins meeting
4. ffmpeg starts screen + audio recording (WebM format, VP9+Opus)
5. Recording stops at end + 5 min buffer (graceful ffmpeg shutdown)
6. Video saved to `data/input/` with format: `{platform}_{timestamp}_mmmail({sender})_{id}.webm`

### 5. Manual Test (Immediate)

To test joining immediately without waiting:

```bash
# In Python console
cd src
python

>>> from browser_joiner import BrowserJoiner
>>> from models import MeetingInvitation
>>> from datetime import datetime
>>> import json

>>> # Load a pending meeting
>>> with open('../data/meetings/pending/MEETING-ID.json') as f:
...     data = json.load(f)
>>>
>>> meeting = MeetingInvitation(**data)
>>>
>>> # Create browser joiner
>>> joiner = BrowserJoiner(
...     profiles_path='../data/browser_profiles',
...     video_output_folder='../../data/input'
... )
>>>
>>> # Join meeting (will start ffmpeg recording)
>>> context = joiner.join_meeting(meeting)
>>> # Browser should open and join!
>>> # Check logs for ffmpeg PID
>>>
>>> # Stop when done (graceful ffmpeg shutdown)
>>> video_path = joiner.stop_recording(context, meeting)
>>> print(f"Video saved: {video_path}")
```

## 🔧 Troubleshooting

### Email Not Connecting

```
Error: Login credentials invalid
```

**Solution:**
- Use App Password (not regular password)
- Check IMAP is enabled
- Verify folder name is correct

### Browser Not Launching

```
Error: Executable doesn't exist
```

**Solution:**
```bash
playwright install chromium
```

### ffmpeg Not Found

```
Error: ffmpeg process failed to start
```

**Solution:**
1. Verify ffmpeg is installed:
   ```bash
   ..\..\tools\ffmpeg-8.0-essentials_build\bin\ffmpeg.exe -version
   ```
2. If not installed, run `setup.bat` and select "Y" for automatic installation
3. Or install manually from https://www.gyan.dev/ffmpeg/builds/
4. Update path in `src\browser_joiner.py` line 42 if using different location

### Recording Not Starting / No Audio

```
Warning: ffmpeg recording failed
```

**Solution:**
1. List available audio devices:
   ```bash
   ..\..\tools\ffmpeg-8.0-essentials_build\bin\ffmpeg.exe -list_devices true -f dshow -i dummy
   ```
2. Update audio device name in `src\browser_joiner.py` line 231
3. Check disk space is available
4. Verify output folder has write permissions
5. Check logs: `logs/autocapture.log`

### Video File Corrupted / Empty

```
Error: Video file cannot be played
```

**Solution:**
1. Check ffmpeg stopped gracefully (logs should show "ffmpeg stopped gracefully")
2. Verify file with ffprobe:
   ```bash
   ..\..\tools\ffmpeg-8.0-essentials_build\bin\ffprobe.exe video.webm
   ```
3. Should show VP9 video stream and Opus audio stream
4. Check disk permissions for output folder
5. Ensure meeting ran long enough (>10 seconds)

### Meeting Not Found

```
No meeting URL found in email
```

**Solution:**
- Check email has meeting link
- Verify platform pattern in `config/meeting_patterns.json`
- Check logs for parsing details

## 📊 Monitoring

### Check Service Status

```bash
# View logs in real-time
powershell Get-Content logs\autocapture.log -Wait -Tail 50

# Check pending meetings
dir data\meetings\pending

# Check in-progress recordings
dir data\meetings\in_progress

# Check completed meetings
dir data\meetings\completed
```

### Check Browser Profiles

```bash
dir data\browser_profiles
```

Folders created:
- `gpb_video/` - GPB Video profile
- `psbank/` - PSBank profile
- `zoom/` - Zoom profile
- etc.

**First Time**: You'll need to manually login to each platform once.

### Check Video Output

```bash
dir ..\..\data\input
```

Videos should appear here after recording stops.

## 🎯 Workflow Summary

```
1. Email arrives → Meetings folder
   ↓
2. Service detects new email (every 60s)
   ↓
3. Parser extracts meeting details + full body
   ↓
4. Meeting JSON saved to pending/
   ↓
5. Scheduler checks every minute
   ↓
6. 2 min before start: Browser launches
   ↓
7. Platform handler joins meeting
   ↓
8. ffmpeg starts screen + audio recording (WebM, VP9+Opus)
   ↓
9. Meeting ends + 5 min buffer
   ↓
10. ffmpeg graceful shutdown, WebM saved
    ↓
11. Video appears in data/input/ ({platform}_{timestamp}_mmmail({sender})_{id}.webm)
    ↓
12. watch_input_folder.py detects
    ↓
13. orchestrator.py processes (transcribe + diarize + Claude protocol)
    ↓
14. Email sent to sender with protocol
```

## 🛠️ Configuration

### Timing

```env
MAC_PRE_MEETING_JOIN_MINUTES=2   # Join early
MAC_POST_MEETING_BUFFER_MINUTES=5 # Record after
MAC_IMAP_CHECK_INTERVAL=60       # Email check frequency
```

### Platforms

Edit `config/meeting_patterns.json` to add/modify platforms:

```json
{
  "name": "my_platform",
  "regex": "myplatform\\.com\\/meeting\\/[\\w\\-]+",
  "priority": 10,
  "requires_auth": true
}
```

Lower priority = checked first.

## 📚 Files Reference

### Scripts

- `setup.bat` - One-time setup
- `start.bat` - Start service
- `test.bat` - Run tests
- `test_installation.py` - Verify installation

### Configuration

- `config/.env` - Environment variables
- `config/meeting_patterns.json` - Platform patterns

### Data

- `data/meetings/pending/` - Scheduled meetings
- `data/meetings/in_progress/` - Currently recording
- `data/meetings/completed/` - Finished meetings
- `data/browser_profiles/` - Persistent Chrome profiles

### Logs

- `logs/autocapture.log` - Main service log

## 🎓 Next Steps

1. ✅ Service running
2. ✅ Email configured
3. ✅ Extension updated
4. ✅ Test meeting successful

**You're ready!** Forward meeting invitations to your Meetings folder and the service will handle the rest.

## 🆘 Support

- Check logs: `logs/autocapture.log`
- Test installation: `test.bat`
- Documentation: `README.md` (includes ffmpeg setup and troubleshooting)
- Main project docs: `../../CLAUDE.md`
- Root README: `../../README.md`

## 🔄 Updating

To update the service:

```bash
git pull
cd services\meeting-autocapture
venv\Scripts\activate
pip install -r requirements.txt --upgrade
playwright install chromium
```

## 🐛 Known Issues

- **Waiting Rooms**: Meetings with waiting rooms need host approval
- **CAPTCHAs**: Cannot auto-solve CAPTCHAs
- **Platform Changes**: UI updates may break handlers
- **Time Zones**: All times in UTC (ensure correct parsing)

## ✨ Tips

- Keep service running 24/7 for full automation
- Configure correct audio device for your system (line 231 in browser_joiner.py)
- Review completed meeting JSONs for accuracy
- Check video files before deleting (WebM format, VP9+Opus)
- Monitor disk space (SD video ~2-3 MB/min, high audio)
- Verify ffmpeg version periodically for updates
- Update platform handlers as needed when UIs change
