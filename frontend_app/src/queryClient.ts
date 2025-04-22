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
