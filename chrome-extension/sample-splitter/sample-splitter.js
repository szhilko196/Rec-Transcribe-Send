/**
 * Sample Splitter - Extract audio samples for speaker recognition enrollment
 */

import {
  audioBufferToWav,
  extractSegment,
  formatDuration,
  validateAudioBuffer,
  speakerNameToId,
  validateSpeakerId
} from './audio-utils.js';

// State
let state = {
  inputFolderHandle: null,
  outputFolderHandle: null,
  files: {
    transcriptJson: null,
    audioWav: null
  },
  audioBuffer: null,
  audioElement: null,
  speakers: [], // Array of speaker IDs
  speakerSegments: {}, // { 'SPEAKER_00': [{start, end, text, duration}, ...] }
  speakerNames: {}, // { 'SPEAKER_00': 'Иван Петров' }
  selectedSegments: {}, // { 'SPEAKER_00': [true, false, true] }
  existingSpeakers: {} // Loaded from speakers.json if exists
};

// IndexedDB for persisting folder handles
const DB_NAME = 'SampleSplitterDB';
const DB_VERSION = 1;
const STORE_NAME = 'settings';
let db = null;

// DOM Elements
const selectInputFolderBtn = document.getElementById('selectInputFolderBtn');
const selectOutputFolderBtn = document.getElementById('selectOutputFolderBtn');
const selectedInputPath = document.getElementById('selectedInputPath');
const selectedOutputPath = document.getElementById('selectedOutputPath');
const filesSection = document.getElementById('filesSection');
const filesInfo = document.getElementById('filesInfo');
const speakersSection = document.getElementById('speakersSection');
const speakersList = document.getElementById('speakersList');
const extractSamplesBtn = document.getElementById('extractSamplesBtn');
const resetBtn = document.getElementById('resetBtn');
const progressSection = document.getElementById('progressSection');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const resultsSection = document.getElementById('resultsSection');
const resultsInfo = document.getElementById('resultsInfo');
const newExtractionBtn = document.getElementById('newExtractionBtn');

// Event Listeners
selectInputFolderBtn.addEventListener('click', handleSelectInputFolder);
selectOutputFolderBtn.addEventListener('click', handleSelectOutputFolder);
extractSamplesBtn.addEventListener('click', handleExtractSamples);
resetBtn.addEventListener('click', handleReset);
newExtractionBtn.addEventListener('click', handleReset);

// Initialize on page load
initializeApp();

/**
 * Initialize IndexedDB
 */
function initDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => {
      db = request.result;
      resolve(db);
    };

    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME);
      }
    };
  });
}

/**
 * Save output folder handle to IndexedDB
 */
async function saveOutputFolderHandle(handle) {
  if (!db) await initDB();

  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_NAME], 'readwrite');
    const store = transaction.objectStore(STORE_NAME);
    const request = store.put(handle, 'outputFolderHandle');

    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

/**
 * Load output folder handle from IndexedDB
 */
async function loadOutputFolderHandle() {
  if (!db) await initDB();

  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_NAME], 'readonly');
    const store = transaction.objectStore(STORE_NAME);
    const request = store.get('outputFolderHandle');

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

/**
 * Initialize the application
 */
async function initializeApp() {
  try {
    // Initialize IndexedDB
    await initDB();

    // Try to restore saved output folder
    await restoreOutputFolder();

    console.log('Sample Splitter initialized');
  } catch (error) {
    console.error('Initialization error:', error);
  }
}

/**
 * Restore previously selected output folder
 */
