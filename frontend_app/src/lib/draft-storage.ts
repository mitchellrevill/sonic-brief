/**
 * Draft Recording Storage Utility
 * 
 * Provides persistent storage for draft recordings using IndexedDB with localStorage fallback.
 * Handles automatic cleanup, quota management, and data integrity.
 */

import { storageToasts } from "./toast-utils";

const DB_NAME = "SonicBriefDrafts";
const DB_VERSION = 1;
const STORE_NAME = "recordings";
const MAX_DRAFT_AGE_MS = 7 * 24 * 60 * 60 * 1000; // 7 days
const MAX_DRAFT_SIZE = 50 * 1024 * 1024; // 50MB

export interface DraftRecording {
  id: string;
  categoryId: string;
  subcategoryId: string;
  categoryName: string;
  subcategoryName: string;
  audioBlob: Blob;
  duration: number;
  timestamp: number;
  preSessionData?: Record<string, any>;
  mimeType?: string;
  uploaded?: boolean; // Track if this recording was successfully uploaded
  jobId?: string; // Track the upload job ID if uploaded
}

// Optional runtime logger for diagnostics (DEV only)
let runtimeLogger: ((msg: string) => void) | null = null;

export function setDraftStorageLogger(logger: ((msg: string) => void) | null) {
  runtimeLogger = logger as any;
}

function log(msg: string) {
  try {
    console.debug('[draft-storage]', msg);
  } catch {}
  try {
    runtimeLogger && runtimeLogger(msg);
  } catch {}
}

class DraftStorageError extends Error {
  constructor(
    message: string,
    public code: string,
  ) {
    super(message);
    this.name = "DraftStorageError";
  }
}

/**
 * Initialize IndexedDB database
 */
async function initDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => {
      reject(new DraftStorageError("Failed to open database", "DB_OPEN_ERROR"));
    };

    request.onsuccess = () => {
      resolve(request.result);
    };

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: "id" });
        store.createIndex("timestamp", "timestamp", { unique: false });
        store.createIndex("categoryId", "categoryId", { unique: false });
      }
    };
  });
}

/**
 * Generate unique draft ID
 */
function generateDraftId(categoryId: string, subcategoryId: string): string {
  return `draft-${categoryId}-${subcategoryId}-${Date.now()}`;
}

/**
 * Check if storage is available
 */
function isStorageAvailable(): boolean {
  try {
    const test = "__storage_test__";
    localStorage.setItem(test, test);
    localStorage.removeItem(test);
    return true;
  } catch {
    return false;
  }
}

/**
 * Estimate storage quota usage
 */
async function getStorageEstimate(): Promise<{ usage: number; quota: number; percentage: number }> {
  if ("storage" in navigator && "estimate" in navigator.storage) {
    const estimate = await navigator.storage.estimate();
    const usage = estimate.usage || 0;
    const quota = estimate.quota || 0;
    const percentage = quota > 0 ? (usage / quota) * 100 : 0;
    
    return { usage, quota, percentage };
  }
  
  return { usage: 0, quota: 0, percentage: 0 };
}

/**
 * Check if there's enough storage space
 */
async function hasEnoughSpace(requiredBytes: number): Promise<boolean> {
  const { usage, quota } = await getStorageEstimate();
  
  if (quota === 0) return true; // Can't determine, assume yes
  
  const available = quota - usage;
  return available > requiredBytes + (10 * 1024 * 1024); // Keep 10MB buffer
}

/**
 * Save draft recording to IndexedDB
 */
