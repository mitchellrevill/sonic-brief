import { createFileRoute } from "@tanstack/react-router";
import { UserProfile } from "@/components/user-profile/user-profile";

export const Route = createFileRoute("/_layout/profile/")({
  component: UserProfile,
});
