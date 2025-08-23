/**
 * Session Tracker for User Activity Analytics
 * 
 * This class tracks user sessions and sends periodic heartbeats
 * to help determine active users and usage patterns.
 */

import { trackSessionEvent, type SessionEventRequest } from './api';

export class SessionTracker {
  private heartbeatInterval: number | null = null;
  private heartbeatPeriodMs = 60000; // 1 minute
  private idleTimeoutMs = 5 * 60 * 1000; // 5 minutes
  private isActive = true;
  private lastActivity = Date.now();
  private sessionStartTime = Date.now();
  private currentPage = window.location.pathname;
  private eventListeners: Array<{ element: EventTarget; event: string; handler: EventListener }> = [];

  constructor() {
    this.setupActivityListeners();
  }

  /**
   * Start tracking user session
   */
  async startSession(): Promise<void> {
    try {
      this.sessionStartTime = Date.now();
      await this.trackSessionEvent('start', { page: this.currentPage });
      this.startHeartbeat();
      console.log('Session tracking started');
    } catch (error) {
      console.error('Failed to start session tracking:', error);
    }
  }

  /**
   * End user session
   */
  async endSession(): Promise<void> {
    try {
      await this.trackSessionEvent('end', { page: this.currentPage });
      this.stopHeartbeat();
      this.cleanupEventListeners();
      console.log('Session tracking ended');
    } catch (error) {
      console.error('Failed to end session tracking:', error);
    }
  }

  /**
   * Track page navigation (just update current page, don't send event)
   */
  setCurrentPage(path: string): void {
    this.currentPage = path;
    this.updateActivity();
  }

  /**
   * Start sending periodic heartbeats (every 2 minutes)
   */
  private startHeartbeat(): void {
    this.heartbeatInterval = window.setInterval(async () => {
      // Auto-detect idle based on last activity
      const now = Date.now();
      if (now - this.lastActivity > this.idleTimeoutMs) {
        this.isActive = false;
      } else {
        this.isActive = true;
      }
      if (this.isActive) {
        await this.trackSessionEvent('heartbeat', { page: this.currentPage });
      }
    }, this.heartbeatPeriodMs);
  }

  /**
   * Stop sending heartbeats
   */
  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      window.clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  /**
   * Set up event listeners for user activity (no longer sends session events for focus/blur/page_view)
   */
  private setupActivityListeners(): void {
    const updateActivity = () => this.updateActivity();
    const addTrackedListener = (element: EventTarget, event: string, handler: EventListener, options?: AddEventListenerOptions) => {
      element.addEventListener(event, handler, options);
      this.eventListeners.push({ element, event, handler });
    };
    addTrackedListener(document, 'mousemove', updateActivity, { passive: true });
    addTrackedListener(document, 'keypress', updateActivity, { passive: true });
    addTrackedListener(document, 'scroll', updateActivity, { passive: true });
    addTrackedListener(document, 'click', updateActivity, { passive: true });
    // Only update activity on focus/blur, don't send session events
    addTrackedListener(window, 'focus', () => { this.isActive = true; this.updateActivity(); });
    addTrackedListener(window, 'blur', () => { this.isActive = false; });
    // Page unload event
    addTrackedListener(window, 'beforeunload', () => { this.endSession(); });
  }

  /**
   * Update last activity timestamp
   */
  private updateActivity(): void {
    this.lastActivity = Date.now();
    this.isActive = true;
  }

  /**
   * Clean up event listeners
   */
  private cleanupEventListeners(): void {
    this.eventListeners.forEach(({ element, event, handler }) => {
      element.removeEventListener(event, handler);
    });
    this.eventListeners = [];
  }

  /**
   * Completely destroy the session tracker instance
   */
  destroy(): void {
    this.stopHeartbeat();
    this.cleanupEventListeners();
    this.isActive = false;
  }

  /**
   * Send session event to backend
   */
  private async trackSessionEvent(action: string, metadata: Record<string, any> = {}): Promise<void> {
    try {
      const eventData: SessionEventRequest = {
        action,
        page: this.currentPage,
        ...metadata,
        session_duration: Date.now() - this.sessionStartTime,
      };

      await trackSessionEvent(eventData);
    } catch (error) {
      // Silently fail to avoid disrupting user experience
      console.debug('Session tracking error:', error);
    }
  }

  /**
   * Get current session info
   */
  getSessionInfo(): {
    isActive: boolean;
    duration: number;
    lastActivity: number;
    currentPage: string;
  } {
    return {
      isActive: this.isActive,
      duration: Date.now() - this.sessionStartTime,
      lastActivity: this.lastActivity,
      currentPage: this.currentPage
    };
  }
}

// Global session tracker instance (singleton)
let sessionTrackerInstance: SessionTracker | null = null;

export const sessionTracker = (() => {
  if (!sessionTrackerInstance) {
    sessionTrackerInstance = new SessionTracker();
  }
  return sessionTrackerInstance;
})();

export const setSessionPage = (path: string) => sessionTracker.setCurrentPage(path);

// Helper function to reset the session tracker (useful for testing or cleanup)
export const resetSessionTracker = () => {
  if (sessionTrackerInstance) {
    sessionTrackerInstance.destroy();
    sessionTrackerInstance = null;
  }
};

// Hook for React components
export function useSessionTracker() {
  const startSession = () => sessionTracker.startSession();
  const endSession = () => sessionTracker.endSession();
  const getSessionInfo = () => sessionTracker.getSessionInfo();

  return {
    startSession,
    endSession,
    getSessionInfo
  };
}
