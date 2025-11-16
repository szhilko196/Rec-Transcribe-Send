# Meeting Auto Capture Module - Implementation Plan

## Overview
Create a standalone Python service in `services/meeting-autocapture/` that monitors email via IMAP, extracts meeting invitations including full email body to JSON, schedules automated browser sessions with Playwright for Python, joins meetings using persistent browser profiles, triggers Chrome extension recording via CDP, and saves videos to configured folder. Start as standalone script, then dockerize for production.

## Module Structure

```
services/meeting-autocapture/
├── src/
│   ├── main.py                     # Main entry point & optional FastAPI server
│   ├── email_monitor.py            # IMAP email monitoring
│   ├── meeting_parser.py           # Parse meeting invitations to JSON
│   ├── scheduler.py                # Schedule & trigger meeting joins
│   ├── browser_joiner.py           # Playwright automation for joining
│   ├── extension_bridge.py         # CDP communication with extension
│   ├── video_manager.py            # Video file tracking
│   ├── platform_handlers/          # Platform-specific join logic
│   │   ├── __init__.py
│   │   ├── base_handler.py        # Base class for handlers
│   │   ├── gpb_video.py           # Priority 1: gpb.video
│   │   ├── psbank_meeting.py      # Priority 2: meeting.psbank.ru
│   │   ├── zoom.py
│   │   ├── webex.py
│   │   ├── google_meet.py
│   │   └── telemost_yandex.py
│   └── models.py                   # Pydantic models for data validation
├── config/
│   ├── meeting_patterns.json       # URL patterns for platform detection
│   └── .env.example
├── data/
│   ├── meetings/                   # Meeting JSON files
│   │   ├── pending/               # Scheduled meetings
│   │   ├── in_progress/           # Currently recording
│   │   └── completed/             # Finished meetings
│   └── browser_profiles/           # Persistent Chrome profiles per platform
├── logs/                           # Service logs
├── requirements.txt
├── Dockerfile                      # For production deployment
└── README.md
```

## Technology Stack

- **Python 3.10**: Consistent with entire project
- **Playwright for Python**: Browser automation with CDP support
- **IMAPClient**: Email monitoring via IMAP protocol
- **icalendar**: Parse calendar attachments (.ics files)
- **APScheduler**: Python-native scheduling library
- **Pydantic**: Data validation and models
- **FastAPI** (optional): REST API for monitoring/control
- **python-dotenv**: Environment variable management

## Data Models

### MeetingInvitation Model (Pydantic)

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
import uuid

class MeetingInvitation(BaseModel):
    # Meeting identification
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    platform: Optional[str] = None  # gpb.video, zoom, etc.
    meeting_link: Optional[str] = None

    # Meeting details
    subject: str
    sender_email: str
    sender_name: str
    participants: List[str] = []
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    password: Optional[str] = None

    # Status tracking
    status: str = "pending"  # pending, in_progress, completed, failed

    # Full email body for later stages (USER REQUIREMENT)
    email_body_html: Optional[str] = None
    email_body_text: Optional[str] = None
    email_raw_headers: Dict[str, str] = {}
    email_attachments: List[str] = []  # Attachment filenames

    # Processing metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    video_file_path: Optional[str] = None
    error_message: Optional[str] = None
    browser_session_id: Optional[str] = None
```

### Meeting Pattern Configuration

`config/meeting_patterns.json`:
```json
{
  "patterns": [
    {
      "name": "gpb.video",
      "regex": "gpb\\.video\\/[\\w\\-]+",
      "priority": 1,
      "requires_auth": false,
      "profile_name": "gpb_video"
    },
    {
      "name": "meeting.psbank.ru",
      "regex": "meeting\\.psbank\\.ru\\/[\\w\\-]+",
      "priority": 2,
      "requires_password": true,
      "profile_name": "psbank"
    },
    {
      "name": "zoom",
      "regex": "zoom\\.us\\/j\\/\\d+",
      "requires_auth": false,
      "profile_name": "zoom"
    },
    {
      "name": "telemost.yandex",
      "regex": "telemost\\.yandex\\.ru\\/[\\w\\-]+",
      "requires_auth": true,
      "profile_name": "telemost"
    },
    {
      "name": "google_meet",
      "regex": "meet\\.google\\.com\\/[\\w\\-]+",
      "requires_auth": true,
      "profile_name": "google_meet"
    },
    {
      "name": "webex",
      "regex": "webex\\.com\\/.*\\/j\\.php",
      "requires_auth": false,
      "profile_name": "webex"
    }
  ]
}
```

## Implementation Phases

### Phase 1: Email Monitor (IMAP)

**File**: `src/email_monitor.py`

**Purpose**: Monitor IMAP folder for new meeting invitations

**Key Features**:
- Connect to IMAP server using credentials from .env
- Poll specified folder every N seconds (configurable)
- Fetch UNSEEN messages only
- Parse email headers, body (HTML + text), attachments
- Save complete email content for later stages
- Extract .ics calendar attachments
- Pass to meeting parser
- Mark as SEEN after processing

**Dependencies**:
```python
import imapclient
import email
from email import policy
from email.parser import BytesParser
import logging
import time
import threading
```

**Core Functions**:
```python
class EmailMonitor:
    def __init__(self, config: dict):
        self.host = config['host']
        self.port = config['port']
        self.username = config['username']
        self.password = config['password']
        self.folder = config['folder']
        self.check_interval = config['check_interval']

    def connect(self) -> imapclient.IMAPClient:
        """Establish IMAP connection"""

    def fetch_new_emails(self) -> List[dict]:
        """Fetch UNSEEN emails from folder"""

    def parse_email(self, email_data: bytes) -> dict:
        """Parse email to extract body, headers, attachments"""

    def extract_calendar_attachment(self, email_msg) -> Optional[bytes]:
        """Extract .ics attachment if present"""

    def start(self):
        """Start monitoring in background thread"""

    def stop(self):
        """Stop monitoring"""
