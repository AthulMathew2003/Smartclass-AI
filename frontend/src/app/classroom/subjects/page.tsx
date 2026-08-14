"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  fetchSubjects,
  createSubject,
  updateSubject,
  archiveSubject,
  Subject
} from "@/lib/subjects";
import { fetchWorkspaces, Workspace } from "@/lib/workspaces";
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export default function SubjectsPage() {
  const { hasPermission, isLoaded: permLoaded, orgId } = usePermissions();

  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Search
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "archived">("active");
  const [workspaceFilter, setWorkspaceFilter] = useState<string>("all");

  // Create Modal State
  const [createOpen, setCreateOpen] = useState(false);
  const [createName, setCreateName] = useState("");
  const [createDesc, setCreateDesc] = useState("");
  const [createWorkspaceId, setCreateWorkspaceId] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);

  // Edit Modal State
  const [editOpen, setEditDialogOpen] = useState(false);
  const [selectedSubject, setSelectedSubject] = useState<Subject | null>(null);
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [editError, setEditError] = useState<string | null>(null);

  // Archive Modal State
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [archiveError, setArchiveError] = useState<string | null>(null);

  const [submitting, setSubmitting] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const wsData = await fetchWorkspaces();
      setWorkspaces(wsData);

      const subjectPromises = wsData.map(ws => fetchSubjects(ws.workspace_id).catch(() => []));
      const subjectsArrays = await Promise.all(subjectPromises);
      const subjData = subjectsArrays.flat();

      setSubjects(subjData);
    } catch (err: any) {
      setError(err.message || "Failed to load subjects.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (permLoaded && hasPermission("subject.read")) {
      loadData();
    }
  }, [permLoaded, orgId, loadData, hasPermission]);

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

  if (!hasPermission("subject.read")) {
    return (
      <ForbiddenState
        message="You do not have permission to view subjects in this organization."
      />
    );
  }

  // Active workspaces for the creation dropdown
  const activeWorkspaces = workspaces.filter(w => w.workspace_status === "active");

  const filteredSubjects = subjects.filter((subj) => {
    if (statusFilter !== "all" && subj.subject_status !== statusFilter) return false;
    if (workspaceFilter !== "all" && subj.subject_workspace_id !== workspaceFilter) return false;
    if (search && !subj.subject_name.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError(null);
    if (!createName.trim() || !createWorkspaceId) {
      setCreateError("Subject name and Workspace are required.");
      return;
    }
    setSubmitting(true);
    try {
      await createSubject({
        subject_name: createName.trim(),
        subject_description: createDesc.trim() || undefined,
        workspace_id: createWorkspaceId
      });
      await loadData();
      setCreateOpen(false);
      setCreateName("");
      setCreateDesc("");
      setCreateWorkspaceId("");
    } catch (err: any) {
      setCreateError(err.message || "Failed to create subject.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSubject) return;
    setEditError(null);
    if (!editName.trim()) {
      setEditError("Subject name is required.");
      return;
    }
    setSubmitting(true);
    try {
      await updateSubject(selectedSubject.subject_id, selectedSubject.subject_workspace_id, {
        subject_name: editName.trim(),
        subject_description: editDesc.trim() || undefined
      });
      await loadData();
      setEditDialogOpen(false);
    } catch (err: any) {
      setEditError(err.message || "Failed to update subject.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleArchive = async () => {
    if (!selectedSubject) return;
    setArchiveError(null);
    setSubmitting(true);
    try {
      await archiveSubject(selectedSubject.subject_id, selectedSubject.subject_workspace_id);
      await loadData();
      setArchiveOpen(false);
    } catch (err: any) {
      setArchiveError(err.message || "Failed to archive subject.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[var(--on-surface)]">Subjects</h1>
          <p className="text-sm text-[var(--on-surface-variant)]">Manage your organization's subjects</p>
        </div>
        {hasPermission("subject.create") && (
          <Button onClick={() => setCreateOpen(true)} className="bg-[var(--primary)] text-[var(--on-primary)] hover:opacity-90 self-start sm:self-auto">
            <span className="material-symbols-outlined mr-2 text-[20px]">add</span>
            Create Subject
          </Button>
        )}
      </div>

      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4 bg-[var(--surface-container-low)] p-4 rounded-xl border border-[var(--outline-variant)]">
        <div className="flex-1">
          <Input
            placeholder="Search subjects..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full sm:max-w-xs bg-[var(--surface)]"
          />
        </div>
        {hasPermission("workspace.read") && workspaces.length > 0 && (
          <Select value={workspaceFilter} onValueChange={setWorkspaceFilter}>
            <SelectTrigger className="w-full sm:w-[180px] bg-[var(--surface)]">
              <SelectValue placeholder="Workspace" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Workspaces</SelectItem>
              {workspaces.map(w => (
                <SelectItem key={w.workspace_id} value={w.workspace_id}>
                  {w.workspace_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
        <Select value={statusFilter} onValueChange={(val: any) => setStatusFilter(val)}>
          <SelectTrigger className="w-full sm:w-[150px] bg-[var(--surface)]">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="archived">Archived</SelectItem>
            <SelectItem value="all">All Statuses</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-50 text-red-600 text-sm border border-red-200">
          {error}
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((n) => (
            <div key={n} className="h-36 rounded-xl bg-[var(--surface-container-low)] animate-pulse" />
          ))}
        </div>
      ) : filteredSubjects.length === 0 ? (
        <div className="text-center py-16 bg-[var(--surface-container-low)] rounded-xl border border-[var(--outline-variant)] space-y-4">
          <span className="material-symbols-outlined text-[48px] text-[var(--on-surface-variant)] opacity-50">
            menu_book
          </span>
          <div>
            <h3 className="text-lg font-semibold text-[var(--on-surface)]">No subjects found</h3>
            <p className="text-sm text-[var(--on-surface-variant)] mt-1">
              {search || statusFilter !== "all" || workspaceFilter !== "all"
                ? "Try adjusting your filters"
                : "Get started by creating your first subject"}
            </p>
          </div>
          {hasPermission("subject.create") && !search && statusFilter === "all" && (
            <Button onClick={() => setCreateOpen(true)} className="bg-[var(--primary)] text-[var(--on-primary)] hover:opacity-90">
              <span className="material-symbols-outlined mr-2 text-[20px]">add</span>
              Create Subject
            </Button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredSubjects.map((subj) => {
            const ws = workspaces.find((w) => w.workspace_id === subj.subject_workspace_id);
            const isArchived = subj.subject_status === "archived";
            const canEdit = hasPermission("subject.update") && !isArchived;
            const canArchive = hasPermission("subject.delete") && !isArchived;
            
            return (
              <div
                key={subj.subject_id}
                className={`relative flex flex-col p-5 rounded-2xl border transition-all duration-200 hover:shadow-md ${
                  isArchived 
                    ? "bg-[var(--surface-container-lowest)] border-[var(--outline-variant)] opacity-75" 
                    : "bg-[var(--surface)] border-[var(--outline-variant)] hover:border-[var(--primary)]"
                }`}
              >
                <div className="flex justify-between items-start mb-2">
                  <div className="flex-1 pr-2">
                    <Link href={`/classroom/subjects/${subj.subject_id}?workspace_id=${subj.subject_workspace_id}`} className="hover:underline">
                      <h3 className="font-bold text-[var(--on-surface)] text-lg truncate flex items-center gap-2">
                        {subj.subject_name}
                        {isArchived && (
                          <Badge variant="secondary" className="text-[10px] bg-[var(--surface-container-high)]">Archived</Badge>
                        )}
                      </h3>
                    </Link>
                    {ws && (
                      <p className="text-[11px] font-medium text-[var(--primary)] truncate mt-1">
                        Workspace: {ws.workspace_name}
                      </p>
                    )}
                  </div>
                  
                  {/* Dropdown Menu (only rendered if user has permissions & subject is not archived) */}
                  {(canEdit || canArchive) && (
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full -mr-2 shrink-0">
                          <span className="material-symbols-outlined text-[18px]">more_vert</span>
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        {canEdit && (
                          <DropdownMenuItem
                            onClick={() => {
                              setSelectedSubject(subj);
                              setEditName(subj.subject_name);
                              setEditDesc(subj.subject_description || "");
                              setEditDialogOpen(true);
                            }}
                          >
                            <span className="material-symbols-outlined text-[18px] mr-2">edit</span>
                            Edit
                          </DropdownMenuItem>
                        )}
                        {canArchive && (
                          <>
                            {canEdit && <DropdownMenuSeparator />}
                            <DropdownMenuItem
                              className="text-red-600 focus:text-red-600"
                              onClick={() => {
                                setSelectedSubject(subj);
                                setArchiveOpen(true);
                              }}
                            >
                              <span className="material-symbols-outlined text-[18px] mr-2">archive</span>
                              Archive
                            </DropdownMenuItem>
                          </>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  )}
                </div>
                
                {subj.subject_description && (
                  <p className="text-sm text-[var(--on-surface-variant)] line-clamp-2 mt-2 mb-4">
                    {subj.subject_description}
                  </p>
                )}

                <div className="mt-auto pt-4 flex flex-col gap-2 border-t border-[var(--outline-variant)]">
                  {subj.teachers && subj.teachers.length > 0 ? (
                    <div className="text-xs text-[var(--on-surface-variant)]">
                      Teachers: {subj.teachers.map((t) => `${t.user_first_name} ${t.user_last_name}`).join(", ")}
                    </div>
                  ) : (
                    <div className="text-xs text-[var(--on-surface-variant)] opacity-60">
                      No teachers assigned
                    </div>
                  )}
                  
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-[var(--on-surface-variant)]">
                      Created {new Date(subj.subject_created_at).toLocaleDateString()}
                    </span>
                    <Link href={`/classroom/subjects/${subj.subject_id}?workspace_id=${subj.subject_workspace_id}`}>
                      <Button variant="secondary" size="sm" className="h-8 text-xs rounded-full">
                        View
                      </Button>
                    </Link>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Create Subject</DialogTitle>
            <DialogDescription>
              Set up a new subject in an active workspace.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4 py-4">
            {createError && (
              <div className="p-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg">
                {createError}
              </div>
            )}
            <div className="space-y-2">
              <Label>Name *</Label>
              <Input
                placeholder="e.g. Artificial Intelligence"
                value={createName}
                onChange={(e) => setCreateName(e.target.value)}
                autoFocus
              />
            </div>
            <div className="space-y-2">
              <Label>Workspace *</Label>
              {activeWorkspaces.length > 0 ? (
                <Select value={createWorkspaceId} onValueChange={setCreateWorkspaceId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select an active workspace..." />
                  </SelectTrigger>
                  <SelectContent>
                    {activeWorkspaces.map(w => (
                      <SelectItem key={w.workspace_id} value={w.workspace_id}>
                        {w.workspace_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : (
                <div className="text-sm text-amber-600 bg-amber-50 p-2 rounded border border-amber-200">
                  No active workspaces available. You must create one first.
                </div>
              )}
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Textarea
                placeholder="Brief description of the subject"
                value={createDesc}
                onChange={(e) => setCreateDesc(e.target.value)}
                rows={3}
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setCreateOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={submitting || !createName.trim() || !createWorkspaceId}>
                {submitting ? "Creating..." : "Create Subject"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={editOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Edit Subject</DialogTitle>
            <DialogDescription>
              Update details for {selectedSubject?.subject_name}.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleEdit} className="space-y-4 py-4">
            {editError && (
              <div className="p-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg">
                {editError}
              </div>
            )}
            <div className="space-y-2">
              <Label>Name *</Label>
              <Input
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                autoFocus
              />
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Textarea
                value={editDesc}
                onChange={(e) => setEditDesc(e.target.value)}
                rows={3}
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setEditDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={submitting || !editName.trim()}>
                {submitting ? "Saving..." : "Save Changes"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Archive Dialog */}
      <Dialog open={archiveOpen} onOpenChange={setArchiveOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle className="text-red-600">Archive Subject</DialogTitle>
            <DialogDescription>
              Are you sure you want to archive <strong>{selectedSubject?.subject_name}</strong>?
            </DialogDescription>
          </DialogHeader>
          <div className="py-4 text-sm text-[var(--on-surface-variant)] space-y-2">
            <p>This subject will become read-only. Archived subjects cannot receive new teachers, but historical data is preserved.</p>
            {archiveError && (
              <div className="p-3 text-red-600 bg-red-50 border border-red-200 rounded-lg mt-4">
                {archiveError}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setArchiveOpen(false)} disabled={submitting}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleArchive} disabled={submitting}>
              {submitting ? "Archiving..." : "Archive"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
