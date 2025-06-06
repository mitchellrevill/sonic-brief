import { useState } from "react";
import { CategorySelection } from "@/components/simple-ui/CategorySelection";
import { RecordingInterface } from "@/components/simple-ui/RecordingInterface";
import { useQuery } from "@tanstack/react-query";
import { getPromptManagementCategoriesQuery, getPromptManagementSubcategoriesQuery } from "@/queries/prompt-management.query";

type UIStep = "category-selection" | "recording";

export function SimpleUploadFlow() {
  const [currentStep, setCurrentStep] = useState<UIStep>("category-selection");
  const [selectedCategoryId, setSelectedCategoryId] = useState<string>("");
  const [selectedSubcategoryId, setSelectedSubcategoryId] = useState<string>("");

  const { data: categories } = useQuery(getPromptManagementCategoriesQuery());
  const { data: subcategories } = useQuery(getPromptManagementSubcategoriesQuery());

  // Get category and subcategory names for display
  const selectedCategory = categories?.find(cat => cat.id === selectedCategoryId);
  const selectedSubcategory = subcategories?.find(sub => sub.id === selectedSubcategoryId);

  const handleSelectionComplete = (categoryId: string, subcategoryId: string) => {
    setSelectedCategoryId(categoryId);
    setSelectedSubcategoryId(subcategoryId);
    setCurrentStep("recording");
  };

  const handleBackToSelection = () => {
    setCurrentStep("category-selection");
  };

  const handleUploadComplete = () => {
    // Reset the flow to start over
    setSelectedCategoryId("");
    setSelectedSubcategoryId("");
    setCurrentStep("category-selection");
  };

  if (currentStep === "category-selection") {
    return <CategorySelection onSelectionComplete={handleSelectionComplete} />;
  }

  if (currentStep === "recording" && selectedCategory && selectedSubcategory) {
    return (
      <RecordingInterface
        categoryId={selectedCategoryId}
        subcategoryId={selectedSubcategoryId}
        categoryName={selectedCategory.name}
        subcategoryName={selectedSubcategory.name}
        onBack={handleBackToSelection}
        onUploadComplete={handleUploadComplete}
      />
    );
  }

  // Fallback - should not reach here in normal flow
  return <CategorySelection onSelectionComplete={handleSelectionComplete} />;
}
