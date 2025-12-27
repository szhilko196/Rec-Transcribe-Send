# MyRecV - Chrome Extension

**MyRecV** (Diarization Recorder) is a Chrome extension for recording screen and audio with task metadata.

## 🎯 Overview

MyRecV lets you quickly capture meetings, presentations, and other events while linking them to a task ID. Each file is saved with a consistent naming pattern to ease downstream transcription processing.

## 🧭 Navigation

The extension provides easy access to all tools through button-based navigation:

### Main Page (Extension UI)
- **⏺ RECORD / ⏹ STOP** - Start/stop recording
- **🎤 Rename speakers** - Opens Speaker Rename tool (post-processing)
- **🎵 Extract samples** - Opens Sample Splitter tool (speaker enrollment)
- **⚙️ Settings** - Opens Settings page

### Settings Page
Footer links provide quick access to:
- **🎤 Speaker Rename** - Rename speakers in transcripts
- **🎵 Sample Splitter** - Extract audio samples for speaker recognition
- **📖 Documentation** - GitHub repository

### Navigation Map

```
┌─────────────────────────────────────────┐
│   MyRecV Extension Main Page            │
│   (Click extension icon in toolbar)     │
├─────────────────────────────────────────┤
│                                          │
│   📝 Task Number: [TASK-123]            │
│   📄 Description: [Optional...]          │
│   □ Audio only                           │
│                                          │
│   [⏺ RECORD]  [⏹ STOP]                  │
│                                          │
│   ┌──────────────────────────────────┐  │
│   │ 🎤 Rename speakers               │  │ ──┐
│   └──────────────────────────────────┘  │   │
│   ┌──────────────────────────────────┐  │   │
│   │ 🎵 Extract samples               │  │ ──┤
│   └──────────────────────────────────┘  │   │
│                                          │   │
│   ⚙️ Settings                            │ ──┤
│                                          │   │
└─────────────────────────────────────────┘   │
                                               │
       ┌───────────────────────────────────────┤
       │                                       │
       ▼                                       ▼
┌──────────────────┐                  ┌──────────────────┐
│ Speaker Rename   │                  │ Sample Splitter  │
│                  │                  │                  │
│ Replace          │                  │ Extract audio    │
│ SPEAKER_00 with  │                  │ samples for      │
│ real names       │                  │ enrollment       │
└──────────────────┘                  └──────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ Settings Page                │
│                              │
│ Configure recording options  │
│                              │
│ Footer Links:                │
│ • 🎤 Speaker Rename          │ ──→ Opens in new tab
│ • 🎵 Sample Splitter         │ ──→ Opens in new tab
│ • 📖 Documentation           │ ──→ Opens GitHub
└──────────────────────────────┘
```

**No need to manually enter URLs** - all tools are one click away!

## ✨ Features

### Recording Features
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

### Post-Processing Tools
- ✅ **Speaker Rename Tool** - Manually rename speakers (SPEAKER_00 → Real names)
- ✅ **Sample Splitter Tool** - Extract audio samples for speaker enrollment
- ✅ Audio playback for speaker identification
- ✅ Automatic segment analysis (3 longest per speaker)
- ✅ Batch file updating (protocol, summary, transcripts)
- ✅ speakers.json auto-generation

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

### Recording Flow

1. **Click the extension icon** in the Chrome toolbar
2. **Enter the task number** (required), e.g., `TASK-123`
3. **Add a description** (optional) for quick context
4. **Choose the mode**:
   - Leave "Audio only" unchecked for video + audio
   - Check "Audio only" to skip video capture
5. **Click "⏺ RECORD"**
6. **Pick the screen/window/tab** to record
7. **Recording starts** — the timer displays duration
8. **Click "⏹ STOP"** to finish
9. **The file is saved automatically** as `TASK-123_Description_2025-01-29_14-30-45.webm`

### Post-Processing Flow

After your meeting is transcribed, use the built-in tools:

