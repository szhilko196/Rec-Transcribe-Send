/**
 * File Handler utility for saving files
 * Uses the File System Access API to store recordings in a custom folder
 */

/**
 * Save recording (blob) locally
 * Attempts to use the File System Access API when directoryHandle is available,
 * otherwise falls back to the chrome.downloads API
 * @param {Blob} blob - File to save
 * @param {string} fileName - Target file name
 * @param {FileSystemDirectoryHandle} directoryHandle - Directory handle (may be null)
 * @returns {Promise<{success: boolean, path: string, method: string, error?: string}>}
 */
export async function saveRecording(blob, fileName, directoryHandle = null) {
  try {
    // Prefer File System Access API when a directory handle is available
    if (directoryHandle) {
      try {
        // Check write permission
        const hasPermission = await verifyDirectoryPermission(directoryHandle);

        if (hasPermission) {
          await saveFileToDirectory(blob, fileName, directoryHandle);
          return {
            success: true,
            path: fileName,
            method: 'fileSystem',
          };
        } else {
          console.warn('No permission to write to the directory, falling back to downloads');
        }
      } catch (fsError) {
        console.warn('File System API error, falling back to downloads:', fsError);
      }
    }

    // Fallback: use chrome.downloads API
    await saveFileViaDownloads(blob, fileName);
    return {
      success: true,
      path: fileName,
      method: 'downloads',
    };
  } catch (error) {
    console.error('Recording save error:', error);
    return {
      success: false,
      path: '',
      method: 'none',
      error: error.message,
    };
  }
}

/**
 * Generate a file name from metadata
 * Format: [TASK]_[DESCRIPTION]_mmmail(email)_[YYYY-MM-DD]_[HH-MM-SS].[ext]
 * @param {string} taskNumber - Task identifier
 * @param {string} description - Optional description
 * @param {boolean} audioOnly - Audio-only mode flag
 * @param {string} email - Optional user email for results
 * @returns {string}
 */
