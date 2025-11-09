/**
 * Background Service Worker for MyRecV
 * Manages recording, commands, and file persistence
 */

import {
  generateFileName,
  saveFileToDirectory,
  verifyDirectoryPermission,
  requestDirectoryAccess,
  saveFileViaDownloads
} from '../utils/file-handler.js';
import {
  getStorageValue,
  setStorageValue,
  STORAGE_KEYS,
  getAllSettings,
  addToHistory
} from '../utils/storage.js';
import { DualSaver } from '../utils/dual-save.js';

// Global state
const state = {
  isRecording: false,
  recordingData: null, // { taskNumber, description, audioOnly, startTime }
  directoryHandle: null,
  offscreenDocument: null,
};

/**
 * Initialize the service worker
 */
async function init() {
  console.log('[MyRecV SW] ========================================');
  console.log('[MyRecV SW] Service Worker (RE)STARTING...');
  console.log('[MyRecV SW] Timestamp:', new Date().toISOString());
  console.log('[MyRecV SW] Chrome version:', navigator.userAgent);

  // Restore recording state after a SW restart
  await restoreRecordingState();

  // Load previously selected directory (if available)
  await loadDirectoryHandle();

  // Listen for messages from popup and other components
  chrome.runtime.onMessage.addListener(handleMessage);

  // Listen for keyboard shortcut commands
  chrome.commands.onCommand.addListener(handleCommand);

  // Handle extension install events
  chrome.runtime.onInstalled.addListener(handleInstall);

  // Handle clicks on the extension icon (opens the tab instead of the popup)
  chrome.action.onClicked.addListener(handleIconClick);

  console.log('[MyRecV SW] Service Worker initialized successfully');
  console.log('[MyRecV SW] Current state:', state);
  console.log('[MyRecV SW] ========================================');
}

/**
 * Handle extension icon clicks
 */
async function handleIconClick() {
  console.log('[MyRecV SW] Extension icon clicked');
  await openRecordingTab();
}

/**
 * Open the recording tab (or focus an existing one)
 */
async function openRecordingTab() {
  const extensionURL = chrome.runtime.getURL('tabs/index.html');

  // Look for an existing tab with the UI
  const tabs = await chrome.tabs.query({});
  const existingTab = tabs.find(tab => tab.url === extensionURL);

  if (existingTab) {
    // Focus the existing tab
    console.log('[MyRecV SW] Switching to existing tab:', existingTab.id);
    await chrome.tabs.update(existingTab.id, { active: true });
    await chrome.windows.update(existingTab.windowId, { focused: true });
  } else {
    // Create a new tab
    console.log('[MyRecV SW] Creating new recording tab');
    await chrome.tabs.create({ url: extensionURL });
  }
}

/**
 * Handle hotkey commands
 */
async function handleCommand(command) {
  console.log('Command received:', command);

  try {
    if (command === 'start-recording') {
      if (!state.isRecording) {
        // Open the tab so the user can provide recording details
        await openRecordingTab();
      }
    } else if (command === 'stop-recording') {
      if (state.isRecording) {
        await stopRecording();
      }
    }
  } catch (error) {
    console.error('Error handling command:', error);
  }
}

/**
 * Обработка сообщений
 */
function handleMessage(message, sender, sendResponse) {
  const { action, data } = message;

  // Avoid logging ping/offscreenLog actions to reduce noise
  if (action !== 'ping' && action !== 'offscreenLog') {
    console.log('[MyRecV SW] Message received:', action, data);
  }

  // Process asynchronously
  (async () => {
    try {
      let response;

      switch (action) {
        case 'startRecording':
          response = await startRecording(data);
          break;

        case 'stopRecording':
          response = await stopRecording();
          break;

        case 'getRecordingState':
          response = getRecordingState();
          break;

        case 'forceStopRecording':
          // Force-stop recording (without saving)
          console.log('[MyRecV SW] Force stop recording requested');
          state.isRecording = false;
          state.recordingData = null;
          await saveRecordingState();
          response = { success: true };
          break;

        case 'directorySelected':
          // Notification that the user selected a directory inside options
          // The FileSystemHandle lives in the options page, not in the service worker
          response = { success: true };
          console.log('[MyRecV SW] Directory selected notification received');
          break;

        case 'selectDirectory':
          // Deprecated: теперь showDirectoryPicker вызывается прямо из options.js
          response = { success: false, error: 'This action is deprecated. Use directorySelected instead.' };
          break;

        case 'ping':
          // Keep-alive ping from a tab — simply acknowledge
          response = { success: true, timestamp: Date.now() };
          // Skip logging to avoid noise
          sendResponse(response);
          return; // Выходим сразу

        case 'offscreenLog':
          // Logs forwarded from the offscreen document
          const logMethod = message.level || 'log';
          console[logMethod](`${message.message}`);
          response = { success: true };
          // Skip logging the response to keep the console clean
          sendResponse(response);
          return; // Выходим сразу

        default:
          response = { success: false, error: 'Unknown action' };
      }

      console.log('[MyRecV SW] Sending response:', response);
      sendResponse(response);
    } catch (error) {
      console.error('[MyRecV SW] Error handling message:', error);
      sendResponse({ success: false, error: error.message });
    }
  })();

  // Return true to indicate an asynchronous response
  return true;
}