```

**Email Parsing Logic**:
1. Use `BytesParser` with `policy.default` for modern email parsing
2. Extract `Subject`, `From`, `To`, `Date` headers
3. Get HTML body: `email_msg.get_body(preferencelist=('html'))`
4. Get plain text body: `email_msg.get_body(preferencelist=('plain'))`
5. Iterate attachments to find .ics files
6. Save all parts to dict for JSON serialization

### Phase 2: Meeting Parser

**File**: `src/meeting_parser.py`

**Purpose**: Parse email content and extract meeting details to JSON

**Key Features**:
- Parse .ics calendar files using `icalendar` library
- Extract meeting URLs from email body using regex patterns
- Detect meeting platform by URL matching
- Extract meeting passwords (common patterns)
- Calculate duration from calendar or default to 60 minutes
- **Save complete email body (HTML + text) to JSON**
- Generate unique meeting ID
- Write to `data/meetings/pending/{id}.json`

**Dependencies**:
```python
from icalendar import Calendar
import re
import json
from datetime import datetime, timedelta
from models import MeetingInvitation
```

**Core Functions**:
```python
class MeetingParser:
    def __init__(self, patterns_file: str):
        self.patterns = self._load_patterns(patterns_file)

    def parse_email_to_meeting(self, email_data: dict) -> Optional[MeetingInvitation]:
        """Main parsing function"""

    def parse_ics_attachment(self, ics_bytes: bytes) -> dict:
        """Extract start, end, duration from .ics"""
        cal = Calendar.from_ical(ics_bytes)
        for component in cal.walk():
            if component.name == "VEVENT":
                return {
                    'start': component.get('dtstart').dt,
                    'end': component.get('dtend').dt,
                    'summary': str(component.get('summary')),
                    'location': str(component.get('location'))
                }

    def extract_meeting_url(self, text: str) -> Optional[tuple[str, str]]:
        """Find meeting URL and detect platform"""
        for pattern in self.patterns:
            match = re.search(pattern['regex'], text)
            if match:
                return (match.group(0), pattern['name'])
        return None

    def extract_password(self, text: str) -> Optional[str]:
        """Extract meeting password from email body"""
        # Common patterns: "Password: 123456", "Пароль: 123456"
        patterns = [
            r'[Pp]assword:\s*(\w+)',
            r'[Пп]ароль:\s*(\w+)',
            r'[Cc]ode:\s*(\w+)'
        ]
        for p in patterns:
            match = re.search(p, text)
            if match:
                return match.group(1)
        return None

    def save_meeting_json(self, meeting: MeetingInvitation):
        """Save meeting to JSON file in pending folder"""
        filepath = f"data/meetings/pending/{meeting.id}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(meeting.dict(), f, indent=2, default=str)
