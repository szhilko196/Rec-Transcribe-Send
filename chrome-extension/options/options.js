/**
 * Options page logic for MyRecV
 * Manages extension preferences
 */

import {
  getAllSettings,
  saveSettings,
  STORAGE_KEYS,
} from '../utils/storage.js';

import { NextCloudClient } from '../utils/nextcloud-client.js';

// DOM elements
const elements = {
  // Email
  userEmail: document.getElementById('userEmail'),
  userEmailError: document.getElementById('userEmailError'),

  selectDirectoryBtn: document.getElementById('selectDirectoryBtn'),
  selectedPath: document.getElementById('selectedPath'),

  audioFormatWav: document.getElementById('audioFormatWav'),
  audioFormatWebm: document.getElementById('audioFormatWebm'),

  videoQuality: document.getElementById('videoQuality'),
  showHistory: document.getElementById('showHistory'),

  // NextCloud elements
  nextcloudEnabled: document.getElementById('nextcloudEnabled'),
  nextcloudSettings: document.getElementById('nextcloudSettings'),
  nextcloudUrl: document.getElementById('nextcloudUrl'),
  nextcloudUrlError: document.getElementById('nextcloudUrlError'),
  nextcloudUsername: document.getElementById('nextcloudUsername'),
  authTypeToken: document.getElementById('authTypeToken'),
  authTypePassword: document.getElementById('authTypePassword'),
  tokenGroup: document.getElementById('tokenGroup'),
  passwordGroup: document.getElementById('passwordGroup'),
  nextcloudToken: document.getElementById('nextcloudToken'),
  nextcloudPassword: document.getElementById('nextcloudPassword'),
  nextcloudBasePath: document.getElementById('nextcloudBasePath'),
  nextcloudGenerateLink: document.getElementById('nextcloudGenerateLink'),
  nextcloudSyncHistory: document.getElementById('nextcloudSyncHistory'),
  testConnectionBtn: document.getElementById('testConnectionBtn'),
  connectionStatus: document.getElementById('connectionStatus'),
  showTokenBtn: document.getElementById('showTokenBtn'),
  showPasswordBtn: document.getElementById('showPasswordBtn'),

  configureShortcutsBtn: document.getElementById('configureShortcutsBtn'),

  saveBtn: document.getElementById('saveBtn'),
  saveStatus: document.getElementById('saveStatus'),

  reportIssueLink: document.getElementById('reportIssueLink'),
};

// Selected directory state
let selectedDirectoryName = null;

/**
 * Initialize settings page
 */
async function init() {
  // Load current settings
  await loadSettings();

  // Attach event listeners
  setupEventListeners();
}

/**
 * Load settings from storage
 */
async function loadSettings() {
  try {
    const settings = await getAllSettings();

    // Email
    elements.userEmail.value = settings.userEmail || '';

    // Audio format
    if (settings.audioFormat === 'wav') {
      elements.audioFormatWav.checked = true;
    } else {
      elements.audioFormatWebm.checked = true;
    }

    // Video quality
    elements.videoQuality.value = settings.videoQuality || '1080p';

    // History toggle
    elements.showHistory.checked = settings.showHistory !== false;

    // Selected directory
    if (settings.directoryName) {
      selectedDirectoryName = settings.directoryName;
      elements.selectedPath.textContent = `Directory selected: ${settings.directoryName}`;
      elements.selectedPath.classList.add('has-path');
    } else {
      selectedDirectoryName = null;
      elements.selectedPath.textContent = 'No folder selected. Files will be saved via Downloads.';
      elements.selectedPath.classList.remove('has-path');
    }

    // NextCloud settings
    elements.nextcloudEnabled.checked = settings.nextcloudEnabled || false;
    elements.nextcloudUrl.value = settings.nextcloudUrl || '';
    elements.nextcloudUsername.value = settings.nextcloudUsername || '';
    elements.nextcloudBasePath.value = settings.nextcloudBasePath || '/Recordings/';
    elements.nextcloudGenerateLink.checked = settings.nextcloudGenerateLink !== false;
    elements.nextcloudSyncHistory.checked = settings.nextcloudSyncHistory !== false;

    // Auth type
    if (settings.nextcloudAuthType === 'password') {
      elements.authTypePassword.checked = true;
    } else {
      elements.authTypeToken.checked = true;
    }

    // Token/password
    elements.nextcloudToken.value = settings.nextcloudToken || '';
    elements.nextcloudPassword.value = settings.nextcloudPassword || '';

    // Show/hide NextCloud settings
    updateNextCloudVisibility();

    // Show/hide token/password inputs
    updateAuthTypeVisibility();

    console.log('Settings loaded:', settings);
  } catch (error) {
    console.error('Error loading settings:', error);
    showStatus('Failed to load settings', 'error');
  }
}