async function restoreOutputFolder() {
  try {
    const savedHandle = await loadOutputFolderHandle();

    if (!savedHandle) {
      console.log('No saved output folder found');
      return;
    }

    // Verify we still have permission
    const permission = await savedHandle.queryPermission({ mode: 'readwrite' });

    if (permission === 'granted') {
      // Permission already granted, use the folder
      state.outputFolderHandle = savedHandle;
      selectedOutputPath.textContent = savedHandle.name;
      selectedOutputPath.classList.add('has-path');

      await loadExistingSpeakers();
      checkCanProcess();

      console.log(`Restored output folder: ${savedHandle.name}`);
    } else if (permission === 'prompt') {
      // Need to request permission again
      const newPermission = await savedHandle.requestPermission({ mode: 'readwrite' });

      if (newPermission === 'granted') {
        state.outputFolderHandle = savedHandle;
        selectedOutputPath.textContent = savedHandle.name;
        selectedOutputPath.classList.add('has-path');

        await loadExistingSpeakers();
        checkCanProcess();

        console.log(`Restored output folder (re-requested permission): ${savedHandle.name}`);
      } else {
        console.log('Permission denied for saved output folder');
      }
    } else {
      console.log('Permission denied for saved output folder');
    }
  } catch (error) {
    console.log('Could not restore output folder:', error.message);
  }
}

/**
 * Handle input folder selection
 */
async function handleSelectInputFolder() {
  try {
    state.inputFolderHandle = await window.showDirectoryPicker({
      mode: 'read'
    });

    selectedInputPath.textContent = state.inputFolderHandle.name;
    selectedInputPath.classList.add('has-path');

    await findAndCheckInputFiles();

    if (state.files.transcriptJson && state.files.audioWav) {
      await parseTranscript();
      await loadAudio();
      checkCanProcess();
    }
  } catch (error) {
    console.error('Input folder selection error:', error);
    if (error.name !== 'AbortError') {
      alert(`Folder selection failed: ${error.message}`);
    }
  }
}

/**
 * Handle output folder selection
 */
async function handleSelectOutputFolder() {
  try {
    state.outputFolderHandle = await window.showDirectoryPicker({
      mode: 'readwrite'
    });

    selectedOutputPath.textContent = state.outputFolderHandle.name;
    selectedOutputPath.classList.add('has-path');

    // Save to IndexedDB for next time
    await saveOutputFolderHandle(state.outputFolderHandle);
    console.log(`Saved output folder: ${state.outputFolderHandle.name}`);

    // Try to load existing speakers.json
    await loadExistingSpeakers();

    checkCanProcess();
  } catch (error) {
    console.error('Output folder selection error:', error);
    if (error.name !== 'AbortError') {
      alert(`Folder selection failed: ${error.message}`);
    }
  }
}

/**
 * Find and check required files in input folder
 */
async function findAndCheckInputFiles() {
  const requiredFiles = [
    { key: 'transcriptJson', name: 'transcript_full.json', required: true },
    { key: 'audioWav', name: 'audio.wav', required: true }
  ];

  filesInfo.innerHTML = '';
  let allFound = true;

  for (const fileSpec of requiredFiles) {
    try {
      const fileHandle = await state.inputFolderHandle.getFileHandle(fileSpec.name);
      state.files[fileSpec.key] = fileHandle;

      filesInfo.innerHTML += `
        <div class="file-item found">
          <span class="file-item-icon">✅</span>
          <span>${fileSpec.name}</span>
        </div>
      `;
    } catch (error) {
      state.files[fileSpec.key] = null;
      allFound = false;

      filesInfo.innerHTML += `
        <div class="file-item missing">
          <span class="file-item-icon">❌</span>
          <span>${fileSpec.name} (not found)</span>
        </div>
      `;
    }
  }

  filesSection.style.display = 'block';

  if (!allFound) {
    throw new Error('Required files not found in the folder');
  }
}

/**
 * Merge consecutive segments for the same speaker
 * This combines segments that occur one after another without a gap
 */
