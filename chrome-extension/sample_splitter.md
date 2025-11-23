# Sample Splitter - Implementation Plan

## Overview
Create a new Chrome extension page for extracting audio samples from transcribed meetings to enroll speakers in the speaker recognition system.

## Files to Create

### 1. **chrome-extension/sample-splitter/sample-splitter.html**
- Main UI structure with sections:
  - Folder selection (results folder + output folder for samples)
  - File detection status (audio.wav, transcript_full.json)
  - Speaker list with segment selection (3 longest per speaker)
  - Audio playback controls
  - Name input fields
  - Progress bar
  - Results summary

### 2. **chrome-extension/sample-splitter/sample-splitter.js** (~800-1000 lines)
- Core functionality:
  - Folder selection using File System Access API
  - Parse transcript_full.json to identify speakers
  - Find 3 longest segments per speaker (excluding UNKNOWN)
  - Audio playback with Web Audio API
  - Segment extraction and WAV encoding
  - Auto-truncate segments >5 minutes to 5 minutes
  - Save samples as sample_01.wav, sample_02.wav, sample_03.wav
  - Generate/update speakers.json
  - Overwrite confirmation dialogs

### 3. **chrome-extension/sample-splitter/sample-splitter.css**
- Styling based on speaker-rename patterns
- Speaker card layout with checkboxes
- Audio player controls
- Progress indicators
- Responsive design

### 4. **chrome-extension/sample-splitter/audio-utils.js**
- WAV encoder utility (convert AudioBuffer to WAV Blob)
- Segment extraction helper functions
- Audio format validation

## User Requirements (Clarified)

1. **Sample Selection**: User can select which samples to extract via checkboxes
2. **Segment Length**: If sample >5 minutes, truncate to 5 minutes
3. **File Naming**: sample_01.wav, sample_02.wav, sample_03.wav (sequential)
4. **Integration**: Auto-create/update speakers.json file
5. **Overwrite Handling**: Ask user before overwriting existing files

## Key Features

### Speaker Analysis
1. Parse transcript_full.json
2. Group segments by speaker ID (SPEAKER_00, SPEAKER_01, etc.)
3. Calculate segment durations (end - start)
4. Select 3 longest continuous segments per speaker
5. Skip "UNKNOWN" speakers
6. Display speech sample text preview

### Segment Selection UI
- Each speaker shows 3 segments with:
  - Checkbox to select/deselect
  - Duration indicator (e.g., "8.5s")
  - Speech sample text (~100 chars)
  - Play button for audio preview
  - Truncation warning if >5 minutes ("Will be truncated to 5:00")
- Input field for real name (required to extract)
- Speaker ID → speaker_id conversion (lowercase, underscores)

### Audio Processing
1. Load audio.wav using Web Audio API
2. Decode to AudioBuffer
3. Extract selected segments (startSample to endSample)
4. Truncate if duration >5 minutes (keep first 5 minutes)
5. Encode to WAV format (16kHz mono PCM)
6. Save to output folder structure

### Output Management
- Folder structure: `{output_path}/{speaker_id}/sample_01.wav`
- Check if speaker folder exists → ask before overwriting
- Sequential numbering for selected samples only
- Update speakers.json with new/modified entries

### speakers.json Generation
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

## Implementation Steps

### Phase 1: UI Structure
1. Create HTML with folder selectors (input folder + output folder)
2. Add file detection section
3. Create speaker list container
4. Add progress/results sections

### Phase 2: Core Logic
1. Implement folder selection handlers
2. Parse transcript_full.json
3. Analyze segments and find longest 3 per speaker
4. Display speaker cards with checkboxes

### Phase 3: Audio Playback
1. Load audio.wav to AudioBuffer
2. Implement play/pause for individual segments
3. Add visual playback indicators

### Phase 4: Audio Extraction
1. Create WAV encoder utility
2. Implement segment extraction
3. Add 5-minute truncation logic
4. Handle file saving with File System Access API

### Phase 5: Integration
1. speakers.json creation/update logic
2. Overwrite confirmation dialogs
3. Validation (speaker ID format, minimum samples)
4. Results summary display

### Phase 6: Testing & Polish
1. Test with real meeting data
2. Error handling (missing files, invalid audio)
3. Memory optimization for large files
4. Update chrome-extension/README.md

## Files to Modify

### **chrome-extension/README.md**
- Add "Sample Splitter Tool" section
- Document usage workflow
- Add to TODO/Roadmap

## Technical Specifications

### Browser Compatibility
- Chrome 86+ (File System Access API)
- Edge 86+
- Not supported: Firefox, Safari

### Audio Format
- Input: WAV (any format from FFmpeg)
- Output: 16kHz mono PCM WAV
- Max segment length: 5 minutes (300 seconds)

### Memory Considerations
- Large audio files loaded into memory
- Progress indicators for processing
- Consider chunked processing if >100MB

### Validation Rules
- Speaker ID: lowercase, alphanumeric + underscore only
- Minimum 1 sample per speaker (recommended 2-3)
- Sample duration: 3-10 seconds recommended
- Max duration: 5 minutes (auto-truncated)

## User Workflow

1. **Select Input Folder** → Choose results folder with audio.wav + transcript_full.json
2. **Select Output Folder** → Choose data/speaker_profiles/ directory
3. **Review Speakers** → See list of detected speakers with 3 longest segments each
4. **Listen to Samples** → Play audio to verify speaker identity
5. **Select Samples** → Check/uncheck segments to extract (at least 1)
6. **Name Speakers** → Enter real names for speakers to enroll
7. **Extract** → Click "Extract Samples" button
8. **Confirm Overwrites** → Approve if speaker folders already exist
9. **Review Results** → See extraction summary and speakers.json status

## Success Criteria

- ✅ Successfully parse transcript_full.json with 12+ speakers
- ✅ Extract 3 longest segments per speaker (excluding UNKNOWN)
- ✅ Play audio segments with precise timestamps
- ✅ User can select which segments to extract
- ✅ Truncate segments >5 minutes to exactly 5 minutes
- ✅ Save WAV files with correct naming (sample_01.wav, etc.)
- ✅ Create/update speakers.json with valid structure
- ✅ Ask before overwriting existing speaker folders
- ✅ Handle errors gracefully (missing files, invalid audio)
- ✅ Update documentation in README.md

## Integration with Speaker Recognition System

This tool generates the exact file structure expected by:
- `services/transcription_orchestrator/manage_speakers.py`
- `services/transcription_orchestrator/speaker_profile_validator.py`
- `services/transcription_orchestrator/recognize.py`

Output can be directly used for speaker enrollment without manual file organization.
