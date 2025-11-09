/**
 * Popup UI logic for MyRecV
 * Manages the extension UI and interacts with the background service worker
 */

import {
  getStorageValue,
  setStorageValue,
  STORAGE_KEYS,
  getAllSettings,
  getHistory,
  clearHistory as clearHistoryStorage
} from '../utils/storage.js';

import { formatDuration, formatFileSize } from '../utils/file-handler.js';

// DOM elements
const elements = {
  taskNumber: document.getElementById('taskNumber'),
  description: document.getElementById('description'),
  audioOnly: document.getElementById('audioOnly'),
  charCount: document.getElementById('charCount'),
  taskNumberError: document.getElementById('taskNumberError'),

  startBtn: document.getElementById('startBtn'),
  stopBtn: document.getElementById('stopBtn'),
  speakerRenameBtn: document.getElementById('speakerRenameBtn'),

  timer: document.getElementById('timer'),
  recordingIndicator: document.getElementById('recordingIndicator'),

  formSection: document.getElementById('formSection'),
  statusSection: document.getElementById('statusSection'),
  statusDetails: document.getElementById('statusDetails'),

  historySection: document.getElementById('historySection'),
  historyList: document.getElementById('historyList'),
  clearHistoryBtn: document.getElementById('clearHistoryBtn'),

  settingsBtn: document.getElementById('settingsBtn'),
  nextcloudBadge: document.getElementById('nextcloudBadge'),
};

// State
let state = {
  isRecording: false,
  startTime: null,
  timerInterval: null,
  keepAliveInterval: null, // Keep-alive interval for the service worker
};

/**
 * Initialize popup
 */
async function init() {
  console.log('[MyRecV] Popup initializing...');

  // Load settings
  const settings = await getAllSettings();
  console.log('[MyRecV] Settings loaded:', settings);

  // Show NextCloud badge when enabled
  console.log('[MyRecV] Checking NextCloud badge...');
  if (settings.nextcloudEnabled) {
    elements.nextcloudBadge.classList.remove('hidden');
  }

  // Reveal history section when enabled
  console.log('[MyRecV] Checking history section...');
  if (settings.showHistory) {
    elements.historySection.classList.remove('hidden');
    console.log('[MyRecV] Loading history...');
    await loadHistory();
    console.log('[MyRecV] History loaded');
  }

  // Restore last entered values
  console.log('[MyRecV] Loading last task data...');
  const lastTaskNumber = await getStorageValue(STORAGE_KEYS.LAST_TASK_NUMBER);
  const lastDescription = await getStorageValue(STORAGE_KEYS.LAST_DESCRIPTION);
  console.log('[MyRecV] Last task data loaded:', { lastTaskNumber, lastDescription });

  if (lastTaskNumber) {
    elements.taskNumber.value = lastTaskNumber;
  }

  if (lastDescription) {
    elements.description.value = lastDescription;
    updateCharCount();
  }

  // Check current recording state
  console.log('[MyRecV] Checking recording state...');
  try {
    const recordingState = await chrome.runtime.sendMessage({ action: 'getRecordingState' });
    console.log('[MyRecV] Recording state received:', recordingState);

    if (recordingState && recordingState.isRecording) {
      console.log('[MyRecV] Recording is active, updating UI...');
      updateUIForRecording(recordingState);
    } else {
      console.log('[MyRecV] No active recording');
    }
  } catch (error) {
    console.error('[MyRecV] Error getting recording state:', error);
    // Surface a helpful hint when the service worker is unavailable
    if (error.message && error.message.includes('Receiving end does not exist')) {
      console.error('[MyRecV] Service worker is not responding—try reloading the extension');
    }
  }

  // Register event listeners
  setupEventListeners();

  console.log('[MyRecV] Popup initialized successfully');
}

/**
 * Configure event listeners
 */
