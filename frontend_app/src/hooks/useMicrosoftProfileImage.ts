import { useEffect, useState } from "react";
import { fetchMicrosoftProfileImage } from "@/lib/api";

// Fetches the Microsoft profile image using the access token
export function useMicrosoftProfileImage(accessToken?: string | null): string | null {
  const [imageUrl, setImageUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken) return;
    let isMounted = true;

    const fetchImage = async () => {
      try {
        const url = await fetchMicrosoftProfileImage(accessToken);
        setImageUrl(url);
      } catch {
        if (isMounted) setImageUrl(null);
      }
    };
    fetchImage();
    return () => { isMounted = false; };
  }, [accessToken]);

  return imageUrl;
}
