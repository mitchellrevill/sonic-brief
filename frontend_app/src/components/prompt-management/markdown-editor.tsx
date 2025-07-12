import type { ChangeEvent } from "react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

import "@uiw/react-markdown-preview/markdown.css";
import "@uiw/react-md-editor/markdown-editor.css";

import type { PromptKeyValue } from "@/lib/prompt-management";
import {
  objectToPromptsArray,
  promptsArrayToObject,
} from "@/lib/prompt-management";
import MDPreview from "@uiw/react-markdown-preview";
import MDEditor from "@uiw/react-md-editor";

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

interface MarkdownEditorProps {
  value?: Record<string, string>;
  onChange: (value: Record<string, string>) => void;
}

export function MarkdownEditor({ value = {}, onChange }: MarkdownEditorProps) {
  const [prompts, setPrompts] = useState<Array<PromptKeyValue>>(() =>
    objectToPromptsArray(value),
  );
  const [activeTab, setActiveTab] = useState("edit");
  const isDark = useTheme();

  useEffect(() => {
    const incomingPromptsArray = objectToPromptsArray(value);
    const currentPromptsObject = promptsArrayToObject(prompts);

    if (
      JSON.stringify(promptsArrayToObject(incomingPromptsArray)) !==
      JSON.stringify(currentPromptsObject)
    ) {
      setPrompts(incomingPromptsArray);
    }
  }, [value]);

  const updatePromptsAndNotify = (newPrompts: Array<PromptKeyValue>) => {
    const finalPrompts =
      newPrompts.length > 0 ? newPrompts : [{ key: "", value: "" }];
    setPrompts(finalPrompts);
    onChange(promptsArrayToObject(finalPrompts));
  };

  const handleAddPrompt = () => {
    updatePromptsAndNotify([...prompts, { key: "", value: "" }]);
  };

  const handleRemovePrompt = (index: number) => {
    const newPrompts = [...prompts];
    newPrompts.splice(index, 1);
    updatePromptsAndNotify(newPrompts);
  };

  const handleKeyChange = (index: number, key: string) => {
    const newPrompts = [...prompts];
    newPrompts[index] = { ...newPrompts[index], key };
    updatePromptsAndNotify(newPrompts);
  };

  const handleValueChange = (index: number, newValue: string) => {
    const newPrompts = [...prompts];
    newPrompts[index] = { ...newPrompts[index], value: newValue || "" };
    updatePromptsAndNotify(newPrompts);
  };

  const canAddPrompt = prompts.every(
    (prompt) => prompt.key.trim() && prompt.value.trim(),
  );

  return (
    <div className="space-y-4">
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="edit">Edit</TabsTrigger>
          <TabsTrigger value="preview">Preview</TabsTrigger>
        </TabsList>
        <TabsContent value="edit" className="space-y-4">
          {prompts.map((prompt, index) => (
            <div
              key={`prompt-${index}`}
              className="space-y-4 rounded-md border p-4"
            >
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium">Prompt {index + 1}</h3>
                {prompts.length > 1 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRemovePrompt(index)}
                  >
                    Remove
                  </Button>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor={`prompt-key-${index}`}>Prompt Key</Label>
                <Input
                  id={`prompt-key-${index}`}
                  value={prompt.key}
                  onChange={(e: ChangeEvent<HTMLInputElement>) =>
                    handleKeyChange(index, e.target.value)
                  }
                  placeholder="Enter prompt key (e.g., 'greeting')"
                />
                {!prompt.key.trim() && index < prompts.length - 1 && (
                  <p className="text-destructive text-xs">
                    Key cannot be empty.
                  </p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor={`prompt-value-${index}`}>
                  Prompt Content (Markdown)
                </Label>
                <div data-color-mode={isDark ? "dark" : "light"} className="w-md-editor-theme">
                  <MDEditor
                    id={`prompt-value-${index}`}
                    value={prompt.value}
                    onChange={(val) => handleValueChange(index, val || "")}
                    preview="edit"
                    height={200}
                    data-color-mode={isDark ? "dark" : "light"}
                    className="!bg-transparent [&_.w-md-editor]:!bg-white dark:[&_.w-md-editor]:!bg-gray-900 [&_.w-md-editor-text-container]:!bg-white dark:[&_.w-md-editor-text-container]:!bg-gray-900 [&_.w-md-editor-text-container_.w-md-editor-text-textarea]:!bg-white dark:[&_.w-md-editor-text-container_.w-md-editor-text-textarea]:!bg-gray-900 [&_.w-md-editor-text-container_.w-md-editor-text-textarea]:!text-gray-900 dark:[&_.w-md-editor-text-container_.w-md-editor-text-textarea]:!text-gray-100 [&_.w-md-editor-text-container_.w-md-editor-text-textarea]:!border-gray-300 dark:[&_.w-md-editor-text-container_.w-md-editor-text-textarea]:!border-gray-600"
                    textareaProps={{
                      placeholder: "Enter prompt content using Markdown",
                    }}
                  />
                </div>
                {!prompt.value.trim() && index < prompts.length - 1 && (
                  <p className="text-destructive text-xs">
                    Value cannot be empty.
                  </p>
                )}
              </div>
            </div>
          ))}
          <Button
            type="button"
            variant="outline"
            onClick={handleAddPrompt}
            className="w-full"
            disabled={!canAddPrompt}
          >
            Add Prompt
          </Button>
        </TabsContent>
        <TabsContent value="preview" className="space-y-4">
          {prompts
            .filter((p) => p.key.trim())
            .map((prompt, index) => (
              <div
                key={`preview-prompt-${index}`}
                className="space-y-4 rounded-md border p-4"
              >
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-medium">{prompt.key}</h3>
                </div>
                <div className="bg-background rounded-md border p-4">
                  <MDPreview source={prompt.value.trim()} />
                </div>
              </div>
            ))}
          {prompts.filter((p) => p.key.trim()).length === 0 && (
            <p className="text-muted-foreground text-sm">
              No prompts with keys entered yet to preview.
            </p>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
