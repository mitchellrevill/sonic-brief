import type { LinkOptions } from "@tanstack/react-router";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { getStorageItem, setStorageItem } from "@/lib/storage";
import { cn } from "@/lib/utils";
import { Link, useRouter } from "@tanstack/react-router";
import { useTheme } from "next-themes";
import {
  ChevronLeft,
  ChevronRight,
  FileAudio,
  FileText,
  LogOut,
  Mic,
  Moon,
  Settings,
  Sun,
  UserCog
} from "lucide-react";

interface MenuItem {
  icon: React.ElementType;
  label: string;
  to: LinkOptions["to"];
}

const menuItems: Array<MenuItem> = [
  { icon: Mic, label: "Media Upload", to: "/audio-upload" },
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
  const [sidebarLayout, setSidebarLayout] = useState(() => {
    const saved = getStorageItem("sidebarLayout", "left");
    return saved; // "left" for vertical sidebar, "top" for horizontal
  });

  const router = useRouter();
  const { setTheme } = useTheme();

  const toggleSidebar = () => {
    const newState = !isOpen;
    setIsOpen(newState);
    setStorageItem("sidebarOpen", JSON.stringify(newState));
  };

  const toggleSidebarLayout = () => {
    const newLayout = sidebarLayout === "left" ? "top" : "left";
    setSidebarLayout(newLayout);
    setStorageItem("sidebarLayout", newLayout);
  };
  const handleLogout = () => {
    localStorage.removeItem("token");
    router.navigate({ to: "/login" });
  };return (
    <div className="flex min-h-screen flex-col">
      {/* Sidebar - responsive: top bar on mobile, user preference on desktop */}
      <div
        className={cn(
          "fixed z-40 flex bg-gray-900 text-white transition-all duration-300 ease-in-out",
          // Mobile: always top bar
          "top-0 left-0 w-full h-16 flex-row",
          // Desktop: user preference
          "md:top-0 md:left-0",
          sidebarLayout === "top" 
            ? "md:w-full md:h-16 md:flex-row" // Desktop top bar
            : cn(
                "md:h-full md:flex-col", // Desktop vertical sidebar
                isOpen ? "md:w-64" : "md:w-16"
              )
        )}
      >
        {/* Toggle button - responsive positioning */}
        <Button
          variant="ghost"
          className={cn(
            "absolute z-50 h-8 w-8 rounded-full bg-gray-800 p-0 hover:bg-gray-700",
            // Mobile: always top-right
            "top-4 right-4",
            // Desktop: depends on layout
            sidebarLayout === "left" && isOpen ? "md:-right-4" : "md:right-2"
          )}
          onClick={toggleSidebar}
        >
          {sidebarLayout === "left" ? (
            isOpen ? <ChevronLeft /> : <ChevronRight />
          ) : (
            isOpen ? <ChevronLeft /> : <ChevronRight />
          )}
        </Button>

        <div className={cn(
          "flex h-full w-full",
          // Mobile: always row
          "flex-row",
          // Desktop: depends on layout
          sidebarLayout === "top" ? "md:flex-row" : "md:flex-col"
        )}>
          {/* Logo */}
          <div className={cn(
            "flex items-center justify-center flex-shrink-0",
            // Mobile: compact
            "w-16 h-full",
            // Desktop: depends on layout
            sidebarLayout === "top" ? "md:w-16 md:h-full" : "md:h-16 md:w-full"
          )}>
            <div className="rounded-full bg-white p-2">
              <Mic className="h-6 w-6 md:h-8 md:w-8 text-gray-900" />
            </div>
          </div>

          {/* Navigation */}
          <nav className={cn(
            "flex-1 p-2 md:p-4",
            // Mobile: always horizontal, no text
            "flex flex-row space-x-1 items-center",
            // Desktop: depends on layout and sidebar state
            sidebarLayout === "top" 
              ? "md:flex-row md:space-x-2 md:space-y-0" 
              : cn(
                  "md:flex-col md:space-x-0 md:space-y-2",
                  !isOpen && "md:items-center"
                )
          )}>
            {menuItems.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  "flex items-center rounded-lg p-2 transition-colors hover:bg-gray-800",
                  // Mobile: compact, no text
                  "w-auto",
                  // Desktop: full width for vertical sidebar
                  sidebarLayout === "left" && "md:w-full"
                )}
                activeProps={{ className: "bg-gray-800" }}
              >
                <item.icon className="h-5 w-5" />
                {/* Text only on desktop when expanded or in top layout */}
                <span className={cn(
                  "ml-3 hidden",
                  sidebarLayout === "top" ? "md:inline" : isOpen && "md:inline"
                )}>
                  {item.label}
                </span>
              </Link>
            ))}
          </nav>

          {/* Settings and Logout - ensure both are visible */}
          <div className={cn(
            "flex-shrink-0 p-2 md:p-4",
            // Mobile: horizontal row
            "flex flex-row space-x-1 items-center",
            // Desktop: depends on layout
            sidebarLayout === "top" 
              ? "md:flex-row md:space-x-2 md:space-y-0" 
              : "md:flex-col md:space-x-0 md:space-y-2"
          )}>
            {/* Settings - hidden on mobile, visible on desktop */}
            <div className="hidden md:block">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    className="w-full justify-start"
                  >
                    <Settings className="h-5 w-5" />
                    {(sidebarLayout === "top" || isOpen) && (
                      <span className="ml-3">Settings</span>
                    )}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuItem onClick={() => setTheme("light")}>
                    <Sun className="mr-2 h-4 w-4" />
                    <span>Light Theme</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setTheme("dark")}>
                    <Moon className="mr-2 h-4 w-4" />
                    <span>Dark Theme</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setTheme("system")}>
                    <Settings className="mr-2 h-4 w-4" />
                    <span>System Theme</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={toggleSidebarLayout}>
                    <ChevronLeft className="mr-2 h-4 w-4" />
                    <span>Switch to {sidebarLayout === "left" ? "Top Bar" : "Left Sidebar"}</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            {/* Logout - always visible */}
            <Button
              variant="ghost"
              className="justify-start"
              onClick={handleLogout}
            >
              <LogOut className="h-5 w-5" />
              {/* Text only on desktop when expanded or in top layout */}
              <span className={cn(
                "ml-3 hidden",
                sidebarLayout === "top" ? "md:inline" : isOpen && "md:inline"
              )}>
                Logout
              </span>
            </Button>
          </div>
        </div>
      </div>

      {/* Main content - responsive margins */}
      <div
        className={cn(
          "flex-1 transition-all duration-300 ease-in-out",
          // Mobile: always top margin
          "mt-16",
          // Desktop: depends on layout
          sidebarLayout === "top" 
            ? "md:mt-16" // Top margin for horizontal layout
            : isOpen 
              ? "md:mt-0 md:ml-64" // Left margin for expanded vertical sidebar
              : "md:mt-0 md:ml-16" // Left margin for collapsed vertical sidebar
        )}
      >
        {children}
      </div>
    </div>
  );
}
