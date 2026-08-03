export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface UserProfile {
  id: string;
  email: string;
  first_name?: string | null;
  last_name?: string | null;
  profile_image?: string | null;
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
  let token = getMemoryAccessToken();
  if (!token) {
    const session = await refreshAuthSession();
    token = session?.accessToken || null;
  }
  if (!token) return null;

  try {
    const headers: Record<string, string> = {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };
    if (typeof window !== "undefined") {
      const activeOrgId = localStorage.getItem("activeOrganizationId");
      if (activeOrgId) {
        headers["X-Organization-Id"] = activeOrgId;
      }
    }

    const res = await fetch(`${API_BASE_URL}/organizations/status`, {
      method: "GET",
      headers,
      credentials: "include",
    });

    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.error("Failed to fetch onboarding status:", err);
    return null;
  }
}

export async function submitOrganizationOnboarding(
  payload: OrganizationOnboardingPayload
): Promise<OrganizationResponse> {
  let token = getMemoryAccessToken();
  if (!token) {
    const session = await refreshAuthSession();
    token = session?.accessToken || null;
  }

  if (!token) {
    throw new Error("Authentication required to complete onboarding.");
  }

  const res = await fetch(`${API_BASE_URL}/organizations/onboarding`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    credentials: "include",
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({ error: { message: "Onboarding failed" } }));
    throw new Error(errData?.error?.message || errData?.detail || "Failed to complete organization onboarding");
  }

  return await res.json();
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
