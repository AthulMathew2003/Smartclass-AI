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