1. **🎤 Rename speakers** - Click button to open Speaker Rename tool
   - Replace SPEAKER_00 with real names in all output files
   - See: [Speaker Rename Tool](#-speaker-rename-tool) section below

2. **🎵 Extract samples** - Click button to open Sample Splitter tool
   - Extract audio samples for speaker recognition enrollment
   - See: [Sample Splitter Tool](#-sample-splitter-tool) section below

3. **⚙️ Settings** - Configure recording preferences and access tool links

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

1. **Manually copy** the file into the project's `./data/input/`
2. **Use the auto-processor** to monitor the folder automatically
3. **Send it via an N8n webhook** (planned)

Once a file appears in `./data/input/`, the system automatically:
- Extracts audio (FFmpeg Service)
- Transcribes speech (Whisper)
- Performs diarization (pyannote.audio)
- Recognizes speakers (SpeechBrain - optional)
- Generates a summary and protocol (Claude API)

### Post-Processing Options

After transcription, you have two options for speaker identification:

**Option 1: Automatic Speaker Recognition**
- Use the **🎵 Extract samples** button to enroll speakers
- Extract audio samples from meetings using Sample Splitter tool
- Enable speaker recognition in `.env`: `ENABLE_SPEAKER_RECOGNITION=true`
- System automatically replaces SPEAKER_XX with real names in future meetings
- See: `SPEAKER_RECOGNITION_IMPLEMENTATION.md`

**Option 2: Manual Speaker Rename Tool**
- Use the **🎤 Rename speakers** button on the extension's main page
- Listen to audio samples and manually identify speakers
- Update all files with real names
- Best for one-off meetings or when automatic recognition isn't available

**Quick Access:**
- Both tools are available via buttons on the extension's main page
- Also accessible from Settings page footer links
- No need to remember or type URLs!

## 🎭 Speaker Rename Tool

**Speaker Rename** is a standalone web-based tool for manually renaming speakers in processed transcripts. After automatic transcription and diarization, speakers are labeled as `SPEAKER_00`, `SPEAKER_01`, etc. This tool allows you to replace these generic labels with real participant names across all output files.

### 🎯 Purpose

- Replace generic speaker labels (SPEAKER_00, SPEAKER_01) with actual names
- Update all output files simultaneously (protocol.md, summary.md, transcripts)
- Listen to audio samples to identify who is speaking
- Quick and easy post-processing workflow

### ✨ Features

- ✅ **Folder Selection** - Pick any results folder from `data/results/`
- ✅ **File Detection** - Automatically finds protocol.md, summary.md, transcript_readable.txt, transcript_full.json
- ✅ **Audio Playback** - Play voice samples for each speaker to identify them
- ✅ **Real-time Preview** - See speech examples before renaming
- ✅ **Batch Renaming** - Update all files at once with a single click
- ✅ **Progress Tracking** - Visual progress bar during processing
- ✅ **File System Access API** - Direct file editing (no downloads/uploads)

### 🚀 How to Use

#### 1. Open the Tool

**Easy way (recommended):**
- Click the **🎤 Rename speakers** button on the extension's main page
- The tool will open in a new tab automatically

**Alternative ways:**
- From **Settings page** → Click "🎤 Speaker Rename" link in footer
- Or open `chrome-extension/speaker-rename/speaker-rename.html` directly in Chrome

#### 2. Select Results Folder

1. Click **"📂 Choose results folder"**
2. Navigate to a specific meeting result folder, e.g., `data/results/meeting_2025-01-29_123456/`
3. Select the folder

**Required files:**
- ✅ `protocol.md` - Meeting protocol
- ✅ `summary.md` - Meeting summary
- ✅ `transcript_readable.txt` - Human-readable transcript
- ✅ `transcript_full.json` - Full transcript with timestamps

**Optional files:**
- ℹ️ `audio.wav` - Enables audio playback for speaker identification

#### 3. Identify Speakers

For each speaker, the tool displays:
- **Speaker ID**: Original label (e.g., SPEAKER_00)
- **Speech sample**: Text excerpt (~250 characters) showing what this speaker said
- **Play button**: Listen to audio clip (if audio.wav is present)

**To identify a speaker:**
1. Read the speech sample
2. Click **▶️ Play** to hear their voice (if available)
3. Enter the participant's name in the input field

**Example:**
```
SPEAKER_00
Speech sample: "Добрый день, коллеги. Начинаем наше совещание по проекту..."
[▶️ Play]
Input: Иван Петров ✅
```

#### 4. Apply Renaming

1. Enter names for at least one speaker
2. Click **"✅ Apply renaming"**
3. Wait for processing (progress bar shows status)
4. Review results summary

**What gets updated:**
- All occurrences of `SPEAKER_00` → `Иван Петров`
- Across all 4 files simultaneously
- Original files are overwritten (make backups if needed!)

#### 5. Results

After completion, you'll see:
- ✅ Files processed successfully: 4 of 4
- ✅ Speakers renamed: 2
- File-by-file status (✅ success or ❌ error)

### 📋 Workflow Example

**Before:**
```markdown
## Meeting Protocol

**SPEAKER_00**: Добрый день, начинаем совещание.
**SPEAKER_01**: Спасибо, у меня есть вопрос по бюджету.
**SPEAKER_02**: Предлагаю обсудить это позже.
```

**After renaming:**
```markdown
## Meeting Protocol

**Иван Петров**: Добрый день, начинаем совещание.
**Мария Смирнова**: Спасибо, у меня есть вопрос по бюджету.
**Алексей Козлов**: Предлагаю обсудить это позже.
```

### 🎵 Audio Playback

When `audio.wav` is present in the results folder:

1. **Play button** appears next to each speaker
2. Click **▶️ Play** to hear the speaker's voice
3. Audio plays the first segment where this speaker talks
4. Button shows **⏸️ Stop** during playback
5. Playback automatically stops at segment end

**Playback features:**
- Precise timestamp seeking (plays specific speaker segment)
- Automatic stop at segment boundary
- Visual feedback (loading state, stop button)

**Tip:** Use audio playback to confidently identify speakers when speech samples are ambiguous.

### 🔧 Technical Details

**Technology Stack:**
- HTML5 + Vanilla JavaScript (no frameworks)
- File System Access API - Direct file read/write
- HTML5 Audio API - Audio playback with precise seeking
- Modern CSS with flexbox/grid

**File Processing:**
- Reads files using FileReader
- Performs regex-based text replacement
- Writes back using FileHandle.createWritable()
- Supports both text (md, txt, json) formats

**Browser Compatibility:**
- ✅ Google Chrome 86+
- ✅ Microsoft Edge 86+
- ❌ Firefox (File System Access API not supported)
- ❌ Safari (File System Access API not supported)

**Permissions:**
- Folder read/write access (granted via file picker)
- No network requests
- No data storage (everything in memory)

### 🎯 Use Cases

**1. Post-processing manual recordings:**
```
Recording → Transcription → Speaker Rename Tool → Final protocol
```

**2. Correcting automated speaker recognition:**
```
If automatic speaker recognition failed → Use this tool to fix names manually
```

**3. Adding names to meetings without speaker profiles:**
```
Meeting with unknown participants → Transcribe → Manually identify speakers
```

### 📁 File Structure

```
chrome-extension/speaker-rename/
├── speaker-rename.html       # Main UI
├── speaker-rename.js         # Core logic (580 lines)
└── speaker-rename.css        # Styling
```

### ⚠️ Important Notes

1. **Original files are overwritten** - Make backups before using the tool
2. **Requires File System Access API** - Only works in Chrome/Edge
3. **No undo functionality** - Renaming is permanent (can reset and redo)
4. **Audio playback requires audio.wav** - Won't work with video-only results

### 🔄 Reset Functionality

Click **"🔄 Reset"** to:
- Clear all input fields
- Deselect folder
- Stop audio playback
- Return to initial state
- Start over with a different folder

### 🆚 Speaker Rename vs Automatic Speaker Recognition

| Feature | Manual Rename Tool | Automatic Recognition |
|---------|-------------------|----------------------|
| **Setup** | No setup needed | Requires speaker enrollment |
| **Accuracy** | 100% (you decide) | 85-95% (depends on samples) |
| **Speed** | Manual (~2-5 min) | Automatic (instant) |
| **Use case** | Ad-hoc meetings | Regular meetings with known participants |
| **Audio needed** | Optional (for identification) | Required (for enrollment) |

**Recommendation:** Use automatic speaker recognition for regular meetings, use this tool for one-off meetings or corrections.

## 🎵 Sample Splitter Tool

**Sample Splitter** is a web-based tool for extracting audio samples from transcribed meetings to enroll speakers in the speaker recognition system. Extract high-quality voice samples and automatically generate the correct folder structure and `speakers.json` file.

### 🎯 Purpose

- Extract audio samples for speaker enrollment in recognition system
- Find the 3 longest speech segments per speaker automatically
- Listen to samples before extraction to verify speaker identity
- Generate proper folder structure and speakers.json automatically
- Truncate long segments (>5 min) to optimal length

### ✨ Features

- ✅ **Automatic Segment Analysis** - Finds 3 longest speeches per speaker
- ✅ **Sample Selection** - Checkboxes to select which segments to extract
- ✅ **Audio Preview** - Play segments before extraction to verify identity
- ✅ **Auto-Truncation** - Segments >5 minutes automatically truncated to 5:00
- ✅ **Batch Processing** - Extract samples for multiple speakers at once
- ✅ **speakers.json Management** - Auto-create/update speakers.json file
- ✅ **Overwrite Protection** - Asks before overwriting existing speaker folders
- ✅ **16kHz Mono WAV** - Correct format for speaker recognition

### 🚀 How to Use

#### 1. Open the Tool

**Easy way (recommended):**
- Click the **🎵 Extract samples** button on the extension's main page
- The tool will open in a new tab automatically

**Alternative ways:**
- From **Settings page** → Click "🎵 Sample Splitter" link in footer
- Or open `chrome-extension/sample-splitter/sample-splitter.html` directly in Chrome

#### 2. Select Input Folder

1. Click **"📂 Choose input folder"**
2. Navigate to a meeting results folder (e.g., `data/results/meeting_2025-01-29_123456/`)
3. Select the folder

**Required files in folder:**
- ✅ `audio.wav` - Original meeting audio
- ✅ `transcript_full.json` - Transcript with speaker labels and timestamps

The tool will automatically:
- Parse transcript to find all speakers (excluding "UNKNOWN")
- Analyze each speaker's segments
- Select the 3 longest continuous speeches per speaker

#### 3. Select Output Folder

1. Click **"📂 Choose output folder"**
2. Navigate to speaker profiles folder (e.g., `data/speaker_profiles/`)
3. Select the folder

The tool will check for existing `speakers.json` and load it if present.

#### 4. Review & Select Segments

For each detected speaker (SPEAKER_00, SPEAKER_01, etc.), you'll see:

**Speaker Card showing:**
- **Speaker ID**: Original label from transcript
- **Name input field**: Enter real participant name
- **3 Longest Segments** with:
  - Checkbox to select/deselect
  - Duration (e.g., "8.5s" or "6:30 → 5:00" if truncated)
  - Speech sample text preview (~100 characters)
  - Play button to hear the audio
  - Warning if segment >5 minutes

**Example:**
```
SPEAKER_04
[Input: Иван Петров]

☑ 2:15  ▶️ Play  "Нужно на самом деле понять бизнес-процесс, как вы работаете с этой формой..."
☑ 1:48  ▶️ Play  "Да, смотрите, у нас есть форма с включенной подписанием, коллеги из банка..."
☐ 1:12  ▶️ Play  "Мы можем настроить интеграцию с вашей системой через API..."
```

#### 5. Listen & Identify

1. **Play audio samples** to confirm speaker identity
2. **Uncheck segments** you don't want to extract
3. **Enter real name** in the input field (required)
4. Repeat for other speakers you want to enroll

**Tips:**
- Select 2-3 diverse segments per speaker (different contexts)
- Avoid segments with background noise or overlapping speech
- Longer segments generally work better (but not too long)

#### 6. Extract Samples

1. Enter names for at least one speaker
2. At least one segment must be checked for that speaker
3. Click **"✅ Extract samples"**
4. Confirm if prompted (overwrite existing speaker folders)
5. Wait for extraction to complete

**What happens:**
- Selected audio segments are extracted from audio.wav
- Segments >5 minutes truncated to first 5 minutes
- Audio resampled to 16kHz mono PCM WAV
- Files saved as `{speaker_id}/sample_01.wav`, `sample_02.wav`, etc.
- speakers.json created or updated with new entries

#### 7. Results

After completion, you'll see:
- ✅ Successfully processed: X speaker(s)
- Individual speaker status (success/error/skipped)
- speakers.json location
- Ready to use with speaker recognition system!

### 📋 Workflow Example

**Input:** Meeting with 4 speakers (SPEAKER_00 through SPEAKER_03)

**Process:**
1. Select results folder containing audio.wav + transcript_full.json
2. Tool analyzes: Found 4 speakers with 3 longest segments each
3. You identify:
   - SPEAKER_00 → Skip (unknown participant)
   - SPEAKER_01 → "Иван Петров" (select all 3 segments)
   - SPEAKER_02 → "Мария Смирнова" (select 2 segments)
   - SPEAKER_03 → Skip (poor audio quality)
4. Extract samples
5. Output generated:
```
data/speaker_profiles/
├── speakers.json (updated)
├── ivan_petrov/
│   ├── sample_01.wav
│   ├── sample_02.wav
│   └── sample_03.wav
└── maria_smirnova/
    ├── sample_01.wav
    └── sample_02.wav
```

### 🔧 Technical Details

**Audio Processing:**
- Web Audio API for loading and decoding
- Segment extraction with sample-accurate timing
- Resampling to 16kHz mono (required for recognition)
- WAV encoding: PCM 16-bit
- Auto-truncation: Max 5 minutes (300 seconds)

**File Naming:**
- Speaker ID generated from name (lowercase, underscores)
- Sequential numbering: `sample_01.wav`, `sample_02.wav`, etc.
- Only numbered as selected (if you select segments 1 and 3, they become sample_01 and sample_02)

**speakers.json Structure:**
```json
{
  "version": "1.0",
  "speakers": [
    {
      "id": "ivan_petrov",
      "name": "Иван Петров",
      "audio_samples": [
        "ivan_petrov/sample_01.wav",
        "ivan_petrov/sample_02.wav"
      ],
      "created_at": "2025-11-20T10:30:00Z",
      "metadata": {}
    }
  ]
}
```

**Browser Compatibility:**
- ✅ Google Chrome 86+
- ✅ Microsoft Edge 86+
- ❌ Firefox (File System Access API not supported)
- ❌ Safari (File System Access API not supported)

### 🎯 Use Cases

**1. Enroll new speakers:**
```
New employee joins meetings → Extract samples from first meeting → Enroll → Future meetings auto-recognized
```

**2. Bulk enrollment from existing meetings:**
```
Have 10 past meetings → Extract samples from all → Enroll entire team at once
```

**3. Improve existing speaker profiles:**
```
Recognition accuracy low → Extract better quality samples → Update speaker profile
```

### 📁 File Structure

```
chrome-extension/sample-splitter/
├── sample-splitter.html       # Main UI
├── sample-splitter.js         # Core logic (~700 lines)
├── sample-splitter.css        # Styling
└── audio-utils.js             # WAV encoder and audio utilities
```

### ⚠️ Important Notes

1. **Audio.wav required** - Cannot extract samples without original audio
2. **Segment quality matters** - Better samples = better recognition accuracy
3. **Name format** - Speaker names converted to IDs (lowercase, underscores only)
4. **Overwrite warning** - Always asks before replacing existing speaker folders
5. **Memory usage** - Large audio files (>1 hour) may take time to load
6. **Sample recommendations**:
   - Minimum 2 samples per speaker
   - Each sample 3-10 seconds (or longer)
   - Diverse speech contexts
   - Clear audio without noise

### 🔄 Integration with Speaker Recognition

Output is directly compatible with:
- `services/transcription_orchestrator/manage_speakers.py`
- `services/transcription_orchestrator/speaker_profile_validator.py`
- `services/transcription_orchestrator/recognize.py`

**After extraction:**
1. Enable speaker recognition in `.env`: `ENABLE_SPEAKER_RECOGNITION=true`
2. Run validation: `python manage_speakers.py --validate`
3. Process new meetings → Speakers automatically recognized!

### 🆚 Sample Splitter vs Manual Extraction

| Feature | Sample Splitter | Manual Tools |
|---------|----------------|--------------|
| **Segment Finding** | Automatic (3 longest) | Manual search |
| **Audio Preview** | Built-in playback | Separate audio player |
| **File Format** | Auto-converted to 16kHz mono | Manual conversion |
| **speakers.json** | Auto-generated | Manual editing |
| **Folder Structure** | Auto-created | Manual organization |
| **Speed** | 5-10 min for full team | 30-60 min manual work |

**Recommendation:** Always use Sample Splitter for speaker enrollment - it's faster, more accurate, and generates correct file structure.

**Recommendation:** Use automatic speaker recognition for regular meetings, use this tool for one-off meetings or corrections.

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
├── speaker-rename/           # Speaker renaming tool
│   ├── speaker-rename.html   # Rename UI
│   ├── speaker-rename.js     # Rename logic (580 lines)
│   └── speaker-rename.css    # Rename styles
├── sample-splitter/          # Sample extraction tool
│   ├── sample-splitter.html  # Splitter UI
│   ├── sample-splitter.js    # Splitter logic (700 lines)
│   ├── sample-splitter.css   # Splitter styles
│   └── audio-utils.js        # WAV encoder utilities
├── utils/
│   ├── storage.js            # Storage utilities
│   └── file-handler.js       # File utilities
├── assets/
│   └── icons/                # Extension icons
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

### Recording Features
- [ ] Audio → WAV conversion
- [ ] Directory handle persistence (IndexedDB)
- [ ] Real PNG icons (16x16, 48x48, 128x128)
- [ ] Automatic upload to an N8n webhook (optional)
- [ ] Screen preview while recording
- [ ] Pause/resume support
- [ ] Settings export
- [ ] Dark theme UI

### Speaker Rename Tool
- [x] Manual speaker renaming functionality
- [x] Audio playback for speaker identification
- [x] Batch file processing
- [ ] Undo/redo functionality
- [ ] Backup creation before renaming
- [ ] Speaker name suggestions (from previous meetings)
- [ ] Keyboard shortcuts for faster workflow

### Sample Splitter Tool
- [x] Automatic segment analysis (3 longest per speaker)
- [x] Audio sample extraction with Web Audio API
- [x] Checkbox-based segment selection
- [x] Audio preview/playback
- [x] 5-minute auto-truncation
- [x] speakers.json auto-generation
- [x] 16kHz mono WAV output
- [ ] Batch processing multiple meetings
- [ ] Quality scoring for segments
- [ ] Custom segment duration limits

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