/**
 * Configure event listeners
 */
function setupEventListeners() {
  // Directory selection
  elements.selectDirectoryBtn.addEventListener('click', handleSelectDirectory);

  // NextCloud enable/disable
  elements.nextcloudEnabled.addEventListener('change', updateNextCloudVisibility);

  // Switch authentication type
  elements.authTypeToken.addEventListener('change', updateAuthTypeVisibility);
  elements.authTypePassword.addEventListener('change', updateAuthTypeVisibility);

  // Show/hide token
  elements.showTokenBtn.addEventListener('click', () => {
    togglePasswordVisibility(elements.nextcloudToken, elements.showTokenBtn);
  });

  // Show/hide password
  elements.showPasswordBtn.addEventListener('click', () => {
    togglePasswordVisibility(elements.nextcloudPassword, elements.showPasswordBtn);
  });

  // Test NextCloud connection
  elements.testConnectionBtn.addEventListener('click', handleTestConnection);

  // Validate email while typing
  elements.userEmail.addEventListener('input', validateEmail);

  // Validate URL while typing
  elements.nextcloudUrl.addEventListener('input', validateNextCloudUrl);

  // Configure hotkeys
  elements.configureShortcutsBtn.addEventListener('click', () => {
    chrome.tabs.create({ url: 'chrome://extensions/shortcuts' });
  });

  // Report an issue
  elements.reportIssueLink.addEventListener('click', (e) => {
    e.preventDefault();
    chrome.tabs.create({ url: 'https://github.com/meeting-transcriber/issues' });
  });

  // Save settings
  elements.saveBtn.addEventListener('click', handleSaveSettings);

  // Reminder on change
  [
    elements.userEmail,
    elements.audioFormatWav,
    elements.audioFormatWebm,
    elements.videoQuality,
    elements.showHistory,
    elements.nextcloudEnabled,
    elements.nextcloudUrl,
    elements.nextcloudUsername,
    elements.authTypeToken,
    elements.authTypePassword,
    elements.nextcloudToken,
    elements.nextcloudPassword,
    elements.nextcloudBasePath,
    elements.nextcloudGenerateLink,
    elements.nextcloudSyncHistory,
  ].forEach(element => {
    element.addEventListener('change', () => {
      showStatus("Don't forget to save your changes", '');
    });
  });
}

/**
 * Handle directory selection
 */
