import { useEffect, useState } from "react";
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
import type { User } from "@/lib/api";
import { updateUserPermission } from "@/lib/api";

const initialUsers: User[] = [
  { id: "1", name: "", email: "", permission: "Admin" },
];


export function UserManagementTable() {
  const [users, setUsers] = useState<User[]>(initialUsers);
const [editingId, setEditingId] = useState<string | null>(null);
const [editPermission, setEditPermission] = useState<Record<string, User["permission"]>>({});
  const [loading, setLoading] = useState(false);


    const fetchAllUsersApi = async () => {
    setLoading(true);
    try {
      const response: User[] | { users: User[] } = await fetchAllUsers();
      let apiUsers: User[];
      if (Array.isArray(response)) {
        apiUsers = response;
      } else if (response && typeof response === "object" && "users" in response && Array.isArray((response as any).users)) {
        apiUsers = (response as { users: User[] }).users;
      } else {
        apiUsers = [];
      }
    const mappedUsers = apiUsers.map((u: any, idx: number) => {
      let dateStr = "";
      if (u._ts) {
      const d = new Date(u._ts * 1000);
      const day = String(d.getDate()).padStart(2, "0");
      const month = String(d.getMonth() + 1).padStart(2, "0");
      const year = d.getFullYear();
      const time = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      dateStr = `${day}/${month}/${year} ${time}`;
      }
      return {
      id: u.id || idx,
      name: u.name || u.email || "",
      email: u.email,
      permission: (u.permission as "User" | "Admin" | "Viewer") || (u.permission as "User" | "Admin" | "Viewer") || "Viewer",
      date: dateStr,
      };
    });
    setUsers(mappedUsers);
  } catch (err) {
    console.error(err);
  } finally {
    setLoading(false);
  }
};

  useEffect(() => {
    fetchAllUsersApi();
  }, []);
 
const startEdit = (user: User) => {
  setEditingId(user.id);
  setEditPermission(prev => ({ ...prev, [user.id]: user.permission }));
};

const saveEdit = async (id: string) => {
  try {
    const permission = editPermission[id];
    await updateUserPermission(id, permission);
    await fetchAllUsersApi();
  } catch (err) {
    console.error("Failed to update user permission:", err);
  } finally {
    setEditingId(null);
  }
};


  return (
    <Card className="w-full max-w-4xl ml-0">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>User List</CardTitle>
          <Button size="sm" onClick={fetchAllUsersApi} disabled={loading}>
            {loading ? "Loading..." : "Refresh Users"}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-left">Id</TableHead>
              <TableHead className="text-left">Email</TableHead>
              <TableHead className="text-left">User Level</TableHead>
              <TableHead className="text-left">Date</TableHead>
              <TableHead className="text-left w-40">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users.map(user => (
              <TableRow key={user.id}>
                <TableCell className="text-left">{user.id}</TableCell>
                <TableCell className="text-left">{user.email}</TableCell>
                <TableCell className="text-left">
                  {editingId === user.id ? (
                  <select
                          value={editPermission[user.id] ?? user.permission}
                          onChange={e =>
                            setEditPermission(prev => ({
                              ...prev,
                              [user.id]: e.target.value as User["permission"],
                            }))
                          }
                          className="border rounded px-2 py-1"
                        >
                          <option value="Admin">Admin</option>
                          <option value="User">User</option>
                          <option value="Viewer">Viewer</option>
                        </select>
                  ) : (
                    <span className="capitalize">{user.permission}</span>
                  )}
                </TableCell>
                <TableCell className="text-left">{user.date || ""}</TableCell> {/* <-- Add this line */}
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