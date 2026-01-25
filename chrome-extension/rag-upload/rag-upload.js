/**
 * RAG Upload - Manual upload to OpenWebUI Knowledge Base
 *
 * This tool helps users manually upload meeting results to OpenWebUI
 * when automatic RAG indexing was skipped due to unrecognized speakers.
 */

// State
let state = {
  folderHandle: null,
  folderName: '',
  files: {
    transcriptJson: null,
    summaryMd: null,
    protocolMd: null,
    needToBeRag: null
  },
  speakersInfo: null
};

// DOM Elements
const selectFolderBtn = document.getElementById('selectFolderBtn');
const selectedFolderPath = document.getElementById('selectedFolderPath');
const filesSection = document.getElementById('filesSection');
const filesInfo = document.getElementById('filesInfo');
const ragMarkerInfo = document.getElementById('ragMarkerInfo');
const speakersInfo = document.getElementById('speakersInfo');
const uploadSection = document.getElementById('uploadSection');
const generateCmdBtn = document.getElementById('generateCmdBtn');
const commandSection = document.getElementById('commandSection');
const uploadCommand = document.getElementById('uploadCommand');
const copyCommandBtn = document.getElementById('copyCommandBtn');
const newUploadBtn = document.getElementById('newUploadBtn');
const pythonPath = document.getElementById('pythonPath');
const uploaderPath = document.getElementById('uploaderPath');

// Event Listeners
selectFolderBtn.addEventListener('click', handleSelectFolder);
generateCmdBtn.addEventListener('click', handleGenerateCommand);
copyCommandBtn.addEventListener('click', handleCopyCommand);
newUploadBtn.addEventListener('click', handleReset);

// Load saved settings
loadSettings();

/**
 * Load saved settings from chrome storage
 */
async function loadSettings() {
  try {
    const settings = await chrome.storage.local.get(['ragUploadPythonPath', 'ragUploadScriptPath']);
    if (settings.ragUploadPythonPath) {
      pythonPath.value = settings.ragUploadPythonPath;
    }
    if (settings.ragUploadScriptPath) {
      uploaderPath.value = settings.ragUploadScriptPath;
    }
  } catch (error) {
    console.error('Error loading settings:', error);
  }
}

/**
 * Save settings to chrome storage
 */
async function saveSettings() {
  try {
    await chrome.storage.local.set({
      ragUploadPythonPath: pythonPath.value,
      ragUploadScriptPath: uploaderPath.value
    });
  } catch (error) {
    console.error('Error saving settings:', error);
  }
}

/**
 * Handle folder selection
 */
async function handleSelectFolder() {
  try {
    state.folderHandle = await window.showDirectoryPicker({
      mode: 'read'
    });

    state.folderName = state.folderHandle.name;
    selectedFolderPath.textContent = state.folderName;
    selectedFolderPath.classList.add('has-path');

    await findAndCheckFiles();

  } catch (error) {
    console.error('Folder selection error:', error);
    if (error.name !== 'AbortError') {
      alert(`Folder selection failed: ${error.message}`);
    }
  }
}

/**
 * Find and check required files in the selected folder
 */
