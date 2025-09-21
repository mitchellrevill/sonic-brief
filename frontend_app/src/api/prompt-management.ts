import { httpClient } from "@/api/httpClient";
import {
  CATEGORIES_API,
  PROMPTS_API,
  SUBCATEGORIES_API,
  JOBS_API,
} from "@/lib/apiConstants";

interface UploadResponse {
  job_id?: string;
  status: number | string;
  message: string;
}

interface Prompt {
  [key: string]: string;
}

interface Subcategory {
  subcategory_name: string;
  subcategory_id: string;
  prompts: Prompt;
  preSessionTalkingPoints?: any[];
  inSessionTalkingPoints?: any[];
}

interface Category {
  category_name: string;
  category_id: string;
  subcategories: Array<Subcategory>;
}

interface PromptsResponse {
  status: number;
  data: Array<Category>;
}

export interface CategoryResponse {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  parent_category_id?: string | null;
}

export interface SubcategoryResponse {
  id: string;
  name: string;
  category_id: string;
  prompts: Prompt;
  preSessionTalkingPoints?: any[];
  inSessionTalkingPoints?: any[];
  created_at: number;
  updated_at: number;
}

export async function uploadFile(
  file: File,
  prompt_category_id: string,
  prompt_subcategory_id: string,
  preSessionFormData?: Record<string, any>,
): Promise<UploadResponse> {
  console.log({ file, prompt_category_id, prompt_subcategory_id, preSessionFormData });

  const formData = new FormData();
  formData.append("file", file);
  formData.append("prompt_category_id", prompt_category_id);
  formData.append("prompt_subcategory_id", prompt_subcategory_id);

  // Add pre-session form data if provided
  if (preSessionFormData && Object.keys(preSessionFormData).length > 0) {
    formData.append("pre_session_form_data", JSON.stringify(preSessionFormData));
  }

  const response = await httpClient.post(JOBS_API, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return response.data;
}

export async function fetchPrompts(): Promise<PromptsResponse> {
  const response = await httpClient.get(PROMPTS_API);

  return response.data;
}

// New functions for category management
export async function createCategory(name: string, parent_category_id?: string | null): Promise<CategoryResponse> {
  const payload: any = { name };
  if (typeof parent_category_id !== "undefined") payload.parent_category_id = parent_category_id;
  const response = await httpClient.post(CATEGORIES_API, payload);
  return response.data;
}

export async function fetchCategories(): Promise<Array<CategoryResponse>> {
  const response = await httpClient.get(CATEGORIES_API);

  return response.data;
}

export interface UpdateCategoryArgs {
  categoryId: string | undefined;
  name: string;
  parent_category_id?: string | null;
}

export async function updateCategory({
  categoryId,
  name,
  parent_category_id,
}: UpdateCategoryArgs): Promise<CategoryResponse> {
  if (!categoryId) {
    console.error("Category ID is undefined or empty");
    throw new Error("Invalid category ID. Cannot update category.");
  }

  const payload: any = { name };
  if (typeof parent_category_id !== "undefined") payload.parent_category_id = parent_category_id;
  const response = await httpClient.put(`${CATEGORIES_API}/${categoryId}`, payload);

  return response.data;
}

export async function deleteCategory(
  categoryId: string,
): Promise<CategoryResponse> {
  const response = await httpClient.delete(`${CATEGORIES_API}/${categoryId}`);

  return response.data;
}

// Functions for subcategory management

export type CreateSubcategoryArgs = {
  name: string;
  categoryId: string;
  prompts: Record<string, string>;
  preSessionTalkingPoints?: any[];
  inSessionTalkingPoints?: any[];
};

export async function createSubcategory({
  name,
  categoryId,
  prompts,
  preSessionTalkingPoints = [],
  inSessionTalkingPoints = [],
}: CreateSubcategoryArgs): Promise<SubcategoryResponse> {
  const response = await httpClient.post(SUBCATEGORIES_API, {
    name,
    category_id: categoryId,
    prompts,
    preSessionTalkingPoints,
    inSessionTalkingPoints,
  });

  return response.data;
}

export async function fetchSubcategories(
  categoryId?: string,
): Promise<Array<SubcategoryResponse>> {
  const url = categoryId
    ? `${SUBCATEGORIES_API}?category_id=${categoryId}`
    : SUBCATEGORIES_API;

  const response = await httpClient.get(url, {
    params: { category_id: categoryId },
  });

  return response.data;
}

export interface UpdateSubcategoryArgs {
  subcategoryId: string | undefined;
  name: string;
  prompts: Record<string, string>;
  preSessionTalkingPoints?: any[];
  inSessionTalkingPoints?: any[];
}

export async function updateSubcategory({
  subcategoryId,
  name,
  prompts,
  preSessionTalkingPoints = [],
  inSessionTalkingPoints = [],
}: UpdateSubcategoryArgs): Promise<SubcategoryResponse> {
  if (!subcategoryId) {
    console.error("Subcategory ID is undefined or empty");
    throw new Error("Invalid subcategory ID. Cannot update subcategory.");
  }

  const response = await httpClient.put(
    `${SUBCATEGORIES_API}/${subcategoryId}`,
    {
      name,
      prompts,
      preSessionTalkingPoints,
      inSessionTalkingPoints,
    },
  );

  return response.data;
}

export async function deleteSubcategory(
  subcategoryId: string,
): Promise<SubcategoryResponse> {
  if (!subcategoryId || typeof subcategoryId !== "string") {
    console.error("Invalid subcategory ID:", subcategoryId);
    throw new Error("Invalid subcategory ID. Cannot delete subcategory.");
  }

  const response = await httpClient.delete(
    `${SUBCATEGORIES_API}/${subcategoryId}`,
  );

  return response.data;
}
