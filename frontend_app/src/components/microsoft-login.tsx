import { useEffect, useState, useRef } from "react";
import { useRouter } from "@tanstack/react-router";
import { PublicClientApplication } from "@azure/msal-browser";
import { msalConfig, loginRequest } from "../msalConfig";
import { authToasts } from "@/lib/toast-utils";
import { toast } from "sonner";
import { MicrosoftIcon } from "./MicrosoftIcon";
import { microsoftSsoLogin } from "@/lib/api";

const msalInstance = new PublicClientApplication(msalConfig);

export default function MicrosoftLogin() {
  const router = useRouter();
  const [isInitialized, setIsInitialized] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [consoleLogs, setConsoleLogs] = useState<string[]>([]);
  const logsRef = useRef<string[]>([]);

  useEffect(() => {
    const initializeMsal = async () => {
      try {
        await msalInstance.initialize();
        setIsInitialized(true);
      } catch (error: any) {
        console.error("MSAL initialization failed:", error);
        setErrorMessage(error?.message || String(error));
        toast.error("Authentication service initialization failed", {
          description: "Please refresh the page and try again"
        });
      }
    };
    initializeMsal();
  }, []);

  // Patch console.log and console.error to capture logs
  useEffect(() => {
    const origLog = console.log;
    const origError = console.error;
    console.log = (...args) => {
      logsRef.current = [...logsRef.current, args.map(String).join(" ")];
      setConsoleLogs([...logsRef.current]);
      origLog(...args);
    };
    console.error = (...args) => {
      logsRef.current = [...logsRef.current, args.map(String).join(" ")];
      setConsoleLogs([...logsRef.current]);
      origError(...args);
    };
    return () => {
      console.log = origLog;
      console.error = origError;
    };
  }, []);

  const handleLogin = async () => {
    if (!isInitialized) {
      toast.warning("Authentication service is still initializing", {
        description: "Please wait a moment and try again"
      });
      return;
    }
    setLoading(true);
    setErrorMessage(null);
    try {
      const response = await msalInstance.loginPopup(loginRequest);
      const mappedResponse = {
        ...response,
        id_token: response.idToken,
        access_token: response.accessToken,
        email: response.account?.username,
      };
      const backendResponse = await microsoftSsoLogin(mappedResponse);
      if (backendResponse) {
        const data = backendResponse;
        localStorage.setItem("token", data.access_token);
        if (data.permission) {
          localStorage.setItem("permission", data.permission);
        }
        authToasts.loginSuccess();
        router.navigate({ to: "/simple-upload" });
      } else {
        setErrorMessage("Login failed");
        console.error("Microsoft login error: Login failed");
        authToasts.loginFailed(() => handleLogin());
      }
    } catch (err: any) {
      console.error("Microsoft login error:", err);
      setErrorMessage(err?.message || String(err));
      authToasts.loginFailed(() => handleLogin());
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center h-full">
      <button
        onClick={handleLogin}
        className={
          `w-full max-w-xs flex items-center justify-center gap-2 px-6 py-3 rounded-full font-semibold shadow-lg transition-all duration-200
          bg-gradient-to-r from-[#0078D4] to-[#005A9E] text-white border-2 border-[#0078D4] focus:outline-none focus:ring-4 focus:ring-blue-200
          hover:scale-105 hover:shadow-xl active:scale-100 disabled:opacity-60 disabled:cursor-not-allowed`
        }
        style={{ minHeight: 56, fontSize: 18, position: 'relative' }}
        disabled={!isInitialized || loading}
        aria-busy={loading}
        aria-label="Sign in with Microsoft"
      >
        <span className={loading ? "opacity-60" : ""}>
          <MicrosoftIcon />
        </span>
        {loading ? (
          <span className="ml-2 flex items-center">
            <svg className="animate-spin mr-2" width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="white" strokeWidth="4" />
              <path className="opacity-75" fill="#fff" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
            </svg>
            Signing in...
          </span>
        ) : isInitialized ? (
          <span className="flex items-center">
            Sign in with <span className="font-bold text-white ml-1">Microsoft</span>
          </span>
        ) : (
          "Initializing..."
        )}
      </button>
      {errorMessage && (
        <div className="mt-4 w-full max-w-xs text-red-700 text-sm break-words" style={{background: 'none', border: 'none', boxShadow: 'none', padding: 0}}>
          <strong>Microsoft Login Error:</strong> {errorMessage}
        </div>
      )}
      {consoleLogs.length > 0 && (
        <div className="mt-4 w-full max-w-xs text-gray-800 text-xs break-words" style={{background: 'none', border: 'none', boxShadow: 'none', padding: 0, maxHeight: 200, overflowY: 'auto'}}>
          <strong>Console Output:</strong>
          <ul className="list-disc pl-4">
            {consoleLogs.slice(-10).map((log, idx) => (
              <li key={idx}>{log}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