async function findAndCheckFiles() {
  const requiredFiles = [
    { key: 'transcriptJson', name: 'transcript_full.json', required: true },
    { key: 'summaryMd', name: 'summary.md', required: true },
    { key: 'protocolMd', name: 'protocol.md', required: true }
  ];

  filesInfo.innerHTML = '';
  let allFound = true;

  for (const fileSpec of requiredFiles) {
    try {
      const fileHandle = await state.folderHandle.getFileHandle(fileSpec.name);
      state.files[fileSpec.key] = fileHandle;

      filesInfo.innerHTML += `
        <div class="file-item found">
          <span class="file-item-icon">OK</span>
          <span>${fileSpec.name}</span>
        </div>
      `;
    } catch (error) {
      state.files[fileSpec.key] = null;
      allFound = false;

      filesInfo.innerHTML += `
        <div class="file-item missing">
          <span class="file-item-icon">MISSING</span>
          <span>${fileSpec.name}</span>
        </div>
      `;
    }
  }

  // Check for need_to_be_RAG.md marker
  try {
    const markerHandle = await state.folderHandle.getFileHandle('need_to_be_RAG.md');
    state.files.needToBeRag = markerHandle;

    // Parse marker file for speaker info
    const markerFile = await markerHandle.getFile();
    const markerContent = await markerFile.text();

    // Extract speakers info
    const recognizedMatch = markerContent.match(/### Recognized Speakers \((\d+)\)\n([\s\S]*?)(?=###|## Required)/);
    const unrecognizedMatch = markerContent.match(/### Unrecognized Speakers \((\d+)\)\n([\s\S]*?)(?=## Required)/);

    let speakersHtml = '<div class="speakers-summary">';
    if (recognizedMatch) {
      speakersHtml += `<p><strong>Recognized:</strong> ${recognizedMatch[1]} speakers</p>`;
    }
    if (unrecognizedMatch) {
      speakersHtml += `<p><strong>Unrecognized:</strong> ${unrecognizedMatch[1]} speakers</p>`;
    }
    speakersHtml += '</div>';

    speakersInfo.innerHTML = speakersHtml;
    ragMarkerInfo.style.display = 'block';

    // Add marker file to files list
    filesInfo.innerHTML += `
      <div class="file-item found">
        <span class="file-item-icon">INFO</span>
        <span>need_to_be_RAG.md (marker file)</span>
      </div>
    `;

  } catch (error) {
    state.files.needToBeRag = null;
    ragMarkerInfo.style.display = 'none';
  }

  filesSection.style.display = 'block';

  if (allFound) {
    uploadSection.style.display = 'block';
    commandSection.style.display = 'none';
  } else {
    uploadSection.style.display = 'none';
    commandSection.style.display = 'none';
    alert('Required files not found. Make sure this is a meeting results folder containing transcript_full.json, summary.md, and protocol.md.');
  }
}

/**
 * Handle generate command button click
 */
async function handleGenerateCommand() {
  await saveSettings();

  const pythonCmd = pythonPath.value || 'python';
  const scriptPath = uploaderPath.value || 'services/OpenWebUi/scripts/openwebui_uploader.py';
  const folderName = state.folderName;

  // Generate the command
  // Note: User needs to replace DATA_PATH with actual path
  const command = `${pythonCmd} "${scriptPath}" "DATA_PATH/results/${folderName}"`;

  uploadCommand.textContent = command;
  uploadSection.style.display = 'none';
  commandSection.style.display = 'block';
}

/**
 * Handle copy command button click
 */
async function handleCopyCommand() {
  const command = uploadCommand.textContent;

  try {
    await navigator.clipboard.writeText(command);
    copyCommandBtn.textContent = 'Copied!';
    setTimeout(() => {
      copyCommandBtn.textContent = 'Copy';
    }, 2000);
  } catch (error) {
    console.error('Copy failed:', error);
    // Fallback: select text for manual copy
    const range = document.createRange();
    range.selectNode(uploadCommand);
    window.getSelection().removeAllRanges();
    window.getSelection().addRange(range);
    alert('Press Ctrl+C to copy the selected command');
  }
}

/**
 * Reset the form for a new upload
 */
function handleReset() {
  state = {
    folderHandle: null,
    folderName: '',
    files: {
      transcriptJson: null,
      summaryMd: null,
      protocolMd: null,
      needToBeRag: null
    },
    speakersInfo: null
  };

  filesSection.style.display = 'none';
  uploadSection.style.display = 'none';
  commandSection.style.display = 'none';

  selectedFolderPath.textContent = 'No folder selected';
  selectedFolderPath.classList.remove('has-path');
  filesInfo.innerHTML = '';
  ragMarkerInfo.style.display = 'none';
  speakersInfo.innerHTML = '';
}

// Check File System Access API support
if (!('showDirectoryPicker' in window)) {
  selectFolderBtn.disabled = true;
  selectFolderBtn.textContent = 'File System Access API not supported';
  alert(
    'Your browser does not support the File System Access API.\n\n' +
    'Try using Google Chrome, Microsoft Edge, or another modern browser.'
  );
}

console.log('[MyRecV] RAG Upload tool initialized');