export function generateFileName(taskNumber, description, audioOnly, email = '') {
  const now = new Date();

  // Format date: YYYY-MM-DD
  const date = now.toISOString().split('T')[0];

  // Format time: HH-MM-SS
  const time = now.toTimeString().split(' ')[0].replace(/:/g, '-');

  // Sanitize description from illegal characters
  const cleanDescription = description
    ? description
        .replace(/[<>:"/\\|?*]/g, '-') // Replace invalid characters
        .replace(/\s+/g, '_') // Replace spaces with underscores
        .substring(0, 50) // Limit length
    : '';

  // Select extension
  const extension = audioOnly ? 'webm' : 'webm';

  // Build file name parts
  const parts = [
    taskNumber,
    cleanDescription,
  ];

  // Append email in _mmmail(email)_ format when provided
  if (email && email.trim()) {
    parts.push(`mmmail(${email.trim()})`);
  }

  // Append date and time
  parts.push(date);
  parts.push(time);

  // Remove empty segments
  const filteredParts = parts.filter(Boolean);

  return `${filteredParts.join('_')}.${extension}`;
}

/**
 * Persist a Blob to disk using the File System Access API
 * @param {Blob} blob - Data to store
 * @param {string} fileName - Target file name
 * @param {FileSystemDirectoryHandle} directoryHandle - Directory handle
 * @returns {Promise<string>} - Stored file path
 */
export async function saveFileToDirectory(blob, fileName, directoryHandle) {
  try {
    // Create the file inside the selected directory
    const fileHandle = await directoryHandle.getFileHandle(fileName, { create: true });

    // Open a writable stream
    const writable = await fileHandle.createWritable();

    // Write data
    await writable.write(blob);
    await writable.close();

    console.log(`File saved: ${fileName}`);
    return fileName;
  } catch (error) {
    console.error('File save error:', error);
    throw error;
  }
}

/**
 * Prompt the user to pick a directory for saving
 * @returns {Promise<FileSystemDirectoryHandle>}
 */
export async function requestDirectoryAccess() {
  try {
    if (!('showDirectoryPicker' in window)) {
      throw new Error('File System Access API is not supported in this browser');
    }

    const directoryHandle = await window.showDirectoryPicker({
      mode: 'readwrite',
      startIn: 'downloads',
    });

    return directoryHandle;
  } catch (error) {
    if (error.name === 'AbortError') {
      console.log('User cancelled directory selection');
      return null;
    }
    console.error('Directory selection error:', error);
    throw error;
  }
}

/**
 * Verify write permission for a directory
 * @param {FileSystemDirectoryHandle} directoryHandle
 * @returns {Promise<boolean>}
 */
export async function verifyDirectoryPermission(directoryHandle) {
  try {
    const options = { mode: 'readwrite' };

    // Check current permission
    if ((await directoryHandle.queryPermission(options)) === 'granted') {
      return true;
    }

    // Request permission from the user
    if ((await directoryHandle.requestPermission(options)) === 'granted') {
      return true;
    }

    return false;
  } catch (error) {
    console.error('Permission check error:', error);
    return false;
  }
}

/**
 * Fallback: save via the chrome.downloads API
 * @param {Object} blobMetadata - Blob metadata (size, type) - Blob itself lives in offscreen
 * @param {string} fileName - Target file name
 * @returns {Promise<void>}
 */
export async function saveFileViaDownloads(blobMetadata, fileName) {
  try {
    console.log('[FileHandler] Saving via downloads API...', {
      blobSize: blobMetadata.size,
      blobType: blobMetadata.type,
      fileName: fileName
    });

    // Step 1: request a Blob URL from the offscreen document (where URL.createObjectURL is allowed)
    const urlResponse = await chrome.runtime.sendMessage({
      action: 'createBlobURL',
      target: 'offscreen'
    });

    if (!urlResponse.success) {
      throw new Error(urlResponse.error || 'Failed to create blob URL');
    }

    console.log('[FileHandler] Blob URL received:', urlResponse.blobUrl);

    // Step 2: use the Blob URL with chrome.downloads (works in the service worker!)
    const downloadId = await chrome.downloads.download({
      url: urlResponse.blobUrl,
      filename: fileName,
      saveAs: true, // Показываем диалог выбора папки
    });

    console.log('[FileHandler] Download initiated, ID:', downloadId);

    // Step 3: wait for download to finish, then revoke the Blob URL
    // Use the onChanged event for tracking progress
    const cleanupPromise = new Promise((resolve) => {
      const listener = (delta) => {
        if (delta.id === downloadId && delta.state) {
          if (delta.state.current === 'complete' || delta.state.current === 'interrupted') {
            chrome.downloads.onChanged.removeListener(listener);

            // Revoke Blob URL inside the offscreen document
            chrome.runtime.sendMessage({
              action: 'revokeBlobURL',
              target: 'offscreen'
            }).then(() => {
              console.log('[FileHandler] Blob URL cleaned up');
              resolve();
            });
          }
        }
      };
      chrome.downloads.onChanged.addListener(listener);
    });

    // Fire and forget cleanup promise
    cleanupPromise.catch(err => console.warn('[FileHandler] Cleanup error:', err));

    console.log(`[FileHandler] File saved successfully: ${fileName}`);
  } catch (error) {
    console.error('[FileHandler] Downloads API error:', error);

    // Attempt to clean up on failure
    try {
      await chrome.runtime.sendMessage({
        action: 'revokeBlobURL',
        target: 'offscreen'
      });
    } catch (e) {}

    throw error;
  }
}

/**
 * Convert size to a human-readable string
 * @param {number} bytes - Size in bytes
 * @returns {string}
 */
export function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Convert duration to HH:MM:SS format
 * @param {number} seconds - Duration in seconds
 * @returns {string}
 */
export function formatDuration(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);

  return [h, m, s]
    .map(v => v.toString().padStart(2, '0'))
    .join(':');
}
