import { apiFetch } from "./api";

export interface Workspace {
  workspace_id: string;
  workspace_organization_id: string;
  workspace_name: string;
  workspace_description: string | null;
  workspace_status: string;
  created_at: string;
  updated_at: string;
}

export async function fetchWorkspaces(): Promise<Workspace[]> {
  return await apiFetch<Workspace[]>("/workspaces");
}
