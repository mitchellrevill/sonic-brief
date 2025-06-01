import { useLocation } from "@tanstack/react-router";
import { useMemo } from "react";

export interface BreadcrumbItem {
  label: string;
  href?: string;
  to?: string;
  isCurrentPage?: boolean;
}

// Route mappings for better breadcrumb labels
const ROUTE_MAPPINGS: Record<string, string> = {
  "/": "Home",
  "/audio-upload": "Media Upload",
  "/audio-recordings": "Audio Recordings", 
  "/audio-recordings/shared": "Shared Recordings",
  "/prompt-management": "Prompt Management",
  "/user-management": "User Management",
  "/admin": "Admin",
  "/admin/user-management": "User Management",
  "/admin/deleted-jobs": "Deleted Recordings",
  "/admin/all-jobs": "All Recordings",
  "/unauthorised": "Unauthorized",
};

// Specific route handlers for complex breadcrumbs
const ROUTE_HANDLERS: Record<string, (pathname: string, segments: string[]) => BreadcrumbItem[]> = {  "/audio-recordings": (_: string, segments) => {
    const items: BreadcrumbItem[] = [
      { label: "Audio Recordings", to: "/audio-recordings" }
    ];
    
    // Handle shared recordings path
    if (segments.length > 1 && segments[1] === "shared") {
      items.push({
        label: "Shared Recordings",
        isCurrentPage: true
      });
    } else if (segments.length > 2 && segments[2]) {
      // If there's a recording ID
      items.push({
        label: `Recording ${segments[2]}`,
        isCurrentPage: true
      });
    } else {
      items[0].isCurrentPage = true;
    }
    
    return items;
  },
  
  "/prompt-management": (_: string, segments) => {
    const items: BreadcrumbItem[] = [
      { label: "Prompt Management", to: "/prompt-management" }
    ];
    
    // Handle subcategory or category views
    if (segments.length > 2) {
      if (segments[2] === "category") {
        items.push({
          label: "Category Management",
          isCurrentPage: true
        });
      } else if (segments[2] === "prompts") {
        items.push({
          label: "Prompt Editor",
          isCurrentPage: true
        });
      }
    } else {
      items[0].isCurrentPage = true;
    }
    
    return items;  },
  
  "/user-management": (_: string, segments) => {
    const items: BreadcrumbItem[] = [
      { label: "User Management", to: "/user-management" }
    ];
    
    if (segments.length > 2 && segments[2]) {
      items.push({
        label: `User ${segments[2]}`,
        isCurrentPage: true
      });
    } else {
      items[0].isCurrentPage = true;
    }
    
    return items;
  },

  "/admin": (_: string, segments) => {
    const items: BreadcrumbItem[] = [
      { label: "Admin", to: "/admin" }
    ];
    
    if (segments.length > 1) {
      if (segments[1] === "deleted-jobs") {
        items.push({
          label: "Deleted Recordings",
          isCurrentPage: true
        });
      } else if (segments[1] === "all-jobs") {
        items.push({
          label: "All Recordings",
          isCurrentPage: true
        });
      } else if (segments[1] === "user-management") {
        items.push({
          label: "User Management",
          isCurrentPage: true
        });
      }
    } else {
      items[0].isCurrentPage = true;
    }
    
    return items;
  }
};

export function useBreadcrumbs(): BreadcrumbItem[] {
  const location = useLocation();
  
  return useMemo(() => {
    const pathname = location.pathname;
    
    // Handle root path
    if (pathname === "/") {
      return [{ label: "Home", isCurrentPage: true }];
    }
    
    const segments = pathname.split("/").filter(Boolean);
    
    // Check if we have a specific handler for this route
    const baseRoute = `/${segments[0]}`;
    const handler = ROUTE_HANDLERS[baseRoute];
    
    if (handler) {
      return handler(pathname, segments);
    }
    
    // Default breadcrumb generation
    const breadcrumbs: BreadcrumbItem[] = [];
    let currentPath = "";
    
    segments.forEach((segment, index) => {
      currentPath += `/${segment}`;
      const isLast = index === segments.length - 1;
      
      // Get a friendly label
      let label = ROUTE_MAPPINGS[currentPath];
      if (!label) {
        // Fallback to formatted segment name
        label = segment
          .split("-")
          .map(word => word.charAt(0).toUpperCase() + word.slice(1))
          .join(" ");
      }
      
      breadcrumbs.push({
        label,
        to: currentPath,
        isCurrentPage: isLast
      });
    });
    
    return breadcrumbs;
  }, [location.pathname]);
}

// Hook for manual breadcrumb management (for complex pages)
export function useManualBreadcrumbs(items: BreadcrumbItem[]) {
  return items;
}
