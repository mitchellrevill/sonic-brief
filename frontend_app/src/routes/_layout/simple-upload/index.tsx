import { createFileRoute } from '@tanstack/react-router'
import { SimpleUploadFlow } from '@/components/simple-ui/SimpleUploadFlow'
import { PermissionGuard } from "@/lib/permission";
import { Capability } from "@/types/permissions";

export const Route = createFileRoute('/_layout/simple-upload/')({
  component: RouteComponent,
})

function RouteComponent() {
  return (
    <PermissionGuard requiredCapability={Capability.CREATE_TRANSCRIPTIONS}>
      <SimpleUploadFlow />
    </PermissionGuard>
  );
}
