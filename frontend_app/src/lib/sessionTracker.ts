/**
 * Session Tracker for User Activity Analytics
 * 
 * This class tracks user sessions and sends periodic heartbeats
 * to help determine active users and usage patterns.
 */

import { trackSessionEvent, type SessionEventRequest } from './api';

export class SessionTracker {
  private heartbeatInterval: number | null = null;
  private isActive = true;
  private lastActivity = Date.now();
  private sessionStartTime = Date.now();
  private currentPage = window.location.pathname;
  private eventListeners: Array<{ element: EventTarget; event: string; handler: EventListener }> = [];
  private lastFocusEvent = 0;
  private lastBlurEvent = 0;
  private focusBlurThrottle = 5000; // 5 seconds throttle for focus/blur events

  constructor() {
    this.setupActivityListeners();
  }

  /**
   * Start tracking user session
   */
  async startSession(): Promise<void> {
    try {
      this.sessionStartTime = Date.now();
      await this.trackSessionEvent('start');
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
      await this.trackSessionEvent('end');
      this.stopHeartbeat();
      this.cleanupEventListeners();
      console.log('Session tracking ended');
    } catch (error) {
      console.error('Failed to end session tracking:', error);
    }
  }

  /**
   * Track page navigation
   */
  async trackPageView(path: string): Promise<void> {
    try {
      this.currentPage = path;
      this.updateActivity();
      await this.trackSessionEvent('page_view', { page: path });
    } catch (error) {
      console.error('Failed to track page view:', error);
    }
  }

  /**
   * Start sending periodic heartbeats
   */
  private startHeartbeat(): void {
    this.heartbeatInterval = window.setInterval(async () => {
      // Only send heartbeat if user was active in last 5 minutes
      if (this.isActive && Date.now() - this.lastActivity < 300000) {
        await this.trackSessionEvent('heartbeat');
      }
    }, 300000); // Every 5 minutes (300 seconds)
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
   * Set up event listeners for user activity
   */
  private setupActivityListeners(): void {
    const updateActivity = () => this.updateActivity();

    // Helper function to add and track event listeners
    const addTrackedListener = (element: EventTarget, event: string, handler: EventListener, options?: AddEventListenerOptions) => {
      element.addEventListener(event, handler, options);
      this.eventListeners.push({ element, event, handler });
    };

    // Mouse and keyboard activity (these don't send tracking events, just update activity)
    addTrackedListener(document, 'mousemove', updateActivity, { passive: true });
    addTrackedListener(document, 'keypress', updateActivity, { passive: true });
    addTrackedListener(document, 'scroll', updateActivity, { passive: true });
    addTrackedListener(document, 'click', updateActivity, { passive: true });
    
    // Window focus/blur events (throttled to prevent excessive calls)
    const handleFocus = () => {
      const now = Date.now();
      if (now - this.lastFocusEvent > this.focusBlurThrottle) {
        this.isActive = true;
        this.updateActivity();
        this.trackSessionEvent('focus');
        this.lastFocusEvent = now;
      } else {
        // Still update activity even if we don't send the event
        this.isActive = true;
        this.updateActivity();
      }
    };

    const handleBlur = () => {
      const now = Date.now();
      if (now - this.lastBlurEvent > this.focusBlurThrottle) {
        this.isActive = false;
        this.trackSessionEvent('blur');
        this.lastBlurEvent = now;
      } else {
        // Still mark as inactive even if we don't send the event
        this.isActive = false;
      }
    };
    
    addTrackedListener(window, 'focus', handleFocus);
    addTrackedListener(window, 'blur', handleBlur);

    // Page unload event
    addTrackedListener(window, 'beforeunload', () => {
      this.endSession();
    });
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
        timestamp: new Date().toISOString(),
        session_duration: Date.now() - this.sessionStartTime,
        ...metadata
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
  const trackPageView = (path: string) => sessionTracker.trackPageView(path);
  const getSessionInfo = () => sessionTracker.getSessionInfo();

  return {
    startSession,
    endSession,
    trackPageView,
    getSessionInfo
  };
}
