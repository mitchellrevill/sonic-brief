/**
 * Enhanced Toast Notifications Utility
 * 
 * Provides rich toast notifications with actions, progress bars, and undo functionality
 * while maintaining backward compatibility with basic toast calls from 'sonner'.
 * 
 * Features:
 * - Action toasts with undo/retry
 * - Progress toasts that update dynamically
 * - Rich toasts with custom content
 * - Standardized messages for common scenarios
 * - Toast queue management
 */

import { toast as sonnerToast, type ExternalToast } from "sonner";
import { CheckCircle2, XCircle, AlertTriangle, Info, Loader2, Download, RotateCcw } from "lucide-react";
import React from "react";

// Re-export basic toast for backward compatibility
export { toast } from "sonner";

/**
 * Toast types with icons
 */
const TOAST_ICONS = {
  success: CheckCircle2,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
  loading: Loader2,
};

/**
 * Enhanced toast options
 */
export interface EnhancedToastOptions extends Omit<ExternalToast, 'icon'> {
  /** Primary action button */
  action?: {
    label: string;
    onClick: () => void | Promise<void>;
  };
  /** Secondary action button */
  secondaryAction?: {
    label: string;
    onClick: () => void | Promise<void>;
  };
  /** Show progress bar (0-100) */
  progress?: number;
  /** Make toast persistent (requires manual dismiss) */
  persistent?: boolean;
  /** Icon component to display (overrides default type icon) */
  iconComponent?: React.ComponentType<{ className?: string }>;
}

/**
 * Base enhanced toast function
 */
function enhancedToast(
  type: keyof typeof TOAST_ICONS,
  message: string,
  options: EnhancedToastOptions = {}
) {
  const {
    action,
    secondaryAction,
    progress,
    persistent,
    iconComponent: CustomIcon,
    ...sonnerOptions
  } = options;

  // Set duration based on options
  const duration = persistent 
    ? Infinity 
    : (action || secondaryAction) 
      ? 10000 // Longer for actionable toasts
      : sonnerOptions.duration || 4000;

  // Build action config
  const actionConfig = action ? {
    label: action.label,
    onClick: async () => {
      try {
        await action.onClick();
      } catch (error) {
        console.error('Toast action failed:', error);
      }
    },
  } : undefined;

  // Build cancel config for secondary action
  const cancelConfig = secondaryAction ? {
    label: secondaryAction.label,
    onClick: async () => {
      try {
        await secondaryAction.onClick();
      } catch (error) {
        console.error('Toast secondary action failed:', error);
      }
    },
  } : undefined;

  // Select icon
  const Icon = CustomIcon || TOAST_ICONS[type];

  // Add progress style if needed
  const finalStyle = progress !== undefined ? {
    ...sonnerOptions.style,
    backgroundImage: `linear-gradient(to right, hsl(var(--primary) / 0.1) ${progress}%, transparent ${progress}%)`,
  } : sonnerOptions.style;

  return sonnerToast[type](message, {
    ...sonnerOptions,
    duration,
    action: actionConfig,
    cancel: cancelConfig,
    icon: React.createElement(Icon, { className: "h-5 w-5" }),
    style: finalStyle,
  });
}

/**
 * Success toast with optional action
 */
export function toastSuccess(message: string, options?: EnhancedToastOptions) {
  return enhancedToast("success", message, options);
}

/**
 * Error toast with optional retry action
 */
export function toastError(message: string, options?: EnhancedToastOptions) {
  return enhancedToast("error", message, {
    duration: 6000, // Longer for errors
    ...options,
  });
}

/**
 * Warning toast
 */
export function toastWarning(message: string, options?: EnhancedToastOptions) {
  return enhancedToast("warning", message, options);
}

/**
 * Info toast
 */
export function toastInfo(message: string, options?: EnhancedToastOptions) {
  return enhancedToast("info", message, options);
}

/**
 * Loading toast with progress support
 */
export function toastLoading(message: string, options?: EnhancedToastOptions) {
  return enhancedToast("loading", message, {
    duration: Infinity, // Loading toasts don't auto-dismiss
    ...options,
  });
}

/**
 * Progress toast that can be updated
 */
export class ProgressToast {
  private toastId: string | number;
  private _progress: number = 0;

