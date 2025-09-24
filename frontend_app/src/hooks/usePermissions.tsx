// Enhanced Permission Hook for React Frontend - Resource-based permission system
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { useMemo } from 'react';
import { getUserPermissions, getPermissionStats, getUsersByPermission, updateUserPermissionApi } from "@/lib/api";
import { 
  Capability,
  PermissionLevel,
  hasCapability,
  hasAnyCapability,
  hasAllCapabilities,
  getCapabilitiesForPermission
} from "@/types/permissions";
import type { UserCapabilities } from "@/types/permissions";

// Backend user interface
interface BackendUser {
  user_id: string;
  email: string;
  permission: PermissionLevel;
  capabilities?: string[];
  custom_capabilities?: UserCapabilities;
}

// Frontend user interface  
interface FrontendUser {
  user_id: string;
  email: string;
  permission: PermissionLevel;
  capabilities: UserCapabilities;
  effective_capabilities: UserCapabilities;
}

interface PermissionStats {
  total_users: number;
  by_permission: Record<PermissionLevel, number>;
}

/**
 * Get user's current permissions from API
 */
export const useUserPermissions = () => {
  return useQuery<FrontendUser>({
    queryKey: ['user-permissions'],
    queryFn: async () => {
  const backendUser: BackendUser = await getUserPermissions();

  // Normalize backend response: some backends return `permission_level` instead of `permission`
  const normalizedPermission = (backendUser as any).permission || (backendUser as any).permission_level || 'User';

  // Get base capabilities from permission level
  const baseCapabilities = getCapabilitiesForPermission(normalizedPermission as PermissionLevel);
      
      // Merge with custom capabilities if available
      const customCapabilities = (backendUser as any).custom_capabilities || (backendUser as any).customCapabilities || {};
      const effectiveCapabilities = { ...baseCapabilities, ...customCapabilities };

      return {
        // Ensure the frontend sees `permission` consistently
        ...backendUser,
        permission: normalizedPermission as PermissionLevel,
        capabilities: effectiveCapabilities,
        effective_capabilities: effectiveCapabilities,
        custom_capabilities: customCapabilities,
      } as any;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 1,
  });
};

/**
 * Permission statistics hook (Admin only)
 */
export const usePermissionStats = () => {
  const { data: userPermissions } = useUserPermissions();
  
  return useQuery<PermissionStats>({
    queryKey: ['permission-stats'],
    queryFn: getPermissionStats,
    enabled: hasCapability(userPermissions?.capabilities || {}, Capability.CAN_MANAGE_SYSTEM),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
};

/**
 * Users by permission hook (Admin only)
 */
export const useUsersByPermission = (permissionLevel: PermissionLevel, limit: number = 100) => {
  const { data: userPermissions } = useUserPermissions();
  
  return useQuery({
    queryKey: ['users-by-permission', permissionLevel, limit],
    queryFn: () => getUsersByPermission(permissionLevel, limit),
    enabled: hasCapability(userPermissions?.capabilities || {}, Capability.CAN_VIEW_USERS),
    staleTime: 5 * 60 * 1000,
  });
};

/**
 * Update user permission mutation
 */
export const useUpdateUserPermission = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ userId, newPermission }: { userId: string; newPermission: PermissionLevel }) => 
      updateUserPermissionApi(userId, newPermission),
    onSuccess: () => {
      // Invalidate relevant queries
      queryClient.invalidateQueries({ queryKey: ['users-by-permission'] });
      queryClient.invalidateQueries({ queryKey: ['permission-stats'] });
      queryClient.invalidateQueries({ queryKey: ['user-permissions'] });
    },
  });
};

/**
 * Custom hook for capability-based UI control
 */
