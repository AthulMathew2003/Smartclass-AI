import { getMemoryAccessToken, refreshAuthSession, API_BASE_URL } from "./auth";

interface ApiFetchOptions extends RequestInit {
  requireOrgContext?: boolean; // If true, requires X-Organization-Id header (defaults to true)
}

export async function getAuthenticatedToken(): Promise<string> {
  let token = getMemoryAccessToken();
  if (!token) {
    const session = await refreshAuthSession();
    token = session?.accessToken || null;
  }
  if (!token) {
    throw new Error("Authentication required.");
  }
  return token;
}

export async function apiFetch<T = any>(
  endpoint: string,
  options: ApiFetchOptions = {}
): Promise<T> {
  const token = await getAuthenticatedToken();

  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
  };

  // Automatically attach content type if body is a string (e.g. JSON.stringify)
  if (options.body && typeof options.body === "string") {
    headers["Content-Type"] = "application/json";
  }

  // Inject organization context if requested (default to true)
  const requireOrgContext = options.requireOrgContext ?? true;
  if (requireOrgContext && typeof window !== "undefined") {
    const activeOrgId = localStorage.getItem("activeOrganizationId");
    if (activeOrgId) {
      headers["X-Organization-Id"] = activeOrgId;
    }
  }

  const { requireOrgContext: _, ...fetchOptions } = options;

  const res = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...fetchOptions,
    headers: {
      ...headers,
      ...(fetchOptions.headers as Record<string, string> || {}),
    },
    credentials: "include",
  });

  if (!res.ok) {
    let errorDetail = "An error occurred";
    try {
      const errData = await res.json();
      errorDetail = errData?.detail || errData?.message || errData?.error?.message || errorDetail;
    } catch {
      // Ignored
    }
    throw new Error(errorDetail);
  }

  // If status is 204 No Content, return null
  if (res.status === 204) {
    return null as T;
  }

  return await res.json();
}
