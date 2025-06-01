import { createFileRoute, redirect } from "@tanstack/react-router";

export const Route = createFileRoute("/_layout/admin/")({
  beforeLoad: () => {
    // Redirect to the all jobs page by default
    throw redirect({
      to: "/admin/all-jobs",
      replace: true
    });
  },
  component: () => null
});