export const useCapabilityGuard = () => {
  const { data: userPermissions, isLoading, error } = useUserPermissions();
  
  const capabilityGuard = useMemo(() => {
    const capabilities = userPermissions?.capabilities || {};
    
    return {
      // Core capability checks
      hasCapability: (capability: Capability) => hasCapability(capabilities, capability),
      hasAnyCapability: (caps: Capability[]) => hasAnyCapability(capabilities, caps),
      hasAllCapabilities: (caps: Capability[]) => hasAllCapabilities(capabilities, caps),
      
      // Specific capability shortcuts
      canViewTranscriptions: hasCapability(capabilities, Capability.CAN_VIEW_OWN_JOBS),
      canCreateTranscriptions: hasCapability(capabilities, Capability.CAN_CREATE_JOBS),
      canEditTranscriptions: hasCapability(capabilities, Capability.CAN_EDIT_OWN_JOBS),
      canDeleteTranscriptions: hasCapability(capabilities, Capability.CAN_DELETE_OWN_JOBS),
      
      canViewUsers: hasCapability(capabilities, Capability.CAN_VIEW_USERS),
      canCreateUsers: hasCapability(capabilities, Capability.CAN_CREATE_USERS),
      canEditUsers: hasCapability(capabilities, Capability.CAN_EDIT_USERS),
      canDeleteUsers: hasCapability(capabilities, Capability.CAN_DELETE_USERS),
      
      canViewSettings: hasCapability(capabilities, Capability.CAN_VIEW_SETTINGS),
      canEditSettings: hasCapability(capabilities, Capability.CAN_EDIT_SETTINGS),
      
      canManageSystem: hasCapability(capabilities, Capability.CAN_MANAGE_SYSTEM),
      canViewAnalytics: hasCapability(capabilities, Capability.CAN_VIEW_ANALYTICS),
      
      canExportData: hasCapability(capabilities, Capability.CAN_EXPORT_DATA),
      canImportData: hasCapability(capabilities, Capability.CAN_IMPORT_DATA),
      
      // User info
      currentPermission: userPermissions?.permission || PermissionLevel.USER,
      userEmail: userPermissions?.email,
      userId: userPermissions?.user_id,
      capabilities,
      
      // Loading state
      isLoading,
      error,
    };
  }, [userPermissions, isLoading, error]);
  
  return capabilityGuard;
};

/**
 * Legacy permission hook for backward compatibility during transition
 */
export const usePermissionGuard = useCapabilityGuard;

/**
 * Capability-based component visibility hook
 */
export const useConditionalRender = () => {
  const capabilityGuard = useCapabilityGuard();
  
  return {
    // Show component only for specific capability
    showForCapability: (capability: Capability, component: React.ReactNode) => {
      return capabilityGuard.hasCapability(capability) ? component : null;
    },
    
    // Show component for any of the specified capabilities
    showForAnyCapability: (capabilities: Capability[], component: React.ReactNode) => {
      return capabilityGuard.hasAnyCapability(capabilities) ? component : null;
    },
    
    // Show component for all specified capabilities
    showForAllCapabilities: (capabilities: Capability[], component: React.ReactNode) => {
      return capabilityGuard.hasAllCapabilities(capabilities) ? component : null;
    },
    
    ...capabilityGuard,
  };
};

// Export capability values for use in components
export const CAPABILITIES = Capability;

// Utility function to get permission badge color
export const getPermissionBadgeColor = (permission: PermissionLevel): string => {
  switch (permission) {
    case PermissionLevel.ADMIN:
      return 'bg-red-100 text-red-800 border-red-200';
    case PermissionLevel.EDITOR:
      return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    case PermissionLevel.USER:
      return 'bg-blue-100 text-blue-800 border-blue-200';
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200';
  }
};

// Utility function to get permission icon
export const getPermissionIcon = (permission: PermissionLevel): string => {
  switch (permission) {
    case PermissionLevel.ADMIN:
      return '👑'; // Crown
    case PermissionLevel.EDITOR:
      return '✏️'; // Pencil
    case PermissionLevel.USER:
      return '👤'; // User
    default:
      return '❓'; // Question mark
  }
};
