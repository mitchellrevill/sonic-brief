import { useState, useEffect } from "react";
import { ChevronDown, ChevronRight, FolderOpen, Folder, FileText, Plus } from "lucide-react";
import { usePromptManagement } from "./prompt-management-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

interface SidebarProps {
  selectedCategory: any;
  setSelectedCategory: (cat: any) => void;
  selectedSubcategory: any;
  setSelectedSubcategory: (sub: any) => void;
  activeTab: string;
}

export function PromptManagementSidebar({
  selectedCategory,
  setSelectedCategory,
  selectedSubcategory,
  setSelectedSubcategory,
}: SidebarProps) {
  const {
    categories,
    subcategories,
    loading,
    error,
    addCategory,
    addSubcategory,
  } = usePromptManagement();

  // Collapsible state management
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());
  const [showNewCategoryDialog, setShowNewCategoryDialog] = useState(false);
  const [showNewSubcategoryDialog, setShowNewSubcategoryDialog] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState("");
  const [newSubcategoryName, setNewSubcategoryName] = useState("");
  const [selectedCategoryForSub, setSelectedCategoryForSub] = useState<any>(null);

  // Persist expanded state in localStorage
  useEffect(() => {
    const saved = localStorage.getItem('prompt-management-expanded-categories');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setExpandedCategories(new Set(parsed));
      } catch (e) {
        console.warn('Failed to parse saved expanded categories', e);
      }
    }
  }, []);

  useEffect(() => {
    localStorage.setItem(
      'prompt-management-expanded-categories', 
      JSON.stringify(Array.from(expandedCategories))
    );
  }, [expandedCategories]);

  // Helper functions
  const getId = (obj: any) => typeof obj?.id === "string" ? obj.id : String(obj?.id ?? "");

  const toggleCategory = (categoryId: string) => {
    setExpandedCategories(prev => {
      const newSet = new Set(prev);
      if (newSet.has(categoryId)) {
        newSet.delete(categoryId);
      } else {
        newSet.add(categoryId);
      }
      return newSet;
    });
  };

  const handleCategoryClick = (category: any) => {
    const categoryId = getId(category);
    setSelectedCategory(category);
    // Auto-expand when selecting a category
    if (!expandedCategories.has(categoryId)) {
      toggleCategory(categoryId);
    }
  };

  const handleSubcategoryClick = (subcategory: any) => {
    setSelectedSubcategory(subcategory);
    // Also select the parent category
    const parentCategory = categories.find(cat => getId(cat) === subcategory.category_id);
    if (parentCategory) {
      setSelectedCategory(parentCategory);
    }
  };

  const getSubcategoriesForCategory = (categoryId: string) => {
    return subcategories.filter(sub => sub.category_id === categoryId);
  };

  const handleCreateCategory = async () => {
    if (!newCategoryName.trim()) return;
    
    try {
      await addCategory(newCategoryName.trim());
      setNewCategoryName("");
      setShowNewCategoryDialog(false);
    } catch (error) {
      console.error("Failed to create category:", error);
    }
  };

  const handleCreateSubcategory = async () => {
    if (!newSubcategoryName.trim() || !selectedCategoryForSub) return;
    
    try {
      await addSubcategory(
        newSubcategoryName.trim(),
        getId(selectedCategoryForSub),
        { "default": "Enter your prompt content here..." }
      );
      setNewSubcategoryName("");
      setShowNewSubcategoryDialog(false);
      setSelectedCategoryForSub(null);
    } catch (error) {
      console.error("Failed to create subcategory:", error);
    }
  };

  if (loading) {
    return (
      <div className="p-4 space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="animate-pulse">
            <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded mb-2"></div>
            <div className="ml-4 space-y-1">
              <div className="h-6 bg-gray-100 dark:bg-gray-600 rounded"></div>
              <div className="h-6 bg-gray-100 dark:bg-gray-600 rounded"></div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4">
        <div className="text-red-500 text-sm">{error}</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-foreground">
            Prompt Library
          </h3>
        </div>
        <div className="flex gap-2">
          <Dialog open={showNewCategoryDialog} onOpenChange={setShowNewCategoryDialog}>
            <DialogTrigger asChild>
              <Button size="sm" variant="outline" className="flex-1">
                <Plus className="h-3 w-3 mr-1" />
                Category
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create New Category</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <Input
                  placeholder="Category name"
                  value={newCategoryName}
                  onChange={(e) => setNewCategoryName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleCreateCategory()}
                />
                <div className="flex gap-2">
                  <Button variant="outline" onClick={() => setShowNewCategoryDialog(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleCreateCategory}>
                    Create
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>

          <Dialog open={showNewSubcategoryDialog} onOpenChange={setShowNewSubcategoryDialog}>
            <DialogTrigger asChild>
              <Button size="sm" variant="outline" className="flex-1">
                <Plus className="h-3 w-3 mr-1" />
                Prompt
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create New Prompt</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium">Category</label>
                  <select
                    className="w-full mt-1 p-2 border rounded-md"
                    value={selectedCategoryForSub ? getId(selectedCategoryForSub) : ""}
                    onChange={(e) => {
                      const cat = categories.find(c => getId(c) === e.target.value);
                      setSelectedCategoryForSub(cat || null);
                    }}
                  >
                    <option value="">Select a category</option>
                    {categories.map(cat => (
                      <option key={getId(cat)} value={getId(cat)}>
                        {cat.name}
                      </option>
                    ))}
                  </select>
                </div>
                <Input
                  placeholder="Prompt name"
                  value={newSubcategoryName}
                  onChange={(e) => setNewSubcategoryName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleCreateSubcategory()}
                />
                <div className="flex gap-2">
                  <Button variant="outline" onClick={() => setShowNewSubcategoryDialog(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleCreateSubcategory}>
                    Create
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Tree View */}
      <div className="flex-1 overflow-y-auto p-2">
        <div className="space-y-1">
          {categories
            .filter(cat => getId(cat))
            .map((category) => {
              const categoryId = getId(category);
              const isExpanded = expandedCategories.has(categoryId);
              const isSelected = selectedCategory && getId(selectedCategory) === categoryId;
              const subcats = getSubcategoriesForCategory(categoryId);

              return (
                <div key={categoryId} className="select-none">
                  {/* Category Row */}
                  <div
                    className={`flex items-center px-2 py-1.5 rounded-md cursor-pointer transition-colors group ${
                      isSelected 
                        ? "bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300" 
                        : "hover:bg-muted text-muted-foreground"
                    }`}
                    onClick={() => handleCategoryClick(category)}
                  >
                    {/* Expand/Collapse Button */}
                    <button
                      className="mr-1 p-0.5 rounded hover:bg-muted"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleCategory(categoryId);
                      }}
                    >
                      {subcats.length > 0 ? (
                        isExpanded ? (
                          <ChevronDown className="h-3 w-3" />
                        ) : (
                          <ChevronRight className="h-3 w-3" />
                        )
                      ) : (
                        <div className="h-3 w-3" />
                      )}
                    </button>

                    {/* Category Icon */}
                    {isExpanded ? (
                      <FolderOpen className="h-4 w-4 mr-2 text-blue-500" />
                    ) : (
                      <Folder className="h-4 w-4 mr-2 text-blue-600 dark:text-blue-400" />
                    )}

                    {/* Category Name */}
                    <span className="flex-1 font-medium text-sm truncate">
                      {category.name}
                    </span>

                    {/* Prompt Count */}
                    <span className="text-xs text-blue-600 dark:text-blue-400 ml-2">
                      {subcats.length}
                    </span>
                  </div>

                  {/* Prompts (formerly subcategories) */}
                  {isExpanded && subcats.length > 0 && (
                    <div className="ml-4 mt-1 space-y-0.5">
                      {subcats.map((subcategory) => {
                        const subId = getId(subcategory);
                        const isSubSelected = selectedSubcategory && getId(selectedSubcategory) === subId;

                        return (
                          <div
                            key={subId}
                            className={`flex items-center px-2 py-1 rounded-md cursor-pointer transition-colors ${
                              isSubSelected 
                                ? "bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400" 
                                : "hover:bg-muted text-foreground"
                            }`}
                            onClick={() => handleSubcategoryClick(subcategory)}
                          >
                            {/* File Icon */}
                            <FileText className="h-3 w-3 mr-2 text-green-600 dark:text-green-400" />
                            
                            {/* Prompt Name */}
                            <span className="flex-1 text-sm truncate">
                              {subcategory.name}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-border">
        <div className="text-xs text-blue-600 dark:text-blue-400">
          {categories.length} categories • {subcategories.length} subcategories
        </div>
      </div>
    </div>
  );
}