function mergeConsecutiveSegments(segments) {
  if (segments.length === 0) return [];

  const merged = [];
  let currentSegment = { ...segments[0] };

  for (let i = 1; i < segments.length; i++) {
    const nextSegment = segments[i];

    // Check if segments are consecutive (with a small tolerance for timestamp rounding)
    // Consider segments consecutive if gap is less than 0.5 seconds
    const gap = nextSegment.start - currentSegment.end;

    if (gap < 0.5) {
      // Merge with current segment
      currentSegment.end = nextSegment.end;
      currentSegment.text = currentSegment.text + ' ' + nextSegment.text;
      currentSegment.duration = currentSegment.end - currentSegment.start;
    } else {
      // Save current segment and start a new one
      merged.push(currentSegment);
      currentSegment = { ...nextSegment };
    }
  }

  // Don't forget the last segment
  merged.push(currentSegment);

  return merged;
}

/**
 * Parse transcript_full.json and analyze segments
 */
async function parseTranscript() {
  try {
    const file = await state.files.transcriptJson.getFile();
    const content = await file.text();
    const transcript = JSON.parse(content);

    const segments = transcript.transcript || transcript.segments || [];

    // Group segments by speaker (in chronological order)
    const speakerSegmentsMap = {};

    for (const segment of segments) {
      const speaker = segment.speaker;

      // Skip UNKNOWN speakers
      if (!speaker || speaker === 'UNKNOWN') continue;

      if (!speakerSegmentsMap[speaker]) {
        speakerSegmentsMap[speaker] = [];
      }

      speakerSegmentsMap[speaker].push({
        start: segment.start,
        end: segment.end,
        text: segment.text || '',
        duration: segment.end - segment.start
      });
    }

    // For each speaker, merge consecutive segments and find the 3 longest
    state.speakers = Object.keys(speakerSegmentsMap).sort();
    state.speakerSegments = {};
    state.selectedSegments = {};

    for (const speaker of state.speakers) {
      // Merge consecutive segments first
      const mergedSegments = mergeConsecutiveSegments(speakerSegmentsMap[speaker]);

      console.log(`${speaker}: ${speakerSegmentsMap[speaker].length} raw segments → ${mergedSegments.length} merged segments`);

      // Sort by duration (longest first)
      mergedSegments.sort((a, b) => b.duration - a.duration);

      // Take top 3
      state.speakerSegments[speaker] = mergedSegments.slice(0, 3);

      // Initialize all as selected by default
      state.selectedSegments[speaker] = [true, true, true].slice(0, state.speakerSegments[speaker].length);
    }

    console.log(`Found ${state.speakers.length} speaker(s)`);
    console.log('Speaker segments:', state.speakerSegments);

  } catch (error) {
    console.error('Transcript parsing error:', error);
    throw new Error(`Failed to parse transcript_full.json: ${error.message}`);
  }
}

/**
 * Load audio.wav file
 */
async function loadAudio() {
  try {
    updateProgress(0, 100, 'Loading audio file...');
    progressSection.style.display = 'block';

    const file = await state.files.audioWav.getFile();
    const arrayBuffer = await file.arrayBuffer();

    updateProgress(50, 100, 'Decoding audio...');

    const audioContext = new AudioContext();
    state.audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

    if (!validateAudioBuffer(state.audioBuffer)) {
      throw new Error('Invalid audio file');
    }

    console.log(`Audio loaded: ${state.audioBuffer.duration.toFixed(1)}s, ${state.audioBuffer.sampleRate}Hz`);

    updateProgress(100, 100, 'Audio loaded!');

    setTimeout(() => {
      progressSection.style.display = 'none';
    }, 500);

  } catch (error) {
    progressSection.style.display = 'none';
    console.error('Audio loading error:', error);
    throw new Error(`Failed to load audio.wav: ${error.message}`);
  }
}

/**
 * Load existing speakers.json if present
 */