/**
 * Начать запись
 */
async function startRecording(data) {
  try {
    if (state.isRecording) {
      throw new Error('Recording is already in progress');
    }

    const { taskNumber, description, audioOnly } = data;

    console.log('[MyRecV SW] Starting recording with data:', data);

    // Получаем email из настроек
    const settings = await getAllSettings();
    const userEmail = settings.userEmail || '';
    console.log('[MyRecV SW] User email from settings:', userEmail);

    // Создаем offscreen document для доступа к DOM APIs
    await createOffscreenDocument();

    console.log('[MyRecV SW] Offscreen document created');

    // Отправляем команду на запись в offscreen document
    const response = await chrome.runtime.sendMessage({
      action: 'startRecording',
      audioOnly: audioOnly,
      target: 'offscreen' // Помечаем что это для offscreen
    });

    console.log('[MyRecV SW] Offscreen response:', response);

    if (!response.success) {
      throw new Error(response.error || 'Failed to start recording');
    }

    // Обновляем состояние
    state.isRecording = true;
    state.recordingData = {
      taskNumber,
      description,
      audioOnly,
      userEmail, // Добавляем email в recordingData
      startTime: Date.now(),
    };

    // ВАЖНО: Сохраняем состояние для переживания перезапусков SW
    await saveRecordingState();

    // Отправляем уведомление
    await showNotification(
      'Recording started',
      `${audioOnly ? 'Audio only' : 'Video + Audio'} | Task: ${taskNumber}`
    );

    // Обновляем иконку расширения
    await updateIcon('recording');

    // Уведомляем popup (ВАЖНО: передаем isRecording!)
    notifyPopup('recordingStateChanged', {
      isRecording: true,
      ...state.recordingData
    });

    console.log('[MyRecV SW] Recording started successfully, state saved');
    return { success: true };
  } catch (error) {
    console.error('[MyRecV SW] Error starting recording:', error);

    // Очистка при ошибке
    state.isRecording = false;
    state.recordingData = null;
    await saveRecordingState();

    return { success: false, error: error.message };
  }
}

/**
 * Остановить запись
 */