```

### Phase 3: Scheduler

**File**: `src/scheduler.py`

**Purpose**: Schedule meeting joins and recording stops

**Key Features**:
- Use `APScheduler` for time-based triggers
- Load pending meetings on startup
- Check every minute for meetings needing action
- Join meetings 2 minutes before start time (configurable)
- Schedule recording stop at end time + buffer
- Update meeting status and move JSON files
- Handle errors and retries

**Dependencies**:
```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import os
import json
import shutil
```

**Core Functions**:
```python
class MeetingScheduler:
    def __init__(self, browser_joiner, video_manager):
        self.scheduler = BackgroundScheduler()
        self.browser_joiner = browser_joiner
        self.video_manager = video_manager
        self.active_sessions = {}  # meeting_id -> browser session

    def start(self):
        """Start scheduler and load pending meetings"""
        self.load_pending_meetings()
        self.scheduler.add_job(
            self.check_meetings,
            'interval',
            minutes=1,
            id='meeting_checker'
        )
        self.scheduler.start()

    def load_pending_meetings(self):
        """Load all pending meeting JSONs"""
        pending_dir = "data/meetings/pending"
        for filename in os.listdir(pending_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(pending_dir, filename)
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    meeting = MeetingInvitation(**data)
                    self._schedule_meeting(meeting)

    def check_meetings(self):
        """Check if any meetings need to join (runs every minute)"""
        now = datetime.utcnow()
        pending_dir = "data/meetings/pending"

        for filename in os.listdir(pending_dir):
            filepath = os.path.join(pending_dir, filename)
            with open(filepath, 'r') as f:
                meeting = MeetingInvitation(**json.load(f))

            join_time = meeting.start_time - timedelta(
                minutes=int(os.getenv('MAC_PRE_MEETING_JOIN_MINUTES', 2))
            )

            if now >= join_time and meeting.status == 'pending':
                self.trigger_join(meeting)

    def trigger_join(self, meeting: MeetingInvitation):
        """Start browser session and join meeting"""
        try:
            # Update status
            meeting.status = 'in_progress'
            self._move_meeting_json(meeting, 'pending', 'in_progress')

            # Start browser session
            session = self.browser_joiner.join_meeting(meeting)
            self.active_sessions[meeting.id] = session

            # Schedule stop
            buffer = int(os.getenv('MAC_POST_MEETING_BUFFER_MINUTES', 5))
            stop_time = meeting.end_time + timedelta(minutes=buffer)

            self.scheduler.add_job(
                self.trigger_stop,
                'date',
                run_date=stop_time,
                args=[meeting.id],
                id=f'stop_{meeting.id}'
            )

        except Exception as e:
            meeting.status = 'failed'
            meeting.error_message = str(e)
            self._move_meeting_json(meeting, 'in_progress', 'completed')

    def trigger_stop(self, meeting_id: str):
        """Stop recording and close browser"""
        if meeting_id in self.active_sessions:
            session = self.active_sessions[meeting_id]
            self.browser_joiner.stop_recording(session)
            session.close()
            del self.active_sessions[meeting_id]

            # Move to completed
            meeting = self._load_meeting(meeting_id, 'in_progress')
            meeting.status = 'completed'
            self._move_meeting_json(meeting, 'in_progress', 'completed')

    def _move_meeting_json(self, meeting: MeetingInvitation, from_status: str, to_status: str):
        """Move meeting JSON between folders"""
        src = f"data/meetings/{from_status}/{meeting.id}.json"
        dst = f"data/meetings/{to_status}/{meeting.id}.json"

        # Update and save
        with open(dst, 'w', encoding='utf-8') as f:
            json.dump(meeting.dict(), f, indent=2, default=str)

        if os.path.exists(src):
            os.remove(src)
```

### Phase 4: Browser Joiner with Playwright

**File**: `src/browser_joiner.py`

**Purpose**: Automate browser launch, meeting join, and recording control

**Key Features**:
- Launch Chromium with persistent profile (per platform)
- Load Chrome extension with recording capability
- Navigate to meeting using platform-specific handler
- Keep browser open during meeting
- Provide session object for later control

**Dependencies**:
```python
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
import os
from models import MeetingInvitation
from platform_handlers import get_handler
from extension_bridge import ExtensionBridge
```

**Core Class**:
```python
class BrowserJoiner:
    def __init__(self, extension_path: str, profiles_path: str):
        self.extension_path = os.path.abspath(extension_path)
        self.profiles_path = os.path.abspath(profiles_path)
        self.extension_bridge = ExtensionBridge()

    def join_meeting(self, meeting: MeetingInvitation) -> BrowserContext:
        """
        Launch browser with persistent profile and extension,
        join meeting, trigger recording, return context
        """
        # Get profile directory for this platform
        profile_name = self._get_profile_name(meeting.platform)
        profile_dir = os.path.join(self.profiles_path, profile_name)
        os.makedirs(profile_dir, exist_ok=True)

        # Launch Playwright
        playwright = sync_playwright().start()

        # Launch persistent context with extension
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,  # MUST be visible for meetings
            args=[
                f'--disable-extensions-except={self.extension_path}',
                f'--load-extension={self.extension_path}',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled'
            ],
            viewport={'width': 1920, 'height': 1080},
            accept_downloads=True,
            ignore_default_args=['--enable-automation'],
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )

        # Get platform-specific handler
        handler = get_handler(meeting.platform)

        # Open new page and join meeting
        page = context.new_page()
        success = handler.join(page, meeting)

        if success:
            # Wait a bit for meeting to load
            page.wait_for_timeout(5000)

            # Trigger recording via extension
            self.extension_bridge.start_recording(context, meeting)

            # Store context for later control
            return context
        else:
            raise Exception(f"Failed to join meeting: {meeting.platform}")

    def stop_recording(self, context: BrowserContext):
        """Stop recording and close browser"""
        try:
            self.extension_bridge.stop_recording(context)
            context.pages[0].wait_for_timeout(3000)  # Wait for save
            context.close()
        except Exception as e:
            logging.error(f"Error stopping recording: {e}")
            context.close()

    def _get_profile_name(self, platform: str) -> str:
        """Convert platform name to profile directory name"""
        return platform.replace('.', '_').replace(':', '_')
