import { PromptManagementHeader } from "@/components/prompt-management/prompt-management-header";
import { PromptManagementView } from "@/components/prompt-management/prompt-management-view";
import { createFileRoute } from "@tanstack/react-router";
import { PermissionGuard } from "@/lib/permission"; 

export const Route = createFileRoute("/_layout/prompt-management/")({
  component: PromptManagementPage,
});

function PromptManagementPage() {
  return (
    <PermissionGuard required={["Admin"]}>
      <div className="space-y-4 p-4 pt-6 md:p-8">
        <PromptManagementHeader />
        <PromptManagementView />
      </div>
    </PermissionGuard>
  );
}