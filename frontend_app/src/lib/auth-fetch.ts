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
    try {
      const parsed = new URL(url, window.location.origin);
      url = parsed.pathname + parsed.search;
    } catch (_) {
      // leave url as-is if it can't be parsed
    }

    // Allow auth endpoints to proceed without forced redirect so UI can show inline errors
    if (/\/api\/auth\//.test(url)) return true;
    // Allow backend job/refinement endpoints to handle auth errors inline (streaming etc.)
    if (/\/api\/jobs\//.test(url)) return true;
    return false;
  };

  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    try {
      const response = await originalFetch(input, init);

      const url = typeof input === "string" ? input : (input instanceof URL ? input.toString() : (input as Request).url);

      if (!shouldBypass(url) && (response.status === 401 || response.status === 403)) {
        // Optional: clear any stored session tokens if used
        try {
          localStorage.removeItem("auth_token");
        } catch (_) {}
        // Redirect preserving intended destination (could be used post-login)
        const target = encodeURIComponent(window.location.pathname + window.location.search);
        const loginUrl = `/login?redirect=${target}`;
        // Use replace so back button doesn't land on a broken protected page repeatedly
        window.location.replace(loginUrl);
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
