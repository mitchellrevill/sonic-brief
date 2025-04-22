import type { CategoryResponse } from "@/api/prompt-management";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

import { SubcategoryForm } from "./subcategory-form";

interface AddSubcategoryDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  categories: Array<CategoryResponse>;
  selectedCategoryId: string | null;
}

export function AddSubcategoryDialog({
  isOpen,
  onOpenChange,
  categories,
  selectedCategoryId,
}: AddSubcategoryDialogProps) {
  // Ensure selectedCategoryId is not null before rendering the form
  if (!isOpen || selectedCategoryId === null) {
    return null;
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-4xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add New Subcategory</DialogTitle>
        </DialogHeader>
        {/* Render the form only when the dialog is open and a category is selected */}
        <SubcategoryForm
          key={`add-subcategory-form-${selectedCategoryId}`} // Use selectedCategoryId in key
          categories={categories}
          selectedCategoryId={selectedCategoryId}
          closeDialog={() => onOpenChange(false)}
        />
      </DialogContent>
    </Dialog>
  );
}