async function loadExistingSpeakers() {
  try {
    const fileHandle = await state.outputFolderHandle.getFileHandle('speakers.json');
    const file = await fileHandle.getFile();
    const content = await file.text();
    const data = JSON.parse(content);

    state.existingSpeakers = {};
    if (data.speakers && Array.isArray(data.speakers)) {
      for (const speaker of data.speakers) {
        state.existingSpeakers[speaker.id] = speaker;
      }
    }

    console.log(`Loaded ${Object.keys(state.existingSpeakers).length} existing speaker(s)`);
  } catch (error) {
    // speakers.json doesn't exist yet - that's okay
    console.log('No existing speakers.json found (will create new)');
    state.existingSpeakers = {};
  }
}

/**
 * Check if we can start processing
 */
function checkCanProcess() {
  if (state.inputFolderHandle && state.outputFolderHandle && state.audioBuffer && state.speakers.length > 0) {
    displaySpeakers();
  }
}

/**
 * Display speaker list with segment selection
 */
function displaySpeakers() {
  speakersList.innerHTML = '';

  state.speakers.forEach((speaker) => {
    const segments = state.speakerSegments[speaker];

    const card = document.createElement('div');
    card.className = 'speaker-card';

    let segmentsHtml = '';
    segments.forEach((segment, index) => {
      const duration = segment.duration;
      const isLong = duration > 300; // >5 minutes
      const displayDuration = isLong ? `${formatDuration(duration)} → 5:00` : formatDuration(duration);
      const warningClass = isLong ? 'long-segment' : '';

      const sampleText = segment.text.substring(0, 100) + (segment.text.length > 100 ? '...' : '');

      segmentsHtml += `
        <div class="segment-item ${warningClass}">
          <div class="segment-header">
            <input
              type="checkbox"
              class="segment-checkbox"
              data-speaker="${speaker}"
              data-index="${index}"
              ${state.selectedSegments[speaker][index] ? 'checked' : ''}
            />
            <span class="segment-duration">${displayDuration}</span>
            <button class="btn-play-segment" data-speaker="${speaker}" data-index="${index}" title="Play this segment">
              ▶️ Play
            </button>
          </div>
          <div class="segment-text">"${sampleText}"</div>
          ${isLong ? '<div class="segment-warning">⚠️ Will be truncated to 5:00</div>' : ''}
        </div>
      `;
    });

    card.innerHTML = `
      <div class="speaker-header">
        <div class="speaker-id">${speaker}</div>
        <div class="speaker-input">
          <input
            type="text"
            placeholder="Enter real name..."
            data-speaker="${speaker}"
            class="speaker-name-input"
            value="${state.speakerNames[speaker] || ''}"
          />
        </div>
      </div>
      <div class="segments-list">
        <div class="segments-label">Select segments to extract:</div>
        ${segmentsHtml}
      </div>
    `;

    speakersList.appendChild(card);
  });

  // Attach event listeners
  document.querySelectorAll('.speaker-name-input').forEach(input => {
    input.addEventListener('input', handleSpeakerNameInput);
  });

  document.querySelectorAll('.segment-checkbox').forEach(checkbox => {
    checkbox.addEventListener('change', handleSegmentCheckboxChange);
  });

  document.querySelectorAll('.btn-play-segment').forEach(button => {
    button.addEventListener('click', handlePlaySegment);
  });

  speakersSection.style.display = 'block';
  checkExtractButtonState();
}

/**
 * Handle speaker name input
 */
function handleSpeakerNameInput(event) {
  const input = event.target;
  const speaker = input.dataset.speaker;
  const name = input.value.trim();

  if (name) {
    state.speakerNames[speaker] = name;
    input.classList.add('filled');
  } else {
    delete state.speakerNames[speaker];
    input.classList.remove('filled');
  }

  checkExtractButtonState();
}

/**
 * Handle segment checkbox change
 */
function handleSegmentCheckboxChange(event) {
  const checkbox = event.target;
  const speaker = checkbox.dataset.speaker;
  const index = parseInt(checkbox.dataset.index);

  state.selectedSegments[speaker][index] = checkbox.checked;

  checkExtractButtonState();
}

/**
 * Check if extract button should be enabled
 */
