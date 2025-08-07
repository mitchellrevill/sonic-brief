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
  const [preSessionData, setPreSessionData] = useState<Record<string, any>>({});

  const { data: categories } = useQuery(getPromptManagementCategoriesQuery());
  const { data: subcategories } = useQuery(getPromptManagementSubcategoriesQuery());

  // Get category and subcategory names for display
  const selectedCategory = categories?.find(cat => cat.id === selectedCategoryId);
  const selectedSubcategory = subcategories?.find(sub => sub.id === selectedSubcategoryId);

  const handleSelectionComplete = (categoryId: string, subcategoryId: string, formData: Record<string, any>) => {
    setSelectedCategoryId(categoryId);
    setSelectedSubcategoryId(subcategoryId);
    setPreSessionData(formData);
    setCurrentStep("recording");
  };

  const handleBackToSelection = () => {
    setCurrentStep("category-selection");
    setPreSessionData({});
  };

  const handleUploadComplete = () => {
    // Reset the flow to start over
    setSelectedCategoryId("");
    setSelectedSubcategoryId("");
    setPreSessionData({});
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
        preSessionData={preSessionData}
        onBack={handleBackToSelection}
        onUploadComplete={handleUploadComplete}
      />
    );
  }

  // Fallback - should not reach here in normal flow
  return <CategorySelection onSelectionComplete={handleSelectionComplete} />;
}
