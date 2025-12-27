# Capturing Folder Implementation

## Problem

When meeting-autocapture writes videos directly to `data/input/`, the watchdog in `watch_input_folder.py` detects the file immediately and tries to process it **while it's still being recorded**, causing errors.

## Solution

Implemented a two-stage recording process:

### 1. **Recording Stage** - `data/capturing/`
- Videos are written to `data/capturing/` folder during recording
- Watchdog does NOT monitor this folder
- ffmpeg writes the video file without interruption

### 2. **Completion Stage** - `data/input/`
- When recording stops, the completed video is **moved** from `data/capturing/` to `data/input/`
- Watchdog detects the complete file and triggers transcription orchestrator
- No risk of processing incomplete files

## Changes Made

### File: `services/meeting-autocapture/src/browser_joiner.py`

#### 1. Added capturing folder initialization (`__init__` method)

```python
# Create capturing folder for in-progress recordings
# This prevents watchdog from detecting files during recording
self.capturing_folder = os.path.join(os.path.dirname(self.video_output_folder), "capturing")
os.makedirs(self.capturing_folder, exist_ok=True)
```

#### 2. Changed recording destination (`_start_ffmpeg_recording` method)

**Before:**
```python
video_path = os.path.join(self.video_output_folder, filename)
```

**After:**
```python
# Save to capturing folder during recording to avoid watchdog detection
video_path = os.path.join(self.capturing_folder, filename)
```

#### 3. Added file move logic (`stop_recording` method)

```python
# Get video file path from capturing folder
capturing_video_path = self.video_file_paths.get(meeting.id)
if capturing_video_path and os.path.exists(capturing_video_path):
    self.logger.info(f"Video recorded to: {capturing_video_path}")

    # Move completed video from capturing folder to final output folder
    # This triggers watchdog only when recording is complete
    filename = os.path.basename(capturing_video_path)
    final_video_path = os.path.join(self.video_output_folder, filename)

    try:
        self.logger.info(f"Moving video to output folder: {final_video_path}")
        shutil.move(capturing_video_path, final_video_path)
        self.logger.info(f"Video successfully moved and ready for processing")
        return final_video_path
    except Exception as e:
        self.logger.error(f"Failed to move video to output folder: {e}")
        return capturing_video_path  # Fallback
```

## Folder Structure

```
data/
├── capturing/              # NEW: In-progress recordings (watchdog ignores)
│   └── (temporary .webm files during recording)
├── input/                  # EXISTING: Completed videos (watchdog monitors)
│   └── platform_timestamp_mmmail(email)_id.webm
└── results/                # EXISTING: Transcription outputs
    └── ...
```

## Flow Diagram

```
Meeting Auto Capture
    ↓
1. Start recording → Save to data/capturing/platform_timestamp.webm
    ↓
2. Meeting in progress... (ffmpeg writing to capturing folder)
    ↓
3. Stop recording → ffmpeg process ends
    ↓
4. Move file → data/input/platform_timestamp.webm
    ↓
5. Watchdog detects complete file
    ↓
6. Orchestrator processes transcription
```

## Benefits

✅ **No race conditions** - Watchdog only sees complete files
✅ **Safe recording** - ffmpeg can write without interruption
✅ **Clean separation** - In-progress vs completed files
✅ **Atomic trigger** - File move operation triggers processing
✅ **Error recovery** - If move fails, file still exists in capturing folder

## Testing

To verify the implementation works:

1. Start meeting-autocapture service
2. Trigger a meeting recording
3. Check that video appears in `data/capturing/` during recording
4. When recording stops, verify file moves to `data/input/`
5. Confirm orchestrator starts processing only after move completes

## Notes

- The `capturing` folder is created automatically on service startup
- `shutil.move()` is atomic on the same filesystem
- Fallback returns capturing path if move fails (manual recovery needed)
- No changes needed to watchdog or orchestrator - they continue to monitor `data/input/`
