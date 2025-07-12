import { PromptManagementPage } from "@/components/prompt-management/prompt-management-page";
import { createFileRoute } from "@tanstack/react-router";
import { PermissionGuard } from "@/lib/permission"; 
import { Capability } from "@/types/permissions"; 

export const Route = createFileRoute("/_layout/prompt-management/")({
  component: PromptManagementRoute,
});

function PromptManagementRoute() {
  return (
    <PermissionGuard requiredCapability={Capability.VIEW_TRANSCRIPTIONS}>
      <div className="flex-1 space-y-4 md:p-8">
        <PromptManagementPage />
      </div>
    </PermissionGuard>
  );
}