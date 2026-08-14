import { apiFetch } from "./api";

export interface Subject {
  subject_id: string;
  subject_workspace_id: string;
  subject_name: string;
  subject_description?: string;
  subject_status: "active" | "archived";
  subject_created_by?: string;
  subject_created_at: string;
  subject_updated_at: string;
  teacher_count: number;
  teachers: SubjectTeacher[];
}

export interface SubjectTeacher {
  subject_teacher_id: string;
  subject_teacher_subject_id: string;
  subject_teacher_user_id: string;
  subject_teacher_assigned_at: string;
  user_email: string;
  user_first_name: string;
  user_last_name: string;
}

export interface SubjectCreatePayload {
  subject_name: string;
  workspace_id: string;
  subject_description?: string;
}

export interface SubjectUpdatePayload {
  subject_name?: string;
  subject_description?: string;
}

export interface SubjectTeacherAddPayload {
  user_id: string;
}

export async function fetchSubjects(workspaceId?: string): Promise<Subject[]> {
  const query = workspaceId ? `?workspace_id=${workspaceId}` : "";
  return await apiFetch<Subject[]>(`/subjects${query}`);
}

export async function fetchSubject(id: string, workspaceId: string): Promise<Subject> {
  return await apiFetch<Subject>(`/subjects/${id}?workspace_id=${workspaceId}`);
}

export async function createSubject(payload: SubjectCreatePayload): Promise<Subject> {
  return await apiFetch<Subject>("/subjects", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateSubject(id: string, workspaceId: string, payload: SubjectUpdatePayload): Promise<Subject> {
  return await apiFetch<Subject>(`/subjects/${id}?workspace_id=${workspaceId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function archiveSubject(id: string, workspaceId: string): Promise<Subject> {
  return await apiFetch<Subject>(`/subjects/${id}?workspace_id=${workspaceId}`, {
    method: "DELETE",
  });
}

export async function fetchSubjectTeachers(id: string, workspaceId: string): Promise<SubjectTeacher[]> {
  return await apiFetch<SubjectTeacher[]>(`/subjects/${id}/teachers?workspace_id=${workspaceId}`);
}

export async function addSubjectTeacher(id: string, workspaceId: string, payload: SubjectTeacherAddPayload): Promise<SubjectTeacher> {
  return await apiFetch<SubjectTeacher>(`/subjects/${id}/teachers?workspace_id=${workspaceId}`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function removeSubjectTeacher(id: string, userId: string, workspaceId: string): Promise<void> {
  return await apiFetch<void>(`/subjects/${id}/teachers/${userId}?workspace_id=${workspaceId}`, {
    method: "DELETE",
  });
}
