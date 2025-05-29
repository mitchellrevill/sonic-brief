import { z } from "zod";

export const mediaUploadSchema = z.object({
  mediaFile: z.instanceof(File, {
    message: "Please select a file to upload.",
  }).optional(),
  textContent: z.string().optional(),
  promptCategory: z.string({
    required_error: "Please select a prompt category.",
  }),
  promptSubcategory: z.string({
    required_error: "Please select a prompt subcategory.",
  }),
}).refine(
  (data) => data.mediaFile || (data.textContent && data.textContent.trim().length > 0),
  {
    message: "Please provide either a file or text content.",
    path: ["mediaFile"],
  }
);

export type MediaUploadValues = z.infer<typeof mediaUploadSchema>;

// Keep the old export for backward compatibility
export const audioUploadSchema = mediaUploadSchema;
export type AudioUploadValues = MediaUploadValues;
