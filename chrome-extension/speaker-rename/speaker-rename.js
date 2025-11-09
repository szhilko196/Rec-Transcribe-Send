/**
 * Speaker Rename - speaker renaming workflow
 */

// State
let state = {
  folderHandle: null,
  files: {
    protocolMd: null,
    summaryMd: null,
    transcriptTxt: null,
    transcriptJson: null,
    audioWav: null  // Optional - used for playback
  },
  speakers: [],
  speakerMappings: {}, // { 'SPEAKER_01': 'John Doe', ... }
  speakerTimestamps: {}, // { 'SPEAKER_01': { start: 10.5, end: 15.2 }, ... }
  audioElement: null  // HTML5 Audio element
};

// DOM Elements
const selectFolderBtn = document.getElementById('selectFolderBtn');
const selectedFolderPath = document.getElementById('selectedFolderPath');
const filesSection = document.getElementById('filesSection');
const filesInfo = document.getElementById('filesInfo');
const speakersSection = document.getElementById('speakersSection');
const speakersList = document.getElementById('speakersList');
const applyRenamingBtn = document.getElementById('applyRenamingBtn');
const resetBtn = document.getElementById('resetBtn');
const progressSection = document.getElementById('progressSection');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const resultsSection = document.getElementById('resultsSection');
const resultsInfo = document.getElementById('resultsInfo');
const newRenamingBtn = document.getElementById('newRenamingBtn');

// Event Listeners
selectFolderBtn.addEventListener('click', handleSelectFolder);
applyRenamingBtn.addEventListener('click', handleApplyRenaming);
resetBtn.addEventListener('click', handleReset);
newRenamingBtn.addEventListener('click', handleReset);

/**
 * Handle folder selection
 */
async function handleSelectFolder() {
  try {
    // File System Access API - folder picker
    state.folderHandle = await window.showDirectoryPicker({
      mode: 'readwrite'
    });

    selectedFolderPath.textContent = state.folderHandle.name;
    selectedFolderPath.classList.add('has-path');

    // Locate and verify required files
    await findAndCheckFiles();

    // Parse files when available
    if (state.files.transcriptJson) {
      await parseTranscript();
      displaySpeakers();
    }
  } catch (error) {
    console.error('Folder selection error:', error);
    if (error.name !== 'AbortError') { // Ignore user cancellation
      alert(`Folder selection failed: ${error.message}`);
    }
  }
}

/**
 * Discover and validate files inside the folder
 */
async function findAndCheckFiles() {
  const requiredFiles = [
    { key: 'protocolMd', name: 'protocol.md', required: true },
    { key: 'summaryMd', name: 'summary.md', required: true },
    { key: 'transcriptTxt', name: 'transcript_readable.txt', required: true },
    { key: 'transcriptJson', name: 'transcript_full.json', required: true }
  ];

  filesInfo.innerHTML = '';
  let allFound = true;

  for (const fileSpec of requiredFiles) {
    try {
      const fileHandle = await state.folderHandle.getFileHandle(fileSpec.name);
      state.files[fileSpec.key] = fileHandle;

      // Show detected file in UI
      filesInfo.innerHTML += `
        <div class="file-item found">
          <span class="file-item-icon">✅</span>
          <span>${fileSpec.name}</span>
        </div>
      `;
    } catch (error) {
      state.files[fileSpec.key] = null;
      allFound = false;

      // Highlight missing file
      filesInfo.innerHTML += `
        <div class="file-item missing">
          <span class="file-item-icon">❌</span>
          <span>${fileSpec.name} (not found)</span>
        </div>
      `;
    }
  }

  // Try to locate audio.wav (optional playback support)
  try {
    const audioHandle = await state.folderHandle.getFileHandle('audio.wav');
    state.files.audioWav = audioHandle;

    filesInfo.innerHTML += `
      <div class="file-item found">
        <span class="file-item-icon">✅</span>
        <span>audio.wav (playback available)</span>
      </div>
    `;
  } catch (error) {
    state.files.audioWav = null;

    filesInfo.innerHTML += `
      <div class="file-item optional">
        <span class="file-item-icon">ℹ️</span>
        <span>audio.wav (optional, for playback)</span>
      </div>
    `;
  }

  filesSection.style.display = 'block';

  if (!allFound) {
    throw new Error('Not all required files were found in the folder');
  }
}

