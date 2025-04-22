import type { AddCategoryFormValues } from "@/schema/prompt-management.schema";
import { useState } from "react";
import { createCategory } from "@/api/prompt-management";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbPage,
} from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { getPromptManagementCategoriesQuery } from "@/queries/prompt-management.query";
import { queryClient } from "@/queryClient";
import { addCategoryFormSchema } from "@/schema/prompt-management.schema";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { PlusCircle } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

export function PromptManagementHeader() {
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const form = useForm<AddCategoryFormValues>({
    resolver: zodResolver(addCategoryFormSchema),
    defaultValues: {
      name: "",
    },
  });

  const { mutate: addCategoryMutation, isPending } = useMutation({
    mutationKey: ["sonic-brief/prompt-management/add-category"],
    mutationFn: (name: string) => createCategory(name),
    onMutate: async (newName) => {
      await queryClient.cancelQueries({
        queryKey: getPromptManagementCategoriesQuery().queryKey,
      });

      const previousCategories = queryClient.getQueryData(
        getPromptManagementCategoriesQuery().queryKey,
      );

      queryClient.setQueryData(
        getPromptManagementCategoriesQuery().queryKey,
        (old) => {
          // @ts-expect-error - old can be undefined and typescript is not happy about it
          return [...old, { id: "new-category", name: newName }];
        },
      );

      setIsDialogOpen(false);

      return { previousCategories };
    },

    onError: (error, _newName, context) => {
      queryClient.setQueryData(
        getPromptManagementCategoriesQuery().queryKey,
        context?.previousCategories,
      );

      toast.error("Error", {
        description:
          error instanceof Error ? error.message : "Failed to create category",
      });
    },
    onSuccess: () => {
      toast.success("Success", {
        description: "Category created successfully",
      });
      form.reset();
    },
  });

  const onSubmit = (values: AddCategoryFormValues) => {
    addCategoryMutation(values.name);
  };

  return (
    <>
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <h2 className="text-2xl font-semibold tracking-tight">
            Prompt Management
          </h2>
          <Breadcrumb>
            <BreadcrumbItem>
              <BreadcrumbLink href="/">Home</BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbItem>
              <BreadcrumbPage>Prompt Management</BreadcrumbPage>
            </BreadcrumbItem>
          </Breadcrumb>
          <p className="text-muted-foreground text-sm">
            Manage categories, subcategories, and prompts for your AI system.
          </p>
        </div>
        <Button onClick={() => setIsDialogOpen(true)}>
          <PlusCircle className="me-2 h-4 w-4" />
          Add Category
        </Button>
      </div>

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Category</DialogTitle>
          </DialogHeader>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Category Name</FormLabel>
                    <FormControl>
                      <Input
                        {...field}
                        placeholder="Enter category name"
                        disabled={isPending}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    form.reset();
                    setIsDialogOpen(false);
                  }}
                  disabled={isPending}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={isPending}>
                  {isPending ? "Creating..." : "Create Category"}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
    </>
  );
}
