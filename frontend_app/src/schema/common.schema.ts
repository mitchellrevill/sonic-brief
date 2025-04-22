import { z } from "zod";

export const emailSchema = z
  .string()
  .email({ message: "Invalid email address" });

export const passwordSchema = z
  .string()
  .min(6, { message: "Password must be at least 6 characters" });

export const categoryNameSchema = z
  .string()
  .min(1, { message: "Category name cannot be empty" })
  .max(50, { message: "Category name cannot exceed 50 characters" });

export type CategoryName = z.infer<typeof categoryNameSchema>;
