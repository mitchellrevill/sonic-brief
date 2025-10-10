/**
 * Date utility functions for parsing and formatting dates
 * Optimized for performance with consistent parsing logic
 */

/**
 * Parse different date formats (number in ms/s, ISO string) into a Date object
 * Supports timestamps in seconds (< 1e12) and milliseconds
 * @param input - Date input as string, number, or null/undefined
 * @returns Date object or null if parsing fails
 */
export function parseDate(input: string | number | undefined | null): Date | null {
  if (input === undefined || input === null || input === "") return null;

  // If it's already a number
  if (typeof input === "number") {
    // If looks like seconds (10 digits), convert to ms
    if (input < 1e12) return new Date(input * 1000);
    return new Date(input);
  }

  // If it's a numeric string, try to parse as int
  if (/^\d+$/.test(String(input))) {
    const n = parseInt(String(input), 10);
    if (n < 1e12) return new Date(n * 1000);
    return new Date(n);
  }

  // Fall back to Date parsing for ISO strings
  const d = new Date(String(input));
  return isNaN(d.getTime()) ? null : d;
}

/**
 * Format date as localized date string (e.g., "Jan 15, 2025")
 * @param input - Date input to format
 * @returns Formatted date string or "-" if invalid
 */
export function formatDate(input: string | number | undefined | null): string {
  const date = parseDate(input);
  return date
    ? date.toLocaleDateString("en-US", { 
        month: "short", 
        day: "numeric", 
        year: "numeric" 
      })
    : "-";
}

/**
 * Format time as localized time string (e.g., "3:45 PM")
 * @param input - Date input to format
 * @returns Formatted time string or "-" if invalid
 */
export function formatTime(input: string | number | undefined | null): string {
  const date = parseDate(input);
  return date
    ? date.toLocaleTimeString("en-US", { 
        hour: "numeric", 
        minute: "2-digit", 
        hour12: true 
      })
    : "-";
}

/**
 * Format date and time together (e.g., "Jan 15, 2025 at 3:45 PM")
 * @param input - Date input to format
 * @returns Formatted date and time string or "-" if invalid
 */
export function formatDateTime(input: string | number | undefined | null): string {
  const date = parseDate(input);
  if (!date) return "-";
  return `${formatDate(input)} at ${formatTime(input)}`;
}

/**
 * Format date as relative time (e.g., "2 hours ago", "3 days ago")
 * @param input - Date input to format
 * @returns Relative time string or formatted date if too old
 */
export function formatRelativeTime(input: string | number | undefined | null): string {
  const date = parseDate(input);
  if (!date) return "-";

  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHr = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHr / 24);

  if (diffSec < 60) return "just now";
  if (diffMin < 60) return `${diffMin} minute${diffMin !== 1 ? 's' : ''} ago`;
  if (diffHr < 24) return `${diffHr} hour${diffHr !== 1 ? 's' : ''} ago`;
  if (diffDay < 7) return `${diffDay} day${diffDay !== 1 ? 's' : ''} ago`;
  
  // For older dates, return formatted date
  return formatDate(input);
}

/**
 * Check if a date is within the last N days
 * @param input - Date input to check
 * @param days - Number of days to check against
 * @returns true if date is within the last N days
 */
export function isWithinLastDays(input: string | number | undefined | null, days: number): boolean {
  const date = parseDate(input);
  if (!date) return false;

  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = diffMs / (1000 * 60 * 60 * 24);
  
  return diffDays <= days;
}

/**
 * Format duration in seconds to human-readable string (e.g., "3:45", "1:23:45")
 * @param seconds - Duration in seconds
 * @returns Formatted duration string
 */
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || isNaN(seconds)) return "-";
  
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  if (hrs > 0) {
    return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}
