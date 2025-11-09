# MyRecV Extension Debugging Guide

## Console checks

### 1. Popup (extension window)

**Steps:**
1. Click the MyRecV icon in the browser toolbar
2. **Right-click** the popup window → **"Inspect"** (or press F12)
3. DevTools opens with the popup console

**Verify:**
- ❌ Are there any **red** error messages?
- ⚠️ Are there **yellow** warnings?
- Do you see logs like `MyRecV popup initialized` or `Popup loaded`?

**Common errors:**
```
❌ Failed to load module — import path problem
❌ chrome.runtime is undefined — Service Worker is not running
❌ Uncaught TypeError — code error
```

### 2. Service Worker (background script)

**Steps:**
1. Open Chrome → **chrome://extensions/**
2. Enable **Developer mode** in the top-right corner
3. Locate the **MyRecV** extension
4. Click the **"service worker"** link ("Inspect views: Service Worker")

**Verify:**
- ✅ The Service Worker should be **active** (not inactive)
- Do you see `MyRecV Service Worker initialized`?
- Any module import errors?

**Common errors:**
```
❌ Failed to load module script — incorrect module path
❌ import not found — module missing
❌ Syntax error in module — syntax issue
```

### 3. Button checks

Open the popup and **open the popup console** (right-click → Inspect), then:

#### "Settings" button
1. Click ⚙️ **Settings**
2. Console should show:
   - `Settings button clicked` (if logging is enabled)
   - The settings page should open

**If it fails:**
- Confirm `options/options.html` exists
- Check `"permissions": ["..."]` in manifest.json

#### "RECORD" button
1. Enter a task number (e.g., `TEST-123`)
2. Click **RECORD**
3. Console should show:
   - `Starting recording with:` + payload
   - `Sending message to background...`
   - A response from the Service Worker

**If it fails:**
- Ensure the Service Worker is active
- Check the Service Worker console for errors
- Confirm `chrome.runtime.sendMessage` is invoked

## Manual code checks

### Test 1: Verify imports

Open the popup console and run:

```javascript
// Confirm chrome APIs are available
console.log('chrome.runtime:', chrome.runtime);
console.log('chrome.storage:', chrome.storage);

// Confirm popup.js loaded
console.log('Elements:', document.getElementById('startBtn'));
console.log('Settings button:', document.getElementById('settingsBtn'));
```

**Expect:**
- `chrome.runtime: Object {...}`
- `chrome.storage: Object {...}`
- Buttons should not be `null`

### Test 2: Manual message

```javascript
chrome.runtime.sendMessage({ action: 'getRecordingState' }, (response) => {
  console.log('Response:', response);
});
```

**Expect:**
- If the Service Worker is alive: `Response: { isRecording: false, ... }`
- If not: error or no response

### Test 3: Event listeners

In the popup console execute:

```javascript
// Check buttons for attached listeners
const startBtn = document.getElementById('startBtn');
console.log('Start button:', startBtn);
console.log('Has listeners:', getEventListeners(startBtn));

const settingsBtn = document.getElementById('settingsBtn');
console.log('Settings button:', settingsBtn);
console.log('Has listeners:', getEventListeners(settingsBtn));
```

**Expect:**
- Buttons should have `click` listeners

## Typical issues and fixes

### Issue 1: "Buttons do nothing"

**Causes:**
1. ❌ JavaScript failed to load (import error)
2. ❌ Event listeners never attached
3. ❌ popup.js ran before DOM was ready

**Fix:**
- Inspect popup console for errors
- Ensure `DOMContentLoaded` fired
- Confirm `init()` executes

### Issue 2: "Service Worker inactive"

**Causes:**
1. ❌ Error in service-worker.js
2. ❌ Incorrect module imports
3. ❌ manifest.json misconfigured

**Fix:**
- Open chrome://extensions/
- Click **Reload**
- Review the Service Worker console

### Issue 3: "chrome.runtime.sendMessage has no response"

**Causes:**
1. ❌ Service Worker not running
2. ❌ Listener missing in Service Worker
3. ❌ Listener doesn’t return `true` for async responses

**Fix:**
- Ensure the Service Worker is active
- Confirm `chrome.runtime.onMessage.addListener` exists in service-worker.js
- Ensure the listener returns `true` for async replies

## Adding extra logging

If needed I can provide a build with additional console logging. Let me know where extra `console.log` statements would help.

## Symptom-to-cause quick reference

| Symptom                    | Likely cause                | Where to check         |
|----------------------------|-----------------------------|------------------------|
| Buttons not clickable      | CSS `pointer-events`        | popup.css              |
| Buttons do not react       | Missing event listeners     | Popup console          |
| Popup does not open        | Error in popup.js           | Popup console          |
| "Settings" not working     | options.html missing        | Popup console          |
| "Record" not working       | Service Worker inactive     | chrome://extensions/   |

## Next steps

1. **Open the popup console** (right-click → Inspect)
2. **Open the Service Worker console** (chrome://extensions → Service Worker)
3. **Copy every error** you see and send it over
4. I’ll fix the issues based on those logs
