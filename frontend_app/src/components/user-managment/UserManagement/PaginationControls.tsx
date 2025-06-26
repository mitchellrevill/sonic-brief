import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface PaginationControlsProps {
  indexOfFirstUser: number;
  indexOfLastUser: number;
  filteredUsersLength: number;
  currentPage: number;
  totalPages: number;
  setCurrentPage: (page: number) => void;
}

export function PaginationControls({
  indexOfFirstUser,
  indexOfLastUser,
  filteredUsersLength,
  currentPage,
  totalPages,
  setCurrentPage
}: PaginationControlsProps) {
  return (
    <div className="flex items-center justify-between px-2">
      <div className="text-sm text-muted-foreground">
        Showing {indexOfFirstUser + 1} to {Math.min(indexOfLastUser, filteredUsersLength)} of {filteredUsersLength} users
      </div>
      <div className="flex items-center space-x-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setCurrentPage(Math.max(currentPage - 1, 1))}
          disabled={currentPage === 1}
        >
          <ChevronLeft className="h-4 w-4" />
          Previous
        </Button>
        <div className="flex items-center space-x-1">
          {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
            const pageNumber = currentPage <= 3 ? i + 1 : currentPage - 2 + i;
            if (pageNumber > totalPages) return null;
            return (
              <Button
                key={pageNumber}
                variant={currentPage === pageNumber ? "default" : "outline"}
                size="sm"
                onClick={() => setCurrentPage(pageNumber)}
                className="w-8 h-8 p-0"
              >
                {pageNumber}
              </Button>
            );
          })}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setCurrentPage(Math.min(currentPage + 1, totalPages))}
          disabled={currentPage === totalPages}
        >
          Next
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