  constructor(message: string, description?: string) {
    this.toastId = toastLoading(message, {
      description: description || "0%",
    });
  }

  /**
   * Update progress (0-100)
   */
  update(progress: number, message?: string) {
    this._progress = Math.max(0, Math.min(100, progress));
    sonnerToast.loading(message || "Processing...", {
      id: this.toastId,
      description: `${Math.round(this._progress)}%`,
      style: {
        backgroundImage: `linear-gradient(to right, hsl(var(--primary) / 0.1) ${this._progress}%, transparent ${this._progress}%)`,
      },
    });
  }

  /**
   * Complete with success
   */
  success(message: string, description?: string) {
    sonnerToast.success(message, {
      id: this.toastId,
      description,
      duration: 4000,
    });
  }

  /**
   * Complete with error
   */
  error(message: string, description?: string, options?: EnhancedToastOptions) {
    sonnerToast.error(message, {
      id: this.toastId,
      description,
      duration: 6000,
      ...options,
    });
  }

  /**
   * Dismiss the toast
   */
  dismiss() {
    sonnerToast.dismiss(this.toastId);
  }

  /**
   * Get current progress
   */
  get progress() {
    return this._progress;
  }
}

/**
 * Action toast with undo functionality
 */
export function toastUndo(
  message: string,
  onUndo: () => void | Promise<void>,
  options?: Omit<EnhancedToastOptions, "action">
) {
  return toastSuccess(message, {
    ...options,
    action: {
      label: "Undo",
      onClick: onUndo,
    },
    duration: 10000, // Longer duration for undo
  });
}

/**
 * Retry toast for failed operations
 */
export function toastRetry(
  message: string,
  onRetry: () => void | Promise<void>,
  options?: Omit<EnhancedToastOptions, "action">
) {
  return toastError(message, {
    ...options,
    action: {
      label: "Retry",
      onClick: onRetry,
    },
    iconComponent: RotateCcw,
  });
}

/**
 * Download toast with action
 */
export function toastDownload(
  message: string,
  onDownload: () => void | Promise<void>,
  options?: Omit<EnhancedToastOptions, "action">
) {
  return toastInfo(message, {
    ...options,
    action: {
      label: "Download",
      onClick: onDownload,
    },
    iconComponent: Download,
  });
}

/**
 * Promise toast - shows loading, then success/error based on promise result
 */
export function toastPromise<T>(
  promise: Promise<T>,
  {
    loading,
    success,
    error,
  }: {
    loading: string;
    success: string | ((data: T) => string);
    error: string | ((error: any) => string);
  }
) {
  return sonnerToast.promise(promise, {
    loading,
    success,
    error,
  });
}

// ============================================================================
// Standardized Toast Messages for Common Scenarios
// ============================================================================

/**
 * Recording-related toasts
 */
export const recordingToasts = {
  started: () => toastInfo("Recording started", { description: "Speak clearly into your microphone" }),
  
  stopped: () => toastInfo("Recording stopped", { description: "Processing audio..." }),
  
  paused: () => toastInfo("Recording paused", { description: "Click resume to continue" }),
  
  resumed: () => toastInfo("Recording resumed"),
  
  empty: () => toastWarning("Recording is empty", { 
    description: "No audio detected. Please try again." 
  }),
  
  tooShort: (minDuration: number) => toastWarning("Recording too short", {
    description: `Minimum duration is ${minDuration} seconds`
  }),
  
  draftSaved: () => toastSuccess("Draft saved", {
    description: "Your recording has been saved locally"
  }),
  
  draftRestored: (onDiscard: () => void) => toastInfo("Draft recording available", {
    description: "Would you like to resume or start fresh?",
    action: {
      label: "Discard",
      onClick: onDiscard,
    },
    duration: 10000,
  }),
  
  microphoneError: () => toastError("Microphone access denied", {
    description: "Please allow microphone access in your browser settings",
    persistent: true,
  }),
  
  qualityWarning: (level: "low" | "high") => toastWarning(
    level === "low" ? "Audio level too low" : "Audio level too high",
    { description: level === "low" ? "Speak louder or move closer" : "Speak softer or move away" }
  ),
};

/**
 * Upload-related toasts
 */
