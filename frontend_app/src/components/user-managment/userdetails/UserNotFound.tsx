import { Card, CardContent } from "@/components/ui/card";
import { ArrowLeft, User as UserIcon } from "lucide-react";
import { Button } from "@/components/ui/button";

export function UserNotFound() {
  return (
    <div className="container mx-auto py-6">
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12">
          <UserIcon className="h-12 w-12 text-muted-foreground mb-4" />
          <h2 className="text-xl font-semibold mb-2">User Not Found</h2>
          <p className="text-muted-foreground mb-4">The requested user could not be found.</p>
          <Button onClick={() => {
            window.location.href = '/admin/users';
          }}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to User Management
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