function setupEventListeners() {
  console.log('[MyRecV] Setting up event listeners...');

  // Start recording button
  elements.startBtn.addEventListener('click', handleStartRecording);
  console.log('[MyRecV] Start button listener attached');

  // Stop recording button
  elements.stopBtn.addEventListener('click', handleStopRecording);

  // Description character counter
  elements.description.addEventListener('input', updateCharCount);

  // Task number validation
  elements.taskNumber.addEventListener('input', validateTaskNumber);
  elements.taskNumber.addEventListener('blur', validateTaskNumber);

  // Settings button
  elements.settingsBtn.addEventListener('click', () => {
    console.log('[MyRecV] Settings button clicked');
    chrome.runtime.openOptionsPage();
  });
  console.log('[MyRecV] Settings button listener attached');

  // Speaker rename button
  elements.speakerRenameBtn.addEventListener('click', () => {
    console.log('[MyRecV] Speaker rename button clicked');
    chrome.tabs.create({
      url: chrome.runtime.getURL('speaker-rename/speaker-rename.html')
    });
  });
  console.log('[MyRecV] Speaker rename button listener attached');

  // Clear history
  elements.clearHistoryBtn.addEventListener('click', handleClearHistory);

  // Listen for background messages
  chrome.runtime.onMessage.addListener(handleBackgroundMessage);
}

/**
 * Handle recording start
 */
async function handleStartRecording() {
  console.log('[MyRecV] handleStartRecording called');

  // Validate inputs
  if (!validateTaskNumber()) {
    console.log('[MyRecV] Validation failed');
    return;
  }

  const taskNumber = elements.taskNumber.value.trim();
  const description = elements.description.value.trim();
  const audioOnly = elements.audioOnly.checked;

  // Persist for next launch
  await setStorageValue(STORAGE_KEYS.LAST_TASK_NUMBER, taskNumber);
  await setStorageValue(STORAGE_KEYS.LAST_DESCRIPTION, description);

  // IMPORTANT: request microphone permission here (UI context can show the prompt)
  // This warms up the permission so the offscreen document can use getUserMedia silently
  try {
    console.log('[MyRecV] Requesting microphone permission...');
    const micStream = await navigator.mediaDevices.getUserMedia({
      audio: true,
      video: false
    });
    console.log('[MyRecV] Microphone permission granted!');

    // Stop stream immediately—only the permission is needed here
    micStream.getTracks().forEach(track => track.stop());
    console.log('[MyRecV] Microphone permission obtained, stream released');
  } catch (micError) {
    console.warn('[MyRecV] Microphone permission denied or not available:', micError);

    // Ask the user whether to continue without microphone
    const continueWithoutMic = confirm(
      'Failed to access the microphone.\n\n' +
      'Possible reasons:\n' +
      '- Permission denied\n' +
      '- Microphone is in use\n' +
      '- Microphone is not connected\n\n' +
      'Continue recording WITHOUT microphone?\n' +
      '(Only screen and system audio will be captured)'
    );

    if (!continueWithoutMic) {
      console.log('[MyRecV] User cancelled recording due to microphone issue');
      return;
    }
  }

  // Send start command to background
  try {
    console.log('[MyRecV] Sending startRecording message...', {
      taskNumber,
      description,
      audioOnly,
    });

    const response = await chrome.runtime.sendMessage({
      action: 'startRecording',
      data: {
        taskNumber,
        description,
        audioOnly,
      },
    });

    console.log('[MyRecV] Response from background:', response);

    if (response.success) {
      console.log('[MyRecV] Recording started successfully, updating UI...');

      updateUIForRecording({
        isRecording: true,
        startTime: Date.now(),
        audioOnly,
      });
      console.log('[MyRecV] UI update completed');
    } else {
      // If recording is already active, offer a forced stop
      if (response.error && (
        response.error.includes('Запись уже идет') ||
        response.error.includes('Recording already in progress')
      )) {
        const forceStop = confirm(
          'An active recording was detected.\n\n' +
          'You may have closed the popup while recording.\n\n' +
          'Force stop the previous recording? (file will NOT be saved)'
        );

        if (forceStop) {
          await chrome.runtime.sendMessage({ action: 'forceStopRecording' });
          alert('Previous recording stopped. Try starting a new recording.');
        }
      } else {
        showError(response.error || 'Failed to start recording');
      }
    }
  } catch (error) {
    console.error('Error starting recording:', error);
    showError('Failed to communicate with the background service');
  }
}

/**
 * Handle stop recording
 */
