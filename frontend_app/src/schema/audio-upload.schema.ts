import { z } from "zod";

export const mediaUploadSchema = z.object({
  mediaFile: z.instanceof(File, {
    message: "Please select a file to upload.",
  }),
  promptCategory: z.string({
    required_error: "Please select a prompt category.",
  }),
  promptSubcategory: z.string({
    required_error: "Please select a prompt subcategory.",
  }),
});

export type MediaUploadValues = z.infer<typeof mediaUploadSchema>;

// Keep the old export for backward compatibility
export const audioUploadSchema = mediaUploadSchema;
export type AudioUploadValues = MediaUploadValues;
