import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ArrowRight, Folder, FileText } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { getPromptManagementCategoriesQuery, getPromptManagementSubcategoriesQuery } from "@/queries/prompt-management.query";
import type { CategoryResponse, SubcategoryResponse } from "@/api/prompt-management";

interface CategorySelectionProps {
  onSelectionComplete: (categoryId: string, subcategoryId: string) => void;
}

export function CategorySelection({ onSelectionComplete }: CategorySelectionProps) {
  const [selectedCategory, setSelectedCategory] = useState<CategoryResponse | null>(null);
  const [selectedSubcategory, setSelectedSubcategory] = useState<SubcategoryResponse | null>(null);

  const { data: categories, isLoading: isCategoriesLoading } = useQuery(
    getPromptManagementCategoriesQuery()
  );

  const { data: subcategories, isLoading: isSubcategoriesLoading } = useQuery(
    getPromptManagementSubcategoriesQuery()
  );

  // Filter subcategories for the selected category
  const availableSubcategories = subcategories?.filter(
    (sub) => sub.category_id === selectedCategory?.id
  ) || [];

  const handleContinue = () => {
    if (selectedCategory && selectedSubcategory) {
      onSelectionComplete(selectedCategory.id, selectedSubcategory.id);
    }
  };

  if (isCategoriesLoading || isSubcategoriesLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
              <p className="text-muted-foreground">Loading service areas...</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background p-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-foreground mb-2">Select Service Area</h1>
          <p className="text-muted-foreground text-lg">Choose the type of meeting you're recording</p>
        </div>

        {/* Progress indicator */}
        <div className="flex items-center justify-center mb-8">
          <div className="flex items-center space-x-2">
            <div className="flex items-center">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                !selectedCategory ? 'bg-primary text-primary-foreground' : 'bg-primary text-primary-foreground'
              }`}>
                1
              </div>
              <span className={`ml-2 text-sm ${!selectedCategory ? 'text-foreground' : 'text-muted-foreground'}`}>
                Service Area
              </span>
            </div>
            <ArrowRight className="w-4 h-4 text-muted-foreground" />
            <div className="flex items-center">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                selectedCategory && !selectedSubcategory ? 'bg-primary text-primary-foreground' : 
                selectedSubcategory ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'
              }`}>
                2
              </div>
              <span className={`ml-2 text-sm ${
                selectedCategory ? 'text-foreground' : 'text-muted-foreground'
              }`}>
                Meeting Type
              </span>
            </div>
            <ArrowRight className="w-4 h-4 text-muted-foreground" />
            <div className="flex items-center">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                selectedSubcategory ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'
              }`}>
                3
              </div>
              <span className={`ml-2 text-sm ${
                selectedSubcategory ? 'text-foreground' : 'text-muted-foreground'
              }`}>
                Record
              </span>
            </div>
          </div>
        </div>

        {/* Category Selection */}
        {!selectedCategory && (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold text-center mb-6">Choose Service Area</h2>
            <div className="grid gap-4">
              {categories?.map((category) => (
                <Card 
                  key={category.id} 
                  className="cursor-pointer transition-all hover:shadow-md hover:scale-[1.02] border-2 hover:border-primary/50"
                  onClick={() => setSelectedCategory(category)}
                >
                  <CardContent className="p-6">
                    <div className="flex items-center space-x-4">
                      <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center">
                        <Folder className="w-6 h-6 text-primary" />
                      </div>
                      <div className="flex-1">
                        <h3 className="text-lg font-medium text-foreground">{category.name}</h3>
                        <p className="text-sm text-muted-foreground">
                          {subcategories?.filter(sub => sub.category_id === category.id).length || 0} meeting types available
                        </p>
                      </div>
                      <ArrowRight className="w-5 h-5 text-muted-foreground" />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* Subcategory Selection */}
        {selectedCategory && !selectedSubcategory && (
          <div className="space-y-4">
            <div className="flex items-center space-x-4 mb-6">
              <Button 
                variant="ghost" 
                onClick={() => setSelectedCategory(null)}
                className="text-muted-foreground hover:text-foreground"
              >
                ← Back
              </Button>
              <div>
                <h2 className="text-xl font-semibold">Choose Meeting Type</h2>
                <p className="text-sm text-muted-foreground">Service Area: {selectedCategory.name}</p>
              </div>
            </div>
            
            <div className="grid gap-4">
              {availableSubcategories.map((subcategory) => (
                <Card 
                  key={subcategory.id} 
                  className="cursor-pointer transition-all hover:shadow-md hover:scale-[1.02] border-2 hover:border-primary/50"
                  onClick={() => setSelectedSubcategory(subcategory)}
                >
                  <CardContent className="p-6">
                    <div className="flex items-center space-x-4">
                      <div className="w-12 h-12 bg-secondary/50 rounded-lg flex items-center justify-center">
                        <FileText className="w-6 h-6 text-secondary-foreground" />
                      </div>
                      <div className="flex-1">
                        <h3 className="text-lg font-medium text-foreground">{subcategory.name}</h3>
                        <div className="flex items-center space-x-2 mt-1">
                          <Badge variant="secondary" className="text-xs">
                            {Object.keys(subcategory.prompts).length} analysis prompts
                          </Badge>
                        </div>
                      </div>
                      <ArrowRight className="w-5 h-5 text-muted-foreground" />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* Final confirmation */}
        {selectedCategory && selectedSubcategory && (
          <div className="space-y-6">
            <div className="flex items-center space-x-4 mb-6">
              <Button 
                variant="ghost" 
                onClick={() => setSelectedSubcategory(null)}
                className="text-muted-foreground hover:text-foreground"
              >
                ← Back
              </Button>
              <div>
                <h2 className="text-xl font-semibold">Ready to Record</h2>
                <p className="text-sm text-muted-foreground">Review your selection</p>
              </div>
            </div>

            <Card className="border-2 border-primary/20">
              <CardHeader>
                <CardTitle className="text-lg">Your Selection</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Service Area:</span>
                  <Badge variant="outline">{selectedCategory.name}</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Meeting Type:</span>
                  <Badge variant="outline">{selectedSubcategory.name}</Badge>
                </div>
              </CardContent>
            </Card>

            <Button 
              onClick={handleContinue} 
              className="w-full h-14 text-lg font-medium"
              size="lg"
            >
              Confirm 
              <ArrowRight className="w-5 h-5 ml-2" />
            </Button>
          </div>
        )}

        {/* No categories available */}
        {categories && categories.length === 0 && (
          <Card>
            <CardContent className="pt-6">
              <div className="text-center">
                <Folder className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-medium text-foreground mb-2">No Service Areas Available</h3>
                <p className="text-muted-foreground">
                  Please contact your administrator to set up service areas and meeting types.
                </p>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
