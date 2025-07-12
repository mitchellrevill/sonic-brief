import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Save, X } from "lucide-react";
import MDEditor from "@uiw/react-md-editor";
import "@uiw/react-md-editor/markdown-editor.css";
import { fetchPrompts, createSubcategory, updateSubcategory } from "@/api/prompt-management";

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

const TALKING_POINT_FIELD_TYPES = [
  { label: 'Text', value: 'text' },
  { label: 'Date', value: 'date' },
  { label: 'Markdown', value: 'markdown' },
  { label: 'Checkbox', value: 'checkbox' },
];

function TalkingPointEditor({
  points,
  setPoints,
  label,
  isDark,
}: {
  points: any[];
  setPoints: (arr: any[]) => void;
  label: string;
  isDark: boolean;
}) {
  const addPoint = () => {
    setPoints([
      ...points,
      {
        fields: [
          { name: 'Text', type: 'text', value: '' },
        ],
      },
    ]);
  };

  const addField = (idx: number) => {
    const arr = [...points];
    arr[idx].fields.push({ name: '', type: 'text', value: '' });
    setPoints(arr);
  };

  const updateField = (pointIdx: number, fieldIdx: number, field: Partial<{ name: string; type: string; value: any }>) => {
    const arr = [...points];
    arr[pointIdx].fields[fieldIdx] = { ...arr[pointIdx].fields[fieldIdx], ...field };
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
              {tp.fields.map((field: any, fIdx: number) => (
                <div key={fIdx} className="mb-3 flex gap-2 items-center">
                  <Input
                    value={field.name}
                    onChange={e => updateField(idx, fIdx, { name: e.target.value })}
                    placeholder="Field Name"
                    className="w-1/3"
                  />
                  <select
                    value={field.type}
                    onChange={e => updateField(idx, fIdx, { type: e.target.value })}
                    className="border rounded px-2 py-1 bg-white dark:bg-gray-900"
                  >
                    {TALKING_POINT_FIELD_TYPES.map(opt => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                  {field.type === 'text' && (
                    <Input
                      value={field.value}
                      onChange={e => updateField(idx, fIdx, { value: e.target.value })}
                      placeholder="Value"
                      className="w-1/2"
                    />
                  )}
                  {field.type === 'date' && (
                    <Input
                      type="date"
                      value={field.value}
                      onChange={e => updateField(idx, fIdx, { value: e.target.value })}
                      className="w-1/3"
                    />
                  )}
                  {field.type === 'markdown' && (
                    <div className="w-full">
                      <MDEditor
                        value={field.value}
                        onChange={val => updateField(idx, fIdx, { value: val || '' })}
                        data-color-mode={isDark ? 'dark' : 'light'}
                        height={120}
                        preview="edit"
                        hideToolbar={false}
                        visibleDragbar={false}
                      />
                    </div>
                  )}
                  {field.type === 'checkbox' && (
                    <input
                      type="checkbox"
                      checked={!!field.value}
                      onChange={e => updateField(idx, fIdx, { value: e.target.checked })}
                      className="w-5 h-5"
                    />
                  )}
                  <Button variant="outline" size="sm" onClick={() => removeField(idx, fIdx)}>
                    Remove Field
                  </Button>
                </div>
              ))}
              <div className="flex gap-2 mt-2">
                <Button variant="outline" size="sm" onClick={() => addField(idx)}>
                  + Add Field
                </Button>
                <Button variant="outline" size="sm" onClick={() => removePoint(idx)}>
                  Remove Section
                </Button>
              </div>
            </div>
          ))}
          <Button variant="outline" onClick={addPoint}>+ Add Section</Button>
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
      try {
        if (selectedSubcategory && selectedSubcategory.id) {
          await updateSubcategory({
            subcategoryId: selectedSubcategory.id,
            name: promptName,
            prompts: {
              [promptName]: promptContent
            },
            preSessionTalkingPoints,
            inSessionTalkingPoints,
          });
        }
        await onSave({
          name: promptName,
          prompts: {
            [promptName]: promptContent
          },
          preSessionTalkingPoints,
          inSessionTalkingPoints,
        });
      } catch (error) {
        console.error("Failed to save:", error);
      }
    }
  };

  const handleCancel = () => {
    if (onCancel) {
      onCancel();
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
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            {isEditing ? `Edit: ${promptName}` : "New Prompt"}
          </h1>
          <div className="flex gap-2">
            <Button 
              onClick={handleSave}
              className="bg-blue-500 hover:bg-blue-600 text-white"
            >
              <Save className="w-4 h-4 mr-2" />
              Save
            </Button>
            <Button 
              variant="outline" 
              onClick={handleCancel}
              className="border-gray-300 dark:border-gray-600"
            >
              <X className="w-4 h-4 mr-2" />
              Cancel
            </Button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 p-6">
          <Tabs defaultValue="content" className="h-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="content">Prompt Content</TabsTrigger>
              <TabsTrigger value="talking-points">Talking Points</TabsTrigger>
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
              <div className="space-y-4">
                <TalkingPointEditor
                  points={preSessionTalkingPoints}
                  setPoints={setPreSessionTalkingPoints}
                  label="Pre-Session Talking Points"
                  isDark={isDark}
                />
                <TalkingPointEditor
                  points={inSessionTalkingPoints}
                  setPoints={setInSessionTalkingPoints}
                  label="In-Session Talking Points"
                  isDark={isDark}
                />
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}
