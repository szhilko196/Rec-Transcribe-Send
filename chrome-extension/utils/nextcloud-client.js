/**
 * NextCloud WebDAV Client
 * Handles NextCloud interactions via WebDAV for uploads and folder management
 */

export class NextCloudClient {
  /**
   * @param {string} serverUrl - NextCloud server URL (https://nextcloud.example.com)
   * @param {string} username - Username
   * @param {string} password - Password or App Password
   * @param {string} basePath - Base directory for recordings (e.g. '/Recordings/')
   */
  constructor(serverUrl, username, password, basePath = '/Recordings/') {
    this.serverUrl = serverUrl.replace(/\/$/, ''); // Remove trailing slash
    this.username = username;
    this.password = password;
    this.basePath = basePath;

    // WebDAV endpoint
    this.webdavUrl = `${this.serverUrl}/remote.php/dav/files/${encodeURIComponent(username)}`;

    // OCS API endpoint (for public links)
    this.ocsUrl = `${this.serverUrl}/ocs/v2.php/apps/files_sharing/api/v1/shares`;

    // Basic Auth header
    this.authHeader = 'Basic ' + btoa(`${username}:${password}`);
  }

  /**
   * Test the connection to NextCloud
   * @returns {Promise<{success: boolean, message: string, serverInfo?: Object}>}
   */
  async testConnection() {
    try {
      // Check server availability via PROPFIND on the root folder
      const response = await fetch(this.webdavUrl, {
        method: 'PROPFIND',
        headers: {
          'Authorization': this.authHeader,
          'Depth': '0',
        },
      });

      if (response.status === 207) {
        // 207 Multi-Status = success
        return {
          success: true,
          message: 'Connection succeeded',
          serverInfo: {
            url: this.serverUrl,
            username: this.username,
          },
        };
      } else if (response.status === 401) {
        return {
          success: false,
          message: 'Invalid username or password',
        };
      } else if (response.status === 404) {
        return {
          success: false,
          message: 'Server not found or WebDAV unavailable',
        };
      } else {
        return {
          success: false,
          message: `Connection error: ${response.status} ${response.statusText}`,
        };
      }
    } catch (error) {
      console.error('Connection test error:', error);
      return {
        success: false,
        message: `Network error: ${error.message}`,
      };
    }
  }

  /**
   * Create a directory (if missing)
   * @param {string} path - Directory path
   * @returns {Promise<boolean>}
   */
  async createDirectory(path) {
    try {
      const fullPath = `${this.webdavUrl}${path}`;

      const response = await fetch(fullPath, {
        method: 'MKCOL',
        headers: {
          'Authorization': this.authHeader,
        },
      });

      // 201 = created, 405 = already exists
      return response.status === 201 || response.status === 405;
    } catch (error) {
      console.error('Create directory error:', error);
      // Not critical if the folder already exists
      return false;
    }
  }

