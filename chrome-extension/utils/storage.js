/**
 * Storage utility for working with chrome.storage.local
 * Manages MyRecV extension settings
 */

// Keys for storing settings
export const STORAGE_KEYS = {
  SAVE_DIRECTORY_HANDLE: 'saveDirectoryHandle',
  DIRECTORY_NAME: 'directoryName', // Selected folder name for display
  AUDIO_FORMAT: 'audioFormat', // 'wav' or 'webm'
  VIDEO_QUALITY: 'videoQuality', // '720p', '1080p', '2k'
  SHOW_HISTORY: 'showHistory',
  RECORDING_HISTORY: 'recordingHistory',
  LAST_TASK_NUMBER: 'lastTaskNumber',
  LAST_DESCRIPTION: 'lastDescription',

  // Email used to send processing results
  USER_EMAIL: 'userEmail',

  // NextCloud settings
  NEXTCLOUD_ENABLED: 'nextcloudEnabled',
  NEXTCLOUD_URL: 'nextcloudUrl',
  NEXTCLOUD_USERNAME: 'nextcloudUsername',
  NEXTCLOUD_AUTH_TYPE: 'nextcloudAuthType', // 'token' or 'password'
  NEXTCLOUD_TOKEN: 'nextcloudToken',
  NEXTCLOUD_PASSWORD: 'nextcloudPassword',
  NEXTCLOUD_BASE_PATH: 'nextcloudBasePath',
  NEXTCLOUD_GENERATE_LINK: 'nextcloudGenerateLink',
  NEXTCLOUD_SYNC_HISTORY: 'nextcloudSyncHistory',
};

// Default settings
export const DEFAULT_SETTINGS = {
  audioFormat: 'wav',
  videoQuality: '1080p',
  showHistory: true,
  recordingHistory: [],

  // Email for receiving results
  userEmail: '',

  // NextCloud defaults
  nextcloudEnabled: false,
  nextcloudUrl: '',
  nextcloudUsername: '',
  nextcloudAuthType: 'token',
  nextcloudToken: '',
  nextcloudPassword: '',
  nextcloudBasePath: '/Recordings/',
  nextcloudGenerateLink: true,
  nextcloudSyncHistory: true,
};

/**
 * Retrieve a value from storage
 * @param {string} key - Setting key
 * @returns {Promise<any>}
 */
export async function getStorageValue(key) {
  try {
    const result = await chrome.storage.local.get(key);
    return result[key];
  } catch (error) {
    console.error(`Failed to get ${key} from storage:`, error);
    return null;
  }
}

/**
 * Save a value to storage
 * @param {string} key - Setting key
 * @param {any} value - Value to store
 * @returns {Promise<void>}
 */
export async function setStorageValue(key, value) {
  try {
    await chrome.storage.local.set({ [key]: value });
  } catch (error) {
    console.error(`Failed to save ${key} to storage:`, error);
    throw error;
  }
}

/**
 * Retrieve all settings
 * @returns {Promise<Object>}
 */
export async function getAllSettings() {
  try {
    const settings = await chrome.storage.local.get(Object.values(STORAGE_KEYS));
    // Merge with defaults
    return { ...DEFAULT_SETTINGS, ...settings };
  } catch (error) {
    console.error('Failed to fetch settings:', error);
    return DEFAULT_SETTINGS;
  }
}

/**
 * Persist settings
 * @param {Object} settings - Settings payload
 * @returns {Promise<void>}
 */
export async function saveSettings(settings) {
  try {
    await chrome.storage.local.set(settings);
  } catch (error) {
    console.error('Failed to save settings:', error);
    throw error;
  }
}

/**
 * Add a recording to history
 * @param {Object} recordingInfo - Recording metadata
 * @returns {Promise<void>}
 */
export async function addToHistory(recordingInfo) {
  try {
    const history = (await getStorageValue(STORAGE_KEYS.RECORDING_HISTORY)) || [];

    // Attach timestamp
    const record = {
      ...recordingInfo,
      timestamp: Date.now(),
    };

    // Prepend and limit to the 10 most recent entries
    history.unshift(record);
    const limitedHistory = history.slice(0, 10);

    await setStorageValue(STORAGE_KEYS.RECORDING_HISTORY, limitedHistory);
  } catch (error) {
    console.error('Failed to append to history:', error);
  }
}

/**
 * Retrieve recording history
 * @returns {Promise<Array>}
 */
export async function getHistory() {
  try {
    return (await getStorageValue(STORAGE_KEYS.RECORDING_HISTORY)) || [];
  } catch (error) {
    console.error('Failed to fetch history:', error);
    return [];
  }
}

/**
 * Clear history
 * @returns {Promise<void>}
 */
export async function clearHistory() {
  try {
    await setStorageValue(STORAGE_KEYS.RECORDING_HISTORY, []);
  } catch (error) {
    console.error('Failed to clear history:', error);
    throw error;
  }
}

/**
 * Retrieve NextCloud settings
 * @returns {Promise<Object>}
 */
export async function getNextCloudSettings() {
  try {
    const settings = await getAllSettings();
    return {
      enabled: settings.nextcloudEnabled || false,
      url: settings.nextcloudUrl || '',
      username: settings.nextcloudUsername || '',
      authType: settings.nextcloudAuthType || 'token',
      token: settings.nextcloudToken || '',
      password: settings.nextcloudPassword || '',
      basePath: settings.nextcloudBasePath || '/Recordings/',
      generateLink: settings.nextcloudGenerateLink !== false,
      syncHistory: settings.nextcloudSyncHistory !== false,
    };
  } catch (error) {
    console.error('Failed to fetch NextCloud settings:', error);
    return DEFAULT_SETTINGS;
  }
}