/**
 * Parse transcript_full.json and extract speaker data
 */
async function parseTranscript() {
  try {
    const file = await state.files.transcriptJson.getFile();
    const content = await file.text();
    const transcript = JSON.parse(content);

    // Collect unique speakers
    const uniqueSpeakers = new Set();
    const speakerExamples = {};
    const speakerTimestamps = {};

    const segments = transcript.transcript || transcript.segments || [];

    for (const segment of segments) {
      const speaker = segment.speaker;
      if (speaker && speaker.startsWith('SPEAKER_')) {
        uniqueSpeakers.add(speaker);

        // Store timestamps for the first utterance for playback
        if (!speakerTimestamps[speaker] && segment.start !== undefined && segment.end !== undefined) {
          speakerTimestamps[speaker] = {
            start: segment.start,
            end: segment.end
          };
        }

        // Collect sample utterances up to ~250 characters
        if (!speakerExamples[speaker]) {
          speakerExamples[speaker] = [];
        }

        // Current combined length
        const currentText = speakerExamples[speaker].join(' ... ');
        const currentLength = currentText.length;

        // Keep appending segments until we reach ~250 characters
        if (currentLength < 250 && segment.text && segment.text.trim()) {
          speakerExamples[speaker].push(segment.text.trim());
        }
      }
    }

    // Sort speakers by numeric suffix
    state.speakers = Array.from(uniqueSpeakers).sort((a, b) => {
      const numA = parseInt(a.replace('SPEAKER_', ''));
      const numB = parseInt(b.replace('SPEAKER_', ''));
      return numA - numB;
    });

    // Store examples and timestamps in state
    state.speakerExamples = speakerExamples;
    state.speakerTimestamps = speakerTimestamps;

    console.log('Speakers found:', state.speakers);
    console.log('Speaker timestamps:', state.speakerTimestamps);
  } catch (error) {
    console.error('Transcript parsing error:', error);
    throw new Error(`Failed to read transcript_full.json: ${error.message}`);
  }
}

/**
 * Render the speaker list
 */
function displaySpeakers() {
  speakersList.innerHTML = '';

  state.speakers.forEach((speaker) => {
    // Join example lines with " ... "
    const exampleArray = state.speakerExamples[speaker] || [];
    const exampleText = exampleArray.length > 0 ? exampleArray.join(' ... ') : 'No sample available';
    const example = truncateText(exampleText, 250);

    const card = document.createElement('div');
    card.className = 'speaker-card';

    // Determine whether audio is available for this speaker
    const hasAudio = state.files.audioWav && state.speakerTimestamps[speaker];

    card.innerHTML = `
      <div class="speaker-header">
        <div class="speaker-id">${speaker}</div>
        <div class="speaker-input">
          <input
            type="text"
            placeholder="Enter participant name..."
            data-speaker="${speaker}"
            class="speaker-name-input"
          />
        </div>
      </div>
      <div class="speaker-example">
        <div class="speaker-example-label">
          Speech sample:
          ${hasAudio ? `
            <button class="btn-play-audio" data-speaker="${speaker}" title="Play this speaker's clip">
              ▶️ Play
            </button>
          ` : ''}
        </div>
        <div class="speaker-example-text">"${example}"</div>
      </div>
    `;

    speakersList.appendChild(card);
  });

  // Watch inputs for changes
  document.querySelectorAll('.speaker-name-input').forEach(input => {
    input.addEventListener('input', handleSpeakerInputChange);
  });

  // Attach handlers to playback buttons
  document.querySelectorAll('.btn-play-audio').forEach(button => {
    button.addEventListener('click', (e) => {
      const speaker = e.currentTarget.dataset.speaker;
      playAudioSegment(speaker, e.currentTarget);
    });
  });

  speakersSection.style.display = 'block';
  checkApplyButtonState();
}

