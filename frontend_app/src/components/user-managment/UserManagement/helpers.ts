// Utility functions for User Management components
import type { User } from "@/lib/api";
import { Shield, ShieldCheck, User as UserIcon } from "lucide-react";

export const getUserInitials = (email: string, name?: string) => {
  if (name && name.trim()) {
    return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
  }
  return email.split('@')[0].slice(0, 2).toUpperCase();
};

export const getPermissionInfo = (permission: User["permission"]) => {
  switch (permission) {
    case "Admin":
      return {
        variant: "default" as const,
        icon: Shield,
        color: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
      };
    case "Editor":
      return {
        variant: "secondary" as const,
        icon: ShieldCheck,
        color: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
      };
    case "User":
      return {
        variant: "outline" as const,
        icon: UserIcon,
        color: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
      };
    default:
      return {
        variant: "outline" as const,
        icon: UserIcon,
        color: "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200"
      };
  }
};