async function stopRecording() {
  try {
    if (!state.isRecording) {
      throw new Error('Recording is not active');
    }

    console.log('[MyRecV SW] Stopping recording...');

    // Проверяем существует ли offscreen document
    const existingContexts = await chrome.runtime.getContexts({
      contextTypes: ['OFFSCREEN_DOCUMENT'],
    });
    console.log('[MyRecV SW] Offscreen contexts found:', existingContexts.length);

    if (existingContexts.length === 0) {
      console.error('[MyRecV SW] ❌ OFFSCREEN DOCUMENT DOES NOT EXIST!');
      throw new Error('The offscreen document was closed by Chrome. Please try again.');
    }

    // Отправляем команду на остановку записи в offscreen document
    const response = await chrome.runtime.sendMessage({
      action: 'stopRecording',
      target: 'offscreen' // Помечаем что это для offscreen
    });

    console.log('[MyRecV SW] Stop recording response:', response);

    if (!response.success) {
      throw new Error(response.error || 'Failed to stop the recording');
    }

    // Получаем metadata из ответа
    // Сам Blob хранится в offscreen (window.recordedBlob)
    console.log('[MyRecV SW] Received recording metadata from offscreen');
    console.log('[MyRecV SW] Response type:', response.type);
    console.log('[MyRecV SW] Response size field:', response.size);

    // Получаем настройки для формата аудио
    const settings = await getAllSettings();

    // Определяем расширение на основе режима записи
    // state.recorder не существует в service worker, recorder живет в offscreen
    let extension = 'webm'; // По умолчанию webm

    // Если нужен WAV формат для audio-only, конвертируем
    if (state.recordingData.audioOnly && settings.audioFormat === 'wav') {
      // TODO: Добавить конвертацию в WAV через Web Audio API
      // Пока оставляем webm
      extension = 'webm';
    }

    // Подготавливаем метаданные для DualSaver
    const metadata = {
      taskNumber: state.recordingData.taskNumber,
      description: state.recordingData.description,
      audioOnly: state.recordingData.audioOnly,
      userEmail: state.recordingData.userEmail || '', // Добавляем email
    };

    // Сохраняем файл (локально + NextCloud)
    // Передаем metadata, сам blob хранится в offscreen
    const blobMetadata = { size: response.size, type: response.type };
    const saveResults = await saveRecordingFile(blobMetadata, metadata);

    // Вычисляем длительность записи
    const duration = Math.floor((Date.now() - state.recordingData.startTime) / 1000);

    // Добавляем в историю
    await addToHistory({
      taskNumber: state.recordingData.taskNumber,
      description: state.recordingData.description,
      fileName: saveResults.fileName,
      duration: duration,
      fileSize: response.size, // Используем size из ответа offscreen
      audioOnly: state.recordingData.audioOnly,
      publicLink: saveResults.publicLink || null, // Сохраняем публичную ссылку
      nextcloudPath: saveResults.nextcloud?.path || null,
    });

    // Отправляем уведомление с результатами
    const notificationMessage = DualSaver.getSummary(saveResults);
    await showNotification('Запись завершена', notificationMessage);

    // Если есть публичная ссылка, копируем в буфер обмена
    if (saveResults.publicLink) {
      try {
        // Используем offscreen document для доступа к clipboard API
        const clipboardResponse = await chrome.runtime.sendMessage({
          action: 'copyToClipboard',
          text: saveResults.publicLink,
          target: 'offscreen' // Помечаем что это для offscreen
        });
        if (clipboardResponse && clipboardResponse.success) {
          console.log('[MyRecV SW] Публичная ссылка скопирована в буфер обмена');
        }
      } catch (error) {
        console.warn('[MyRecV SW] Не удалось скопировать ссылку в буфер обмена:', error);
      }
    }

    // Обновляем иконку
    await updateIcon('idle');

    // Сбрасываем состояние
    state.isRecording = false;
    const recordingData = state.recordingData;
    state.recordingData = null;

    // Сохраняем сброшенное состояние
    await saveRecordingState();

    // Уведомляем popup
    notifyPopup('recordingStateChanged', {
      isRecording: false,
      lastRecording: {
        fileName: saveResults.fileName,
        publicLink: saveResults.publicLink,
        localSaved: saveResults.local?.success,
        nextcloudSaved: saveResults.nextcloud?.success,
      },
    });

    // Закрываем offscreen document с задержкой
    // Даем время на завершение download через offscreen
    setTimeout(async () => {
      await closeOffscreenDocument();
    }, 5000); // 5 секунд задержка (чтобы download точно завершился)

    console.log('[MyRecV SW] Recording stopped successfully');
    return {
      success: true,
      fileName: saveResults.fileName,
      saveResults: saveResults,
    };
  } catch (error) {
    console.error('[MyRecV SW] Error stopping recording:', error);

    // Сбрасываем состояние
    state.isRecording = false;
    state.recordingData = null;

    // Сохраняем сброшенное состояние
    await saveRecordingState();

    // Уведомляем popup об ошибке
    notifyPopup('recordingError', { error: error.message });

    await updateIcon('idle');

    return { success: false, error: error.message };
  }
}

/**
 * Сохранить файл записи (локально + NextCloud)
 */
async function saveRecordingFile(blobMetadata, metadata) {
  try {
    console.log('[MyRecV SW] Сохранение файла с метаданными:', metadata);
    console.log('[MyRecV SW] Blob metadata - size:', blobMetadata.size, 'type:', blobMetadata.type);

    // Use DualSaver to handle persistence
    // Pass blobMetadata (size, type); the blob itself lives in offscreen
    const results = await DualSaver.save(blobMetadata, metadata, state.directoryHandle);

    console.log('[MyRecV SW] Результаты сохранения:', results);

    return results;
  } catch (error) {
    console.error('[MyRecV SW] Error saving file:', error);
    throw error;
  }
}

/**
 * Выбрать директорию для сохранения
 */
async function selectSaveDirectory() {
  try {
    // Создаем offscreen document для доступа к window.showDirectoryPicker
    await createOffscreenDocument();

    const directoryHandle = await requestDirectoryAccess();

    if (directoryHandle) {
      state.directoryHandle = directoryHandle;

      // Persist the handle (needs dedicated IndexedDB storage)
      // For now we keep it in memory
      // TODO: Implement IndexedDB persistence

      console.log('Directory selected');
      return { success: true };
    } else {
      return { success: false, error: 'Directory not selected' };
    }
  } catch (error) {
    console.error('Error selecting directory:', error);
    return { success: false, error: error.message };
  }
}