async function handleSelectDirectory() {
  try {
    showStatus('Selecting directory...', '');

    // Check File System Access API support
    if (!('showDirectoryPicker' in window)) {
      showStatus('File System Access API is not supported in this browser', 'error');
      return;
    }

    // Call showDirectoryPicker directly from options page (window context)
    const directoryHandle = await window.showDirectoryPicker({
      mode: 'readwrite',
      startIn: 'downloads',
    });

    if (directoryHandle) {
      // Save directory name for display
      selectedDirectoryName = directoryHandle.name;

      // Notify the service worker that a handle was selected
      // Note: FileSystemDirectoryHandle cannot be posted via postMessage
      // It will stay in memory within this session only
      await chrome.runtime.sendMessage({
        action: 'directorySelected',
        // Do not pass the handle itself—it remains in the options page memory
      });

      elements.selectedPath.textContent = `Directory selected: ${directoryHandle.name}`;
      elements.selectedPath.classList.add('has-path');
      showStatus('Directory selected. Remember to click "Save settings"!', '');

      console.log('Directory selected:', directoryHandle.name);
    }
  } catch (error) {
    if (error.name === 'AbortError') {
      showStatus('Directory selection cancelled', '');
      console.log('User cancelled directory selection');
    } else {
      console.error('Directory selection error:', error);
      showStatus('Directory selection error: ' + error.message, 'error');
    }
  }
}

/**
 * Persist settings
 */
async function handleSaveSettings() {
  try {
    showStatus('Saving...', '');

    // Validate NextCloud settings when enabled
    if (elements.nextcloudEnabled.checked) {
      if (!validateNextCloudSettings()) {
        showStatus('✗ Check NextCloud settings', 'error');
        return;
      }
    }

    // Collect settings
    const settings = {
      // Email
      userEmail: elements.userEmail.value.trim(),

      audioFormat: elements.audioFormatWav.checked ? 'wav' : 'webm',
      videoQuality: elements.videoQuality.value,
      showHistory: elements.showHistory.checked,
      directoryName: selectedDirectoryName, // Store selected folder name

      // NextCloud settings
      nextcloudEnabled: elements.nextcloudEnabled.checked,
      nextcloudUrl: elements.nextcloudUrl.value.trim(),
      nextcloudUsername: elements.nextcloudUsername.value.trim(),
      nextcloudAuthType: elements.authTypeToken.checked ? 'token' : 'password',
      nextcloudToken: elements.nextcloudToken.value.trim(),
      nextcloudPassword: elements.nextcloudPassword.value.trim(),
      nextcloudBasePath: elements.nextcloudBasePath.value.trim() || '/Recordings/',
      nextcloudGenerateLink: elements.nextcloudGenerateLink.checked,
      nextcloudSyncHistory: elements.nextcloudSyncHistory.checked,
    };

    // Save
    await saveSettings(settings);

    showStatus('✓ Settings saved', 'success');

    console.log('Settings saved:', settings);
  } catch (error) {
    console.error('Failed to save settings:', error);
    showStatus('✗ Failed to save', 'error');
  }
}

/**
 * Update NextCloud settings visibility
 */
function updateNextCloudVisibility() {
  if (elements.nextcloudEnabled.checked) {
    elements.nextcloudSettings.classList.remove('hidden');
  } else {
    elements.nextcloudSettings.classList.add('hidden');
  }
}

/**
 * Update auth field visibility
 */
function updateAuthTypeVisibility() {
  if (elements.authTypeToken.checked) {
    elements.tokenGroup.classList.remove('hidden');
    elements.passwordGroup.classList.add('hidden');
  } else {
    elements.tokenGroup.classList.add('hidden');
    elements.passwordGroup.classList.remove('hidden');
  }
}

/**
 * Toggle password visibility
 */
function togglePasswordVisibility(inputElement, buttonElement) {
  if (inputElement.type === 'password') {
    inputElement.type = 'text';
    buttonElement.textContent = '🙈 Hide';
  } else {
    inputElement.type = 'password';
    buttonElement.textContent = '👁️ Show';
  }
}

/**
 * Validate email address
 */
function validateEmail() {
  const email = elements.userEmail.value.trim();

  if (!email) {
    // Email optional
    elements.userEmailError.textContent = '';
    elements.userEmail.classList.remove('error');
    return true;
  }

  // Simple email regex
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  if (!emailRegex.test(email)) {
    elements.userEmailError.textContent = 'Invalid email format';
    elements.userEmail.classList.add('error');
    return false;
  }

  elements.userEmailError.textContent = '';
  elements.userEmail.classList.remove('error');
  return true;
}

