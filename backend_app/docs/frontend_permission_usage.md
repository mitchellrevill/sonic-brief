# Using the Permission System in the React App

## Overview
The Sonic Brief frontend (React + TypeScript) integrates with the backend permission system to control UI and feature access based on the user's permission level and capabilities.

---

## How Permissions Work in the Frontend
- The backend encodes the user's permission (e.g., `User`, `Editor`, `Admin`) in the JWT and/or user API responses.
- The frontend decodes the JWT or fetches the user profile to determine the current user's permission level and capabilities.
- UI components and routes use this information to show/hide features, restrict actions, and display admin/editor-only content.

---

## Typical Usage Patterns

### 1. Fetching User Permissions
- On login or app load, fetch the user profile (e.g., `/api/auth/users/me/permissions` or `/api/auth/users/me`).
- Store the permission level and capabilities in React context, Redux, or a global state.

```typescript
// Example: Fetch and store user permissions
const { data: user } = useQuery(['user'], fetchCurrentUser);
const permission = user?.permission; // e.g., 'Admin', 'Editor', 'User'
const capabilities = user?.capabilities; // e.g., { can_manage_users: true, ... }
```

### 2. Conditional Rendering by Permission

```tsx
// Show admin-only button
{permission === 'Admin' && (
  <Button onClick={handleAdminAction}>Admin Action</Button>
)}

// Show editor or admin features
{['Admin', 'Editor'].includes(permission) && (
  <EditorPanel />
)}

// Use capabilities for fine-grained checks
{capabilities?.can_manage_users && <UserManagement />}
```

### 3. Route Protection
- Use a custom hook or wrapper to restrict access to certain routes:

```tsx
import { usePermissions } from '../hooks/usePermissions';

function AdminRoute({ children }) {
  const { permission } = usePermissions();
  if (permission !== 'Admin') {
    return <Navigate to="/unauthorized" />;
  }
  return children;
}
```

### 4. Feature Flags and UI Hiding
- Use permission/capability checks to hide or disable UI elements for users without access.

```tsx
<Button disabled={!capabilities?.can_create_templates}>
  Create Template
</Button>
```

---

## Best Practices
- Always check permissions before showing sensitive UI or triggering privileged actions.
- Use both permission level and capabilities for flexibility.
- Keep permission logic in a central place (e.g., a custom hook or context provider).
- Sync permission logic with backend changes—update frontend enums/capabilities as needed.

---

## References
- [`frontend_app/src/lib/permission-constants.ts`](../../frontend_app/src/lib/permission-constants.ts)
- [`frontend_app/src/hooks/usePermissions.tsx`](../../frontend_app/src/hooks/usePermissions.tsx)
- [`frontend_app/src/lib/permission.tsx`](../../frontend_app/src/lib/permission.tsx)
- [`frontend_app/PERMISSION_MIGRATION_GUIDE.md`](../../frontend_app/PERMISSION_MIGRATION_GUIDE.md)

_Last updated: June 2025_
