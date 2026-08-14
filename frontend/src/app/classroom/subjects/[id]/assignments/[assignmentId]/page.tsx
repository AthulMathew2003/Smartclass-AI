"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
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
  getAssignmentAttachmentDownloadUrl,
  deleteAssignmentAttachment,
  Assignment,
  AssignmentStatus,
  AssignmentAttachment,
} from "@/lib/assignments";
import { fetchSubject, Subject } from "@/lib/subjects";
import { usePermissions } from "@/lib/permissions";
import ForbiddenState from "../../../../components/ForbiddenState";
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

const ALLOWED_MIME_TYPES = [
  "application/pdf",
  "image/jpeg",
  "image/png",
  "image/webp",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/vnd.ms-excel",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
];
const MAX_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB

export default function AssignmentDetailPage() {
  const { id: subjectId, assignmentId } = useParams() as {
    id: string;
    assignmentId: string;
  };
  const searchParams = useSearchParams();
  const workspaceIdFromQuery = searchParams.get("workspace_id");
  const router = useRouter();

  const { hasPermission, isLoaded: permLoaded, orgId } = usePermissions();

  const [subject, setSubject] = useState<Subject | null>(null);
  const [assignment, setAssignment] = useState<Assignment | null>(null);
  const [attachments, setAttachments] = useState<AssignmentAttachment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isForbidden, setIsForbidden] = useState(false);

  // Edit Modal State
  const [editOpen, setEditDialogOpen] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editDueAt, setEditDueAt] = useState("");
  const [editError, setEditError] = useState<string | null>(null);

  // Archive Confirm Modal State
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [archiveError, setArchiveError] = useState<string | null>(null);

  // Attachment Upload Modal State
  const [uploadOpen, setUploadOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Delete Attachment Modal State
  const [attachmentToDelete, setAttachmentToDelete] = useState<AssignmentAttachment | null>(null);
  const [deleteAttachmentError, setDeleteAttachmentError] = useState<string | null>(null);

  const [submitting, setSubmitting] = useState(false);
  const [actionMessage, setActionMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  const canUpdate = hasPermission("assignment.update");
  const canDelete = hasPermission("assignment.delete");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    setIsForbidden(false);

    try {
      if (workspaceIdFromQuery) {
        try {
          const subjData = await fetchSubject(subjectId, workspaceIdFromQuery);
          setSubject(subjData);
        } catch {
          // Graceful fallback
        }
      }

      const assignData = await fetchAssignment(assignmentId, subjectId);
      setAssignment(assignData);

      try {
        const attList = await fetchAssignmentAttachments(assignmentId, subjectId);
        setAttachments(attList);
      } catch {
        // Attachments fetch fails gracefully if not authorized or empty
      }
    } catch (err: any) {
      const msg = err.message || "Failed to load assignment.";
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
  }, [assignmentId, subjectId, workspaceIdFromQuery]);

  useEffect(() => {
    if (permLoaded && hasPermission("assignment.read")) {
      loadData();
    }
  }, [permLoaded, orgId, loadData, hasPermission]);

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setEditError(null);

    if (!editTitle.trim()) {
      setEditError("Title is required.");
      return;
    }

    setSubmitting(true);
    try {
      const formattedDue = editDueAt ? new Date(editDueAt).toISOString() : undefined;
      const updated = await updateAssignment(assignmentId, subjectId, {
        title: editTitle.trim(),
        description: editDescription.trim() || undefined,
        due_at: formattedDue,
      });
      setAssignment(updated);
      setEditDialogOpen(false);
      setActionMessage({ type: "success", text: "Assignment updated successfully." });
    } catch (err: any) {
      setEditError(err.message || "Failed to update assignment.");
    } finally {
      setSubmitting(false);
    }
  };

  const handlePublish = async () => {
    if (!assignment) return;
    setSubmitting(true);
    setActionMessage(null);
    try {
      const updated = await publishAssignment(assignment.assignment_id, subjectId);
      setAssignment(updated);
      setActionMessage({ type: "success", text: "Assignment published! Students can now view this assignment." });
    } catch (err: any) {
      setActionMessage({ type: "error", text: err.message || "Failed to publish assignment." });
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = async () => {
    if (!assignment) return;
    setSubmitting(true);
    setActionMessage(null);
    try {
      const updated = await closeAssignment(assignment.assignment_id, subjectId);
      setAssignment(updated);
      setActionMessage({ type: "success", text: "Assignment closed for submissions." });
    } catch (err: any) {
      setActionMessage({ type: "error", text: err.message || "Failed to close assignment." });
    } finally {
      setSubmitting(false);
    }
  };

  const handleArchive = async () => {
    if (!assignment) return;
    setSubmitting(true);
    setArchiveError(null);
    try {
      const updated = await archiveAssignment(assignment.assignment_id, subjectId);
      setAssignment(updated);
      setArchiveOpen(false);
      setActionMessage({ type: "success", text: "Assignment archived." });
    } catch (err: any) {
      setArchiveError(err.message || "Failed to archive assignment.");
    } finally {
      setSubmitting(false);
    }
  };

  const openEditModal = () => {
    if (!assignment) return;
    setEditTitle(assignment.assignment_title);
    setEditDescription(assignment.assignment_description || "");
    if (assignment.assignment_due_at) {
      const date = new Date(assignment.assignment_due_at);
      const localIso = new Date(date.getTime() - date.getTimezoneOffset() * 60000)
        .toISOString()
        .slice(0, 16);
      setEditDueAt(localIso);
    } else {
      setEditDueAt("");
    }
    setEditError(null);
    setEditDialogOpen(true);
  };

  // ── Attachment Upload Handlers ─────────────────────────────────

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setUploadError(null);
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.size > MAX_ATTACHMENT_SIZE_BYTES) {
        setUploadError("File size exceeds the 10 MB limit.");
        setSelectedFile(null);
        return;
      }
      if (!ALLOWED_MIME_TYPES.includes(file.type)) {
        setUploadError("File type is not supported. Please choose a PDF, Word document, Excel spreadsheet, or image.");
        setSelectedFile(null);
        return;
      }
      setSelectedFile(file);
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setUploadError("Please select a file to upload.");
      return;
    }

    setUploading(true);
    setUploadError(null);
    setUploadProgress(10);

    try {
      // 1. Request presigned upload URL
      const { attachment_id, s3_key, upload_url } = await requestAssignmentAttachmentUploadUrl(
        assignmentId,
        subjectId,
        {
          filename: selectedFile.name,
          content_type: selectedFile.type,
          file_size: selectedFile.size,
        }
      );

      setUploadProgress(40);

      // 2. Direct browser upload to S3 using presigned PUT URL
      const s3Response = await fetch(upload_url, {
        method: "PUT",
        headers: {
          "Content-Type": selectedFile.type,
        },
        body: selectedFile,
      });

      if (!s3Response.ok) {
        throw new Error("Failed to upload file directly to storage.");
      }

      setUploadProgress(80);

      // 3. Confirm upload with backend
      await confirmAssignmentAttachmentUpload(assignmentId, subjectId, {
        attachment_id,
        s3_key,
        original_filename: selectedFile.name,
        content_type: selectedFile.type,
        file_size: selectedFile.size,
      });

      setUploadProgress(100);

      // 4. Refresh attachment list
      const updatedList = await fetchAssignmentAttachments(assignmentId, subjectId);
      setAttachments(updatedList);

      setUploadOpen(false);
      setSelectedFile(null);
      setActionMessage({ type: "success", text: "Attachment uploaded successfully." });
    } catch (err: any) {
      setUploadError(err.message || "Failed to upload attachment.");
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const handleDownloadAttachment = async (attachment: AssignmentAttachment) => {
    try {
      const { download_url } = await getAssignmentAttachmentDownloadUrl(
        assignmentId,
        attachment.attachment_id,
        subjectId
      );
      window.open(download_url, "_blank", "noopener,noreferrer");
    } catch (err: any) {
      setActionMessage({
        type: "error",
        text: err.message || "Failed to generate download link.",
      });
    }
  };

  const handleDeleteAttachmentSubmit = async () => {
    if (!attachmentToDelete) return;
    setSubmitting(true);
    setDeleteAttachmentError(null);

    try {
      await deleteAssignmentAttachment(
        assignmentId,
        attachmentToDelete.attachment_id,
        subjectId
      );
      setAttachments((prev) =>
        prev.filter((a) => a.attachment_id !== attachmentToDelete.attachment_id)
      );
      setAttachmentToDelete(null);
      setActionMessage({ type: "success", text: "Attachment deleted." });
    } catch (err: any) {
      setDeleteAttachmentError(err.message || "Failed to delete attachment.");
    } finally {
      setSubmitting(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getFileIcon = (contentType: string) => {
    if (contentType.includes("pdf")) return "picture_as_pdf";
    if (contentType.includes("image")) return "image";
    if (contentType.includes("spreadsheet") || contentType.includes("excel"))
      return "table_chart";
    if (contentType.includes("word") || contentType.includes("document"))
      return "description";
    return "attach_file";
  };

  if (!permLoaded || loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="flex items-center gap-3 text-sm font-semibold text-[var(--on-surface-variant)]">
          <div className="w-6 h-6 border-2 border-t-transparent border-[var(--primary)] rounded-full animate-spin" />
          {loading ? "Loading assignment..." : "Checking permissions..."}
        </div>
      </div>
    );
  }

  if (!hasPermission("assignment.read") || isForbidden) {
    return (
      <ForbiddenState message="You do not have permission to view this assignment." />
    );
  }

  if (error || !assignment) {
    return (
      <div className="p-6 max-w-4xl mx-auto space-y-4">
        <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/40 text-red-600 dark:text-red-400 text-sm border border-red-200 dark:border-red-800">
          {error || "Assignment not found."}
        </div>
        <Button
          variant="outline"
          onClick={() =>
            router.push(
              workspaceIdFromQuery
                ? `/classroom/subjects/${subjectId}/assignments?workspace_id=${workspaceIdFromQuery}`
                : `/classroom/subjects/${subjectId}/assignments`
            )
          }
        >
          &larr; Back to Assignments
        </Button>
      </div>
    );
  }

  const isArchived = assignment.assignment_status === "archived";
  const isDraft = assignment.assignment_status === "draft";
  const isPublished = assignment.assignment_status === "published";
  const isClosed = assignment.assignment_status === "closed";
  const canManageAttachments = canUpdate && !isArchived && !isClosed;

  const getStatusBadge = (status: AssignmentStatus) => {
    switch (status) {
      case "draft":
        return (
          <Badge
            variant="secondary"
            className="bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-700 capitalize font-semibold px-3 py-1 text-xs"
          >
            Draft
          </Badge>
        );
      case "published":
        return (
          <Badge className="bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800 capitalize font-semibold px-3 py-1 text-xs">
            Published
          </Badge>
        );
      case "closed":
        return (
          <Badge className="bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border border-amber-300 dark:border-amber-800 capitalize font-semibold px-3 py-1 text-xs">
            Closed
          </Badge>
        );
      case "archived":
        return (
          <Badge
            variant="outline"
            className="bg-zinc-100 dark:bg-zinc-800 text-zinc-500 capitalize font-semibold px-3 py-1 text-xs"
          >
            Archived
          </Badge>
        );
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  const listUrl = workspaceIdFromQuery
    ? `/classroom/subjects/${subjectId}/assignments?workspace_id=${workspaceIdFromQuery}`
    : `/classroom/subjects/${subjectId}/assignments`;

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-8">
      {/* Header Navigation */}
      <div>
        <Link
          href={listUrl}
          className="text-sm font-medium text-[var(--primary)] hover:underline mb-3 inline-flex items-center gap-1"
        >
          <span className="material-symbols-outlined text-[16px]">arrow_back</span>
          Back to Assignments
        </Link>

        {actionMessage && (
          <div
            className={`mt-3 p-3.5 rounded-xl text-sm border flex items-center justify-between ${
              actionMessage.type === "success"
                ? "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800"
                : "bg-red-50 dark:bg-red-950/40 text-red-600 dark:text-red-400 border-red-200 dark:border-red-800"
            }`}
          >
            <span>{actionMessage.text}</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setActionMessage(null)}
              className="h-6 px-2 text-xs"
            >
              Dismiss
            </Button>
          </div>
        )}

        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mt-3">
          <div className="space-y-1.5 flex-1">
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-3xl font-bold text-[var(--on-surface)] leading-tight">
                {assignment.assignment_title}
              </h1>
              {getStatusBadge(assignment.assignment_status)}
            </div>
            {subject && (
              <p className="text-sm font-medium text-[var(--on-surface-variant)]">
                Subject: <span className="font-semibold text-[var(--on-surface)]">{subject.subject_name}</span>
              </p>
            )}
          </div>

          {/* Action Toolbar for Teachers / Admins */}
          {!isArchived && (canUpdate || canDelete) && (
            <div className="flex items-center gap-2 flex-wrap self-start sm:self-auto">
              {canUpdate && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={openEditModal}
                  disabled={submitting}
                >
                  <span className="material-symbols-outlined mr-1.5 text-[18px]">edit</span>
                  Edit
                </Button>
              )}

              {canUpdate && isDraft && (
                <Button
                  size="sm"
                  onClick={handlePublish}
                  disabled={submitting}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium"
                >
                  <span className="material-symbols-outlined mr-1.5 text-[18px]">publish</span>
                  Publish
                </Button>
              )}

              {canUpdate && isPublished && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleClose}
                  disabled={submitting}
                  className="border-amber-400 text-amber-700 dark:text-amber-300 hover:bg-amber-50 dark:hover:bg-amber-950/40"
                >
                  <span className="material-symbols-outlined mr-1.5 text-[18px]">lock</span>
                  Close Submissions
                </Button>
              )}

              {canDelete && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setArchiveOpen(true)}
                  disabled={submitting}
                  className="text-red-500 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950/40"
                >
                  <span className="material-symbols-outlined mr-1.5 text-[18px]">archive</span>
                  Archive
                </Button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Metadata Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-4 rounded-2xl bg-[var(--surface-container-low)] border border-[var(--outline-variant)]">
        <div className="space-y-0.5">
          <span className="text-xs font-semibold uppercase tracking-wider text-[var(--on-surface-variant)]">
            Due Date
          </span>
          <p className="text-sm font-bold text-[var(--on-surface)] flex items-center gap-1.5">
            <span className="material-symbols-outlined text-[18px] text-[var(--primary)]">event</span>
            {assignment.assignment_due_at
              ? new Date(assignment.assignment_due_at).toLocaleString(undefined, {
                  dateStyle: "medium",
                  timeStyle: "short",
                })
              : "No due date set"}
          </p>
        </div>

        <div className="space-y-0.5">
          <span className="text-xs font-semibold uppercase tracking-wider text-[var(--on-surface-variant)]">
            Created On
          </span>
          <p className="text-sm font-bold text-[var(--on-surface)]">
            {new Date(assignment.assignment_created_at).toLocaleDateString(undefined, {
              dateStyle: "medium",
            })}
          </p>
        </div>

        <div className="space-y-0.5">
          <span className="text-xs font-semibold uppercase tracking-wider text-[var(--on-surface-variant)]">
            Status
          </span>
          <p className="text-sm font-bold capitalize text-[var(--on-surface)]">
            {assignment.assignment_status}
          </p>
        </div>
      </div>

      {/* Main Content Area: Instructions & Description */}
      <div className="space-y-3">
        <h2 className="text-xl font-bold text-[var(--on-surface)]">Instructions & Description</h2>
        <div className="p-6 rounded-2xl bg-[var(--surface-container-lowest)] border border-[var(--outline-variant)] min-h-[120px]">
          {assignment.assignment_description ? (
            <div className="text-[var(--on-surface)] leading-relaxed whitespace-pre-wrap text-sm sm:text-base">
              {assignment.assignment_description}
            </div>
          ) : (
            <p className="text-sm text-[var(--on-surface-variant)] italic">
              No detailed instructions provided for this assignment.
            </p>
          )}
        </div>
      </div>

      {/* Attachments Section (Step 10.3A) */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-[var(--on-surface)]">Attachments</h2>
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-[var(--surface-container-high)] text-[var(--on-surface-variant)]">
              {attachments.length}
            </span>
          </div>

          {canManageAttachments && (
            <Button
              size="sm"
              onClick={() => {
                setSelectedFile(null);
                setUploadError(null);
                setUploadOpen(true);
              }}
              className="bg-[var(--primary)] text-[var(--on-primary)]"
            >
              <span className="material-symbols-outlined mr-1.5 text-[18px]">upload</span>
              Add Attachment
            </Button>
          )}
        </div>

        {attachments.length === 0 ? (
          <div className="p-6 rounded-2xl border border-dashed border-[var(--outline-variant)] bg-[var(--surface-container-lowest)] text-center space-y-2">
            <span className="material-symbols-outlined text-[28px] text-[var(--on-surface-variant)]">
              attach_file
            </span>
            <p className="text-sm text-[var(--on-surface-variant)]">
              {canManageAttachments
                ? "No attachments yet. You can attach PDFs, documents, spreadsheets, or images (up to 10 MB each)."
                : "No attachments provided for this assignment."}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {attachments.map((att) => (
              <div
                key={att.attachment_id}
                className="p-4 rounded-xl border border-[var(--outline-variant)] bg-[var(--surface-container-lowest)] flex items-center justify-between gap-3 group hover:border-[var(--primary)] transition-all"
              >
                <div className="flex items-center gap-3 min-w-0 flex-1">
                  <div className="w-10 h-10 rounded-lg bg-[var(--surface-container-high)] flex items-center justify-center text-[var(--primary)] shrink-0">
                    <span className="material-symbols-outlined text-[22px]">
                      {getFileIcon(att.content_type)}
                    </span>
                  </div>
                  <div className="min-w-0 flex-1">
                    <div
                      className="text-sm font-semibold text-[var(--on-surface)] truncate"
                      title={att.original_filename}
                    >
                      {att.original_filename}
                    </div>
                    <div className="text-xs text-[var(--on-surface-variant)] flex items-center gap-2 mt-0.5">
                      <span>{formatFileSize(att.size)}</span>
                      <span>&bull;</span>
                      <span>{new Date(att.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-1 shrink-0">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDownloadAttachment(att)}
                    title="Download attachment"
                    className="h-8 px-2.5 text-xs"
                  >
                    <span className="material-symbols-outlined mr-1 text-[16px]">download</span>
                    Download
                  </Button>

                  {canManageAttachments && (
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => {
                        setAttachmentToDelete(att);
                        setDeleteAttachmentError(null);
                      }}
                      title="Delete attachment"
                      className="h-8 w-8 text-red-500 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950/40"
                    >
                      <span className="material-symbols-outlined text-[18px]">delete</span>
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Submissions Section Placeholder (Foundation for Step 10.3B) */}
      <div className="space-y-3 pt-4 border-t border-[var(--outline-variant)]">
        <h2 className="text-xl font-bold text-[var(--on-surface)]">Submissions & Grading</h2>
        <div className="p-6 rounded-2xl border border-dashed border-[var(--outline-variant)] bg-[var(--surface-container-lowest)] text-center space-y-2">
          <span className="material-symbols-outlined text-[32px] text-[var(--on-surface-variant)]">
            upload_file
          </span>
          <h3 className="font-bold text-sm text-[var(--on-surface)]">
            {isPublished
              ? "Submissions are open"
              : isClosed
              ? "Submissions are closed"
              : "Submissions will open when published"}
          </h3>
          <p className="text-xs text-[var(--on-surface-variant)] max-w-md mx-auto">
            Student assignment submission and assessment workflows will be enabled in Step 10.3B.
          </p>
        </div>
      </div>

      {/* Edit Assignment Modal */}
      <Dialog open={editOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Edit Assignment</DialogTitle>
            <DialogDescription>
              Update assignment details and due date.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleEditSubmit} className="space-y-4 py-3">
            {editError && (
              <div className="p-3 text-sm text-red-600 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 rounded-lg">
                {editError}
              </div>
            )}

            <div className="space-y-1.5">
              <Label htmlFor="edit-title">Title *</Label>
              <Input
                id="edit-title"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                maxLength={255}
                autoFocus
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="edit-desc">Description</Label>
              <Textarea
                id="edit-desc"
                rows={5}
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="edit-due">Due Date & Time</Label>
              <Input
                id="edit-due"
                type="datetime-local"
                value={editDueAt}
                onChange={(e) => setEditDueAt(e.target.value)}
              />
            </div>

            <DialogFooter className="pt-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => setEditDialogOpen(false)}
                disabled={submitting}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={submitting}
                className="bg-[var(--primary)] text-[var(--on-primary)]"
              >
                {submitting ? "Saving..." : "Save Changes"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Upload Attachment Modal */}
      <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
        <DialogContent className="sm:max-w-[480px]">
          <DialogHeader>
            <DialogTitle>Add Attachment</DialogTitle>
            <DialogDescription>
              Upload supplementary materials (PDF, Word, Excel, or Images up to 10 MB).
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleUploadSubmit} className="space-y-4 py-3">
            {uploadError && (
              <div className="p-3 text-sm text-red-600 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 rounded-lg">
                {uploadError}
              </div>
            )}

            <div
              onClick={() => fileInputRef.current?.click()}
              className="p-6 rounded-2xl border-2 border-dashed border-[var(--outline-variant)] hover:border-[var(--primary)] transition-colors cursor-pointer text-center space-y-2 bg-[var(--surface-container-lowest)]"
            >
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept=".pdf,.png,.jpg,.jpeg,.webp,.doc,.docx,.xls,.xlsx"
                onChange={handleFileChange}
              />
              <span className="material-symbols-outlined text-[32px] text-[var(--primary)]">
                cloud_upload
              </span>
              <div className="text-sm font-semibold text-[var(--on-surface)]">
                {selectedFile ? selectedFile.name : "Click to select a file"}
              </div>
              <p className="text-xs text-[var(--on-surface-variant)]">
                {selectedFile
                  ? `${formatFileSize(selectedFile.size)} · ${selectedFile.type || "file"}`
                  : "PDF, DOCX, XLSX, PNG, JPG up to 10 MB"}
              </p>
            </div>

            {uploading && (
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs text-[var(--on-surface-variant)] font-medium">
                  <span>Uploading directly to storage...</span>
                  <span>{uploadProgress}%</span>
                </div>
                <div className="w-full h-2 rounded-full bg-[var(--surface-container-high)] overflow-hidden">
                  <div
                    className="h-full bg-[var(--primary)] transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            )}

            <DialogFooter className="pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setUploadOpen(false)}
                disabled={uploading}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={!selectedFile || uploading}
                className="bg-[var(--primary)] text-[var(--on-primary)]"
              >
                {uploading ? "Uploading..." : "Upload Attachment"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Attachment Confirmation Modal */}
      <Dialog
        open={!!attachmentToDelete}
        onOpenChange={(open) => !open && setAttachmentToDelete(null)}
      >
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Delete Attachment</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &quot;
              {attachmentToDelete?.original_filename}&quot;? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>

          {deleteAttachmentError && (
            <div className="p-3 text-sm text-red-600 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 rounded-lg">
              {deleteAttachmentError}
            </div>
          )}

          <DialogFooter className="pt-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => setAttachmentToDelete(null)}
              disabled={submitting}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={handleDeleteAttachmentSubmit}
              disabled={submitting}
            >
              {submitting ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Archive Confirmation Dialog */}
      <Dialog open={archiveOpen} onOpenChange={setArchiveOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Archive Assignment</DialogTitle>
            <DialogDescription>
              Are you sure you want to archive &quot;{assignment.assignment_title}&quot;? Archived
              assignments cannot be published or edited.
            </DialogDescription>
          </DialogHeader>

          {archiveError && (
            <div className="p-3 text-sm text-red-600 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 rounded-lg">
              {archiveError}
            </div>
          )}

          <DialogFooter className="pt-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => setArchiveOpen(false)}
              disabled={submitting}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={handleArchive}
              disabled={submitting}
            >
              {submitting ? "Archiving..." : "Archive"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