/**
 * React to speaker name changes
 */
function handleSpeakerInputChange(event) {
  const input = event.target;
  const speaker = input.dataset.speaker;
  const name = input.value.trim();

  // Update mapping
  if (name) {
    state.speakerMappings[speaker] = name;
    input.classList.add('filled');
  } else {
    delete state.speakerMappings[speaker];
    input.classList.remove('filled');
  }

  checkApplyButtonState();
}

/**
 * Enable/disable the Apply button
 */
function checkApplyButtonState() {
  // Activate when at least one speaker has a mapping
  const hasAnyMapping = Object.keys(state.speakerMappings).length > 0;
  applyRenamingBtn.disabled = !hasAnyMapping;
}

/**
 * Play audio snippet for a speaker
 */
async function playAudioSegment(speaker, buttonElement) {
  try {
    // Ensure timestamps are present
    const timestamps = state.speakerTimestamps[speaker];
    if (!timestamps) {
      alert('Timestamps for this speaker are missing');
      return;
    }

    // Show loading state
    const originalText = buttonElement.innerHTML;
    buttonElement.disabled = true;
    buttonElement.innerHTML = '⏳ Loading...';

    // Load audio.wav on demand
    if (!state.audioElement) {
      const audioFile = await state.files.audioWav.getFile();
      const audioUrl = URL.createObjectURL(audioFile);
      state.audioElement = new Audio(audioUrl);

      console.log('Audio loaded:', audioUrl);
    }

    // Stop any current playback
    state.audioElement.pause();
    state.audioElement.currentTime = 0;

    // Seek to the start of the clip
    state.audioElement.currentTime = timestamps.start;

    // Update button label
    buttonElement.disabled = false;
    buttonElement.innerHTML = '⏸️ Stop';

    console.log(`Playing ${speaker}: ${timestamps.start}s - ${timestamps.end}s`);

    // Start playback
    await state.audioElement.play();

    // Stop playback when segment ends
    const stopHandler = () => {
      if (state.audioElement.currentTime >= timestamps.end) {
        state.audioElement.pause();
        state.audioElement.removeEventListener('timeupdate', stopHandler);
        buttonElement.innerHTML = originalText;
        console.log('Playback finished');
      }
    };

    // Restore button on natural end
    const endedHandler = () => {
      buttonElement.innerHTML = originalText;
      state.audioElement.removeEventListener('ended', endedHandler);
      state.audioElement.removeEventListener('timeupdate', stopHandler);
    };

    // Restore button when paused
    const pauseHandler = () => {
      buttonElement.innerHTML = originalText;
    };

    state.audioElement.addEventListener('timeupdate', stopHandler);
    state.audioElement.addEventListener('ended', endedHandler);
    state.audioElement.addEventListener('pause', pauseHandler);

  } catch (error) {
    console.error('Playback error:', error);
    alert(`Playback error: ${error.message}`);
    buttonElement.disabled = false;
    buttonElement.innerHTML = '▶️ Play';
  }
}

/**
 * Apply speaker renaming
 */
async function handleApplyRenaming() {
  try {
    applyRenamingBtn.disabled = true;
    speakersSection.style.display = 'none';
    progressSection.style.display = 'block';

    await performRenaming();

    progressSection.style.display = 'none';
    resultsSection.style.display = 'block';
  } catch (error) {
    console.error('Rename application error:', error);
    alert(`Error: ${error.message}`);
    progressSection.style.display = 'none';
    speakersSection.style.display = 'block';
    applyRenamingBtn.disabled = false;
  }
}

/**
 * Perform replacements across files
 */