function checkExtractButtonState() {
  // At least one speaker must have a name and at least one selected segment
  let canExtract = false;

  for (const speaker of state.speakers) {
    const hasName = state.speakerNames[speaker] && state.speakerNames[speaker].length > 0;
    const hasSelectedSegments = state.selectedSegments[speaker].some(selected => selected);

    if (hasName && hasSelectedSegments) {
      canExtract = true;
      break;
    }
  }

  extractSamplesBtn.disabled = !canExtract;
}

/**
 * Play segment
 */
async function handlePlaySegment(event) {
  const button = event.currentTarget;
  const speaker = button.dataset.speaker;
  const index = parseInt(button.dataset.index);

  // If this button is currently playing, stop it
  if (button.classList.contains('playing')) {
    stopPlayback(button);
    return;
  }

  const segment = state.speakerSegments[speaker][index];

  try {
    // Show loading state
    button.disabled = true;
    button.innerHTML = '⏳ Loading...';

    // Create audio element if needed
    if (!state.audioElement) {
      const audioBlob = new Blob([await state.files.audioWav.getFile().then(f => f.arrayBuffer())], { type: 'audio/wav' });
      const audioUrl = URL.createObjectURL(audioBlob);
      state.audioElement = new Audio(audioUrl);
    }

    // Stop any other buttons that are playing
    document.querySelectorAll('.btn-play-segment.playing').forEach(otherButton => {
      if (otherButton !== button) {
        stopPlayback(otherButton);
      }
    });

    // Remove old event listeners if any
    if (state.audioElement._stopHandler) {
      state.audioElement.removeEventListener('timeupdate', state.audioElement._stopHandler);
    }
    if (state.audioElement._endedHandler) {
      state.audioElement.removeEventListener('ended', state.audioElement._endedHandler);
    }
    if (state.audioElement._pauseHandler) {
      state.audioElement.removeEventListener('pause', state.audioElement._pauseHandler);
    }

    // Stop any current playback
    state.audioElement.pause();
    state.audioElement.currentTime = 0;

    // Seek to segment start
    state.audioElement.currentTime = segment.start;

    // Update button
    button.disabled = false;
    button.innerHTML = '⏸️ Stop';
    button.classList.add('playing');

    console.log(`Playing ${speaker} segment ${index}: ${segment.start}s - ${segment.end}s`);

    // Start playback
    await state.audioElement.play();

    // Stop at segment end (or 5 minutes max)
    const endTime = Math.min(segment.end, segment.start + 300);

    const stopHandler = () => {
      if (state.audioElement.currentTime >= endTime) {
        stopPlayback(button);
      }
    };

    const endedHandler = () => {
      stopPlayback(button);
    };

    const pauseHandler = () => {
      // Only reset button if pause wasn't triggered by our stopPlayback function
      if (!button.classList.contains('stopping')) {
        stopPlayback(button);
      }
    };

    // Store handlers on the element for cleanup
    state.audioElement._stopHandler = stopHandler;
    state.audioElement._endedHandler = endedHandler;
    state.audioElement._pauseHandler = pauseHandler;

    state.audioElement.addEventListener('timeupdate', stopHandler);
    state.audioElement.addEventListener('ended', endedHandler);
    state.audioElement.addEventListener('pause', pauseHandler);

  } catch (error) {
    console.error('Playback error:', error);
    alert(`Playback error: ${error.message}`);
    button.disabled = false;
    button.innerHTML = '▶️ Play';
    button.classList.remove('playing');
  }
}

/**
 * Stop playback and reset button
 */
