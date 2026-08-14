import { apiFetch } from "./api";

export type AssignmentStatus = "draft" | "published" | "closed" | "archived";

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

export async function fetchAssignments(
  subjectId: string,
  status?: AssignmentStatus | "all"
): Promise<Assignment[]> {
  let url = `/assignments?subject_id=${encodeURIComponent(subjectId)}`;
  if (status && status !== "all") {
    url += `&status=${encodeURIComponent(status)}`;
  }
  return await apiFetch<Assignment[]>(url);
}

export async function fetchAssignment(
  assignmentId: string,
  subjectId: string
): Promise<Assignment> {
  return await apiFetch<Assignment>(
    `/assignments/${encodeURIComponent(assignmentId)}?subject_id=${encodeURIComponent(subjectId)}`
  );
}

export async function createAssignment(
  data: AssignmentCreateInput
): Promise<Assignment> {
  return await apiFetch<Assignment>("/assignments", {
    method: "POST",
    body: JSON.stringify({
      assignment_subject_id: data.subject_id,
      title: data.title,
      description: data.description || undefined,
      due_at: data.due_at || undefined,
    }),
  });
}

export async function updateAssignment(
  assignmentId: string,
  subjectId: string,
  data: AssignmentUpdateInput
): Promise<Assignment> {
  return await apiFetch<Assignment>(
    `/assignments/${encodeURIComponent(assignmentId)}?subject_id=${encodeURIComponent(subjectId)}`,
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
  subjectId: string
): Promise<Assignment> {
  return await apiFetch<Assignment>(
    `/assignments/${encodeURIComponent(assignmentId)}/publish?subject_id=${encodeURIComponent(subjectId)}`,
    {
      method: "POST",
    }
  );
}

export async function closeAssignment(
  assignmentId: string,
  subjectId: string
): Promise<Assignment> {
  return await apiFetch<Assignment>(
    `/assignments/${encodeURIComponent(assignmentId)}/close?subject_id=${encodeURIComponent(subjectId)}`,
    {
      method: "POST",
    }
  );
}

export async function archiveAssignment(
  assignmentId: string,
  subjectId: string
): Promise<Assignment> {
  return await apiFetch<Assignment>(
    `/assignments/${encodeURIComponent(assignmentId)}?subject_id=${encodeURIComponent(subjectId)}`,
    {
      method: "DELETE",
    }
  );
}