```

### Phase 5: Platform Handlers

**File**: `src/platform_handlers/base_handler.py`

**Purpose**: Abstract base class for platform-specific join logic

```python
from abc import ABC, abstractmethod
from playwright.sync_api import Page
from models import MeetingInvitation
import logging

class BasePlatformHandler(ABC):
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def join(self, page: Page, meeting: MeetingInvitation) -> bool:
        """
        Navigate to meeting and join.
        Return True on success, False on failure.
        """
        pass

    def enter_name(self, page: Page, name: str, selector: str):
        """Helper: Enter participant name"""
        try:
            page.fill(selector, name)
            return True
        except Exception as e:
            self.logger.error(f"Failed to enter name: {e}")
            return False

    def enter_password(self, page: Page, password: str, selector: str):
        """Helper: Enter meeting password"""
        try:
            page.fill(selector, password)
            return True
        except Exception as e:
            self.logger.error(f"Failed to enter password: {e}")
            return False

    def click_join_button(self, page: Page, selector: str):
        """Helper: Click join button"""
        try:
            page.click(selector)
            return True
        except Exception as e:
            self.logger.error(f"Failed to click join: {e}")
            return False
```

**Priority Handler 1**: `src/platform_handlers/gpb_video.py`

```python
from .base_handler import BasePlatformHandler
from playwright.sync_api import Page
from models import MeetingInvitation

class GPBVideoHandler(BasePlatformHandler):
    def join(self, page: Page, meeting: MeetingInvitation) -> bool:
        try:
            # Navigate to meeting
            page.goto(meeting.meeting_link, wait_until='networkidle')

            # Wait for join button (adjust selector based on actual page)
            page.wait_for_selector('button:has-text("Join")', timeout=10000)

            # Enter name if required
            name_input = page.query_selector('input[name="name"]')
            if name_input:
                self.enter_name(page, meeting.sender_name, 'input[name="name"]')

            # Click join
            page.click('button:has-text("Join")')

            # Wait for meeting to load
            page.wait_for_timeout(5000)

            self.logger.info(f"Successfully joined GPB Video meeting: {meeting.id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to join GPB Video meeting: {e}")
            return False
```

**Priority Handler 2**: `src/platform_handlers/psbank_meeting.py`

```python
from .base_handler import BasePlatformHandler
from playwright.sync_api import Page
from models import MeetingInvitation

class PSBankMeetingHandler(BasePlatformHandler):
    def join(self, page: Page, meeting: MeetingInvitation) -> bool:
        try:
            # Navigate to meeting
            page.goto(meeting.meeting_link, wait_until='networkidle')

            # Check if password required
            password_input = page.query_selector('input[type="password"]')
            if password_input and meeting.password:
                self.enter_password(page, meeting.password, 'input[type="password"]')
                page.click('button[type="submit"]')
                page.wait_for_timeout(2000)

            # Enter name
            name_input = page.query_selector('input[placeholder*="name"], input[placeholder*="имя"]')
            if name_input:
                self.enter_name(page, meeting.sender_name, name_input)

            # Click join button
            page.click('button:has-text("Join"), button:has-text("Войти")')

            # Wait for meeting interface
            page.wait_for_timeout(5000)

            self.logger.info(f"Successfully joined PSBank meeting: {meeting.id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to join PSBank meeting: {e}")
            return False
```

**Other handlers**: Implement similar classes for Zoom, Webex, Google Meet, Telemost Yandex

**File**: `src/platform_handlers/__init__.py`

```python
from .base_handler import BasePlatformHandler
from .gpb_video import GPBVideoHandler
from .psbank_meeting import PSBankMeetingHandler
from .zoom import ZoomHandler
from .webex import WebexHandler
from .google_meet import GoogleMeetHandler
from .telemost_yandex import TelemostYandexHandler

HANDLERS = {
    'gpb.video': GPBVideoHandler,
    'meeting.psbank.ru': PSBankMeetingHandler,
    'zoom': ZoomHandler,
    'webex': WebexHandler,
    'google_meet': GoogleMeetHandler,
    'telemost.yandex': TelemostYandexHandler,
}

def get_handler(platform: str) -> BasePlatformHandler:
    """Get handler instance for platform"""
    handler_class = HANDLERS.get(platform)
    if handler_class:
        return handler_class()
    else:
        raise ValueError(f"No handler for platform: {platform}")
