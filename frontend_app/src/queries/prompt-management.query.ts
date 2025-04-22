import { fetchCategories, fetchSubcategories } from "@/api/prompt-management";
import { queryOptions } from "@tanstack/react-query";

export function getPromptManagementCategoriesQuery() {
  return queryOptions({
    queryKey: ["sonic-brief", "prompt-management", "categories"],
    queryFn: () => fetchCategories(),
  });
}

export function getPromptManagementSubcategoriesQuery() {
  return queryOptions({
    queryKey: ["sonic-brief", "prompt-management", "subcategories"],
    queryFn: () => fetchSubcategories(),
  });
}
