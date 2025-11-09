/**
 * DualSaver - dual-save module
 * Coordinates saving recordings locally and to NextCloud
 */

import { saveRecording, generateFileName } from './file-handler.js';
import { NextCloudClient, uploadWithRetry } from './nextcloud-client.js';
import { getNextCloudSettings } from './storage.js';

export class DualSaver {
  /**
   * Save a recording to both destinations (local + NextCloud)
   * @param {Blob} blob - Recording file
   * @param {Object} metadata - Metadata: { taskNumber, description, audioOnly }
   * @param {Object} directoryHandle - File System Access API handle (may be null)
   * @returns {Promise<{local: Object, nextcloud: Object|null, publicLink: string|null}>}
   */
  static async save(blob, metadata, directoryHandle = null) {
    console.log('DualSaver: starting save...', metadata);

    // Generate file name once for both storage locations
    const fileName = generateFileName(
      metadata.taskNumber,
      metadata.description,
      metadata.audioOnly,
      metadata.userEmail // Include email in file name if provided
    );

    console.log('DualSaver: file name -', fileName);

    // Results container
    const results = {
      local: null,
      nextcloud: null,
      publicLink: null,
      fileName: fileName,
    };

    // 1. Always perform local save
    try {
      console.log('DualSaver: saving locally...');
      const localResult = await saveRecording(blob, fileName, directoryHandle);
      results.local = {
        success: localResult.success,
        path: localResult.path,
        method: localResult.method,
        error: localResult.error,
      };
      console.log('DualSaver: local save complete', results.local);
    } catch (error) {
      console.error('DualSaver: local save error', error);
      results.local = {
        success: false,
        error: error.message,
      };
    }

    // 2. NextCloud save (if enabled)
    const ncSettings = await getNextCloudSettings();

    if (ncSettings.enabled) {
      console.log('DualSaver: NextCloud enabled, uploading...');

      try {
        // Create NextCloud client
        const credential = ncSettings.authType === 'token'
          ? ncSettings.token
          : ncSettings.password;

        if (!credential) {
          throw new Error('NextCloud credentials not configured');
        }

        const client = new NextCloudClient(
          ncSettings.url,
          ncSettings.username,
          credential,
          ncSettings.basePath
        );

        // Upload file with retry logic
        const uploadResult = await uploadWithRetry(
          () => client.uploadFile(blob, fileName, (progress) => {
            console.log(`DualSaver: NextCloud upload progress: ${progress.toFixed(1)}%`);
          }),
          3 // Three attempts
        );

        results.nextcloud = {
          success: uploadResult.success,
          path: uploadResult.path,
          url: uploadResult.url,
          error: uploadResult.error,
        };

        console.log('DualSaver: NextCloud upload complete', results.nextcloud);

        // 3. Generate public link (if enabled and upload succeeded)
        if (uploadResult.success && ncSettings.generateLink) {
          console.log('DualSaver: generating public link...');
          try {
            const publicLink = await client.createPublicShare(uploadResult.path);
            if (publicLink) {
              results.publicLink = publicLink;
              console.log('DualSaver: public link created:', publicLink);
            } else {
              console.warn('DualSaver: failed to create public link');
            }
          } catch (error) {
            console.error('DualSaver: error creating public link', error);
          }
        }
      } catch (error) {
        console.error('DualSaver: NextCloud upload error', error);
        results.nextcloud = {
          success: false,
          error: error.message,
        };
      }
    } else {
      console.log('DualSaver: NextCloud disabled, skipping');
      results.nextcloud = null;
    }

    console.log('DualSaver: save complete', results);
    return results;
  }

  /**
   * Produce a human-readable summary of the save outcome
   * @param {Object} results - Result from save()
   * @returns {string}
   */
  static getSummary(results) {
    const messages = [];

    // Local save
    if (results.local?.success) {
      messages.push(`✅ Saved locally: ${results.fileName}`);
    } else {
      messages.push(`❌ Local save failed: ${results.local?.error || 'Unknown error'}`);
    }

    // NextCloud save
    if (results.nextcloud !== null) {
      if (results.nextcloud.success) {
        messages.push('☁️ NextCloud: upload succeeded');
        if (results.publicLink) {
          messages.push(`🔗 Public link: ${results.publicLink}`);
        }
      } else {
        messages.push(`⚠️ NextCloud: ${results.nextcloud.error || 'upload failed'}`);
      }
    }

    return messages.join('\n');
  }

  /**
   * Check readiness for saving
   * @returns {Promise<{ready: boolean, message: string}>}
   */
  static async checkReadiness() {
    const ncSettings = await getNextCloudSettings();

    if (!ncSettings.enabled) {
      return {
        ready: true,
        message: 'Local save only (NextCloud disabled)',
      };
    }

    // Ensure required NextCloud settings are provided
    if (!ncSettings.url || !ncSettings.username) {
      return {
        ready: false,
        message: 'NextCloud: URL or username is not configured',
      };
    }

    const credential = ncSettings.authType === 'token'
      ? ncSettings.token
      : ncSettings.password;

    if (!credential) {
      return {
        ready: false,
        message: 'NextCloud: credentials are not configured',
      };
    }

    return {
      ready: true,
      message: 'Ready for dual save (Local + NextCloud)',
    };
  }
}

/**
 * Helper to save without explicitly instantiating the class
 * @param {Blob} blob - Recording file
 * @param {Object} metadata - Metadata
 * @param {Object} directoryHandle - Directory handle (optional)
   * @returns {Promise<Object>}
   */
export async function dualSave(blob, metadata, directoryHandle = null) {
  return await DualSaver.save(blob, metadata, directoryHandle);
}