```

### Phase 6: Extension Bridge (CDP)

**File**: `src/extension_bridge.py`

**Purpose**: Communicate with Chrome extension via CDP to trigger recording

**Key Features**:
- Find extension page in browser context
- Send start/stop recording commands via JavaScript injection
- Handle extension communication protocol

```python
from playwright.sync_api import BrowserContext
from models import MeetingInvitation
import logging

class ExtensionBridge:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def start_recording(self, context: BrowserContext, meeting: MeetingInvitation):
        """Send CDP command to extension to start recording"""
        try:
            # Find any page (extension or meeting page)
            pages = context.pages
            if not pages:
                raise Exception("No pages available in browser context")

            page = pages[0]

            # Inject JavaScript to communicate with extension
            result = page.evaluate("""
                (meetingData) => {
                    return new Promise((resolve) => {
                        // Try to send message to extension
                        if (chrome && chrome.runtime) {
                            chrome.runtime.sendMessage({
                                action: 'START_RECORDING',
                                taskNumber: meetingData.id,
                                description: meetingData.subject
                            }, (response) => {
                                resolve(response || {success: true});
                            });
                        } else {
                            // Fallback: trigger via keyboard shortcut simulation
                            resolve({success: true, method: 'fallback'});
                        }
                    });
                }
            """, meeting.dict())

            self.logger.info(f"Recording started for meeting: {meeting.id}")
            return result

        except Exception as e:
            self.logger.error(f"Failed to start recording: {e}")
            # Try fallback: simulate Ctrl+Shift+R
            try:
                page = context.pages[0]
                page.keyboard.press('Control+Shift+R')
                self.logger.info("Triggered recording via keyboard shortcut")
            except:
                raise Exception(f"All recording trigger methods failed: {e}")

    def stop_recording(self, context: BrowserContext):
        """Send CDP command to stop recording"""
        try:
            pages = context.pages
            if not pages:
                return

            page = pages[0]

            result = page.evaluate("""
                () => {
                    return new Promise((resolve) => {
                        if (chrome && chrome.runtime) {
                            chrome.runtime.sendMessage({
                                action: 'STOP_RECORDING'
                            }, (response) => {
                                resolve(response || {success: true});
                            });
                        } else {
                            resolve({success: true, method: 'fallback'});
                        }
                    });
                }
            """)

            self.logger.info("Recording stopped")
            return result

        except Exception as e:
            self.logger.error(f"Failed to stop recording: {e}")
            # Try fallback: simulate Ctrl+Shift+S
            try:
                page = context.pages[0]
                page.keyboard.press('Control+Shift+S')
            except:
                pass
```

**Chrome Extension Modifications Required**:

Add to `chrome-extension/background/service-worker.js`:
```javascript
// Listen for messages from Playwright
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === 'START_RECORDING') {
        // Trigger recording with task number and description
        startRecording(message.taskNumber, message.description);
        sendResponse({success: true});
        return true;
    }

    if (message.action === 'STOP_RECORDING') {
        stopRecording();
        sendResponse({success: true});
        return true;
    }
});
```

### Phase 7: Video Manager

**File**: `src/video_manager.py`

**Purpose**: Track video file creation and link to meetings

```python
import os
import time
from typing import Optional
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from models import MeetingInvitation
import json

class VideoFileHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.webm'):
            self.callback(event.src_path)

