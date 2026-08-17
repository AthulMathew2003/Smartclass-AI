"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  fetchAssignment,
  updateAssignment,
  publishAssignment,
  closeAssignment,
  archiveAssignment,
  fetchAssignmentAttachments,
  requestAssignmentAttachmentUploadUrl,
  confirmAssignmentAttachmentUpload,
  deleteAssignmentAttachment,
  getAssignmentAttachmentDownloadUrl,
  fetchStudentSubmission,
  fetchAssignmentSubmissions,
  requestSubmissionFileUploadUrl,
  submitAssignment,
  getSubmissionAttachmentDownloadUrl,
  gradeSubmission,
  returnSubmission,
  uploadFileToS3,
  Assignment,
  AssignmentAttachment,
  Submission,
} from "@/lib/assignments";
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
  DialogFooter,
} from "@/components/ui/dialog";

export default function AssignmentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const assignmentId = params?.assignmentId as string;

  const { hasPermission, isLoaded: permLoaded } = usePermissions();

  const [assignment, setAssignment] = useState<Assignment | null>(null);
  const [attachments, setAttachments] = useState<AssignmentAttachment[]>([]);
  const [studentSubmission, setStudentSubmission] = useState<Submission | null>(null);
  const [allSubmissions, setAllSubmissions] = useState<Submission[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Student upload state
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [uploadingProgress, setUploadingProgress] = useState<number | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Teacher attachment upload state
  const [teacherUploadFile, setTeacherUploadFile] = useState<File | null>(null);
  const [teacherUploading, setTeacherUploading] = useState(false);
  const [teacherUploadError, setTeacherUploadError] = useState<string | null>(null);

  // Teacher grading modal state
  const [selectedSubForGrade, setSelectedSubForGrade] = useState<Submission | null>(null);
  const [gradeScore, setGradeScore] = useState<string>("");
  const [gradeFeedback, setGradeFeedback] = useState<string>("");
  const [grading, setGrading] = useState(false);
  const [gradeError, setGradeError] = useState<string | null>(null);

  // Teacher edit assignment modal state
  const [editOpen, setEditOpen] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [editDue, setEditDue] = useState("");
  const [editing, setEditing] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  const isTeacherOrAdmin = hasPermission("assignment.update") || hasPermission("assignment.create") || hasPermission("member.update");

  const loadData = useCallback(async () => {
    if (!assignmentId) return;
    setLoading(true);
    setError(null);
    try {
      // 1. Fetch assignment details
      const assign = await fetchAssignment(assignmentId);
      setAssignment(assign);
      setEditTitle(assign.assignment_title);
      setEditDesc(assign.assignment_description || "");
      if (assign.assignment_due_at) {
        const d = new Date(assign.assignment_due_at);
        const pad = (n: number) => n.toString().padStart(2, "0");
        const formatted = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
        setEditDue(formatted);
      }

      // 2. Fetch teacher attachments
      const atts = await fetchAssignmentAttachments(assignmentId).catch(() => []);
      setAttachments(atts);

      // 3. Fetch submissions depending on role
      if (isTeacherOrAdmin) {
        const subs = await fetchAssignmentSubmissions(assignmentId).catch(() => []);
        setAllSubmissions(subs);
      } else {
        const mySub = await fetchStudentSubmission(assignmentId).catch(() => null);
        setStudentSubmission(mySub);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load assignment.");
    } finally {
      setLoading(false);
    }
  }, [assignmentId, isTeacherOrAdmin]);

  useEffect(() => {
    if (permLoaded && assignmentId) {
      loadData();
    }
  }, [permLoaded, assignmentId, loadData]);

  // ── Teacher Actions ─────────────────────────────────────────────

  const handlePublish = async () => {
    if (!assignment) return;
    try {
      await publishAssignment(assignment.assignment_id);
      await loadData();
    } catch (err: any) {
      alert(err?.message || "Failed to publish assignment.");
    }
  };

  const handleClose = async () => {
    if (!assignment) return;
    if (!confirm("Are you sure you want to close submissions for this assignment?")) return;
    try {
      await closeAssignment(assignment.assignment_id);
      await loadData();
    } catch (err: any) {
      alert(err?.message || "Failed to close assignment.");
    }
  };

  const handleArchive = async () => {
    if (!assignment) return;
    if (!confirm("Are you sure you want to archive (delete) this assignment?")) return;
    try {
      await archiveAssignment(assignment.assignment_id);
      router.push("/classroom/assignments");
    } catch (err: any) {
      alert(err?.message || "Failed to archive assignment.");
    }
  };

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assignment) return;
    if (!editTitle.trim()) {
      setEditError("Title cannot be empty.");
      return;
    }

    setEditing(true);
    setEditError(null);
    try {
      let isoDue: string | undefined = undefined;
      if (editDue) {
        isoDue = new Date(editDue).toISOString();
      }
      await updateAssignment(assignment.assignment_id, {
        title: editTitle.trim(),
        description: editDesc.trim() || undefined,
        due_at: isoDue,
      });
      setEditOpen(false);
      await loadData();
    } catch (err: any) {
      setEditError(err?.message || "Failed to update assignment.");
    } finally {
      setEditing(false);
    }
  };

  const handleTeacherUploadAttachment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assignment || !teacherUploadFile) return;

    setTeacherUploading(true);
    setTeacherUploadError(null);
    try {
      // 1. Request presigned upload URL
      const { upload_url, s3_key, attachment_id } = await requestAssignmentAttachmentUploadUrl(
        assignment.assignment_id,
        {
          filename: teacherUploadFile.name,
          content_type: teacherUploadFile.type || "application/octet-stream",
          file_size: teacherUploadFile.size,
        }
      );

      // 2. Direct S3 Upload
      await uploadFileToS3(upload_url, teacherUploadFile, teacherUploadFile.type || "application/octet-stream");

      // 3. Confirm attachment in backend DB
      await confirmAssignmentAttachmentUpload(assignment.assignment_id, {
        attachment_id,
        s3_key,
        original_filename: teacherUploadFile.name,
        content_type: teacherUploadFile.type || "application/octet-stream",
        file_size: teacherUploadFile.size,
      });

      setTeacherUploadFile(null);
      await loadData();
    } catch (err: any) {
      setTeacherUploadError(err?.message || "Failed to upload attachment.");
    } finally {
      setTeacherUploading(false);
    }
  };

  const handleDeleteAttachment = async (attachmentId: string) => {
    if (!assignment) return;
    if (!confirm("Are you sure you want to remove this attachment?")) return;
    try {
      await deleteAssignmentAttachment(assignment.assignment_id, attachmentId);
      await loadData();
    } catch (err: any) {
      alert(err?.message || "Failed to delete attachment.");
    }
  };

  const handleDownloadTeacherAttachment = async (attachmentId: string) => {
    if (!assignment) return;
    try {
      const res = await getAssignmentAttachmentDownloadUrl(assignment.assignment_id, attachmentId);
      window.open(res.download_url, "_blank");
    } catch (err: any) {
      alert(err?.message || "Failed to generate download link.");
    }
  };

  // ── Student Submission Actions ──────────────────────────────────

  const handleStudentSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assignment) return;

    setSubmitting(true);
    setSubmitError(null);
    setUploadingProgress(0);

    try {
      const confirmedFiles: Array<{
        attachment_id: string;
        s3_key: string;
        original_filename: string;
        content_type: string;
        file_size: number;
      }> = [];

      // Upload each file to S3 via presigned URL
      for (let i = 0; i < uploadFiles.length; i++) {
        const file = uploadFiles[i];
        const contentType = file.type || "application/octet-stream";

        // 1. Request presigned upload URL
        const presigned = await requestSubmissionFileUploadUrl(assignment.assignment_id, {
          filename: file.name,
          content_type: contentType,
          file_size: file.size,
        });

        // 2. Direct S3 Upload
        await uploadFileToS3(presigned.upload_url, file, contentType, (pct) => {
          const overallProgress = Math.round(((i + pct / 100) / uploadFiles.length) * 100);
          setUploadingProgress(overallProgress);
        });

        confirmedFiles.push({
          attachment_id: presigned.attachment_id,
          s3_key: presigned.s3_key,
          original_filename: file.name,
          content_type: contentType,
          file_size: file.size,
        });
      }

      // 3. Finalize student submission in DB
      await submitAssignment(assignment.assignment_id, {
        files: confirmedFiles.length > 0 ? confirmedFiles : undefined,
      });

      setUploadFiles([]);
      setUploadingProgress(null);
      await loadData();
    } catch (err: any) {
      setSubmitError(err?.message || "Submission failed. Please check file format and try again.");
    } finally {
      setSubmitting(false);
      setUploadingProgress(null);
    }
  };

  const handleDownloadStudentAttachment = async (attachmentId: string) => {
    if (!assignment) return;
    try {
      const res = await getSubmissionAttachmentDownloadUrl(assignment.assignment_id, attachmentId);
      window.open(res.download_url, "_blank");
    } catch (err: any) {
      alert(err?.message || "Failed to download submission attachment.");
    }
  };

  // ── Teacher Grading Actions ─────────────────────────────────────

  const handleGradeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assignment || !selectedSubForGrade) return;

    const numGrade = parseFloat(gradeScore);
    if (isNaN(numGrade) || numGrade < 0 || numGrade > 100) {
      setGradeError("Grade must be a number between 0 and 100.");
      return;
    }

    setGrading(true);
    setGradeError(null);
    try {
      await gradeSubmission(assignment.assignment_id, selectedSubForGrade.submission_id, {
        grade: numGrade,
        feedback: gradeFeedback.trim() || undefined,
      });
      setSelectedSubForGrade(null);
      await loadData();
    } catch (err: any) {
      setGradeError(err?.message || "Failed to save grade.");
    } finally {
      setGrading(false);
    }
  };

  const handleReturnSubmission = async () => {
    if (!assignment || !selectedSubForGrade) return;
    setGrading(true);
    setGradeError(null);
    try {
      await returnSubmission(assignment.assignment_id, selectedSubForGrade.submission_id, {
        feedback: gradeFeedback.trim() || undefined,
      });
      setSelectedSubForGrade(null);
      await loadData();
    } catch (err: any) {
      setGradeError(err?.message || "Failed to return submission.");
    } finally {
      setGrading(false);
    }
  };

  if (permLoaded && !hasPermission("assignment.read")) {
    return <ForbiddenState message="You do not have permission to view this assignment." />;
  }

  if (loading) {
    return (
      <div className="min-h-screen p-6 md:p-10 flex items-center justify-center">
        <div className="text-center space-y-3">
          <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p className="text-sm font-semibold text-muted-foreground">Loading assignment details...</p>
        </div>
      </div>
    );
  }

  if (error || !assignment) {
    return (
      <div className="min-h-screen p-6 md:p-10">
        <div className="max-w-4xl mx-auto p-8 text-center rounded-2xl bg-destructive/10 border border-destructive/20 text-destructive space-y-4">
          <span className="material-symbols-outlined text-[40px]">assignment_late</span>
          <h2 className="text-xl font-bold">Assignment Not Found</h2>
          <p className="text-sm text-muted-foreground">{error || "The requested assignment could not be found."}</p>
          <Link href="/classroom/assignments">
            <Button variant="outline" className="mt-2 font-bold cursor-pointer">
              Back to Assignments
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  const dueDate = assignment.assignment_due_at ? new Date(assignment.assignment_due_at) : null;
  const isPast = dueDate ? new Date() > dueDate : false;
  const isClosed = assignment.assignment_status === "closed" || assignment.assignment_status === "archived";

  return (
    <div className="min-h-screen p-6 md:p-10 space-y-8 max-w-7xl mx-auto" style={{ backgroundColor: "var(--surface)" }}>
      {/* Breadcrumb Navigation */}
      <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground">
        <Link href="/classroom/assignments" className="hover:text-primary transition-colors">
          Assignments
        </Link>
        <span>/</span>
        <span className="text-foreground">{assignment.subject_name || "Subject"}</span>
        <span>/</span>
        <span className="text-foreground font-bold truncate max-w-xs">{assignment.assignment_title}</span>
      </div>

      {/* Header Card */}
      <div className="bg-card border rounded-3xl p-6 md:p-8 shadow-sm space-y-6">
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge
                variant={
                  assignment.assignment_status === "published"
                    ? "default"
                    : assignment.assignment_status === "closed"
                    ? "secondary"
                    : "outline"
                }
                className="capitalize text-xs font-bold"
              >
                {assignment.assignment_status}
              </Badge>
              {dueDate && (
                <span
                  className={`inline-flex items-center gap-1 text-xs font-bold px-2.5 py-0.5 rounded-full ${
                    isPast
                      ? "bg-destructive/15 text-destructive border border-destructive/20"
                      : "bg-primary/10 text-primary border border-primary/20"
                  }`}
                >
                  <span className="material-symbols-outlined text-[14px]">event</span>
                  {isPast ? "Past Due: " : "Due: "}
                  {dueDate.toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              )}
            </div>

            <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight" style={{ color: "var(--on-surface)" }}>
              {assignment.assignment_title}
            </h1>
          </div>

          {/* Teacher Toolbar */}
          {isTeacherOrAdmin && (
            <div className="flex items-center gap-2 flex-wrap shrink-0">
              {assignment.assignment_status === "draft" && (
                <Button onClick={handlePublish} className="font-bold gap-1.5 cursor-pointer">
                  <span className="material-symbols-outlined text-[18px]">publish</span>
                  Publish
                </Button>
              )}
              {assignment.assignment_status === "published" && (
                <Button onClick={handleClose} variant="secondary" className="font-bold gap-1.5 cursor-pointer">
                  <span className="material-symbols-outlined text-[18px]">lock</span>
                  Close Submissions
                </Button>
              )}
              {!isClosed && (
                <Button onClick={() => setEditOpen(true)} variant="outline" className="font-bold gap-1.5 cursor-pointer">
                  <span className="material-symbols-outlined text-[18px]">edit</span>
                  Edit
                </Button>
              )}
              <Button onClick={handleArchive} variant="destructive" className="font-bold gap-1.5 cursor-pointer">
                <span className="material-symbols-outlined text-[18px]">delete</span>
                Archive
              </Button>
            </div>
          )}
        </div>

        {/* Instructions / Description */}
        {assignment.assignment_description && (
          <div className="pt-4 border-t border-border/60">
            <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">Instructions</h3>
            <p className="text-sm leading-relaxed whitespace-pre-line text-foreground/90">
              {assignment.assignment_description}
            </p>
          </div>
        )}

        {/* Teacher Resources & Attachments */}
        <div className="pt-4 border-t border-border/60 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Assignment Attachments ({attachments.length})
            </h3>
          </div>

          {attachments.length === 0 ? (
            <p className="text-xs text-muted-foreground italic">No reference attachments uploaded.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {attachments.map((att) => (
                <div
                  key={att.attachment_id}
                  className="flex items-center justify-between p-3 rounded-xl border bg-background/50 hover:bg-muted/50 transition-colors text-xs"
                >
                  <div className="flex items-center gap-2 overflow-hidden">
                    <span className="material-symbols-outlined text-primary text-[20px] shrink-0">
                      description
                    </span>
                    <div className="truncate">
                      <p className="font-bold truncate">{att.original_filename}</p>
                      <p className="text-[10px] text-muted-foreground">
                        {(att.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-1 shrink-0 ml-2">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDownloadTeacherAttachment(att.attachment_id)}
                      title="Download file"
                      className="h-8 w-8 p-0 cursor-pointer"
                    >
                      <span className="material-symbols-outlined text-[18px]">download</span>
                    </Button>
                    {isTeacherOrAdmin && !isClosed && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDeleteAttachment(att.attachment_id)}
                        title="Delete attachment"
                        className="h-8 w-8 p-0 text-destructive hover:text-destructive cursor-pointer"
                      >
                        <span className="material-symbols-outlined text-[18px]">delete</span>
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Teacher Upload Attachment Section */}
          {isTeacherOrAdmin && !isClosed && (
            <form onSubmit={handleTeacherUploadAttachment} className="flex items-center gap-3 pt-2">
              <Input
                type="file"
                onChange={(e) => setTeacherUploadFile(e.target.files?.[0] || null)}
                className="max-w-xs text-xs file:cursor-pointer"
              />
              <Button
                type="submit"
                size="sm"
                variant="outline"
                disabled={!teacherUploadFile || teacherUploading}
                className="font-bold cursor-pointer"
              >
                {teacherUploading ? "Uploading..." : "Attach Reference File"}
              </Button>
              {teacherUploadError && (
                <span className="text-xs text-destructive font-semibold">{teacherUploadError}</span>
              )}
            </form>
          )}
        </div>
      </div>

      {/* ── Main Role-Specific Section ── */}
      {isTeacherOrAdmin ? (
        /* Teacher Submissions Management Table */
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold">Student Submissions</h2>
              <p className="text-xs text-muted-foreground">
                Review, grade, and return student assignments across all submission attempts.
              </p>
            </div>
            <Badge variant="outline" className="font-mono text-xs">
              {allSubmissions.length} Total Submissions
            </Badge>
          </div>

          <div className="bg-card border rounded-2xl overflow-hidden shadow-sm">
            {allSubmissions.length === 0 ? (
              <div className="p-12 text-center space-y-2">
                <span className="material-symbols-outlined text-[40px] text-muted-foreground">inbox</span>
                <h4 className="text-base font-bold">No submissions yet</h4>
                <p className="text-xs text-muted-foreground">
                  Students enrolled in this workspace will appear here when they submit work.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-muted/50 border-b font-bold text-muted-foreground uppercase text-[10px] tracking-wider">
                    <tr>
                      <th className="p-4">Student</th>
                      <th className="p-4">Status</th>
                      <th className="p-4">Submitted At</th>
                      <th className="p-4">Grade</th>
                      <th className="p-4 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {allSubmissions.map((sub) => {
                      const subDate = sub.submission_submitted_at ? new Date(sub.submission_submitted_at) : null;
                      return (
                        <tr key={sub.submission_id} className="hover:bg-muted/20 transition-colors">
                          <td className="p-4">
                            <p className="font-bold text-foreground">{sub.student_name || "Student"}</p>
                            <p className="text-[10px] text-muted-foreground">{sub.student_email}</p>
                          </td>
                          <td className="p-4">
                            <Badge
                              className={`capitalize text-[10px] font-bold ${
                                sub.submission_status === "graded"
                                  ? "bg-emerald-500/15 text-emerald-600 border-emerald-500/20"
                                  : sub.submission_status === "late"
                                  ? "bg-amber-500/15 text-amber-600 border-amber-500/20"
                                  : "bg-blue-500/15 text-blue-600 border-blue-500/20"
                              }`}
                            >
                              {sub.submission_status}
                            </Badge>
                          </td>
                          <td className="p-4 text-muted-foreground">
                            {subDate
                              ? subDate.toLocaleDateString("en-US", {
                                  month: "short",
                                  day: "numeric",
                                  hour: "2-digit",
                                  minute: "2-digit",
                                })
                              : "—"}
                          </td>
                          <td className="p-4 font-mono font-bold">
                            {sub.submission_grade !== null && sub.submission_grade !== undefined
                              ? `${sub.submission_grade} / 100`
                              : "—"}
                          </td>
                          <td className="p-4 text-right">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => {
                                setSelectedSubForGrade(sub);
                                setGradeScore(sub.submission_grade !== null && sub.submission_grade !== undefined ? String(sub.submission_grade) : "");
                                setGradeFeedback(sub.submission_feedback || "");
                                setGradeError(null);
                              }}
                              className="font-bold text-xs gap-1 cursor-pointer"
                            >
                              <span className="material-symbols-outlined text-[16px]">edit_note</span>
                              {sub.submission_status === "graded" ? "Edit Grade" : "Grade"}
                            </Button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Student Submission Box */
        <div className="max-w-4xl mx-auto space-y-6">
          <div className="bg-card border rounded-3xl p-6 md:p-8 shadow-sm space-y-6">
            <div className="flex items-center justify-between border-b pb-4">
              <div>
                <h2 className="text-xl font-bold">Your Submission</h2>
                <p className="text-xs text-muted-foreground">
                  Upload and submit your assignment files directly for evaluation.
                </p>
              </div>

              {studentSubmission && (
                <Badge
                  className={`capitalize text-xs font-bold ${
                    studentSubmission.submission_status === "graded"
                      ? "bg-emerald-500/15 text-emerald-600 border-emerald-500/20"
                      : studentSubmission.submission_status === "late"
                      ? "bg-amber-500/15 text-amber-600 border-amber-500/20"
                      : "bg-blue-500/15 text-blue-600 border-blue-500/20"
                  }`}
                >
                  {studentSubmission.submission_status}
                </Badge>
              )}
            </div>

            {/* Feedback Alert if Graded */}
            {studentSubmission?.submission_status === "graded" && (
              <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-emerald-600 uppercase tracking-wider flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[18px]">verified</span>
                    Teacher Evaluation & Score
                  </span>
                  <span className="text-base font-extrabold text-emerald-700 font-mono">
                    {studentSubmission.submission_grade} / 100
                  </span>
                </div>
                {studentSubmission.submission_feedback && (
                  <p className="text-xs leading-relaxed text-emerald-900 dark:text-emerald-200">
                    &quot;{studentSubmission.submission_feedback}&quot;
                  </p>
                )}
              </div>
            )}

            {/* Current Submitted Files List */}
            {studentSubmission && studentSubmission.attachments && studentSubmission.attachments.length > 0 && (
              <div className="space-y-3 p-4 rounded-2xl border bg-muted/20">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-foreground flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[18px] text-primary">task</span>
                    Current Submitted Files ({studentSubmission.attachments.length})
                  </span>
                  <span className="text-[11px] text-muted-foreground">
                    Submitted: {studentSubmission.submission_submitted_at ? new Date(studentSubmission.submission_submitted_at).toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "—"}
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {studentSubmission.attachments.map((att) => (
                    <button
                      key={att.attachment_id}
                      type="button"
                      onClick={() => handleDownloadStudentAttachment(att.attachment_id)}
                      className="flex items-center justify-between p-3 rounded-xl border bg-card hover:bg-muted/50 text-left text-xs transition-colors cursor-pointer shadow-xs"
                    >
                      <div className="truncate mr-2">
                        <p className="font-semibold truncate">{att.original_filename}</p>
                        <p className="text-[10px] text-muted-foreground font-mono">
                          {(att.size / 1024 / 1024).toFixed(2)} MB
                        </p>
                      </div>
                      <span className="material-symbols-outlined text-[18px] text-primary shrink-0">
                        download
                      </span>
                    </button>
                  ))}
                </div>

                <p className="text-[11px] text-muted-foreground pt-1">
                  Need to update your work? Uploading new files below will replace all previous submission files.
                </p>
              </div>
            )}

            {/* Upload Dropzone & Submission Form */}
            {!isClosed && (
              <form onSubmit={handleStudentSubmit} className="space-y-4">
                {submitError && (
                  <div className="p-3 rounded-xl bg-destructive/15 text-destructive text-xs font-semibold">
                    {submitError}
                  </div>
                )}

                <div className="space-y-2">
                  <Label className="text-xs font-bold">
                    {studentSubmission ? "Upload New Files to Replace Submission" : "Select Submission Files"}
                  </Label>
                  <div className="border-2 border-dashed rounded-2xl p-6 text-center hover:border-primary transition-colors cursor-pointer bg-background/50">
                    <input
                      type="file"
                      multiple
                      onChange={(e) => {
                        if (e.target.files) {
                          setUploadFiles(Array.from(e.target.files));
                        }
                      }}
                      className="hidden"
                      id="studentFilePicker"
                    />
                    <label htmlFor="studentFilePicker" className="cursor-pointer block space-y-2">
                      <span className="material-symbols-outlined text-[36px] text-primary">
                        cloud_upload
                      </span>
                      <p className="text-xs font-bold">Click to choose files or drag &amp; drop</p>
                      <p className="text-[11px] text-muted-foreground">
                        PDF, Word (DOCX), PowerPoint (PPTX), Excel (XLSX), Plain Text, or Images (Max 25MB each, max 10 files)
                      </p>
                    </label>
                  </div>
                </div>

                {/* Selected files preview */}
                {uploadFiles.length > 0 && (
                  <div className="space-y-2">
                    <span className="text-xs font-bold text-muted-foreground">Selected Replacement Files ({uploadFiles.length}):</span>
                    <div className="space-y-1.5">
                      {uploadFiles.map((f, i) => (
                        <div
                          key={i}
                          className="flex items-center justify-between p-2.5 rounded-xl border bg-muted/30 text-xs"
                        >
                          <span className="font-semibold truncate">{f.name}</span>
                          <span className="text-muted-foreground font-mono text-[10px]">
                            {(f.size / 1024 / 1024).toFixed(2)} MB
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Upload Progress Bar */}
                {uploadingProgress !== null && (
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs font-semibold">
                      <span>Uploading files to storage...</span>
                      <span>{uploadingProgress}%</span>
                    </div>
                    <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary transition-all duration-200"
                        style={{ width: `${uploadingProgress}%` }}
                      ></div>
                    </div>
                  </div>
                )}

                <Button
                  type="submit"
                  disabled={submitting || (uploadFiles.length === 0 && !studentSubmission)}
                  className="w-full font-bold shadow-md cursor-pointer text-xs py-5"
                >
                  {submitting ? (
                    "Submitting..."
                  ) : studentSubmission ? (
                    "Replace & Resubmit Assignment"
                  ) : (
                    "Submit Assignment"
                  )}
                </Button>
              </form>
            )}

            {isClosed && (
              <div className="p-4 text-center rounded-xl bg-muted/50 border text-xs text-muted-foreground">
                Submissions are closed for this assignment.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Teacher Grading Dialog */}
      <Dialog open={!!selectedSubForGrade} onOpenChange={(open) => !open && setSelectedSubForGrade(null)}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Grade Student Submission</DialogTitle>
            <DialogDescription>
              Review files submitted by {selectedSubForGrade?.student_name}.
            </DialogDescription>
          </DialogHeader>

          {selectedSubForGrade && (
            <div className="space-y-5 py-2">
              {gradeError && (
                <div className="p-3 rounded-lg bg-destructive/15 text-destructive text-xs font-semibold">
                  {gradeError}
                </div>
              )}

              {/* Submitted Files */}
              <div className="space-y-2">
                <Label className="text-xs font-bold">
                  Submitted Files ({selectedSubForGrade.attachments?.length || 0}):
                </Label>
                {(!selectedSubForGrade.attachments || selectedSubForGrade.attachments.length === 0) ? (
                  <p className="text-xs text-muted-foreground">No files attached to this submission.</p>
                ) : (
                  selectedSubForGrade.attachments.map((att) => (
                    <div
                      key={att.attachment_id}
                      className="flex items-center justify-between p-3 rounded-xl border bg-muted/40 text-xs"
                    >
                      <div className="truncate mr-2">
                        <span className="font-semibold truncate block">{att.original_filename}</span>
                        <span className="text-[10px] text-muted-foreground font-mono">
                          {(att.size / 1024 / 1024).toFixed(2)} MB
                        </span>
                      </div>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDownloadStudentAttachment(att.attachment_id)}
                        className="h-8 gap-1 font-bold text-primary cursor-pointer shrink-0"
                      >
                        <span className="material-symbols-outlined text-[16px]">download</span>
                        Download
                      </Button>
                    </div>
                  ))
                )}
              </div>

              {/* Grade Input Form */}
              <form onSubmit={handleGradeSubmit} className="space-y-4">
                <div className="space-y-1.5">
                  <Label htmlFor="gradeScoreInput">Grade Score (0 - 100) *</Label>
                  <Input
                    id="gradeScoreInput"
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    placeholder="e.g. 95.0"
                    value={gradeScore}
                    onChange={(e) => setGradeScore(e.target.value)}
                    required
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="gradeFeedbackInput">Feedback / Comments</Label>
                  <Textarea
                    id="gradeFeedbackInput"
                    rows={4}
                    placeholder="Provide constructive feedback on what the student did well and what needs improvement..."
                    value={gradeFeedback}
                    onChange={(e) => setGradeFeedback(e.target.value)}
                  />
                </div>

                <DialogFooter className="gap-2 pt-2">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleReturnSubmission}
                    disabled={grading}
                    className="cursor-pointer"
                  >
                    Return Submission
                  </Button>
                  <Button type="submit" disabled={grading} className="font-bold cursor-pointer">
                    {grading ? "Saving..." : "Submit Grade"}
                  </Button>
                </DialogFooter>
              </form>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Edit Assignment Dialog */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Edit Assignment</DialogTitle>
            <DialogDescription>Update assignment title, instructions, and due date.</DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSaveEdit} className="space-y-4 py-2">
            {editError && (
              <div className="p-3 rounded-lg bg-destructive/15 text-destructive text-xs font-semibold">
                {editError}
              </div>
            )}

            <div className="space-y-1.5">
              <Label htmlFor="editTitleInput">Title *</Label>
              <Input
                id="editTitleInput"
                value={editTitle}
                maxLength={255}
                onChange={(e) => setEditTitle(e.target.value)}
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="editDescInput">Instructions / Description</Label>
              <Textarea
                id="editDescInput"
                rows={4}
                value={editDesc}
                onChange={(e) => setEditDesc(e.target.value)}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="editDueInput">Due Date &amp; Time</Label>
              <Input
                id="editDueInput"
                type="datetime-local"
                value={editDue}
                onChange={(e) => setEditDue(e.target.value)}
              />
            </div>

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={() => setEditOpen(false)} disabled={editing}>
                Cancel
              </Button>
              <Button type="submit" disabled={editing} className="font-bold">
                {editing ? "Saving..." : "Save Changes"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
