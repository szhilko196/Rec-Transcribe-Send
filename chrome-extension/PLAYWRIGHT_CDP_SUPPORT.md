# Chrome Extension CDP Support for Meeting Auto Capture

This document describes modifications needed to enable the Chrome extension to receive recording commands from Playwright via CDP (Chrome DevTools Protocol).

## Modifications Required

### 1. Update manifest.json

Add `externally_connectable` to allow communication from web pages:

**File**: `chrome-extension/manifest.json`

**Add after line 65 (before the closing brace):**

```json
  ,
  "externally_connectable": {
    "matches": [
      "http://localhost/*",
      "https://localhost/*",
      "<all_urls>"
    ]
  }
```

**Complete updated manifest.json:**

```json
{
  "manifest_version": 3,
  "name": "MyRecV - Screen & Audio Recorder",
  "version": "1.0.1",
  "description": "Screen and audio recording for meeting transcription. Saves files with task metadata.",
  "author": "Meeting Transcriber Team",

  "permissions": [
    "storage",
    "notifications",
    "offscreen",
    "downloads",
    "activeTab",
    "tabCapture"
  ],

  "host_permissions": [
    "<all_urls>"
  ],

  "background": {
    "service_worker": "background/service-worker.js",
    "type": "module"
  },

  "action": {
    "default_icon": {
      "16": "assets/icons/icon16.png",
      "48": "assets/icons/icon48.png",
      "128": "assets/icons/icon128.png"
    },
    "default_title": "MyRecV - Start Recording"
  },

  "icons": {
    "16": "assets/icons/icon16.png",
    "48": "assets/icons/icon48.png",
    "128": "assets/icons/icon128.png"
  },

  "options_page": "options/options.html",

  "commands": {
    "start-recording": {
      "suggested_key": {
        "default": "Ctrl+Shift+R",
        "mac": "Command+Shift+R"
      },
      "description": "Start screen recording"
    },
    "stop-recording": {
      "suggested_key": {
        "default": "Ctrl+Shift+S",
        "mac": "Command+Shift+S"
      },
      "description": "Stop current recording"
    }
  },

  "web_accessible_resources": [
    {
      "resources": ["assets/*"],
      "matches": ["<all_urls>"]
    }
  ],

  "externally_connectable": {
    "matches": [
      "http://localhost/*",
      "https://localhost/*",
      "<all_urls>"
    ]
  }
}
```

### 2. Update service-worker.js

Add CDP command handlers for external recording control.

**File**: `chrome-extension/background/service-worker.js`

**Add these new actions to the `handleMessage` switch statement (around line 180):**

Find the section with:
```javascript
        default:
          response = { success: false, error: 'Unknown action' };
      }
```

**Replace with:**

```javascript
        // CDP Support: Start recording from external automation (Playwright)
        case 'START_RECORDING':
          console.log('[MyRecV SW] CDP: Start recording request received');
          console.log('[MyRecV SW] CDP: Message data:', message);

          // Extract meeting data from message
          const startData = {
            taskNumber: message.taskNumber || 'AUTO',
            description: message.description || 'Automated Meeting Recording',
            audioOnly: message.audioOnly || false
          };

          console.log('[MyRecV SW] CDP: Starting recording with data:', startData);
          response = await startRecording(startData);
          console.log('[MyRecV SW] CDP: Recording started, response:', response);
          break;

        // CDP Support: Stop recording from external automation (Playwright)
        case 'STOP_RECORDING':
          console.log('[MyRecV SW] CDP: Stop recording request received');
          response = await stopRecording();
          console.log('[MyRecV SW] CDP: Recording stopped, response:', response);
          break;

        default:
          response = { success: false, error: 'Unknown action' };
      }
```

## How It Works

### From Meeting Auto Capture Service

The Meeting Auto Capture service (Playwright) sends messages like this:

```python
# Start recording
page.evaluate("""
    (meetingData) => {
        return new Promise((resolve) => {
            chrome.runtime.sendMessage({
                action: 'START_RECORDING',
                taskNumber: meetingData.id,
                description: meetingData.subject
            }, (response) => {
                resolve(response || {success: true});
            });
        });
    }
""", meeting_data)

# Stop recording
page.evaluate("""
    () => {
        return new Promise((resolve) => {
            chrome.runtime.sendMessage({
                action: 'STOP_RECORDING'
            }, (response) => {
                resolve(response || {success: true});
            });
        });
    }
""")
```

### Communication Flow

```
Playwright (Python)
    ↓
page.evaluate() - Inject JavaScript
    ↓
chrome.runtime.sendMessage()
    ↓
Extension Service Worker - handleMessage()
    ↓
Switch statement - case 'START_RECORDING'
    ↓
startRecording() function
    ↓
Recording begins
```

## Testing

### 1. Manual Test from Browser Console

After loading the extension, open any page and run in console:

```javascript
// Test START_RECORDING
chrome.runtime.sendMessage(
  'YOUR_EXTENSION_ID',  // Replace with actual ID
  {
    action: 'START_RECORDING',
    taskNumber: 'TEST-001',
    description: 'Test Recording from Console'
  },
  (response) => {
    console.log('Response:', response);
  }
);

// Test STOP_RECORDING
chrome.runtime.sendMessage(
  'YOUR_EXTENSION_ID',
  {
    action: 'STOP_RECORDING'
  },
  (response) => {
    console.log('Response:', response);
  }
);
```

### 2. Test from Meeting Auto Capture

The Meeting Auto Capture service will automatically test this when joining a meeting.

Check logs:
```bash
# Extension logs
chrome://extensions/ → MyRecV → Inspect views: service worker

# Meeting Auto Capture logs
tail -f services/meeting-autocapture/logs/autocapture.log
```

## Troubleshooting

### Message Not Received

**Problem**: `chrome.runtime.sendMessage` doesn't work

**Solution**:
1. Check `externally_connectable` is in manifest.json
2. Reload extension: chrome://extensions/ → Reload
3. Check extension ID matches
4. Verify sender origin is allowed

### Recording Doesn't Start

**Problem**: Message received but recording doesn't start

**Solution**:
1. Check service worker logs: chrome://extensions/ → Inspect
2. Verify `startRecording()` function is called
3. Check if directory permission is granted in options
4. Ensure no recording is already in progress

### Extension Not Loaded in Playwright

**Problem**: Extension not loading in automated browser

**Solution**:
1. Check `MAC_CHROME_EXTENSION_PATH` in .env
2. Verify path is absolute
3. Check manifest.json is valid
4. Test loading extension manually first

## Security Considerations

- `externally_connectable` allows any page to send messages
- Extension validates all incoming messages
- Only specific actions (START_RECORDING, STOP_RECORDING) are exposed
- No sensitive data exposed through this interface

## Alternative: Keyboard Shortcuts

If CDP messages fail, the extension bridge falls back to keyboard shortcuts:
- `Ctrl+Shift+R` - Start recording
- `Ctrl+Shift+S` - Stop recording

This is already implemented in `extension_bridge.py`.

## Version History

- **v1.0.0**: Original version
- **v1.0.1**: Added CDP support for automation
