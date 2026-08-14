"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  fetchAssignments,
  createAssignment,
  Assignment,
  AssignmentStatus,
} from "@/lib/assignments";
import { fetchSubject, Subject } from "@/lib/subjects";
import { usePermissions } from "@/lib/permissions";
import ForbiddenState from "../../../components/ForbiddenState";
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
  DialogFooter,
} from "@/components/ui/dialog";

export default function SubjectAssignmentsPage() {
  const { id } = useParams() as { id: string };
  const searchParams = useSearchParams();
  const workspaceIdFromQuery = searchParams.get("workspace_id");
  const router = useRouter();

  const { hasPermission, isLoaded: permLoaded, orgId } = usePermissions();

  const [subject, setSubject] = useState<Subject | null>(null);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isForbidden, setIsForbidden] = useState(false);

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<AssignmentStatus | "all">("all");

  // Create Assignment Modal State
  const [createOpen, setCreateOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const canCreate = hasPermission("assignment.create");
  const canUpdate = hasPermission("assignment.update");
  const isTeacherOrAdmin = canCreate || canUpdate;

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    setIsForbidden(false);

    try {
      if (workspaceIdFromQuery) {
        try {
          const subjData = await fetchSubject(id, workspaceIdFromQuery);
          setSubject(subjData);
        } catch {
          // Handled gracefully if subject fetch fails
        }
      }

      const list = await fetchAssignments(id, statusFilter);
      setAssignments(list);
    } catch (err: any) {
      const msg = err.message || "Failed to load assignments.";
      if (
        msg.toLowerCase().includes("permission") ||
        msg.toLowerCase().includes("denied") ||
        msg.includes("403")
      ) {
        setIsForbidden(true);
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  }, [id, workspaceIdFromQuery, statusFilter]);

  useEffect(() => {
    if (permLoaded && hasPermission("assignment.read")) {
      loadData();
    }
  }, [permLoaded, orgId, loadData, hasPermission]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError(null);

    if (!title.trim()) {
      setCreateError("Assignment title is required.");
      return;
    }

    setSubmitting(true);
    try {
      const formattedDue = dueAt ? new Date(dueAt).toISOString() : undefined;
      await createAssignment({
        subject_id: id,
        title: title.trim(),
        description: description.trim() || undefined,
        due_at: formattedDue,
      });

      setTitle("");
      setDescription("");
      setDueAt("");
      setCreateOpen(false);
      await loadData();
    } catch (err: any) {
      setCreateError(err.message || "Failed to create assignment.");
    } finally {
      setSubmitting(false);
    }
  };

  // Filter client-side search query
  const filteredAssignments = assignments.filter((a) => {
    const q = searchQuery.toLowerCase();
    const matchesTitle = a.assignment_title.toLowerCase().includes(q);
    const matchesDesc = (a.assignment_description || "")
      .toLowerCase()
      .includes(q);
    return matchesTitle || matchesDesc;
  });

  if (!permLoaded || loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="flex items-center gap-3 text-sm font-semibold text-[var(--on-surface-variant)]">
          <div className="w-6 h-6 border-2 border-t-transparent border-[var(--primary)] rounded-full animate-spin" />
          {loading ? "Loading assignments..." : "Checking permissions..."}
        </div>
      </div>
    );
  }

  if (!hasPermission("assignment.read") || isForbidden) {
    return (
      <ForbiddenState message="You do not have permission to view assignments for this subject." />
    );
  }

  const getStatusBadge = (status: AssignmentStatus) => {
    switch (status) {
      case "draft":
        return (
          <Badge
            variant="secondary"
            className="bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-700 capitalize font-medium"
          >
            Draft
          </Badge>
        );
      case "published":
        return (
          <Badge className="bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800 capitalize font-medium">
            Published
          </Badge>
        );
      case "closed":
        return (
          <Badge className="bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border border-amber-300 dark:border-amber-800 capitalize font-medium">
            Closed
          </Badge>
        );
      case "archived":
        return (
          <Badge
            variant="outline"
            className="bg-zinc-100 dark:bg-zinc-800 text-zinc-500 capitalize font-medium"
          >
            Archived
          </Badge>
        );
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  const formatDueDate = (isoString?: string | null) => {
    if (!isoString) return null;
    const date = new Date(isoString);
    const isPast = date.getTime() < Date.now();
    return {
      formatted: date.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      }),
      isPast,
    };
  };

  const subjectBackUrl = workspaceIdFromQuery
    ? `/classroom/subjects/${id}?workspace_id=${workspaceIdFromQuery}`
    : `/classroom/subjects/${id}`;

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-8">
      {/* Header & Breadcrumb */}
      <div>
        <Link
          href={subjectBackUrl}
          className="text-sm font-medium text-[var(--primary)] hover:underline mb-3 inline-flex items-center gap-1"
        >
          <span className="material-symbols-outlined text-[16px]">arrow_back</span>
          Back to {subject?.subject_name || "Subject"}
        </Link>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mt-2">
          <div>
            <h1 className="text-3xl font-bold text-[var(--on-surface)] flex items-center gap-3">
              Assignments
              <span className="text-sm font-semibold px-2.5 py-0.5 rounded-full bg-[var(--surface-container-high)] text-[var(--on-surface-variant)]">
                {assignments.length}
              </span>
            </h1>
            <p className="text-sm text-[var(--on-surface-variant)] mt-1">
              {subject
                ? `Coursework and assessments for ${subject.subject_name}`
                : "Manage and view subject assignments"}
            </p>
          </div>

          {canCreate && (
            <Button
              onClick={() => setCreateOpen(true)}
              className="bg-[var(--primary)] text-[var(--on-primary)] hover:opacity-90 self-start sm:self-auto shadow-sm"
            >
              <span className="material-symbols-outlined mr-2 text-[20px]">add</span>
              Create Assignment
            </Button>
          )}
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/40 text-red-600 dark:text-red-400 text-sm border border-red-200 dark:border-red-800 flex items-center justify-between">
          <span>{error}</span>
          <Button variant="outline" size="sm" onClick={loadData}>
            Retry
          </Button>
        </div>
      )}

      {/* Controls: Search & Filter */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 pb-2 border-b border-[var(--outline-variant)]">
        <div className="relative flex-1 max-w-md">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-[var(--on-surface-variant)] text-[20px]">
            search
          </span>
          <Input
            placeholder="Search assignments by title or description..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 bg-[var(--surface-container-lowest)]"
          />
        </div>

        {/* Status Filter Buttons */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          <Button
            variant={statusFilter === "all" ? "default" : "outline"}
            size="sm"
            onClick={() => setStatusFilter("all")}
            className={statusFilter === "all" ? "bg-[var(--primary)] text-[var(--on-primary)]" : ""}
          >
            All
          </Button>

          {isTeacherOrAdmin && (
            <Button
              variant={statusFilter === "draft" ? "default" : "outline"}
              size="sm"
              onClick={() => setStatusFilter("draft")}
              className={statusFilter === "draft" ? "bg-[var(--primary)] text-[var(--on-primary)]" : ""}
            >
              Draft
            </Button>
          )}

          <Button
            variant={statusFilter === "published" ? "default" : "outline"}
            size="sm"
            onClick={() => setStatusFilter("published")}
            className={statusFilter === "published" ? "bg-[var(--primary)] text-[var(--on-primary)]" : ""}
          >
            Published
          </Button>

          <Button
            variant={statusFilter === "closed" ? "default" : "outline"}
            size="sm"
            onClick={() => setStatusFilter("closed")}
            className={statusFilter === "closed" ? "bg-[var(--primary)] text-[var(--on-primary)]" : ""}
          >
            Closed
          </Button>

          {isTeacherOrAdmin && (
            <Button
              variant={statusFilter === "archived" ? "default" : "outline"}
              size="sm"
              onClick={() => setStatusFilter("archived")}
              className={statusFilter === "archived" ? "bg-[var(--primary)] text-[var(--on-primary)]" : ""}
            >
              Archived
            </Button>
          )}
        </div>
      </div>

      {/* Assignment List */}
      {filteredAssignments.length === 0 ? (
        <div className="text-center py-16 px-4 rounded-2xl border border-dashed border-[var(--outline-variant)] bg-[var(--surface-container-lowest)] space-y-4">
          <div className="w-14 h-14 mx-auto rounded-full bg-[var(--surface-container-high)] flex items-center justify-center text-[var(--on-surface-variant)]">
            <span className="material-symbols-outlined text-[28px]">assignment</span>
          </div>
          <div>
            <h3 className="text-lg font-bold text-[var(--on-surface)]">
              {isTeacherOrAdmin ? "No assignments yet" : "No assignments available"}
            </h3>
            <p className="text-sm text-[var(--on-surface-variant)] max-w-sm mx-auto mt-1">
              {isTeacherOrAdmin
                ? "Create your first assignment for this subject to start assessing student learning."
                : "Your teacher hasn't published any assignments for this subject yet. Check back soon!"}
            </p>
          </div>
          {canCreate && (
            <Button
              onClick={() => setCreateOpen(true)}
              className="bg-[var(--primary)] text-[var(--on-primary)] hover:opacity-90 mt-2"
            >
              <span className="material-symbols-outlined mr-2 text-[18px]">add</span>
              Create Assignment
            </Button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredAssignments.map((assignment) => {
            const dueInfo = formatDueDate(assignment.assignment_due_at);
            const detailUrl = workspaceIdFromQuery
              ? `/classroom/subjects/${id}/assignments/${assignment.assignment_id}?workspace_id=${workspaceIdFromQuery}`
              : `/classroom/subjects/${id}/assignments/${assignment.assignment_id}`;

            return (
              <div
                key={assignment.assignment_id}
                onClick={() => router.push(detailUrl)}
                className="p-5 rounded-2xl border border-[var(--outline-variant)] bg-[var(--surface-container-lowest)] hover:border-[var(--primary)] transition-all hover:shadow-md cursor-pointer flex flex-col justify-between group"
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <h3 className="font-bold text-lg text-[var(--on-surface)] group-hover:text-[var(--primary)] transition-colors leading-snug">
                      {assignment.assignment_title}
                    </h3>
                    <div className="shrink-0">
                      {getStatusBadge(assignment.assignment_status)}
                    </div>
                  </div>

                  {assignment.assignment_description && (
                    <p className="text-sm text-[var(--on-surface-variant)] line-clamp-2 leading-relaxed">
                      {assignment.assignment_description}
                    </p>
                  )}
                </div>

                <div className="mt-5 pt-4 border-t border-[var(--outline-variant)] flex items-center justify-between text-xs text-[var(--on-surface-variant)]">
                  <div className="flex items-center gap-1.5">
                    {dueInfo ? (
                      <span
                        className={`flex items-center gap-1 font-medium ${
                          dueInfo.isPast && assignment.assignment_status !== "closed"
                            ? "text-red-500 font-semibold"
                            : ""
                        }`}
                      >
                        <span className="material-symbols-outlined text-[16px]">schedule</span>
                        Due {dueInfo.formatted}
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-[var(--on-surface-variant)] italic">
                        <span className="material-symbols-outlined text-[16px]">event_available</span>
                        No due date
                      </span>
                    )}
                  </div>

                  <span className="text-[var(--primary)] font-semibold group-hover:translate-x-0.5 transition-transform flex items-center gap-0.5">
                    View
                    <span className="material-symbols-outlined text-[16px]">chevron_right</span>
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Assignment Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Create Assignment</DialogTitle>
            <DialogDescription>
              Create a new draft assignment for {subject?.subject_name || "this subject"}.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleCreate} className="space-y-4 py-3">
            {createError && (
              <div className="p-3 text-sm text-red-600 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 rounded-lg">
                {createError}
              </div>
            )}

            <div className="space-y-1.5">
              <Label htmlFor="assign-title">Title *</Label>
              <Input
                id="assign-title"
                placeholder="e.g. Relational Normalization Assignment"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                maxLength={255}
                autoFocus
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="assign-desc">Description</Label>
              <Textarea
                id="assign-desc"
                placeholder="Provide instructions, reading references, or question prompts..."
                rows={4}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="assign-due">Due Date & Time (Optional)</Label>
              <Input
                id="assign-due"
                type="datetime-local"
                value={dueAt}
                onChange={(e) => setDueAt(e.target.value)}
              />
            </div>

            <DialogFooter className="pt-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => setCreateOpen(false)}
                disabled={submitting}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={submitting}
                className="bg-[var(--primary)] text-[var(--on-primary)]"
              >
                {submitting ? "Creating..." : "Create Draft"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
