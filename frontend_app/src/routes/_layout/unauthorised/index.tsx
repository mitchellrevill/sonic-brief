import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/_layout/unauthorised/')({
  component: Unauthorized,
})

function Unauthorized() {
  return (
    <div className="p-8 text-center text-red-600">
      <h1 className="text-2xl font-bold">Unauthorized</h1>
      <p>You do not have permission to view this page.</p>
    </div>
  );
}
