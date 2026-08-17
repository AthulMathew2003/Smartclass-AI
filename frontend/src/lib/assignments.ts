import { apiFetch } from "./api";

export type AssignmentStatus = "draft" | "published" | "closed" | "archived";
export type SubmissionStatus = "draft" | "submitted" | "late" | "graded" | "returned";

export interface SubmissionSummary {
  submission_id: string;
  submission_status: SubmissionStatus;
  submission_submitted_at?: string | null;
  submission_grade?: number | null;
}

export interface Assignment {
  assignment_id: string;
  assignment_subject_id: string;
  assignment_title: string;
  assignment_description?: string | null;
  assignment_status: AssignmentStatus;
  assignment_due_at?: string | null;
  assignment_created_by?: string | null;
  assignment_created_at: string;
  assignment_updated_at: string;

  // Enriched global fields
  subject_name?: string | null;
  workspace_id?: string | null;
  workspace_name?: string | null;
  submission_count?: number | null;
  graded_count?: number | null;
  pending_count?: number | null;
  student_submission?: SubmissionSummary | null;
}

export interface AssignmentCreateInput {
  subject_id: string;
  title: string;
  description?: string;
  due_at?: string;
}

export interface AssignmentUpdateInput {
  title?: string;
  description?: string;
  due_at?: string;
}

export interface AssignmentAttachment {
  attachment_id: string;
  assignment_id: string;
  original_filename: string;
  content_type: string;
  size: number;
  created_by?: string | null;
  created_at: string;
}

export interface AttachmentUploadUrlResponse {
  attachment_id: string;
  s3_key: string;
  upload_url: string;
  expires_in: number;
}

export interface AttachmentDownloadUrlResponse {
  attachment_id: string;
  original_filename: string;
  download_url: string;
  expires_in: number;
}

export interface SubmissionAttachment {
  attachment_id: string;
  submission_id: string;
  original_filename: string;
  content_type: string;
  size: number;
  created_at: string;
}

export interface Submission {
  submission_id: string;
  submission_assignment_id: string;
  submission_student_id: string;
  submission_status: SubmissionStatus;
  submission_submitted_at?: string | null;
  submission_grade?: number | null;
  submission_feedback?: string | null;
  submission_graded_by?: string | null;
  submission_graded_at?: string | null;
  submission_created_at: string;
  submission_updated_at: string;
  student_name?: string | null;
  student_email?: string | null;
  attachments: SubmissionAttachment[];
}

export interface SubmissionFileUploadUrlResponse {
  attachment_id: string;
  s3_key: string;
  upload_url: string;
  expires_in: number;
}

// ── Assignment CRUD Operations ──────────────────────────────────

export async function fetchAssignments(
  subjectId?: string,
  status?: AssignmentStatus | "all"
): Promise<Assignment[]> {
  const params = new URLSearchParams();
  if (subjectId) {
    params.append("subject_id", subjectId);
  }
  if (status && status !== "all") {
    params.append("status", status);
  }
  const queryStr = params.toString() ? `?${params.toString()}` : "";
  return await apiFetch<Assignment[]>(`/assignments${queryStr}`);
}

export async function fetchAssignment(
  assignmentId: string,
  subjectId?: string
): Promise<Assignment> {
  const queryStr = subjectId ? `?subject_id=${encodeURIComponent(subjectId)}` : "";
  return await apiFetch<Assignment>(`/assignments/${encodeURIComponent(assignmentId)}${queryStr}`);
}

export async function createAssignment(
  data: AssignmentCreateInput
): Promise<Assignment> {
  return await apiFetch<Assignment>("/assignments", {
    method: "POST",
    body: JSON.stringify({
      subject_id: data.subject_id,
      title: data.title,
      description: data.description || undefined,
      due_at: data.due_at || undefined,
    }),
  });
}

export async function updateAssignment(
  assignmentId: string,
  arg2: AssignmentUpdateInput | string,
  arg3?: AssignmentUpdateInput | string
): Promise<Assignment> {
  let data: AssignmentUpdateInput;
  let subjectId: string | undefined;

  if (typeof arg2 === "string") {
    subjectId = arg2;
    data = (arg3 as AssignmentUpdateInput) || {};
  } else {
    data = arg2;
    subjectId = typeof arg3 === "string" ? arg3 : undefined;
  }

  const queryStr = subjectId ? `?subject_id=${encodeURIComponent(subjectId)}` : "";
  return await apiFetch<Assignment>(
    `/assignments/${encodeURIComponent(assignmentId)}${queryStr}`,
    {
      method: "PATCH",
      body: JSON.stringify({
        title: data.title,
        description: data.description !== undefined ? data.description : undefined,
        due_at: data.due_at !== undefined ? data.due_at : undefined,
      }),
    }
  );
}

