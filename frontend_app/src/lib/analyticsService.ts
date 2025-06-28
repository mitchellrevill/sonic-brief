/**
 * Analytics Service for tracking user events and system activity
 * 
 * This service provides a centralized way to track analytics events
 * throughout the application with proper error handling and retry logic.
 */

import { trackAnalyticsEvent, type AnalyticsEventRequest } from './api';

export class AnalyticsService {
  private static instance: AnalyticsService | null = null;
  private eventQueue: AnalyticsEventRequest[] = [];
  private isProcessingQueue = false;

  private constructor() {
    // Start processing queue when service is created
    this.startQueueProcessor();
  }

  static getInstance(): AnalyticsService {
    if (!AnalyticsService.instance) {
      AnalyticsService.instance = new AnalyticsService();
    }
    return AnalyticsService.instance;
  }

  /**
   * Track a job creation event
   */
  async trackJobCreated(jobId: string, metadata: {
    hasFile: boolean;
    fileName?: string;
    fileSize?: number;
    fileType?: string;
    categoryId: string;
    subcategoryId: string;
    estimatedDurationMinutes?: number;
  }): Promise<void> {
    return this.trackEvent('job_created', {
      job_id: jobId,
      metadata: {
        has_file: metadata.hasFile,
        file_name: metadata.fileName,
        file_size: metadata.fileSize,
        file_type: metadata.fileType,
        prompt_category_id: metadata.categoryId,
        prompt_subcategory_id: metadata.subcategoryId,
        estimated_audio_duration_minutes: metadata.estimatedDurationMinutes
      }
    });
  }

  /**
   * Track a job completion event
   */
  async trackJobCompleted(jobId: string, metadata: {
    actualDurationMinutes?: number;
    transcriptionMethod?: string;
    processingTimeSeconds?: number;
    success: boolean;
  }): Promise<void> {
    return this.trackEvent('job_completed', {
      job_id: jobId,
      metadata: {
        audio_duration_minutes: metadata.actualDurationMinutes,
        transcription_method: metadata.transcriptionMethod,
        processing_time_seconds: metadata.processingTimeSeconds,
        success: metadata.success
      }
    });
  }

  /**
   * Track a user login event
   */
  async trackUserLogin(metadata: {
    loginMethod: string;
    userAgent?: string;
  }): Promise<void> {
    return this.trackEvent('user_login', {
      metadata: {
        login_method: metadata.loginMethod,
        user_agent: metadata.userAgent || navigator.userAgent,
        timestamp: new Date().toISOString()
      }
    });
  }

  /**
   * Track a user logout event
   */
  async trackUserLogout(): Promise<void> {
    return this.trackEvent('user_logout', {
      metadata: {
        timestamp: new Date().toISOString()
      }
    });
  }

  /**
   * Track a page view event
   */
  async trackPageView(path: string, metadata?: Record<string, any>): Promise<void> {
    return this.trackEvent('page_view', {
      metadata: {
        page: path,
        timestamp: new Date().toISOString(),
        ...metadata
      }
    });
  }

  /**
   * Track a user action event
   */
  async trackUserAction(action: string, metadata?: Record<string, any>): Promise<void> {
    return this.trackEvent('user_action', {
      metadata: {
        action,
        timestamp: new Date().toISOString(),
        ...metadata
      }
    });
  }

  /**
   * Generic event tracking method
   */
  private async trackEvent(eventType: string, options: {
    job_id?: string;
    metadata?: Record<string, any>;
  }): Promise<void> {
    const eventData: AnalyticsEventRequest = {
      event_type: eventType,
      job_id: options.job_id,
      metadata: options.metadata
    };

    // Add to queue for processing
    this.eventQueue.push(eventData);
    
    // Process queue if not already processing
    if (!this.isProcessingQueue) {
      this.processQueue();
    }
  }

  /**
   * Process the event queue
   */
  private async processQueue(): Promise<void> {
    if (this.isProcessingQueue || this.eventQueue.length === 0) {
      return;
    }

    this.isProcessingQueue = true;

    while (this.eventQueue.length > 0) {
      const event = this.eventQueue.shift();
      if (!event) continue;

      try {
        await trackAnalyticsEvent(event);
        console.debug('Analytics event tracked:', event.event_type);
      } catch (error) {
        console.debug('Analytics event failed:', event.event_type, error);
        // Could implement retry logic here if needed
      }

      // Small delay to avoid overwhelming the server
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    this.isProcessingQueue = false;
  }

  /**
   * Start the queue processor
   */
  private startQueueProcessor(): void {
    // Process queue every 5 seconds
    setInterval(() => {
      if (!this.isProcessingQueue) {
        this.processQueue();
      }
    }, 5000);
  }

  /**
   * Flush all pending events immediately
   */
  async flush(): Promise<void> {
    await this.processQueue();
  }
}

// Export singleton instance
export const analyticsService = AnalyticsService.getInstance();

// Export convenient tracking functions
export const trackJobCreated = (jobId: string, metadata: Parameters<AnalyticsService['trackJobCreated']>[1]) => 
  analyticsService.trackJobCreated(jobId, metadata);

export const trackJobCompleted = (jobId: string, metadata: Parameters<AnalyticsService['trackJobCompleted']>[1]) => 
  analyticsService.trackJobCompleted(jobId, metadata);

export const trackUserLogin = (metadata: Parameters<AnalyticsService['trackUserLogin']>[0]) => 
  analyticsService.trackUserLogin(metadata);

export const trackUserLogout = () => 
  analyticsService.trackUserLogout();

export const trackPageView = (path: string, metadata?: Record<string, any>) => 
  analyticsService.trackPageView(path, metadata);

export const trackUserAction = (action: string, metadata?: Record<string, any>) => 
  analyticsService.trackUserAction(action, metadata);
