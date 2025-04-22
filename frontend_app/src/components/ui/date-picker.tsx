import type { ControllerRenderProps } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import {
  FormControl,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { format } from "date-fns";
import { CalendarIcon } from "lucide-react";

interface DatePickerProps {
  field: ControllerRenderProps<any, any>;
  label: string;
  placeholder?: string;
}

export function DatePicker({
  field,
  label,
  placeholder = "Pick a date",
}: DatePickerProps) {
  const selectedDate = field.value ? new Date(field.value) : undefined;

  return (
    <FormItem className="flex flex-col">
      <FormLabel>{label}</FormLabel>
      <Popover>
        <PopoverTrigger asChild>
          <FormControl>
            <Button
              variant="outline"
              className={cn(
                "justify-start text-left font-normal",
                !field.value && "text-muted-foreground",
              )}
            >
              <CalendarIcon className="me-2 h-4 w-4" />
              {field.value ? (
                format(new Date(field.value), "yyyy-MM-dd")
              ) : (
                <span>{placeholder}</span>
              )}
            </Button>
          </FormControl>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            mode="single"
            selected={selectedDate}
            onSelect={(date) => {
              const formattedDate = date ? format(date, "yyyy-MM-dd") : "";
              field.onChange(formattedDate);
            }}
            initialFocus
          />
        </PopoverContent>
      </Popover>
      <FormMessage />
    </FormItem>
  );
}
