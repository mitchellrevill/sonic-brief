// Enhanced Permission Hook for React Frontend
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { useMemo } from 'react';

export type PermissionLevel = 'Admin' | 'User' | 'Viewer';

export interface UserPermissions {
  user_id: string;
  email: string;
  permission: PermissionLevel;
  capabilities: {
    can_view: boolean;
    can_edit: boolean;
    can_admin: boolean;
    can_manage_users: boolean;
    can_create_content: boolean;
    can_delete_content: boolean;
  };
}

export interface PermissionStats {
  counts: Record<PermissionLevel, number>;
  percentages: Record<PermissionLevel, number>;
  total_users: number;
}

// Permission hierarchy for frontend validation
const PERMISSION_HIERARCHY: Record<PermissionLevel, number> = {
  'Viewer': 1,
  'User': 2,
  'Admin': 3,
};

/**
 * Check if user has required permission level (hierarchical)
 */
export const hasPermission = (userPermission: PermissionLevel, requiredPermission: PermissionLevel): boolean => {
  const userLevel = PERMISSION_HIERARCHY[userPermission] || 0;
  const requiredLevel = PERMISSION_HIERARCHY[requiredPermission] || 0;
  return userLevel >= requiredLevel;
};

/**
 * Check if user has any of the required permissions
 */
export const hasAnyPermission = (userPermission: PermissionLevel, requiredPermissions: PermissionLevel[]): boolean => {
  return requiredPermissions.some(required => hasPermission(userPermission, required));
};

/**
 * Get user's current permissions from API
 */
