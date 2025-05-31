import React from "react";
import { Link } from "@tanstack/react-router";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
  BreadcrumbEllipsis,
} from "@/components/ui/breadcrumb";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

export interface BreadcrumbItem {
  label: string;
  href?: string;
  to?: string;
  isCurrentPage?: boolean;
}

interface SmartBreadcrumbProps {
  items: BreadcrumbItem[];
  className?: string;
  maxItems?: number;
  showHome?: boolean;
}

export function SmartBreadcrumb({
  items,
  className,
  maxItems = 3,
  showHome = true,
}: SmartBreadcrumbProps) {
  // Always include home if showHome is true
  const allItems: BreadcrumbItem[] = showHome
    ? [{ label: "Home", to: "/" }, ...items]
    : items;

  // Handle ellipsis for long breadcrumb trails
  const shouldShowEllipsis = allItems.length > maxItems;
  const displayItems = shouldShowEllipsis
    ? [
        allItems[0], // First item (usually Home)
        ...allItems.slice(-2), // Last 2 items
      ]
    : allItems;

  const hiddenItems = shouldShowEllipsis
    ? allItems.slice(1, -2) // Items between first and last 2
    : [];

  return (
    <Breadcrumb className={cn("", className)}>
      <BreadcrumbList>
        {displayItems.map((item, index) => {
          const isLast = index === displayItems.length - 1;
          const isEllipsisPosition = shouldShowEllipsis && index === 1;

          return (
            <React.Fragment key={`${item.label}-${index}`}>
              {/* Show ellipsis dropdown for hidden items */}
              {isEllipsisPosition && hiddenItems.length > 0 && (
                <>
                  <BreadcrumbItem>
                    <DropdownMenu>
                      <DropdownMenuTrigger className="flex h-9 w-9 items-center justify-center">
                        <BreadcrumbEllipsis className="h-4 w-4" />
                        <span className="sr-only">Toggle menu</span>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="start">
                        {hiddenItems.map((hiddenItem) => (
                          <DropdownMenuItem key={hiddenItem.label} asChild>
                            {hiddenItem.to ? (
                              <Link to={hiddenItem.to}>{hiddenItem.label}</Link>
                            ) : hiddenItem.href ? (
                              <a href={hiddenItem.href}>{hiddenItem.label}</a>
                            ) : (
                              <span>{hiddenItem.label}</span>
                            )}
                          </DropdownMenuItem>
                        ))}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </BreadcrumbItem>
                  <BreadcrumbSeparator />
                </>
              )}

              {/* Regular breadcrumb item */}
              <BreadcrumbItem>
                {isLast || item.isCurrentPage ? (
                  <BreadcrumbPage className="max-w-[200px] truncate">
                    {item.label}
                  </BreadcrumbPage>
                ) : (
                  <BreadcrumbLink asChild>
                    {item.to ? (
                      <Link to={item.to}>{item.label}</Link>
                    ) : item.href ? (
                      <a href={item.href}>{item.label}</a>
                    ) : (
                      <span>{item.label}</span>
                    )}
                  </BreadcrumbLink>
                )}
              </BreadcrumbItem>

              {/* Add separator if not the last item */}
              {!isLast && <BreadcrumbSeparator />}
            </React.Fragment>
          );
        })}
      </BreadcrumbList>
    </Breadcrumb>
  );
}

// Hook for generating breadcrumbs from router location
export function useBreadcrumbFromLocation() {
  // This could be extended to automatically generate breadcrumbs
  // based on the current route path
  const generateBreadcrumbs = (pathname: string): BreadcrumbItem[] => {
    const segments = pathname.split("/").filter(Boolean);
    const breadcrumbs: BreadcrumbItem[] = [];

    segments.forEach((segment, index) => {
      const path = "/" + segments.slice(0, index + 1).join("/");
      const label = segment
        .split("-")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");

      breadcrumbs.push({
        label,
        to: path,
        isCurrentPage: index === segments.length - 1,
      });
    });

    return breadcrumbs;
  };

  return { generateBreadcrumbs };
}