function stopPlayback(button) {
  if (!state.audioElement) return;

  // Mark as stopping to prevent pause event from triggering
  button.classList.add('stopping');

  // Pause audio
  state.audioElement.pause();

  // Remove event listeners
  if (state.audioElement._stopHandler) {
    state.audioElement.removeEventListener('timeupdate', state.audioElement._stopHandler);
    state.audioElement._stopHandler = null;
  }
  if (state.audioElement._endedHandler) {
    state.audioElement.removeEventListener('ended', state.audioElement._endedHandler);
    state.audioElement._endedHandler = null;
  }
  if (state.audioElement._pauseHandler) {
    state.audioElement.removeEventListener('pause', state.audioElement._pauseHandler);
    state.audioElement._pauseHandler = null;
  }

  // Reset button
  button.innerHTML = '▶️ Play';
  button.classList.remove('playing');
  button.classList.remove('stopping');
}

/**
 * Handle extract samples
 */
async function handleExtractSamples() {
  try {
    extractSamplesBtn.disabled = true;
    speakersSection.style.display = 'none';
    progressSection.style.display = 'block';

    await performExtraction();

    progressSection.style.display = 'none';
    resultsSection.style.display = 'block';

  } catch (error) {
    console.error('Extraction error:', error);
    alert(`Error: ${error.message}`);
    progressSection.style.display = 'none';
    speakersSection.style.display = 'block';
    extractSamplesBtn.disabled = false;
  }
}

/**
 * Perform sample extraction
 */
async function performExtraction() {
  const results = [];
  let processed = 0;

  // Filter speakers with names and selected segments
  const speakersToProcess = state.speakers.filter(speaker => {
    const hasName = state.speakerNames[speaker] && state.speakerNames[speaker].length > 0;
    const hasSelectedSegments = state.selectedSegments[speaker].some(selected => selected);
    return hasName && hasSelectedSegments;
  });

  const totalSteps = speakersToProcess.length + 1; // +1 for speakers.json

  for (const speaker of speakersToProcess) {
    try {
      const speakerName = state.speakerNames[speaker];
      const speakerId = speakerNameToId(speakerName);

      if (!validateSpeakerId(speakerId)) {
        throw new Error(`Invalid speaker ID generated: ${speakerId}`);
      }

      updateProgress(processed, totalSteps, `Processing ${speakerName}...`);

      // Check if speaker folder exists
      let speakerFolderHandle;
      let folderExists = false;
      let existingSamplePaths = [];

      try {
        speakerFolderHandle = await state.outputFolderHandle.getDirectoryHandle(speakerId);
        folderExists = true;
      } catch (error) {
        folderExists = false;
      }

      // Find highest existing sample number
      let startSampleNumber = 1;

      if (folderExists) {
        // Ask if user wants to add new samples
        const addMore = confirm(`Speaker folder "${speakerId}" already exists. Add new samples to this speaker?`);
        if (!addMore) {
          results.push({
            speaker: speakerName,
            speakerId: speakerId,
            success: false,
            skipped: true,
            message: 'Skipped by user'
          });
          processed++;
          continue;
        }

        // Scan existing files to find highest sample number
        let highestNumber = 0;
        for await (const [name, handle] of speakerFolderHandle.entries()) {
          if (handle.kind === 'file' && name.startsWith('sample_') && name.endsWith('.wav')) {
            // Extract number from filename like "sample_03.wav"
            const match = name.match(/sample_(\d+)\.wav/);
            if (match) {
              const num = parseInt(match[1], 10);
              if (num > highestNumber) {
                highestNumber = num;
              }
              // Keep track of existing samples
              existingSamplePaths.push(`${speakerId}/${name}`);
            }
          }
        }

        // Start numbering from next available
        startSampleNumber = highestNumber + 1;
        console.log(`Found ${highestNumber} existing samples, starting from sample_${String(startSampleNumber).padStart(2, '0')}.wav`);

      } else {
        // Create speaker folder
        speakerFolderHandle = await state.outputFolderHandle.getDirectoryHandle(speakerId, { create: true });
      }

      // Extract selected segments
      const segments = state.speakerSegments[speaker];
      const selectedIndices = state.selectedSegments[speaker]
        .map((selected, index) => selected ? index : null)
        .filter(index => index !== null);

      const samplePaths = [];
      let sampleNumber = startSampleNumber;

      for (const index of selectedIndices) {
        const segment = segments[index];

        // Extract segment (max 5 minutes)
        const segmentBuffer = extractSegment(
          state.audioBuffer,
          segment.start,
          segment.end,
          300 // 5 minutes max
        );

        // Convert to WAV
        const wavBlob = await audioBufferToWav(segmentBuffer, 16000);

        // Save file
        const filename = `sample_${String(sampleNumber).padStart(2, '0')}.wav`;
        const fileHandle = await speakerFolderHandle.getFileHandle(filename, { create: true });
        const writable = await fileHandle.createWritable();
        await writable.write(wavBlob);
        await writable.close();

        samplePaths.push(`${speakerId}/${filename}`);
        sampleNumber++;
      }

      results.push({
        speaker: speakerName,
        speakerId: speakerId,
        success: true,
        samplesCount: samplePaths.length,
        samplePaths: samplePaths,
        existingSamplePaths: existingSamplePaths  // For merging in speakers.json
      });

      processed++;

    } catch (error) {
      console.error(`Error processing ${speaker}:`, error);
      results.push({
        speaker: state.speakerNames[speaker] || speaker,
        speakerId: speaker,
        success: false,
        error: error.message
      });
      processed++;
    }
  }

  // Update speakers.json
  updateProgress(processed, totalSteps, 'Updating speakers.json...');
  await updateSpeakersJson(results.filter(r => r.success && !r.skipped));
  processed++;

  updateProgress(totalSteps, totalSteps, 'Completed!');
  displayResults(results);
}

