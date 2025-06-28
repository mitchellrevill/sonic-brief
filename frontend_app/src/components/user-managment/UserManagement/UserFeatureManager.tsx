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
import { Settings, Shield, ChevronDown, Save, RotateCcw, AlertTriangle, Copy } from "lucide-react";
import { 
  FeatureToggle, 
  PermissionLevel, 
  FEATURE_GROUPS, 
  FEATURE_DESCRIPTIONS,
  applyRoleTemplate 
} from "@/types/permissions";
import type { UserFeatures, User as UserType } from "@/types/permissions";
import { toast } from "sonner";

interface UserFeatureManagerProps {
  user: UserType;
  onUpdateFeatures: (userId: string, features: UserFeatures) => Promise<void>;
  onCopyFeatures?: (fromUserId: string, toUserId: string) => Promise<void>;
  allUsers?: UserType[];
  readOnly?: boolean;
}

export function UserFeatureManager({ 
  user, 
  onUpdateFeatures, 
  onCopyFeatures, 
  allUsers = [],
  readOnly = false 
}: UserFeatureManagerProps) {
  const [features, setFeatures] = useState<UserFeatures>(user.features);
  const [isUpdating, setIsUpdating] = useState(false);
  const [showCopyDialog, setShowCopyDialog] = useState(false);
  const [selectedCopyUser, setSelectedCopyUser] = useState<string>("");
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({
    "Core Features": true, // Expand the most important group by default
  });

  const hasUnsavedChanges = JSON.stringify(features) !== JSON.stringify(user.features);

  const handleFeatureToggle = (feature: FeatureToggle, enabled: boolean) => {
    if (readOnly) return;
    
    setFeatures((prev: UserFeatures) => ({
      ...prev,
      [feature]: enabled
    }));
  };

  const handleApplyRoleTemplate = (role: PermissionLevel) => {
    if (readOnly) return;
    
    const templateFeatures = applyRoleTemplate(role);
    setFeatures(templateFeatures);
    toast.success(`Applied ${role} role template`);
  };

  const handleSaveFeatures = async () => {
    if (readOnly) return;
    
    setIsUpdating(true);
    try {
      await onUpdateFeatures(user.id, features);
      toast.success("User features updated successfully");
    } catch (error) {
      console.error("Failed to update features:", error);
      toast.error("Failed to update features");
    } finally {
      setIsUpdating(false);
    }
  };

  const handleResetFeatures = () => {
    if (readOnly) return;
    
    setFeatures(user.features);
    toast.info("Changes reverted");
  };

  const handleCopyFeatures = async () => {
    if (!selectedCopyUser || !onCopyFeatures) return;
    
    try {
      await onCopyFeatures(selectedCopyUser, user.id);
      setShowCopyDialog(false);
      setSelectedCopyUser("");
      toast.success("Features copied successfully");
    } catch (error) {
      console.error("Failed to copy features:", error);
      toast.error("Failed to copy features");
    }
  };

  const toggleGroupExpansion = (groupName: string) => {
    setExpandedGroups(prev => ({
      ...prev,
      [groupName]: !prev[groupName]
    }));
  };

  const getEnabledFeaturesCount = (groupFeatures: FeatureToggle[]) => {
    return groupFeatures.filter(feature => features[feature] === true).length;
  };

  const getFeatureCountSummary = () => {
    const totalFeatures = Object.values(FeatureToggle).length;
    const enabledFeatures = Object.values(features).filter(Boolean).length;
    return { enabled: enabledFeatures, total: totalFeatures };
  };

  const summary = getFeatureCountSummary();

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            <CardTitle>Feature Permissions</CardTitle>
            <Badge variant="outline">
              {summary.enabled}/{summary.total} Features Enabled
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            {!readOnly && onCopyFeatures && allUsers.length > 1 && (
              <Dialog open={showCopyDialog} onOpenChange={setShowCopyDialog}>
                <DialogTrigger asChild>
                  <Button variant="outline" size="sm">
                    <Copy className="h-4 w-4 mr-2" />
                    Copy From User
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Copy Features</DialogTitle>
                    <DialogDescription>
                      Copy feature settings from another user to {user.email}
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4">
                    <div>
                      <Label>Select User</Label>
                      <Select value={selectedCopyUser} onValueChange={setSelectedCopyUser}>
                        <SelectTrigger>
                          <SelectValue placeholder="Select a user to copy from" />
                        </SelectTrigger>
                        <SelectContent>
                          {allUsers
                            .filter(u => u.id !== user.id)
                            .map(u => (
                              <SelectItem key={u.id} value={u.id}>
                                {u.name || u.email} ({u.permission || "User"})
                              </SelectItem>
                            ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setShowCopyDialog(false)}>
                      Cancel
                    </Button>
                    <Button onClick={handleCopyFeatures} disabled={!selectedCopyUser}>
                      Copy Features
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            )}
            {!readOnly && (
              <div className="flex items-center gap-2">
                <Select onValueChange={(value) => handleApplyRoleTemplate(value as PermissionLevel)}>
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder="Apply Template" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={PermissionLevel.USER}>User Template</SelectItem>
                    <SelectItem value={PermissionLevel.EDITOR}>Editor Template</SelectItem>
                    <SelectItem value={PermissionLevel.ADMIN}>Admin Template</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>
        </div>
        {hasUnsavedChanges && (
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              You have unsaved changes. Click "Save Changes" to apply them.
            </AlertDescription>
          </Alert>
        )}
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Feature Groups */}
        <ScrollArea className="h-96">
          <div className="space-y-4">
            {Object.entries(FEATURE_GROUPS).map(([groupName, groupFeatures]) => {
              const isExpanded = expandedGroups[groupName];
              const enabledCount = getEnabledFeaturesCount(groupFeatures);
              
              return (
                <Collapsible key={groupName} open={isExpanded} onOpenChange={() => toggleGroupExpansion(groupName)}>
                  <CollapsibleTrigger asChild>
                    <Button variant="ghost" className="w-full justify-between p-4 h-auto">
                      <div className="flex items-center gap-2">
                        <Shield className="h-4 w-4" />
                        <span className="font-medium">{groupName}</span>
                        <Badge variant="secondary" className="ml-2">
                          {enabledCount}/{groupFeatures.length}
                        </Badge>
                      </div>
                      <ChevronDown className={`h-4 w-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                    </Button>
                  </CollapsibleTrigger>
                  <CollapsibleContent className="space-y-3 pt-3">
                    <div className="grid gap-3 pl-6">
                      {groupFeatures.map((feature: FeatureToggle) => (
                        <div key={feature} className="flex items-center justify-between space-x-3 py-2">
                          <div className="space-y-1 flex-1">
                            <Label 
                              htmlFor={feature} 
                              className="text-sm font-medium cursor-pointer"
                            >
                              {feature.split('_').map((word: string) => 
                                word.charAt(0).toUpperCase() + word.slice(1)
                              ).join(' ')}
                            </Label>
                            <p className="text-xs text-muted-foreground">
                              {FEATURE_DESCRIPTIONS[feature]}
                            </p>
                          </div>
                          <Switch
                            id={feature}
                            checked={features[feature] === true}
                            onCheckedChange={(checked) => handleFeatureToggle(feature, checked)}
                            disabled={readOnly}
                          />
                        </div>
                      ))}
                    </div>
                    {groupFeatures.length > 1 && (
                      <Separator className="my-3" />
                    )}
                  </CollapsibleContent>
                </Collapsible>
              );
            })}
          </div>
        </ScrollArea>

        {/* Action Buttons */}
        {!readOnly && (
          <div className="flex items-center gap-3 pt-4 border-t">
            <Button 
              onClick={handleSaveFeatures} 
              disabled={!hasUnsavedChanges || isUpdating}
              className="flex-1"
            >
              {isUpdating ? (
                <>
                  <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full mr-2" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  Save Changes
                </>
              )}
            </Button>
            <Button 
              variant="outline" 
              onClick={handleResetFeatures} 
              disabled={!hasUnsavedChanges || isUpdating}
            >
              <RotateCcw className="h-4 w-4 mr-2" />
              Reset
            </Button>
          </div>
        )}

        {readOnly && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground pt-4 border-t">
            <AlertTriangle className="h-4 w-4" />
            You don't have permission to modify this user's features
          </div>
        )}
      </CardContent>
    </Card>
  );
}
