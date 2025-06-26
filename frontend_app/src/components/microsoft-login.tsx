import { useEffect, useState } from "react";
import { useRouter } from "@tanstack/react-router";
import { PublicClientApplication } from "@azure/msal-browser";
import { msalConfig, loginRequest } from "../msalConfig";
import { toast } from "sonner";
import { MicrosoftIcon } from "./MicrosoftIcon";
import { microsoftSsoLogin } from "@/lib/api";

const msalInstance = new PublicClientApplication(msalConfig);

export default function MicrosoftLogin() {
  const router = useRouter();
  const [isInitialized, setIsInitialized] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const initializeMsal = async () => {
      try {
        await msalInstance.initialize();
        setIsInitialized(true);
      } catch (error) {
        console.error("MSAL initialization failed:", error);
        toast.error("Authentication service initialization failed");
      }
    };
    initializeMsal();
  }, []);

  const handleLogin = async () => {
    if (!isInitialized) {
      toast.error("Authentication service is still initializing. Please wait.");
      return;
    }
    setLoading(true);
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
        toast.success("Login successful!");
        router.navigate({ to: "/audio-upload" });
      } else {
        toast.error("Login failed");
      }
    } catch (err) {
      console.error("Microsoft login error:", err);
      toast.error("Microsoft login failed. Please try again.");
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
    </div>
  );
}
