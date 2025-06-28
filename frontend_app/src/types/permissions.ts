// Resource-based permission system for Sonic Brief - matches backend

export enum PermissionLevel {
  USER = "User",
  EDITOR = "Editor", 
  ADMIN = "Admin"
}

export enum Capability {
  // Job/Transcription Management
  CAN_VIEW_OWN_JOBS = "can_view_own_jobs",
  CAN_CREATE_JOBS = "can_create_jobs",
  CAN_EDIT_OWN_JOBS = "can_edit_own_jobs",
  CAN_DELETE_OWN_JOBS = "can_delete_own_jobs",
  CAN_VIEW_SHARED_JOBS = "can_view_shared_jobs",
  CAN_EDIT_SHARED_JOBS = "can_edit_shared_jobs",
  CAN_DELETE_SHARED_JOBS = "can_delete_shared_jobs",
  CAN_SHARE_JOBS = "can_share_jobs",
  CAN_VIEW_ALL_JOBS = "can_view_all_jobs",
  CAN_EDIT_ALL_JOBS = "can_edit_all_jobs",
  CAN_DELETE_ALL_JOBS = "can_delete_all_jobs",

  // Prompt/Template Management
  CAN_VIEW_PROMPTS = "can_view_prompts",
  CAN_CREATE_PROMPTS = "can_create_prompts",
  CAN_EDIT_PROMPTS = "can_edit_prompts",
  CAN_DELETE_PROMPTS = "can_delete_prompts",
  CAN_CREATE_TEMPLATES = "can_create_templates",

  // User Management
  CAN_VIEW_USERS = "can_view_users",
  CAN_CREATE_USERS = "can_create_users",
  CAN_EDIT_USERS = "can_edit_users",
  CAN_DELETE_USERS = "can_delete_users",
  CAN_MANAGE_USERS = "can_manage_users",

  // System/Settings
  CAN_VIEW_SETTINGS = "can_view_settings",
  CAN_EDIT_SETTINGS = "can_edit_settings",
  CAN_VIEW_ANALYTICS = "can_view_analytics",
  CAN_MANAGE_SYSTEM = "can_manage_system",

  // File Operations
  CAN_UPLOAD_FILES = "can_upload_files",
  CAN_DOWNLOAD_FILES = "can_download_files",
  CAN_EXPORT_DATA = "can_export_data",
  CAN_IMPORT_DATA = "can_import_data",

  // Legacy capabilities for backward compatibility
  VIEW_TRANSCRIPTIONS = "can_view_own_jobs",
  CREATE_TRANSCRIPTIONS = "can_create_jobs",
  EDIT_TRANSCRIPTIONS = "can_edit_own_jobs",
  DELETE_TRANSCRIPTIONS = "can_delete_own_jobs",
  VIEW_USERS = "can_view_users",
  CREATE_USERS = "can_create_users",
  EDIT_USERS = "can_edit_users",
  DELETE_USERS = "can_delete_users",
  VIEW_SETTINGS = "can_view_settings",
  EDIT_SETTINGS = "can_edit_settings",
  MANAGE_SYSTEM = "can_manage_system",
  VIEW_ANALYTICS = "can_view_analytics",
  EXPORT_DATA = "can_export_data",
  IMPORT_DATA = "can_import_data"
}

export interface UserCapabilities {
  [key: string]: boolean;
}

// Permission hierarchy (higher number = more permissions)
export const PERMISSION_HIERARCHY: Record<PermissionLevel, number> = {
  [PermissionLevel.USER]: 1,
  [PermissionLevel.EDITOR]: 2,
  [PermissionLevel.ADMIN]: 3,
};

