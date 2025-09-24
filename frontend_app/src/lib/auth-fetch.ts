// Lightweight global fetch interceptor to redirect to /login on auth/permission failures
// Triggers on HTTP 401 (expired/invalid session) or 403 (permission denied)
// Avoids redirect loops and ignores responses while already on /login

(() => {
  if (typeof window === "undefined") return;
  const originalFetch = window.fetch.bind(window);

  const shouldBypass = (url: string) => {
    // Avoid intercepting static assets or already on login
    if (window.location.pathname === "/login") return true;

    // Normalize: if an absolute URL is provided, strip origin so the regexp matches
    let normalizedUrl = url;
    try {
      const parsed = new URL(url, window.location.origin);
      normalizedUrl = parsed.pathname + parsed.search;
    } catch (_) {
      // If URL parsing fails, check if it's a relative path or use as-is
      if (!url.startsWith('/')) {
        // If it's not absolute and doesn't start with /, it might be a relative path
        normalizedUrl = '/' + url;
      }
    }

    // Check for permissions endpoints - these should NEVER be bypassed
    // so that auth errors trigger immediate redirect to login
    if (normalizedUrl.includes('/permissions') || normalizedUrl.includes('/api/auth/')) {
      // For permissions endpoints, only bypass if it's not actually a permissions check
      if (normalizedUrl.includes('/permissions')) {
        return false; // Never bypass permissions endpoints
      }
      // For other auth endpoints, bypass to allow inline error handling
      return true;
    }

    // Allow backend job/refinement endpoints to handle auth errors inline (streaming etc.)
    if (normalizedUrl.includes('/api/jobs/')) return true;
    return false;
  };

  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    try {
      const response = await originalFetch(input, init);

      const url = typeof input === "string" ? input : (input instanceof URL ? input.toString() : (input as Request).url);

      if (!shouldBypass(url) && (response.status === 401 || response.status === 403)) {
        // Clear all stored authentication data
        try {
          localStorage.removeItem("token");
          localStorage.removeItem("permission");
          localStorage.removeItem("auth_token");
          // Clear any other auth-related storage
          localStorage.removeItem("user");
          localStorage.removeItem("profile");
          sessionStorage.clear(); // Clear session storage too
        } catch (_) {}
        // Redirect preserving intended destination (could be used post-login)
        const target = encodeURIComponent(window.location.pathname + window.location.search);
        const loginUrl = `/login?redirect=${target}`;
        // Use replace so back button doesn't land on a broken protected page repeatedly
        window.location.replace(loginUrl);
      }

      // Special handling for permissions endpoints: also check for auth errors in successful responses
      if (url.includes('/permissions') && response.ok) {
        try {
          // Clone the response to check the body without consuming it
          const clonedResponse = response.clone();
          const data = await clonedResponse.json();
          // Check for common auth error patterns
          if (data.detail && (
            data.detail.includes('Invalid token') ||
            data.detail.includes('Signature verification failed') ||
            data.detail.includes('Token expired') ||
            data.detail.includes('Authentication failed')
          )) {
            // This looks like an auth error despite 200 status
            // Clear all stored authentication data
            try {
              localStorage.removeItem("token");
              localStorage.removeItem("permission");
              localStorage.removeItem("auth_token");
              localStorage.removeItem("user");
              localStorage.removeItem("profile");
              sessionStorage.clear();
            } catch (_) {}
            const target = encodeURIComponent(window.location.pathname + window.location.search);
            const loginUrl = `/login?redirect=${target}`;
            window.location.replace(loginUrl);
            return response; // Still return the original response
          }
        } catch (e) {
          // If we can't parse JSON or check for errors, continue normally
        }
      }

      return response;
    } catch (err) {
      // Network or CORS errors: do not force a navigation. Let callers handle errors.
      // Log for visibility but rethrow so UI components (including streaming clients)
      // can display inline errors instead of triggering a full-page redirect.
      console.warn("Network error during fetch (no auto-redirect):", err);
      throw err;
    }
  };
})();
