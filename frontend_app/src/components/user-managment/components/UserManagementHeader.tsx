// UI controls were removed; keep props for compatibility

interface UserManagementHeaderProps {
  onAddUser?: () => void;
  onExportCSV?: () => void;
}

export function UserManagementHeader({ onAddUser, onExportCSV }: UserManagementHeaderProps) {
  // Keep props referenced for compatibility (they may be used elsewhere).
  void onAddUser;
  void onExportCSV;

  return (
    <div className="flex justify-between items-center">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">User Management</h1>
        <p className="text-muted-foreground">
          Monitor user activity, manage permissions, and track system analytics
        </p>
      </div>
      <div className="flex gap-2">
        {/* 'Add User' and 'Export Minutes CSV' removed per UI update request. */}
      </div>
    </div>
  );
}