export const uploadToasts = {
  started: () => {
    const toast = new ProgressToast("Uploading recording...", "Preparing file...");
    return toast;
  },
  
  converting: () => toastLoading("Converting audio...", {
    description: "Optimizing file format"
  }),
  
  success: () => toastSuccess("Upload complete!", {
    description: "Your recording is being processed"
  }),
  
  failed: (onRetry: () => void, onDownload: () => void) => toastError("Upload failed", {
    description: "Connection interrupted",
    action: {
      label: "Retry",
      onClick: onRetry,
    },
    secondaryAction: {
      label: "Download",
      onClick: onDownload,
    },
    persistent: true,
  }),
  
  retrying: (attempt: number, maxAttempts: number) => toastLoading(
    `Retrying upload (${attempt}/${maxAttempts})...`
  ),
  
  sizeTooLarge: (size: number, maxSize: number) => toastError("File too large", {
    description: `File is ${(size / (1024 * 1024)).toFixed(1)}MB. Maximum is ${maxSize}MB.`,
  }),
};

/**
 * Authentication toasts
 */
export const authToasts = {
  loginSuccess: () => toastSuccess("Login successful!", {
    description: "Redirecting..."
  }),
  
  loginFailed: (onRetry?: () => void) => toastError("Login failed", {
    description: "Please check your credentials and try again",
    action: onRetry ? {
      label: "Retry",
      onClick: onRetry,
    } : undefined,
  }),
  
  sessionExpired: () => toastWarning("Session expired", {
    description: "Please log in again",
    persistent: true,
  }),
  
  logoutSuccess: () => toastInfo("Logged out successfully"),
};

/**
 * File operation toasts
 */
export const fileToasts = {
  downloaded: (fileName: string) => toastSuccess(`${fileName} downloaded`),
  
  downloadFailed: (fileName: string, onRetry?: () => void) => toastError(`Failed to download ${fileName}`, {
    action: onRetry ? {
      label: "Retry",
      onClick: onRetry,
    } : undefined,
  }),
  
  copied: (label: string) => toastSuccess(`${label} copied to clipboard!`),
  
  copyFailed: (label: string) => toastError(`Failed to copy ${label}`),
  
  deleted: (fileName: string, onUndo?: () => void) => {
    if (onUndo) {
      return toastUndo(`${fileName} deleted`, onUndo, {
        description: "Moved to trash"
      });
    }
    return toastSuccess(`${fileName} deleted`, { description: "Moved to trash" });
  },
  
  restored: (fileName: string) => toastSuccess(`${fileName} restored`),
};

/**
 * Sharing toasts
 */
export const sharingToasts = {
  granted: (email: string, jobTitle: string) => toastSuccess(`Shared with ${email}`, {
    description: `${jobTitle} is now accessible`
  }),
  
  revoked: (email: string, onUndo?: () => void) => {
    if (onUndo) {
      return toastUndo(`Removed sharing with ${email}`, onUndo);
    }
    return toastSuccess(`Removed sharing with ${email}`);
  },
  
  failed: (email: string, error: string) => toastError(`Failed to share with ${email}`, {
    description: error
  }),
};

/**
 * Permission toasts
 */
export const permissionToasts = {
  updated: (permission: string) => toastSuccess(`Permission updated to ${permission}`),
  
  denied: (action: string) => toastError("Permission denied", {
    description: `You don't have permission to ${action}`
  }),
  
  delegated: () => toastSuccess("Permission delegated successfully"),
  
  revoked: () => toastSuccess("Permission delegation revoked"),
};

/**
 * Settings toasts
 */
export const settingsToasts = {
  saved: (setting?: string) => toastSuccess(
    setting ? `${setting} saved` : "Settings saved",
    { description: "Changes have been applied" }
  ),
  
  failed: (setting?: string) => toastError(
    setting ? `Failed to save ${setting}` : "Failed to save settings"
  ),
  
  reset: () => toastInfo("Settings reset to defaults"),
};

/**
 * Storage toasts
 */
export const storageToasts = {
  almostFull: (percentage: number) => toastWarning("Storage almost full", {
    description: `${percentage}% of available storage used. Consider clearing old recordings.`,
    persistent: true,
  }),
  
  full: () => toastError("Storage full", {
    description: "Delete old recordings or clear browser data to continue",
    persistent: true,
  }),
  
  usageHigh: (percentage: number) => toastInfo("Storage usage high", {
    description: `${percentage}% of available storage used`
  }),
};
