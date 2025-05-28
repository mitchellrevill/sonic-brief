import { useState } from "react"
import { PlusCircle } from "lucide-react"
import { usePromptManagement } from "./prompt-management-context"
import { Button } from "@/components/ui/button"
import { Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbPage } from "@/components/ui/breadcrumb"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useToast } from "@/components/ui/use-toast"

export function PromptManagementHeader() {
  const { addCategory, loading } = usePromptManagement()
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [categoryName, setCategoryName] = useState("")
  const { toast } = useToast()

  const handleAddCategory = async () => {
    if (!categoryName.trim()) {
      toast({
        title: "Error",
        description: "Category name cannot be empty",
        variant: "destructive",
      })
      return
    }

    try {
      await addCategory(categoryName)
      toast({
        title: "Success",
        description: "Category created successfully",
      })
      setCategoryName("")
      setIsDialogOpen(false)
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to create category",
        variant: "destructive",
      })
    }
  }

  return (
    <>
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between px-2 py-2 md:px-4 md:py-3">
        <div className="space-y-1 text-center md:text-left">
          <h2 className="text-lg md:text-2xl font-semibold tracking-tight">Prompt Management</h2>
          <Breadcrumb className="justify-center md:justify-start flex flex-wrap">
            <BreadcrumbItem>
              <BreadcrumbLink href="/">Home</BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbItem>
              <BreadcrumbPage>Prompt Management</BreadcrumbPage>
            </BreadcrumbItem>
          </Breadcrumb>
          <p className="text-muted-foreground text-xs md:text-sm">
            Manage categories, subcategories, and prompts for your AI system.
          </p>
        </div>
        <Button onClick={() => setIsDialogOpen(true)} className="w-full md:w-auto" size="sm">
          <PlusCircle className="mr-2 h-4 w-4" />
          <span className="hidden sm:inline">Add Category</span>
        </Button>
      </div>

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Category</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div key="category-name-field" className="grid gap-2">
              <Label htmlFor="name">Category Name</Label>
              <Input
                id="name"
                value={categoryName}
                onChange={(e) => setCategoryName(e.target.value)}
                placeholder="Enter category name"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleAddCategory} disabled={loading}>
              {loading ? "Creating..." : "Create Category"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

