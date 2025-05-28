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
    setEditingId(String(user.id));
    setEditPermission(prev => ({ ...prev, [String(user.id)]: user.permission }));
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
        {/* Mobile: Vertical Table */}
        <div className="block sm:hidden space-y-4">
          {users.map(user => {
            const userId = String(user.id);
            return (
              <div key={user.id} className="border rounded-lg p-4 shadow-sm bg-white dark:bg-zinc-900">
                <div className="mb-2 flex items-center justify-between">
                  <span className="font-semibold">{user.email}</span>
                  <span className="capitalize text-xs px-2 py-1 rounded bg-gray-100 dark:bg-zinc-800 dark:text-gray-200">{user.permission}</span>
                </div>
                <div className="text-xs text-gray-500 mb-1"><span className="font-semibold">ID:</span> {user.id}</div>
                <div className="text-xs text-gray-500 mb-1"><span className="font-semibold">Date:</span> {user.date || ""}</div>
                <div className="text-xs text-gray-500 mb-2"><span className="font-semibold">User Level:</span> {editingId === userId ? (
                  <select
                    value={editPermission[userId] ?? user.permission}
                    onChange={e =>
                      setEditPermission(prev => ({
                        ...prev,
                        [userId]: e.target.value as User["permission"],
                      }))
                    }
                    className="border rounded px-2 py-1 w-full mt-1"
                  >
                    <option value="Admin">Admin</option>
                    <option value="User">User</option>
                    <option value="Viewer">Viewer</option>
                  </select>
                ) : (
                  <span className="capitalize ml-1">{user.permission}</span>
                )}</div>
                <div className="flex gap-2 mt-2">
                  {editingId === userId ? (
                    <>
                      <Button size="sm" onClick={() => saveEdit(userId)} className="w-1/2 min-w-[80px] px-2 py-1 text-xs">
                        Save
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => setEditingId(null)} className="w-1/2 min-w-[80px] px-2 py-1 text-xs">
                        Cancel
                      </Button>
                    </>
                  ) : (
                    <Button size="icon" onClick={() => startEdit(user)} className="w-8 h-8 p-0 text-muted-foreground border border-gray-300 hover:bg-gray-100">
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536M9 13l6.586-6.586a2 2 0 112.828 2.828L11.828 15.828a4 4 0 01-1.414.828l-4.243 1.414 1.414-4.243a4 4 0 01.828-1.414z" /></svg>
                      <span className="sr-only">Edit</span>
                    </Button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
        {/* Desktop: Table */}
        <div className="hidden sm:block">
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
              {users.map(user => {
                const userId = String(user.id);
                return (
                  <TableRow key={user.id}>
                    <TableCell className="text-left">{user.id}</TableCell>
                    <TableCell className="text-left">{user.email}</TableCell>
                    <TableCell className="text-left">
                      {editingId === userId ? (
                        <select
                          value={editPermission[userId] ?? user.permission}
                          onChange={e =>
                            setEditPermission(prev => ({
                              ...prev,
                              [userId]: e.target.value as User["permission"],
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
                    <TableCell className="text-left">{user.date || ""}</TableCell>
                    <TableCell className="text-left w-40">
                      <div className="flex gap-2 min-w-[120px]">
                        {editingId === userId ? (
                          <>
                            <Button size="sm" onClick={() => saveEdit(userId)}>
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
                );
              })}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}