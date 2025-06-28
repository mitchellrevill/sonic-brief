# Simplified Feature-Based Permissions System

## Overview

The Sonic Brief application now uses a simplified feature-based permissions system that allows administrators to enable or disable specific features for each user individually. This provides granular control over what each user can do within the application.

## Key Concepts

### 1. Feature Toggles (Instead of Complex Permissions)

Each feature in the application is represented by a simple toggle that can be enabled or disabled per user:

```typescript
export enum FeatureToggle {
  // Core Features
  CREATE_JOBS = "create_jobs",
  EDIT_JOBS = "edit_jobs", 
  DELETE_JOBS = "delete_jobs",
  EXPORT_JOBS = "export_jobs",
  
  // Sharing & Collaboration
  SHARE_JOBS = "share_jobs",
  VIEW_SHARED_JOBS = "view_shared_jobs",
  
  // Templates
  CREATE_TEMPLATES = "create_templates",
  EDIT_TEMPLATES = "edit_templates",
  DELETE_TEMPLATES = "delete_templates",
  
  // Advanced Features
  BULK_OPERATIONS = "bulk_operations",
  CHANGE_TRANSCRIPTION_METHOD = "change_transcription_method",
  ADVANCED_SETTINGS = "advanced_settings",
  
  // Analytics & Reporting
  VIEW_ANALYTICS = "view_analytics",
  VIEW_REPORTS = "view_reports",
  
  // Admin Features
  MANAGE_USERS = "manage_users",
  SYSTEM_SETTINGS = "system_settings",
  VIEW_LOGS = "view_logs",
}
```

### 2. User Feature Configuration

Each user has a `features` object that specifies which features are enabled:

```typescript
interface User {
  id: string;
  email: string;
  name?: string;
  features: UserFeatures; // The main configuration
  permission?: PermissionLevel; // Legacy field for compatibility
}
```

### 3. Role Templates (Optional Quick Setup)

For convenience, there are role templates that provide default feature sets:

- **User**: Basic features (create, edit, delete own jobs, export)
- **Editor**: User features + templates, sharing, analytics
- **Admin**: All features enabled

## Implementation

### 1. UserFeatureManager Component

The main component for managing user features:

```typescript
<UserFeatureManager
  user={user}
  onUpdateFeatures={handleUpdateFeatures}
  onCopyFeatures={handleCopyFeatures}
  allUsers={allUsers}
  readOnly={false}
/>
```

**Key Features:**
- Toggle individual features on/off
- Apply role templates for quick setup
- Copy feature settings from another user
- Organized into logical groups (Core, Templates, Admin, etc.)
- Real-time preview of changes
- Save/reset functionality

### 2. Integration with User Management

```typescript
// Example integration in user list
<UserFeatureManagement 
  user={user}
  allUsers={allUsers}
  onUpdateUser={updateUserFunction}
/>
```

### 3. Feature Checking in Components

```typescript
// Check if user has a specific feature
if (userHasFeature(user, FeatureToggle.CREATE_JOBS)) {
  // Show create job button
}

// Check if user has multiple features
if (userHasAllFeatures(user, [FeatureToggle.CREATE_JOBS, FeatureToggle.EDIT_JOBS])) {
  // Show advanced job management
}
```

## Feature Groups

Features are organized into logical groups for better UX:

1. **Core Features**: Basic job operations (create, edit, delete, export)
2. **Sharing & Collaboration**: Share jobs, view shared content
3. **Templates**: Create and manage job templates
4. **Advanced Features**: Bulk operations, transcription settings
5. **Analytics & Reporting**: View metrics and generate reports
6. **Administration**: User management, system settings, logs

## API Integration

### Frontend to Backend

```typescript
// Convert frontend format to API format
const apiPermissions = convertToApiFormat(user.features);

// Convert API format to frontend format
const userFeatures = convertFromApiFormat(apiResponse.permissions);
```

### Backend Expected Format

```json
{
  "create_jobs": true,
  "edit_jobs": true,
  "delete_jobs": false,
  "manage_users": false,
  // ... other features
}
```

## Migration from Old System

The new system maintains backward compatibility:

1. **Legacy Types**: Old `PermissionCapability` type is aliased to `FeatureToggle`
2. **Role Templates**: Existing permission levels can be converted to feature sets
3. **Gradual Migration**: Components can be updated one by one

## Usage Examples

### 1. Basic Feature Check

```typescript
// In a component
const canCreateJobs = userHasFeature(currentUser, FeatureToggle.CREATE_JOBS);

return (
  <div>
    {canCreateJobs && (
      <Button onClick={createJob}>Create New Job</Button>
    )}
  </div>
);
```

### 2. Feature Management Dialog

```typescript
const [showFeatureManager, setShowFeatureManager] = useState(false);

return (
  <Dialog open={showFeatureManager} onOpenChange={setShowFeatureManager}>
    <DialogTrigger asChild>
      <Button>Manage Features</Button>
    </DialogTrigger>
    <DialogContent>
      <UserFeatureManager
        user={selectedUser}
        onUpdateFeatures={updateFeatures}
        allUsers={users}
      />
    </DialogContent>
  </Dialog>
);
```

### 3. Quick Feature Indicators

```typescript
// Show visual indicators for enabled features
<div className="flex gap-1">
  {user.features.create_jobs && (
    <Badge variant="secondary">Create</Badge>
  )}
  {user.features.manage_users && (
    <Badge variant="secondary">Admin</Badge>
  )}
  {user.features.view_analytics && (
    <Badge variant="secondary">Analytics</Badge>
  )}
</div>
```

## Benefits

1. **Simplicity**: Clear, understandable feature toggles
2. **Flexibility**: Granular control over individual features
3. **User Experience**: Organized groups, visual feedback
4. **Maintainability**: Easy to add new features
5. **Performance**: Simple boolean checks
6. **Auditability**: Clear trail of what features users have

## Next Steps

1. **Backend Integration**: Update API endpoints to support the new feature format
2. **Component Updates**: Update existing components to use `userHasFeature()` checks
3. **Testing**: Add comprehensive tests for feature checking logic
4. **Documentation**: Update user-facing documentation
5. **Migration Script**: Create script to convert existing users to new format

## Files Modified

- `src/types/permissions.ts`: Complete rewrite for simplified system
- `src/components/user-managment/UserManagement/UserFeatureManager.tsx`: New feature management UI
- `src/components/user-managment/UserManagement/UserFeatureManagement.tsx`: Integration example

## API Endpoints Needed

```typescript
// Update user features
PUT /api/users/{userId}/features
{
  "features": {
    "create_jobs": true,
    "edit_jobs": true,
    // ... other features
  }
}

// Get user with features
GET /api/users/{userId}
{
  "id": "user123",
  "email": "user@example.com",
  "features": { ... }
}
```

This simplified system provides all the flexibility needed for per-user feature control while being much easier to understand and maintain than the previous complex permission system.
