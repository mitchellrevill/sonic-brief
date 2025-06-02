/**
 * Utility functions for audio file handling
 */

/**
 * Checks if a file path is an audio file based on its extension
 * @param path The file path to check
 * @returns Boolean indicating if the file is a valid audio format
 */
export const isAudioFile = (path: string | undefined): boolean => {
  if (!path) return false;
  
  // Handle URLs with query parameters
  const urlPath = path.split('?')[0];
  
  // Get the file name from the path (handle both forward and backslashes)
  const fileName = urlPath.split('/').pop() || urlPath.split('\\').pop() || '';
  
  // Get the extension from the file name
  const fileNameParts = fileName.split('.');
  const ext = fileNameParts.length > 1 ? fileNameParts.pop()?.toLowerCase() || '' : '';
  
  // Common audio file extensions
  const audioExtensions = ['mp3', 'mp4', 'wav', 'ogg', 'aac', 'm4a', 'flac', 'webm'];
  
  return audioExtensions.includes(ext);
};

/**
 * Checks if a file path is a well-supported audio format in browsers
 * @param path The file path to check
 * @returns Boolean indicating if the file format is well-supported
 */
export const isWellSupportedAudioFormat = (path: string | undefined): boolean => {
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
};

/**
 * Extracts a filename from a file path
 * @param path The file path
 * @returns The extracted file name or a fallback string
 */
export const getFileNameFromPath = (path: string | undefined): string => {
  if (!path) return 'Unnamed File';
  
  // Handle URLs with query parameters
  const urlPath = path.split('?')[0];
  
  // Get the file name
  const fileName = urlPath.split('/').pop() || urlPath.split('\\').pop() || 'Unnamed File';
  
  return fileName;
};
