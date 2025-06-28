F# Frontend Permission System Migration Plan

This document outlines the step-by-step process to migrate the frontend to the new, granular permission system that matches the backend architecture.

## 1. Overview
- Standardize all permission checks to use the `PermissionLevel` enum and `PERMISSION_CAPABILITIES` from `lib/permission-constants.ts`.
- Replace all string-based permission checks and hardcoded role logic with capability-based checks.
- Ensure all protected routes and UI elements use the new system.

## 2. Files to Update

### Core Permission Logic
- `src/lib/permission-constants.ts` (already up to date)
- `src/lib/permission.tsx` (PermissionGuard component)
- `src/hooks/usePermissions.tsx` (permission/capability hook)

### API & Types
- `src/lib/api.ts` (user and permission types, API responses)
- Any other files defining or using user/permission types

### Route Protection
- All route files using `PermissionGuard` (e.g. `src/routes/_layout/admin/user-management/index.tsx`, etc.)

### UI Components
- All components with permission-based rendering (e.g. admin menus, user management, settings, etc.)

## 3. Step-by-Step Migration Guide

### Step 1: Update Permission Constants and Types
- Ensure `src/lib/permission-constants.ts` exports `PermissionLevel` enum and `PERMISSION_CAPABILITIES` object matching backend.

### Step 2: Refactor Permission Hook
- In `src/hooks/usePermissions.tsx`,
  - Use `PermissionLevel` enum for all permission checks.
  - Add properties for each capability (e.g. `canManageUsers`, `canCreateTemplates`, etc.)
  - Expose `capabilities` object for advanced checks.

### Step 3: Refactor PermissionGuard Component
- In `src/lib/permission.tsx`,
  - Update props to use `PermissionLevel` enum and capability keys.
  - Support `requiredPermission`, `requiredPermissions`, and `requiredCapability` props.
  - Use the new hook for all checks.

### Step 4: Update Route Protection
- In all route files using `PermissionGuard`,
  - Replace string literals with `PermissionLevel` enum values.
  - Use `requiredCapability` for granular access (e.g. `canManageUsers`).

### Step 5: Update UI Components
- In all components with permission-based rendering,
  - Replace checks like `if (userPermission === "Admin")` with `if (permissionGuard.canManageUsers)` or similar.
  - Use the `capabilities` object for advanced UI logic.

### Step 6: Update API Types
- In `src/lib/api.ts` and related files,
  - Update user and permission types to use `PermissionLevel`.
  - Ensure API responses include capabilities if needed.

### Step 7: Test Thoroughly
- Test all routes and UI for each permission level.
- Ensure all protected features are only visible to users with the correct capabilities.
- Add/Update tests for permission logic if present.

## 4. Example Migration

**Before (simple check):**
```tsx
if (userPermission === "Admin") {
  // show admin features
}
```

**After (capability check):**
```tsx
if (permissionGuard.canManageUsers) {
  // show admin features
}
```

**Before (route protection):**
```tsx
<PermissionGuard requiredPermission="Admin">
  <UserManagementPage />
</PermissionGuard>
```

**After (route protection):**
```tsx
<PermissionGuard requiredCapability="canManageUsers">
  <UserManagementPage />
</PermissionGuard>
```

**Before (menu rendering):**
```tsx
{userPermission === "Admin" && (
  <MenuItem to="/admin">Admin Panel</MenuItem>
)}
```

**After (menu rendering):**
```tsx
{permissionGuard.canManageUsers && (
  <MenuItem to="/admin">Admin Panel</MenuItem>
)}
```

**Before (API types):**
```ts
export type User = {
  id: string;
  name: string;
  permission: string; // e.g. "Admin", "User"
};
```

**After (API types):**
```ts
import { PermissionLevel } from "./permission-constants";

export type User = {
  id: string;
  name: string;
  permission: PermissionLevel;
  capabilities: string[]; // e.g. ["canManageUsers", "canCreateTemplates"]
};
```

## 5. Files to Update (Checklist)

### Core Permission Logic
- [x] `src/lib/permission-constants.ts`
- [x] `src/lib/permission.tsx`
- [x] `src/hooks/usePermissions.tsx`

### API & Types
- [ ] `src/lib/api.ts`
- [ ] Any other files defining or using user/permission types

### Route Protection (examples, not exhaustive)
- [x] `src/routes/_layout/admin/user-management/index.tsx`
- [x] `src/routes/_layout/admin/users/$userId.tsx`
- [x] `src/routes/_layout/admin/deleted-jobs/index.tsx`
- [x] `src/routes/_layout/prompt-management/index.tsx`
- [x] `src/routes/_layout/audio-upload/index.tsx`
- [ ] `src/routes/_layout/admin/settings/index.tsx`
- [ ] `src/routes/_layout/admin/roles/index.tsx`
- [ ] `src/routes/_layout/admin/audit-log/index.tsx`
- [ ] `src/routes/_layout/admin/permissions/index.tsx`
- [ ] Any other admin or protected route files

### UI Components
- [ ] `src/components/app-sidebar.tsx`
- [ ] `src/components/admin-menu.tsx`
- [ ] `src/components/user-menu.tsx`
- [ ] `src/components/settings-panel.tsx`
- [ ] Any other components with permission-based rendering

### Tests
- [ ] `src/hooks/usePermissions.test.tsx`
- [ ] `src/lib/permission.test.tsx`
- [ ] Any other tests for permission logic or protected routes/components

## 6. Summary
- This migration ensures the frontend is fully aligned with the backend permission model.
- All permission logic is now centralized, granular, and easy to maintain.
- Follow this guide step by step for a smooth migration.