export const useUserPermissions = () => {
  return useQuery<UserPermissions>({
    queryKey: ['user-permissions'],
    queryFn: async () => {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('No authentication token found');
      }

      const response = await fetch('/api/auth/users/me/permissions', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch user permissions');
      }

      const result = await response.json();
      
      // Handle backend response format
      if (result.status === 200 && result.data) {
        return result.data;
      } else {
        throw new Error(result.message || 'Failed to fetch user permissions');
      }
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
    queryFn: async () => {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('No authentication token found');
      }

      const response = await fetch('/api/auth/users/permission-stats', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch permission statistics');
      }

      const result = await response.json();
      
      // Handle backend response format
      if (result.status === 200 && result.data) {
        return result.data;
      } else {
        throw new Error(result.message || 'Failed to fetch permission statistics');
      }
    },
    enabled: userPermissions?.permission === 'Admin',
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
    queryFn: async () => {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('No authentication token found');
      }

      const response = await fetch(`/api/auth/users/by-permission/${permissionLevel}?limit=${limit}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch users by permission');
      }

      const result = await response.json();
      
      // Handle backend response format
      if (result.status === 200 && result.data) {
        return result.data;
      } else {
        throw new Error(result.message || 'Failed to fetch users by permission');
      }
    },
    enabled: userPermissions?.permission === 'Admin',
    staleTime: 5 * 60 * 1000,
  });
};

/**
 * Update user permission mutation
 */
export const useUpdateUserPermission = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ userId, newPermission }: { userId: string; newPermission: PermissionLevel }) => {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('No authentication token found');
      }

      const response = await fetch(`/api/auth/users/${userId}/permission`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ permission: newPermission }),
      });

      if (!response.ok) {
        const result = await response.json();
        throw new Error(result.detail || result.message || 'Failed to update user permission');
      }

      const result = await response.json();
      
      // Handle backend response format
      if (result.status === 200) {
        return result;
      } else {
        throw new Error(result.message || 'Failed to update user permission');
      }
    },
    onSuccess: () => {
      // Invalidate relevant queries
      queryClient.invalidateQueries({ queryKey: ['users-by-permission'] });
      queryClient.invalidateQueries({ queryKey: ['permission-stats'] });
      queryClient.invalidateQueries({ queryKey: ['user-permissions'] });
    },
  });
};

/**
 * Custom hook for permission-based UI control
 */
export const usePermissionGuard = () => {
  const { data: userPermissions, isLoading, error } = useUserPermissions();
  
  const permissionGuard = useMemo(() => ({
    // Permission checks
    hasPermission: (requiredPermission: PermissionLevel) => {
      if (!userPermissions) return false;
      return hasPermission(userPermissions.permission, requiredPermission);
    },
    
    hasAnyPermission: (requiredPermissions: PermissionLevel[]) => {
      if (!userPermissions) return false;
      return hasAnyPermission(userPermissions.permission, requiredPermissions);
    },
    
    // Capability checks
    canView: userPermissions?.capabilities.can_view || false,
    canEdit: userPermissions?.capabilities.can_edit || false,
    canAdmin: userPermissions?.capabilities.can_admin || false,
    canManageUsers: userPermissions?.capabilities.can_manage_users || false,
    canCreateContent: userPermissions?.capabilities.can_create_content || false,
    canDeleteContent: userPermissions?.capabilities.can_delete_content || false,
    
    // User info
    currentPermission: userPermissions?.permission || 'Viewer',
    userEmail: userPermissions?.email,
    userId: userPermissions?.user_id,
    
    // Loading state
    isLoading,
    error,
  }), [userPermissions, isLoading, error]);
  
  return permissionGuard;
};

/**
 * Permission-based route guard component
 */
interface PermissionGuardProps {
  requiredPermission?: PermissionLevel;
  requiredPermissions?: PermissionLevel[];
  fallback?: React.ReactNode;
  children: React.ReactNode;
}

export const PermissionGuard: React.FC<PermissionGuardProps> = ({
  requiredPermission,
  requiredPermissions,
  fallback = <div>Access Denied: Insufficient permissions</div>,
  children,
}) => {
  const { hasPermission: checkPermission, hasAnyPermission: checkAnyPermission, isLoading } = usePermissionGuard();
  
  if (isLoading) {
    return <div>Loading permissions...</div>;
  }
  
  // Check single permission
  if (requiredPermission && !checkPermission(requiredPermission)) {
    return <>{fallback}</>;
  }
  
  // Check multiple permissions (any)
  if (requiredPermissions && !checkAnyPermission(requiredPermissions)) {
    return <>{fallback}</>;
  }
  
  return <>{children}</>;
};

/**
 * Permission-based component visibility hook
 */
export const useConditionalRender = () => {
  const permissionGuard = usePermissionGuard();
  
  return {
    // Show component only for specific permission
    showForPermission: (requiredPermission: PermissionLevel, component: React.ReactNode) => {
      return permissionGuard.hasPermission(requiredPermission) ? component : null;
    },
    
    // Show component for any of the specified permissions
    showForAnyPermission: (requiredPermissions: PermissionLevel[], component: React.ReactNode) => {
      return permissionGuard.hasAnyPermission(requiredPermissions) ? component : null;
    },
    
    // Show component based on capability
    showForCapability: (capability: keyof typeof permissionGuard, component: React.ReactNode) => {
      return permissionGuard[capability] ? component : null;
    },
    
    ...permissionGuard,
  };
};

// Export permission levels for use in components
export const PERMISSION_LEVELS = {
  ADMIN: 'Admin' as const,
  USER: 'User' as const,
  VIEWER: 'Viewer' as const,
};

// Utility function to get permission badge color
export const getPermissionBadgeColor = (permission: PermissionLevel): string => {
  switch (permission) {
    case 'Admin':
      return 'bg-red-100 text-red-800 border-red-200';
    case 'User':
      return 'bg-blue-100 text-blue-800 border-blue-200';
    case 'Viewer':
      return 'bg-gray-100 text-gray-800 border-gray-200';
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200';
  }
};

// Utility function to get permission icon
export const getPermissionIcon = (permission: PermissionLevel): string => {
  switch (permission) {
    case 'Admin':
      return '👑'; // Crown
    case 'User':
      return '🔧'; // Wrench
    case 'Viewer':
      return '👁️'; // Eye
    default:
      return '❓'; // Question mark
  }
};
