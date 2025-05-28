import type { LinkOptions } from "@tanstack/react-router";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { getStorageItem, setStorageItem } from "@/lib/storage";
import { cn } from "@/lib/utils";
import { Link, useRouter } from "@tanstack/react-router";
import {
  ChevronLeft,
  ChevronRight,
  FileAudio,
  FileText,
  LogOut,
  Mic,
  UserCog
} from "lucide-react";

interface MenuItem {
  icon: React.ElementType;
  label: string;
  to: LinkOptions["to"];
}

const menuItems: Array<MenuItem> = [
  { icon: Mic, label: "Audio Upload", to: "/audio-upload" },
  { icon: FileAudio, label: "Audio Recordings", to: "/audio-recordings" },
  { icon: FileText, label: "Prompt Management", to: "/prompt-management" },
  { icon: UserCog, label: "User Management", to: "/user-management" }
];

interface AppSidebarProps {
  children?: React.ReactNode;
}

export function AppSidebar({ children }: AppSidebarProps) {
  const [isOpen, setIsOpen] = useState(() => {
    const saved = getStorageItem("sidebarOpen", "true");
    return JSON.parse(saved);
  });

  const router = useRouter();

  const toggleSidebar = () => {
    const newState = !isOpen;
    setIsOpen(newState);
    setStorageItem("sidebarOpen", JSON.stringify(newState));
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    router.navigate({ to: "/login" });
  };

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      {/* Sidebar: vertical on md+, horizontal top bar on mobile */}
      <div
        className={cn(
          // On mobile: row, full width, height 16; on md+: col, fixed left, full height, width 64 or 16
          "fixed md:static z-40 flex bg-gray-900 text-white transition-all duration-300 ease-in-out",
          "top-0 left-0 w-full h-16 flex-row md:w-64 md:h-full md:flex-col md:w-64 md:top-auto md:left-auto",
          isOpen ? "md:w-64" : "md:w-16",
        )}
        style={{ minWidth: 0 }}
      >
        <Button
          variant="ghost"
          className={cn(
            // Place toggle button top-right on mobile, right of sidebar on desktop
            "absolute z-50 h-8 w-8 rounded-full bg-gray-800 p-0 hover:bg-gray-700",
            "top-4 right-4 md:top-4 md:-right-4"
          )}
          onClick={toggleSidebar}
        >
          {isOpen ? <ChevronLeft /> : <ChevronRight />}
        </Button>
        <div className={cn("flex h-full w-full", "flex-row md:flex-col")}> {/* Responsive orientation */}
          <div className={cn(
            // Logo: center on desktop, left on mobile
            "flex items-center justify-center md:h-16 md:w-full w-16 h-full"
          )}>
            <div className="rounded-full bg-white p-2">
              <Mic className="h-8 w-8 text-gray-900" />
            </div>
          </div>
          <nav className={cn(
            "flex-1 space-y-2 p-4 md:p-4",
            "flex-row md:flex-col flex md:space-y-2 space-x-2 md:space-x-0 items-center md:items-stretch"
          )}>
            {menuItems.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  "flex items-center rounded-lg p-2 transition-colors hover:bg-gray-800",
                  "md:w-full w-auto"
                )}
                activeProps={{ className: "bg-gray-800" }}
              >
                <item.icon className="h-5 w-5" />
                {isOpen && <span className="ml-3 hidden md:inline">{item.label}</span>}
                {/* On mobile, hide label */}
              </Link>
            ))}
          </nav>
          <div className={cn("p-4 flex-shrink-0")}> {/* Logout always at end */}
            <Button
              variant="ghost"
              className="w-full justify-start"
              onClick={handleLogout}
            >
              <LogOut className="h-5 w-5" />
              {isOpen && <span className="ml-3 hidden md:inline">Logout</span>}
            </Button>
          </div>
        </div>
      </div>

      {/* Main content: margin-top for mobile, margin-left for desktop */}
      <div
        className={cn(
          "flex-1 transition-all duration-300 ease-in-out",
          "mt-16 md:mt-0 md:ml-64",
          isOpen ? "md:ml-64" : "md:ml-16"
        )}
      >
        {children}
      </div>
    </div>
  );
}
