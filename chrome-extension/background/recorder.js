/**
 * MediaRecorder wrapper for capturing screen and audio
 * Uses the Screen Capture API and MediaRecorder API
 */

export class ScreenRecorder {
  constructor() {
    this.mediaRecorder = null;
    this.recordedChunks = [];
    this.stream = null;
    this.startTime = null;
    this.audioOnly = false;
    this.audioContext = null;
    this.microphoneStream = null;
  }

  /**
   * Start recording the screen
   * @param {boolean} audioOnly - Record audio only
   * @returns {Promise<void>}
   */
  async startRecording(audioOnly = false) {
    try {
      this.audioOnly = audioOnly;
      this.recordedChunks = [];

      // Obtain stream via the Screen Capture API
      this.stream = await this.getMediaStream(audioOnly);

      // Determine MIME type based on mode
      const mimeType = this.getMimeType(audioOnly);

      // Create MediaRecorder instance
      this.mediaRecorder = new MediaRecorder(this.stream, {
        mimeType: mimeType,
        videoBitsPerSecond: audioOnly ? undefined : 2500000, // 2.5 Mbps for video
        audioBitsPerSecond: 128000, // 128 kbps for audio
      });

      // Event handlers
      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          this.recordedChunks.push(event.data);
        }
      };

      this.mediaRecorder.onerror = (event) => {
        console.error('MediaRecorder error:', event.error);
        throw new Error(`Recording error: ${event.error.name}`);
      };

      // Begin recording
      this.mediaRecorder.start(1000); // Save chunks every second
      this.startTime = Date.now();