async function handleStopRecording() {
  try {
    const response = await chrome.runtime.sendMessage({
      action: 'stopRecording',
    });

    if (response.success) {
      updateUIForIdle();

      // Refresh history list
      if (!elements.historySection.classList.contains('hidden')) {
        await loadHistory();
      }

      // Display notification
      showNotification('Recording finished', response.fileName);
    } else {
      showError(response.error || 'Failed to stop recording');
    }
  } catch (error) {
    console.error('Error stopping recording:', error);
    showError('Failed to communicate with the background service');
  }
}

/**
 * Update UI when recording is active
 */
function updateUIForRecording(recordingState) {
  console.log('[MyRecV] updateUIForRecording called', recordingState);

  state.isRecording = true;
  state.startTime = recordingState.startTime;

  // Toggle sections
  elements.formSection.classList.add('hidden');
  elements.statusSection.classList.add('active');

  // Toggle buttons
  elements.startBtn.classList.add('hidden');
  elements.stopBtn.classList.remove('hidden');

  // Activate indicator
  elements.recordingIndicator.classList.add('active');
  elements.timer.classList.add('recording');

  // Update status details
  elements.statusDetails.textContent = recordingState.audioOnly ? 'Audio only' : 'Video + Audio';

  // IMPORTANT for Yandex Browser: force a reflow/repaint
  // Ensures DOM updates apply immediately
  forceUIUpdate();

  // Start timer
  startTimer();

  // IMPORTANT: start keep-alive for the service worker
  startKeepAlive();
}

/**
 * Force UI update (compatibility helper)
 * Forces the browser to apply DOM changes immediately
 */
function forceUIUpdate() {
  // Method 1: trigger reflow by reading layout metrics
  void elements.timer.offsetHeight;
  void elements.recordingIndicator.offsetHeight;
  void elements.statusSection.offsetHeight;

  // Method 2: requestAnimationFrame to ensure repaint
  requestAnimationFrame(() => {
    // Additional reflow on the next frame
    void elements.timer.offsetHeight;
  });

  console.log('[MyRecV] UI update forced');
}

/**
 * Update UI when idle
 */
function updateUIForIdle() {
  state.isRecording = false;
  state.startTime = null;

  // Stop timer
  stopTimer();

  // Stop keep-alive
  stopKeepAlive();

  // Toggle sections
  elements.formSection.classList.remove('hidden');
  elements.statusSection.classList.remove('active');

  // Toggle buttons
  elements.startBtn.classList.remove('hidden');
  elements.stopBtn.classList.add('hidden');

  // Deactivate indicator
  elements.recordingIndicator.classList.remove('active');
  elements.timer.classList.remove('recording');

  // Reset timer display
  elements.timer.textContent = '00:00:00';
}

/**
 * Start timer
 */
function startTimer() {
  console.log('[MyRecV] Starting timer with startTime:', state.startTime);

  if (state.timerInterval) {
    clearInterval(state.timerInterval);
  }

  // IMPORTANT: update immediately (do not wait for first interval)
  updateTimerDisplay();

  // Then update every second
  state.timerInterval = setInterval(() => {
    updateTimerDisplay();
  }, 1000);
}

/**
 * Refresh timer display
 */
function updateTimerDisplay() {
  if (!state.startTime) return;

  const elapsed = Math.floor((Date.now() - state.startTime) / 1000);
  const formattedTime = formatDuration(elapsed);

  // Update text
  elements.timer.textContent = formattedTime;

  // IMPORTANT for Yandex Browser: force reflow for timer
  void elements.timer.offsetHeight;

  // console.log('[MyRecV] Timer updated:', formattedTime);
}

/**
 * Stop timer
 */
function stopTimer() {
  if (state.timerInterval) {
    clearInterval(state.timerInterval);
    state.timerInterval = null;
  }
}

/**
 * Start keep-alive for the service worker
 * Sends a ping every 20 seconds to keep the SW alive
 */
function startKeepAlive() {
  console.log('[MyRecV] Starting keep-alive for Service Worker');

  if (state.keepAliveInterval) {
    clearInterval(state.keepAliveInterval);
  }

  // Immediate first ping
  pingServiceWorker();

  // Then every 20 seconds
  state.keepAliveInterval = setInterval(() => {
    pingServiceWorker();
  }, 20000); // 20 seconds
}

