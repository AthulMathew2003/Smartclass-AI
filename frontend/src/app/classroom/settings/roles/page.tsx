"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  fetchRoles,
  fetchRole,
  fetchGroupedPermissions,
  createRole,
  updateRole,
  deleteRole,
  RoleDetail,
  PermissionGroup,
  PermissionItem
} from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from "@/components/ui/dialog";
import { hasPermission, isPermissionsLoaded } from "@/lib/permissions";
import ForbiddenState from "../../components/ForbiddenState";

// ── Human-friendly Permission Labels ─────────────────────────
const PERMISSION_LABELS: Record<string, string> = {
  "member.create": "Create Members",
  "member.read": "View Members",
  "member.update": "Edit Members",
  "member.delete": "Remove Members",
  "workspace.create": "Create Workspaces",
  "workspace.read": "View Workspaces",
  "workspace.update": "Edit Workspaces",
  "workspace.delete": "Delete Workspaces",
  "organization.update": "Update Organization",
  "classroom.create": "Create Classrooms",
  "classroom.update": "Update Classrooms",
  "assignment.create": "Create Assignments",
  "assignment.update": "Update Assignments",
  "assignment.grade": "Grade Assignments",
  "attendance.view": "View Attendance",
  "attendance.manage": "Take & Manage Attendance",
  "exam.create": "Create Exams",
  "exam.publish": "Publish Exams",
  "analytics.view": "View Analytics",
  "ai.use": "Use AI Learning Features",
  "settings.manage": "Manage System Settings"
};

