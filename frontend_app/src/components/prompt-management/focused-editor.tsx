import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Save } from "lucide-react";
import MDEditor from "@uiw/react-md-editor";
import "@uiw/react-md-editor/markdown-editor.css";
import { fetchPrompts, updateSubcategory, deleteSubcategory } from "@/api/prompt-management";
import { toast } from "sonner";

// Hook to detect theme
function useTheme() {
  const [isDark, setIsDark] = useState(false);
  
  useEffect(() => {
    const checkTheme = () => {
      setIsDark(document.documentElement.classList.contains('dark'));
    };
    
    checkTheme();
    
    // Watch for theme changes
    const observer = new MutationObserver(checkTheme);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class']
    });
    
    return () => observer.disconnect();
  }, []);
  
  return isDark;
}

interface FocusedEditorProps {
  selectedSubcategory?: any;
  onSave?: (data: any) => Promise<void>;
  onCancel?: () => void;
}

const PRE_SESSION_FORM_FIELD_TYPES = [
  { label: 'Short Text', value: 'text', description: 'Single-line text field' },
  { label: 'Date', value: 'date', description: 'Date selection field' },
  { label: 'Long Text (Markdown)', value: 'markdown', description: 'Multi-line text area with formatting' },
  { label: 'Checkbox', value: 'checkbox', description: 'Yes/No checkbox' },
  { label: 'Number', value: 'number', description: 'Numeric input field' },
  { label: 'Dropdown', value: 'select', description: 'Dropdown with predefined options' },
];

const IN_SESSION_TALKING_POINT_TYPES = [
  { label: 'Long Text (Markdown)', value: 'markdown', description: 'Rich text talking point (recommended)' },
  { label: 'Short Text', value: 'text', description: 'Simple text note' },
  { label: 'Date', value: 'date', description: 'Date-based reminder' },
  { label: 'Checkbox', value: 'checkbox', description: 'Yes/No reminder' },
];

