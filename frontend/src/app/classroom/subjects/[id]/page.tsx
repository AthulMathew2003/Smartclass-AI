"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  fetchSubject,
  fetchSubjectTeachers,
  addSubjectTeacher,
  removeSubjectTeacher,
  updateSubject,
  Subject,
  SubjectTeacher
} from "@/lib/subjects";
import { fetchWorkspaceMembers, WorkspaceMemberItem } from "@/lib/workspaces";
import { usePermissions } from "@/lib/permissions";
import ForbiddenState from "../../components/ForbiddenState";
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function SubjectDetailsPage() {
  const { id } = useParams() as { id: string };
  const searchParams = useSearchParams();
  const workspaceIdFromQuery = searchParams.get("workspace_id");
  const router = useRouter();
  
  const { hasPermission, isLoaded: permLoaded, orgId } = usePermissions();

  const [subject, setSubject] = useState<Subject | null>(null);
  const [teachers, setTeachers] = useState<SubjectTeacher[]>([]);
  const [workspaceMembers, setWorkspaceMembers] = useState<WorkspaceMemberItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isForbidden, setIsForbidden] = useState(false);

  // Edit Modal State
  const [editOpen, setEditDialogOpen] = useState(false);
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [editError, setEditError] = useState<string | null>(null);

  // Add Teacher Modal State
  const [addOpen, setAddOpen] = useState(false);
  const [addUserId, setAddUserId] = useState("");
  const [addError, setAddError] = useState<string | null>(null);

  // Remove Teacher Modal State
  const [removeOpen, setRemoveOpen] = useState(false);
  const [teacherToRemove, setTeacherToRemove] = useState<SubjectTeacher | null>(null);
  const [removeError, setRemoveError] = useState<string | null>(null);

  const [submitting, setSubmitting] = useState(false);

  const loadData = useCallback(async () => {
    if (!workspaceIdFromQuery) {
      setError("Workspace ID is missing from the URL. Cannot load subject.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    setIsForbidden(false);
    try {
      const subj = await fetchSubject(id, workspaceIdFromQuery);
      setSubject(subj);

      const mems = await fetchSubjectTeachers(id, workspaceIdFromQuery);
      setTeachers(mems);

      if (hasPermission("subject.teacher.add")) {
        try {
          const wsMems = await fetchWorkspaceMembers(workspaceIdFromQuery);
          setWorkspaceMembers(wsMems);
        } catch {
          // Handled gracefully
        }
      }
    } catch (err: any) {
      const msg = err.message || "Failed to load subject details.";
      if (msg.toLowerCase().includes("permission") || msg.toLowerCase().includes("denied") || msg.includes("403")) {
        setIsForbidden(true);
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  }, [id, workspaceIdFromQuery, hasPermission]);

  useEffect(() => {
    if (permLoaded && hasPermission("subject.read")) {
      loadData();
    }
  }, [permLoaded, orgId, loadData, hasPermission]);

  if (!permLoaded || loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="flex items-center gap-3 text-sm font-semibold text-[var(--on-surface-variant)]">
          <div className="w-6 h-6 border-2 border-t-transparent border-[var(--primary)] rounded-full animate-spin" />
          {loading ? "Loading subject..." : "Checking permissions..."}
        </div>
      </div>
    );
  }

  if (!hasPermission("subject.read") || isForbidden) {
    return (
      <ForbiddenState
        message="You do not have permission to view this subject."
      />
    );
  }

  if (error || !subject) {
    return (
      <div className="p-6 max-w-6xl mx-auto space-y-4">
        <div className="p-4 rounded-xl bg-red-50 text-red-600 text-sm border border-red-200">
          {error || "Subject not found"}
        </div>
        <Button variant="outline" onClick={() => router.push("/classroom/subjects")}>
          &larr; Back to Subjects
        </Button>
      </div>
    );
  }

  const isArchived = subject.subject_status === "archived";
  const canEdit = hasPermission("subject.update") && !isArchived;
  const canAddTeacher = hasPermission("subject.teacher.add") && !isArchived;
  const canRemoveTeacher = hasPermission("subject.teacher.remove") && !isArchived;

  // Only Workspace Members with a Teacher role can be assigned
  const availableUsers = workspaceMembers.filter(
    wu => wu.role_name === "Teacher" && !teachers.some(t => t.subject_teacher_user_id === wu.user_id)
  );

  const handleEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspaceIdFromQuery) return;
    setEditError(null);
    if (!editName.trim()) {
      setEditError("Subject name is required.");
      return;
    }
    setSubmitting(true);
    try {
      const updated = await updateSubject(id, workspaceIdFromQuery, {
        subject_name: editName.trim(),
        subject_description: editDesc.trim() || undefined
      });
      setSubject(updated);
      setEditDialogOpen(false);
    } catch (err: any) {
      setEditError(err.message || "Failed to update subject.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleAddTeacher = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspaceIdFromQuery) return;
    setAddError(null);
    if (!addUserId) {
      setAddError("Please select a teacher.");
      return;
    }
    setSubmitting(true);
    try {
      await addSubjectTeacher(id, workspaceIdFromQuery, {
        user_id: addUserId
      });
      await loadData();
      setAddOpen(false);
      setAddUserId("");
    } catch (err: any) {
      setAddError(err.message || "Failed to assign teacher.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleRemoveTeacher = async () => {
    if (!teacherToRemove || !workspaceIdFromQuery) return;
    setRemoveError(null);
    setSubmitting(true);
    try {
      await removeSubjectTeacher(id, teacherToRemove.subject_teacher_user_id, workspaceIdFromQuery);
      await loadData();
      setRemoveOpen(false);
      setTeacherToRemove(null);
    } catch (err: any) {
      setRemoveError(err.message || "Failed to remove teacher.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <Link href="/classroom/subjects" className="text-sm font-medium text-[var(--primary)] hover:underline mb-4 inline-flex items-center gap-1">
          <span className="material-symbols-outlined text-[16px]">arrow_back</span>
          Back to Subjects
        </Link>
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mt-2">
          <div>
            <h1 className="text-3xl font-bold text-[var(--on-surface)] flex items-center gap-3">
              {subject.subject_name}
              {isArchived && (
                <Badge variant="secondary" className="bg-[var(--surface-container-high)] text-[var(--on-surface-variant)]">
                  Archived
                </Badge>
              )}
            </h1>
            {subject.subject_description && (
              <p className="text-[var(--on-surface-variant)] mt-2 max-w-2xl">{subject.subject_description}</p>
            )}
          </div>
          <div className="flex items-center gap-3 self-start sm:self-auto">
            {canEdit && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setEditName(subject.subject_name);
                  setEditDesc(subject.subject_description || "");
                  setEditDialogOpen(true);
                }}
              >
                <span className="material-symbols-outlined mr-1.5 text-[18px]">edit</span>
                Edit
              </Button>
            )}
            <div className="text-right">
              <div className="text-xs text-[var(--on-surface-variant)] font-medium uppercase tracking-wider">Status</div>
              <div className={`font-bold capitalize text-sm ${isArchived ? "text-amber-600" : "text-emerald-600"}`}>
                {subject.subject_status}
              </div>
            </div>
          </div>
        </div>
      </div>

      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="bg-[var(--surface-container-low)]">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="teachers">Teachers ({teachers.length})</TabsTrigger>
        </TabsList>
        
        <TabsContent value="overview" className="space-y-6 pt-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="p-6 rounded-xl bg-[var(--surface-container-lowest)] border border-[var(--outline-variant)]">
              <div className="text-sm text-[var(--on-surface-variant)] font-medium mb-1">Assigned Teachers</div>
              <div className="text-3xl font-bold text-[var(--on-surface)]">{teachers.length}</div>
            </div>
            <div className="p-6 rounded-xl bg-[var(--surface-container-lowest)] border border-[var(--outline-variant)]">
              <div className="text-sm text-[var(--on-surface-variant)] font-medium mb-1">Created</div>
              <div className="text-lg font-bold text-[var(--on-surface)]">
                {new Date(subject.subject_created_at).toLocaleDateString()}
              </div>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="teachers" className="space-y-8 pt-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-[var(--on-surface)]">Assigned Teachers</h2>
            {canAddTeacher && (
              <Button onClick={() => setAddOpen(true)} className="bg-[var(--primary)] text-[var(--on-primary)] hover:opacity-90">
                <span className="material-symbols-outlined mr-2 text-[20px]">person_add</span>
                Assign Teacher
              </Button>
            )}
          </div>

          <div className="space-y-6">
            <div>
              {teachers.length === 0 ? (
                <p className="text-sm text-[var(--on-surface-variant)] italic">No teachers assigned.</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {teachers.map(t => (
                    <div key={t.subject_teacher_id} className="flex items-center justify-between p-3.5 rounded-xl border border-[var(--outline-variant)] bg-[var(--surface-container-lowest)]">
                      <div className="truncate pr-2">
                        <div className="font-semibold text-sm truncate text-[var(--on-surface)]">
                          {t.user_first_name || t.user_last_name ? `${t.user_first_name || ""} ${t.user_last_name || ""}`.trim() : (t.user_email || "Teacher")}
                        </div>
                        <div className="text-xs text-[var(--on-surface-variant)] truncate">
                          {t.user_email || `ID: ${t.subject_teacher_user_id.slice(0, 8)}...`}
                        </div>
                      </div>
                      {canRemoveTeacher && (
                        <Button variant="ghost" size="icon" className="text-red-500 hover:text-red-700 hover:bg-red-50 shrink-0" title="Remove Teacher" onClick={() => {
                          setTeacherToRemove(t);
                          setRemoveOpen(true);
                        }}>
                          <span className="material-symbols-outlined text-[18px]">person_remove</span>
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </TabsContent>
      </Tabs>

      {/* Edit Subject Dialog */}
      <Dialog open={editOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Edit Subject</DialogTitle>
            <DialogDescription>
              Update name or description for this subject.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleEdit} className="space-y-4 py-4">
            {editError && (
              <div className="p-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg">
                {editError}
              </div>
            )}
            <div className="space-y-2">
              <Label>Subject Name *</Label>
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

      {/* Add Teacher Dialog */}
      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Assign Teacher</DialogTitle>
            <DialogDescription>
              Assign a workspace teacher to this subject.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleAddTeacher} className="space-y-4 py-4">
            {addError && (
              <div className="p-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg">
                {addError}
              </div>
            )}
            
            <div className="space-y-2">
              <Label>Select Teacher *</Label>
              {availableUsers.length > 0 ? (
                <Select value={addUserId} onValueChange={setAddUserId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a workspace teacher..." />
                  </SelectTrigger>
                  <SelectContent>
                    {availableUsers.map(u => (
                      <SelectItem key={u.user_id} value={u.user_id}>
                        {u.first_name || u.email} {u.last_name || ""} ({u.email})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : (
                <div className="text-sm text-amber-600 bg-amber-50 p-3 rounded-lg border border-amber-200">
                  No eligible workspace teachers available to add.
                </div>
              )}
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setAddOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={submitting || !addUserId}>
                {submitting ? "Assigning..." : "Assign Teacher"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Remove Teacher Dialog */}
      <Dialog open={removeOpen} onOpenChange={setRemoveOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle className="text-red-600">Remove Teacher</DialogTitle>
            <DialogDescription>
              Are you sure you want to remove <strong>{teacherToRemove?.user_first_name} {teacherToRemove?.user_last_name}</strong>?
            </DialogDescription>
          </DialogHeader>
          <div className="py-4 text-sm text-[var(--on-surface-variant)] space-y-2">
            <p>They will no longer be assigned to <strong>{subject?.subject_name}</strong>.</p>
            {removeError && (
              <div className="p-3 text-red-600 bg-red-50 border border-red-200 rounded-lg mt-4">
                {removeError}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRemoveOpen(false)} disabled={submitting}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleRemoveTeacher} disabled={submitting}>
              {submitting ? "Removing..." : "Remove Teacher"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
