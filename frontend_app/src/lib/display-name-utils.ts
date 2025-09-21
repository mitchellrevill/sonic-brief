/**
 * Get the display name for a job/recording with fallback logic
 */
export function getDisplayName(job: {
  displayname?: string;
  display_name?: string; // legacy
  file_name?: string;
  filename?: string;
  file_path?: string;
}): string {
  // Priority: displayname > display_name (legacy) > file_name > filename > derived from path > fallback
  return (
    job.displayname ||
    job.display_name ||
    job.file_name ||
    job.filename ||
    (job.file_path ? getFileNameFromPath(job.file_path) : null) ||
    "Untitled Recording"
  );
}

/**
 * Extract filename from file path URL
 */
export function getFileNameFromPath(filePath: string): string | null {
  if (!filePath) return null;
  try {
    const url = new URL(filePath);
    const pathname = url.pathname;
    const segments = pathname.split('/');
    return segments[segments.length - 1] || null;
  } catch {
    // Fallback for non-URL paths
    const segments = filePath.split('/');
    return segments[segments.length - 1] || null;
  }
}