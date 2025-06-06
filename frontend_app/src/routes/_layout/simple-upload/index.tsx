import { createFileRoute } from '@tanstack/react-router'
import { SimpleUploadFlow } from '@/components/simple-ui/SimpleUploadFlow'

export const Route = createFileRoute('/_layout/simple-upload/')({
  component: RouteComponent,
})

function RouteComponent() {
  return <SimpleUploadFlow />
}
