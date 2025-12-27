/**
 * Offscreen Document Script
 * Handles screen/audio recording because the service worker cannot access DOM APIs
 */

import { ScreenRecorder } from './background/recorder.js';

// Helper for forwarding logs to the service worker (debugging)
function logToServiceWorker(level, ...args) {
  const message = args.map(arg =>
    typeof arg === 'object' ? JSON.stringify(arg) : String(arg)
  ).join(' ');

  console[level](...args); // Mirror into the offscreen console

  // Forward to the service worker for visibility
  chrome.runtime.sendMessage({
    action: 'offscreenLog',
    level: level,
    message: `[Offscreen] ${message}`,
    timestamp: new Date().toISOString()
  }).catch(() => {}); // Ignore send errors
}

logToServiceWorker('log', '========================================');
logToServiceWorker('log', 'Document loaded at:', new Date().toISOString());
logToServiceWorker('log', '========================================');

let recorder = null;

// Track offscreen document unload
window.addEventListener('beforeunload', () => {
  logToServiceWorker('error', '⚠️⚠️⚠️ Document is being UNLOADED!');
});

// Watch for pagehide event
window.addEventListener('pagehide', () => {
  logToServiceWorker('error', '⚠️ PAGEHIDE event fired!');
});

// Keep-alive: perform lightweight work so Chrome keeps the offscreen document alive
setInterval(() => {
  // Simple operation to prove activity
  const timestamp = Date.now();
  logToServiceWorker('log', '💓 Keep-alive heartbeat - recorder:', !!recorder);
}, 10000); // Every 10 seconds

// Periodically log recorder status
setInterval(() => {
  logToServiceWorker('log', 'Health check - recorder exists:', !!recorder);
  if (recorder) {
    logToServiceWorker('log', 'Recorder state seems OK');
  } else {
    logToServiceWorker('warn', '⚠️ Recorder is NULL!');
  }
}, 15000); // Every 15 seconds

// Listen for messages from the service worker
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  // IMPORTANT: process only messages addressed to the offscreen context
  // Otherwise the popup → SW and SW → offscreen traffic will be duplicated
  if (message.target !== 'offscreen') {
    return; // Ignore messages meant for other contexts
  }

  logToServiceWorker('log', 'Message received:', message.action);
  logToServiceWorker('log', 'Current recorder state:', recorder ? 'EXISTS' : 'NULL');

  (async () => {
    try {
      switch (message.action) {
        case 'startRecording':
          logToServiceWorker('log', 'Starting recording...');
          if (!recorder) {
            recorder = new ScreenRecorder();
            logToServiceWorker('log', 'Created new ScreenRecorder instance');
          } else {
            logToServiceWorker('log', 'Reusing existing ScreenRecorder instance');
          }
          // Pass videoBitrate and videoQuality from message
          await recorder.startRecording(
            message.audioOnly,
            message.videoBitrate || 800000,
            message.videoQuality || '1080p'
          );
          logToServiceWorker('log', `Recording started successfully (bitrate: ${message.videoBitrate || 800000} bps, quality: ${message.videoQuality || '1080p'})`);
          sendResponse({ success: true });
          break;

        case 'stopRecording':
          logToServiceWorker('log', '🛑 Stop recording requested');
          logToServiceWorker('log', '🛑 Recorder exists?', !!recorder);
          if (recorder) {
            logToServiceWorker('log', 'Stopping recorder...');
            const blob = await recorder.stopRecording();
            logToServiceWorker('log', 'Recorder stopped, blob size:', blob.size);

            // IMPORTANT: store the Blob globally for the subsequent download
            // We cannot pass the Blob via sendMessage, but we can keep it locally
            window.recordedBlob = blob;

            // Send only metadata back to the service worker
            logToServiceWorker('log', 'Sending metadata to service worker');
            sendResponse({
              success: true,
              type: blob.type,
              size: blob.size
            });
            recorder = null;
            logToServiceWorker('log', 'Recorder cleared, blob stored in window.recordedBlob');
          } else {
            logToServiceWorker('error', '❌ No active recording! Recorder is NULL!');
            sendResponse({ success: false, error: 'No active recording' });
          }
          break;

        case 'createBlobURL':
          logToServiceWorker('log', '🔗 Create Blob URL requested');
          try {
            if (!window.recordedBlob) {
              throw new Error('No recorded blob available');
            }

            // Create a Blob URL (supported in offscreen context)
            const url = URL.createObjectURL(window.recordedBlob);
            logToServiceWorker('log', 'Blob URL created:', url);

            // Save the URL so we can revoke it later
            window.recordedBlobURL = url;

            // Send the Blob URL to the service worker
            // The Blob URL format blob:chrome-extension://[id]/[uuid]
            // should remain valid within the extension
            sendResponse({ success: true, blobUrl: url });
          } catch (error) {
            logToServiceWorker('error', '❌ Error creating blob URL:', error.message);
            sendResponse({ success: false, error: error.message });
          }
          break;

        case 'revokeBlobURL':
          logToServiceWorker('log', '🗑️ Revoke Blob URL requested');
          if (window.recordedBlobURL) {
            URL.revokeObjectURL(window.recordedBlobURL);
            delete window.recordedBlob;
            delete window.recordedBlobURL;
            logToServiceWorker('log', 'Blob URL revoked and blob cleared');
          }
          sendResponse({ success: true });
          break;

        case 'getRecordingDuration':
          if (recorder) {
            sendResponse({ duration: recorder.getDuration() });
          } else {
            sendResponse({ duration: 0 });
          }
          break;

        case 'copyToClipboard':
          try {
            await navigator.clipboard.writeText(message.text);
            sendResponse({ success: true });
          } catch (error) {
            sendResponse({ success: false, error: error.message });
          }
          break;

        default:
          sendResponse({ success: false, error: 'Unknown action' });
      }
    } catch (error) {
      console.error('[Offscreen] Error:', error);
      sendResponse({ success: false, error: error.message });
    }
  })();

  return true; // Asynchronous response
});

console.log('[Offscreen] Ready to handle recording');
