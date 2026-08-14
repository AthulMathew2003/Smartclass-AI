"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  fetchWorkspaces,
  createWorkspace,
  updateWorkspace,
  archiveWorkspace,
  Workspace
} from "@/lib/workspaces";
import { usePermissions } from "@/lib/permissions";
import ForbiddenState from "../components/ForbiddenState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator
} from "@/components/ui/dropdown-menu";

export default function WorkspacesPage() {
  const { hasPermission, isLoaded: permLoaded, orgId } = usePermissions();

  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Filters & Search
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "archived">("all");

  // Create Modal State
  const [createOpen, setCreateOpen] = useState(false);
  const [createName, setCreateName] = useState("");
  const [createDesc, setCreateDesc] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);

  // Edit Modal State
  const [editOpen, setEditDialogOpen] = useState(false);
  const [selectedWorkspace, setSelectedWorkspace] = useState<Workspace | null>(null);
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [editError, setEditError] = useState<string | null>(null);

  // Archive Modal State
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [archiveError, setArchiveError] = useState<string | null>(null);

  // Submission spinner state
  const [submitting, setSubmitting] = useState(false);

  // Load Workspaces for Active Organization
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchWorkspaces();
      setWorkspaces(data);
    } catch (err: any) {
      setError(err.message || "Failed to load workspaces.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (permLoaded && hasPermission("workspace.read")) {
      loadData();
    }
  }, [permLoaded, orgId, loadData]);

  // ── Permission Guard ──────────────────────────────────────
  if (!permLoaded) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="flex items-center gap-3 text-sm font-semibold text-[var(--on-surface-variant)]">
          <div className="w-6 h-6 border-2 border-t-transparent border-[var(--primary)] rounded-full animate-spin" />
          Checking permissions...
        </div>
      </div>
    );
  }

  if (!hasPermission("workspace.read")) {
    return (
      <ForbiddenState message="You do not have permission to view or manage workspaces in this organization." />
    );
  }

  // ── Handlers ──────────────────────────────────────────────
  const handleOpenCreate = () => {
    setCreateName("");
    setCreateDesc("");
    setCreateError(null);
    setCreateOpen(true);
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createName.trim()) {
      setCreateError("Workspace name is required.");
      return;
    }
    setCreateError(null);
    setSubmitting(true);

    try {
      const created = await createWorkspace({
        workspace_name: createName.trim(),
        workspace_description: createDesc.trim() || null
      });
      setSuccess(`Workspace "${created.workspace_name}" created successfully.`);
      setCreateOpen(false);
      await loadData();
    } catch (err: any) {
      setCreateError(err.message || "Failed to create workspace.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleOpenEdit = (ws: Workspace) => {
    setSelectedWorkspace(ws);
    setEditName(ws.workspace_name);
    setEditDesc(ws.workspace_description || "");
    setEditError(null);
    setEditDialogOpen(true);
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedWorkspace || !editName.trim()) {
      setEditError("Workspace name is required.");
      return;
    }
    setEditError(null);
    setSubmitting(true);

    try {
      const updated = await updateWorkspace(selectedWorkspace.workspace_id, {
        workspace_name: editName.trim(),
        workspace_description: editDesc.trim() || null
      });
      setSuccess(`Workspace "${updated.workspace_name}" updated successfully.`);
      setEditDialogOpen(false);
      await loadData();
    } catch (err: any) {
      setEditError(err.message || "Failed to update workspace.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleOpenArchive = (ws: Workspace) => {
    setSelectedWorkspace(ws);
    setArchiveError(null);
    setArchiveOpen(true);
  };

  const handleArchiveConfirm = async () => {
    if (!selectedWorkspace) return;
    setArchiveError(null);
    setSubmitting(true);

    try {
      await archiveWorkspace(selectedWorkspace.workspace_id);
      setSuccess(`Workspace "${selectedWorkspace.workspace_name}" archived successfully.`);
      setArchiveOpen(false);
      await loadData();
    } catch (err: any) {
      setArchiveError(err.message || "Failed to archive workspace.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleUnarchive = async (ws: Workspace) => {
    try {
      const updated = await updateWorkspace(ws.workspace_id, { workspace_status: "active" });
      setSuccess(`Workspace "${updated.workspace_name}" unarchived successfully.`);
      await loadData();
    } catch (err: any) {
      setError(err.message || "Failed to unarchive workspace.");
    }
  };

  // Filtered List
  const filteredWorkspaces = workspaces.filter((ws) => {
    const q = search.toLowerCase();
    const matchesSearch =
      ws.workspace_name.toLowerCase().includes(q) ||
      (ws.workspace_description && ws.workspace_description.toLowerCase().includes(q));

    if (statusFilter === "active") return matchesSearch && ws.workspace_status === "active";
    if (statusFilter === "archived") return matchesSearch && ws.workspace_status === "archived";
    return matchesSearch;
  });

  const canCreate = hasPermission("workspace.create");
  const canUpdate = hasPermission("workspace.update");
  const canDelete = hasPermission("workspace.delete");

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      {/* ── Page Header ────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span
              className="material-symbols-outlined text-[20px]"
              style={{ color: "var(--primary)" }}
            >
              workspaces
            </span>
            <span
              className="text-xs font-bold uppercase tracking-wider"
              style={{ color: "var(--secondary)" }}
            >
              Organization Workspaces
            </span>
          </div>
          <h1
            className="text-3xl font-bold tracking-tight"
            style={{ color: "var(--on-surface)" }}
          >
            Workspaces
          </h1>
          <p
            className="text-sm mt-1"
            style={{ color: "var(--on-surface-variant)" }}
          >
            Manage academic departments, campuses, and learning environments.
          </p>
        </div>

        {canCreate && (
          <Button
            onClick={handleOpenCreate}
            className="ds-btn-primary self-start sm:self-auto gap-2 px-5 py-2.5 shadow-md"
          >
            <span className="material-symbols-outlined text-[18px]">add</span>
            Create Workspace
          </Button>
        )}
      </div>

      {/* ── Feedback Banners ────────────────────────────────────── */}
      {success && (
        <div className="p-4 rounded-2xl flex items-center justify-between gap-3 text-sm font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 animate-fade-in">
          <div className="flex items-center gap-2.5">
            <span className="material-symbols-outlined text-[20px]">check_circle</span>
            <span>{success}</span>
          </div>
          <button
            onClick={() => setSuccess(null)}
            className="p-1 rounded-lg hover:bg-emerald-500/10 cursor-pointer"
          >
            <span className="material-symbols-outlined text-[16px]">close</span>
          </button>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-2xl flex items-center justify-between gap-3 text-sm font-semibold bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20 animate-fade-in">
          <div className="flex items-center gap-2.5">
            <span className="material-symbols-outlined text-[20px]">error</span>
            <span>{error}</span>
          </div>
          <button
            onClick={() => setError(null)}
            className="p-1 rounded-lg hover:bg-red-500/10 cursor-pointer"
          >
            <span className="material-symbols-outlined text-[16px]">close</span>
          </button>
        </div>
      )}

      {/* ── Search & Filter Controls ────────────────────────────── */}
      <div className="flex flex-col md:flex-row gap-4 items-stretch md:items-center justify-between">
        <div className="relative flex-1 max-w-md">
          <span
            className="material-symbols-outlined absolute left-3.5 top-1/2 -translate-y-1/2 text-[20px]"
            style={{ color: "var(--on-surface-variant)" }}
          >
            search
          </span>
          <Input
            placeholder="Search workspaces by name or description..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-11 pr-4 py-2.5 rounded-xl border-[var(--outline-variant)]/40 bg-[var(--surface-container-low)] focus:bg-[var(--surface)] text-sm"
          />
        </div>

        <div className="flex items-center gap-2 self-start md:self-auto">
          <span
            className="text-xs font-bold uppercase tracking-wider mr-1"
            style={{ color: "var(--on-surface-variant)" }}
          >
            Status:
          </span>
          {(["all", "active", "archived"] as const).map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold capitalize transition-all cursor-pointer ${
                statusFilter === st
                  ? "bg-[var(--primary)] text-[var(--on-primary)] shadow-sm"
                  : "bg-[var(--surface-container-high)] text-[var(--on-surface-variant)] hover:bg-[var(--surface-container-highest)]"
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* ── Loading Skeleton ────────────────────────────────────── */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="p-6 rounded-3xl border border-[var(--outline-variant)]/30 space-y-4 animate-pulse bg-[var(--surface-container)]"
            >
              <div className="flex justify-between items-start">
                <div className="w-12 h-12 rounded-2xl bg-[var(--surface-container-high)]" />
                <div className="w-16 h-6 rounded-full bg-[var(--surface-container-high)]" />
              </div>
              <div className="space-y-2">
                <div className="w-3/4 h-5 rounded bg-[var(--surface-container-high)]" />
                <div className="w-full h-4 rounded bg-[var(--surface-container-high)]" />
              </div>
              <div className="pt-4 border-t border-[var(--outline-variant)]/20 flex justify-between">
                <div className="w-20 h-4 rounded bg-[var(--surface-container-high)]" />
                <div className="w-24 h-4 rounded bg-[var(--surface-container-high)]" />
              </div>
            </div>
          ))}
        </div>
      ) : filteredWorkspaces.length === 0 ? (
        /* ── Empty State ───────────────────────────────────────── */
        <div
          className="p-12 rounded-3xl text-center space-y-5 border border-dashed border-[var(--outline-variant)]/50"
          style={{ backgroundColor: "var(--surface-container-low)" }}
        >
          <div
            className="w-16 h-16 rounded-3xl flex items-center justify-center mx-auto"
            style={{
              backgroundColor: "rgba(21,69,57,0.08)",
              color: "var(--primary)"
            }}
          >
            <span className="material-symbols-outlined text-[36px]">workspaces</span>
          </div>
          <div className="max-w-md mx-auto space-y-1.5">
            <h3
              className="text-lg font-bold tracking-tight"
              style={{ color: "var(--on-surface)" }}
            >
              {search || statusFilter !== "all"
                ? "No matching workspaces found"
                : "No workspaces created yet"}
            </h3>
            <p
              className="text-sm leading-relaxed"
              style={{ color: "var(--on-surface-variant)" }}
            >
              {search || statusFilter !== "all"
                ? "Try adjusting your search criteria or status filter."
                : canCreate
                ? "Create your first workspace to organize members, subjects, and learning resources."
                : "Contact your organization administrator to set up workspaces."}
            </p>
          </div>
          {canCreate && !search && statusFilter === "all" && (
            <Button onClick={handleOpenCreate} className="ds-btn-primary gap-2 px-5 py-2.5">
              <span className="material-symbols-outlined text-[18px]">add</span>
              Create First Workspace
            </Button>
          )}
        </div>
      ) : (
        /* ── Workspace Cards Grid ────────────────────────────────── */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredWorkspaces.map((ws) => {
            const isArchived = ws.workspace_status === "archived";
            return (
              <div
                key={ws.workspace_id}
                className="p-6 rounded-3xl border transition-all duration-200 flex flex-col justify-between hover:shadow-lg relative overflow-hidden group"
                style={{
                  backgroundColor: "var(--surface-container)",
                  borderColor: "color-mix(in srgb, var(--outline-variant) 30%, transparent)",
                  opacity: isArchived ? 0.75 : 1
                }}
              >
                <div>
                  {/* Top Bar */}
                  <div className="flex items-start justify-between gap-3 mb-4">
                    <div
                      className="w-12 h-12 rounded-2xl flex items-center justify-center font-bold text-lg shrink-0 shadow-sm transition-transform group-hover:scale-105"
                      style={{
                        backgroundColor: isArchived
                          ? "var(--surface-container-high)"
                          : "rgba(21,69,57,0.1)",
                        color: isArchived
                          ? "var(--on-surface-variant)"
                          : "var(--primary)"
                      }}
                    >
                      <span className="material-symbols-outlined text-[24px]">
                        {isArchived ? "archive" : "domain"}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <Badge
                        className={`text-[10px] uppercase font-bold tracking-wider px-2.5 py-1 border-0 ${
                          isArchived
                            ? "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                            : "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                        }`}
                      >
                        {ws.workspace_status}
                      </Badge>

                      {/* Dropdown Menu for Actions */}
                      {(canUpdate || canDelete) && (
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <button
                              className="p-1.5 rounded-xl hover:bg-[var(--surface-container-high)] transition-colors cursor-pointer text-[var(--on-surface-variant)]"
                              title="Workspace Actions"
                            >
                              <span className="material-symbols-outlined text-[20px]">
                                more_vert
                              </span>
                            </button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end" className="w-48">
                            {canUpdate && (
                              <DropdownMenuItem
                                onClick={() => handleOpenEdit(ws)}
                                className="cursor-pointer gap-2"
                              >
                                <span className="material-symbols-outlined text-[18px]">
                                  edit
                                </span>
                                Edit Workspace
                              </DropdownMenuItem>
                            )}

                            {canDelete && !isArchived && (
                              <>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem
                                  onClick={() => handleOpenArchive(ws)}
                                  className="cursor-pointer gap-2 text-amber-600 dark:text-amber-400 focus:text-amber-600"
                                >
                                  <span className="material-symbols-outlined text-[18px]">
                                    archive
                                  </span>
                                  Archive Workspace
                                </DropdownMenuItem>
                              </>
                            )}

                            {canUpdate && isArchived && (
                              <>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem
                                  onClick={() => handleUnarchive(ws)}
                                  className="cursor-pointer gap-2 text-emerald-600 dark:text-emerald-400 focus:text-emerald-600"
                                >
                                  <span className="material-symbols-outlined text-[18px]">
                                    unarchive
                                  </span>
                                  Unarchive Workspace
                                </DropdownMenuItem>
                              </>
                            )}
                          </DropdownMenuContent>
                        </DropdownMenu>
                      )}
                    </div>
                  </div>

                  {/* Title & Description */}
                  <h3
                    className="text-lg font-bold tracking-tight mb-1.5 line-clamp-1"
                    style={{ color: "var(--on-surface)" }}
                  >
                    {ws.workspace_name}
                  </h3>
                  <p
                    className="text-xs leading-relaxed line-clamp-2 min-h-[2.25rem] mb-6"
                    style={{ color: "var(--on-surface-variant)" }}
                  >
                    {ws.workspace_description || "No description provided."}
                  </p>
                </div>

                {/* Card Footer Meta */}
                <div className="pt-4 border-t border-[var(--outline-variant)]/20 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-4 text-[var(--on-surface-variant)] font-medium">
                    <div className="flex items-center gap-1.5" title="Workspace members">
                      <span className="material-symbols-outlined text-[16px] opacity-70">
                        group
                      </span>
                      <span>{ws.member_count ?? 0} member(s)</span>
                    </div>
                    <div className="flex items-center gap-1.5" title="Workspace subjects">
                      <span className="material-symbols-outlined text-[15px]">menu_book</span>
                      <span>{ws.subject_count ?? 0} subject(s)</span>
                    </div>
                  </div>

                  {hasPermission("member.read") && (
                    <Link
                      href="/classroom/members"
                      className="font-bold text-[var(--primary)] hover:underline flex items-center gap-1 text-[11px]"
                    >
                      Manage Members
                      <span className="material-symbols-outlined text-[14px]">
                        chevron_right
                      </span>
                    </Link>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ── Create Workspace Dialog ─────────────────────────────── */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-xl font-bold">
              <span
                className="material-symbols-outlined text-[22px]"
                style={{ color: "var(--primary)" }}
              >
                add_circle
              </span>
              Create New Workspace
            </DialogTitle>
            <DialogDescription className="text-xs">
              Add a new isolated workspace to this organization.
            </DialogDescription>
          </DialogHeader>

          {createError && (
            <div className="p-3 rounded-xl flex items-center gap-2 text-xs font-semibold bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20">
              <span className="material-symbols-outlined text-[18px]">error</span>
              <span>{createError}</span>
            </div>
          )}

          <form onSubmit={handleCreateSubmit} className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label htmlFor="create-name" className="text-xs font-bold">
                Workspace Name <span className="text-red-500">*</span>
              </Label>
              <Input
                id="create-name"
                placeholder="e.g. Science Department, Main Campus"
                value={createName}
                onChange={(e) => setCreateName(e.target.value)}
                required
                maxLength={255}
                className="rounded-xl border-[var(--outline-variant)]/40 text-sm"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="create-desc" className="text-xs font-bold">
                Description <span className="text-xs font-normal opacity-70">(Optional)</span>
              </Label>
              <Textarea
                id="create-desc"
                placeholder="Brief summary of this workspace's purpose..."
                value={createDesc}
                onChange={(e) => setCreateDesc(e.target.value)}
                maxLength={1000}
                rows={3}
                className="rounded-xl border-[var(--outline-variant)]/40 text-sm resize-none"
              />
            </div>

            <DialogFooter className="pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={() => setCreateOpen(false)}
                disabled={submitting}
                className="rounded-xl text-xs font-bold"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={submitting || !createName.trim()}
                className="ds-btn-primary rounded-xl text-xs font-bold px-5"
              >
                {submitting ? (
                  <div className="flex items-center gap-2">
                    <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Creating...
                  </div>
                ) : (
                  "Create Workspace"
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ── Edit Workspace Dialog ───────────────────────────────── */}
      <Dialog open={editOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-xl font-bold">
              <span
                className="material-symbols-outlined text-[22px]"
                style={{ color: "var(--primary)" }}
              >
                edit
              </span>
              Edit Workspace
            </DialogTitle>
            <DialogDescription className="text-xs">
              Update details for &quot;{selectedWorkspace?.workspace_name}&quot;.
            </DialogDescription>
          </DialogHeader>

          {editError && (
            <div className="p-3 rounded-xl flex items-center gap-2 text-xs font-semibold bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20">
              <span className="material-symbols-outlined text-[18px]">error</span>
              <span>{editError}</span>
            </div>
          )}

          <form onSubmit={handleEditSubmit} className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label htmlFor="edit-name" className="text-xs font-bold">
                Workspace Name <span className="text-red-500">*</span>
              </Label>
              <Input
                id="edit-name"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                required
                maxLength={255}
                className="rounded-xl border-[var(--outline-variant)]/40 text-sm"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="edit-desc" className="text-xs font-bold">
                Description <span className="text-xs font-normal opacity-70">(Optional)</span>
              </Label>
              <Textarea
                id="edit-desc"
                value={editDesc}
                onChange={(e) => setEditDesc(e.target.value)}
                maxLength={1000}
                rows={3}
                className="rounded-xl border-[var(--outline-variant)]/40 text-sm resize-none"
              />
            </div>

            <DialogFooter className="pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={() => setEditDialogOpen(false)}
                disabled={submitting}
                className="rounded-xl text-xs font-bold"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={submitting || !editName.trim()}
                className="ds-btn-primary rounded-xl text-xs font-bold px-5"
              >
                {submitting ? (
                  <div className="flex items-center gap-2">
                    <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Saving...
                  </div>
                ) : (
                  "Save Changes"
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ── Archive Confirmation Dialog ─────────────────────────── */}
      <Dialog open={archiveOpen} onOpenChange={setArchiveOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-xl font-bold text-amber-600 dark:text-amber-400">
              <span className="material-symbols-outlined text-[22px]">archive</span>
              Archive Workspace
            </DialogTitle>
            <DialogDescription className="text-xs leading-relaxed pt-2">
              Are you sure you want to archive &quot;{selectedWorkspace?.workspace_name}&quot;?
              <br />
              Archiving removes this workspace from active listings. All workspace members and historical records will be preserved safely.
            </DialogDescription>
          </DialogHeader>

          {archiveError && (
            <div className="p-3 rounded-xl flex items-center gap-2 text-xs font-semibold bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20">
              <span className="material-symbols-outlined text-[18px]">error</span>
              <span>{archiveError}</span>
            </div>
          )}

          <DialogFooter className="pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => setArchiveOpen(false)}
              disabled={submitting}
              className="rounded-xl text-xs font-bold"
            >
              Cancel
            </Button>
            <Button
              type="button"
              onClick={handleArchiveConfirm}
              disabled={submitting}
              className="bg-amber-600 hover:bg-amber-700 text-white rounded-xl text-xs font-bold px-5 cursor-pointer"
            >
              {submitting ? (
                <div className="flex items-center gap-2">
                  <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Archiving...
                </div>
              ) : (
                "Archive Workspace"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
