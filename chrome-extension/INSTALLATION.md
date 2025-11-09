# MyRecV Installation Guide

## Quick setup

### Step 1: Prepare files

1. Make sure you have the full `chrome-extension/` folder with the project structure
2. **IMPORTANT**: Replace the SVG placeholder icons with real PNG files:
   - `assets/icons/icon16.png` (16x16 pixels)
   - `assets/icons/icon48.png` (48x48 pixels)
   - `assets/icons/icon128.png` (128x128 pixels)

### Step 2: Load into Chrome

1. Open the Chrome browser
2. Navigate to `chrome://extensions/`
3. Enable **Developer mode** in the top-right corner
4. Click **Load unpacked**
5. Select the folder `C:\prj\meeting-transcriber\chrome-extension\`
6. The extension should appear in the list as “MyRecV - Screen & Audio Recorder”

### Step 3: Verify installation

1. Confirm the MyRecV icon appears in the extensions toolbar
2. Click the icon — the popup form should open
3. Check the consoles for errors:
   - Right-click the popup → “Inspect”
   - Chrome Extensions → MyRecV → “Inspect views: Service Worker”

### Step 4: Initial configuration

1. Click the MyRecV icon
2. At the bottom of the popup, click “⚙️ Settings”
3. Click “Choose folder” and pick a directory for recordings
4. Adjust audio format and video quality as needed
5. Click “Save settings”

### Step 5: Configure hotkeys (optional)

1. Open `chrome://extensions/shortcuts`
2. Locate MyRecV
3. Configure shortcuts:
   - Start recording: default `Ctrl+Shift+R`
   - Stop recording: default `Ctrl+Shift+S`

## Testing

### Test 1: Screen + video recording

1. Click the MyRecV icon
2. Enter task number: `TEST-001`
3. Description: `Test recording`
4. Ensure “Audio only” is **unchecked**
5. Click “RECORD”
6. Select a screen/window to capture
7. Wait 10–15 seconds (timer should be running)
8. Click “STOP”
9. Verify the saved file: `TEST-001_Test-recording_[DATE]_[TIME].webm`

### Test 2: Audio-only recording

1. Open the popup
2. Enter task number: `TEST-002`
3. Check “Audio only”
4. Click “RECORD”
5. Allow microphone access
6. Speak into the microphone
7. Click “STOP”
8. Verify the file: `TEST-002_[DATE]_[TIME].webm`

### Test 3: Hotkeys

1. Press `Ctrl+Shift+R` — the popup should open
2. Fill out the form
3. Start recording
4. Press `Ctrl+Shift+S` — recording should stop

## Troubleshooting

### Issue: Extension fails to load

**Fix:**
- Confirm `manifest.json` is in the root of `chrome-extension/`
- Check the console for syntax errors in files
- Ensure all required files are present

### Issue: “Cannot read property 'sendMessage'”

**Fix:**
- Reload the extension: `chrome://extensions/` → “Reload” button
- Verify the Service Worker is running: Inspect views → Service Worker

### Issue: Screen recording doesn’t work

**Fix:**
- Check Chrome permissions: Settings → Privacy and security → Site settings → Permissions
- Make sure you grant access when prompted to choose a screen
- Inspect the Service Worker console for errors

### Issue: File does not save

**Fix:**
- Ensure you selected a folder in Settings
- Check write permissions for the chosen folder
- If using the Downloads API fallback, review Chrome download settings

### Issue: SVG icons not showing

**Fix:**
- Replace the SVG files with real PNG images
- Use any graphics editor or online converter
- Required sizes: 16x16, 48x48, 128x128 pixels

## Uninstalling

1. Open `chrome://extensions/`
2. Locate MyRecV
3. Click “Remove”

## Updating the extension

1. Modify the code
2. Go to `chrome://extensions/`
3. Locate MyRecV
4. Click the “Reload” icon
5. Confirm the changes applied

## Additional resources

- Full documentation: `chrome-extension/README.md`
- Project overview: `project_description.md`
- GitHub Issues: [create an issue](https://github.com/meeting-transcriber/issues)

---

**All set!** You’re ready to use MyRecV for meeting recordings! 🎙️🎬