// Default capabilities for each permission level (matches backend)
export const DEFAULT_CAPABILITIES: Record<PermissionLevel, Capability[]> = {
  [PermissionLevel.USER]: [
    Capability.CAN_VIEW_OWN_JOBS,
    Capability.CAN_CREATE_JOBS,
    Capability.CAN_EDIT_OWN_JOBS,
    Capability.CAN_DELETE_OWN_JOBS,
    Capability.CAN_VIEW_SHARED_JOBS,
    Capability.CAN_VIEW_PROMPTS,
    Capability.CAN_VIEW_SETTINGS,
    Capability.CAN_UPLOAD_FILES,
    Capability.CAN_DOWNLOAD_FILES,
  ],
  [PermissionLevel.EDITOR]: [
    Capability.CAN_VIEW_OWN_JOBS,
    Capability.CAN_CREATE_JOBS,
    Capability.CAN_EDIT_OWN_JOBS,
    Capability.CAN_DELETE_OWN_JOBS,
    Capability.CAN_VIEW_SHARED_JOBS,
    Capability.CAN_EDIT_SHARED_JOBS,
    Capability.CAN_DELETE_SHARED_JOBS,
    Capability.CAN_SHARE_JOBS,
    Capability.CAN_VIEW_PROMPTS,
    Capability.CAN_CREATE_PROMPTS,
    Capability.CAN_EDIT_PROMPTS,
    Capability.CAN_CREATE_TEMPLATES,
    Capability.CAN_VIEW_SETTINGS,
    Capability.CAN_EDIT_SETTINGS,
    Capability.CAN_UPLOAD_FILES,
    Capability.CAN_DOWNLOAD_FILES,
    Capability.CAN_EXPORT_DATA,
  ],
  [PermissionLevel.ADMIN]: [
    // All capabilities enabled for admin
    Capability.CAN_VIEW_OWN_JOBS,
    Capability.CAN_CREATE_JOBS,
    Capability.CAN_EDIT_OWN_JOBS,
    Capability.CAN_DELETE_OWN_JOBS,
    Capability.CAN_VIEW_SHARED_JOBS,
    Capability.CAN_EDIT_SHARED_JOBS,
    Capability.CAN_DELETE_SHARED_JOBS,
    Capability.CAN_SHARE_JOBS,
    Capability.CAN_VIEW_ALL_JOBS,
    Capability.CAN_EDIT_ALL_JOBS,
    Capability.CAN_DELETE_ALL_JOBS,
    Capability.CAN_VIEW_PROMPTS,
    Capability.CAN_CREATE_PROMPTS,
    Capability.CAN_EDIT_PROMPTS,
    Capability.CAN_DELETE_PROMPTS,
    Capability.CAN_CREATE_TEMPLATES,
    Capability.CAN_VIEW_USERS,
    Capability.CAN_CREATE_USERS,
    Capability.CAN_EDIT_USERS,
    Capability.CAN_DELETE_USERS,
    Capability.CAN_MANAGE_USERS,
    Capability.CAN_VIEW_SETTINGS,
    Capability.CAN_EDIT_SETTINGS,
    Capability.CAN_VIEW_ANALYTICS,
    Capability.CAN_MANAGE_SYSTEM,
    Capability.CAN_UPLOAD_FILES,
    Capability.CAN_DOWNLOAD_FILES,
    Capability.CAN_EXPORT_DATA,
    Capability.CAN_IMPORT_DATA,
  ]
};

// Grouped capabilities for UI display
export const CAPABILITY_GROUPS = {
  jobs: {
    label: "Job Management",
    capabilities: [
      Capability.CAN_VIEW_OWN_JOBS,
      Capability.CAN_CREATE_JOBS,
      Capability.CAN_EDIT_OWN_JOBS,
      Capability.CAN_DELETE_OWN_JOBS,
      Capability.CAN_VIEW_SHARED_JOBS,
      Capability.CAN_EDIT_SHARED_JOBS,
      Capability.CAN_DELETE_SHARED_JOBS,
      Capability.CAN_SHARE_JOBS,
      Capability.CAN_VIEW_ALL_JOBS,
      Capability.CAN_EDIT_ALL_JOBS,
      Capability.CAN_DELETE_ALL_JOBS,
    ]
  },
  prompts: {
    label: "Prompt Management", 
    capabilities: [
      Capability.CAN_VIEW_PROMPTS,
      Capability.CAN_CREATE_PROMPTS,
      Capability.CAN_EDIT_PROMPTS,
      Capability.CAN_DELETE_PROMPTS,
      Capability.CAN_CREATE_TEMPLATES,
    ]
  },
  users: {
    label: "User Management", 
    capabilities: [
      Capability.CAN_VIEW_USERS,
      Capability.CAN_CREATE_USERS,
      Capability.CAN_EDIT_USERS,
      Capability.CAN_DELETE_USERS,
      Capability.CAN_MANAGE_USERS,
    ]
  },
  settings: {
    label: "Settings",
    capabilities: [
      Capability.CAN_VIEW_SETTINGS,
      Capability.CAN_EDIT_SETTINGS,
      Capability.CAN_VIEW_ANALYTICS,
      Capability.CAN_MANAGE_SYSTEM,
    ]
  },
  files: {
    label: "File Operations",
    capabilities: [
      Capability.CAN_UPLOAD_FILES,
      Capability.CAN_DOWNLOAD_FILES,
      Capability.CAN_EXPORT_DATA,
      Capability.CAN_IMPORT_DATA,
    ]
  }
};

