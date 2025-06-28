/**
 * Frontend permission utilities for the resource-based permission system
 */
import { 
  PermissionLevel, 
  Capability,
  type UserCapabilities,
  hasCapability,
  hasAnyCapability,
  hasAllCapabilities,
  hasPermissionLevel as typeHasPermissionLevel,
  getCapabilitiesForPermission
} from '../types/permissions';

export interface User {
  id: string;
  permission: PermissionLevel;
  capabilities?: string[];
  custom_capabilities?: UserCapabilities;
  email?: string;
  name?: string;
}

export interface Resource {
  id: string;
  user_id: string;
  shared_with?: Array<{
    user_id: string;
    permission_level?: PermissionLevel;
  }>;
}

/**
 * Check if a user has a specific permission level or higher
 */
export function hasPermissionLevel(
  userLevel: PermissionLevel, 
  requiredLevel: PermissionLevel
): boolean {
  return typeHasPermissionLevel(userLevel, requiredLevel);
}

/**
 * Check if a user can perform a specific action (capability)
 */
export function canUserPerformAction(
  user: User,
  capability: Capability
): boolean {
  if (!user) return false;
  
  // Use user's custom capabilities if available, otherwise get defaults from permission level
  const userCapabilities = user.custom_capabilities || getCapabilitiesForPermission(user.permission);
  
  return hasCapability(userCapabilities, capability);
}

/**
 * Check if a user can perform any of the specified actions
 */
export function canUserPerformAnyAction(
  user: User,
  capabilities: Capability[]
): boolean {
  if (!user) return false;
  
  const userCapabilities = user.custom_capabilities || getCapabilitiesForPermission(user.permission);
  
  return hasAnyCapability(userCapabilities, capabilities);
}

/**
 * Check if a user can perform all of the specified actions
 */
export function canUserPerformAllActions(
  user: User,
  capabilities: Capability[]
): boolean {
  if (!user) return false;
  
  const userCapabilities = user.custom_capabilities || getCapabilitiesForPermission(user.permission);
  
  return hasAllCapabilities(userCapabilities, capabilities);
}

/**
 * Check if a user has access to a resource
 */
export function checkResourceAccess(
  resource: Resource,
  user: User,
  requiredCapability: Capability = Capability.CAN_VIEW_OWN_JOBS
): boolean {
  if (!resource || !user) return false;
  
  // Check if user can view all resources (system-wide capability)
  if (canUserPerformAction(user, Capability.CAN_MANAGE_SYSTEM)) {
    return true;
  }
  
  // Check if user is the owner/creator
  if (resource.user_id === user.id) {
    return true;
  }
  
  // Check shared permissions
  if (resource.shared_with) {
    const userShare = resource.shared_with.find(share => share.user_id === user.id);
    if (userShare && userShare.permission_level) {
      return hasPermissionLevel(userShare.permission_level, getRequiredLevelForCapability(requiredCapability));
    }
  }
  
  return false;
}

/**
 * Get the minimum permission level required for a capability
 */
function getRequiredLevelForCapability(capability: Capability): PermissionLevel {
  const adminCapabilities = [
    Capability.CAN_DELETE_ALL_JOBS,
    Capability.CAN_DELETE_USERS,
    Capability.CAN_MANAGE_SYSTEM,
    Capability.CAN_MANAGE_USERS
  ];
  
  const editorCapabilities = [
    Capability.CAN_CREATE_JOBS,
    Capability.CAN_EDIT_SHARED_JOBS,
    Capability.CAN_CREATE_USERS,
    Capability.CAN_EDIT_USERS,
    Capability.CAN_EDIT_SETTINGS,
    Capability.CAN_EXPORT_DATA,
    Capability.CAN_IMPORT_DATA
  ];
  
  if (adminCapabilities.includes(capability)) {
    return PermissionLevel.ADMIN;
  } else if (editorCapabilities.includes(capability)) {
    return PermissionLevel.EDITOR;
  } else {
    return PermissionLevel.USER;
  }
}

/**
 * Get the user's effective permission level for a specific resource
 */
export function getUserResourcePermissionLevel(
  resource: Resource,
  user: User
): PermissionLevel | null {
  if (!resource || !user) return null;
  
  // System managers have full access
  if (canUserPerformAction(user, Capability.CAN_MANAGE_SYSTEM)) {
    return PermissionLevel.ADMIN;
  }
  
  // Check if user is the owner/creator
  if (resource.user_id === user.id) {
    return user.permission;
  }
  
  // Check shared permissions
  if (resource.shared_with) {
    const userShare = resource.shared_with.find(share => share.user_id === user.id);
    if (userShare && userShare.permission_level) {
      return userShare.permission_level;
    }
  }
  
  return null; // No access
}
