import { createFileRoute, redirect } from "@tanstack/react-router";

export const Route = createFileRoute("/_layout/user-management/")({
  beforeLoad: () => {
    // Redirect to the new admin user-management path
    throw redirect({
      to: "/admin/user-management",
      replace: true
    });
  },
  component: () => null
});