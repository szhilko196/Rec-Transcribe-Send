/**
 * Audio Utilities - WAV encoding and audio processing
 */

/**
 * Convert AudioBuffer to WAV Blob
 * @param {AudioBuffer} audioBuffer - The audio buffer to convert
 * @param {number} targetSampleRate - Target sample rate (default: 16000 for speech recognition)
 * @returns {Promise<Blob>} WAV file as Blob
 */
export async function audioBufferToWav(audioBuffer, targetSampleRate = 16000) {
  // Resample if needed
  let processedBuffer = audioBuffer;
  if (audioBuffer.sampleRate !== targetSampleRate) {
    processedBuffer = await resampleAudioBuffer(audioBuffer, targetSampleRate);
  }

  // Convert to mono if stereo
  const numChannels = 1; // Always mono for speech recognition
  const length = processedBuffer.length;
  const sampleRate = processedBuffer.sampleRate;

  // Get audio data (convert to mono if needed)
  const samples = new Float32Array(length);

  if (processedBuffer.numberOfChannels === 1) {
    processedBuffer.copyFromChannel(samples, 0);
  } else {
    // Mix down to mono by averaging channels
    const tempSamples = [];
    for (let i = 0; i < processedBuffer.numberOfChannels; i++) {
      const channelData = new Float32Array(length);
      processedBuffer.copyFromChannel(channelData, i);
      tempSamples.push(channelData);
    }

    for (let i = 0; i < length; i++) {
      let sum = 0;
      for (let ch = 0; ch < tempSamples.length; ch++) {
        sum += tempSamples[ch][i];
      }
      samples[i] = sum / tempSamples.length;
    }
  }

  // Convert float samples to 16-bit PCM
  const pcmSamples = new Int16Array(length);
  for (let i = 0; i < length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    pcmSamples[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
  }

  // Create WAV file
  const wavBuffer = createWavFile(pcmSamples, sampleRate, numChannels);
  return new Blob([wavBuffer], { type: 'audio/wav' });
}

/**
 * Create WAV file buffer from PCM data
 * @param {Int16Array} samples - PCM samples
 * @param {number} sampleRate - Sample rate
 * @param {number} numChannels - Number of channels
 * @returns {ArrayBuffer} WAV file buffer
 */
function createWavFile(samples, sampleRate, numChannels) {
  const bytesPerSample = 2; // 16-bit
  const blockAlign = numChannels * bytesPerSample;
  const dataSize = samples.length * bytesPerSample;
  const fileSize = 44 + dataSize;

  const buffer = new ArrayBuffer(fileSize);
  const view = new DataView(buffer);

  let offset = 0;

  // RIFF chunk descriptor
  writeString(view, offset, 'RIFF'); offset += 4;
  view.setUint32(offset, fileSize - 8, true); offset += 4;
  writeString(view, offset, 'WAVE'); offset += 4;

  // fmt sub-chunk
  writeString(view, offset, 'fmt '); offset += 4;
  view.setUint32(offset, 16, true); offset += 4; // Subchunk size
  view.setUint16(offset, 1, true); offset += 2; // Audio format (1 = PCM)
  view.setUint16(offset, numChannels, true); offset += 2;
  view.setUint32(offset, sampleRate, true); offset += 4;
  view.setUint32(offset, sampleRate * blockAlign, true); offset += 4; // Byte rate
  view.setUint16(offset, blockAlign, true); offset += 2;
  view.setUint16(offset, 16, true); offset += 2; // Bits per sample

  // data sub-chunk
  writeString(view, offset, 'data'); offset += 4;
  view.setUint32(offset, dataSize, true); offset += 4;

  // Write PCM samples
  for (let i = 0; i < samples.length; i++) {
    view.setInt16(offset, samples[i], true);
    offset += 2;
  }

  return buffer;
}

/**
 * Write string to DataView
 * @param {DataView} view - DataView to write to
 * @param {number} offset - Offset position
 * @param {string} string - String to write
 */
function writeString(view, offset, string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}

/**
 * Resample AudioBuffer to target sample rate
 * @param {AudioBuffer} audioBuffer - Source audio buffer
 * @param {number} targetSampleRate - Target sample rate
 * @returns {Promise<AudioBuffer>} Resampled audio buffer
 */
async function resampleAudioBuffer(audioBuffer, targetSampleRate) {
  const offlineContext = new OfflineAudioContext(
    audioBuffer.numberOfChannels,
    Math.ceil(audioBuffer.duration * targetSampleRate),
    targetSampleRate
  );

  const source = offlineContext.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(offlineContext.destination);
  source.start(0);

  // startRendering() returns a Promise in modern browsers
  return await offlineContext.startRendering();
}

/**
 * Extract segment from AudioBuffer
 * @param {AudioBuffer} audioBuffer - Source audio buffer
 * @param {number} startTime - Start time in seconds
 * @param {number} endTime - End time in seconds
 * @param {number} maxDuration - Maximum duration in seconds (default: 300 = 5 minutes)
 * @returns {AudioBuffer} Extracted segment
 */
export function extractSegment(audioBuffer, startTime, endTime, maxDuration = 300) {
  const sampleRate = audioBuffer.sampleRate;
  const numberOfChannels = audioBuffer.numberOfChannels;

  // Calculate duration and apply max limit
  let duration = endTime - startTime;
  if (duration > maxDuration) {
    duration = maxDuration;
    endTime = startTime + maxDuration;
  }

  const startSample = Math.floor(startTime * sampleRate);
  const endSample = Math.floor(endTime * sampleRate);
  const segmentLength = endSample - startSample;

  // Create new buffer for segment
  const audioContext = new AudioContext();
  const segmentBuffer = audioContext.createBuffer(
    numberOfChannels,
    segmentLength,
    sampleRate
  );

  // Copy audio data
  for (let channel = 0; channel < numberOfChannels; channel++) {
    const sourceData = audioBuffer.getChannelData(channel);
    const targetData = segmentBuffer.getChannelData(channel);

    for (let i = 0; i < segmentLength; i++) {
      const sourceIndex = startSample + i;
      if (sourceIndex < sourceData.length) {
        targetData[i] = sourceData[sourceIndex];
      } else {
        targetData[i] = 0;
      }
    }
  }

  return segmentBuffer;
}

/**
 * Format duration in seconds to MM:SS format
 * @param {number} seconds - Duration in seconds
 * @returns {string} Formatted duration
 */
export function formatDuration(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Validate audio buffer
 * @param {AudioBuffer} audioBuffer - Audio buffer to validate
 * @returns {boolean} True if valid
 */
export function validateAudioBuffer(audioBuffer) {
  if (!audioBuffer) return false;
  if (audioBuffer.length === 0) return false;
  if (audioBuffer.sampleRate === 0) return false;
  return true;
}

/**
 * Transliterate Cyrillic to Latin
 * @param {string} text - Text with Cyrillic characters
 * @returns {string} Transliterated text
 */
function transliterateCyrillic(text) {
  const cyrillicMap = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    'А': 'a', 'Б': 'b', 'В': 'v', 'Г': 'g', 'Д': 'd', 'Е': 'e', 'Ё': 'yo',
    'Ж': 'zh', 'З': 'z', 'И': 'i', 'Й': 'y', 'К': 'k', 'Л': 'l', 'М': 'm',
    'Н': 'n', 'О': 'o', 'П': 'p', 'Р': 'r', 'С': 's', 'Т': 't', 'У': 'u',
    'Ф': 'f', 'Х': 'h', 'Ц': 'ts', 'Ч': 'ch', 'Ш': 'sh', 'Щ': 'sch',
    'Ъ': '', 'Ы': 'y', 'Ь': '', 'Э': 'e', 'Ю': 'yu', 'Я': 'ya'
  };

  return text.split('').map(char => cyrillicMap[char] || char).join('');
}

/**
 * Convert speaker name to valid filename format
 * @param {string} speakerName - Speaker name (e.g., "Иван Петров" or "John Doe")
 * @returns {string} Valid speaker ID (e.g., "ivan_petrov" or "john_doe")
 */
export function speakerNameToId(speakerName) {
  return speakerName
    .trim()
    .replace(/\s+/g, '_')                 // Replace spaces with underscores
    .toLowerCase()                         // Convert to lowercase
    .normalize('NFD')                      // Decompose unicode (for Latin diacritics)
    .replace(/[\u0300-\u036f]/g, '')      // Remove diacritics from Latin chars
    .split('').map(char => {              // Transliterate Cyrillic
      return transliterateCyrillic(char);
    }).join('')
    .replace(/[^a-z0-9_]/g, '')           // Remove non-alphanumeric except underscore
    .replace(/_{2,}/g, '_')               // Replace multiple underscores with single
    .replace(/^_+|_+$/g, '');             // Trim underscores from start/end
}

/**
 * Validate speaker ID format
 * @param {string} speakerId - Speaker ID to validate
 * @returns {boolean} True if valid
 */
export function validateSpeakerId(speakerId) {
  if (!speakerId || speakerId.length === 0) return false;
  if (/^[a-z0-9_]+$/.test(speakerId) === false) return false;
  if (speakerId.startsWith('_') || speakerId.endsWith('_')) return false;
  return true;
}

console.log('Audio utilities loaded');