/**
 * Stop keep-alive
 */
function stopKeepAlive() {
  console.log('[MyRecV] Stopping keep-alive');

  if (state.keepAliveInterval) {
    clearInterval(state.keepAliveInterval);
    state.keepAliveInterval = null;
  }
}

/**
 * Ping service worker to keep it active
 */
async function pingServiceWorker() {
  try {
    await chrome.runtime.sendMessage({ action: 'ping' });
    // Avoid logging successful pings to reduce noise
    // console.log('[MyRecV] Keep-alive ping sent');
  } catch (error) {
    console.warn('[MyRecV] Keep-alive ping failed:', error);
  }
}

/**
 * Update character counter
 */
function updateCharCount() {
  const count = elements.description.value.length;
  elements.charCount.textContent = count;

  if (count > 180) {
    elements.charCount.style.color = 'var(--error-color)';
  } else {
    elements.charCount.style.color = 'var(--text-secondary)';
  }
}

/**
 * Validate task number
 */
function validateTaskNumber() {
  const value = elements.taskNumber.value.trim();

  if (!value) {
    elements.taskNumber.classList.add('error');
    elements.taskNumberError.textContent = 'Task number is required';
    return false;
  }

  elements.taskNumber.classList.remove('error');
  elements.taskNumberError.textContent = '';
  return true;
}

/**
 * Load recording history
 */
async function loadHistory() {
  const history = await getHistory();

  if (!history || history.length === 0) {
    elements.historyList.innerHTML = '<div class="empty-state">No recordings yet</div>';
    return;
  }

  elements.historyList.innerHTML = history.map(record => {
    // Build NextCloud link if available
    let nextcloudLink = '';
    if (record.publicLink) {
      nextcloudLink = `
        <br>
        <a href="${record.publicLink}" class="history-item-link" target="_blank" title="Open public link">
          ☁️ NextCloud
        </a>
        <span class="history-item-link" data-link="${record.publicLink}" title="Copy link">
          📋 Copy
        </span>
      `;
    }

    return `
      <div class="history-item">
        <div class="history-item-title">${record.taskNumber}</div>
        <div class="history-item-details">
          ${record.description || 'No description'}<br>
          ${new Date(record.timestamp).toLocaleString('en-US')}<br>
          ${record.fileName}
          ${nextcloudLink}
        </div>
      </div>
    `;
  }).join('');

  // Attach copy handlers
  document.querySelectorAll('.history-item-link[data-link]').forEach(button => {
    button.addEventListener('click', (e) => {
      const link = e.target.dataset.link;
      copyToClipboard(link);
    });
  });
}

/**
 * Clear history
 */
async function handleClearHistory() {
  if (confirm('Clear entire recording history?')) {
    await clearHistoryStorage();
    await loadHistory();
  }
}

/**
 * Handle background messages
 */
function handleBackgroundMessage(message, sender, sendResponse) {
  if (message.action === 'recordingStateChanged') {
    if (message.isRecording) {
      updateUIForRecording(message);
    } else {
      updateUIForIdle();
    }
  }

  if (message.action === 'recordingError') {
    showError(message.error);
    updateUIForIdle();
  }
}

/**
 * Show error message
 */
function showError(errorMessage) {
  alert(`Error: ${errorMessage}`);
}

/**
 * Show informational notification
 */
function showNotification(title, message) {
  // TODO: replace with a toast notification if desired
  console.log(`${title}: ${message}`);
}

/**
 * Copy text to clipboard
 */
async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    // Display temporary notification
    showNotification('Copied', 'Link copied to clipboard');
    // Optional: add visual cue for copy action
  } catch (error) {
    console.error('Clipboard copy error:', error);
    showError('Failed to copy the link');
  }
}

// Initialize on load
console.log('[MyRecV] popup.js loaded, waiting for DOMContentLoaded...');
document.addEventListener('DOMContentLoaded', () => {
  console.log('[MyRecV] DOMContentLoaded fired');
  init().catch(error => {
    console.error('[MyRecV] Init error:', error);
  });
});
