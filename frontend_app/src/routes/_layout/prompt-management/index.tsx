import { PromptManagementHeader } from "@/components/prompt-management/prompt-management-header";
import { PromptManagementView } from "@/components/prompt-management/prompt-management-view";
import { createFileRoute } from "@tanstack/react-router";
import { PermissionGuard } from "@/lib/permission"; 
import { Capability } from "@/types/permissions"; 

export const Route = createFileRoute("/_layout/prompt-management/")({
  component: PromptManagementPage,
});

function PromptManagementPage() {
  return (
    <PermissionGuard requiredCapability={Capability.VIEW_TRANSCRIPTIONS}>
      <div className="space-y-8 p-4 pt-6 md:p-8">
        <div>
          <PromptManagementHeader />
          <PromptManagementView />
        </div>
        
        {/* <div className="border-t pt-8">
          <h2 className="text-xl font-bold mb-4">New Capability System Demo</h2>
          <CapabilityDemo />
        </div> */}
      </div>
    </PermissionGuard>
  );
}