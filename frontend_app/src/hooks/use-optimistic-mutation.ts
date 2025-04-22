import type { UseMutationOptions } from "@tanstack/react-query";
import { queryClient } from "@/queryClient";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";

interface OptimisticUpdateConfig<TData> {
  queryKey: Array<string>;
  updateFn: (oldData: Array<TData> | undefined, newData: any) => Array<TData>;
  successMessage?: string;
  onMutateSideEffect?: () => void;
}

interface OptimisticMutationConfig<TData, TVariables, TError = Error>
  extends OptimisticUpdateConfig<TData> {
  mutationFn: (variables: TVariables) => Promise<TData>;
  options?: Omit<
    UseMutationOptions<
      TData,
      TError,
      TVariables,
      { previousData: Array<TData> | undefined }
    >,
    "mutationFn" | "onMutate" | "onError" | "onSuccess" | "onSettled"
  >;
}

export function useOptimisticMutation<TData, TVariables, TError = Error>({
  mutationFn,
  queryKey,
  updateFn,
  successMessage,
  onMutateSideEffect,
  options,
}: OptimisticMutationConfig<TData, TVariables, TError>) {
  return useMutation({
    mutationFn,
    onMutate: async (newData) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey });

      // Snapshot the previous value
      const previousData = queryClient.getQueryData<Array<TData>>(queryKey);

      // Optimistically update
      queryClient.setQueryData<Array<TData>>(queryKey, (old) =>
        updateFn(old, newData),
      );

      // Run side effects, like resetting the form or closing the dialog
      onMutateSideEffect?.();

      return { previousData };
    },
    onError: (_error, _newData, context) => {
      // Rollback on error
      queryClient.setQueryData(queryKey, context?.previousData);
    },
    onSuccess: () => {
      if (successMessage) {
        toast.success("Success", {
          description: successMessage,
        });
      }
    },
    ...options,
  });
}