  /**
   * Upload a file to NextCloud
   * @param {Blob} blob - File contents
   * @param {string} fileName - File name
   * @param {Function} onProgress - Optional progress callback
   * @returns {Promise<{success: boolean, path: string, url: string, error?: string}>}
   */
  async uploadFile(blob, fileName, onProgress = null) {
    try {
      // Ensure base directory exists
      await this.createDirectory(this.basePath);

      // Build full file path
      const filePath = `${this.basePath}${fileName}`;
      const fullUrl = `${this.webdavUrl}${filePath}`;

      // Detect content type
      const contentType = blob.type || 'application/octet-stream';

      // Upload via XMLHttpRequest to support progress events
      return await new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();

        xhr.upload.addEventListener('progress', (event) => {
          if (event.lengthComputable && onProgress) {
            const percentComplete = (event.loaded / event.total) * 100;
            onProgress(percentComplete);
          }
        });

        xhr.addEventListener('load', () => {
          if (xhr.status === 201 || xhr.status === 204) {
            // 201 = created, 204 = updated
            resolve({
              success: true,
              path: filePath,
              url: `${this.serverUrl}/f/${filePath.split('/').pop()}`,
            });
          } else if (xhr.status === 401) {
            resolve({
              success: false,
              error: 'Invalid credentials',
            });
          } else if (xhr.status === 507) {
            resolve({
              success: false,
              error: 'Insufficient storage on server',
            });
          } else {
            resolve({
              success: false,
              error: `Upload error: ${xhr.status} ${xhr.statusText}`,
            });
          }
        });

        xhr.addEventListener('error', () => {
          reject(new Error('Network error during upload'));
        });

        xhr.addEventListener('abort', () => {
          reject(new Error('Upload cancelled'));
        });

        xhr.open('PUT', fullUrl);
        xhr.setRequestHeader('Authorization', this.authHeader);
        xhr.setRequestHeader('Content-Type', contentType);
        xhr.send(blob);
      });
    } catch (error) {
      console.error('Upload file error:', error);
      return {
        success: false,
        error: error.message,
      };
    }
  }

  /**
   * Create a public link for a file
   * @param {string} filePath - File path (starting with /)
   * @returns {Promise<string|null>} - Public link URL or null
   */
  async createPublicShare(filePath) {
    try {
      // OCS API for creating a public link
      const formData = new FormData();
      formData.append('path', filePath);
      formData.append('shareType', '3'); // 3 = public link
      formData.append('permissions', '1'); // 1 = read only

      const response = await fetch(this.ocsUrl, {
        method: 'POST',
        headers: {
          'Authorization': this.authHeader,
          'OCS-APIRequest': 'true',
        },
        body: formData,
      });

      if (response.ok) {
        const text = await response.text();

        // Parse XML response
        const parser = new DOMParser();
        const xmlDoc = parser.parseFromString(text, 'text/xml');

        // Extract URL from XML
        const urlElement = xmlDoc.querySelector('url');
        if (urlElement) {
          return urlElement.textContent;
        }
      }

      console.warn('Failed to create public share:', response.status);
      return null;
    } catch (error) {
      console.error('Create public share error:', error);
      return null;
    }
  }

  /**
   * List files in a directory
   * @param {string} path - Directory path
   * @returns {Promise<Array<{name: string, size: number, modified: Date}>>}
   */
  async listFiles(path = '/') {
    try {
      const fullPath = `${this.webdavUrl}${path}`;

      const response = await fetch(fullPath, {
        method: 'PROPFIND',
        headers: {
          'Authorization': this.authHeader,
          'Depth': '1',
          'Content-Type': 'application/xml',
        },
        body: `<?xml version="1.0"?>
          <d:propfind xmlns:d="DAV:">
            <d:prop>
              <d:displayname/>
              <d:getcontentlength/>
              <d:getlastmodified/>
              <d:resourcetype/>
            </d:prop>
          </d:propfind>`,
      });

      if (!response.ok) {
        throw new Error(`Failed to list files: ${response.status}`);
      }

      const text = await response.text();
      const parser = new DOMParser();
      const xmlDoc = parser.parseFromString(text, 'text/xml');

      const files = [];
      const responses = xmlDoc.querySelectorAll('response');

      responses.forEach((resp, index) => {
        // Skip the first entry (the folder itself)
        if (index === 0) return;

        const name = resp.querySelector('displayname')?.textContent;
        const size = parseInt(resp.querySelector('getcontentlength')?.textContent || '0');
        const modified = resp.querySelector('getlastmodified')?.textContent;
        const isDir = resp.querySelector('resourcetype collection') !== null;

        if (name && !isDir) {
          files.push({
            name,
            size,
            modified: modified ? new Date(modified) : null,
          });
        }
      });

      return files;
    } catch (error) {
      console.error('List files error:', error);
      return [];
    }
  }

  /**
   * Download a file from NextCloud
   * @param {string} filePath - File path
   * @returns {Promise<Blob|null>}
   */
  async downloadFile(filePath) {
    try {
      const fullUrl = `${this.webdavUrl}${filePath}`;

      const response = await fetch(fullUrl, {
        method: 'GET',
        headers: {
          'Authorization': this.authHeader,
        },
      });

      if (response.ok) {
        return await response.blob();
      }

      console.warn('Failed to download file:', response.status);
      return null;
    } catch (error) {
      console.error('Download file error:', error);
      return null;
    }
  }

  /**
   * Delete a file
   * @param {string} filePath - File path
   * @returns {Promise<boolean>}
   */
  async deleteFile(filePath) {
    try {
      const fullUrl = `${this.webdavUrl}${filePath}`;

      const response = await fetch(fullUrl, {
        method: 'DELETE',
        headers: {
          'Authorization': this.authHeader,
        },
      });

      return response.status === 204;
    } catch (error) {
      console.error('Delete file error:', error);
      return false;
    }
  }
}

/**
 * Retry helper with exponential backoff for upload operations
 * @param {Function} uploadFn - Upload function
 * @param {number} maxRetries - Max retry attempts
 * @returns {Promise}
 */
export async function uploadWithRetry(uploadFn, maxRetries = 3) {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      const result = await uploadFn();

      if (result.success) {
        return result;
      }

      // Do not retry 401 or 507 responses
      if (result.error && (result.error.includes('401') || result.error.includes('507'))) {
        return result;
      }

      // Last attempt
      if (attempt === maxRetries - 1) {
        return result;
      }

      // Exponential backoff: 1s, 2s, 4s
      const delay = 1000 * Math.pow(2, attempt);
      await new Promise(resolve => setTimeout(resolve, delay));

    } catch (error) {
      // Last attempt
      if (attempt === maxRetries - 1) {
        throw error;
      }

      // Exponential backoff
      const delay = 1000 * Math.pow(2, attempt);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
}
