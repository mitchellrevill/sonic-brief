import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, FormInput, CheckCircle2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchSubcategories, type SubcategoryResponse } from "@/api/prompt-management";
import { toast } from "sonner";
import MDEditor from "@uiw/react-md-editor";

interface PreSessionFormProps {
  categoryId: string;
  subcategoryId: string;
  categoryName: string;
  subcategoryName: string;
  onFormComplete: (formData: Record<string, any>) => void;
  onBack: () => void;
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

export function PreSessionForm({ 
  subcategoryId, 
  categoryName, 
  subcategoryName, 
  onFormComplete, 
  onBack 
}: PreSessionFormProps) {
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Fetch subcategory details to get pre-session form fields
  const { data: subcategories, isLoading } = useQuery({
    queryKey: ['subcategories'],
    queryFn: () => fetchSubcategories(),
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });

  const currentSubcategory = (subcategories as SubcategoryResponse[])?.find(sub => sub.id === subcategoryId);
  const preSessionSections = currentSubcategory?.preSessionTalkingPoints || [];

  // Check if there are any form fields to display
  const hasFormFields = preSessionSections.length > 0 && 
    preSessionSections.some((section: FormSection) => section.fields && section.fields.length > 0);

  const handleInputChange = (fieldName: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      [fieldName]: value
    }));
  };

  const validateForm = () => {
    const requiredFields: string[] = [];
    
    preSessionSections.forEach((section: FormSection) => {
      section.fields?.forEach((field: FormField) => {
        if (field.required && (!formData[field.name] || formData[field.name] === '')) {
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

  const handleSubmit = async () => {
    if (!validateForm()) return;

    setIsSubmitting(true);
    try {
      // Add a small delay for better UX
      await new Promise(resolve => setTimeout(resolve, 500));
      
      toast.success("Pre-session form completed successfully!");
      onFormComplete(formData);
    } catch (error) {
      toast.error("Failed to process form data");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSkip = () => {
    toast.info("Skipping pre-session form");
    onFormComplete({});
  };

  const renderField = (field: FormField, sectionIndex: number, fieldIndex: number) => {
    const fieldKey = field.name || `section_${sectionIndex}_field_${fieldIndex}`;
    const fieldValue = formData[fieldKey] ?? field.value ?? '';
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

  if (isLoading) {
    return (
      <div className="container mx-auto p-6">
        <Card>
          <CardContent className="flex items-center justify-center py-12">
            <div className="text-center space-y-2">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
              <p className="text-muted-foreground">Loading form configuration...</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={onBack}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold">Pre-Session Form</h1>
          <div className="flex items-center gap-2 text-muted-foreground">
            <Badge variant="secondary">{categoryName}</Badge>
            <span>→</span>
            <Badge variant="secondary">{subcategoryName}</Badge>
          </div>
        </div>
      </div>

      {/* Form Content */}
      {!hasFormFields ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-green-500" />
              No Pre-Session Form Required
            </CardTitle>
            <CardDescription>
              This category doesn't have any pre-session form fields configured. You can proceed directly to recording.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-3">
              <Button onClick={handleSkip} className="flex-1">
                Continue to Recording
              </Button>
              <Button variant="outline" onClick={onBack}>
                Back to Selection
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FormInput className="h-5 w-5" />
              Pre-Session Information
            </CardTitle>
            <CardDescription>
              Please fill out the following information before we begin the recording session.
            </CardDescription>
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

            <div className="flex gap-3 pt-4">
              <Button 
                onClick={handleSubmit} 
                disabled={isSubmitting}
                className="flex-1"
              >
                {isSubmitting ? "Processing..." : "Complete Form & Start Recording"}
              </Button>
              <Button variant="outline" onClick={onBack}>
                Back
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
