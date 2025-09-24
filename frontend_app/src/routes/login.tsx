import { getStorageItem } from "@/lib/storage";
import { createFileRoute, redirect } from "@tanstack/react-router";
import { LoginForm } from "@/components/login-form";

export const Route = createFileRoute("/login")({
  beforeLoad: () => {
    const token = getStorageItem("token", "");
    if (token) {
      return redirect({ to: "/simple-upload" });
    }
  },
  component: LoginPage,
});

function LoginPage() {
  return (
    <div className="bg-background flex min-h-screen items-center justify-center p-4">
      <LoginForm />
    </div>
  );
}