export async function saveDraftRecording(draft: Omit<DraftRecording, "id" | "timestamp">): Promise<string> {
  // Check if storage is available
  if (!isStorageAvailable()) {
    throw new DraftStorageError("Storage is not available. Please check browser settings.", "STORAGE_UNAVAILABLE");
  }

  // Check draft size
  if (draft.audioBlob.size > MAX_DRAFT_SIZE) {
    throw new DraftStorageError(
      `Recording is too large (${(draft.audioBlob.size / (1024 * 1024)).toFixed(1)}MB). Maximum size is 50MB.`,
      "SIZE_EXCEEDED"
    );
  }

  // Delete any existing draft for the same category/subcategory to avoid accumulation
  try {
    const existingDraft = await getDraftRecording(draft.categoryId, draft.subcategoryId, true); // include uploaded drafts for cleanup
    if (existingDraft) {
      log(`saveDraftRecording: deleting existing draft ${existingDraft.id} before saving new one`);
      await deleteDraftRecording(existingDraft.id);
    }
  } catch (deleteError) {
    // Log but don't fail the save if cleanup fails
    console.warn('Failed to cleanup existing draft:', deleteError);
    log(`saveDraftRecording: cleanup failed ${String(deleteError)}`);
  }

  // Check available space
  const hasSpace = await hasEnoughSpace(draft.audioBlob.size);
  if (!hasSpace) {
    // Try to cleanup old drafts
    await cleanupOldDrafts();
    
    // Check again
    const hasSpaceAfterCleanup = await hasEnoughSpace(draft.audioBlob.size);
    if (!hasSpaceAfterCleanup) {
      throw new DraftStorageError(
        "Not enough storage space. Please delete some old recordings or clear browser data.",
        "QUOTA_EXCEEDED"
      );
    }
  }

  const draftId = generateDraftId(draft.categoryId, draft.subcategoryId);
  const draftRecord: DraftRecording = {
    ...draft,
    id: draftId,
    timestamp: Date.now(),
  };

  try {
    log('initDB: opening database');
    const db = await initDB();
    
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORE_NAME, "readwrite");
      const store = transaction.objectStore(STORE_NAME);
      const request = store.put(draftRecord);

      request.onsuccess = () => {
        resolve(draftId);
      };

      request.onerror = () => {
  log('saveDraftRecording: request.onerror');
  reject(new DraftStorageError("Failed to save draft", "SAVE_ERROR"));
      };

      transaction.oncomplete = () => {
        log(`saveDraftRecording: transaction complete for ${draftId}`);
        db.close();
      };
    });
  } catch (error) {
    console.error("Error saving draft:", error);
    log(`saveDraftRecording: caught error ${String(error)}`);
    throw new DraftStorageError("Failed to save draft recording", "SAVE_ERROR");
  }
}

/**
 * Get draft recording by category and subcategory
 * @param includeUploaded - if true, includes drafts that were successfully uploaded (default: false)
 */
export async function getDraftRecording(categoryId: string, subcategoryId: string, includeUploaded = false): Promise<DraftRecording | null> {
  try {
    log(`getDraftRecording: fetching for category=${categoryId} subcategory=${subcategoryId} includeUploaded=${includeUploaded}`);
    const db = await initDB();
    
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORE_NAME, "readonly");
      const store = transaction.objectStore(STORE_NAME);
      const index = store.index("categoryId");
      const request = index.getAll(categoryId);

      request.onsuccess = () => {
        const drafts = request.result as DraftRecording[];
        
        // Find the most recent draft for this category/subcategory
        // Filter out uploaded drafts unless explicitly requested
        const matchingDraft = drafts
          .filter(d => d.subcategoryId === subcategoryId && (includeUploaded || !d.uploaded))
          .sort((a, b) => b.timestamp - a.timestamp)[0];
        
        resolve(matchingDraft || null);
      };

      request.onerror = () => {
        log('getDraftRecording: request.onerror');
        reject(new DraftStorageError("Failed to retrieve draft", "READ_ERROR"));
      };

      transaction.oncomplete = () => {
        log('getDraftRecording: transaction complete');
        db.close();
      };
    });
  } catch (error) {
    console.error("Error retrieving draft:", error);
    log(`getDraftRecording: caught error ${String(error)}`);
    return null;
  }
}

