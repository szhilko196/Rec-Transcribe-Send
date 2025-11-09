# Automatic processing of video files

## Description

A system that continuously monitors the `data/input/` folder to process meeting video files.

### Features:

✅ **Automatic detection** of new video files
✅ **Protection against re-processing** — files are identified by their SHA256 hash
✅ **Database of processed files** — `data/processed_videos.json`
✅ **Full logging** — `data/video_processor.log`
✅ **Supported formats**: mp4, avi, mov, mkv, webm, flv, wmv
✅ **Startup scan** — processes existing unprocessed files
✅ **File stabilization** — waits until copying is finished

## Usage

### 1. Start monitoring

```bash
python scripts/watch_input_folder.py
```

The script runs in the background and will:
- Scan the `data/input/` folder at startup
- Automatically process any unprocessed files it finds
- Watch for new files as they appear
- Launch `orchestrator.py` for every new file

### 2. Add a video for processing

Simply copy a video file into the `data/input/` folder:

```bash
# Windows
copy "C:\path\to\meeting.mp4" data\input\

# Linux/Mac
cp /path/to/meeting.mp4 data/input/
```

The system will automatically:
1. Detect the new file
2. Wait for the copy operation to finish
3. Check whether the file was processed before (by hash)
4. Launch the full processing pipeline
5. Create a results folder at `data/results/<video_name>_<timestamp>/`

### 3. Stop monitoring

Press `Ctrl+C` in the terminal where the script is running.

## Processed files database

File: `data/processed_videos.json`

Record structure:
```json
{
  "sha256_hash_here": {
    "file_name": "meeting.mp4",
    "file_path": "C:/prj/meeting-transcriber/data/input/meeting.mp4",
    "file_hash": "sha256_hash_here",
    "file_size": 281519587,
    "processed_at": "2025-10-19T17:30:45.123456",
    "status": "success",
    "result_folder": "data/results/meeting_20251019_173045",
    "error": null
  }
}
```

### Processing statuses:
- `success` — processed successfully
- `failed` — processing error

## Logging

All operations are logged to `data/video_processor.log`:

```
2025-10-19 17:30:45 - Detected new video file: meeting.mp4
2025-10-19 17:30:50 - meeting.mp4 stabilized (281519587 bytes)
2025-10-19 17:30:50 - Processing started: meeting.mp4
2025-10-19 17:30:50 - File size: 268.48 MB
2025-10-19 17:51:23 - [SUCCESS] meeting.mp4 processed successfully!
```

## Protection against duplicate processing

### How it works:
1. **Hashing** — calculates the SHA256 hash of the first 1 MB of the file
2. **Database check** — verifies the hash in the DB before processing
3. **Automatic skip** — skips the file if it has already been processed successfully

### Examples:

**Scenario 1**: The same file is copied twice
```bash
copy meeting.mp4 data\input\meeting_copy1.mp4
copy meeting.mp4 data\input\meeting_copy2.mp4
```
✅ Only `meeting_copy1.mp4` will be processed
⏭️ `meeting_copy2.mp4` will be skipped (identical hash)

**Scenario 2**: Monitoring restart
```bash
# Run 1
python scripts/watch_input_folder.py  # processed meeting.mp4

# Run 2
python scripts/watch_input_folder.py  # will skip meeting.mp4 (already in DB)
```

**Scenario 3**: New video with the same name
```bash
# If this is a NEW video (different content)
copy different_meeting.mp4 data\input\meeting.mp4
```
✅ It will be processed (different hash)

## Auto-start on system boot

### Windows (Task Scheduler):

1. Open Task Scheduler
2. Create Task → Triggers → "At startup"
3. Actions → "Start a program"
   - Program: `C:\Users\YourUser\AppData\Local\Programs\Python\Python313\python.exe`
   - Arguments: `C:\prj\meeting-transcriber\scripts\watch_input_folder.py`
   - Start in: `C:\prj\meeting-transcriber`

### Linux/Mac (systemd):

Create `/etc/systemd/system/video-processor.service`:

```ini
[Unit]
Description=Meeting Video Auto Processor
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/meeting-transcriber
ExecStart=/usr/bin/python3 /path/to/meeting-transcriber/scripts/watch_input_folder.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Then run:
```bash
sudo systemctl enable video-processor
sudo systemctl start video-processor
sudo systemctl status video-processor
```

## Monitoring and diagnostics

### View logs in real time:

```bash
# Windows
Get-Content data\video_processor.log -Wait

# Linux/Mac
tail -f data/video_processor.log
```

### Check processing statistics:

```python
import json
with open('data/processed_videos.json', 'r') as f:
    db = json.load(f)

success = sum(1 for r in db.values() if r['status'] == 'success')
failed = sum(1 for r in db.values() if r['status'] == 'failed')

print(f"Success: {success}")
print(f"Errors: {failed}")
print(f"Total: {len(db)}")
```

### Reset the database (WARNING: this removes history):

```bash
del data\processed_videos.json  # Windows
rm data/processed_videos.json   # Linux/Mac
```

## Troubleshooting

### Problem: File is processed again

**Cause**: The database was deleted or corrupted

**Solution**:
1. Check that `data/processed_videos.json` exists
2. Inspect logs for database write errors

### Problem: File is not processed automatically

**Cause 1**: Unsupported format

**Solution**: Verify the file extension (only mp4, avi, mov, mkv, webm, flv, wmv)

**Cause 2**: The file is still being copied

**Solution**: Wait for the copy operation to finish (the script automatically waits for stabilization)

### Problem: Monitoring stopped

**Cause**: Unhandled exception

**Solution**:
1. Check the `data/video_processor.log`
2. Restart the monitoring script
3. Use systemd/Task Scheduler for automatic restarts

## Integration with N8n

For N8n integration, see `n8n/README.md`, which describes the workflow for automatic processing.

## Performance

- **CPU mode**: ~20-25 minutes for a 12-minute video
- **Parallel processing**: NOT supported (files are handled sequentially)
- **Recommendation**: Use GPU mode to speed up transcription

## Requirements

- Python 3.8+
- watchdog >= 2.0
- All dependencies from `requirements.txt`
- Running Docker services (ffmpeg, transcription)
- Claude API key in `.env`
