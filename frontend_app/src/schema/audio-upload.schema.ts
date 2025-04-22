import { z } from "zod";

export const audioUploadSchema = z.object({
  audioFile: z.instanceof(File),
  promptCategory: z.string({
    required_error: "Please select a prompt category.",
  }),
  promptSubcategory: z.string({
    required_error: "Please select a prompt subcategory.",
  }),
});

export type AudioUploadValues = z.infer<typeof audioUploadSchema>;
