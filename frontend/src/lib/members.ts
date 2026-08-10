import { apiFetch } from "./api";
import { UserProfile } from "./auth";

export interface WorkspaceBrief {
  workspace_id: string;
  workspace_name: string;
}

export interface Member {
  user_id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string | null;
  organization_member_id: string;
  status: string;
  role_id: string;
  role_name: string;
  workspaces: WorkspaceBrief[];
}

export interface MemberCreatePayload {
  email: string;
  first_name: string;
  last_name: string;
  phone?: string | null;
  role_id: string;
  workspace_ids?: string[];
}

export interface MemberUpdatePayload {
  first_name?: string;
  last_name?: string;
  phone?: string | null;
  role_id?: string;
}

export async function fetchMembers(params: {
  search?: string;
  role_id?: string;
  status?: string;
}): Promise<Member[]> {
  const queryParts: string[] = [];
  if (params.search) queryParts.push(`search=${encodeURIComponent(params.search)}`);
  if (params.role_id) queryParts.push(`role_id=${encodeURIComponent(params.role_id)}`);
  if (params.status) queryParts.push(`status=${encodeURIComponent(params.status)}`);
  
  const queryString = queryParts.length > 0 ? `?${queryParts.join("&")}` : "";
  return await apiFetch<Member[]>(`/organizations/members${queryString}`);
}

export async function checkMemberEmail(email: string): Promise<any> {
  return await apiFetch<any>(`/organizations/members/check-email?email=${encodeURIComponent(email)}`);
}

export async function addMember(payload: MemberCreatePayload): Promise<Member> {
  return await apiFetch<Member>("/organizations/members", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateMember(memberId: string, payload: MemberUpdatePayload): Promise<Member> {
  return await apiFetch<Member>(`/organizations/members/${memberId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function updateMemberStatus(memberId: string, status: string): Promise<Member> {
  return await apiFetch<Member>(`/organizations/members/${memberId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export async function deleteMember(memberId: string): Promise<void> {
  await apiFetch(`/organizations/members/${memberId}`, {
    method: "DELETE",
  });
}

export async function updateMemberWorkspaces(userId: string, workspaceIds: string[]): Promise<void> {
  await apiFetch(`/organizations/members/${userId}/workspaces`, {
    method: "PATCH",
    body: JSON.stringify(workspaceIds),
  });
}
