import { apiFetch } from "./api";

export interface Workspace {
  workspace_id: string;
  workspace_organization_id: string;
  workspace_name: string;
  workspace_description: string | null;
  workspace_banner?: string | null;
  workspace_status: "active" | "archived" | string;
  workspace_created_by: string;
  workspace_created_at: string;
  workspace_updated_at: string;
  member_count?: number;
  student_count?: number;
  subject_count?: number;
}

export interface WorkspaceStudent {
  id: string;
  name: string;
  first_name: string | null;
  last_name: string | null;
  email: string | null;
  avatar_url: string | null;
  status: string;
  joined_at: string | null;
}

export interface WorkspaceStudentsResponse {
  success: boolean;
  message: string;
  data: {
    items: WorkspaceStudent[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  };
  request_id?: string | null;
}

export interface WorkspaceMemberItem {
  user_id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  role_name: string;
}

export interface WorkspaceCreatePayload {
  workspace_name: string;
  workspace_description?: string | null;
}

export interface WorkspaceUpdatePayload {
  workspace_name?: string;
  workspace_description?: string | null;
  workspace_status?: string;
}

export async function fetchWorkspaces(): Promise<Workspace[]> {
  return await apiFetch<Workspace[]>("/workspaces");
}

export async function fetchWorkspace(workspaceId: string): Promise<Workspace> {
  return await apiFetch<Workspace>(`/workspaces/${workspaceId}`);
}

export async function createWorkspace(payload: WorkspaceCreatePayload): Promise<Workspace> {
  return await apiFetch<Workspace>("/workspaces", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateWorkspace(
  workspaceId: string,
  payload: WorkspaceUpdatePayload
): Promise<Workspace> {
  return await apiFetch<Workspace>(`/workspaces/${workspaceId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function archiveWorkspace(workspaceId: string): Promise<Workspace> {
  return await apiFetch<Workspace>(`/workspaces/${workspaceId}`, {
    method: "DELETE",
  });
}

export async function fetchWorkspaceMembers(workspaceId: string): Promise<WorkspaceMemberItem[]> {
  return await apiFetch<WorkspaceMemberItem[]>(`/workspaces/${workspaceId}/members`);
}

export async function fetchWorkspaceStudents(
  workspaceId: string,
  params?: {
    search?: string;
    page?: number;
    page_size?: number;
  }
): Promise<WorkspaceStudentsResponse> {
  const query = new URLSearchParams();
  if (params?.search && params.search.trim()) query.set("search", params.search.trim());
  if (params?.page) query.set("page", String(params.page));
  if (params?.page_size) query.set("page_size", String(params.page_size));

  const qs = query.toString();
  const endpoint = `/workspaces/${workspaceId}/students${qs ? `?${qs}` : ""}`;
  return await apiFetch<WorkspaceStudentsResponse>(endpoint);
}

