"use client";

import React, { useEffect, useState, useCallback, useMemo } from "react";
import Link from "next/link";
import {
  fetchAssignments,
  createAssignment,
  Assignment,
  AssignmentStatus,
} from "@/lib/assignments";
import { fetchWorkspaces, Workspace } from "@/lib/workspaces";
import { fetchSubjects, Subject } from "@/lib/subjects";
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
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function AssignmentsPage() {
  const { hasPermission, isLoaded: permLoaded, orgId } = usePermissions();

  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Search
  const [search, setSearch] = useState("");
  const [subjectFilter, setSubjectFilter] = useState<string>("all");
  const [studentTab, setStudentTab] = useState<"all" | "pending" | "submitted" | "due_soon" | "completed">("all");
  const [teacherTab, setTeacherTab] = useState<"all" | "draft" | "published" | "due_soon" | "needs_grading" | "closed">("all");

  // Create Assignment Modal State
  const [createOpen, setCreateOpen] = useState(false);
  const [createSubjectId, setCreateSubjectId] = useState("");
  const [createTitle, setCreateTitle] = useState("");
  const [createDesc, setCreateDesc] = useState("");
  const [createDueDate, setCreateDueDate] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const isTeacherOrAdmin = hasPermission("assignment.create") || hasPermission("subject.create") || hasPermission("member.update");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Fetch assignments across organization
      const assignData = await fetchAssignments();
      setAssignments(assignData);

      // 2. If educator/admin, fetch workspaces & subjects for assignment creation modal
      let availableSubjects: Subject[] = [];
      if (isTeacherOrAdmin) {
        try {
          const wsData = await fetchWorkspaces();
          setWorkspaces(wsData);
          const subPromises = wsData.map((ws) => fetchSubjects(ws.workspace_id).catch(() => []));
          const subArrays = await Promise.all(subPromises);
          availableSubjects = subArrays.flat();
        } catch {
          // Ignore error
        }
      }

      // 3. Populate subject filter options from returned assignments
      if (availableSubjects.length === 0 && assignData.length > 0) {
        const seen = new Set<string>();
        const extracted: Subject[] = [];
        for (const a of assignData) {
          if (a.assignment_subject_id && !seen.has(a.assignment_subject_id)) {
            seen.add(a.assignment_subject_id);
            extracted.push({
              subject_id: a.assignment_subject_id,
              subject_name: a.subject_name || "Subject",
              subject_workspace_id: a.workspace_id || "",
              subject_status: "active",
              subject_created_at: a.assignment_created_at,
              subject_updated_at: a.assignment_updated_at,
            } as Subject);
          }
        }
        availableSubjects = extracted;
      }
      setSubjects(availableSubjects);
    } catch (err: any) {
      setError(err?.message || "Failed to load assignments.");
    } finally {
      setLoading(false);
    }
  }, [isTeacherOrAdmin]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Handle Create Assignment
  const handleCreateAssignment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createTitle.trim()) {
      setCreateError("Assignment title is required.");
      return;
    }
    if (!createSubjectId) {
      setCreateError("Please select a subject.");
      return;
    }

    setCreating(true);
    setCreateError(null);
    try {
      let isoDue: string | undefined = undefined;
      if (createDueDate) {
        isoDue = new Date(createDueDate).toISOString();
      }

      await createAssignment({
        subject_id: createSubjectId,
        title: createTitle.trim(),
        description: createDesc.trim() || undefined,
        due_at: isoDue,
      });

      setCreateOpen(false);
      setCreateTitle("");
      setCreateDesc("");
      setCreateDueDate("");
      setCreateSubjectId("");
      await loadData();
    } catch (err: any) {
      setCreateError(err?.message || "Failed to create assignment.");
    } finally {
      setCreating(false);
    }
  };

  // Filtered assignments
  const filteredAssignments = useMemo(() => {
    return assignments.filter((a) => {
      // Search filter
      const matchesSearch =
        a.assignment_title.toLowerCase().includes(search.toLowerCase()) ||
        (a.assignment_description && a.assignment_description.toLowerCase().includes(search.toLowerCase())) ||
        (a.subject_name && a.subject_name.toLowerCase().includes(search.toLowerCase()));

      if (!matchesSearch) return false;

      // Subject filter
      if (subjectFilter !== "all" && a.assignment_subject_id !== subjectFilter) {
        return false;
      }

      const now = new Date();
      const dueDate = a.assignment_due_at ? new Date(a.assignment_due_at) : null;
      const isDueSoon = dueDate ? dueDate > now && (dueDate.getTime() - now.getTime()) <= 3 * 86400 * 1000 : false;

      // Role-specific Tab Filtering
      if (isTeacherOrAdmin) {
        if (teacherTab === "draft" && a.assignment_status !== "draft") return false;
        if (teacherTab === "published" && a.assignment_status !== "published") return false;
        if (teacherTab === "closed" && a.assignment_status !== "closed") return false;
        if (teacherTab === "due_soon" && (a.assignment_status !== "published" || !isDueSoon)) return false;
        if (teacherTab === "needs_grading") {
          const pending = (a.pending_count ?? 0) > 0;
          if (!pending) return false;
        }
      } else {
        // Student Tabs
        const hasSub = !!a.student_submission && a.student_submission.submission_status !== "draft";
        const subStatus = a.student_submission?.submission_status;

        if (studentTab === "pending" && hasSub) return false;
        if (studentTab === "due_soon" && (!isDueSoon || hasSub)) return false;
        if (studentTab === "submitted" && (!hasSub || subStatus === "graded" || subStatus === "returned")) return false;
        if (studentTab === "completed" && (subStatus !== "graded" && subStatus !== "returned")) return false;
      }

      return true;
    });
  }, [assignments, search, subjectFilter, studentTab, teacherTab, isTeacherOrAdmin]);

  if (permLoaded && !hasPermission("assignment.read")) {
    return <ForbiddenState message="You do not have permission to view assignments." />;
  }

  return (
    <div className="min-h-screen p-6 md:p-10" style={{ backgroundColor: "var(--surface)" }}>
      {/* Header */}
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="material-symbols-outlined text-[24px]" style={{ color: "var(--primary)" }}>
                assignment
              </span>
              <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight" style={{ color: "var(--on-surface)" }}>
                Assignments
              </h1>
              <Badge variant="outline" className="ml-2 font-mono text-xs uppercase">
                {isTeacherOrAdmin ? "Teacher / Admin View" : "Student View"}
              </Badge>
            </div>
            <p className="text-sm font-medium text-muted-foreground">
              {isTeacherOrAdmin
                ? "Manage class assignments, track student submissions, and review graded coursework."
                : "View upcoming coursework, submit your homework, and review feedback from your teachers."}
            </p>
          </div>

          {isTeacherOrAdmin && (
            <Button
              onClick={() => {
                setCreateError(null);
                setCreateOpen(true);
              }}
              className="gap-2 shrink-0 font-bold shadow-md cursor-pointer"
              style={{
                backgroundColor: "var(--primary)",
                color: "var(--on-primary)",
              }}
            >
              <span className="material-symbols-outlined text-[18px]">add_circle</span>
              New Assignment
            </Button>
          )}
        </div>

        {/* Filters and Controls */}
        <div className="bg-card border rounded-2xl p-4 md:p-5 shadow-sm space-y-4">
          <div className="flex flex-col md:flex-row gap-3 items-center justify-between">
            {/* Search Input */}
            <div className="relative w-full md:w-96">
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-[18px] text-muted-foreground">
                search
              </span>
              <Input
                type="text"
                placeholder="Search assignments by title or description..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9 bg-background"
              />
            </div>

            {/* Subject Filter Dropdown */}
            <div className="w-full md:w-64">
              <Select value={subjectFilter} onValueChange={setSubjectFilter}>
                <SelectTrigger className="bg-background">
                  <SelectValue placeholder="All Subjects" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Subjects</SelectItem>
                  {subjects.map((s) => (
                    <SelectItem key={s.subject_id} value={s.subject_id}>
                      {s.subject_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Role-Specific Tabs */}
          <div className="flex items-center gap-1 overflow-x-auto pt-2 border-t border-border">
            {isTeacherOrAdmin ? (
              <>
                {(
                  [
                    { key: "all", label: "All" },
                    { key: "draft", label: "Draft" },
                    { key: "published", label: "Published" },
                    { key: "due_soon", label: "Due Soon" },
                    { key: "needs_grading", label: "Needs Grading" },
                    { key: "closed", label: "Closed" },
                  ] as const
                ).map((tab) => (
                  <button
                    key={tab.key}
                    onClick={() => setTeacherTab(tab.key)}
                    className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors cursor-pointer ${
                      teacherTab === tab.key
                        ? "bg-primary text-primary-foreground shadow-sm"
                        : "text-muted-foreground hover:bg-muted"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </>
            ) : (
              <>
                {(
                  [
                    { key: "all", label: "All" },
                    { key: "pending", label: "Pending" },
                    { key: "submitted", label: "Submitted" },
                    { key: "due_soon", label: "Due Soon" },
                    { key: "completed", label: "Completed" },
                  ] as const
                ).map((tab) => (
                  <button
                    key={tab.key}
                    onClick={() => setStudentTab(tab.key)}
                    className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors cursor-pointer ${
                      studentTab === tab.key
                        ? "bg-primary text-primary-foreground shadow-sm"
                        : "text-muted-foreground hover:bg-muted"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </>
            )}
          </div>
        </div>

        {/* Assignments Grid */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="h-56 bg-card rounded-2xl border animate-pulse p-6 space-y-4">
                <div className="h-4 bg-muted rounded w-1/3"></div>
                <div className="h-6 bg-muted rounded w-3/4"></div>
                <div className="h-4 bg-muted rounded w-full"></div>
                <div className="h-10 bg-muted rounded w-full mt-auto"></div>
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="p-8 text-center rounded-2xl bg-destructive/10 border border-destructive/20 text-destructive">
            <span className="material-symbols-outlined text-[36px] mb-2">error</span>
            <p className="font-semibold">{error}</p>
            <Button onClick={loadData} variant="outline" className="mt-4">
              Try Again
            </Button>
          </div>
        ) : filteredAssignments.length === 0 ? (
          <div className="p-12 text-center rounded-2xl bg-card border shadow-sm space-y-3">
            <span className="material-symbols-outlined text-[48px] text-muted-foreground">assignment_late</span>
            <h3 className="text-lg font-bold">No assignments found</h3>
            <p className="text-sm text-muted-foreground max-w-md mx-auto">
              {search || subjectFilter !== "all"
                ? "No assignments matched your current filters. Try changing or clearing your search criteria."
                : isTeacherOrAdmin
                ? "Get started by creating your first assignment for this class."
                : "You don't have any assignments assigned in this category right now."}
            </p>
            {isTeacherOrAdmin && !search && subjectFilter === "all" && (
              <Button onClick={() => setCreateOpen(true)} className="mt-2 font-bold cursor-pointer">
                Create Assignment
              </Button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredAssignments.map((assignment) => {
              const dueDate = assignment.assignment_due_at ? new Date(assignment.assignment_due_at) : null;
              const now = new Date();
              const isPast = dueDate ? now > dueDate : false;
              const hasSub = !!assignment.student_submission && assignment.student_submission.submission_status !== "draft";
              const subStatus = assignment.student_submission?.submission_status;
              const subGrade = assignment.student_submission?.submission_grade;

              return (
                <div
                  key={assignment.assignment_id}
                  className="group bg-card rounded-2xl border p-6 flex flex-col justify-between hover:shadow-lg transition-all duration-200 hover:border-primary/40 relative overflow-hidden"
                >
                  <div className="space-y-3">
                    {/* Top Chips */}
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-primary/10 text-primary border border-primary/20">
                          {assignment.subject_name || "Subject"}
                        </span>
                        {assignment.workspace_name && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-muted text-muted-foreground">
                            {assignment.workspace_name}
                          </span>
                        )}
                      </div>

                      {/* Status Badges */}
                      {isTeacherOrAdmin ? (
                        <Badge
                          variant={
                            assignment.assignment_status === "published"
                              ? "default"
                              : assignment.assignment_status === "closed"
                              ? "secondary"
                              : "outline"
                          }
                          className="capitalize text-[10px] font-bold"
                        >
                          {assignment.assignment_status}
                        </Badge>
                      ) : (
                        <div>
                          {subStatus === "graded" ? (
                            <Badge className="bg-emerald-500/15 text-emerald-600 border border-emerald-500/30 text-[10px] font-bold">
                              Graded: {subGrade !== null && subGrade !== undefined ? `${subGrade}/100` : "Complete"}
                            </Badge>
                          ) : subStatus === "submitted" ? (
                            <Badge className="bg-blue-500/15 text-blue-600 border border-blue-500/30 text-[10px] font-bold">
                              Submitted
                            </Badge>
                          ) : subStatus === "late" ? (
                            <Badge className="bg-amber-500/15 text-amber-600 border border-amber-500/30 text-[10px] font-bold">
                              Late Submission
                            </Badge>
                          ) : isPast ? (
                            <Badge variant="destructive" className="text-[10px] font-bold">
                              Missing / Overdue
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="text-[10px] font-bold">
                              Not Submitted
                            </Badge>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Title & Description */}
                    <div>
                      <Link
                        href={`/classroom/assignments/${assignment.assignment_id}`}
                        className="text-base font-bold line-clamp-1 group-hover:text-primary transition-colors block"
                        style={{ color: "var(--on-surface)" }}
                      >
                        {assignment.assignment_title}
                      </Link>
                      {assignment.assignment_description && (
                        <p className="text-xs text-muted-foreground line-clamp-2 mt-1">
                          {assignment.assignment_description}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Due Date & Submission Counts */}
                  <div className="pt-4 mt-4 border-t border-border/60 space-y-3">
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <div className="flex items-center gap-1.5">
                        <span className="material-symbols-outlined text-[16px]">schedule</span>
                        <span>
                          {dueDate
                            ? dueDate.toLocaleDateString("en-US", {
                                month: "short",
                                day: "numeric",
                                hour: "2-digit",
                                minute: "2-digit",
                              })
                            : "No due date"}
                        </span>
                      </div>

                      {isTeacherOrAdmin && assignment.submission_count !== undefined && (
                        <span className="font-semibold text-[11px] text-foreground">
                          {assignment.submission_count || 0} Submissions
                        </span>
                      )}
                    </div>

                    {/* Teacher Submission Stats Bar */}
                    {isTeacherOrAdmin && assignment.submission_count !== undefined && (
                      <div className="flex items-center gap-2 text-[11px] font-medium text-muted-foreground">
                        <span className="text-emerald-600 font-bold">{assignment.graded_count || 0} Graded</span>
                        <span>•</span>
                        <span className="text-amber-600 font-bold">{assignment.pending_count || 0} Pending</span>
                      </div>
                    )}

                    {/* Action Button */}
                    <Link
                      href={`/classroom/assignments/${assignment.assignment_id}`}
                      className="block w-full"
                    >
                      <Button
                        variant={isTeacherOrAdmin ? "outline" : hasSub ? "secondary" : "default"}
                        className="w-full text-xs font-bold justify-between cursor-pointer"
                      >
                        <span>
                          {isTeacherOrAdmin
                            ? "Manage & Grade"
                            : hasSub
                            ? assignment.assignment_status === "published"
                              ? "View / Resubmit"
                              : "View Submission"
                            : "View & Submit"}
                        </span>
                        <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
                      </Button>
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Create Assignment Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Create New Assignment</DialogTitle>
            <DialogDescription>
              Create an assignment draft for a subject. You can add instructions and attachments before publishing.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleCreateAssignment} className="space-y-4 py-2">
            {createError && (
              <div className="p-3 rounded-lg bg-destructive/15 text-destructive text-xs font-semibold">
                {createError}
              </div>
            )}

            {/* Subject Selector */}
            <div className="space-y-1.5">
              <Label htmlFor="createSubject">Subject *</Label>
              <Select value={createSubjectId} onValueChange={setCreateSubjectId}>
                <SelectTrigger id="createSubject">
                  <SelectValue placeholder="Select subject" />
                </SelectTrigger>
                <SelectContent>
                  {subjects.map((s) => (
                    <SelectItem key={s.subject_id} value={s.subject_id}>
                      {s.subject_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Title */}
            <div className="space-y-1.5">
              <div className="flex justify-between">
                <Label htmlFor="createTitle">Assignment Title *</Label>
                <span className="text-[11px] text-muted-foreground">{createTitle.length}/255</span>
              </div>
              <Input
                id="createTitle"
                placeholder="e.g. Chapter 4 Calculus Problem Set"
                maxLength={255}
                value={createTitle}
                onChange={(e) => setCreateTitle(e.target.value)}
                required
              />
            </div>

            {/* Description / Instructions */}
            <div className="space-y-1.5">
              <Label htmlFor="createDesc">Instructions / Description</Label>
              <Textarea
                id="createDesc"
                placeholder="Provide instructions, rubric guidelines, and reading requirements..."
                rows={4}
                value={createDesc}
                onChange={(e) => setCreateDesc(e.target.value)}
              />
            </div>

            {/* Due Date & Time */}
            <div className="space-y-1.5">
              <Label htmlFor="createDue">Due Date & Time (Optional)</Label>
              <Input
                id="createDue"
                type="datetime-local"
                value={createDueDate}
                onChange={(e) => setCreateDueDate(e.target.value)}
              />
            </div>

            <DialogFooter className="pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setCreateOpen(false)}
                disabled={creating}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={creating} className="font-bold">
                {creating ? "Creating..." : "Create Draft"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
