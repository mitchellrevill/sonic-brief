import { MutationCache, QueryCache, QueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { getMessageFromError } from "./lib/error";

function onError(error: Error) {
  if (typeof error.message === "string") {
    try {
      const parsed = JSON.parse(error.message);
      if (parsed.body) {
        error.message =
          typeof parsed.body === "string"
            ? parsed.body
            : (parsed.body?.result?.message ??
              parsed.body?.issues

                ?.map((m: any) => m?.message)
                .filter(Boolean)
                .join(", ") ??
              parsed.body?.message ??
              parsed.message ??
              error.message);
      }
    } catch (_e) {
      // noop
    }
  }
  toast.error("An error occurred", {
    description: getMessageFromError(error),
  });
}

export const queryClient: QueryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnReconnect: () => !queryClient.isMutating(),
      // Default stale time of 30 seconds to reduce unnecessary refetches
      staleTime: 30 * 1000,
      // Keep inactive queries in cache for 5 minutes
      gcTime: 5 * 60 * 1000,
      // Retry failed requests with exponential backoff
      retry: (failureCount, error: any) => {
        // Don't retry on 4xx errors (client errors)
        if (error?.response?.status >= 400 && error?.response?.status < 500) {
          return false;
        }
        // Retry up to 2 times for other errors
        return failureCount < 2;
      },
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
  },
  queryCache: new QueryCache({
    onError,
  }),
  mutationCache: new MutationCache({
    onError,
    onSettled: () => {
      if (queryClient.isMutating() === 1) {
        return queryClient.invalidateQueries();
      }
    },
  }),
});