export async function publishAssignment(
  assignmentId: string,
  subjectId?: string
): Promise<Assignment> {
  const queryStr = subjectId ? `?subject_id=${encodeURIComponent(subjectId)}` : "";
  return await apiFetch<Assignment>(
    `/assignments/${encodeURIComponent(assignmentId)}/publish${queryStr}`,
    {
      method: "POST",
    }
  );
}

export async function closeAssignment(
  assignmentId: string,
  subjectId?: string
): Promise<Assignment> {
  const queryStr = subjectId ? `?subject_id=${encodeURIComponent(subjectId)}` : "";
  return await apiFetch<Assignment>(
    `/assignments/${encodeURIComponent(assignmentId)}/close${queryStr}`,
    {
      method: "POST",
    }
  );
}

export async function archiveAssignment(
  assignmentId: string,
  subjectId?: string
): Promise<Assignment> {
  const queryStr = subjectId ? `?subject_id=${encodeURIComponent(subjectId)}` : "";
  return await apiFetch<Assignment>(
    `/assignments/${encodeURIComponent(assignmentId)}${queryStr}`,
    {
      method: "DELETE",
    }
  );
}

// ── Assignment Attachments Operations ───────────────────────────

export async function requestAssignmentAttachmentUploadUrl(
  assignmentId: string,
  arg2: string | { filename: string; content_type: string; file_size: number },
  arg3?: string | { filename: string; content_type: string; file_size: number }
): Promise<AttachmentUploadUrlResponse> {
  let data: { filename: string; content_type: string; file_size: number };
  let subjectId: string | undefined;

  if (typeof arg2 === "string") {
    subjectId = arg2;
    data = arg3 as { filename: string; content_type: string; file_size: number };
  } else {
    data = arg2;
    subjectId = typeof arg3 === "string" ? arg3 : undefined;
  }

  const queryStr = subjectId ? `?subject_id=${encodeURIComponent(subjectId)}` : "";
  return await apiFetch<AttachmentUploadUrlResponse>(
    `/assignments/${encodeURIComponent(assignmentId)}/attachments/upload-url${queryStr}`,
    {
      method: "POST",
      body: JSON.stringify(data),
    }
  );
}

export async function confirmAssignmentAttachmentUpload(
  assignmentId: string,
  arg2: string | { attachment_id: string; s3_key: string; original_filename: string; content_type: string; file_size: number },
  arg3?: string | { attachment_id: string; s3_key: string; original_filename: string; content_type: string; file_size: number }
): Promise<AssignmentAttachment> {
  let data: { attachment_id: string; s3_key: string; original_filename: string; content_type: string; file_size: number };
  let subjectId: string | undefined;

  if (typeof arg2 === "string") {
    subjectId = arg2;
    data = arg3 as { attachment_id: string; s3_key: string; original_filename: string; content_type: string; file_size: number };
  } else {
    data = arg2;
    subjectId = typeof arg3 === "string" ? arg3 : undefined;
  }

  const queryStr = subjectId ? `?subject_id=${encodeURIComponent(subjectId)}` : "";
  return await apiFetch<AssignmentAttachment>(
    `/assignments/${encodeURIComponent(assignmentId)}/attachments/confirm${queryStr}`,
    {
      method: "POST",
      body: JSON.stringify(data),
    }
  );
}

export async function fetchAssignmentAttachments(
  assignmentId: string,
  subjectId?: string
): Promise<AssignmentAttachment[]> {
  const queryStr = subjectId ? `?subject_id=${encodeURIComponent(subjectId)}` : "";
  return await apiFetch<AssignmentAttachment[]>(
    `/assignments/${encodeURIComponent(assignmentId)}/attachments${queryStr}`
  );
}