export default function CustomRolesPage() {
  // ── Permission Guard ──────────────────────────────────────
  if (!isPermissionsLoaded()) {
    return (
      <div className="p-16 text-center space-y-3">
        <div className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin mx-auto" style={{ borderColor: "var(--primary)", borderTopColor: "transparent" }} />
        <p className="text-sm font-semibold" style={{ color: "var(--on-surface-variant)" }}>Loading…</p>
      </div>
    );
  }
  if (!hasPermission("member.update")) {
    return <ForbiddenState message="You don't have permission to manage roles and permissions." />;
  }

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [roles, setRoles] = useState<RoleDetail[]>([]);
  const [permissionGroups, setPermissionGroups] = useState<PermissionGroup[]>([]);
  
  const [search, setSearch] = useState("");
  const [activeTab, setActiveTab] = useState<"all" | "system" | "custom">("all");

  // Dialog states
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [loadingRoleDetails, setLoadingRoleDetails] = useState(false);

  const [selectedRole, setSelectedRole] = useState<RoleDetail | null>(null);

  // Form State
  const [formName, setFormName] = useState("");
  const [formDesc, setFormDesc] = useState("");
  const [selectedPermIds, setSelectedPermIds] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // ── Load Roles & Permissions ─────────────────────────────
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [fetchedRoles, fetchedGroups] = await Promise.all([
        fetchRoles(),
        fetchGroupedPermissions()
      ]);
      setRoles(fetchedRoles);
      setPermissionGroups(fetchedGroups);
    } catch (err: any) {
      setError(err.message || "Failed to load roles and permissions from backend.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // ── Handlers ──────────────────────────────────────────────
  const handleOpenCreate = () => {
    setFormName("");
    setFormDesc("");
    setSelectedPermIds([]);
    setError(null);
    setCreateDialogOpen(true);
  };

  const handleTogglePerm = (permId: string, checked: boolean) => {
    if (checked) {
      setSelectedPermIds(prev => [...prev, permId]);
    } else {
      setSelectedPermIds(prev => prev.filter(id => id !== permId));
    }
  };

  const handleCreateRole = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formName.trim()) return;

    setError(null);
    setSuccess(null);
    setSubmitting(true);

    try {
      const newRole = await createRole({
        role_name: formName.trim(),
        role_description: formDesc.trim() || null,
        permission_ids: selectedPermIds
      });

      setSuccess(`Custom role "${newRole.role_name}" created successfully.`);
      setCreateDialogOpen(false);
      await loadData();
    } catch (err: any) {
      setError(err.message || "Failed to create custom role.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleOpenEdit = async (role: RoleDetail) => {
    if (role.role_is_system) return; // Guard system roles

    setSelectedRole(role);
    setFormName(role.role_name);
    setFormDesc(role.role_description || "");
    setSelectedPermIds(role.permissions.map(p => p.permission_id));
    setLoadingRoleDetails(true);
    setEditDialogOpen(true);

    try {
      const freshRole = await fetchRole(role.role_id);
      setSelectedRole(freshRole);
      setFormName(freshRole.role_name);
      setFormDesc(freshRole.role_description || "");
      setSelectedPermIds(freshRole.permissions.map(p => p.permission_id));
    } catch (err: any) {
      setError(err.message || "Failed to load fresh role details.");
    } finally {
      setLoadingRoleDetails(false);
    }
  };

  const handleEditRole = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRole || selectedRole.role_is_system || !formName.trim()) return;

    setError(null);
    setSuccess(null);
    setSubmitting(true);

    try {
      const updated = await updateRole(selectedRole.role_id, {
        role_name: formName.trim(),
        role_description: formDesc.trim() || null,
        permission_ids: selectedPermIds
      });

      setSuccess(`Custom role "${updated.role_name}" updated successfully.`);
      setEditDialogOpen(false);
      await loadData();
    } catch (err: any) {
      setError(err.message || "Failed to update custom role.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleOpenDelete = (role: RoleDetail) => {
    if (role.role_is_system) return;
    setSelectedRole(role);
    setDeleteError(null);
    setDeleteDialogOpen(true);
  };

  const handleDeleteRole = async () => {
    if (!selectedRole || selectedRole.role_is_system) return;

    setDeleteError(null);
    setSubmitting(true);

    try {
      await deleteRole(selectedRole.role_id);
      setSuccess(`Custom role "${selectedRole.role_name}" deleted successfully.`);
      setDeleteDialogOpen(false);
      await loadData();
    } catch (err: any) {
      setDeleteError(err.message || "Failed to delete custom role.");
    } finally {
      setSubmitting(false);
    }
  };

  // Categorize Roles
  const systemRoles = roles.filter(r => r.role_is_system);
  const customRoles = roles.filter(r => !r.role_is_system);

  const filterRoleList = (list: RoleDetail[]) => {
    return list.filter(r => {
      const q = search.toLowerCase();
      return r.role_name.toLowerCase().includes(q) ||
        (r.role_description && r.role_description.toLowerCase().includes(q));
    });
  };

  const filteredSystem = filterRoleList(systemRoles);
  const filteredCustom = filterRoleList(customRoles);

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      {/* ── Page Header ────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-[var(--primary)]" />
            <span className="text-xs font-bold uppercase tracking-wider text-[var(--on-surface-variant)]">Organization Governance</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-[var(--on-surface)]">Custom Role Management</h1>
          <p className="text-sm text-[var(--on-surface-variant)] mt-1">
            Manage system roles and create organization-specific custom roles with granular permission mappings.
          </p>
        </div>

        {hasPermission("member.update") && (
          <Button onClick={handleOpenCreate} className="ds-btn-primary px-5 py-2.5 shrink-0">
            <span className="material-symbols-outlined text-[18px]">add_moderator</span>
            Create Role
          </Button>
        )}
      </div>

      {/* ── Notifications ──────────────────────────────────────── */}
      {error && (
        <div className="p-4 rounded-xl flex items-center justify-between gap-3 text-sm font-medium animate-fade-in bg-red-500/10 border border-red-500/20 text-red-700 dark:text-red-300">
          <div className="flex items-center gap-2.5">
            <span className="material-symbols-outlined text-[20px] shrink-0">error</span>
            <span>{error}</span>
          </div>
          <Button variant="outline" size="sm" onClick={loadData} className="text-xs font-bold shrink-0">
            <span className="material-symbols-outlined text-[16px] mr-1">refresh</span>
            Retry
          </Button>
        </div>
      )}

      {success && (
        <div className="p-4 rounded-xl flex items-center justify-between gap-3 text-sm font-medium animate-fade-in bg-emerald-500/10 border border-emerald-500/20 text-emerald-800 dark:text-emerald-300">
          <div className="flex items-center gap-2.5">
            <span className="material-symbols-outlined text-[20px] shrink-0">check_circle</span>
            <span>{success}</span>
          </div>
          <button onClick={() => setSuccess(null)} className="cursor-pointer opacity-60 hover:opacity-100">
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>
      )}

      {/* ── Search & Filter Controls ───────────────────────────── */}
      <div className="ds-card p-4 flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="relative flex-1 w-full">
          <span className="material-symbols-outlined absolute left-3.5 top-1/2 -translate-y-1/2 text-[18px] text-[var(--on-surface-variant)]">search</span>
          <Input
            type="text"
            className="pl-10 text-sm"
            placeholder="Search roles by title or description..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="flex items-center gap-1.5 bg-[var(--surface-container)] p-1 rounded-xl w-full md:w-auto shrink-0">
          {(["all", "system", "custom"] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-1.5 rounded-lg text-xs font-bold capitalize transition-all cursor-pointer ${
                activeTab === tab
                  ? "bg-[var(--surface)] text-[var(--primary)] shadow-sm"
                  : "text-[var(--on-surface-variant)] hover:text-[var(--on-surface)]"
              }`}
            >
              {tab === "all" ? "All Roles" : tab === "system" ? "System Roles" : "Custom Roles"}
            </button>
          ))}
        </div>
      </div>

      {/* ── Main Roles Content ─────────────────────────────────── */}
      {loading ? (
        /* Loading Skeleton */
        <div className="space-y-6">
          <div className="h-6 w-32 bg-[var(--surface-container-high)] rounded animate-pulse" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {[1, 2, 3, 4, 5, 6].map(i => (
              <div key={i} className="ds-card p-6 space-y-4 animate-pulse">
                <div className="flex justify-between items-center">
                  <div className="h-5 w-28 bg-[var(--surface-container-high)] rounded" />
                  <div className="h-5 w-16 bg-[var(--surface-container-high)] rounded-full" />
                </div>
                <div className="h-10 bg-[var(--surface-container-low)] rounded" />
                <div className="h-16 bg-[var(--surface-container-high)] rounded" />
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="space-y-10">
          {/* ── SYSTEM ROLES SECTION ───────────────────────────── */}
          {(activeTab === "all" || activeTab === "system") && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-[var(--on-surface)] flex items-center gap-2">
                    <span className="material-symbols-outlined text-[20px] text-[var(--primary)]">shield</span>
                    System Roles ({systemRoles.length})
                  </h2>
                  <p className="text-xs text-[var(--on-surface-variant)]">Built-in system roles with predefined architectural privileges.</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {filteredSystem.map(role => (
                  <div
                    key={role.role_id}
                    className="ds-card p-6 flex flex-col justify-between border border-[var(--outline-variant)]/30 relative"
                  >
                    <div>
                      <div className="flex items-start justify-between gap-3 mb-2">
                        <div>
                          <h3 className="text-base font-bold text-[var(--on-surface)]">{role.role_name}</h3>
                          <span className="text-[11px] text-[var(--on-surface-variant)] font-medium">
                            {role.member_count} {role.member_count === 1 ? "member" : "members"}
                          </span>
                        </div>
                        <Badge variant="outline" className="bg-[var(--surface-container)] text-[var(--on-surface-variant)] border-[var(--outline-variant)] text-[10px] uppercase font-bold tracking-wider">
                          System Role
                        </Badge>
                      </div>

                      <p className="text-xs text-[var(--on-surface-variant)] leading-relaxed mb-4 min-h-[36px]">
                        {role.role_description || "Global system role."}
                      </p>

                      <div className="space-y-2">
                        <span className="ds-section-label">Permissions ({role.permissions.length})</span>
                        <div className="flex flex-wrap gap-1 max-h-20 overflow-y-auto">
                          {role.permissions.slice(0, 5).map(p => (
                            <span key={p.permission_id} className="px-2 py-0.5 rounded text-[10px] font-semibold bg-[var(--surface-container-high)] text-[var(--on-surface)]">
                              {PERMISSION_LABELS[p.permission_name] || p.permission_name}
                            </span>
                          ))}
                          {role.permissions.length > 5 && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[var(--surface-container-highest)] text-[var(--primary)]">
                              +{role.permissions.length - 5} more
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="pt-4 mt-4 border-t border-[var(--outline-variant)]/20 flex items-center justify-between text-xs text-[var(--on-surface-variant)]">
                      <span className="italic">Read-only system role</span>
                      <span className="material-symbols-outlined text-[16px]">lock</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── CUSTOM ROLES SECTION ───────────────────────────── */}
          {(activeTab === "all" || activeTab === "custom") && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-[var(--on-surface)] flex items-center gap-2">
                    <span className="material-symbols-outlined text-[20px] text-[var(--primary)]">badge</span>
                    Custom Roles ({customRoles.length})
                  </h2>
                  <p className="text-xs text-[var(--on-surface-variant)]">Organization-specific roles created to match your school governance.</p>
                </div>
              </div>

              {filteredCustom.length === 0 ? (
                <div className="ds-card p-12 text-center space-y-3">
                  <span className="material-symbols-outlined text-[40px] text-[var(--outline-variant)]">add_moderator</span>
                  <h3 className="text-base font-bold text-[var(--on-surface)]">No Custom Roles Created</h3>
                  <p className="text-xs text-[var(--on-surface-variant)] max-w-md mx-auto">
                    Create custom roles such as Math Coordinator, Exam Coordinator, or Lab Assistant to delegate granular organization duties.
                  </p>
                  <Button onClick={handleOpenCreate} className="ds-btn-primary px-4 py-2 mt-2 text-xs">
                    + Create Custom Role
                  </Button>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                  {filteredCustom.map(role => (
                    <div
                      key={role.role_id}
                      className="ds-card p-6 flex flex-col justify-between border border-[var(--outline-variant)]/30 relative hover:shadow-md transition-shadow"
                    >
                      <div>
                        <div className="flex items-start justify-between gap-3 mb-2">
                          <div>
                            <h3 className="text-base font-bold text-[var(--on-surface)]">{role.role_name}</h3>
                            <span className="text-[11px] text-[var(--on-surface-variant)] font-medium">
                              {role.member_count} {role.member_count === 1 ? "member" : "members"} assigned
                            </span>
                          </div>
                          <Badge className="bg-[var(--tertiary-fixed)] text-[var(--on-tertiary-fixed)] text-[10px] uppercase font-bold tracking-wider">
                            Custom Role
                          </Badge>
                        </div>

                        <p className="text-xs text-[var(--on-surface-variant)] leading-relaxed mb-4 min-h-[36px]">
                          {role.role_description || "No description specified."}
                        </p>

                        <div className="space-y-2">
                          <span className="ds-section-label">Permissions ({role.permissions.length})</span>
                          <div className="flex flex-wrap gap-1 max-h-20 overflow-y-auto">
                            {role.permissions.slice(0, 5).map(p => (
                              <span key={p.permission_id} className="px-2 py-0.5 rounded text-[10px] font-semibold bg-[var(--surface-container-high)] text-[var(--on-surface)]">
                                {PERMISSION_LABELS[p.permission_name] || p.permission_name}
                              </span>
                            ))}
                            {role.permissions.length > 5 && (
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[var(--surface-container-highest)] text-[var(--primary)]">
                                +{role.permissions.length - 5} more
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Custom Action Buttons */}
                      {hasPermission("member.update") && (
                        <div className="pt-4 mt-4 border-t border-[var(--outline-variant)]/30 flex items-center justify-end gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-xs font-semibold cursor-pointer"
                            onClick={() => handleOpenEdit(role)}
                          >
                            <span className="material-symbols-outlined text-[16px] mr-1">edit</span>
                            Edit
                          </Button>
                          <Button
                            variant="destructive"
                            size="sm"
                            className="text-xs font-semibold cursor-pointer"
                            onClick={() => handleOpenDelete(role)}
                          >
                            <span className="material-symbols-outlined text-[16px] mr-1">delete</span>
                            Delete
                          </Button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── CREATE ROLE DIALOG ──────────────────────────────────── */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-bold">Create Custom Role</DialogTitle>
            <DialogDescription className="text-xs text-[var(--on-surface-variant)]">
              Specify a title, description, and permissions from the backend API registry.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleCreateRole} className="space-y-5 pt-2">
            <div className="space-y-2">
              <Label htmlFor="create-role-name">Role Name <span className="text-red-500">*</span></Label>
              <Input
                id="create-role-name"
                placeholder="e.g. Department Head, Exam Coordinator, Counselor"
                value={formName}
                onChange={e => setFormName(e.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="create-role-desc">Description</Label>
              <Input
                id="create-role-desc"
                placeholder="Briefly describe the duties of this role..."
                value={formDesc}
                onChange={e => setFormDesc(e.target.value)}
              />
            </div>

            {/* Dynamic Permission Checkboxes */}
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <Label className="text-xs font-bold uppercase tracking-wider text-[var(--on-surface-variant)]">
                  Permissions ({selectedPermIds.length} Selected)
                </Label>
              </div>

              <div className="space-y-4 max-h-72 overflow-y-auto p-4 rounded-xl bg-[var(--surface-container)] border border-[var(--outline-variant)]/40">
                {permissionGroups.map(group => (
                  <div key={group.category} className="space-y-2">
                    <h4 className="text-xs font-bold text-[var(--primary)] uppercase tracking-wider border-b border-[var(--outline-variant)]/30 pb-1">
                      {group.category} Permissions
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      {group.permissions.map(perm => {
                        const checked = selectedPermIds.includes(perm.permission_id);
                        return (
                          <label
                            key={perm.permission_id}
                            className={`flex items-start gap-2.5 p-2 rounded-lg border text-xs cursor-pointer transition-colors ${
                              checked
                                ? "bg-[var(--surface)] border-[var(--primary)] shadow-xs"
                                : "bg-[var(--surface-container-low)] border-transparent hover:border-[var(--outline-variant)]"
                            }`}
                          >
                            <Checkbox
                              checked={checked}
                              onCheckedChange={c => handleTogglePerm(perm.permission_id, !!c)}
                              className="mt-0.5"
                            />
                            <div>
                              <div className="font-semibold text-[var(--on-surface)]">
                                {PERMISSION_LABELS[perm.permission_name] || perm.permission_name}
                              </div>
                              <div className="text-[10px] text-[var(--on-surface-variant)] font-mono">
                                {perm.permission_name}
                              </div>
                            </div>
                          </label>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <DialogFooter className="gap-2">
              <Button type="button" variant="ghost" onClick={() => setCreateDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={submitting || !formName.trim()} className="ds-btn-primary">
                {submitting ? "Creating..." : "Save Role"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ── EDIT ROLE DIALOG ────────────────────────────────────── */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-bold">Edit Custom Role: {selectedRole?.role_name}</DialogTitle>
            <DialogDescription className="text-xs text-[var(--on-surface-variant)]">
              Modify custom role name, description, and permission mappings.
            </DialogDescription>
          </DialogHeader>

          {loadingRoleDetails ? (
            <div className="p-12 text-center space-y-2">
              <div className="w-6 h-6 border-2 border-t-transparent border-[var(--primary)] rounded-full animate-spin mx-auto" />
              <p className="text-xs text-[var(--on-surface-variant)]">Loading role details...</p>
            </div>
          ) : (
            <form onSubmit={handleEditRole} className="space-y-5 pt-2">
              <div className="space-y-2">
                <Label htmlFor="edit-role-name">Role Name <span className="text-red-500">*</span></Label>
                <Input
                  id="edit-role-name"
                  value={formName}
                  onChange={e => setFormName(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="edit-role-desc">Description</Label>
                <Input
                  id="edit-role-desc"
                  value={formDesc}
                  onChange={e => setFormDesc(e.target.value)}
                />
              </div>

              {/* Permissions */}
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <Label className="text-xs font-bold uppercase tracking-wider text-[var(--on-surface-variant)]">
                    Permissions ({selectedPermIds.length} Selected)
                  </Label>
                </div>

                <div className="space-y-4 max-h-72 overflow-y-auto p-4 rounded-xl bg-[var(--surface-container)] border border-[var(--outline-variant)]/40">
                  {permissionGroups.map(group => (
                    <div key={group.category} className="space-y-2">
                      <h4 className="text-xs font-bold text-[var(--primary)] uppercase tracking-wider border-b border-[var(--outline-variant)]/30 pb-1">
                        {group.category} Permissions
                      </h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {group.permissions.map(perm => {
                          const checked = selectedPermIds.includes(perm.permission_id);
                          return (
                            <label
                              key={perm.permission_id}
                              className={`flex items-start gap-2.5 p-2 rounded-lg border text-xs cursor-pointer transition-colors ${
                                checked
                                  ? "bg-[var(--surface)] border-[var(--primary)] shadow-xs"
                                  : "bg-[var(--surface-container-low)] border-transparent hover:border-[var(--outline-variant)]"
                              }`}
                            >
                              <Checkbox
                                checked={checked}
                                onCheckedChange={c => handleTogglePerm(perm.permission_id, !!c)}
                                className="mt-0.5"
                              />
                              <div>
                                <div className="font-semibold text-[var(--on-surface)]">
                                  {PERMISSION_LABELS[perm.permission_name] || perm.permission_name}
                                </div>
                                <div className="text-[10px] text-[var(--on-surface-variant)] font-mono">
                                  {perm.permission_name}
                                </div>
                              </div>
                            </label>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <DialogFooter className="gap-2">
                <Button type="button" variant="ghost" onClick={() => setEditDialogOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={submitting || !formName.trim()} className="ds-btn-primary">
                  {submitting ? "Saving..." : "Apply Changes"}
                </Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>

      {/* ── DELETE CONFIRMATION DIALOG ──────────────────────────── */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold text-red-600">Delete Custom Role</DialogTitle>
            <DialogDescription className="text-xs text-[var(--on-surface-variant)]">
              Delete &quot;{selectedRole?.role_name}&quot;? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>

          {deleteError && (
            <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-xs font-semibold text-red-700 dark:text-red-300 flex items-start gap-2">
              <span className="material-symbols-outlined text-[18px] shrink-0">error</span>
              <span>{deleteError}</span>
            </div>
          )}

          {selectedRole && selectedRole.member_count > 0 && !deleteError && (
            <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs font-semibold text-amber-800 dark:text-amber-300">
              ⚠️ Note: This role is currently assigned to {selectedRole.member_count} member(s). Backend validation will block deletion until members are reassigned.
            </div>
          )}

          <DialogFooter className="gap-2 mt-4">
            <Button type="button" variant="ghost" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              disabled={submitting}
              onClick={handleDeleteRole}
            >
              {submitting ? "Deleting..." : "Delete Role"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
