import { Edit, Download, Copy, Eye } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import MDPreview from "@uiw/react-markdown-preview";

interface PromptBrowseViewProps {
  selectedCategory: any;
  selectedSubcategory: any;
  onEditPrompt?: (subcategory: any) => void;
}

export function PromptBrowseView({ 
  selectedCategory, 
  selectedSubcategory, 
  onEditPrompt 
}: PromptBrowseViewProps) {
  if (!selectedSubcategory) {
    return (
      <div className="flex items-center justify-center h-full text-blue-600 dark:text-blue-400">
        <div className="text-center">
          <Eye className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <h3 className="text-lg font-medium mb-2">No prompt selected</h3>
          <p>Select a prompt from the sidebar to view its content</p>
        </div>
      </div>
    );
  }

  // Since subcategories are now prompts, get the first (and only) prompt content
  const prompts = selectedSubcategory.prompts || {};
  const promptKeys = Object.keys(prompts);
  const promptContent = promptKeys.length > 0 ? prompts[promptKeys[0]] : "";

  const handleEditPrompt = () => {
    if (onEditPrompt) {
      onEditPrompt(selectedSubcategory);
    }
  };

  const handleExportPrompt = () => {
    const blob = new Blob([promptContent], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedSubcategory.name}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDuplicatePrompt = () => {
    // TODO: Implement prompt duplication
    console.log('Duplicate prompt:', selectedSubcategory.name);
  };

  return (
    <div className="flex-1 flex flex-col bg-background">
      {/* Prompt Header */}
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground mb-2">
              {selectedSubcategory.name}
            </h1>
            <div className="flex items-center space-x-2">
              <Badge variant="secondary" className="text-xs">
                {selectedCategory?.name || 'Unknown Category'}
              </Badge>
              <Badge variant="outline" className="text-xs">
                Prompt
              </Badge>
            </div>
          </div>
          <div className="flex space-x-2">
            <Button
              size="sm"
              variant="outline"
              onClick={handleExportPrompt}
              className="border-gray-300 dark:border-gray-600"
            >
              <Download className="h-4 w-4 mr-1" />
              Export
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={handleDuplicatePrompt}
              className="border-gray-300 dark:border-gray-600"
            >
              <Copy className="h-4 w-4 mr-1" />
              Duplicate
            </Button>
            <Button
              size="sm"
              onClick={handleEditPrompt}
              className="bg-blue-500 hover:bg-blue-600 text-white"
            >
              <Edit className="h-4 w-4 mr-1" />
              Edit
            </Button>
          </div>
        </div>
      </div>

      {/* Prompt Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {promptContent ? (
          <>
            <Card className="mb-6">
              <CardHeader>
                <CardTitle className="text-lg text-foreground">Prompt Content</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="prose dark:prose-invert max-w-none">
                  <MDPreview
                    source={promptContent}
                    style={{
                      backgroundColor: 'transparent',
                      color: 'inherit',
                    }}
                    data-color-mode="auto"
                  />
                </div>
              </CardContent>
            </Card>

            {/* Metadata */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg text-foreground">Metadata</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="font-medium text-blue-600 dark:text-blue-400">Length:</span>
                    <p className="text-foreground">{promptContent.length} characters</p>
                  </div>
                  <div>
                    <span className="font-medium text-blue-600 dark:text-blue-400">Words:</span>
                    <p className="text-foreground">{promptContent.split(/\s+/).length} words</p>
                  </div>
                  <div>
                    <span className="font-medium text-blue-600 dark:text-blue-400">Lines:</span>
                    <p className="text-foreground">{promptContent.split('\n').length} lines</p>
                  </div>
                  <div>
                    <span className="font-medium text-blue-600 dark:text-blue-400">Last Modified:</span>
                    <p className="text-foreground">
                      {selectedSubcategory.updated_at 
                        ? new Date(selectedSubcategory.updated_at * 1000).toLocaleDateString()
                        : 'Unknown'
                      }
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </>
        ) : (
          <div className="flex items-center justify-center h-full text-blue-600 dark:text-blue-400">
            <div className="text-center">
              <Eye className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <h3 className="text-lg font-medium mb-2">No content available</h3>
              <p>This prompt has no content yet</p>
              <Button
                size="sm"
                variant="outline"
                onClick={handleEditPrompt}
                className="mt-4"
              >
                Add Content
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
