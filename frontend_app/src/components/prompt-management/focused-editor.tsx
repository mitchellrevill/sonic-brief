import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Save, X } from "lucide-react";
import MDEditor from "@uiw/react-md-editor";
import "@uiw/react-md-editor/markdown-editor.css";
import { fetchPrompts, updateSubcategory } from "@/api/prompt-management";

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

export function FocusedEditor({ 
  selectedSubcategory, 
  onSave, 
  onCancel 
}: FocusedEditorProps) {
  const [promptName, setPromptName] = useState("");
  const [promptContent, setPromptContent] = useState("");
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
            setIsEditing(true);
          } else {
            setPromptName("");
            setPromptContent("");
            setIsEditing(false);
          }
        } catch (error) {
          setPromptName("");
          setPromptContent("");
          setIsEditing(false);
        }
      } else {
        setPromptName("");
        setPromptContent("");
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
          });
        }
        await onSave({
          name: promptName,
          prompts: {
            [promptName]: promptContent
          },
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
      <div className="flex-1 flex items-center justify-center bg-background rounded-lg">
        <div className="text-center">
          <p className="text-lg font-medium text-foreground mb-2">
            Select a prompt to edit
          </p>
          <p className="text-sm text-muted-foreground">
            Choose a prompt from the sidebar to view and edit its content
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 bg-background">
      <div className="h-full flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-border bg-background">
          <h1 className="text-2xl font-bold text-foreground">
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
              className="border-border"
            >
              <X className="w-4 h-4 mr-2" />
              Cancel
            </Button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 p-6 bg-background">
          <div className="space-y-4 h-full">
            <div className="space-y-2">
              <Label htmlFor="prompt-name" className="text-sm font-medium text-foreground">
                Prompt Name
              </Label>
              <Input
                id="prompt-name"
                value={promptName}
                onChange={(e) => setPromptName(e.target.value)}
                placeholder="Enter prompt name"
                className="bg-background border-border text-foreground"
              />
            </div>
            
            <div className="space-y-2 flex-1">
              <Label className="text-sm font-medium text-foreground">
                Prompt Content
              </Label>
              <div 
                className="border border-border rounded-lg overflow-hidden bg-background"
                data-color-mode={isDark ? 'dark' : 'light'}
                style={{
                  '--md-editor-bg': isDark ? 'hsl(var(--background))' : 'hsl(var(--background))',
                  '--md-editor-color': isDark ? 'hsl(var(--foreground))' : 'hsl(var(--foreground))',
                  '--md-editor-border': isDark ? 'hsl(var(--border))' : 'hsl(var(--border))',
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
        </div>
      </div>
    </div>
  );
}
