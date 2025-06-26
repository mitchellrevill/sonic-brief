import { Button } from "@/components/ui/button";
import { FileDown } from "lucide-react";
import { useState } from "react";
import { exportUsersCSV } from "@/lib/api";
import { toast } from "sonner";

export function ExportCSVButton() {
  const [exportLoading, setExportLoading] = useState(false);

  const handleExportCSV = async () => {
    setExportLoading(true);
    try {
      const blob = await exportUsersCSV();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = `sonic-brief-users-${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success("Users exported successfully");
    } catch (error) {
      console.error("Export failed:", error);
      toast.error("Failed to export users");
    } finally {
      setExportLoading(false);
    }
  };

  return (
    <Button 
      onClick={handleExportCSV} 
      disabled={exportLoading}
      variant="outline"
      className="flex items-center gap-2"
    >
      {exportLoading ? (
        <>
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
          Exporting...
        </>
      ) : (
        <>
          <FileDown className="h-4 w-4" />
          Export CSV
        </>
      )}
    </Button>
  );
}
