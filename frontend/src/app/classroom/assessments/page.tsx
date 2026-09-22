"use client";

import React, { useEffect, useState, useCallback, useMemo } from "react";
import Link from "next/link";
import {
  fetchAssessments,
  createAssessment,
  publishAssessment,
  closeAssessment,
  archiveAssessment,
  Assessment,
  AssessmentStatus,
  AssessmentType,
} from "@/lib/assessments";
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

export default function GlobalAssessmentsPage() {
  const { hasPermission, isLoaded: permLoaded, orgId } = usePermissions();

  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Search
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [statusTab, setStatusTab] = useState<string>("all");

  // Create Modal State
  const [createOpen, setCreateOpen] = useState(false);
  const [createSubjectId, setCreateSubjectId] = useState("");
  const [createTitle, setCreateTitle] = useState("");
  const [createDesc, setCreateDesc] = useState("");
  const [createType, setCreateType] = useState<AssessmentType>("quiz");
  const [createDuration, setCreateDuration] = useState<string>("");
  const [createMarks, setCreateMarks] = useState<string>("100");
  const [createStartAt, setCreateStartAt] = useState<string>("");
  const [createEndAt, setCreateEndAt] = useState<string>("");
  const [createError, setCreateError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const isTeacherOrAdmin = hasPermission("assessment.create") || hasPermission("subject.create") || hasPermission("member.update");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAssessments();
      setAssessments(data);

      if (isTeacherOrAdmin) {
        try {
          const [wsData, subData] = await Promise.all([
            fetchWorkspaces().catch(() => []),
            fetchSubjects().catch(() => [])
          ]);
          setWorkspaces(wsData);
          setSubjects(subData);
        } catch {
          // Non-blocking
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load assessments.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [isTeacherOrAdmin]);

  useEffect(() => {
    if (permLoaded && orgId) {
      loadData();
    }
  }, [permLoaded, orgId, loadData]);

  // Handle Quick Lifecycle Action
  const handleAction = async (assessmentId: string, action: "publish" | "close" | "archive") => {
    try {
      if (action === "publish") {
        await publishAssessment(assessmentId);
      } else if (action === "close") {
        await closeAssessment(assessmentId);
      } else if (action === "archive") {
        if (!confirm("Are you sure you want to archive this assessment?")) return;
        await archiveAssessment(assessmentId);
      }
      await loadData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : `Failed to ${action} assessment.`);
    }
  };

  // Handle Create Assessment
  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError(null);

    if (!createSubjectId) {
      setCreateError("Please select a subject.");
      return;
    }
    if (!createTitle.trim()) {
      setCreateError("Title is required.");
      return;
    }
    const marksNum = parseFloat(createMarks);
    if (isNaN(marksNum) || marksNum <= 0) {
      setCreateError("Total marks must be greater than 0.");
      return;
    }
    const durationNum = createDuration ? parseInt(createDuration, 10) : null;
    if (durationNum !== null && (isNaN(durationNum) || durationNum <= 0)) {
      setCreateError("Duration must be a positive number of minutes.");
      return;
    }

    if (createStartAt && createEndAt) {
      if (new Date(createEndAt) <= new Date(createStartAt)) {
        setCreateError("End time must be after start time.");
        return;
      }
    }

    setCreating(true);
    try {
      await createAssessment({
        subject_id: createSubjectId,
        title: createTitle.trim(),
        description: createDesc.trim() || null,
        type: createType,
        total_marks: marksNum,
        duration_minutes: durationNum,
        start_at: createStartAt ? new Date(createStartAt).toISOString() : null,
        end_at: createEndAt ? new Date(createEndAt).toISOString() : null,
      });

      setCreateOpen(false);
      setCreateSubjectId("");
      setCreateTitle("");
      setCreateDesc("");
      setCreateDuration("");
      setCreateMarks("100");
      setCreateStartAt("");
      setCreateEndAt("");
      await loadData();
    } catch (err: unknown) {
      setCreateError(err instanceof Error ? err.message : "Failed to create assessment.");
    } finally {
      setCreating(false);
    }
  };

  // Filtered Assessments
  const filtered = useMemo(() => {
    return assessments.filter((a) => {
      // Status filter
      if (statusTab !== "all" && a.assessment_status !== statusTab) {
        return false;
      }
      // Type filter
      if (typeFilter !== "all" && a.assessment_type !== typeFilter) {
        return false;
      }
      // Search
      if (search.trim()) {
        const q = search.toLowerCase();
        const matchesTitle = a.assessment_title.toLowerCase().includes(q);
        const matchesDesc = a.assessment_description?.toLowerCase().includes(q) || false;
        const matchesSubj = a.subject_name?.toLowerCase().includes(q) || false;
        if (!matchesTitle && !matchesDesc && !matchesSubj) return false;
      }
      return true;
    });
  }, [assessments, statusTab, typeFilter, search]);

  const getStatusBadge = (status: AssessmentStatus) => {
    switch (status) {
      case "draft":
        return <Badge variant="outline" className="bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20">Draft</Badge>;
      case "published":
        return <Badge variant="outline" className="bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20">Published</Badge>;
      case "active":
        return <Badge variant="outline" className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20">Active</Badge>;
      case "closed":
        return <Badge variant="outline" className="bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/20">Closed</Badge>;
      case "archived":
        return <Badge variant="outline" className="bg-zinc-500/10 text-zinc-500 border-zinc-500/20">Archived</Badge>;
    }
  };

  const getTypeBadge = (type: AssessmentType) => {
    switch (type) {
      case "exam":
        return <span className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-md bg-purple-500/10 text-purple-600 dark:text-purple-400"><span className="material-symbols-outlined text-[14px]">school</span>Exam</span>;
      case "quiz":
        return <span className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-md bg-sky-500/10 text-sky-600 dark:text-sky-400"><span className="material-symbols-outlined text-[14px]">timer</span>Quiz</span>;
      case "practice":
        return <span className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"><span className="material-symbols-outlined text-[14px]">psychology</span>Practice</span>;
    }
  };

  if (permLoaded && !hasPermission("assessment.read")) {
    return <ForbiddenState message="You do not have permission to view assessments." />;
  }

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-[var(--on-surface)]">
            Assessments & Exams
          </h1>
          <p className="text-sm text-[var(--on-surface-variant)] mt-1">
            Manage quizzes, midterm exams, and practice tests across all subjects.
          </p>
        </div>
        {isTeacherOrAdmin && (
          <Button
            onClick={() => setCreateOpen(true)}
            className="flex items-center gap-2 shadow-sm font-medium"
            style={{ backgroundColor: "var(--primary)", color: "var(--on-primary)" }}
          >
            <span className="material-symbols-outlined text-[18px]">add</span>
            Create Assessment
          </Button>
        )}
      </div>

      {/* Control Bar: Tabs, Search & Filters */}
      <div className="flex flex-col md:flex-row gap-4 justify-between items-start md:items-center bg-[var(--surface-container-low)] p-3 rounded-2xl border border-[var(--outline-variant)]">
        {/* Status Tabs */}
        <div className="flex items-center gap-1 overflow-x-auto pb-1 md:pb-0 w-full md:w-auto">
          {["all", "active", "published", ...(isTeacherOrAdmin ? ["draft", "closed", "archived"] : ["closed"])].map((tab) => (
            <button
              key={tab}
              onClick={() => setStatusTab(tab)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold uppercase tracking-wider transition-all whitespace-nowrap ${
                statusTab === tab
                  ? "bg-[var(--primary)] text-[var(--on-primary)] shadow-sm"
                  : "text-[var(--on-surface-variant)] hover:bg-[var(--surface-container-high)]"
              }`}
            >
              {tab === "all" ? "All Status" : tab}
            </button>
          ))}
        </div>

        {/* Search and Type Filter */}
        <div className="flex items-center gap-3 w-full md:w-auto">
          <Select value={typeFilter} onValueChange={setTypeFilter}>
            <SelectTrigger className="w-[130px] h-9 text-xs">
              <SelectValue placeholder="All Types" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="quiz">Quizzes</SelectItem>
              <SelectItem value="exam">Exams</SelectItem>
              <SelectItem value="practice">Practice</SelectItem>
            </SelectContent>
          </Select>

          <div className="relative w-full md:w-64">
            <span className="material-symbols-outlined absolute left-3 top-2 text-[18px] text-[var(--on-surface-variant)]">
              search
            </span>
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search assessments..."
              className="pl-9 h-9 text-xs"
            />
          </div>
        </div>
      </div>

      {/* Assessment List */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-48 rounded-2xl bg-[var(--surface-container-lowest)] border border-[var(--outline-variant)] animate-pulse" />
          ))}
        </div>
      ) : error ? (
        <div className="p-8 text-center rounded-2xl border border-red-500/20 bg-red-500/5 text-red-600 dark:text-red-400">
          <p className="font-semibold text-sm">{error}</p>
          <Button onClick={loadData} variant="outline" size="sm" className="mt-3">
            Try Again
          </Button>
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 px-4 rounded-3xl border border-dashed border-[var(--outline-variant)] bg-[var(--surface-container-lowest)]">
          <span className="material-symbols-outlined text-[48px] text-[var(--on-surface-variant)] opacity-40 mb-3 block">
            quiz
          </span>
          <h3 className="text-base font-bold text-[var(--on-surface)]">No assessments found</h3>
          <p className="text-xs text-[var(--on-surface-variant)] mt-1 max-w-sm mx-auto">
            {search || statusTab !== "all" || typeFilter !== "all"
              ? "No assessments match your current filters. Try changing or clearing your filters."
              : "Get started by creating your first quiz, exam, or practice test."}
          </p>
          {isTeacherOrAdmin && !search && statusTab === "all" && (
            <Button
              onClick={() => setCreateOpen(true)}
              size="sm"
              className="mt-4"
              style={{ backgroundColor: "var(--primary)", color: "var(--on-primary)" }}
            >
              Create Assessment
            </Button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filtered.map((item) => (
            <div
              key={item.assessment_id}
              className="group flex flex-col justify-between p-5 rounded-2xl bg-[var(--surface-container-lowest)] border border-[var(--outline-variant)] hover:border-[var(--primary)] hover:shadow-md transition-all duration-200"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-3">
                  {getTypeBadge(item.assessment_type)}
                  {getStatusBadge(item.assessment_status)}
                </div>

                <Link
                  href={`/classroom/assessments/${item.assessment_id}`}
                  className="font-bold text-base text-[var(--on-surface)] group-hover:text-[var(--primary)] transition-colors line-clamp-1"
                >
                  {item.assessment_title}
                </Link>

                {item.subject_name && (
                  <p className="text-xs font-semibold text-[var(--primary)] mt-1 truncate">
                    {item.subject_name}
                    {item.workspace_name && (
                      <span className="text-[var(--on-surface-variant)] font-normal"> · {item.workspace_name}</span>
                    )}
                  </p>
                )}

                {item.assessment_description && (
                  <p className="text-xs text-[var(--on-surface-variant)] mt-2 line-clamp-2 leading-relaxed">
                    {item.assessment_description}
                  </p>
                )}

                <div className="grid grid-cols-2 gap-2 mt-4 pt-3 border-t border-[var(--outline-variant)] text-[11px] text-[var(--on-surface-variant)]">
                  <div className="flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[15px] opacity-70">timer</span>
                    <span>{item.assessment_duration_minutes ? `${item.assessment_duration_minutes} mins` : "Untimed"}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[15px] opacity-70">grade</span>
                    <span>{item.assessment_total_marks} Marks</span>
                  </div>
                </div>
              </div>

              {/* Card Footer Actions */}
              <div className="flex items-center justify-between gap-2 mt-4 pt-3 border-t border-[var(--outline-variant)]">
                <Link
                  href={`/classroom/assessments/${item.assessment_id}`}
                  className="text-xs font-semibold text-[var(--primary)] hover:underline flex items-center gap-1"
                >
                  View Details
                  <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
                </Link>

                {isTeacherOrAdmin && (
                  <div className="flex items-center gap-1.5">
                    {item.assessment_status === "draft" && (
                      <Button
                        onClick={() => handleAction(item.assessment_id, "publish")}
                        variant="outline"
                        size="sm"
                        className="h-7 text-[11px] px-2.5 text-blue-600 border-blue-500/30 hover:bg-blue-500/10"
                      >
                        Publish
                      </Button>
                    )}
                    {(item.assessment_status === "published" || item.assessment_status === "active") && (
                      <Button
                        onClick={() => handleAction(item.assessment_id, "close")}
                        variant="outline"
                        size="sm"
                        className="h-7 text-[11px] px-2.5 text-gray-600 border-gray-500/30 hover:bg-gray-500/10"
                      >
                        Close
                      </Button>
                    )}
                    {item.assessment_status !== "archived" && (
                      <button
                        onClick={() => handleAction(item.assessment_id, "archive")}
                        className="p-1 text-[var(--on-surface-variant)] hover:text-red-500 transition-colors"
                        title="Archive"
                      >
                        <span className="material-symbols-outlined text-[16px]">archive</span>
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Assessment Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Create Assessment</DialogTitle>
            <DialogDescription>
              Create a new quiz, exam, or practice test container for a subject.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleCreate} className="space-y-4">
            {createError && (
              <div className="p-3 text-xs rounded-xl bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20">
                {createError}
              </div>
            )}

            <div className="space-y-1.5">
              <Label htmlFor="subject">Subject *</Label>
              <Select value={createSubjectId} onValueChange={setCreateSubjectId}>
                <SelectTrigger id="subject" className="w-full">
                  <SelectValue placeholder="Select a subject..." />
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

            <div className="space-y-1.5">
              <Label htmlFor="title">Assessment Title *</Label>
              <Input
                id="title"
                value={createTitle}
                onChange={(e) => setCreateTitle(e.target.value)}
                placeholder="e.g. Midterm Physics Exam"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="type">Assessment Type</Label>
                <Select value={createType} onValueChange={(v) => setCreateType(v as AssessmentType)}>
                  <SelectTrigger id="type">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="quiz">Quiz</SelectItem>
                    <SelectItem value="exam">Exam</SelectItem>
                    <SelectItem value="practice">Practice</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="marks">Total Marks *</Label>
                <Input
                  id="marks"
                  type="number"
                  step="0.5"
                  min="1"
                  max="99999"
                  value={createMarks}
                  onChange={(e) => setCreateMarks(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="duration">Duration (Minutes)</Label>
              <Input
                id="duration"
                type="number"
                min="1"
                placeholder="e.g. 60 (optional for untimed)"
                value={createDuration}
                onChange={(e) => setCreateDuration(e.target.value)}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="start_at">Start Time (Optional)</Label>
                <Input
                  id="start_at"
                  type="datetime-local"
                  value={createStartAt}
                  onChange={(e) => setCreateStartAt(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="end_at">End Time (Optional)</Label>
                <Input
                  id="end_at"
                  type="datetime-local"
                  value={createEndAt}
                  onChange={(e) => setCreateEndAt(e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="description">Instructions / Description</Label>
              <Textarea
                id="description"
                rows={3}
                value={createDesc}
                onChange={(e) => setCreateDesc(e.target.value)}
                placeholder="Add special instructions, allowed materials, or syllabus topics..."
              />
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setCreateOpen(false)}>
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={creating}
                style={{ backgroundColor: "var(--primary)", color: "var(--on-primary)" }}
              >
                {creating ? "Creating..." : "Create Assessment"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
