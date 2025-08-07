import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { RetentionDisclaimer } from "@/components/ui/retention-disclaimer";
import { ArrowRight, Folder, FileText, FormInput } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { getPromptManagementCategoriesQuery, getPromptManagementSubcategoriesQuery } from "@/queries/prompt-management.query";
import { fetchSubcategories } from "@/api/prompt-management";
import type { CategoryResponse, SubcategoryResponse } from "@/api/prompt-management";
import { toast } from "sonner";
import MDEditor from "@uiw/react-md-editor";

interface CategorySelectionProps {
  onSelectionComplete: (categoryId: string, subcategoryId: string, preSessionData: Record<string, any>) => void;
}

interface FormField {
  name: string;
  type: string;
  label: string;
  placeholder?: string;
  description?: string;
  required?: boolean;
  options?: string;
  value?: any;
}

interface FormSection {
  fields: FormField[];
}

export function CategorySelection({ onSelectionComplete }: CategorySelectionProps) {
  const [selectedCategory, setSelectedCategory] = useState<CategoryResponse | null>(null);
  const [selectedSubcategory, setSelectedSubcategory] = useState<SubcategoryResponse | null>(null);
  const [preSessionFormData, setPreSessionFormData] = useState<Record<string, any>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { data: categories, isLoading: isCategoriesLoading } = useQuery(
    getPromptManagementCategoriesQuery()
  );

  const { data: subcategories, isLoading: isSubcategoriesLoading } = useQuery(
    getPromptManagementSubcategoriesQuery()
  );

  // Fetch detailed subcategory info for pre-session form
  const { data: subcategoryDetails } = useQuery({
    queryKey: ['subcategories-detailed'],
    queryFn: () => fetchSubcategories(),
    staleTime: 5 * 60 * 1000,
    enabled: !!selectedSubcategory
  });

  // Filter subcategories for the selected category
  const availableSubcategories = subcategories?.filter(
    (sub) => sub.category_id === selectedCategory?.id
  ) || [];

  // Get current subcategory details for pre-session form
  const currentSubcategoryDetails = subcategoryDetails?.find(sub => sub.id === selectedSubcategory?.id);
  const preSessionSections = currentSubcategoryDetails?.preSessionTalkingPoints || [];

  // Check if there are any form fields to display
  const hasFormFields = preSessionSections.length > 0 && 
    preSessionSections.some((section: FormSection) => section.fields && section.fields.length > 0);

  const handleInputChange = (fieldName: string, value: any) => {
    setPreSessionFormData(prev => ({
      ...prev,
      [fieldName]: value
    }));
  };

  const validateForm = () => {
    if (!hasFormFields) return true;
    
    const requiredFields: string[] = [];
    
    preSessionSections.forEach((section: FormSection) => {
      section.fields?.forEach((field: FormField) => {
        if (field.required && (!preSessionFormData[field.name] || preSessionFormData[field.name] === '')) {
          requiredFields.push(field.label || field.name);
        }
      });
    });

    if (requiredFields.length > 0) {
      toast.error(`Please fill in required fields: ${requiredFields.join(', ')}`);
      return false;
    }

    return true;
  };

  const handleContinue = async () => {
    if (selectedCategory && selectedSubcategory) {
      if (!validateForm()) return;

      setIsSubmitting(true);
      try {
        // Add a small delay for better UX
        await new Promise(resolve => setTimeout(resolve, 300));
        
        if (hasFormFields) {
          toast.success("Pre-session form completed successfully!");
        }
        onSelectionComplete(selectedCategory.id, selectedSubcategory.id, preSessionFormData);
      } catch (error) {
        toast.error("Failed to process form data");
      } finally {
        setIsSubmitting(false);
      }
    }
  };

  const renderField = (field: FormField, sectionIndex: number, fieldIndex: number) => {
    const fieldKey = field.name || `section_${sectionIndex}_field_${fieldIndex}`;
    const fieldValue = preSessionFormData[fieldKey] ?? field.value ?? '';
    // Defensive: always use string fallback for all string fields
    const label = field.label ?? field.name ?? '';
    const placeholder = field.placeholder ?? '';
    const description = field.description ?? '';
    const required = !!field.required;
    // Defensive: always use string for options
    const optionsStr = field.options ?? '';
    const options = optionsStr ? optionsStr.split(',').map(opt => opt.trim()).filter(Boolean) : [];

    switch (field.type) {
      case 'text':
        return (
          <div key={fieldKey} className="space-y-2">
            <Label htmlFor={fieldKey} className="flex items-center gap-2">
              {label}
              {required && <span className="text-red-500">*</span>}
            </Label>
            {description && (
              <p className="text-sm text-muted-foreground">{description}</p>
            )}
            <Input
              id={fieldKey}
              value={fieldValue}
              onChange={(e) => handleInputChange(fieldKey, e.target.value)}
              placeholder={placeholder}
              required={required}
            />
          </div>
        );

      case 'date':
        return (
          <div key={fieldKey} className="space-y-2">
            <Label htmlFor={fieldKey} className="flex items-center gap-2">
              {label}
              {required && <span className="text-red-500">*</span>}
            </Label>
            {description && (
              <p className="text-sm text-muted-foreground">{description}</p>
            )}
            <Input
              id={fieldKey}
              type="date"
              value={fieldValue}
              onChange={(e) => handleInputChange(fieldKey, e.target.value)}
              required={required}
            />
          </div>
        );

      case 'number':
        return (
          <div key={fieldKey} className="space-y-2">
            <Label htmlFor={fieldKey} className="flex items-center gap-2">
              {label}
              {required && <span className="text-red-500">*</span>}
            </Label>
            {description && (
              <p className="text-sm text-muted-foreground">{description}</p>
            )}
            <Input
              id={fieldKey}
              type="number"
              value={fieldValue}
              onChange={(e) => handleInputChange(fieldKey, parseFloat(e.target.value) || 0)}
              placeholder={placeholder}
              required={required}
            />
          </div>
        );

      case 'markdown':
        return (
          <div key={fieldKey} className="space-y-2">
            <Label htmlFor={fieldKey} className="flex items-center gap-2">
              {label}
              {required && <span className="text-red-500">*</span>}
            </Label>
            {description && (
              <p className="text-sm text-muted-foreground">{description}</p>
            )}
            <div className="border rounded-md">
              <MDEditor
                value={fieldValue}
                onChange={(val) => handleInputChange(fieldKey, val || '')}
                data-color-mode="light"
                height={120}
                preview="edit"
                hideToolbar={false}
                visibleDragbar={false}
              />
            </div>
          </div>
        );

      case 'checkbox':
        return (
          <div key={fieldKey} className="space-y-2">
            <div className="flex items-center space-x-2">
              <Checkbox
                id={fieldKey}
                checked={!!fieldValue}
                onCheckedChange={(checked) => handleInputChange(fieldKey, checked)}
              />
              <Label htmlFor={fieldKey} className="flex items-center gap-2">
                {label}
                {required && <span className="text-red-500">*</span>}
              </Label>
            </div>
            {description && (
              <p className="text-sm text-muted-foreground ml-6">{description}</p>
            )}
          </div>
        );

      case 'select':
        return (
          <div key={fieldKey} className="space-y-2">
            <Label htmlFor={fieldKey} className="flex items-center gap-2">
              {label}
              {required && <span className="text-red-500">*</span>}
            </Label>
            {description && (
              <p className="text-sm text-muted-foreground">{description}</p>
            )}
            <Select value={fieldValue} onValueChange={(value) => handleInputChange(fieldKey, value)}>
              <SelectTrigger>
                <SelectValue placeholder={placeholder || "Select an option"} />
              </SelectTrigger>
              <SelectContent>
                {options.map((option, idx) => (
                  <SelectItem key={idx} value={option}>
                    {option}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        );

      default:
        return (
          <div key={fieldKey} className="space-y-2">
            <Label htmlFor={fieldKey} className="flex items-center gap-2">
              {label}
              {required && <span className="text-red-500">*</span>}
            </Label>
            {description && (
              <p className="text-sm text-muted-foreground">{description}</p>
            )}
            <Textarea
              id={fieldKey}
              value={fieldValue}
              onChange={(e) => handleInputChange(fieldKey, e.target.value)}
              placeholder={placeholder}
              required={required}
              rows={3}
            />
          </div>
        );
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

        {/* Retention Policy Disclaimer */}
        <RetentionDisclaimer className="mb-8" />

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
                Pre-Session
              </span>
            </div>
            <ArrowRight className="w-4 h-4 text-muted-foreground" />
            <div className="flex items-center">
              <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium bg-muted text-muted-foreground">
                4
              </div>
              <span className="ml-2 text-sm text-muted-foreground">
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
                <h2 className="text-xl font-semibold">Ready for Pre-Session</h2>
                <p className="text-sm text-muted-foreground">Review your selection and complete the pre-session form</p>
              </div>
            </div>

            {/* Selection Summary */}
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

            {/* Pre-Session Form */}
            {hasFormFields ? (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <FormInput className="h-5 w-5" />
                    Pre-Session Information
                  </CardTitle>
                  <p className="text-sm text-muted-foreground">
                    Please fill out the following information before we begin the recording session.
                  </p>
                </CardHeader>
                <CardContent className="space-y-6">
                  {preSessionSections.map((section: FormSection, sectionIndex: number) => (
                    <div key={sectionIndex} className="space-y-4">
                      {section.fields?.length > 0 && (
                        <div className="space-y-4">
                          {section.fields.map((field: FormField, fieldIndex: number) => 
                            renderField(field, sectionIndex, fieldIndex)
                          )}
                        </div>
                      )}
                      {sectionIndex < preSessionSections.length - 1 && (
                        <div className="border-b border-border my-6" />
                      )}
                    </div>
                  ))}
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardContent className="pt-6">
                  <div className="text-center text-muted-foreground">
                    <FormInput className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">No pre-session form required for this meeting type.</p>
                  </div>
                </CardContent>
              </Card>
            )}

            <Button 
              onClick={handleContinue} 
              disabled={isSubmitting}
              className="w-full h-14 text-lg font-medium"
              size="lg"
            >
              {isSubmitting ? "Processing..." : "Continue to Recording"}
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
