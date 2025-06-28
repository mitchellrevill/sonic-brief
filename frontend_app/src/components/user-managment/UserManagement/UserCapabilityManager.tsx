import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Shield, ChevronDown, Save, RotateCcw, CheckCircle, AlertTriangle, Copy } from "lucide-react";
import { 
  Capability, 
  PermissionLevel, 
  type UserCapabilities, 
  CAPABILITY_GROUPS,
  getCapabilitiesForPermission,
  type User as UserType 
} from "@/types/permissions";
import { updateUserCapabilities } from "@/lib/api";
import { toast } from "sonner";

interface UserCapabilityManagerProps {
  user: UserType;
  onUpdateCapabilities?: (userId: string, capabilities: UserCapabilities) => Promise<void>;
  onCopyCapabilities?: (fromUserId: string, toUserId: string) => Promise<void>;
  allUsers?: UserType[];
  readOnly?: boolean;
}

export function UserCapabilityManager({ 
  user, 
  onUpdateCapabilities, 
  onCopyCapabilities, 
  allUsers = [],
  readOnly = false 
}: UserCapabilityManagerProps) {
  const [capabilities, setCapabilities] = useState<UserCapabilities>(
    user.custom_capabilities || getCapabilitiesForPermission(user.permission)
  );
  const [isUpdating, setIsUpdating] = useState(false);
  const [showCopyDialog, setShowCopyDialog] = useState(false);
  const [selectedCopyUser, setSelectedCopyUser] = useState<string>("");
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});

  const hasUnsavedChanges = JSON.stringify(capabilities) !== JSON.stringify(user.custom_capabilities || {});

  const handleCapabilityChange = (capability: Capability, enabled: boolean) => {
    if (readOnly) return;
    
    setCapabilities(prev => ({
      ...prev,
      [capability]: enabled
    }));
  };

  const handleApplyRoleTemplate = (role: PermissionLevel) => {
    if (readOnly) return;
    
    const roleCapabilities = getCapabilitiesForPermission(role);
    setCapabilities(roleCapabilities);
    toast.success(`Applied ${role} role template`);
  };

  const handleSave = async () => {
    if (!onUpdateCapabilities) {
      // Fallback to direct API call
      try {
        setIsUpdating(true);
        await updateUserCapabilities(user.id, {
          custom_capabilities: capabilities
        });
        toast.success("Capabilities updated successfully");
      } catch (error: any) {
        toast.error(error.message || "Failed to update capabilities");
      } finally {
        setIsUpdating(false);
      }
      return;
    }

    try {
      setIsUpdating(true);
      await onUpdateCapabilities(user.id, capabilities);
      toast.success("Capabilities updated successfully");
    } catch (error: any) {
      toast.error(error.message || "Failed to update capabilities");
    } finally {
      setIsUpdating(false);
    }
  };

  const handleReset = () => {
    setCapabilities(user.custom_capabilities || getCapabilitiesForPermission(user.permission));
  };

  const handleCopyCapabilities = async () => {
    if (!onCopyCapabilities || !selectedCopyUser) return;
    
    try {
      setIsUpdating(true);
      await onCopyCapabilities(selectedCopyUser, user.id);
      setShowCopyDialog(false);
      setSelectedCopyUser("");
      toast.success("Capabilities copied successfully");
    } catch (error: any) {
      toast.error(error.message || "Failed to copy capabilities");
    } finally {
      setIsUpdating(false);
    }
  };

  const toggleGroupExpansion = (groupName: string) => {
    setExpandedGroups(prev => ({
      ...prev,
      [groupName]: !prev[groupName]
    }));
  };

  const getEnabledCapabilitiesCount = (groupCapabilities: Capability[]) => {
    return groupCapabilities.filter(cap => capabilities[cap]).length;
  };

  const getTotalCapabilitiesCount = () => {
    const totalCapabilities = Object.values(Capability).length;
    const enabledCount = Object.values(capabilities).filter(Boolean).length;
    return { enabled: enabledCount, total: totalCapabilities };
  };

  const capabilityCount = getTotalCapabilitiesCount();

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            <CardTitle>User Capabilities</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="flex items-center gap-1">
              <CheckCircle className="h-3 w-3" />
              {capabilityCount.enabled}/{capabilityCount.total} enabled
            </Badge>
            {hasUnsavedChanges && (
              <Badge variant="destructive" className="flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" />
                Unsaved changes
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Actions Bar */}
        <div className="flex flex-wrap items-center gap-2">
          {!readOnly && (
            <>
              <Button
                onClick={handleSave}
                disabled={!hasUnsavedChanges || isUpdating}
                className="flex items-center gap-2"
              >
                <Save className="h-4 w-4" />
                Save Changes
              </Button>
              <Button
                variant="outline"
                onClick={handleReset}
                disabled={!hasUnsavedChanges || isUpdating}
                className="flex items-center gap-2"
              >
                <RotateCcw className="h-4 w-4" />
                Reset
              </Button>
            </>
          )}
          
          {/* Role Templates */}
          <div className="flex items-center gap-2 ml-auto">
            <Label htmlFor="role-template" className="text-sm font-medium">
              Apply Role Template:
            </Label>
            <Select onValueChange={(value: PermissionLevel) => handleApplyRoleTemplate(value)} disabled={readOnly}>
              <SelectTrigger className="w-32">
                <SelectValue placeholder="Choose role" />
              </SelectTrigger>
              <SelectContent>
                {Object.values(PermissionLevel).map(role => (
                  <SelectItem key={role} value={role}>
                    {role}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          
          {/* Copy Capabilities */}
          {onCopyCapabilities && allUsers.length > 0 && !readOnly && (
            <Dialog open={showCopyDialog} onOpenChange={setShowCopyDialog}>
              <DialogTrigger asChild>
                <Button variant="outline" className="flex items-center gap-2">
                  <Copy className="h-4 w-4" />
                  Copy From User
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Copy Capabilities</DialogTitle>
                  <DialogDescription>
                    Select a user to copy their capabilities to {user.email}
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <Select value={selectedCopyUser} onValueChange={setSelectedCopyUser}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select user to copy from" />
                    </SelectTrigger>
                    <SelectContent>
                      {allUsers
                        .filter(u => u.id !== user.id)
                        .map(u => (
                          <SelectItem key={u.id} value={u.id}>
                            {u.email} ({u.permission})
                          </SelectItem>
                        ))}
                    </SelectContent>
                  </Select>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setShowCopyDialog(false)}>
                    Cancel
                  </Button>
                  <Button 
                    onClick={handleCopyCapabilities}
                    disabled={!selectedCopyUser || isUpdating}
                  >
                    Copy Capabilities
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          )}
        </div>

        {/* Current Role Info */}
        <Alert>
          <Shield className="h-4 w-4" />
          <AlertDescription>
            Base Role: <strong>{user.permission}</strong> | 
            Custom overrides: <strong>{Object.keys(user.custom_capabilities || {}).length} capabilities</strong>
          </AlertDescription>
        </Alert>

        <Separator />

        {/* Capability Groups */}
        <ScrollArea className="h-96">
          <div className="space-y-4">
            {Object.entries(CAPABILITY_GROUPS).map(([groupKey, group]) => {
              const isExpanded = expandedGroups[groupKey];
              const enabledCount = getEnabledCapabilitiesCount(group.capabilities);
              const totalCount = group.capabilities.length;

              return (
                <Collapsible
                  key={groupKey}
                  open={isExpanded}
                  onOpenChange={() => toggleGroupExpansion(groupKey)}
                >
                  <CollapsibleTrigger asChild>
                    <Button
                      variant="ghost"
                      className="w-full justify-between p-4 h-auto hover:bg-muted/50"
                    >
                      <div className="flex items-center gap-3">
                        <ChevronDown
                          className={`h-4 w-4 transition-transform ${
                            isExpanded ? "rotate-180" : ""
                          }`}
                        />
                        <span className="font-medium">{group.label}</span>
                      </div>
                      <Badge variant="secondary">
                        {enabledCount}/{totalCount}
                      </Badge>
                    </Button>
                  </CollapsibleTrigger>
                  <CollapsibleContent className="space-y-2 p-4 pt-0">
                    {group.capabilities.map(capability => (
                      <div
                        key={capability}
                        className="flex items-center justify-between space-x-2 p-2 rounded-md hover:bg-muted/30"
                      >
                        <div className="flex-1">
                          <Label
                            htmlFor={capability}
                            className="text-sm font-medium cursor-pointer"
                          >
                            {capability.replace(/_/g, " ").replace(/^can\s/, "").toLowerCase()}
                          </Label>
                          <p className="text-xs text-muted-foreground">
                            {capability}
                          </p>
                        </div>
                        <Switch
                          id={capability}
                          checked={!!capabilities[capability]}
                          onCheckedChange={(enabled) => handleCapabilityChange(capability, enabled)}
                          disabled={readOnly}
                        />
                      </div>
                    ))}
                  </CollapsibleContent>
                </Collapsible>
              );
            })}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
