import { useEffect, useState } from "react";

// Fetches the Microsoft profile image using the access token
export function useMicrosoftProfileImage(accessToken?: string | null): string | null {
  const [imageUrl, setImageUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken) return;
    let isMounted = true;

    const fetchImage = async () => {
      try {
        // Check localStorage cache first
        const cached = localStorage.getItem("ms_profile_image");
        if (cached) {
          setImageUrl(cached);
          return;
        }
        const res = await fetch("https://graph.microsoft.com/v1.0/me/photo/$value", {
          headers: { Authorization: `Bearer ${accessToken}` },
        });
        if (!res.ok) throw new Error("No profile image");
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        if (isMounted) {
          setImageUrl(url);
          localStorage.setItem("ms_profile_image", url);
        }
      } catch {
        // No image or error, fallback to initials
        if (isMounted) setImageUrl(null);
      }
    };
    fetchImage();
    return () => { isMounted = false; };
  }, [accessToken]);

  return imageUrl;
}
