import { AppSidebar } from "@/components/app-sidebar";
import { ThemeToggle } from "@/components/theme-toggle";
import { getStorageItem } from "@/lib/storage";
import { createFileRoute, Outlet, redirect } from "@tanstack/react-router";

export const Route = createFileRoute("/_layout")({
  beforeLoad: () => {
    const token = getStorageItem("token", "");
    if (!token) {
      return redirect({ to: "/login" });
    }
  },
  component: RouteComponent,
});

function RouteComponent() {
  return (
    <div className="flex min-h-screen">
      <AppSidebar />
      <main className="min-h-screen flex-1">
        <div className="container mx-auto p-4">
          <div className="mb-4 flex justify-end">
            <ThemeToggle />
          </div>
          <Outlet />
        </div>
      </main>
    </div>
  );
}