function FormBuilderEditor({
  points,
  setPoints,
  label,
  isDark,
  isFormBuilder = false,
}: {
  points: any[];
  setPoints: (arr: any[]) => void;
  label: string;
  isDark: boolean;
  isFormBuilder?: boolean;
}) {
  const fieldTypes = isFormBuilder ? PRE_SESSION_FORM_FIELD_TYPES : IN_SESSION_TALKING_POINT_TYPES;

  // Helper to generate a computer name from label
  const generateNameFromLabel = (label: string) =>
    label
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '')
      .replace(/_+/g, '_');

  const addPoint = () => {
    const defaultField = isFormBuilder
      ? { label: '', type: 'text', placeholder: '', required: false, description: '' }
      : { name: '', type: 'markdown', value: '' };
    setPoints([
      ...points,
      {
        fields: [defaultField],
      },
    ]);
  };

  const addField = (idx: number) => {
    const arr = [...points];
    const defaultField = isFormBuilder
      ? { label: '', type: 'text', placeholder: '', required: false, description: '' }
      : { name: '', type: 'markdown', value: '' };
    arr[idx].fields.push(defaultField);
    setPoints(arr);
  };

  const updateField = (pointIdx: number, fieldIdx: number, field: Partial<any>) => {
    const arr = [...points];
    let updatedField = { ...arr[pointIdx].fields[fieldIdx], ...field };
    // For pre-session, auto-generate name from label
    if (isFormBuilder && 'label' in field) {
      updatedField.name = generateNameFromLabel(field.label || '');
    }
    arr[pointIdx].fields[fieldIdx] = updatedField;
    setPoints(arr);
  };

  const removeField = (pointIdx: number, fieldIdx: number) => {
    const arr = [...points];
    arr[pointIdx].fields.splice(fieldIdx, 1);
    setPoints(arr);
  };

  const removePoint = (idx: number) => {
    const arr = [...points];
    arr.splice(idx, 1);
    setPoints(arr);
  };

  return (
    <Card>
      <CardContent className="p-6">
        <h3 className="font-medium mb-4 text-gray-900 dark:text-white">{label}</h3>
        <div className="space-y-6">
          {points.map((tp, idx) => (
            <div key={idx} className="border rounded-lg p-4 mb-2 bg-gray-50 dark:bg-gray-900">
              <h4 className="font-medium mb-3 text-gray-900 dark:text-white">
                {isFormBuilder ? `Form Section ${idx + 1}` : `Talking Point Section ${idx + 1}`}
              </h4>
              {tp.fields.map((field: any, fIdx: number) => (
                <div key={fIdx} className="mb-4 border-l-2 border-blue-200 pl-4">
                  {isFormBuilder ? (
                    // Pre-Session Form Fields (no explicit name input)
                    <div className="space-y-3">
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="text-xs font-medium text-gray-600 dark:text-gray-400">Field Label</label>
                          <Input
                            value={field.label || ''}
                            onChange={e => updateField(idx, fIdx, { label: e.target.value })}
                            placeholder="What users will see (e.g., 'Client Name', 'Session Date')"
                            className="mt-1"
                          />
                        </div>
                        <div>
                          <label className="text-xs font-medium text-gray-600 dark:text-gray-400">Field Type</label>
                          <select
                            value={field.type || 'text'}
                            onChange={e => updateField(idx, fIdx, { type: e.target.value })}
                            className="mt-1 w-full border rounded px-2 py-1 bg-white dark:bg-gray-900"
                          >
                            {fieldTypes.map((opt: any) => (
                              <option key={opt.value} value={opt.value} title={opt.description}>
                                {opt.label}
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>
                      <div>
                        <label className="text-xs font-medium text-gray-600 dark:text-gray-400">Placeholder Text</label>
                        <Input
                          value={field.placeholder || ''}
                          onChange={e => updateField(idx, fIdx, { placeholder: e.target.value })}
                          placeholder="Hint text for users"
                          className="mt-1"
                        />
                      </div>
                      <div>
                        <label className="text-xs font-medium text-gray-600 dark:text-gray-400">Description</label>
                        <Input
                          value={field.description || ''}
                          onChange={e => updateField(idx, fIdx, { description: e.target.value })}
                          placeholder="Help text to explain this field"
                          className="mt-1"
                        />
                      </div>
                      {field.type === 'select' && (
                        <div>
                          <label className="text-xs font-medium text-gray-600 dark:text-gray-400">Options (comma-separated)</label>
                          <Input
                            value={field.options || ''}
                            onChange={e => updateField(idx, fIdx, { options: e.target.value })}
                            placeholder="Option 1, Option 2, Option 3"
                            className="mt-1"
                          />
                        </div>
                      )}
                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={field.required || false}
                          onChange={e => updateField(idx, fIdx, { required: e.target.checked })}
                          className="w-4 h-4"
                        />
                        <label className="text-xs font-medium text-gray-600 dark:text-gray-400">Required field</label>
                      </div>
                      {/* Show generated name for reference */}
                      {field.label && (
                        <div className="text-xs text-gray-400 mt-1">Field variable: <span className="font-mono">{generateNameFromLabel(field.label)}</span></div>
                      )}
                    </div>
                  ) : (
                    // In-Session Talking Points (Rich Text default, with title)
                    <div className="space-y-3">
                      <div className="mb-2">
                        <label className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1 block">Title</label>
                        <Input
                          value={field.title || ''}
                          onChange={e => updateField(idx, fIdx, { title: e.target.value })}
                          placeholder="Enter a title for this talking point"
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <select
                          value={field.type || 'markdown'}
                          onChange={e => updateField(idx, fIdx, { type: e.target.value })}
                          className="border rounded px-2 py-1 bg-white dark:bg-gray-900"
                        >
                          {fieldTypes.map((opt: any) => (
                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                          ))}
                        </select>
                        {field.type === 'date' && (
                          <Input
                            type="date"
                            value={field.value || ''}
                            onChange={e => updateField(idx, fIdx, { value: e.target.value })}
                          />
                        )}
                        {field.type === 'checkbox' && (
                          <div className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              checked={!!field.value}
                              onChange={e => updateField(idx, fIdx, { value: e.target.checked })}
                              className="w-5 h-5"
                            />
                            <span>Checked?</span>
                          </div>
                        )}
                      </div>
                      {/* Rich Text editor is default for talking points */}
                      {(!field.type || field.type === 'markdown') && (
                        <div className="w-full">
                          <label className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1 block">Rich Text</label>
                          <MDEditor
                            value={field.value || ''}
                            onChange={val => updateField(idx, fIdx, { value: val || '' })}
                            data-color-mode={isDark ? 'dark' : 'light'}
                            height={120}
                            preview="edit"
                            hideToolbar={false}
                            visibleDragbar={false}
                          />
                        </div>
                      )}
                      {field.type === 'text' && (
                        <Input
                          value={field.value || ''}
                          onChange={e => updateField(idx, fIdx, { value: e.target.value })}
                          placeholder="Quick note (plain text)"
                        />
                      )}
                    </div>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => removeField(idx, fIdx)}
                    className="mt-2"
                  >
                    Remove {isFormBuilder ? 'Field' : 'Talking Point'}
                  </Button>
                </div>
              ))}
              <div className="flex gap-2 mt-3 pt-3 border-t">
                <Button variant="outline" size="sm" onClick={() => addField(idx)}>
                  + Add {isFormBuilder ? 'Form Field' : 'Talking Point'}
                </Button>
                <Button variant="outline" size="sm" onClick={() => removePoint(idx)}>
                  Remove Section
                </Button>
              </div>
            </div>
          ))}
          <Button variant="outline" onClick={addPoint}>
            + Add {isFormBuilder ? 'Form Section' : 'Talking Point Section'}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export function FocusedEditor({ 
  selectedSubcategory, 
  onSave, 
  onCancel 
}: FocusedEditorProps) {
  const [promptName, setPromptName] = useState("");
  const [promptContent, setPromptContent] = useState("");
  const [preSessionTalkingPoints, setPreSessionTalkingPoints] = useState<any[]>([]);
  const [inSessionTalkingPoints, setInSessionTalkingPoints] = useState<any[]>([]);
  const [isEditing, setIsEditing] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const isDark = useTheme();

  useEffect(() => {
    // Apply theme to MDEditor
    const mdEditor = document.querySelector('.w-md-editor');
    if (mdEditor) {
      mdEditor.setAttribute('data-color-mode', isDark ? 'dark' : 'light');
    }
  }, [isDark]);

  // Remove all mock data: fetch real data from backend endpoints
  useEffect(() => {
    async function fetchData() {
      if (selectedSubcategory) {
        try {
          const promptsResponse = await fetchPrompts();
          let foundSubcategory = null;
          for (const category of promptsResponse.data) {
            for (const sub of category.subcategories) {
              if (sub.subcategory_id === selectedSubcategory.id || sub.subcategory_id === selectedSubcategory.subcategory_id) {
                foundSubcategory = sub;
                break;
              }
            }
            if (foundSubcategory) break;
          }
          if (foundSubcategory) {
            setPromptName(foundSubcategory.subcategory_name || "");
            const prompts = foundSubcategory.prompts || {};
            const firstPromptKey = Object.keys(prompts)[0];
            setPromptContent(firstPromptKey ? prompts[firstPromptKey] : "");
            setPreSessionTalkingPoints(foundSubcategory.preSessionTalkingPoints || []);
            setInSessionTalkingPoints(foundSubcategory.inSessionTalkingPoints || []);
            setIsEditing(true);
          } else {
            setPromptName("");
            setPromptContent("");
            setPreSessionTalkingPoints([]);
            setInSessionTalkingPoints([]);
            setIsEditing(false);
          }
        } catch (error) {
          setPromptName("");
          setPromptContent("");
          setPreSessionTalkingPoints([]);
          setInSessionTalkingPoints([]);
          setIsEditing(false);
        }
      } else {
        setPromptName("");
        setPromptContent("");
        setPreSessionTalkingPoints([]);
        setInSessionTalkingPoints([]);
        setIsEditing(false);
      }
    }
    fetchData();
  }, [selectedSubcategory]);

  const handleSave = async () => {
    if (onSave) {
      setIsSaving(true);
      try {
        // Ensure inSessionTalkingPoints fields always have title, type, value
        // Support legacy schema: map 'name' to 'title' if present
        const cleanedInSessionTalkingPoints = inSessionTalkingPoints.map(section => ({
          ...section,
          fields: (section.fields || []).map((f: any) => ({
            title: f.title || f.name || '',
            name: f.name || f.title || '',
            type: f.type || 'markdown',
            value: f.value || '',
          }))
        }));
        const cleanedPreSessionTalkingPoints = preSessionTalkingPoints.map(section => ({
          ...section,
          fields: (section.fields || []).map((f: any) => ({
            ...f
          }))
        }));
        if (selectedSubcategory && selectedSubcategory.id) {
          await updateSubcategory({
            subcategoryId: selectedSubcategory.id,
            name: promptName,
            prompts: {
              [promptName]: promptContent
            },
            preSessionTalkingPoints: cleanedPreSessionTalkingPoints,
            inSessionTalkingPoints: cleanedInSessionTalkingPoints,
          });
        }
        await onSave({
          name: promptName,
          prompts: {
            [promptName]: promptContent
          },
          preSessionTalkingPoints: cleanedPreSessionTalkingPoints,
          inSessionTalkingPoints: cleanedInSessionTalkingPoints,
        });
        toast.success("Prompt saved successfully!");
      } catch (error) {
        console.error("Failed to save:", error);
        toast.error("Failed to save prompt. Please try again.");
      } finally {
        setIsSaving(false);
      }
    }
  };

  // Delete handler (to be implemented with backend API if needed)
  const handleDelete = async () => {
    if (!selectedSubcategory || !selectedSubcategory.id) return;
    setShowDeleteDialog(true);
  };

  const confirmDelete = async () => {
    if (!selectedSubcategory || !selectedSubcategory.id) return;
    setIsDeleting(true);
    try {
      await deleteSubcategory(selectedSubcategory.id);
      setPromptName("");
      setPromptContent("");
      setPreSessionTalkingPoints([]);
      setInSessionTalkingPoints([]);
      setIsEditing(false);
      setShowDeleteDialog(false);
      setIsDeleting(false);
      toast.success("Prompt deleted successfully!");
      if (onCancel) onCancel();
    } catch (error) {
      setIsDeleting(false);
      setShowDeleteDialog(false);
      console.error("Failed to delete subcategory:", error);
      toast.error("Failed to delete prompt. Please try again.");
    }
  };

  if (!selectedSubcategory && !isEditing) {
    return (
      <div className="flex-1 flex items-center justify-center bg-white dark:bg-black rounded-lg">
        <div className="text-center">
          <p className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            Select a prompt to edit
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Choose a prompt from the sidebar to view and edit its content
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 bg-white dark:bg-black">
      <div className="h-full flex flex-col">
        {/* Delete Confirmation Dialog */}
        {showDeleteDialog && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40">
            <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-8 w-full max-w-md border border-gray-200 dark:border-gray-700">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">Delete Prompt</h2>
              <p className="text-gray-700 dark:text-gray-300 mb-6">Are you sure you want to delete this prompt? This action cannot be undone.</p>
              <div className="flex justify-end gap-3">
                <Button
                  variant="outline"
                  className="border-gray-300 dark:border-gray-600"
                  onClick={() => setShowDeleteDialog(false)}
                  disabled={isDeleting}
                >
                  Cancel
                </Button>
                <Button
                  className="bg-red-500 hover:bg-red-600 text-white"
                  onClick={confirmDelete}
                  disabled={isDeleting}
                >
                  {isDeleting ? "Deleting..." : "Delete"}
                </Button>
              </div>
            </div>
          </div>
        )}
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            {isEditing ? `Edit: ${promptName}` : "New Prompt"}
          </h1>
          <div className="flex gap-2">
            <Button 
              onClick={handleSave}
              disabled={isSaving}
              className="bg-blue-500 hover:bg-blue-600 text-white disabled:opacity-50"
            >
              <Save className="w-4 h-4 mr-2" />
              {isSaving ? "Saving..." : "Save"}
            </Button>
            <Button
              onClick={handleDelete}
              disabled={isSaving}
              className="bg-red-500 hover:bg-red-600 text-white disabled:opacity-50"
            >
              Delete
            </Button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 p-6">
          <Tabs defaultValue="content" className="h-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="content">Prompt Content</TabsTrigger>
              <TabsTrigger value="talking-points">Form Builder & Talking Points</TabsTrigger>
            </TabsList>
            
            <TabsContent value="content" className="mt-6 h-full">
              <div className="space-y-4 h-full">
                <div className="space-y-2">
                  <Label htmlFor="prompt-name" className="text-sm font-medium text-gray-900 dark:text-white">
                    Prompt Name
                  </Label>
                  <Input
                    id="prompt-name"
                    value={promptName}
                    onChange={(e) => setPromptName(e.target.value)}
                    placeholder="Enter prompt name"
                    className="bg-white dark:bg-gray-900 border-gray-300 dark:border-gray-600"
                  />
                </div>
                
                <div className="space-y-2 flex-1">
                  <Label className="text-sm font-medium text-gray-900 dark:text-white">
                    Prompt Content
                  </Label>
                  <div 
                    className="border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden bg-white dark:bg-gray-900"
                    data-color-mode={isDark ? 'dark' : 'light'}
                    style={{
                      '--md-editor-bg': isDark ? '#111827' : '#ffffff',
                      '--md-editor-color': isDark ? '#ffffff' : '#111827',
                      '--md-editor-border': isDark ? '#374151' : '#d1d5db',
                    } as React.CSSProperties}
                  >
                    <MDEditor
                      value={promptContent}
                      onChange={(val) => setPromptContent(val || "")}
                      data-color-mode={isDark ? 'dark' : 'light'}
                      height={400}
                      preview="edit"
                      hideToolbar={false}
                      visibleDragbar={false}
                    />
                  </div>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="talking-points" className="mt-6">
              <div className="space-y-8">
                <div className="bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-6">
                  <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">Pre-Session Form Builder</h3>
                  <p className="text-sm text-blue-700 dark:text-blue-300">
                    Design form fields that users will fill out before starting a session. This data will be injected into the prompt context automatically.
                  </p>
                </div>
                <FormBuilderEditor
                  points={preSessionTalkingPoints}
                  setPoints={setPreSessionTalkingPoints}
                  label="Pre-Session Form Fields"
                  isDark={isDark}
                  isFormBuilder={true}
                />
                
                <div className="bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg p-4 mb-6">
                  <h3 className="font-semibold text-green-900 dark:text-green-100 mb-2">In-Session Talking Points</h3>
                  <p className="text-sm text-green-700 dark:text-green-300">
                    Create talking points and reminders to guide conversations during the session.
                  </p>
                </div>
                <FormBuilderEditor
                  points={inSessionTalkingPoints}
                  setPoints={setInSessionTalkingPoints}
                  label="In-Session Talking Points"
                  isDark={isDark}
                  isFormBuilder={false}
                />
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}