/**
 * Update or create speakers.json
 */
async function updateSpeakersJson(successfulExtractions) {
  try {
    // Load existing data or create new
    let speakersData = {
      version: "1.0",
      speakers: [],
      settings: {}
    };

    if (Object.keys(state.existingSpeakers).length > 0) {
      speakersData.speakers = Object.values(state.existingSpeakers);
    }

    // Add or update speakers
    for (const extraction of successfulExtractions) {
      const { speakerId, speaker, samplePaths, existingSamplePaths } = extraction;

      // Find existing speaker or create new
      let speakerEntry = speakersData.speakers.find(s => s.id === speakerId);

      if (speakerEntry) {
        // Update existing - merge old and new samples
        speakerEntry.name = speaker;

        // Merge existing samples with new ones
        const mergedSamples = [...existingSamplePaths, ...samplePaths];
        // Remove duplicates (just in case)
        speakerEntry.audio_samples = [...new Set(mergedSamples)];

        speakerEntry.updated_at = new Date().toISOString();

        console.log(`Updated speaker ${speakerId}: ${existingSamplePaths.length} existing + ${samplePaths.length} new = ${speakerEntry.audio_samples.length} total samples`);
      } else {
        // Create new
        speakerEntry = {
          id: speakerId,
          name: speaker,
          audio_samples: samplePaths,
          created_at: new Date().toISOString(),
          metadata: {}
        };
        speakersData.speakers.push(speakerEntry);

        console.log(`Created new speaker ${speakerId} with ${samplePaths.length} samples`);
      }
    }

    // Write speakers.json
    const fileHandle = await state.outputFolderHandle.getFileHandle('speakers.json', { create: true });
    const writable = await fileHandle.createWritable();
    await writable.write(JSON.stringify(speakersData, null, 2));
    await writable.close();

    console.log('speakers.json updated successfully');

  } catch (error) {
    console.error('Error updating speakers.json:', error);
    throw new Error(`Failed to update speakers.json: ${error.message}`);
  }
}

/**
 * Display extraction results
 */