/**
 * Validate NextCloud URL
 */
function validateNextCloudUrl() {
  const url = elements.nextcloudUrl.value.trim();

  if (!url) {
    elements.nextcloudUrlError.textContent = '';
    elements.nextcloudUrl.classList.remove('error');
    return true;
  }

  // Ensure URL starts with https://
  if (!url.startsWith('https://')) {
    elements.nextcloudUrlError.textContent = 'URL must start with https://';
    elements.nextcloudUrl.classList.add('error');
    return false;
  }

  // Ensure URL is valid
  try {
    new URL(url);
    elements.nextcloudUrlError.textContent = '';
    elements.nextcloudUrl.classList.remove('error');
    return true;
  } catch (error) {
    elements.nextcloudUrlError.textContent = 'Invalid URL format';
    elements.nextcloudUrl.classList.add('error');
    return false;
  }
}

/**
 * Validate all NextCloud settings
 */
function validateNextCloudSettings() {
  // Validate URL first
  if (!validateNextCloudUrl()) {
    return false;
  }

  const url = elements.nextcloudUrl.value.trim();
  const username = elements.nextcloudUsername.value.trim();
  const token = elements.nextcloudToken.value.trim();
  const password = elements.nextcloudPassword.value.trim();
  const authType = elements.authTypeToken.checked ? 'token' : 'password';

  // Required fields
  if (!url) {
    alert('Enter the NextCloud server URL');
    elements.nextcloudUrl.focus();
    return false;
  }

  if (!username) {
    alert('Enter the username');
    elements.nextcloudUsername.focus();
    return false;
  }

  // Enforce token/password presence
  if (authType === 'token' && !token) {
    alert('Enter the App Password (Token)');
    elements.nextcloudToken.focus();
    return false;
  }

  if (authType === 'password' && !password) {
    alert('Enter the password');
    elements.nextcloudPassword.focus();
    return false;
  }

  return true;
}

/**
 * Test NextCloud connectivity
 */
async function handleTestConnection() {
  try {
    // Validate before testing
    if (!validateNextCloudSettings()) {
      return;
    }

    // Display testing status
    elements.connectionStatus.textContent = '🔄 Testing connection...';
    elements.connectionStatus.className = 'connection-status testing';
    elements.testConnectionBtn.disabled = true;

    // Gather data
    const url = elements.nextcloudUrl.value.trim();
    const username = elements.nextcloudUsername.value.trim();
    const authType = elements.authTypeToken.checked ? 'token' : 'password';
    const credential = authType === 'token'
      ? elements.nextcloudToken.value.trim()
      : elements.nextcloudPassword.value.trim();

    // Create client
    const client = new NextCloudClient(url, username, credential, '/Recordings/');

    // Test connection
    const result = await client.testConnection();

    if (result.success) {
      elements.connectionStatus.textContent = `✅ ${result.message}`;
      elements.connectionStatus.className = 'connection-status success';
      console.log('NextCloud connection succeeded:', result);
    } else {
      elements.connectionStatus.textContent = `❌ ${result.message}`;
      elements.connectionStatus.className = 'connection-status error';
      console.error('NextCloud connection failed:', result);
    }
  } catch (error) {
    console.error('Connection test error:', error);
    elements.connectionStatus.textContent = `❌ Error: ${error.message}`;
    elements.connectionStatus.className = 'connection-status error';
  } finally {
    elements.testConnectionBtn.disabled = false;
  }
}

/**
 * Show save status message
 */
function showStatus(message, type = '') {
  elements.saveStatus.textContent = message;
  elements.saveStatus.className = 'save-status';

  if (type === 'error') {
    elements.saveStatus.classList.add('error');
  }

  // Hide after 3 seconds
  if (message && type === 'success') {
    setTimeout(() => {
      elements.saveStatus.textContent = '';
    }, 3000);
  }
}

// Initialize on load
document.addEventListener('DOMContentLoaded', init);