class VideoManager:
    def __init__(self, output_folder: str):
        self.output_folder = output_folder
        self.logger = logging.getLogger(__name__)
        self.pending_meetings = {}  # meeting_id -> meeting_data

    def register_meeting(self, meeting: MeetingInvitation):
        """Register meeting to watch for its video file"""
        self.pending_meetings[meeting.id] = meeting

    def monitor_for_video(self, meeting_id: str, timeout: int = 300) -> Optional[str]:
        """
        Monitor output folder for video file matching meeting_id
        Returns path to video file or None if timeout
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            files = os.listdir(self.output_folder)
            for file in files:
                # Check if filename contains meeting ID
                if meeting_id in file and file.endswith('.webm'):
                    video_path = os.path.join(self.output_folder, file)
                    self.logger.info(f"Found video file: {video_path}")
                    return video_path

            time.sleep(5)  # Check every 5 seconds

        self.logger.warning(f"Video file not found for meeting {meeting_id} after {timeout}s")
        return None

    def update_meeting_with_video(self, meeting_id: str, video_path: str):
        """Update meeting JSON with video file path"""
        meeting_json = f"data/meetings/completed/{meeting_id}.json"

        if os.path.exists(meeting_json):
            with open(meeting_json, 'r') as f:
                data = json.load(f)

            data['video_file_path'] = video_path
            data['processed_at'] = str(datetime.utcnow())

            with open(meeting_json, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)

            self.logger.info(f"Updated meeting {meeting_id} with video path")
```

### Phase 8: Environment Configuration

**File**: `config/.env.example`

```env
# ==========================================
# Meeting Auto Capture - Email Settings
# ==========================================
MAC_IMAP_HOST=imap.gmail.com
MAC_IMAP_PORT=993
MAC_IMAP_USER=your-email@gmail.com
MAC_IMAP_PASSWORD=your-app-password              # Use app-specific password
MAC_IMAP_FOLDER=Meetings                          # Folder to monitor
MAC_IMAP_CHECK_INTERVAL=60                        # Check every N seconds

# ==========================================
# Meeting Auto Capture - Browser Settings
# ==========================================
MAC_CHROME_EXTENSION_PATH=../../chrome-extension
MAC_BROWSER_PROFILES_PATH=./data/browser_profiles
MAC_PRE_MEETING_JOIN_MINUTES=2                    # Join N minutes before start
MAC_POST_MEETING_BUFFER_MINUTES=5                 # Record N minutes after end

# ==========================================
# Meeting Auto Capture - Video Storage
# ==========================================
MAC_VIDEO_OUTPUT_FOLDER=../../data/input          # Where extension saves videos
MAC_ENABLE_AUTO_PROCESSING=true                   # Trigger orchestrator automatically

# ==========================================
# Meeting Auto Capture - API (Optional)
# ==========================================
MAC_API_PORT=8004
MAC_LOG_LEVEL=info                                # debug, info, warning, error
MAC_ENABLE_API=false                              # Enable FastAPI server
```

### Phase 9: Main Entry Point

**File**: `src/main.py`

```python
import os
import sys
import logging
import time
from dotenv import load_dotenv
from email_monitor import EmailMonitor
from scheduler import MeetingScheduler
from browser_joiner import BrowserJoiner
from video_manager import VideoManager

def setup_logging():
    """Configure logging"""
    log_level = os.getenv('MAC_LOG_LEVEL', 'INFO').upper()

    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/autocapture.log'),
            logging.StreamHandler()
        ]
    )

def main():
    """Main entry point for standalone execution"""
    # Load environment variables
    load_dotenv()

    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("="*60)
    logger.info("Meeting Auto Capture - Starting...")
    logger.info("="*60)

    # Validate required environment variables
    required_vars = [
        'MAC_IMAP_HOST',
        'MAC_IMAP_USER',
        'MAC_IMAP_PASSWORD',
        'MAC_CHROME_EXTENSION_PATH'
    ]

    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        logger.error(f"Missing required environment variables: {missing}")
        sys.exit(1)

    # Initialize components
    logger.info("Initializing components...")

    # Video Manager
    video_manager = VideoManager(
        output_folder=os.getenv('MAC_VIDEO_OUTPUT_FOLDER')
    )

    # Browser Joiner
    browser_joiner = BrowserJoiner(
        extension_path=os.getenv('MAC_CHROME_EXTENSION_PATH'),
        profiles_path=os.getenv('MAC_BROWSER_PROFILES_PATH', './data/browser_profiles')
    )

    # Scheduler
    scheduler = MeetingScheduler(
        browser_joiner=browser_joiner,
        video_manager=video_manager
    )

    # Email Monitor
    email_config = {
        'host': os.getenv('MAC_IMAP_HOST'),
        'port': int(os.getenv('MAC_IMAP_PORT', 993)),
        'username': os.getenv('MAC_IMAP_USER'),
        'password': os.getenv('MAC_IMAP_PASSWORD'),
        'folder': os.getenv('MAC_IMAP_FOLDER', 'INBOX'),
        'check_interval': int(os.getenv('MAC_IMAP_CHECK_INTERVAL', 60))
    }

    email_monitor = EmailMonitor(config=email_config)

    # Start services
    logger.info("Starting services...")

    try:
        # Start scheduler (loads pending meetings)
        scheduler.start()
        logger.info("✓ Scheduler started")

        # Start email monitoring
        email_monitor.start()
        logger.info("✓ Email monitor started")

        logger.info("="*60)
        logger.info("Meeting Auto Capture is running!")
        logger.info("Press Ctrl+C to stop")
        logger.info("="*60)

        # Keep running
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("\n" + "="*60)
        logger.info("Shutting down gracefully...")
        logger.info("="*60)

        email_monitor.stop()
        scheduler.stop()

        logger.info("Stopped successfully")

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### Phase 10: Optional FastAPI Server

Add to `src/main.py` (if MAC_ENABLE_API=true):

```python
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import threading

app = FastAPI(title="Meeting Auto Capture API", version="1.0.0")

# Global references to services
email_monitor_ref = None
scheduler_ref = None

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "email_connected": email_monitor_ref.is_connected() if email_monitor_ref else False,
        "scheduler_running": scheduler_ref.scheduler.running if scheduler_ref else False
    }

@app.get("/meetings")
def list_meetings(status: str = None):
    """List all meetings, optionally filtered by status"""
    statuses = ['pending', 'in_progress', 'completed'] if not status else [status]
    meetings = []

    for s in statuses:
        folder = f"data/meetings/{s}"
        if os.path.exists(folder):
            for file in os.listdir(folder):
                if file.endswith('.json'):
                    with open(os.path.join(folder, file)) as f:
                        meetings.append(json.load(f))

    return {"meetings": meetings, "count": len(meetings)}

@app.get("/meetings/{meeting_id}")
def get_meeting(meeting_id: str):
    """Get specific meeting details"""
    for status in ['pending', 'in_progress', 'completed']:
        filepath = f"data/meetings/{status}/{meeting_id}.json"
        if os.path.exists(filepath):
            with open(filepath) as f:
                return json.load(f)

    raise HTTPException(status_code=404, detail="Meeting not found")

@app.post("/meetings/{meeting_id}/join")
def manual_join(meeting_id: str):
    """Manually trigger meeting join"""
    # Load meeting from pending
    filepath = f"data/meetings/pending/{meeting_id}.json"
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Meeting not found in pending")

    with open(filepath) as f:
        meeting = MeetingInvitation(**json.load(f))

    # Trigger join
    scheduler_ref.trigger_join(meeting)

    return {"status": "joining", "meeting_id": meeting_id}

def start_api_server():
    """Start FastAPI server in separate thread"""
    port = int(os.getenv('MAC_API_PORT', 8004))
    uvicorn.run(app, host="0.0.0.0", port=port)

# In main(), add after service initialization:
if os.getenv('MAC_ENABLE_API', 'false').lower() == 'true':
    api_thread = threading.Thread(target=start_api_server, daemon=True)
    api_thread.start()
    logger.info(f"✓ API server started on port {os.getenv('MAC_API_PORT', 8004)}")
```

### Phase 11: Integration with Existing Pipeline

**Video Processing Integration**:

The module integrates seamlessly with your existing pipeline:

```
Email → Parser (saves body to JSON) → Scheduler →
Browser Joins → Extension Records →
Video saved to data/input/ →
watch_input_folder.py detects →
orchestrator.py processes →
Email with protocol sent to sender
```

**Key Integration Points**:

1. **Video Output**: Extension saves to `MAC_VIDEO_OUTPUT_FOLDER` (set to `data/input/`)
2. **Filename Pattern**: Include `_mmmail(sender-email)_` so orchestrator sends results
3. **Auto-Detection**: Existing `watch_input_folder.py` picks up new videos
4. **Processing**: Existing `orchestrator.py` handles transcription, Claude protocol, email
5. **Meeting JSON**: Keep in `completed/` folder for reference and auditing

**Extension Configuration**:

Configure Chrome extension to save files with this naming pattern:
```
MEETING-{meeting.id}_{meeting.subject}_{date-time}_mmmail({sender.email})_.webm
```

Example: `MEETING-abc123_Q1Review_2025-01-15_14-30_mmmail(sender@example.com)_.webm`

### Phase 12: Docker for Production (Later Stage)

**File**: `Dockerfile`

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and browsers
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy source code
COPY src/ ./src/
COPY config/ ./config/

# Create data directories
RUN mkdir -p /app/data/meetings/pending \
             /app/data/meetings/in_progress \
             /app/data/meetings/completed \
             /app/data/browser_profiles \
             /app/logs

# Expose API port (if enabled)
EXPOSE 8004

# Run as non-root user for security
RUN useradd -m -u 1000 autocapture && \
    chown -R autocapture:autocapture /app
USER autocapture

CMD ["python", "src/main.py"]
```

**Docker Compose Integration**:

Add to `docker-compose.yaml`:

```yaml
meeting-autocapture:
  build: ./services/meeting-autocapture
  container_name: meeting-autocapture
  ports:
    - "8004:8004"
  volumes:
    - ./data:/app/data/shared              # Share data folder with host
    - ./chrome-extension:/app/chrome-extension
    - ./services/meeting-autocapture/data/browser_profiles:/app/data/browser_profiles
    - ./services/meeting-autocapture/logs:/app/logs
  env_file:
    - .env
  environment:
    - MAC_VIDEO_OUTPUT_FOLDER=/app/data/shared/input
    - MAC_CHROME_EXTENSION_PATH=/app/chrome-extension
  restart: unless-stopped
  depends_on:
    - ffmpeg-service
    - transcription-service
```

## Dependencies

**File**: `requirements.txt`

```
# Core frameworks
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.5.0
python-dotenv>=1.0.0

# Email processing
imapclient>=2.3.1
email-validator>=2.1.0
icalendar>=5.0.11
python-dateutil>=2.8.2

# Browser automation
playwright>=1.40.0

# Scheduling
APScheduler>=3.10.4

# Utilities
aiofiles>=23.2.1
httpx>=0.25.0
watchdog>=3.0.0

# Logging
colorlog>=6.8.0
```

## Running the Service

### Standalone Mode (Development)

```bash
# Navigate to service directory
cd services/meeting-autocapture

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Copy and configure environment
cp config/.env.example .env
# Edit .env with your credentials

# Create directories (if not exist)
mkdir -p data/meetings/{pending,in_progress,completed}
mkdir -p data/browser_profiles
mkdir -p logs

# Run the service
python src/main.py
```

### Docker Mode (Production)

```bash
# From project root
docker-compose build meeting-autocapture
docker-compose up -d meeting-autocapture

# View logs
docker-compose logs -f meeting-autocapture

# Check status
docker-compose ps
```

## Testing Strategy

### Unit Tests

Create `tests/test_meeting_parser.py`:
```python
import pytest
from src.meeting_parser import MeetingParser

def test_extract_zoom_url():
    parser = MeetingParser('config/meeting_patterns.json')
    text = "Join meeting: https://zoom.us/j/1234567890"
    url, platform = parser.extract_meeting_url(text)
    assert platform == 'zoom'
    assert '1234567890' in url

def test_extract_password():
    parser = MeetingParser('config/meeting_patterns.json')
    text = "Meeting Password: abc123"
    password = parser.extract_password(text)
    assert password == 'abc123'
```

### Integration Tests

Create `tests/test_email_monitor.py`:
```python
def test_imap_connection():
    config = {
        'host': 'imap.gmail.com',
        'port': 993,
        'username': os.getenv('MAC_IMAP_USER'),
        'password': os.getenv('MAC_IMAP_PASSWORD'),
        'folder': 'INBOX',
        'check_interval': 60
    }
    monitor = EmailMonitor(config)
    assert monitor.connect() is not None
```

### End-to-End Test

```bash
# 1. Send test meeting email to yourself
# 2. Run service
python src/main.py

# 3. Check logs
tail -f logs/autocapture.log

# 4. Verify JSON created
ls data/meetings/pending/

# 5. Manually trigger join (if API enabled)
curl -X POST http://localhost:8004/meetings/{id}/join

# 6. Verify video file saved
ls ../../data/input/
```

## Troubleshooting

### Email Connection Issues

```bash
# Test IMAP connection
python -c "
import imapclient
client = imapclient.IMAPClient('imap.gmail.com', ssl=True)
client.login('your-email@gmail.com', 'your-app-password')
print('Connected successfully')
"
```

### Browser Launch Issues

```bash
# Verify Playwright installation
playwright install --help

# Test browser launch
python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto('https://google.com')
    print('Browser launched successfully')
    browser.close()
"
```

### Extension Not Loading

- Check extension path is absolute
- Verify extension manifest.json is valid
- Check Chrome extension folder structure
- Test extension manually in Chrome first

## Timeline & Milestones

### Week 1: Core Infrastructure
- **Days 1-2**: Email monitor + meeting parser (with full body JSON)
- **Day 3**: Scheduler implementation
- **Day 4**: Testing email→JSON workflow

### Week 2: Browser Automation
- **Days 5-6**: Browser joiner + platform handlers
- **Day 7**: Extension bridge (CDP)
- **Day 8**: Testing browser automation

### Week 3: Integration & Polish
- **Day 9**: Video manager + integration with existing pipeline
- **Day 10**: End-to-end testing
- **Day 11**: Optional API + Docker
- **Day 12**: Documentation + deployment

## Success Criteria

✅ **Python-based**: Consistent with entire project architecture
✅ **Full email body saved**: HTML + text in JSON for later stages
✅ **Standalone execution**: Runs as Python script without Docker
✅ **7+ meeting platforms**: gpb.video, meeting.psbank.ru, Zoom, Webex, Google Meet, Telemost, custom
✅ **IMAP monitoring**: Reliable email polling with configurable interval
✅ **Browser persistence**: Manual login once per platform, then auto-join
✅ **CDP recording trigger**: Programmatic Chrome extension control
✅ **Auto-processing**: Videos saved to data/input/, detected by watch_input_folder.py
✅ **Email integration**: Sender receives protocol via _mmmail() pattern
✅ **Production-ready**: Dockerizable for production deployment
✅ **Configurable**: All settings in .env file
✅ **Logging**: Comprehensive logging for debugging
✅ **Error handling**: Graceful failures with retries

## Next Steps

1. **Review this plan** with the team
2. **Create folder structure** and configuration files
3. **Start with Phase 1**: Email monitoring (simplest, most testable)
4. **Iterate through phases**: Test each component independently
5. **Integration testing**: Connect components gradually
6. **Deploy standalone**: Run as Python script first
7. **Docker production**: Containerize when ready for production

## Notes

- **Browser profiles**: First run requires manual login to each platform (gpb.video, psbank, etc.)
- **Extension modification**: Minor changes needed to support CDP messaging
- **Email patterns**: May need adjustment based on actual invitation formats
- **Platform selectors**: HTML selectors will need refinement per platform
- **Scheduling**: Consider time zones if meetings are international
- **Video size**: Monitor disk space, implement cleanup strategy if needed