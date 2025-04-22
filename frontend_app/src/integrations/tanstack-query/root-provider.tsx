import { queryClient } from "@/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";

export function getContext() {
  return {
    queryClient,
  };
}

export function Provider({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
