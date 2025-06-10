import React, { useState } from "react";
import type { LinkOptions } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { Link, useRouter } from "@tanstack/react-router";
import { useTheme } from "next-themes";
import {
  ChevronLeft,
  ChevronRight,
  FileAudio,
  FileText,  LogOut,
  Mic,
  Sun,
  Moon,
  Monitor,
  UserCog,
  Users,
  Trash2,
  User,
  MoreHorizontal,
  Upload,
} from "lucide-react";
import { getStorageItem, setStorageItem } from "@/lib/storage";
import { usePermissionGuard, useUserPermissions } from "@/hooks/usePermissions";

interface MenuItem {
  icon: React.ElementType;
  label: string;
  to: LinkOptions["to"];
}

const menuItems: Array<MenuItem> = [
  { icon: Mic, label: "Simple Upload", to: "/simple-upload" },
  { icon: Upload, label: "Media Upload", to: "/audio-upload" },
  { icon: FileAudio, label: "Audio Recordings", to: "/audio-recordings" },
  { icon: Users, label: "Shared Recordings", to: "/audio-recordings/shared" },
];

const adminMenuItems: Array<MenuItem> = [
  { icon: FileAudio, label: "All Recordings", to: "/admin/all-jobs" },
  { icon: Trash2, label: "Deleted Recordings", to: "/admin/deleted-jobs" },
  { icon: UserCog, label: "User Management", to: "/admin/user-management" },
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
  
  const { currentPermission } = usePermissionGuard();
  const isAdmin = currentPermission === "Admin";
  const { data: userPermissions } = useUserPermissions();

  const router = useRouter();
  const { setTheme } = useTheme();

  // Helper functions for user display
  const getUserInitials = (email?: string) => {
    if (!email) return "U";
    return email.split('@')[0].slice(0, 2).toUpperCase();
  };

  const getPermissionColor = (permission?: string) => {
    switch (permission) {
      case "Admin":
        return "bg-red-100 text-red-800 border-red-200";
      case "User":
        return "bg-blue-100 text-blue-800 border-blue-200";
      case "Viewer":
        return "bg-gray-100 text-gray-800 border-gray-200";
      default:
        return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

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
  };  return (
    <div className="flex min-h-screen flex-col">
      {/* Sidebar - responsive: top bar on mobile, user preference on desktop */}
      <div
        className={cn(
          "fixed z-40 flex bg-gray-900 text-white transition-all duration-300 ease-in-out",
          // Mobile: always top bar, no overflow issues
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
        {/* Toggle button - only show in left sidebar layout and positioned better */}
        {sidebarLayout === "left" && (
          <Button
            variant="ghost"
            className={cn(
              "absolute z-50 h-8 w-8 rounded-full bg-gray-800 p-0 hover:bg-gray-700",
              // Only show on desktop
              "hidden md:block",
              // Desktop: positioned outside sidebar
              isOpen ? "md:-right-4 md:top-4" : "md:-right-4 md:top-4"
            )}
            onClick={toggleSidebar}
          >
            {isOpen ? <ChevronLeft /> : <ChevronRight />}
          </Button>
        )}        <div
          className={cn(
            "flex h-full w-full",
            // Mobile: always row
            "flex-row",
            // Desktop: depends on layout
            sidebarLayout === "top" ? "md:flex-row" : "md:flex-col"
          )}
        >
          {/* Logo */}
          <div
            className={cn(
              "flex items-center justify-center flex-shrink-0",
              // Mobile: compact
              "w-16 h-full",
              // Desktop: depends on layout
              sidebarLayout === "top" ? "md:w-16 md:h-full" : "md:h-16 md:w-full"
            )}
          >
            <div className="rounded-full bg-white p-2">
              <Mic className="h-6 w-6 md:h-8 md:w-8 text-gray-900" />
            </div>
          </div>

          {/* Mobile Navigation - Show only essential items + dropdown for rest */}
          <nav className="flex-1 p-2 flex flex-row space-x-1 items-center md:hidden">
            {/* Show first 3 menu items on mobile */}
            {menuItems.slice(0, 3).map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className="flex items-center rounded-lg p-2 transition-colors hover:bg-gray-800 flex-shrink-0"
                activeProps={{ className: "bg-gray-800" }}
              >
                <item.icon className="h-5 w-5" />
              </Link>
            ))}

            {/* More menu dropdown for remaining items */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="flex items-center p-2 flex-shrink-0">
                  <MoreHorizontal className="h-5 w-5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">                {/* Remaining menu items */}
                {menuItems.slice(3).map((item) => (
                  <DropdownMenuItem key={item.to} asChild>
                    <Link to={item.to} className="flex items-center">
                      <item.icon className="mr-2 h-4 w-4" />
                      <span>{item.label}</span>
                    </Link>
                  </DropdownMenuItem>
                ))}

                {/* Admin/User permission items */}
                {(currentPermission === "Admin" || currentPermission === "User") && (
                  <DropdownMenuItem asChild>
                    <Link to="/prompt-management" className="flex items-center">
                      <FileText className="mr-2 h-4 w-4" />
                      <span>Prompt Management</span>
                    </Link>
                  </DropdownMenuItem>
                )}

                {/* Admin items if admin */}
                {isAdmin && adminMenuItems.map((item) => (
                  <DropdownMenuItem key={item.to} asChild>
                    <Link to={item.to} className="flex items-center">
                      <item.icon className="mr-2 h-4 w-4" />
                      <span>{item.label}</span>
                    </Link>
                  </DropdownMenuItem>
                ))}

                {/* Settings items */}
                <DropdownMenuItem asChild>
                  <Link to="/profile" className="flex items-center">
                    <User className="mr-2 h-4 w-4" />
                    <span>Profile Settings</span>
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setTheme("light")}>
                  <Sun className="mr-2 h-4 w-4" />
                  <span>Light Theme</span>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setTheme("dark")}>
                  <Moon className="mr-2 h-4 w-4" />
                  <span>Dark Theme</span>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setTheme("system")}>
                  <Monitor className="mr-2 h-4 w-4" />
                  <span>System Theme</span>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={toggleSidebarLayout}>
                  <ChevronLeft className="mr-2 h-4 w-4" />
                  <span>
                    Switch to{" "}
                    {sidebarLayout === "left" ? "Top Bar" : "Left Sidebar"}
                  </span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </nav>          {/* Desktop Navigation - Full navigation */}
          <nav
            className={cn(
              "hidden md:flex flex-1 p-4",
              // Desktop: depends on layout and sidebar state
              sidebarLayout === "top"
                ? "flex-row space-x-2 space-y-0"
                : cn(
                    "flex-col space-x-0 space-y-2",
                    !isOpen && "items-center"
                  )
            )}
          >{/* Regular menu items */}
            {menuItems.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  "flex items-center rounded-lg p-2 transition-colors hover:bg-gray-800",
                  sidebarLayout === "left" && "w-full"
                )}
                activeProps={{ className: "bg-gray-800" }}
              >
                <item.icon className="h-5 w-5" />
                <span
                  className={cn(
                    "ml-3 hidden",
                    sidebarLayout === "top" ? "inline" : isOpen && "inline"
                  )}
                >
                  {item.label}
                </span>
              </Link>
            ))}

            {/* Admin/User permission items */}
            {(currentPermission === "Admin" || currentPermission === "User") && (
              <Link
                to="/prompt-management"
                className={cn(
                  "flex items-center rounded-lg p-2 transition-colors hover:bg-gray-800",
                  sidebarLayout === "left" && "w-full"
                )}
                activeProps={{ className: "bg-gray-800" }}
              >
                <FileText className="h-5 w-5" />
                <span
                  className={cn(
                    "ml-3 hidden",
                    sidebarLayout === "top" ? "inline" : isOpen && "inline"
                  )}
                >
                  Prompt Management
                </span>
              </Link>
            )}

            {/* Admin-only menu items */}
            {isAdmin && (
              <>
                {/* Admin section divider - only show when sidebar is expanded in left mode */}
                {sidebarLayout === "left" && isOpen && (
                  <div className="flex items-center my-3 mx-2">
                    <div className="h-px bg-gray-700 flex-grow" />
                    <span className="px-3 text-xs font-medium text-gray-400 uppercase tracking-wider">
                      Admin
                    </span>
                    <div className="h-px bg-gray-700 flex-grow" />
                  </div>
                )}
                
                {adminMenuItems.map((item) => (
                  <Link
                    key={item.to}
                    to={item.to}
                    className={cn(
                      "flex items-center rounded-lg p-2 transition-colors hover:bg-gray-800",
                      sidebarLayout === "left" && "w-full"
                    )}
                    activeProps={{ className: "bg-gray-800" }}
                  >
                    <item.icon className="h-5 w-5" />
                    <span
                      className={cn(
                        "ml-3 hidden",
                        sidebarLayout === "top" ? "inline" : isOpen && "inline"
                      )}
                    >
                      {item.label}
                    </span>
                  </Link>
                ))}              </>
            )}
          </nav>

          {/* Mobile Logout - Always visible */}
          <div className="flex-shrink-0 p-2 md:hidden">
            <Button
              variant="ghost"
              className="flex items-center p-2"
              onClick={handleLogout}
            >
              <LogOut className="h-5 w-5" />
            </Button>
          </div>          {/* Desktop User info and controls */}
          <div className="hidden md:flex md:flex-shrink-0">            {/* For top bar - profile dropdown and separate logout button */}
            {sidebarLayout === "top" && (
              <div className="flex items-center space-x-2 mr-4">
                {/* Profile Dropdown */}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" className="flex items-center space-x-3 px-3 py-3 h-full">
                      <Avatar className="h-8 w-8">
                        <AvatarFallback className="bg-gray-700 text-white text-xs font-medium">
                          {getUserInitials(userPermissions?.email)}
                        </AvatarFallback>
                      </Avatar>
                      {userPermissions && (
                        <div className="flex flex-col items-start min-w-0">
                          <span className="text-sm font-medium text-white truncate max-w-[180px]">
                            {userPermissions.email}
                          </span>
                          <Badge 
                            variant="outline" 
                            className={cn(
                              "text-xs px-1.5 py-0.5 h-4",
                              getPermissionColor(userPermissions.permission)
                            )}
                          >
                            {userPermissions.permission}
                          </Badge>
                        </div>
                      )}
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-64">
                    {userPermissions && (
                      <>
                        <div className="px-3 py-2 border-b">
                          <div className="text-sm font-medium">{userPermissions.email}</div>
                          <div className="mt-1">
                            <Badge 
                              variant="outline" 
                              className={cn(
                                "text-xs px-2 py-0.5",
                                getPermissionColor(userPermissions.permission)
                              )}
                            >
                              {userPermissions.permission}
                            </Badge>
                          </div>
                        </div>
                      </>
                    )}
                    <DropdownMenuItem asChild>
                      <Link to="/profile" className="flex items-center">
                        <User className="mr-2 h-4 w-4" />
                        <span>Profile Settings</span>
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setTheme("light")}>
                      <Sun className="mr-2 h-4 w-4" />
                      <span>Light Theme</span>
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setTheme("dark")}>
                      <Moon className="mr-2 h-4 w-4" />
                      <span>Dark Theme</span>
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setTheme("system")}>
                      <Monitor className="mr-2 h-4 w-4" />
                      <span>System Theme</span>
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={toggleSidebarLayout}>
                      <ChevronLeft className="mr-2 h-4 w-4" />
                      <span>Switch to Left Sidebar</span>
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>

                {/* Separate Logout Button */}
                <Button
                  variant="ghost"
                  className="flex items-center px-3 py-3 h-full text-red-400 hover:text-red-300 hover:bg-red-900/20"
                  onClick={handleLogout}
                >
                  <LogOut className="h-5 w-5" />
                </Button>
              </div>
            )}{/* For left sidebar - user profile positioned higher up */}
            {sidebarLayout === "left" && (
              <div className="w-full flex flex-col mt-8">
                {/* User Profile Section */}
                <div className="p-4 border-t border-gray-700 mt-6">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" className={cn(
                        "w-full p-4 justify-start",
                        !isOpen 
                          ? "flex-col space-y-3 space-x-0" 
                          : "flex-row space-x-4 space-y-0"
                      )}>                        <Avatar className="h-10 w-10">
                          <AvatarFallback className="bg-gray-700 text-white text-sm font-medium">
                            {getUserInitials(userPermissions?.email)}
                          </AvatarFallback>
                        </Avatar>
                        {userPermissions && isOpen && (
                          <div className="flex flex-col items-start min-w-0">
                            <span className="text-sm font-medium text-white truncate max-w-full">
                              {userPermissions.email}
                            </span>
                            <Badge 
                              variant="outline" 
                              className={cn(
                                "text-xs px-2 py-1 h-5 mt-1.5",
                                getPermissionColor(userPermissions.permission)
                              )}
                            >
                              {userPermissions.permission}
                            </Badge>
                          </div>
                        )}
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-64">
                      {userPermissions && (
                        <>
                          <div className="px-3 py-2 border-b">
                            <div className="text-sm font-medium">{userPermissions.email}</div>
                            <div className="mt-1">
                              <Badge 
                                variant="outline" 
                                className={cn(
                                  "text-xs px-2 py-0.5",
                                  getPermissionColor(userPermissions.permission)
                                )}
                              >
                                {userPermissions.permission}
                              </Badge>
                            </div>
                          </div>
                        </>
                      )}
                      <DropdownMenuItem asChild>
                        <Link to="/profile" className="flex items-center">
                          <User className="mr-2 h-4 w-4" />
                          <span>Profile Settings</span>
                        </Link>
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => setTheme("light")}>
                        <Sun className="mr-2 h-4 w-4" />
                        <span>Light Theme</span>
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => setTheme("dark")}>
                        <Moon className="mr-2 h-4 w-4" />
                        <span>Dark Theme</span>
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => setTheme("system")}>
                        <Monitor className="mr-2 h-4 w-4" />
                        <span>System Theme</span>
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={toggleSidebarLayout}>
                        <ChevronLeft className="mr-2 h-4 w-4" />
                        <span>Switch to Top Bar</span>
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>                {/* Logout Button at the very bottom */}
                <div className="mt-auto p-4 border-t border-gray-700">
                  <Button
                    variant="ghost"
                    className={cn(
                      "w-full p-4 text-red-400 hover:text-red-300 hover:bg-red-900/20 justify-start",
                      !isOpen && "flex-col space-y-2"
                    )}
                    onClick={handleLogout}
                  >
                    <LogOut className="h-5 w-5" />
                    {isOpen && <span className="ml-3">Logout</span>}
                  </Button>
                </div>
              </div>
            )}
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