// Utility functions for permission checks
export function hasCapability(userCapabilities: UserCapabilities, capability: Capability): boolean {
  return userCapabilities[capability] === true;
}

export function hasAnyCapability(userCapabilities: UserCapabilities, capabilities: Capability[]): boolean {
  return capabilities.some(cap => hasCapability(userCapabilities, cap));
}

export function hasAllCapabilities(userCapabilities: UserCapabilities, capabilities: Capability[]): boolean {
  return capabilities.every(cap => hasCapability(userCapabilities, cap));
}

// Convert between backend array format and frontend object format
export function capabilitiesToArray(userCapabilities: UserCapabilities): string[] {
  return Object.entries(userCapabilities)
    .filter(([_, enabled]) => enabled)
    .map(([capability, _]) => capability);
}

export function capabilitiesFromArray(capabilities: string[]): UserCapabilities {
  const result: UserCapabilities = {};
  
  // Initialize all capabilities to false
  Object.values(Capability).forEach(cap => {
    result[cap] = false;
  });
  
  // Set enabled capabilities to true
  capabilities.forEach(cap => {
    if (Object.values(Capability).includes(cap as Capability)) {
      result[cap] = true;
    }
  });
  
  return result;
}

// Get user capabilities for a permission level
export function getUserCapabilities(level: PermissionLevel): UserCapabilities {
  const capabilities = DEFAULT_CAPABILITIES[level];
  return capabilitiesFromArray(capabilities);
}

// Get permission level from capabilities
export function getPermissionLevel(userCapabilities: UserCapabilities): PermissionLevel {
  const enabledCapabilities = capabilitiesToArray(userCapabilities) as Capability[];
  
  // Check if user has all admin capabilities
  const adminCapabilities = DEFAULT_CAPABILITIES[PermissionLevel.ADMIN];
  if (adminCapabilities.every(cap => enabledCapabilities.includes(cap))) {
    return PermissionLevel.ADMIN;
  }
  
  // Check if user has all editor capabilities  
  const editorCapabilities = DEFAULT_CAPABILITIES[PermissionLevel.EDITOR];
  if (editorCapabilities.every(cap => enabledCapabilities.includes(cap))) {
    return PermissionLevel.EDITOR;
  }
  
  // Default to user level
  return PermissionLevel.USER;
}

// Additional utility functions
export function hasPermissionLevel(userPermission: PermissionLevel, requiredPermission: PermissionLevel): boolean {
  const userLevel = PERMISSION_HIERARCHY[userPermission] || 0;
  const requiredLevel = PERMISSION_HIERARCHY[requiredPermission] || 0;
  return userLevel >= requiredLevel;
}

export function arrayToCapabilities(capabilities: string[]): UserCapabilities {
  return capabilitiesFromArray(capabilities);
}

export function getCapabilitiesForPermission(permission: PermissionLevel): UserCapabilities {
  const capabilities = DEFAULT_CAPABILITIES[permission] || [];
  return capabilitiesFromArray(capabilities);
}

// Type for user data from API
export interface User {
  id: string;
  email: string;
  permission: PermissionLevel;
  capabilities?: string[];
  custom_capabilities?: UserCapabilities;
  created_at: string;
  updated_at?: string;
}

// Type for permission update requests
export interface PermissionUpdateRequest {
  permission?: PermissionLevel;
  custom_capabilities?: UserCapabilities;
}