/**
 * Загрузить сохраненную директорию
 */
async function loadDirectoryHandle() {
  // TODO: Restore handle from IndexedDB
  // File System Access API handles cannot be serialized into chrome.storage
  // Need to rely on IndexedDB for handle storage
}

/**
 * Восстановить состояние записи после перезапуска Service Worker
 */
async function restoreRecordingState() {
  try {
    const savedState = await chrome.storage.session.get(['isRecording', 'recordingData']);

    if (savedState.isRecording) {
      console.log('[MyRecV SW] Restoring recording state:', savedState.recordingData);
      state.isRecording = true;
      state.recordingData = savedState.recordingData;

      // Пересоздаем offscreen document
      await createOffscreenDocument();
    } else {
      console.log('[MyRecV SW] No active recording to restore');
    }
  } catch (error) {
    console.error('[MyRecV SW] Error restoring state:', error);
  }
}

/**
 * Сохранить состояние записи (для переживания перезапусков SW)
 */
async function saveRecordingState() {
  try {
    await chrome.storage.session.set({
      isRecording: state.isRecording,
      recordingData: state.recordingData,
    });
    console.log('[MyRecV SW] Recording state saved to session storage');
  } catch (error) {
    console.error('[MyRecV SW] Error saving recording state:', error);
  }
}

/**
 * Получить текущее состояние записи
 */
function getRecordingState() {
  return {
    isRecording: state.isRecording,
    ...state.recordingData,
  };
}

/**
 * Создать offscreen document для DOM APIs
 */
async function createOffscreenDocument() {
  // Проверяем, существует ли уже offscreen document
  const existingContexts = await chrome.runtime.getContexts({
    contextTypes: ['OFFSCREEN_DOCUMENT'],
  });

  console.log('[MyRecV SW] Checking existing offscreen contexts:', existingContexts.length);

  if (existingContexts.length > 0) {
    console.log('[MyRecV SW] Offscreen document already exists, reusing');
    return;
  }

  // Создаем offscreen document
  console.log('[MyRecV SW] Creating NEW offscreen document...');
  try {
    await chrome.offscreen.createDocument({
      url: 'offscreen.html',
      reasons: ['USER_MEDIA', 'DISPLAY_MEDIA'],
      justification: 'Recording screen and audio',
    });
    console.log('[MyRecV SW] ✅ Offscreen document created successfully');
  } catch (error) {
    console.error('[MyRecV SW] ❌ Error creating offscreen document:', error);
    throw error;
  }
}

/**
 * Закрыть offscreen document
 */
async function closeOffscreenDocument() {
  try {
    await chrome.offscreen.closeDocument();
    console.log('[MyRecV SW] Offscreen document closed');
  } catch (error) {
    console.warn('[MyRecV SW] Error closing offscreen document:', error);
  }
}

/**
 * Уведомить popup об изменениях
 */
function notifyPopup(action, data) {
  chrome.runtime.sendMessage({ action, ...data }).catch(() => {
    // Popup может быть закрыт
  });
}

/**
 * Показать нотификацию
 */
async function showNotification(title, message) {
  // Временно отключено - уведомления требуют валидную иконку
  console.log('[MyRecV SW] Notification:', title, '-', message);

  /* try {
    await chrome.notifications.create({
      type: 'basic',
      iconUrl: 'assets/icons/icon128.png',
      title: title,
      message: message,
      priority: 2,
    });
  } catch (error) {
    console.error('Error showing notification:', error);
  } */
}

/**
 * Обновить иконку расширения
 */
async function updateIcon(status) {
  // TODO: Создать иконки для разных состояний
  // idle: обычная иконка
  // recording: иконка с красной точкой

  // Временно отключено из-за проблем с иконками
  console.log('[MyRecV SW] Icon update skipped (status:', status, ')');

  /* const iconPath = status === 'recording'
    ? 'assets/icons/icon128.png' // TODO: icon-recording.png
    : 'assets/icons/icon128.png';

  try {
    await chrome.action.setIcon({
      path: {
        '16': iconPath,
        '48': iconPath,
        '128': iconPath,
      },
    });
  } catch (error) {
    console.error('Error updating icon:', error);
  } */
}

/**
 * Обработка установки расширения
 */
function handleInstall(details) {
  if (details.reason === 'install') {
    console.log('MyRecV installed');
    // Открываем страницу настроек при первой установке
    chrome.runtime.openOptionsPage();
  } else if (details.reason === 'update') {
    console.log('MyRecV updated');
  }
}

// Инициализация при загрузке service worker
console.log('[MyRecV SW] service-worker.js loaded');
init().catch(error => {
  console.error('[MyRecV SW] Init error:', error);
});