export async function getAssignmentAttachmentDownloadUrl(
  assignmentId: string,
  attachmentId: string,
  subjectId?: string
): Promise<AttachmentDownloadUrlResponse> {
  const queryStr = subjectId ? `?subject_id=${encodeURIComponent(subjectId)}` : "";
  return await apiFetch<AttachmentDownloadUrlResponse>(
    `/assignments/${encodeURIComponent(assignmentId)}/attachments/${encodeURIComponent(attachmentId)}/download-url${queryStr}`
  );
}

export async function deleteAssignmentAttachment(
  assignmentId: string,
  attachmentId: string,
  subjectId?: string
): Promise<void> {
  const queryStr = subjectId ? `?subject_id=${encodeURIComponent(subjectId)}` : "";
  await apiFetch<void>(
    `/assignments/${encodeURIComponent(assignmentId)}/attachments/${encodeURIComponent(attachmentId)}${queryStr}`,
    {
      method: "DELETE",
    }
  );
}

// ── Student Submissions & Versions Operations ───────────────────

export async function fetchStudentSubmission(
  assignmentId: string,
  studentId?: string
): Promise<Submission | null> {
  const queryStr = studentId ? `?student_id=${encodeURIComponent(studentId)}` : "";
  return await apiFetch<Submission | null>(
    `/assignments/${encodeURIComponent(assignmentId)}/submission${queryStr}`
  );
}

export async function fetchAssignmentSubmissions(
  assignmentId: string
): Promise<Submission[]> {
  return await apiFetch<Submission[]>(
    `/assignments/${encodeURIComponent(assignmentId)}/submissions`
  );
}

export async function requestSubmissionFileUploadUrl(
  assignmentId: string,
  data: {
    filename: string;
    content_type: string;
    file_size: number;
  }
): Promise<SubmissionFileUploadUrlResponse> {
  return await apiFetch<SubmissionFileUploadUrlResponse>(
    `/assignments/${encodeURIComponent(assignmentId)}/submission/files/upload-url`,
    {
      method: "POST",
      body: JSON.stringify(data),
    }
  );
}

export async function submitAssignment(
  assignmentId: string,
  data: {
    files?: Array<{
      attachment_id: string;
      s3_key: string;
      original_filename: string;
      content_type: string;
      file_size: number;
    }>;
  }
): Promise<Submission> {
  return await apiFetch<Submission>(
    `/assignments/${encodeURIComponent(assignmentId)}/submit`,
    {
      method: "POST",
      body: JSON.stringify(data),
    }
  );
}

export async function getSubmissionAttachmentDownloadUrl(
  assignmentId: string,
  attachmentId: string
): Promise<AttachmentDownloadUrlResponse> {
  return await apiFetch<AttachmentDownloadUrlResponse>(
    `/assignments/${encodeURIComponent(assignmentId)}/submission/files/${encodeURIComponent(attachmentId)}/download-url`
  );
}

// ── Teacher Grading Operations ──────────────────────────────────

export async function gradeSubmission(
  assignmentId: string,
  submissionId: string,
  data: {
    grade: number;
    feedback?: string;
  }
): Promise<Submission> {
  return await apiFetch<Submission>(
    `/assignments/${encodeURIComponent(assignmentId)}/submissions/${encodeURIComponent(submissionId)}/grade`,
    {
      method: "POST",
      body: JSON.stringify(data),
    }
  );
}

export async function returnSubmission(
  assignmentId: string,
  submissionId: string,
  data: {
    feedback?: string;
  }
): Promise<Submission> {
  return await apiFetch<Submission>(
    `/assignments/${encodeURIComponent(assignmentId)}/submissions/${encodeURIComponent(submissionId)}/return`,
    {
      method: "POST",
      body: JSON.stringify(data),
    }
  );
}

// ── S3 Direct Upload Helper ─────────────────────────────────────

export async function uploadFileToS3(
  uploadUrl: string,
  file: File,
  contentType: string,
  onProgress?: (progress: number) => void
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", uploadUrl);
    xhr.setRequestHeader("Content-Type", contentType);

    if (xhr.upload && onProgress) {
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          const percent = Math.round((event.loaded / event.total) * 100);
          onProgress(percent);
        }
      };
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve();
      } else {
        reject(new Error(`S3 upload failed with status ${xhr.status}: ${xhr.statusText}`));
      }
    };

    xhr.onerror = () => {
      reject(new Error("Network error during S3 file upload"));
    };

    xhr.send(file);
  });
}
