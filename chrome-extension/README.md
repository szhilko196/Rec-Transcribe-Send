# MyRecV - Chrome Extension

**MyRecV** (Diarization Recorder) is a Chrome extension for recording screen and audio with task metadata.

## 🎯 Overview

MyRecV lets you quickly capture meetings, presentations, and other events while linking them to a task ID. Each file is saved with a consistent naming pattern to ease downstream transcription processing.

## ✨ Features

- ✅ Screen recording with audio (video + audio)
- ✅ Audio-only recording (no video)
- ✅ Task ID binding (required field)
- ✅ Recording description (up to 200 characters)
- ✅ Automatic file naming: `[TASK]_[DESCRIPTION]_[DATE]_[TIME].webm`
- ✅ Real-time recording timer
- ✅ Visual recording indicator
- ✅ Hotkeys (Ctrl+Shift+R to start, Ctrl+Shift+S to stop)
- ✅ Save to a chosen folder (File System Access API)
- ✅ Downloads API fallback
- ✅ History of the last 10 recordings
- ✅ Configurable parameters (audio format, video quality)

## 📦 Installation

### From source (Developer Mode)

1. Clone the Meeting Transcriber repository
2. Open Chrome and navigate to `chrome://extensions/`
3. Enable **Developer mode** in the top-right corner
4. Click **Load unpacked**
5. Choose the project’s `chrome-extension/` folder
6. The extension is installed!

### Note
For correct icon rendering, replace the SVG placeholders in `assets/icons/` with real PNG images.

## 🚀 Usage

### Basic flow

1. **Click the extension icon** in the Chrome toolbar
2. **Enter the task number** (required), e.g., `TASK-123`
3. **Add a description** (optional) for quick context
4. **Choose the mode**:
   - Leave “Audio only” unchecked for video + audio
   - Check “Audio only” to skip video capture
5. **Click “RECORD”**
6. **Pick the screen/window/tab** to record
7. **Recording starts** — the timer displays duration
8. **Click “STOP”** to finish
9. **The file is saved automatically** as `TASK-123_Description_2025-01-29_14-30-45.webm`

### Hotkeys

- **Ctrl+Shift+R** (⌘+Shift+R on Mac) — open the popup to begin recording
- **Ctrl+Shift+S** (⌘+Shift+S on Mac) — stop the current recording

Configure hotkeys at `chrome://extensions/shortcuts`

### Settings

Open the **extension Settings** to:

1. **Select the save folder** — pick any directory
2. **Choose audio format** — `.wav` (uncompressed) or `.webm` (compressed)
3. **Set video quality** — 720p, 1080p, or 2K
4. **Toggle recording history** — show/hide history in the popup

## 📁 File naming format

Recordings follow this pattern:

```
[TASK_NUMBER]_[DESCRIPTION]_[YYYY-MM-DD]_[HH-MM-SS].[ext]
```

**Examples:**
```
TASK-123_Bug-fix-auth_2025-01-29_14-30-45.webm
TASK-456_Weekly-meeting_2025-01-29_10-00-00.webm
ISSUE-789_2025-01-29_16-45-30.webm  
```

## 🔧 Technical details

### Technologies
- **Manifest V3** — current Chrome Extensions standard
- **Screen Capture API** — screen capture
- **MediaRecorder API** — media capture
- **File System Access API** — save into a user-selected folder
- **Chrome Storage API** — settings persistence
- **Chrome Commands API** — keyboard shortcuts
- **Chrome Notifications API** — notifications

### Formats
- **Video**: `.webm` (VP9 + Opus audio, 2.5 Mbps)
- **Audio**: `.webm` (Opus, 128 kbps) or `.wav` (PCM, planned)

### Permissions
- `storage` — save settings
- `notifications` — notify on start/stop
- `offscreen` — allow DOM APIs for MediaRecorder

## 🔗 Integration with Meeting Transcriber

MyRecV is part of the Meeting Transcriber ecosystem. After recording you can:

1. **Manually copy** the file into the project’s `./data/input/`
2. **Use the auto-processor** to monitor the folder automatically
3. **Send it via an N8n webhook** (planned)

Once a file appears in `./data/input/`, the system automatically:
- Extracts audio (FFmpeg Service)
- Transcribes speech (Whisper)
- Performs diarization (pyannote.audio)
- Generates a summary and protocol (Claude API)

## 🐛 Known issues

1. **SVG icons** — currently placeholders. Replace them with real PNG assets.
2. **WAV format** — conversion from webm to wav is not implemented yet (planned via Web Audio API).
3. **Directory handle persistence** — File System Access handles do not persist between sessions; reconnect the folder when needed.
4. **Browser compatibility** — Chrome/Edge only (Manifest V3).

## 🛠️ Development

### Project structure
```
chrome-extension/
├── manifest.json              # Extension manifest
├── background/
│   ├── service-worker.js      # Background service worker
│   └── recorder.js            # MediaRecorder wrapper
├── popup/
│   ├── popup.html            # Popup UI
│   ├── popup.js              # Popup logic
│   └── popup.css             # Popup styles
├── options/
│   ├── options.html          # Settings page
│   ├── options.js            # Settings logic
│   └── options.css           # Settings styles
├── utils/
│   ├── storage.js            # Storage utilities
│   └── file-handler.js       # File utilities
├── assets/
│   └── icons/                # Иконки расширения
└── offscreen.html            # Offscreen document
```

### Local development

1. Make your changes
2. Go to `chrome://extensions/`
3. Click **Reload** for the extension
4. Verify the behavior

### Debugging

- **Background Service Worker**: `chrome://extensions/` → Inspect views: Service Worker
- **Popup**: Right-click the popup → “Inspect”
- **Options Page**: Right-click the page → “Inspect”

### Logs

All logs are printed to the Console of their respective contexts (background, popup, options).

## 📝 TODO / Roadmap

- [ ] Audio → WAV conversion
- [ ] Directory handle persistence (IndexedDB)
- [ ] Real PNG icons (16x16, 48x48, 128x128)
- [ ] Automatic upload to an N8n webhook (optional)
- [ ] Screen preview while recording
- [ ] Pause/resume support
- [ ] Settings export
- [ ] Dark theme UI

## 📄 License

MIT License — see the LICENSE file in the project root

## 🤝 Contributing

Contributions are welcome! Please open Issues and Pull Requests in the GitHub repository.

## 📧 Support

If you run into problems:
1. Check the Console for errors
2. Confirm the required permissions are granted
3. Open a GitHub issue with details

---

**MyRecV** — record meetings effortlessly! 🎙️🎬