async function performRenaming() {
  const filesToProcess = [
    { key: 'protocolMd', name: 'protocol.md' },
    { key: 'summaryMd', name: 'summary.md' },
    { key: 'transcriptTxt', name: 'transcript_readable.txt' },
    { key: 'transcriptJson', name: 'transcript_full.json' }
  ];

  const results = [];
  let processed = 0;

  for (const fileSpec of filesToProcess) {
    try {
      updateProgress(processed, filesToProcess.length, `Processing ${fileSpec.name}...`);

      const fileHandle = state.files[fileSpec.key];
      if (!fileHandle) {
        results.push({
          file: fileSpec.name,
          success: false,
          error: 'File not found'
        });
        continue;
      }

      // Read file
      const file = await fileHandle.getFile();
      let content = await file.text();

      // Apply replacements
      content = applySpeakerReplacements(content);

      // Write changes back to disk
      const writable = await fileHandle.createWritable();
      await writable.write(content);
      await writable.close();

      results.push({
        file: fileSpec.name,
        success: true
      });

      processed++;
      updateProgress(processed, filesToProcess.length, `${fileSpec.name} processed`);
    } catch (error) {
      console.error(`Processing error for ${fileSpec.name}:`, error);
      results.push({
        file: fileSpec.name,
        success: false,
        error: error.message
      });
      processed++;
    }
  }

  updateProgress(100, 100, 'Completed!');
  displayResults(results);
}

/**
 * Replace speaker placeholders with mapped names
 */
function applySpeakerReplacements(content) {
  let result = content;

  // Apply each mapping
  for (const [oldName, newName] of Object.entries(state.speakerMappings)) {
    // Replace SPEAKER_XX tokens with the provided name
    const regex = new RegExp(oldName, 'g');
    result = result.replace(regex, newName);
  }

  return result;
}

/**
 * Update progress bar
 */
function updateProgress(current, total, text) {
  const percent = (current / total) * 100;
  progressFill.style.width = `${percent}%`;
  progressText.textContent = text;
}

/**
 * Render results summary
 */
function displayResults(results) {
  resultsInfo.innerHTML = '';

  const successCount = results.filter(r => r.success).length;
  const totalCount = results.length;

  // Overall stats
  resultsInfo.innerHTML += `
    <div class="result-item success">
      <span class="result-item-icon">✅</span>
      <div>
        <strong>Files processed successfully: ${successCount} of ${totalCount}</strong>
        <br>
        <small>Speakers renamed: ${Object.keys(state.speakerMappings).length}</small>
      </div>
    </div>
  `;

  // Per-file details
  results.forEach(result => {
    const className = result.success ? 'result-item success' : 'result-item error';
    const icon = result.success ? '✅' : '❌';

    resultsInfo.innerHTML += `
      <div class="${className}">
        <span class="result-item-icon">${icon}</span>
        <div>
          ${result.file}
          ${result.error ? `<br><small>Error: ${result.error}</small>` : ''}
        </div>
      </div>
    `;
  });
}

/**
 * Reset workflow
 */
function handleReset() {
  // Stop playback if active
  if (state.audioElement) {
    state.audioElement.pause();
    state.audioElement = null;
  }

  // Reset state
  state = {
    folderHandle: null,
    files: {
      protocolMd: null,
      summaryMd: null,
      transcriptTxt: null,
      transcriptJson: null,
      audioWav: null
    },
    speakers: [],
    speakerMappings: {},
    speakerTimestamps: {},
    audioElement: null
  };

  // Hide sections
  filesSection.style.display = 'none';
  speakersSection.style.display = 'none';
  progressSection.style.display = 'none';
  resultsSection.style.display = 'none';

  // Reset UI labels
  selectedFolderPath.textContent = 'No folder selected';
  selectedFolderPath.classList.remove('has-path');
  filesInfo.innerHTML = '';
  speakersList.innerHTML = '';
  resultsInfo.innerHTML = '';
}

/**
 * Utility: truncate text
 */
function truncateText(text, maxLength) {
  if (text.length <= maxLength) {
    return text;
  }
  return text.substring(0, maxLength) + '...';
}

// Check File System Access API support
if (!('showDirectoryPicker' in window)) {
  selectFolderBtn.disabled = true;
  selectFolderBtn.textContent = '❌ File System Access API is not supported';
  alert(
    'Your browser does not support the File System Access API.\n\n' +
    'Try using Google Chrome, Microsoft Edge, or another modern browser.'
  );
}

console.log('Speaker Rename initialized');
