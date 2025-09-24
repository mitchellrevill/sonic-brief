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
  const [isTransitioning, setIsTransitioning] = useState(false);

  const { data: categories } = useQuery(getPromptManagementCategoriesQuery());
  const { data: subcategories } = useQuery(getPromptManagementSubcategoriesQuery());

  // Get category and subcategory names for display
  const selectedCategory = categories?.find(cat => cat.id === selectedCategoryId);
  const selectedSubcategory = subcategories?.find(sub => sub.id === selectedSubcategoryId);

  const handleSelectionComplete = (categoryId: string, subcategoryId: string, formData: Record<string, any>) => {
    setIsTransitioning(true);
    
    setTimeout(() => {
      setSelectedCategoryId(categoryId);
      setSelectedSubcategoryId(subcategoryId);
      setPreSessionData(formData);
      setCurrentStep("recording");
      setIsTransitioning(false);
    }, 150);
  };

  const handleBackToSelection = () => {
    setIsTransitioning(true);
    
    setTimeout(() => {
      setCurrentStep("category-selection");
      setPreSessionData({});
      setIsTransitioning(false);
    }, 150);
  };

  const handleUploadComplete = () => {
    setIsTransitioning(true);
    
    setTimeout(() => {
      // Reset the flow to start over
      setSelectedCategoryId("");
      setSelectedSubcategoryId("");
      setPreSessionData({});
      setCurrentStep("category-selection");
      setIsTransitioning(false);
    }, 150);
  };

  const renderCurrentStep = () => {
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

    // Fallback
    return <CategorySelection onSelectionComplete={handleSelectionComplete} />;
  };

  return (
    <div className="relative">
      <div 
        className={`transition-all duration-300 ease-in-out ${
          isTransitioning 
            ? 'opacity-0 transform scale-95' 
            : 'opacity-100 transform scale-100'
        }`}
      >
        {renderCurrentStep()}
      </div>
      
      {/* Transition overlay */}
      {isTransitioning && (
        <div className="absolute inset-0 bg-white/50 backdrop-blur-sm flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-600"></div>
        </div>
      )}
    </div>
  );
}
