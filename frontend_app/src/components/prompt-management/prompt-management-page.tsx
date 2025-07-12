import { useState } from "react";
import { PromptManagementProvider } from "@/components/prompt-management/prompt-management-context";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Plus, Search } from "lucide-react";
import { PromptManagementSidebar } from "@/components/prompt-management/prompt-management-sidebar";
import { PromptBrowseView } from "@/components/prompt-management/prompt-browse-view";
import { FocusedEditor } from "@/components/prompt-management/focused-editor";
import { PromptAnalyticsDashboard } from "@/components/prompt-management/prompt-analytics-dashboard";

const TABS = ["Browse", "Editor", "Analytics"] as const;
type TabType = typeof TABS[number];

function PromptManagementHeader() {
  return (
    <div className="flex items-center justify-between px-4 py-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          Prompt Management
        </h1>
      </div>
      <div className="flex items-center space-x-2">
        <Button size="sm" variant="outline">
          <Search className="mr-2 h-4 w-4" />
          <span className="hidden sm:inline">Search</span>
        </Button>
        <Button size="sm">
          <Plus className="mr-2 h-4 w-4" />
          <span className="hidden sm:inline">New Category</span>
        </Button>
      </div>
    </div>
  );
}

function PromptManagementContent() {
  const [activeTab, setActiveTab] = useState<TabType>("Browse");
  const [selectedCategory, setSelectedCategory] = useState<any>(null);
  const [selectedSubcategory, setSelectedSubcategory] = useState<any>(null);

  const handleTabChange = (tab: TabType) => {
    setActiveTab(tab);
  };

  return (
    <div className="space-y-4">
      {/* Tab Navigation */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Prompt Library</CardTitle>
            <div className="flex space-x-1">
              {TABS.map((tab) => (
                <Button
                  key={tab}
                  size="sm"
                  variant={activeTab === tab ? "default" : "ghost"}
                  onClick={() => handleTabChange(tab)}
                  className="h-8"
                >
                  {tab}
                </Button>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="flex min-h-[600px]">
            {/* Sidebar */}
            <div className="w-80 border-r bg-white dark:bg-black">
              <PromptManagementSidebar
                selectedCategory={selectedCategory}
                setSelectedCategory={setSelectedCategory}
                selectedSubcategory={selectedSubcategory}
                setSelectedSubcategory={setSelectedSubcategory}
                activeTab={activeTab}
              />
            </div>

            {/* Main Content */}
            <div className="flex-1 bg-white dark:bg-black overflow-auto">
              {activeTab === "Browse" && (
                <PromptBrowseView
                  selectedCategory={selectedCategory}
                  selectedSubcategory={selectedSubcategory}
                  onEditPrompt={(subcategory: any) => {
                    setSelectedSubcategory(subcategory);
                    setActiveTab("Editor");
                  }}
                />
              )}
              
              {activeTab === "Editor" && (
                <FocusedEditor
                  selectedSubcategory={selectedSubcategory}
                  onSave={async () => {
                    // Handle save
                  }}
                  onCancel={() => {
                    setActiveTab("Browse");
                  }}
                />
              )}
              
              {activeTab === "Analytics" && (
                <PromptAnalyticsDashboard
                  selectedCategory={selectedCategory}
                  selectedSubcategory={selectedSubcategory}
                />
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export function PromptManagementPage() {
  return (
    <PromptManagementProvider>
      <div className="space-y-6">
        <PromptManagementHeader />
        <PromptManagementContent />
      </div>
    </PromptManagementProvider>
  );
}