/**
 * Get all draft recordings
 */
export async function getAllDrafts(): Promise<DraftRecording[]> {
  try {
    log('getAllDrafts: fetching all drafts');
    const db = await initDB();
    
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORE_NAME, "readonly");
      const store = transaction.objectStore(STORE_NAME);
      const request = store.getAll();

      request.onsuccess = () => {
        resolve(request.result as DraftRecording[]);
      };

      request.onerror = () => {
        log('getAllDrafts: request.onerror');
        reject(new DraftStorageError("Failed to retrieve drafts", "READ_ERROR"));
      };

      transaction.oncomplete = () => {
        log('getAllDrafts: transaction complete');
        db.close();
      };
    });
  } catch (error) {
    console.error("Error retrieving all drafts:", error);
    log(`getAllDrafts: caught error ${String(error)}`);
    return [];
  }
}

/**
 * Delete draft recording by ID
 */
export async function deleteDraftRecording(draftId: string): Promise<void> {
  try {
    log(`deleteDraftRecording: deleting ${draftId}`);
    const db = await initDB();
    
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORE_NAME, "readwrite");
      const store = transaction.objectStore(STORE_NAME);
      const request = store.delete(draftId);

      request.onsuccess = () => {
        resolve();
      };

      request.onerror = () => {
        log('deleteDraftRecording: request.onerror');
        reject(new DraftStorageError("Failed to delete draft", "DELETE_ERROR"));
      };

      transaction.oncomplete = () => {
        log('deleteDraftRecording: transaction complete');
        db.close();
      };
    });
  } catch (error) {
    console.error("Error deleting draft:", error);
    log(`deleteDraftRecording: caught error ${String(error)}`);
  }
}

/**
 * Clean up old draft recordings (older than 7 days)
 */
export async function cleanupOldDrafts(): Promise<number> {
  try {
    const drafts = await getAllDrafts();
    const now = Date.now();
    const oldDrafts = drafts.filter(d => now - d.timestamp > MAX_DRAFT_AGE_MS);

    for (const draft of oldDrafts) {
      await deleteDraftRecording(draft.id);
    }

    if (oldDrafts.length > 0) {
      console.log(`Cleaned up ${oldDrafts.length} old draft(s)`);
    }

    return oldDrafts.length;
  } catch (error) {
    console.error("Error cleaning up old drafts:", error);
    return 0;
  }
}

/**
 * Get storage usage summary
 */
export async function getStorageSummary(): Promise<{
  draftCount: number;
  totalSize: number;
  oldestDraft: number | null;
  storageUsage: number;
  storageQuota: number;
  storagePercentage: number;
}> {
  try {
    const drafts = await getAllDrafts();
    const totalSize = drafts.reduce((sum, d) => sum + d.audioBlob.size, 0);
    const oldestDraft = drafts.length > 0 
      ? Math.min(...drafts.map(d => d.timestamp))
      : null;
    
    const { usage, quota, percentage } = await getStorageEstimate();

    return {
      draftCount: drafts.length,
      totalSize,
      oldestDraft,
      storageUsage: usage,
      storageQuota: quota,
      storagePercentage: percentage,
    };
  } catch (error) {
    console.error("Error getting storage summary:", error);
    return {
      draftCount: 0,
      totalSize: 0,
      oldestDraft: null,
      storageUsage: 0,
      storageQuota: 0,
      storagePercentage: 0,
    };
  }
}

/**
 * Format bytes to human-readable string
 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 Bytes";
  
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
}

/**
 * Show storage warning if usage is high
 */
export async function checkStorageAndWarn(): Promise<void> {
  const { storagePercentage } = await getStorageSummary();
  
  if (storagePercentage > 90) {
    storageToasts.almostFull(Math.round(storagePercentage));
  } else if (storagePercentage > 75) {
    storageToasts.usageHigh(Math.round(storagePercentage));
  }
}
