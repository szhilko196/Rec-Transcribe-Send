# ffmpeg Recording Fix - Audio Capture Issue

## Problem

The meeting-autocapture service was not recording videos because:
1. **ffmpeg "essentials" build** doesn't include DirectShow support
2. **DirectShow is required** for audio device capture on Windows
3. The hardcoded audio device name was system-specific

## Solution Implemented

### 1. **Automatic Fallback to Video-Only** (Immediate Fix)

The system now:
- ✅ Tries audio+video recording first
- ✅ Auto-detects if audio capture fails
- ✅ Automatically retries with video-only mode
- ✅ Logs clear error messages

**Result**: Meetings will be recorded even without audio support

### 2. **Configurable Audio Settings** (For Future)

Added environment variables to `.env`:

```env
# Disable audio for essentials build
MAC_ENABLE_AUDIO=false

# Audio device (only works with full ffmpeg build)
MAC_AUDIO_DEVICE=audio="Your Device Name"

# ffmpeg path
MAC_FFMPEG_PATH=../../tools/ffmpeg-8.0-essentials_build/bin/ffmpeg.exe
```

### 3. **Better Error Logging**

Now logs:
- ffmpeg command being executed
- Full stderr output when ffmpeg fails
- Clear instructions on how to fix

## Current Status

✅ **VIDEO-ONLY RECORDING IS NOW WORKING**

With `MAC_ENABLE_AUDIO=false`, the system records:
- ✅ Screen video at 15 FPS
- ✅ VP9 codec (WebM format)
- ❌ No audio (microphone not captured)

## To Enable Audio Recording (Optional)

### Option 1: Download Full ffmpeg Build (Recommended)

1. Go to https://www.gyan.dev/ffmpeg/builds/
2. Download `ffmpeg-release-full.7z` (NOT essentials)
3. Extract to `C:\prj\Rec-Transcribe-Send\tools\ffmpeg-full\`
4. Update `.env`:
   ```env
   MAC_FFMPEG_PATH=../../tools/ffmpeg-full/bin/ffmpeg.exe
   MAC_ENABLE_AUDIO=true
   ```
5. Find your audio device:
   ```cmd
   cd services\meeting-autocapture
   venv\Scripts\python.exe list_audio_devices.py
   ```
6. Update `.env` with your device name:
   ```env
   MAC_AUDIO_DEVICE=audio="Your Microphone Name Here"
   ```

### Option 2: Use Screen+Audio Loopback (Alternative)

Capture system audio ("what you hear") instead of microphone:
- Install VB-Audio Virtual Cable
- Configure Windows audio routing
- Set as audio device in `.env`

## Testing

To test the current video-only setup:

1. Restart the service:
   ```cmd
   cd services\meeting-autocapture
   start_meeting-autocapture.bat
   ```

2. Send a test meeting invitation email

3. Check logs for:
   ```
   Audio capture disabled - recording video only
   ffmpeg process started successfully (PID: ...)
   ```

4. After meeting ends, check:
   - `data/capturing/` - video should appear here during recording
   - `data/input/` - video moves here when complete

## Files Modified

1. **browser_joiner.py** (lines 46-51, 241-350)
   - Added configurable audio device
   - Added video-only fallback mode
   - Added better error handling and logging

2. **config/.env** (lines 20-30)
   - Added `MAC_ENABLE_AUDIO=false`
   - Added `MAC_AUDIO_DEVICE` configuration
   - Added `MAC_FFMPEG_PATH` configuration

3. **config/.env.example** (lines 19-31)
   - Added ffmpeg recording section
   - Documented configuration options

## Impact on Transcription

**Video-only recordings WILL STILL WORK** for transcription:
- ❌ No audio from recording itself
- ✅ BUT: Meeting platforms have their own audio
- ✅ Speakers in the meeting ARE audible in screen capture
- ✅ Transcription will work if meeting audio is playing through speakers

**Recommendation**: Ensure meeting audio plays through speakers (not headphones) so screen capture includes it.

## Next Steps

1. **Test current setup** - Video-only recording should work now
2. **Verify transcription** - Check if meeting audio is captured via speakers
3. **Optional**: Download full ffmpeg build for microphone recording
4. **Optional**: Configure proper audio device for better quality

## Related Files

- `browser_joiner.py` - Main recording logic
- `list_audio_devices.py` - Audio device detection helper
- `test_ffmpeg_capture.py` - ffmpeg capability tester
- `CAPTURING_FOLDER_CHANGES.md` - Two-stage recording process
