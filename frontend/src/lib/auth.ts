export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

import { apiFetch } from "./api";
import { clearPermissions } from "./permissions";

export interface UserProfile {
  id: string;
  email: string;
  first_name?: string | null;
  last_name?: string | null;
  profile_image?: string | null;
  profile_image_url?: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export interface OnboardingStatusResponse {
  has_organization: boolean;
  multiple_organizations?: boolean;
  organizations?: Array<{
    organization_id: string;
    organization_name: string;
    organization_slug: string;
    role_name: string;
  }> | null;
  organization_id?: string | null;
  organization_name?: string | null;
  workspace_id?: string | null;
  workspace_name?: string | null;
  role?: string | null;
  onboarding_completed?: boolean;
}

export interface OrganizationOnboardingPayload {
  organization_name: string;
  organization_slug?: string;
  organization_type: string;
  organization_country: string;
  organization_state?: string;
  organization_city?: string;
  organization_timezone?: string;
  organization_logo?: string;
  organization_description?: string;
  first_name?: string;
  last_name?: string;
  phone: string;
  workspace_name: string;
}

export interface OrganizationResponse {
  organization_id: string;
  organization_name: string;
  organization_slug: string;
  organization_type: string;
  organization_country: string;
  organization_timezone: string;
  workspace_id: string;
  workspace_name: string;
  owner_user_id: string;
}

// In-Memory Access Token Storage
let memoryAccessToken: string | null = null;
let currentUser: UserProfile | null = null;

export function getMemoryAccessToken(): string | null {
  return memoryAccessToken;
}

export function setMemoryAccessToken(token: string | null) {
  memoryAccessToken = token;
}

export function getCurrentUser(): UserProfile | null {
  return currentUser;
}

export function setCurrentUser(user: UserProfile | null) {
  currentUser = user;
}

export function getGoogleOAuthUrl(): string {
  return `${API_BASE_URL}/auth/google`;
}

export function getGitHubOAuthUrl(): string {
  return `${API_BASE_URL}/auth/github`;
}

export async function registerWithPassword(payload: {
  email: string;
  password: string;
  first_name?: string;
  last_name?: string;
}): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({ error: { message: "Registration failed" } }));
    throw new Error(errData?.error?.message || errData?.detail || "Failed to register account");
  }

  const data: AuthResponse = await res.json();
  setMemoryAccessToken(data.access_token);
  setCurrentUser(data.user);
  return data;
}

export async function loginWithPassword(payload: {
  email: string;
  password: string;
}): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({ error: { message: "Login failed" } }));
    throw new Error(errData?.error?.message || errData?.detail || "Invalid email or password");
  }

  const data: AuthResponse = await res.json();
  setMemoryAccessToken(data.access_token);
  setCurrentUser(data.user);
  return data;
}

export async function refreshAuthSession(): Promise<{ accessToken: string; user: UserProfile } | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include",
    });

    if (!res.ok) {
      setMemoryAccessToken(null);
      setCurrentUser(null);
      return null;
    }

    const data: AuthResponse = await res.json();
    setMemoryAccessToken(data.access_token);
    setCurrentUser(data.user);
    return {
      accessToken: data.access_token,
      user: data.user,
    };
  } catch (error) {
    console.error("Failed to refresh session:", error);
    setMemoryAccessToken(null);
    setCurrentUser(null);
    return null;
  }
}

export async function fetchCurrentUser(): Promise<UserProfile | null> {
  let token = getMemoryAccessToken();
  if (!token) {
    const session = await refreshAuthSession();
    token = session?.accessToken || null;
  }
  if (!token) return null;

  try {
    const res = await fetch(`${API_BASE_URL}/auth/me`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      credentials: "include",
    });

    if (!res.ok) return null;
    const user: UserProfile = await res.json();
    setCurrentUser(user);
    return user;
  } catch (err) {
    console.error("Failed to fetch current user:", err);
    return null;
  }
}

export async function fetchOnboardingStatus(): Promise<OnboardingStatusResponse | null> {
  try {
    return await apiFetch<OnboardingStatusResponse>("/organizations/status");
  } catch (err) {
    console.error("Failed to fetch onboarding status:", err);
    return null;
  }
}

export interface UserMembershipBrief {
  organization_id: string;
  organization_name: string;
  organization_slug: string;
  role_name: string;
  workspace_name?: string | null;
}

export async function fetchUserMemberships(): Promise<UserMembershipBrief[] | null> {
  try {
    return await apiFetch<UserMembershipBrief[]>("/organizations/memberships");
  } catch (err) {
    console.error("Failed to fetch user memberships:", err);
    return null;
  }
}

export async function submitOrganizationOnboarding(
  payload: OrganizationOnboardingPayload
): Promise<OrganizationResponse> {
  try {
    return await apiFetch<OrganizationResponse>("/organizations/onboarding", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  } catch (err: any) {
    throw new Error(err.message || "Failed to complete organization onboarding");
  }
}

export async function logoutUser(): Promise<void> {
  try {
    await fetch(`${API_BASE_URL}/auth/logout`, {
      method: "POST",
      credentials: "include",
    });
  } catch (err) {
    console.error("Logout request failed:", err);
  } finally {
    setMemoryAccessToken(null);
    setCurrentUser(null);
    clearPermissions();
  }
}

export function consumeInitialAccessTokenCookie(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|; )initial_access_token=([^;]*)/);
  if (match) {
    const token = decodeURIComponent(match[1]);
    document.cookie = "initial_access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
    return token;
  }
  return null;
}

// ── Roles & Permissions API Interfaces & Helpers ─────────────

export interface PermissionItem {
  permission_id: string;
  permission_name: string;
  permission_description: string | null;
  category: string;
}

export interface PermissionGroup {
  category: string;
  permissions: PermissionItem[];
}

export interface RoleDetail {
  role_id: string;
  role_name: string;
  role_description: string | null;
  role_is_system: boolean;
  role_organization_id: string | null;
  member_count: number;
  permissions: PermissionItem[];
}

export interface RoleCreatePayload {
  role_name: string;
  role_description?: string | null;
  permission_ids?: string[];
}

export interface RoleUpdatePayload {
  role_name?: string;
  role_description?: string | null;
  permission_ids?: string[];
}

// ── Removed getOrgHeaders and getAuthenticatedToken here. ─────────────

export async function fetchRoles(): Promise<RoleDetail[]> {
  return await apiFetch<RoleDetail[]>("/roles");
}

export async function fetchRole(roleId: string): Promise<RoleDetail> {
  return await apiFetch<RoleDetail>(`/roles/${roleId}`);
}

export async function fetchGroupedPermissions(): Promise<PermissionGroup[]> {
  return await apiFetch<PermissionGroup[]>("/roles/permissions");
}

export async function createRole(payload: RoleCreatePayload): Promise<RoleDetail> {
  return await apiFetch<RoleDetail>("/roles", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateRole(roleId: string, payload: RoleUpdatePayload): Promise<RoleDetail> {
  return await apiFetch<RoleDetail>(`/roles/${roleId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function updateRolePermissions(roleId: string, permissionIds: string[]): Promise<RoleDetail> {
  return await updateRole(roleId, { permission_ids: permissionIds });
}

export async function deleteRole(roleId: string): Promise<void> {
  await apiFetch(`/roles/${roleId}`, {
    method: "DELETE",
  });
}
