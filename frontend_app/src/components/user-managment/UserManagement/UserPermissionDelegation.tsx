import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { UserPlus, Shield, Clock, CheckCircle } from "lucide-react";
import { PermissionLevel } from "@/types/permissions";
import type { User } from "@/lib/api";
import { toast } from "sonner";

interface PermissionDelegation {
  id: string;
  delegatedTo: string;
  delegatedBy: string;
  permission: PermissionLevel;
  scope: 'all' | 'specific';
  specificResources?: string[];
  expiresAt?: Date;
  reason: string;
  status: 'active' | 'expired' | 'revoked';
  createdAt: Date;
}

interface UserPermissionDelegationProps {
  currentUser: User;
  users: User[];
  onDelegate: (delegation: Omit<PermissionDelegation, 'id' | 'createdAt' | 'status'>) => Promise<void>;
  onRevoke: (delegationId: string) => Promise<void>;
  delegations: PermissionDelegation[];
}

export function UserPermissionDelegation({ 
  currentUser, 
  users, 
  onDelegate, 
  onRevoke, 
  delegations 
}: UserPermissionDelegationProps) {
  const [showDelegateDialog, setShowDelegateDialog] = useState(false);
  const [selectedUser, setSelectedUser] = useState<string>("");
  const [delegatedPermission, setDelegatedPermission] = useState<PermissionLevel>(PermissionLevel.USER);
  const [scope, setScope] = useState<'all' | 'specific'>('all');
  const [specificResources, setSpecificResources] = useState<string[]>([]);
  const [reason, setReason] = useState("");
  const [expirationDays, setExpirationDays] = useState<number>(7);
  const [hasExpiration, setHasExpiration] = useState(true);
  const [loading, setLoading] = useState(false);

  // Filter users that can receive delegation (lower permission than current user)
  const eligibleUsers = (users || []).filter(user => {
    const userLevel = getPermissionLevel(user.permission);
    const currentLevel = getPermissionLevel(currentUser.permission);
    return userLevel < currentLevel && user.id !== currentUser.id;
  });

  // Get active delegations made by current user
  const activeDelegations = delegations.filter(d => 
    d.delegatedBy === currentUser.email && d.status === 'active'
  );

  // Get delegations received by current user
  const receivedDelegations = delegations.filter(d => 
    d.delegatedTo === currentUser.email && d.status === 'active'
  );

  function getPermissionLevel(permission: string): number {
    switch (permission) {
      case PermissionLevel.ADMIN: return 3;
      case PermissionLevel.EDITOR: return 2;
      case PermissionLevel.USER: return 1;
      default: return 0;
    }
  }

  function getUserInitials(email: string): string {
    return email.split('@')[0].slice(0, 2).toUpperCase();
  }

  const availablePermissions = (): PermissionLevel[] => {
    const currentLevel = getPermissionLevel(currentUser.permission);
    const permissions: PermissionLevel[] = [];
    
    if (currentLevel >= 2) permissions.push(PermissionLevel.USER);
    if (currentLevel >= 3) permissions.push(PermissionLevel.EDITOR);
    
    return permissions;
  };

  const handleDelegate = async () => {
    if (!selectedUser || !reason.trim()) {
      toast.error("Please select a user and provide a reason");
      return;
    }

    setLoading(true);
    try {
      const expiresAt = hasExpiration 
        ? new Date(Date.now() + expirationDays * 24 * 60 * 60 * 1000)
        : undefined;

      await onDelegate({
        delegatedTo: selectedUser,
        delegatedBy: currentUser.email,
        permission: delegatedPermission,
        scope,
        specificResources: scope === 'specific' ? specificResources : undefined,
        expiresAt,
        reason,
      });

      // Reset form
      setSelectedUser("");
      setDelegatedPermission(PermissionLevel.USER);
      setScope('all');
      setSpecificResources([]);
      setReason("");
      setExpirationDays(7);
      setHasExpiration(true);
      setShowDelegateDialog(false);
      
      toast.success("Permission delegated successfully");
    } catch (error) {
      console.error("Failed to delegate permission:", error);
      toast.error("Failed to delegate permission");
    } finally {
      setLoading(false);
    }
  };

  const handleRevoke = async (delegationId: string) => {
    try {
      await onRevoke(delegationId);
      toast.success("Permission delegation revoked");
    } catch (error) {
      console.error("Failed to revoke delegation:", error);
      toast.error("Failed to revoke delegation");
    }
  };

  const formatExpiresAt = (date: Date) => {
    const now = new Date();
    const diffHours = Math.ceil((date.getTime() - now.getTime()) / (1000 * 60 * 60));
    
    if (diffHours < 24) {
      return `${diffHours}h`;
    } else {
      const diffDays = Math.ceil(diffHours / 24);
      return `${diffDays}d`;
    }
  };

  // Only show if user has permission to delegate (Editor or Admin)
  if (getPermissionLevel(currentUser.permission) < 2) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Delegate Permission Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <UserPlus className="h-5 w-5" />
              Permission Delegation
            </CardTitle>
            <Dialog open={showDelegateDialog} onOpenChange={setShowDelegateDialog}>
              <DialogTrigger asChild>
                <Button size="sm" disabled={eligibleUsers.length === 0}>
                  <UserPlus className="mr-2 h-4 w-4" />
                  Delegate Permission
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-md">
                <DialogHeader>
                  <DialogTitle>Delegate Permission</DialogTitle>
                  <DialogDescription>
                    Temporarily grant permissions to another user
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label>Select User</Label>
                    <Select value={selectedUser} onValueChange={setSelectedUser}>
                      <SelectTrigger>
                        <SelectValue placeholder="Choose a user..." />
                      </SelectTrigger>
                      <SelectContent>
                        {eligibleUsers.map(user => (
                          <SelectItem key={user.id} value={user.email}>
                            <div className="flex items-center gap-2">
                              <Avatar className="h-6 w-6">
                                <AvatarFallback className="text-xs">
                                  {getUserInitials(user.email)}
                                </AvatarFallback>
                              </Avatar>
                              <span>{user.email}</span>
                              <Badge variant="outline" className="text-xs">
                                {user.permission}
                              </Badge>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label>Permission Level</Label>
                    <Select value={delegatedPermission} onValueChange={(value: PermissionLevel) => setDelegatedPermission(value)}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {availablePermissions().map(permission => (
                          <SelectItem key={permission} value={permission}>
                            {permission}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label>Scope</Label>
                    <Select value={scope} onValueChange={(value: 'all' | 'specific') => setScope(value)}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Resources</SelectItem>
                        <SelectItem value="specific">Specific Resources</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {scope === 'specific' && (
                    <div>
                      <Label>Resource IDs (comma-separated)</Label>
                      <Input
                        placeholder="resource1, resource2, ..."
                        value={specificResources.join(', ')}
                        onChange={(e) => setSpecificResources(
                          e.target.value.split(',').map(s => s.trim()).filter(Boolean)
                        )}
                      />
                    </div>
                  )}

                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="has-expiration"
                        checked={hasExpiration}
                        onCheckedChange={(checked) => setHasExpiration(!!checked)}
                      />
                      <Label htmlFor="has-expiration">Set expiration</Label>
                    </div>
                    {hasExpiration && (
                      <div>
                        <Label>Expires in (days)</Label>
                        <Input
                          type="number"
                          min="1"
                          max="30"
                          value={expirationDays}
                          onChange={(e) => setExpirationDays(Number(e.target.value))}
                        />
                      </div>
                    )}
                  </div>

                  <div>
                    <Label>Reason for delegation</Label>
                    <Textarea
                      placeholder="Explain why this delegation is needed..."
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      className="resize-none"
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setShowDelegateDialog(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleDelegate} disabled={loading}>
                    {loading ? "Delegating..." : "Delegate Permission"}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </CardHeader>
        <CardContent>
          {eligibleUsers.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No eligible users for permission delegation
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">
              You can delegate your permissions to {eligibleUsers.length} eligible user(s)
            </p>
          )}
        </CardContent>
      </Card>

      {/* Active Delegations Made */}
      {activeDelegations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Active Delegations Made
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {activeDelegations.map(delegation => (
                <div key={delegation.id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center gap-3">
                    <Avatar className="h-8 w-8">
                      <AvatarFallback className="text-xs">
                        {getUserInitials(delegation.delegatedTo)}
                      </AvatarFallback>
                    </Avatar>
                    <div>
                      <p className="font-medium text-sm">{delegation.delegatedTo}</p>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <Badge variant="secondary" className="text-xs">
                          {delegation.permission}
                        </Badge>
                        <span>•</span>
                        <span>{delegation.scope} scope</span>
                        {delegation.expiresAt && (
                          <>
                            <span>•</span>
                            <div className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {formatExpiresAt(delegation.expiresAt)}
                            </div>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleRevoke(delegation.id)}
                  >
                    Revoke
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Delegations Received */}
      {receivedDelegations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5" />
              Delegations Received
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {receivedDelegations.map(delegation => (
                <div key={delegation.id} className="flex items-center justify-between p-3 border rounded-lg bg-green-50 border-green-200">
                  <div className="flex items-center gap-3">
                    <Avatar className="h-8 w-8">
                      <AvatarFallback className="text-xs">
                        {getUserInitials(delegation.delegatedBy)}
                      </AvatarFallback>
                    </Avatar>
                    <div>
                      <p className="font-medium text-sm">From: {delegation.delegatedBy}</p>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <Badge variant="secondary" className="text-xs">
                          {delegation.permission}
                        </Badge>
                        <span>•</span>
                        <span>{delegation.scope} scope</span>
                        {delegation.expiresAt && (
                          <>
                            <span>•</span>
                            <div className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {formatExpiresAt(delegation.expiresAt)}
                            </div>
                          </>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        {delegation.reason}
                      </p>
                    </div>
                  </div>
                  <Badge variant="outline" className="text-green-700 border-green-300">
                    <CheckCircle className="h-3 w-3 mr-1" />
                    Active
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