function displayResults(results) {
  resultsInfo.innerHTML = '';

  const successCount = results.filter(r => r.success && !r.skipped).length;
  const skippedCount = results.filter(r => r.skipped).length;
  const totalCount = results.length;

  // Overall stats
  resultsInfo.innerHTML += `
    <div class="result-item success">
      <span class="result-item-icon">✅</span>
      <div>
        <strong>Extraction completed!</strong>
        <br>
        <small>Successfully processed: ${successCount} speaker(s)</small>
        ${skippedCount > 0 ? `<br><small>Skipped: ${skippedCount} speaker(s)</small>` : ''}
      </div>
    </div>
  `;

  // Per-speaker details
  results.forEach(result => {
    if (result.skipped) {
      resultsInfo.innerHTML += `
        <div class="result-item warning">
          <span class="result-item-icon">⚠️</span>
          <div>
            ${result.speaker} (${result.speakerId})
            <br><small>${result.message}</small>
          </div>
        </div>
      `;
    } else if (result.success) {
      const isAddingToExisting = result.existingSamplePaths && result.existingSamplePaths.length > 0;
      const totalSamples = isAddingToExisting
        ? result.existingSamplePaths.length + result.samplesCount
        : result.samplesCount;

      resultsInfo.innerHTML += `
        <div class="result-item success">
          <span class="result-item-icon">✅</span>
          <div>
            ${result.speaker} (${result.speakerId})
            <br><small>${result.samplesCount} new sample(s) added${isAddingToExisting ? ` (${totalSamples} total)` : ''}</small>
          </div>
        </div>
      `;
    } else {
      resultsInfo.innerHTML += `
        <div class="result-item error">
          <span class="result-item-icon">❌</span>
          <div>
            ${result.speaker}
            <br><small>Error: ${result.error}</small>
          </div>
        </div>
      `;
    }
  });

  // speakers.json status
  resultsInfo.innerHTML += `
    <div class="result-item success">
      <span class="result-item-icon">📝</span>
      <div>
        <strong>speakers.json updated</strong>
        <br><small>Location: ${state.outputFolderHandle.name}/speakers.json</small>
      </div>
    </div>
  `;
}

/**
 * Update progress
 */
function updateProgress(current, total, text) {
  const percent = (current / total) * 100;
  progressFill.style.width = `${percent}%`;
  progressText.textContent = text;
}

/**
 * Reset workflow
 */
function handleReset() {
  // Stop any playing segments
  document.querySelectorAll('.btn-play-segment.playing').forEach(button => {
    stopPlayback(button);
  });

  // Stop and cleanup audio element
  if (state.audioElement) {
    state.audioElement.pause();
    state.audioElement = null;
  }

  // Reset state
  state = {
    inputFolderHandle: null,
    outputFolderHandle: null,
    files: {
      transcriptJson: null,
      audioWav: null
    },
    audioBuffer: null,
    audioElement: null,
    speakers: [],
    speakerSegments: {},
    speakerNames: {},
    selectedSegments: {},
    existingSpeakers: {}
  };

  // Hide sections
  filesSection.style.display = 'none';
  speakersSection.style.display = 'none';
  progressSection.style.display = 'none';
  resultsSection.style.display = 'none';

  // Reset UI
  selectedInputPath.textContent = 'No folder selected';
  selectedInputPath.classList.remove('has-path');
  selectedOutputPath.textContent = 'No folder selected';
  selectedOutputPath.classList.remove('has-path');
  filesInfo.innerHTML = '';
  speakersList.innerHTML = '';
  resultsInfo.innerHTML = '';
  extractSamplesBtn.disabled = true;
}

// Check File System Access API support
if (!('showDirectoryPicker' in window)) {
  selectInputFolderBtn.disabled = true;
  selectOutputFolderBtn.disabled = true;
  selectInputFolderBtn.textContent = '❌ File System Access API not supported';
  selectOutputFolderBtn.textContent = '❌ File System Access API not supported';
  alert(
    'Your browser does not support the File System Access API.\n\n' +
    'Try using Google Chrome, Microsoft Edge, or another modern browser.'
  );
}
