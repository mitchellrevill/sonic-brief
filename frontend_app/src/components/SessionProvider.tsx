import { useEffect } from 'react';
import { useRouter } from '@tanstack/react-router';
import { sessionTracker } from '@/lib/sessionTracker';

/**
 * SessionProvider component that manages user session tracking
 * 
 * This component:
 * - Starts session tracking when mounted
 * - Tracks page navigation
 * - Ends session when unmounted
 * - Handles browser focus/blur events
 */
export function SessionProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  useEffect(() => {
    // Start session tracking when component mounts
    sessionTracker.startSession();

    // Track page navigation
    const unsubscribe = router.subscribe('onLoad', ({ toLocation }) => {
      sessionTracker.trackPageView(toLocation.pathname);
    });

    // Cleanup function
    return () => {
      unsubscribe();
      sessionTracker.endSession();
    };
  }, [router]);

  return <>{children}</>;
}

/**
 * Hook to manually track session events
 */
export function useSessionTracking() {
  const trackPageView = (path: string) => {
    sessionTracker.trackPageView(path);
  };

  const getSessionInfo = () => {
    return sessionTracker.getSessionInfo();
  };

  return {
    trackPageView,
    getSessionInfo
  };
}
