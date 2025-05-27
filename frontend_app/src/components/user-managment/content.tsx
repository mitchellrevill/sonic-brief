import { useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchAllUsers } from "@/lib/api"; 

type User = {
  id: number;
  name: string;
  email: string; 
  permission: "admin" | "editor" | "viewer";
};

const initialUsers: User[] = [
  { id: 1, name: "Alice Smith", email: "alice@example.com", permission: "admin" },
  { id: 2, name: "Bob Jones", email: "bob@example.com", permission: "editor" },
  { id: 3, name: "Charlie Brown", email: "charlie@example.com", permission: "viewer" },
];

// ...existing code...
export function UserManagementTable() {
  const [users, setUsers] = useState<User[]>(initialUsers);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editPermission, setEditPermission] = useState<"admin" | "editor" | "viewer">("viewer");
  const [loading, setLoading] = useState(false);

  // Uncomment and implement fetchAllUsersApi if needed
  const fetchAllUsersApi = async () => {
    setLoading(true);
    try {
      const data = await fetchAllUsers();
      setUsers(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const startEdit = (user: User) => {
    setEditingId(user.id);
    setEditPermission(user.permission);
  };

  const saveEdit = (id: number) => {
    setUsers(users =>
      users.map(user =>
        user.id === id ? { ...user, permission: editPermission } : user
      )
    );
    setEditingId(null);
  };

  return (
    <Card className="w-full max-w-3xl ml-0">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>User List</CardTitle>
          <Button size="sm" onClick={fetchAllUsersApi} disabled={loading}>
            {loading ? "Loading..." : "Test Fetch Users"}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-left">Name</TableHead>
              <TableHead className="text-left">Email</TableHead>
              <TableHead className="text-left">Permission</TableHead>
              <TableHead className="text-left w-40">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users.map(user => (
              <TableRow key={user.id}>
                <TableCell className="text-left">{user.name}</TableCell>
                <TableCell className="text-left">{user.email}</TableCell>
                <TableCell className="text-left">
                  {editingId === user.id ? (
                    <select
                      value={editPermission}
                      onChange={e => setEditPermission(e.target.value as User["permission"])}
                      className="border rounded px-2 py-1"
                    >
                      <option value="admin">Admin</option>
                      <option value="editor">Editor</option>
                      <option value="viewer">Viewer</option>
                    </select>
                  ) : (
                    <span className="capitalize">{user.permission}</span>
                  )}
                </TableCell>
                <TableCell className="text-left w-40">
                  <div className="flex gap-2 min-w-[120px]">
                    {editingId === user.id ? (
                      <>
                        <Button size="sm" onClick={() => saveEdit(user.id)}>
                          Save
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => setEditingId(null)}
                        >
                          Cancel
                        </Button>
                      </>
                    ) : (
                      <Button size="sm" onClick={() => startEdit(user)}>
                        Edit
                      </Button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}