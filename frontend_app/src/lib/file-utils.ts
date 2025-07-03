/**
 * Utility functions for file operations and metadata extraction
 */

// Comprehensive list of supported audio file extensions
const AUDIO_EXTENSIONS = [
  'mp3', 'wav', 'ogg', 'oga', 'flac', 'aac', 'm4a', 'wma', 'webm', 'opus'
] as const;

// MIME types for audio files
const AUDIO_MIME_TYPES = [
  'audio/mpeg',
  'audio/wav', 
  'audio/wave',
  'audio/x-wav',
  'audio/ogg',
  'audio/flac',
  'audio/aac',
  'audio/mp4',
  'audio/x-m4a',
  'audio/webm',
  'audio/opus'
] as const;

/**
 * Check if a file path or URL represents an audio file
 */
export function isAudioFile(filePath: string | undefined): boolean {
  if (!filePath || typeof filePath !== 'string') {
    return false;
  }

  try {
    // Remove query parameters and fragments
    const cleanPath = filePath.split('?')[0].split('#')[0];
    
    // Extract file extension
    const extension = cleanPath.split('.').pop()?.toLowerCase() || '';
    
    // Check against known audio extensions
    return AUDIO_EXTENSIONS.includes(extension as any);
  } catch (error) {
    console.warn('Error checking if file is audio:', error);
    return false;
  }
}

/**
 * Check if a MIME type represents an audio file
 */
export function isAudioMimeType(mimeType: string): boolean {
  if (!mimeType || typeof mimeType !== 'string') {
    return false;
  }
  
  return AUDIO_MIME_TYPES.includes(mimeType.toLowerCase() as any) || 
         mimeType.toLowerCase().startsWith('audio/');
}

/**
 * Checks if a file path is a well-supported audio format in browsers
 */
export function isWellSupportedAudioFormat(path: string | undefined): boolean {
  if (!path) return false;
  
  // Handle URLs with query parameters
  const urlPath = path.split('?')[0];
  
  // Get the file name from the path (handle both forward and backslashes)
  const fileName = urlPath.split('/').pop() || urlPath.split('\\').pop() || '';
  
  // Get the extension from the file name
  const fileNameParts = fileName.split('.');
  const ext = fileNameParts.length > 1 ? fileNameParts.pop()?.toLowerCase() || '' : '';
  
  // Well-supported audio formats across browsers
  const wellSupportedFormats = ['mp3', 'wav', 'ogg'];
  
  return wellSupportedFormats.includes(ext);
}

/**
 * Extract filename from a file path or URL
 */
export function getFileNameFromPath(filePath: string | undefined): string {
  if (!filePath || typeof filePath !== 'string') {
    return 'Unknown File';
  }

  try {
    // Remove query parameters and fragments
    const cleanPath = filePath.split('?')[0].split('#')[0];
    
    // Extract filename from path
    const fileName = cleanPath.split('/').pop() || cleanPath.split('\\').pop() || '';
    
    return fileName || 'Unknown File';
  } catch (error) {
    console.warn('Error extracting filename:', error);
    return 'Unknown File';
  }
}

/**
 * Get file extension from path
 */
export function getFileExtension(filePath: string): string {
  if (!filePath || typeof filePath !== 'string') {
    return '';
  }

  try {
    const cleanPath = filePath.split('?')[0].split('#')[0];
    const extension = cleanPath.split('.').pop()?.toLowerCase() || '';
    return extension;
  } catch (error) {
    console.warn('Error extracting file extension:', error);
    return '';
  }
}

/**
 * Format file size in human readable format
 */
export function formatFileSize(bytes: number): string {
  if (!bytes || bytes === 0) return '0 B';
  
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

/**
 * Validate audio file and extract metadata
 */
export async function validateAndGetAudioMetadata(file: File): Promise<{
  isValid: boolean;
  duration?: number;
  error?: string;
}> {
  return new Promise((resolve) => {
    // Check file type first
    if (!isAudioFile(file.name) && !isAudioMimeType(file.type)) {
      resolve({
        isValid: false,
        error: 'File is not a supported audio format'
      });
      return;
    }

    // Create audio element to get metadata
    const audio = new Audio();
    const url = URL.createObjectURL(file);
    
    const cleanup = () => {
      URL.revokeObjectURL(url);
      audio.remove();
    };

    const handleSuccess = () => {
      cleanup();
      resolve({
        isValid: true,
        duration: isFinite(audio.duration) ? audio.duration : undefined
      });
    };

    const handleError = (error: string) => {
      cleanup();
      resolve({
        isValid: false,
        error
      });
    };

    // Set up event listeners
    audio.addEventListener('loadedmetadata', () => {
      // Check if we got valid duration
      if (audio.duration && isFinite(audio.duration)) {
        handleSuccess();
      } else {
        // Try to get duration after a short delay
        setTimeout(() => {
          if (audio.duration && isFinite(audio.duration)) {
            handleSuccess();
          } else {
            // File is valid but duration unknown
            resolve({
              isValid: true,
              duration: undefined
            });
            cleanup();
          }
        }, 100);
      }
    });

    audio.addEventListener('error', () => {
      handleError('Failed to load audio file - file may be corrupted');
    });

    // Set timeout to avoid hanging
    setTimeout(() => {
      handleError('Timeout while loading audio metadata');
    }, 10000);

    // Load the audio
    audio.src = url;
    audio.load();
  });
}

/**
 * Get audio duration from URL (for already uploaded files)
 */
export async function getAudioDurationFromUrl(audioUrl: string): Promise<number | null> {
  return new Promise((resolve) => {
    if (!audioUrl || !isAudioFile(audioUrl)) {
      resolve(null);
      return;
    }

    const audio = new Audio();
    
    const cleanup = () => {
      audio.remove();
    };

    audio.addEventListener('loadedmetadata', () => {
      cleanup();
      if (audio.duration && isFinite(audio.duration)) {
        resolve(audio.duration);
      } else {
        // Try again after a short delay
        setTimeout(() => {
          if (audio.duration && isFinite(audio.duration)) {
            resolve(audio.duration);
          } else {
            resolve(null);
          }
        }, 100);
      }
    });

    audio.addEventListener('error', () => {
      cleanup();
      resolve(null);
    });

    audio.addEventListener('canplay', () => {
      // Sometimes duration becomes available at canplay
      if (audio.duration && isFinite(audio.duration)) {
        cleanup();
        resolve(audio.duration);
      }
    });

    // Set timeout
    setTimeout(() => {
      cleanup();
      resolve(null);
    }, 5000);

    // Add CORS headers if needed
    audio.crossOrigin = 'anonymous';
    audio.preload = 'metadata';
    audio.src = audioUrl;
    audio.load();
  });
}