      console.log(`Recording started (${audioOnly ? 'audio' : 'video + audio'})`);
    } catch (error) {
      console.error('Error starting recording:', error);
      this.cleanup();
      throw error;
    }
  }

  /**
   * Stop recording
   * @returns {Promise<Blob>}
   */
  async stopRecording() {
    return new Promise((resolve, reject) => {
      if (!this.mediaRecorder || this.mediaRecorder.state === 'inactive') {
        reject(new Error('Recording is not active'));
        return;
      }

      this.mediaRecorder.onstop = () => {
        try {
          // Create a Blob from recorded chunks
          const mimeType = this.getMimeType(this.audioOnly);
          const blob = new Blob(this.recordedChunks, { type: mimeType });

          console.log(`Recording stopped. Size: ${blob.size} bytes`);

          // Cleanup
          this.cleanup();

          resolve(blob);
        } catch (error) {
          console.error('Error creating Blob:', error);
          reject(error);
        }
      };

      // Stop recording
      this.mediaRecorder.stop();
    });
  }

  /**
   * Get media stream
  * @param {boolean} audioOnly - Audio only
   * @returns {Promise<MediaStream>}
   */
  async getMediaStream(audioOnly) {
    try {
      if (audioOnly) {
        // For audio-only mode, request only audio
        return await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            sampleRate: 48000,
          },
          video: false,
        });
      } else {
        // For video mode, use getDisplayMedia
        const displayStream = await navigator.mediaDevices.getDisplayMedia({
          video: {
            cursor: 'always',
            displaySurface: 'monitor', // or 'window', 'browser'
          },
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            sampleRate: 48000,
          },
          preferCurrentTab: false,
        });

        // IMPORTANT: getDisplayMedia captures only system audio (browser/app sounds).
        // To record MICROPHONE input, we must request getUserMedia separately
        let microphoneStream = null;
        try {
          microphoneStream = await navigator.mediaDevices.getUserMedia({
            audio: {
              echoCancellation: true,
              noiseSuppression: true,
              sampleRate: 48000,
            },
            video: false,
          });
          console.log('[ScreenRecorder] Microphone stream obtained');
        } catch (micError) {
          console.warn('[ScreenRecorder] Failed to get microphone, will record without mic audio:', micError);
          // Continue without microphone (system audio + video only)
        }

        // If microphone stream is available, merge tracks
        if (microphoneStream) {
          const audioContext = new AudioContext();
          const mixedDestination = audioContext.createMediaStreamDestination();

          // Add system audio (if present)
          const displayAudioTracks = displayStream.getAudioTracks();
          if (displayAudioTracks.length > 0) {
            const displayAudioSource = audioContext.createMediaStreamSource(
              new MediaStream(displayAudioTracks)
            );
            displayAudioSource.connect(mixedDestination);
            console.log('[ScreenRecorder] System audio added to mix');
          }

          // Add microphone
          const microphoneSource = audioContext.createMediaStreamSource(microphoneStream);
          microphoneSource.connect(mixedDestination);
          console.log('[ScreenRecorder] Microphone audio added to mix');

          // Create new stream with video + mixed audio
          const videoTracks = displayStream.getVideoTracks();
          const mixedAudioTrack = mixedDestination.stream.getAudioTracks()[0];

          const combinedStream = new MediaStream([...videoTracks, mixedAudioTrack]);

          // Store AudioContext for later cleanup
          this.audioContext = audioContext;
          this.microphoneStream = microphoneStream;

          console.log('[ScreenRecorder] Combined stream created with video + system audio + microphone');
          return combinedStream;
        } else {
          // Screen only (with system audio if available)
          console.log('[ScreenRecorder] Using display stream only (no microphone)');
          return displayStream;
        }
      }
    } catch (error) {
      if (error.name === 'NotAllowedError') {
        throw new Error('User cancelled screen selection or denied permission');
      } else if (error.name === 'NotFoundError') {
        throw new Error('No available devices found for recording');
      } else {
        throw new Error(`Media access error: ${error.message}`);
      }
    }
  }

  /**
   * Resolve MIME type for recording
   * @param {boolean} audioOnly
   * @returns {string}
   */
  getMimeType(audioOnly) {
    if (audioOnly) {
      // Try different formats for audio
      if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
        return 'audio/webm;codecs=opus';
      } else if (MediaRecorder.isTypeSupported('audio/webm')) {
        return 'audio/webm';
      } else if (MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')) {
        return 'audio/ogg;codecs=opus';
      }
    } else {
      // Try different formats for video
      if (MediaRecorder.isTypeSupported('video/webm;codecs=vp9,opus')) {
        return 'video/webm;codecs=vp9,opus';
      } else if (MediaRecorder.isTypeSupported('video/webm;codecs=vp8,opus')) {
        return 'video/webm;codecs=vp8,opus';
      } else if (MediaRecorder.isTypeSupported('video/webm')) {
        return 'video/webm';
      }
    }

    // Fallback
    return audioOnly ? 'audio/webm' : 'video/webm';
  }

  /**
   * Get file extension based on MIME type
   * @returns {string}
   */
  getFileExtension() {
    const mimeType = this.getMimeType(this.audioOnly);

    if (mimeType.includes('video/webm')) {
      return 'webm';
    } else if (mimeType.includes('audio/webm')) {
      return 'webm';
    } else if (mimeType.includes('audio/ogg')) {
      return 'ogg';
    } else if (mimeType.includes('audio/wav')) {
      return 'wav';
    }

    return this.audioOnly ? 'webm' : 'webm';
  }

  /**
   * Get recording duration in seconds
   * @returns {number}
   */
  getDuration() {
    if (!this.startTime) return 0;
    return Math.floor((Date.now() - this.startTime) / 1000);
  }

  /**
   * Determine if recording is active
   * @returns {boolean}
   */
  isRecording() {
    return this.mediaRecorder && this.mediaRecorder.state === 'recording';
  }

  /**
   * Clean up resources
   */
  cleanup() {
    // Stop all stream tracks
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }

    // Stop microphone stream if present
    if (this.microphoneStream) {
      this.microphoneStream.getTracks().forEach(track => track.stop());
      this.microphoneStream = null;
    }

    // Close AudioContext if it was created
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }

    this.mediaRecorder = null;
    this.recordedChunks = [];
    this.startTime = null;
  }

  /**
   * Force stop recording
   */
  forceStop() {
    if (this.isRecording()) {
      this.mediaRecorder.stop();
    }
    this.cleanup();
  }
}
