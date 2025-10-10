import { Users } from "lucide-react";
import { SmartBreadcrumb } from "@/components/ui/smart-breadcrumb";
import { useBreadcrumbs } from "@/hooks/use-breadcrumbs";

// UI controls were removed; keep props for compatibility

interface UserManagementHeaderProps {
  onAddUser?: () => void;
  onExportCSV?: () => void;
}

export function UserManagementHeader({ onAddUser, onExportCSV }: UserManagementHeaderProps) {
  // Keep props referenced for compatibility (they may be used elsewhere).
  void onAddUser;
  void onExportCSV;

  const breadcrumbs = useBreadcrumbs();

  return (
    <div>
      <div className="container mx-auto px-4 py-6">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-zinc-200/70 text-zinc-700 dark:bg-zinc-700/60 dark:text-zinc-100">
            <Users className="h-6 w-6" />
          </div>
          <div className="space-y-1">
            <h1 className="text-2xl font-bold bg-gradient-to-r from-zinc-800 to-zinc-600 dark:from-zinc-200 dark:to-zinc-400 bg-clip-text text-transparent">
              User Management
            </h1>
            <SmartBreadcrumb items={breadcrumbs} />
            <p className="text-muted-foreground">
              Monitor user activity, manage permissions, and track system analytics
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
