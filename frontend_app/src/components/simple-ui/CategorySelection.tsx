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
import { ArrowRight, ArrowLeft, Folder, FormInput, FileText, CheckCircle} from "lucide-react";
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
  const [expandedParentCategoryId, setExpandedParentCategoryId] = useState<string>("");
  const [preSessionFormData, setPreSessionFormData] = useState<Record<string, any>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { data: categories, isLoading: isCategoriesLoading } = useQuery(
    getPromptManagementCategoriesQuery()
  );

  const { data: subcategories, isLoading: isSubcategoriesLoading } = useQuery(
    getPromptManagementSubcategoriesQuery()
  );

  // Filter subcategories for the selected category
  const availableSubcategories = (subcategories?.filter(
    (sub) => sub.category_id === selectedCategory?.id
  ) || []).sort((a, b) => a.name.localeCompare(b.name));

  // Fetch detailed subcategory info for pre-session form
  const { data: subcategoryDetails } = useQuery({
    queryKey: ['subcategories-detailed'],
    queryFn: () => fetchSubcategories(),
    staleTime: 5 * 60 * 1000,
    enabled: availableSubcategories.length > 0
  });

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
    const label = field.label ?? field.name ?? '';
    const placeholder = field.placeholder ?? '';
    const description = field.description ?? '';
    const required = !!field.required;
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
              <p className="text-sm text-black">{description}</p>
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
              <p className="text-sm text-black">{description}</p>
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
              <p className="text-sm text-black">{description}</p>
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
              <p className="text-sm text-black">{description}</p>
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
              <p className="text-sm text-black ml-6">{description}</p>
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
              <p className="text-sm text-black">{description}</p>
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
              <p className="text-sm text-black">{description}</p>
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
        <Card className="w-full max-w-md border-0 shadow-xl">
          <CardContent className="pt-8 pb-8">
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-slate-100 dark:bg-slate-900/30 flex items-center justify-center mx-auto mb-6">
                <div className="w-8 h-8 border-3 border-slate-500 border-t-transparent rounded-full animate-spin"></div>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                Loading Service Areas
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                Please wait while we prepare your recording options...
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        {/* Header */}
        <div className="text-center mb-8 sm:mb-10">
            <h1 className="text-3xl sm:text-4xl font-bold bg-gradient-to-r from-gray-700 to-gray-900 dark:from-gray-100 dark:to-gray-400 bg-clip-text text-transparent mb-3 sm:mb-4">
            Create New Recording
            </h1>
          <p className="text-base sm:text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto px-2">
            Choose your service area and meeting type to get started with your recording session
          </p>
        </div>

        {/* Retention Policy Disclaimer */}
        <div className="mb-8 sm:mb-10">
          <RetentionDisclaimer className="max-w-3xl mx-auto" />
        </div>

        {/* Enhanced Progress Steps */}
        <div className="mb-12">
          <div className="max-w-3xl mx-auto">
            <div className="flex items-center justify-between relative">
              {/* Progress Line */}
              <div className="absolute top-4 left-0 right-0 h-0.5 bg-gray-200 dark:bg-gray-700"></div>
              <div 
                className="absolute top-4 left-0 h-0.5 bg-gradient-to-r from-gray-500 to-gray-600 transition-all duration-500" 
                style={{ 
                  width: selectedSubcategory ? '100%' : selectedCategory ? '66%' : '33%'
                }}
              ></div>

              {/* Step 1: Service Area */}
              <div className="relative flex flex-col items-center">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-all duration-300 z-10 ${
                  selectedCategory 
                    ? 'bg-gray-500 text-white shadow-lg' 
                    : 'bg-white dark:bg-gray-800 border-2 border-gray-500 text-gray-500'
                }`}>
                  {selectedCategory ? <CheckCircle className="w-4 h-4" /> : '1'}
                </div>
                <span className="mt-2 text-sm font-medium text-gray-700 dark:text-gray-300">
                  Service Area
                </span>
              </div>

              {/* Step 2: Meeting Type */}
              <div className="relative flex flex-col items-center">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-all duration-300 z-10 ${
                  selectedSubcategory 
                    ? 'bg-gray-500 text-white shadow-lg' 
                    : selectedCategory 
                      ? 'bg-white dark:bg-gray-800 border-2 border-gray-500 text-gray-500'
                      : 'bg-gray-200 dark:bg-gray-700 text-gray-500'
                }`}>
                  {selectedSubcategory ? <CheckCircle className="w-4 h-4" /> : '2'}
                </div>
                <span className={`mt-2 text-sm font-medium transition-colors ${
                  selectedCategory ? 'text-gray-700 dark:text-gray-300' : 'text-gray-400'
                }`}>
                  Meeting Type
                </span>
              </div>

              {/* Step 3: Pre-Session */}
              <div className="relative flex flex-col items-center">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-all duration-300 z-10 ${
                  selectedSubcategory 
                    ? 'bg-white dark:bg-gray-800 border-2 border-gray-500 text-gray-500'
                    : 'bg-gray-200 dark:bg-gray-700 text-gray-500'
                }`}>
                  3
                </div>
                <span className={`mt-2 text-sm font-medium transition-colors ${
                  selectedSubcategory ? 'text-gray-700 dark:text-gray-300' : 'text-gray-400'
                }`}>
                  Pre-Session
                </span>
              </div>

              {/* Step 4: Record */}
              <div className="relative flex flex-col items-center">
                <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold bg-gray-200 dark:bg-gray-700 text-gray-500 z-10">
                  4
                </div>
                <span className="mt-2 text-sm font-medium text-gray-400">
                  Record
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Category Selection - Step 1 */}
        {!selectedCategory && (
          <div className="space-y-8 animate-in fade-in-0 slide-in-from-bottom-4 duration-500">
            <div className="text-center">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                Choose Your Service Area
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                Select the department or area where your meeting will take place
              </p>
            </div>
            
            {(() => {
              const rootCategories = (categories || [])
                .filter(cat => !(cat as any).parent_category_id)
                .sort((a, b) => a.name.localeCompare(b.name));
              const childrenByParent: Record<string, Array<any>> = {};
              (categories || []).forEach(cat => {
                const parent = (cat as any).parent_category_id;
                if (parent) {
                  childrenByParent[parent] = childrenByParent[parent] || [];
                  childrenByParent[parent].push(cat);
                }
              });

              const toggleExpand = (parentId: string) => setExpandedParentCategoryId(cur => cur === parentId ? "" : parentId);
              
              return (
                <div className="grid gap-6 md:grid-cols-2" role="radiogroup" aria-label="Service Areas">
                  {rootCategories.map((category: CategoryResponse, index: number) => {
                    const hasChildren = childrenByParent[category.id]?.length > 0;
                    const expanded = expandedParentCategoryId === category.id;
                    const isSelected = !!(selectedCategory && (selectedCategory as any).id === category.id);
                    const subcategoryCount = subcategories?.filter(sub => sub.category_id === category.id).length || 0;
                    
                    return (
                      <Card 
                        key={category.id} 
                        className={`group cursor-pointer transition-all duration-300 hover:shadow-lg hover:-translate-y-1 border-2 overflow-hidden animate-in fade-in-0 slide-in-from-bottom-4 ${
                          isSelected 
                            ? 'border-slate-500 bg-slate-50/50 dark:bg-slate-900/20 shadow-lg' 
                            : 'border-gray-200 dark:border-gray-700 hover:border-slate-300'
                        }`}
                        style={{ animationDelay: `${index * 100}ms` }}
                        onClick={() => setSelectedCategory(category)}
                        role="radio" 
                        aria-checked={isSelected}
                      >
                        <CardContent className="p-6">
                          <div className="flex items-start space-x-4">
                            <div className={`flex-shrink-0 w-14 h-14 rounded-xl flex items-center justify-center transition-colors ${
                              isSelected 
                                ? 'bg-gray-500 text-white' 
                                : 'bg-gray-100 dark:bg-gray-900/30 text-gray-600 dark:text-gray-400 group-hover:bg-gray-200'
                            }`}>
                              <Folder className="w-7 h-7" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2 group-hover:text-gray-600 dark:group-hover:text-gray-400 transition-colors">
                                {category.name}
                              </h3>
                              <div className="flex items-center space-x-4 text-sm text-gray-600 dark:text-gray-400">
                                <span className="flex items-center">
                                  <FileText className="w-4 h-4 mr-1" />
                                  {subcategoryCount} meeting types
                                </span>
                                {hasChildren && (
                                  <span className="flex items-center">
                                    <Folder className="w-4 h-4 mr-1" />
                                    {childrenByParent[category.id].length} subcategories
                                  </span>
                                )}
                              </div>
                              
                              {hasChildren && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={(e) => { 
                                    e.stopPropagation(); 
                                    toggleExpand(category.id); 
                                  }}
                                  className="mt-3 h-8 px-3 text-xs hover:bg-gray-100 dark:hover:bg-gray-900/30"
                                >
                                  {expanded ? 'Hide' : 'Show'} subcategories
                                </Button>
                              )}
                            </div>
                            
                            <div className="flex-shrink-0">
                              <ArrowRight className={`w-5 h-5 transition-all duration-300 ${
                                isSelected 
                                  ? 'text-gray-500 translate-x-1' 
                                  : 'text-gray-400 group-hover:text-gray-500 group-hover:translate-x-1'
                              }`} />
                            </div>
                          </div>
                          
                          {/* Expanded subcategories */}
                          {hasChildren && expanded && (
                            <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700 animate-in fade-in-0 slide-in-from-top-4 duration-300">
                              <div className="grid gap-3 sm:grid-cols-2">
                                {childrenByParent[category.id].map(child => {
                                  const childSelected = !!(selectedCategory && (selectedCategory as any).id === child.id);
                                  return (
                                    <button
                                      key={child.id}
                                      type="button"
                                      role="radio"
                                      aria-checked={childSelected}
                                      onClick={(e) => { 
                                        e.stopPropagation(); 
                                        setSelectedCategory(child); 
                                      }}
                                      className={`text-left p-3 rounded-lg border transition-all duration-200 ${
                                        childSelected 
                                          ? 'border-slate-500 bg-slate-50 dark:bg-slate-900/30' 
                                          : 'border-gray-200 dark:border-gray-700 hover:border-slate-300 hover:bg-gray-50 dark:hover:bg-gray-800'
                                      }`}
                                    >
                                      <p className="font-medium text-sm text-gray-900 dark:text-white">
                                        {child.name}
                                      </p>
                                    </button>
                                  );
                                })}
                              </div>
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>
              );
            })()}
          </div>
        )}

        {/* Subcategory Selection - Step 2 */}
        {selectedCategory && !selectedSubcategory && (
          <div className="space-y-8 animate-in fade-in-0 slide-in-from-bottom-4 duration-500">
            <div className="flex items-center justify-between">
              <Button 
                variant="ghost" 
                onClick={() => setSelectedCategory(null)}
                className="text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Service Areas
              </Button>
              
              <Badge variant="secondary" className="px-3 py-1">
                {selectedCategory.name}
              </Badge>
            </div>

            <div className="text-center">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                Choose Meeting Type
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                Select the specific type of meeting you'll be recording
              </p>
            </div>

            {(() => {
              const rootCategories = (categories || []).filter(cat => !(cat as any).parent_category_id);
              const childrenByParent: Record<string, Array<any>> = {};
              (categories || []).forEach(cat => {
                const parent = (cat as any).parent_category_id;
                if (parent) {
                  childrenByParent[parent] = childrenByParent[parent] || [];
                  childrenByParent[parent].push(cat);
                }
              });

              const isRootCategory = rootCategories.find(cat => cat.id === selectedCategory.id);
              const selectedCategoryChildren = (isRootCategory ? childrenByParent[selectedCategory.id] : [])?.sort((a, b) => a.name.localeCompare(b.name)) || [];

              return (
                <div className="space-y-8">
                  {/* Show child categories if the selected category has them */}
                  {selectedCategoryChildren?.length > 0 && (
                    <div className="space-y-6">
                      <div className="text-center">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                          {selectedCategory.name} Subcategories
                        </h3>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          Choose a more specific area within {selectedCategory.name}
                        </p>
                      </div>
                      
                      <div className="grid gap-4 md:grid-cols-2" role="radiogroup" aria-label="Subcategories">
                        {selectedCategoryChildren.map((child: any, index: number) => {
                          const childSelected = !!(selectedCategory && (selectedCategory as any).id === child.id);
                          const childSubcategoryCount = subcategories?.filter(sub => sub.category_id === child.id).length || 0;
                          
                          return (
                            <Card
                              key={child.id}
                              className={`group cursor-pointer transition-all duration-300 hover:shadow-md hover:-translate-y-0.5 border-2 animate-in fade-in-0 slide-in-from-bottom-4 ${
                                childSelected
                                  ? 'border-slate-500 bg-slate-50/50 dark:bg-slate-900/20'
                                  : 'border-gray-200 dark:border-gray-700 hover:border-slate-300'
                              }`}
                              style={{ animationDelay: `${index * 100}ms` }}
                              onClick={() => setSelectedCategory(child)}
                              role="radio"
                              aria-checked={childSelected}
                            >
                              <CardContent className="p-4">
                                <div className="flex items-center space-x-3">
                                  <div className={`flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center transition-colors ${
                                    childSelected 
                                      ? 'bg-slate-500 text-white' 
                                      : 'bg-slate-100 dark:bg-slate-900/30 text-slate-600 dark:text-slate-400 group-hover:bg-slate-200'
                                  }`}>
                                    <Folder className="w-5 h-5" />
                                  </div>
                                  <div className="flex-1">
                                    <h4 className="font-medium text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                                      {child.name}
                                    </h4>
                                    <p className="text-sm text-gray-600 dark:text-gray-400">
                                      {childSubcategoryCount} meeting types
                                    </p>
                                  </div>
                                  {childSelected && (
                                    <CheckCircle className="w-5 h-5 text-blue-500" />
                                  )}
                                </div>
                              </CardContent>
                            </Card>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Show meeting types for the selected category */}
                  <div className="space-y-6">
                    <div className="text-center">
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                        Available Meeting Types
                      </h3>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        Select the type of meeting you want to record
                      </p>
                    </div>
                    
                    {availableSubcategories.length > 0 ? (
                      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3" role="radiogroup" aria-label="Meeting Types">
                        {availableSubcategories.map((subcategory: SubcategoryResponse, index: number) => {
                          const active = !!(selectedSubcategory && (selectedSubcategory as any).id === (subcategory as any).id);
                          return (
                            <Card
                              key={subcategory.id}
                              className={`group cursor-pointer transition-all duration-300 hover:shadow-md hover:-translate-y-0.5 border-2 animate-in fade-in-0 slide-in-from-bottom-4 ${
                                active
                                  ? 'border-green-500 bg-green-50/50 dark:bg-green-900/20'
                                  : 'border-gray-200 dark:border-gray-700 hover:border-green-300'
                              }`}
                              style={{ animationDelay: `${index * 100}ms` }}
                              onClick={() => setSelectedSubcategory(subcategory)}
                              role="radio"
                              aria-checked={active}
                            >
                              <CardContent className="p-4">
                                <div className="flex items-center space-x-3">
                                  <div className={`flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center transition-colors ${
                                    active 
                                      ? 'bg-green-500 text-white' 
                                      : 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 group-hover:bg-green-200'
                                  }`}>
                                    <FileText className="w-5 h-5" />
                                  </div>
                                  <div className="flex-1">
                                    <h4 className="font-medium text-gray-900 dark:text-white group-hover:text-green-600 dark:group-hover:text-green-400 transition-colors">
                                      {subcategory.name}
                                    </h4>
                                  </div>
                                  {active && (
                                    <CheckCircle className="w-5 h-5 text-green-500" />
                                  )}
                                </div>
                              </CardContent>
                            </Card>
                          );
                        })}
                      </div>
                    ) : (
                      <Card className="border-2 border-dashed border-gray-300 dark:border-gray-700">
                        <CardContent className="p-8 text-center">
                          <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                            No Meeting Types Available
                          </h3>
                          <p className="text-gray-600 dark:text-gray-400">
                            There are no meeting types configured for this service area yet.
                          </p>
                        </CardContent>
                      </Card>
                    )}
                  </div>
                </div>
              );
            })()}
          </div>
        )}

        {/* Pre-Session Form - Step 3 */}
        {selectedCategory && selectedSubcategory && (
          <div className="space-y-8 animate-in fade-in-0 slide-in-from-bottom-4 duration-500">
            <div className="flex items-center justify-between">
              <Button 
                variant="ghost" 
                onClick={() => setSelectedSubcategory(null)}
                className="text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Meeting Types
              </Button>
              
              <div className="flex items-center space-x-2">
                <Badge variant="secondary" className="px-2 py-1 text-xs">
                  {selectedCategory.name}
                </Badge>
                <span className="text-gray-400">•</span>
                <Badge variant="secondary" className="px-2 py-1 text-xs">
                  {selectedSubcategory.name}
                </Badge>
              </div>
            </div>

            <div className="text-center">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                Pre-Session Information
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                Complete any required information before starting your recording
              </p>
            </div>

            {/* Selection Summary Card */}
            <Card className="border-2 border-slate-200 bg-gradient-to-r from-slate-50 to-gray-50 dark:from-slate-900/20 dark:to-gray-900/20">
              <CardContent className="p-6">
                <div className="flex items-center space-x-4">
                  <div className="flex-shrink-0">
                    <div className="w-12 h-12 rounded-xl bg-slate-500 flex items-center justify-center">
                      <CheckCircle className="w-6 h-6 text-white" />
                    </div>
                  </div>
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
                      Ready to Record
                    </h3>
                    <div className="space-y-1">
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        <span className="font-medium">Service Area:</span> {selectedCategory.name}
                      </p>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        <span className="font-medium">Meeting Type:</span> {selectedSubcategory.name}
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Pre-Session Form */}
            {hasFormFields ? (
              <Card className="border-2 border-gray-200 dark:border-gray-700">
                <CardHeader className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
                  <CardTitle className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-orange-100 dark:bg-orange-900/30 flex items-center justify-center">
                      <FormInput className="h-4 w-4 text-orange-600 dark:text-orange-400" />
                    </div>
                    <span>Required Information</span>
                  </CardTitle>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                    Please fill out the following information to help us provide the best recording experience.
                  </p>
                </CardHeader>
                <CardContent className="p-6">
                  <div className="space-y-8">
                    {preSessionSections.map((section: FormSection, sectionIndex: number) => (
                      <div key={sectionIndex} className="space-y-6">
                        {section.fields?.length > 0 && (
                          <div className="grid gap-6 md:grid-cols-2">
                            {section.fields.map((field: FormField, fieldIndex: number) => 
                              <div key={fieldIndex} className="col-span-full md:col-span-1">
                                {renderField(field, sectionIndex, fieldIndex)}
                              </div>
                            )}
                          </div>
                        )}
                        {sectionIndex < preSessionSections.length - 1 && (
                          <div className="border-b border-gray-200 dark:border-gray-700" />
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Card className="border-2 border-dashed border-gray-300 dark:border-gray-700">
                <CardContent className="p-8 text-center">
                  <div className="w-16 h-16 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center mx-auto mb-4">
                    <CheckCircle className="w-8 h-8 text-green-600 dark:text-green-400" />
                  </div>
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                    No Additional Information Required
                  </h3>
                  <p className="text-gray-600 dark:text-gray-400">
                    You're all set! No pre-session form is required for this meeting type.
                  </p>
                </CardContent>
              </Card>
            )}

            {/* Continue Button */}
            <div className="pt-4">
              <Button 
                onClick={handleContinue} 
                disabled={isSubmitting}
                className="w-full h-14 text-lg font-semibold bg-gradient-to-r from-zinc-700 to-zinc-800 hover:from-zinc-800 hover:to-zinc-700 shadow-lg hover:shadow-xl transition-all duration-300 disabled:opacity-50 dark:from-zinc-200 dark:to-zinc-300 dark:hover:from-zinc-300 dark:hover:to-zinc-200 dark:text-zinc-800"
                size="lg"
              >
                {isSubmitting ? (
                  <div className="flex items-center space-x-2">
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    <span>Processing...</span>
                  </div>
                ) : (
                  <div className="flex items-center space-x-2">
                    <span>Start Recording</span>
                    <ArrowRight className="w-5 h-5" />
                  </div>
                )}
              </Button>
            </div>
          </div>
        )}

        {/* No categories available */}
        {categories && categories.length === 0 && (
          <Card className="border-2 border-dashed border-gray-300 dark:border-gray-700 max-w-2xl mx-auto">
            <CardContent className="p-12 text-center">
              <div className="w-20 h-20 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center mx-auto mb-6">
                <Folder className="w-10 h-10 text-gray-400" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-3">
                No Service Areas Available
              </h3>
              <p className="text-gray-600 dark:text-gray-400 max-w-md mx-auto">
                It looks like no service areas have been configured yet. Please contact your administrator to set up service areas and meeting types for recording.
              </p>
            </CardContent>
          </Card>
        )}

      </div>
    </div>
  );
}
