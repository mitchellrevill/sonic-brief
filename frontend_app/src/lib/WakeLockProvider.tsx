
import { useScreenWakeLock } from "../hooks/useScreenWakeLock";
import type { ReactNode } from "react";

/**
 * App-level wrapper that keeps the screen awake while mounted.
 * Place this at the root of your app (e.g., in main.tsx).
 */
export function WakeLockProvider({ children }: { children: ReactNode }) {
  useScreenWakeLock();
  return <>{children}</>;
}
