import { useEffect, useRef } from "react";

/**
 * Keeps the device screen awake while the component is mounted.
 * Uses the Screen Wake Lock API (supported in most modern browsers).
 *
 * Usage: Call useScreenWakeLock() in your component.
 */
export function useScreenWakeLock() {
  const wakeLockRef = useRef<WakeLockSentinel | null>(null);

  useEffect(() => {
    let isActive = true;
    async function requestWakeLock() {
      try {
        if ("wakeLock" in navigator) {
          // @ts-ignore
          wakeLockRef.current = await navigator.wakeLock.request("screen");
        }
      } catch (err) {
        // Optionally handle error (e.g., show a message to the user)
        console.error("Wake Lock error:", err);
      }
    }

    requestWakeLock();

    // Re-acquire wake lock on visibility change (e.g., after tab switch)
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible" && isActive) {
        requestWakeLock();
      }
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      isActive = false;
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      wakeLockRef.current?.release();
      wakeLockRef.current = null;
    };
  }, []);
}
