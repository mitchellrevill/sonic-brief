import { z } from "zod";

import { categoryNameSchema } from "./common.schema";

export const subcategoryFormSchema = z.object({
  name: z.string().min(1, { message: "Subcategory name cannot be empty" }),
  categoryId: z.string({ required_error: "Please select a category" }),
  prompts: z
    .record(z.string(), z.string())
    .refine(
      (prompts) =>
        Object.entries(prompts).filter(([key]) => key.trim()).length > 0,
      {
        message: "Please add at least one prompt with a non-empty key",
      },
    )
    .refine(
      (prompts) =>
        Object.entries(prompts).every(
          ([key, value]) => key.trim().length > 0 && value.trim().length > 0,
        ),
      {
        message: "Prompt keys and values cannot be empty",
      },
    ),
});

export type SubcategoryFormValues = z.infer<typeof subcategoryFormSchema>;

export const addCategoryFormSchema = z.object({
  name: categoryNameSchema,
});

export type AddCategoryFormValues = z.infer<typeof addCategoryFormSchema>;

export const editCategoryFormSchema = z.object({
  name: categoryNameSchema,
  id: z.string().min(1, { message: "Category ID cannot be empty" }),
});

export type EditCategoryFormValues = z.infer<typeof editCategoryFormSchema>;
