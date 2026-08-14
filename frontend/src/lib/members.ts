import { apiFetch } from "./api";
import { UserProfile } from "./auth";

export interface WorkspaceBrief {
  workspace_id: string;
  workspace_name: string;
}

export interface ProfilePhotoUploadInfo {
  key: string;
  upload_url: string;
  expires_in: number;
}

export interface Member {
  user_id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string | null;
  profile_image_url?: string | null;
  organization_member_id: string;
  status: string;
  role_id: string;
  role_name: string;
  workspaces: WorkspaceBrief[];
}

export interface MemberCreateResponse extends Member {
  profile_photo_upload?: ProfilePhotoUploadInfo | null;
}

export interface MemberCreatePayload {
  email: string;
  first_name: string;
  last_name: string;
  phone?: string | null;
  role_id: string;
  workspace_ids?: string[];
  content_type?: string | null;
  file_size?: number | null;
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
  workspace_id?: string;
}): Promise<Member[]> {
  const queryParts: string[] = [];
  if (params.search) queryParts.push(`search=${encodeURIComponent(params.search)}`);
  if (params.role_id) queryParts.push(`role_id=${encodeURIComponent(params.role_id)}`);
  if (params.status) queryParts.push(`status=${encodeURIComponent(params.status)}`);
  if (params.workspace_id) queryParts.push(`workspace_id=${encodeURIComponent(params.workspace_id)}`);
  
  const queryString = queryParts.length > 0 ? `?${queryParts.join("&")}` : "";
  return await apiFetch<Member[]>(`/organizations/members${queryString}`);
}

export async function checkMemberEmail(email: string): Promise<any> {
  return await apiFetch<any>(`/organizations/members/check-email?email=${encodeURIComponent(email)}`);
}

export async function addMember(payload: MemberCreatePayload): Promise<MemberCreateResponse> {
  return await apiFetch<MemberCreateResponse>("/organizations/members", {
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

/**
 * Request a presigned upload URL for a user's profile photo.
 */
export async function requestProfilePhotoUploadUrl(
  userId: string,
  contentType: string,
  fileSize: number
): Promise<ProfilePhotoUploadInfo> {
  return await apiFetch<ProfilePhotoUploadInfo>(`/users/${userId}/profile-photo/upload-url`, {
    method: "POST",
    body: JSON.stringify({ content_type: contentType, file_size: fileSize }),
  });
}

/**
 * Confirm a profile photo upload with the backend after PUT to S3 succeeds.
 */
export async function confirmProfilePhotoUpload(
  userId: string,
  key: string
): Promise<UserProfile> {
  return await apiFetch<UserProfile>(`/users/${userId}/profile-photo/confirm`, {
    method: "POST",
    body: JSON.stringify({ key }),
  });
}

/**
 * Remove a user's profile photo.
 */
export async function deleteProfilePhoto(userId: string): Promise<UserProfile> {
  return await apiFetch<UserProfile>(`/users/${userId}/profile-photo`, {
    method: "DELETE",
  });
}

/**
 * Directly upload a file to S3 using a presigned PUT URL.
 */
export async function uploadFileToS3(uploadUrl: string, file: File): Promise<void> {
  const response = await fetch(uploadUrl, {
    method: "PUT",
    headers: {
      "Content-Type": file.type,
    },
    body: file,
  });

  if (!response.ok) {
    throw new Error(`Failed to upload photo to storage (Status ${response.status})`);
  }
}
