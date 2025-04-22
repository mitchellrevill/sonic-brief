import type { AudioUploadValues } from "@/schema/audio-upload.schema";
import { useCallback, useState } from "react";
import { fetchPrompts, uploadFile } from "@/api/prompt-management";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { audioUploadSchema } from "@/schema/audio-upload.schema";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Loader2, RefreshCcw } from "lucide-react";
import { useForm } from "react-hook-form";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { toast } from "sonner";

export function AudioUploadForm() {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedSubcategory, setSelectedSubcategory] = useState<string | null>(
    null,
  );

  const form = useForm<AudioUploadValues>({
    resolver: zodResolver(audioUploadSchema),
  });

  const {
    data: categories,
    isLoading: isLoadingCategories,
    refetch: refetchCategories,
  } = useQuery({
    queryKey: ["sonic-brief", "prompts"],
    queryFn: fetchPrompts,
    select: (data) => data.data,
  });

  const { mutateAsync: uploadAudioMutation, isPending: isUploading } =
    useMutation({
      mutationKey: ["sonic-brief/upload-audio"],
      mutationFn: async (values: AudioUploadValues) =>
        await uploadFile(
          values.audioFile,
          values.promptCategory,
          values.promptSubcategory,
        ),
      onSuccess: (data) =>
        toast.success(`File uploaded successfully! Job ID: ${data.job_id}`),
      onError: () =>
        toast.error(
          "There was an error uploading your file. Please try again.",
        ),
    });

  const onSubmit = useCallback(
    async (values: AudioUploadValues) => {
      await uploadAudioMutation(values);
      form.reset({
        audioFile: undefined,
        promptCategory: "",
        promptSubcategory: "",
      });
    },
    [form, uploadAudioMutation],
  );

  const selectedCategoryData = categories?.find(
    (cat) => cat.category_id === selectedCategory,
  );
  const selectedSubcategoryData = selectedCategoryData?.subcategories.find(
    (sub) => sub.subcategory_id === selectedSubcategory,
  );

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
        <FormField
          control={form.control}
          name="audioFile"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Audio File</FormLabel>
              <FormControl>
                <Input
                  type="file"
                  accept="audio/*"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    field.onChange(file);
                  }}
                />
              </FormControl>
              <FormDescription>
                Upload an audio file (no size limit)
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="promptCategory"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Prompt Category</FormLabel>
              <div className="flex items-center space-x-2">
                <Select
                  value={selectedCategory || ""}
                  onValueChange={(value) => {
                    field.onChange(value);
                    setSelectedCategory(value);
                    setSelectedSubcategory(null);
                    form.setValue("promptSubcategory", "");
                  }}
                  disabled={isLoadingCategories}
                >
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="Select a category" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {categories?.map((category) => (
                      <SelectItem
                        key={category.category_id}
                        value={category.category_id}
                      >
                        {category.category_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => refetchCategories()}
                  disabled={isLoadingCategories}
                >
                  <RefreshCcw className="mr-2 h-4 w-4" />
                  {isLoadingCategories ? "Refreshing..." : "Refresh"}
                </Button>
              </div>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="promptSubcategory"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Prompt Subcategory</FormLabel>
              <Select
                value={selectedSubcategory || ""}
                onValueChange={(value) => {
                  field.onChange(value);
                  setSelectedSubcategory(value);
                }}
                disabled={!selectedCategory}
              >
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a subcategory" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {selectedCategoryData?.subcategories.map((subcategory) => (
                    <SelectItem
                      key={subcategory.subcategory_id}
                      value={subcategory.subcategory_id}
                    >
                      {subcategory.subcategory_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />
        {selectedSubcategoryData && (
          <Card>
            <CardHeader>
              <CardTitle className="font-bold">
                {selectedSubcategoryData.subcategory_name}
              </CardTitle>
              <CardDescription>
                Prompt details for the selected subcategory
              </CardDescription>
            </CardHeader>
            <CardContent className="max-h-60 overflow-auto p-4">
              {Object.entries(selectedSubcategoryData.prompts).map(
                ([key, value]) => (
                  <div key={key} className="mb-4">
                    <h4 className="text-lg font-semibold">{key}</h4>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {value}
                    </ReactMarkdown>
                  </div>
                ),
              )}
            </CardContent>
          </Card>
        )}
        <Button type="submit" disabled={isUploading || !form.formState.isValid}>
          {isUploading ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            "Upload and Process"
          )}
        </Button>
      </form>
    </Form>
  );
}
