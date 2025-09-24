import { useState, useEffect } from "react";
import { ChevronDown, ChevronRight, FolderOpen, Folder, FileText, Plus, MoreHorizontal, Trash2} from "lucide-react";
import { usePromptManagement } from "./prompt-management-context";
import { useCapabilityGuard } from "@/hooks/usePermissions";
import { Capability } from "@/types/permissions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { toast } from "sonner";

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
    removeCategory,
    removeSubcategory,
  } = usePromptManagement();

  const guard = useCapabilityGuard();

  // Collapsible state management
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());
  const [showNewCategoryDialog, setShowNewCategoryDialog] = useState(false);
  const [parentForNewCategory, setParentForNewCategory] = useState<string | null>(null);
  const [showNewSubcategoryDialog, setShowNewSubcategoryDialog] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState("");
  const [newSubcategoryName, setNewSubcategoryName] = useState("");
  const [selectedCategoryForSub, setSelectedCategoryForSub] = useState<any>(null);
  
  // Delete dialog state
  const [showDeleteCategoryDialog, setShowDeleteCategoryDialog] = useState(false);
  const [showDeleteSubcategoryDialog, setShowDeleteSubcategoryDialog] = useState(false);
  const [categoryToDelete, setCategoryToDelete] = useState<any>(null);
  const [subcategoryToDelete, setSubcategoryToDelete] = useState<any>(null);

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

  // Build one-level tree using server-provided `parent_category_id` on categories.
  const rootCategories = categories.filter(cat => !cat.parent_category_id)
  const rootSubcategories = subcategories.filter(sub => !sub.category_id)

  const childrenByParent: Record<string, Array<any>> = {}
  categories.forEach(cat => {
    const parent = (cat as any).parent_category_id
    if (parent) {
      childrenByParent[parent] = childrenByParent[parent] || []
      childrenByParent[parent].push(cat)
    }
  })

  const handleCreateCategory = async () => {
    if (!newCategoryName.trim()) return;
    
    try {
      // Use nested category creation to allow optional parent
      // @ts-ignore - provider exposes addNestedCategory when available
      await (addCategory as any)(newCategoryName.trim(), parentForNewCategory || null);
      setNewCategoryName("");
      setShowNewCategoryDialog(false);
      setParentForNewCategory(null);
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

  const handleDeleteCategory = async () => {
    if (!categoryToDelete) return;
    
    try {
      await removeCategory(getId(categoryToDelete));
      toast.success("Category deleted successfully");
      setShowDeleteCategoryDialog(false);
      setCategoryToDelete(null);
      
      // Clear selection if deleted category was selected
      if (selectedCategory && getId(selectedCategory) === getId(categoryToDelete)) {
        setSelectedCategory(null);
        setSelectedSubcategory(null);
      }
    } catch (error) {
      console.error("Failed to delete category:", error);
      toast.error("Failed to delete category");
    }
  };

  const handleDeleteSubcategory = async () => {
    if (!subcategoryToDelete) return;
    
    try {
      await removeSubcategory(getId(subcategoryToDelete));
      toast.success("Subcategory deleted successfully");
      setShowDeleteSubcategoryDialog(false);
      setSubcategoryToDelete(null);
      
      // Clear selection if deleted subcategory was selected
      if (selectedSubcategory && getId(selectedSubcategory) === getId(subcategoryToDelete)) {
        setSelectedSubcategory(null);
      }
    } catch (error) {
      console.error("Failed to delete subcategory:", error);
      toast.error("Failed to delete subcategory");
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
            Prompts & Folders
          </h3>
        </div>
        <div className="flex gap-2">
          {/* Show create controls only if user has prompt create/edit capability */}
          {guard.hasAnyCapability([Capability.CAN_CREATE_PROMPTS, Capability.CAN_EDIT_PROMPTS]) && (
            <>
              <Dialog open={showNewCategoryDialog} onOpenChange={setShowNewCategoryDialog}>
                <DialogTrigger asChild>
                  <Button size="sm" variant="outline" className="flex-1">
                    <Plus className="h-3 w-3 mr-1" />
                    Folder
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Create Folder</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4">
                    <div>
                      <label className="text-sm font-medium">Parent folder (optional)</label>
                      <select
                        className="w-full mt-1 p-2 border rounded-md"
                        value={parentForNewCategory || ""}
                        onChange={(e) => setParentForNewCategory(e.target.value || null)}
                      >
                        <option value="">No parent (top-level)</option>
                        {categories.map(cat => (
                          <option key={getId(cat)} value={getId(cat)}>{cat.name}</option>
                        ))}
                      </select>
                    </div>
                    <Input
                      placeholder="Folder name"
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
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Create Prompt</DialogTitle>
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
                        <option value="">Select a folder</option>
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
            </>
          )}
        </div>
      </div>

      {/* Tree View */}
      <div className="flex-1 overflow-y-auto p-2">
        <div className="space-y-0.5">
          {rootCategories.map((category) => {
            const categoryId = getId(category)
            const isExpanded = expandedCategories.has(categoryId)
            const isSelected = selectedCategory && getId(selectedCategory) === categoryId
            const subcats = getSubcategoriesForCategory(categoryId)
            const childCats = childrenByParent[categoryId] || []

            return (
              <div key={categoryId} className="select-none">
                <div
                  className={`flex items-center px-3 py-2 rounded-lg cursor-pointer transition-all duration-200 group ${
                    isSelected
                      ? "bg-gray-100 dark:bg-gray-900/50 text-gray-700 dark:text-gray-300 shadow-sm"
                      : "hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300"
                  }`}
                >
                  <button
                    className="mr-2 p-1 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                    onClick={(e) => {
                      e.stopPropagation()
                      toggleCategory(categoryId)
                    }}
                  >
                    {subcats.length + childCats.length > 0 ? (
                      isExpanded ? (
                        <ChevronDown className="h-3.5 w-3.5 text-gray-500 dark:text-gray-400" />
                      ) : (
                        <ChevronRight className="h-3.5 w-3.5 text-gray-500 dark:text-gray-400" />
                      )
                    ) : (
                      <div className="h-3.5 w-3.5" />
                    )}
                  </button>

                  <div 
                    className="flex items-center flex-1 min-w-0"
                    onClick={() => handleCategoryClick(category)}
                  >
                    {isExpanded ? (
                      <FolderOpen className="h-4 w-4 mr-3 text-gray-500 dark:text-gray-400 flex-shrink-0" />
                    ) : (
                      <Folder className="h-4 w-4 mr-3 text-gray-600 dark:text-gray-400 flex-shrink-0" />
                    )}

                    <span className="flex-1 font-medium text-sm truncate">{category.name}</span>

                    <span className="text-xs bg-gray-100 dark:bg-gray-900/50 text-gray-600 dark:text-gray-400 px-2 py-1 rounded-full ml-3 flex-shrink-0">
                      {subcats.length + childCats.length}
                    </span>
                  </div>

                  {guard.hasCapability(Capability.CAN_DELETE_PROMPTS) && (
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <button 
                          className="p-1.5 opacity-0 group-hover:opacity-100 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-md transition-all duration-200 ml-2"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <MoreHorizontal className="h-3.5 w-3.5 text-gray-500 dark:text-gray-400" />
                        </button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-48">
                        <DropdownMenuItem onClick={() => {
                          setSelectedCategoryForSub(category);
                          setShowNewSubcategoryDialog(true);
                        }}>
                          <Plus className="h-4 w-4 mr-2" />
                          Add prompt
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem onClick={() => {
                          setCategoryToDelete(category);
                          setShowDeleteCategoryDialog(true);
                        }}>
                          <Trash2 className="h-4 w-4 mr-2" />
                          Delete Category
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  )}
                </div>

                {isExpanded && (
                  <div className="ml-6 mt-2 space-y-1 border-l-2 border-gray-200 dark:border-gray-700 pl-4">
                    {/* Child categories (folders) */}
                    {childCats.map((child) => {
                      const childId = getId(child)
                      const isChildSelected = selectedCategory && getId(selectedCategory) === childId
                      const isChildExpanded = expandedCategories.has(childId)
                      const childSubcats = getSubcategoriesForCategory(childId)

                      return (
                        <div key={childId} className="select-none">
                          <div
                            className={`flex items-center px-3 py-1.5 rounded-md cursor-pointer transition-all duration-200 group ${
                              isChildSelected ? "bg-gray-50 dark:bg-gray-900/30 text-gray-600 dark:text-gray-400 shadow-sm" : "hover:bg-gray-50 dark:hover:bg-gray-800/50 text-gray-600 dark:text-gray-400"
                            }`}
                          >
                            <button
                              className="mr-2 p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                              onClick={(e) => {
                                e.stopPropagation()
                                toggleCategory(childId)
                              }}
                            >
                              {childSubcats.length > 0 ? (
                                isChildExpanded ? (
                                  <ChevronDown className="h-3 w-3 text-gray-500 dark:text-gray-400" />
                                ) : (
                                  <ChevronRight className="h-3 w-3 text-gray-500 dark:text-gray-400" />
                                )
                              ) : (
                                <div className="h-3 w-3" />
                              )}
                            </button>

                            <div 
                              className="flex items-center flex-1 min-w-0"
                              onClick={() => handleCategoryClick(child)}
                            >
                              {isChildExpanded ? (
                                <FolderOpen className="h-3.5 w-3.5 mr-2 text-gray-500 dark:text-gray-400 flex-shrink-0" />
                              ) : (
                                <Folder className="h-3.5 w-3.5 mr-2 text-gray-500 dark:text-gray-400 flex-shrink-0" />
                              )}
                              <span className="flex-1 text-sm truncate font-medium">{child.name}</span>
                              <span className="text-xs bg-gray-50 dark:bg-gray-900/30 text-gray-600 dark:text-gray-400 px-1.5 py-0.5 rounded ml-2 flex-shrink-0">
                                {childSubcats.length}
                              </span>
                            </div>
                            
                            {guard.hasCapability(Capability.CAN_DELETE_PROMPTS) && (
                              <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                  <button 
                                    className="p-1 opacity-0 group-hover:opacity-100 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-all duration-200 ml-1"
                                    onClick={(e) => e.stopPropagation()}
                                  >
                                    <MoreHorizontal className="h-3 w-3 text-gray-500 dark:text-gray-400" />
                                  </button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end" className="w-48">
                                  <DropdownMenuItem onClick={() => {
                                    setSelectedCategoryForSub(child);
                                    setShowNewSubcategoryDialog(true);
                                  }}>
                                    <Plus className="h-4 w-4 mr-2" />
                                    Add prompt
                                  </DropdownMenuItem>
                                  <DropdownMenuSeparator />
                                  <DropdownMenuItem onClick={() => {
                                    setCategoryToDelete(child);
                                    setShowDeleteCategoryDialog(true);
                                  }}>
                                    <Trash2 className="h-4 w-4 mr-2" />
                                    Delete Category
                                  </DropdownMenuItem>
                                </DropdownMenuContent>
                              </DropdownMenu>
                            )}
                          </div>

                          {/* Prompts under child category */}
                          {isChildExpanded && childSubcats.length > 0 && (
                            <div className="ml-4 mt-2 space-y-1">
                              {childSubcats.map((subcategory) => {
                                const subId = getId(subcategory)
                                const isSubSelected = selectedSubcategory && getId(selectedSubcategory) === subId

                                return (
                                  <div
                                    key={subId}
                                    className={`flex items-center px-3 py-1.5 rounded-md cursor-pointer transition-all duration-200 group ${
                                      isSubSelected ? "bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 shadow-sm" : "hover:bg-gray-50 dark:hover:bg-gray-800/50 text-gray-600 dark:text-gray-400"
                                    }`}
                                  >
                                    <div 
                                      className="flex items-center flex-1 min-w-0"
                                      onClick={() => handleSubcategoryClick(subcategory)}
                                    >
                                      <FileText className="h-3.5 w-3.5 mr-3 text-green-600 dark:text-green-400 flex-shrink-0" />
                                      <span className="flex-1 text-sm truncate">{subcategory.name}</span>
                                    </div>
                                    
                                    {guard.hasCapability(Capability.CAN_DELETE_PROMPTS) && (
                                      <DropdownMenu>
                                        <DropdownMenuTrigger asChild>
                                          <button 
                                            className="p-1 opacity-0 group-hover:opacity-100 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-all duration-200 ml-1"
                                            onClick={(e) => e.stopPropagation()}
                                          >
                                            <MoreHorizontal className="h-3 w-3 text-gray-500 dark:text-gray-400" />
                                          </button>
                                        </DropdownMenuTrigger>
                                        <DropdownMenuContent align="end" className="w-48">
                                          <DropdownMenuItem onClick={() => {
                                            setSubcategoryToDelete(subcategory);
                                            setShowDeleteSubcategoryDialog(true);
                                          }}>
                                            <Trash2 className="h-4 w-4 mr-2" />
                                            Delete Subcategory
                                          </DropdownMenuItem>
                                        </DropdownMenuContent>
                                      </DropdownMenu>
                                    )}
                                  </div>
                                )
                              })}
                            </div>
                          )}
                        </div>
                      )
                    })}

                    {/* Prompts directly under root category */}
                    {subcats.length > 0 && (
                      <div className="ml-4 mt-2 space-y-1">
                        {subcats.map((subcategory) => {
                          const subId = getId(subcategory)
                          const isSubSelected = selectedSubcategory && getId(selectedSubcategory) === subId

                          return (
                            <div
                              key={subId}
                              className={`flex items-center px-3 py-1.5 rounded-md cursor-pointer transition-all duration-200 group ${
                                isSubSelected ? "bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 shadow-sm" : "hover:bg-gray-50 dark:hover:bg-gray-800/50 text-gray-600 dark:text-gray-400"
                              }`}
                            >
                              <div 
                                className="flex items-center flex-1 min-w-0"
                                onClick={() => handleSubcategoryClick(subcategory)}
                              >
                                <FileText className="h-3.5 w-3.5 mr-3 text-green-600 dark:text-green-400 flex-shrink-0" />
                                <span className="flex-1 text-sm truncate">{subcategory.name}</span>
                              </div>
                              
                              {guard.hasCapability(Capability.CAN_DELETE_PROMPTS) && (
                                <DropdownMenu>
                                  <DropdownMenuTrigger asChild>
                                    <button 
                                      className="p-1 opacity-0 group-hover:opacity-100 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-all duration-200 ml-1"
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      <MoreHorizontal className="h-3 w-3 text-gray-500 dark:text-gray-400" />
                                    </button>
                                  </DropdownMenuTrigger>
                                  <DropdownMenuContent align="end" className="w-48">
                                    <DropdownMenuItem onClick={() => {
                                      setSubcategoryToDelete(subcategory);
                                      setShowDeleteSubcategoryDialog(true);
                                    }}>
                                      <Trash2 className="h-4 w-4 mr-2" />
                                      Delete Subcategory
                                    </DropdownMenuItem>
                                  </DropdownMenuContent>
                                </DropdownMenu>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}

          {/* Root level subcategories (prompts without categories) */}
          {rootSubcategories.map((subcategory) => {
            const subId = getId(subcategory)
            const isSubSelected = selectedSubcategory && getId(selectedSubcategory) === subId

            return (
              <div
                key={subId}
                className={`flex items-center px-3 py-2 rounded-lg cursor-pointer transition-all duration-200 group ${
                  isSubSelected ? "bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 shadow-sm" : "hover:bg-gray-50 dark:hover:bg-gray-800/50 text-gray-600 dark:text-gray-400"
                }`}
              >
                <div 
                  className="flex items-center flex-1 min-w-0"
                  onClick={() => handleSubcategoryClick(subcategory)}
                >
                  <FileText className="h-4 w-4 mr-3 text-green-600 dark:text-green-400 flex-shrink-0" />
                  <span className="flex-1 text-sm truncate">{subcategory.name}</span>
                </div>
                
                {guard.hasCapability(Capability.CAN_DELETE_PROMPTS) && (
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <button 
                        className="p-1.5 opacity-0 group-hover:opacity-100 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-md transition-all duration-200 ml-2"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <MoreHorizontal className="h-3.5 w-3.5 text-gray-500 dark:text-gray-400" />
                      </button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-48">
                      <DropdownMenuItem onClick={() => {
                        setSubcategoryToDelete(subcategory);
                        setShowDeleteSubcategoryDialog(true);
                      }}>
                        <Trash2 className="h-4 w-4 mr-2" />
                        Delete Template
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-border">
        <div className="text-xs text-blue-600 dark:text-blue-400">
          {categories.length} categories • {subcategories.length} subcategories
        </div>
      </div>

      {/* Delete Category Dialog */}
      <AlertDialog open={showDeleteCategoryDialog} onOpenChange={setShowDeleteCategoryDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Category</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the category "{categoryToDelete?.name}"? This action cannot be undone and will also delete all subcategories and prompts within this category.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteCategory} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete Subcategory Dialog */}
      <AlertDialog open={showDeleteSubcategoryDialog} onOpenChange={setShowDeleteSubcategoryDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Subcategory</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the subcategory "{subcategoryToDelete?.name}"? This action cannot be undone and will delete all prompts within this subcategory.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteSubcategory} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
