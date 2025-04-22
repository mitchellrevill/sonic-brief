import type { SubcategoryResponse } from "@/api/prompt-management";
import { deleteSubcategory } from "@/api/prompt-management";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useOptimisticMutation } from "@/hooks/use-optimistic-mutation";
import { getPromptManagementSubcategoriesQuery } from "@/queries/prompt-management.query";
import { AlertTriangle } from "lucide-react";

interface DeleteSubcategoryDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  subcategory: SubcategoryResponse | null;
}

export function DeleteSubcategoryDialog({
  isOpen,
  onOpenChange,
  subcategory,
}: DeleteSubcategoryDialogProps) {
  const { mutate: removeSubcategoryMutation, isPending } =
    useOptimisticMutation({
      mutationFn: deleteSubcategory,
      queryKey: getPromptManagementSubcategoriesQuery().queryKey,
      updateFn: (old = [], subcategoryId) =>
        old.filter((sub) => sub.id !== subcategoryId),
      successMessage: "Subcategory deleted successfully",
      onMutateSideEffect: () => {
        onOpenChange(false);
      },
    });

  // Don't render if no subcategory is selected
  if (!subcategory) {
    return null;
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="text-destructive h-5 w-5" />
            Delete Subcategory
          </DialogTitle>
          <DialogDescription>
            Are you sure you want to delete the subcategory "{subcategory.name}
            "? This will also delete all prompts associated with this
            subcategory. This action cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isPending}
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={() => removeSubcategoryMutation(subcategory.id)}
            disabled={isPending}
          >
            {isPending ? "Deleting..." : "Delete Subcategory"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
