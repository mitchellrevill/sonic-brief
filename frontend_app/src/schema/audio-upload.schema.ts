import { z } from "zod";

export const mediaUploadSchema = z.object({
  mediaFile: z.any().refine(
    (file) => {
      // Check if it's a File instance or a File-like object with required properties
      return (
        file instanceof File || 
        (file && 
         typeof file.name === 'string' && 
         typeof file.size === 'number' && 
         typeof file.type === 'string' &&
         typeof file.lastModified === 'number' &&
         file.constructor === Blob)
      );
    },
    {
      message: "Please select a file to upload.",
    }
  ),
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
