/**
 * Centralized Permission System for SmartClass AI
 *
 * Provides permission state management, subscriber listeners, a React hook, and query functions.
 * Permissions are scoped per-organization and refreshed on org switch.
 *
 * Frontend permission checks are for UX only — backend always enforces via require_permission().
 */

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "./api";

// ── Types ───────────────────────────────────────────────────────────
interface MyPermissionsResponse {
  organization_id: string;
  permissions: string[];
}

type PermissionListener = () => void;

// ── Module-level state (scoped to active organization) ──────────────
let _permissions: string[] = [];
let _permissionsOrgId: string | null = null;
let _permissionsLoaded = false;
let _permissionsLoading = false;
let _loadPromise: Promise<void> | null = null;
const _listeners = new Set<PermissionListener>();

function notifyListeners() {
  _listeners.forEach((listener) => {
    try {
      listener();
    } catch (e) {
      console.error("Error in permission listener:", e);
    }
  });
}

/**
 * Subscribe a component or callback to permission state changes.
 * Returns an unsubscribe function.
 */
export function subscribePermissions(listener: PermissionListener): () => void {
  _listeners.add(listener);
  return () => {
    _listeners.delete(listener);
  };
}

// ── API Function ────────────────────────────────────────────────────

/**
 * Fetch the authenticated user's effective permissions for the active organization.
 * Uses the existing apiFetch helper which automatically injects the
 * Authorization header and X-Organization-Id from localStorage.
 */
export async function fetchMyPermissions(): Promise<MyPermissionsResponse> {
  return await apiFetch<MyPermissionsResponse>("/roles/me/permissions");
}

// ── State Management ────────────────────────────────────────────────

/**
 * Load permissions for the current active organization.
 * Deduplicates concurrent calls (returns existing promise if loading).
 * Safe to call multiple times — only fetches if not already loaded for the current org.
 */
export async function loadPermissions(forceReload = false): Promise<void> {
  const activeOrgId =
    typeof window !== "undefined"
      ? localStorage.getItem("activeOrganizationId")
      : null;

  // Already loaded for this org unless forceReload
  if (!forceReload && _permissionsLoaded && _permissionsOrgId === activeOrgId) {
    return;
  }

  // Already loading — return existing promise
  if (_permissionsLoading && _loadPromise) {
    return _loadPromise;
  }

  _permissionsLoading = true;

  _loadPromise = (async () => {
    try {
      const data = await fetchMyPermissions();
      _permissions = data.permissions;
      _permissionsOrgId = data.organization_id;
      _permissionsLoaded = true;
    } catch (err) {
      console.error("Failed to load permissions:", err);
      _permissions = [];
      _permissionsOrgId = activeOrgId;
      _permissionsLoaded = true;
    } finally {
      _permissionsLoading = false;
      _loadPromise = null;
      notifyListeners();
    }
  })();

  return _loadPromise;
}

/**
 * Clear all permission state.
 * Must be called on:
 * - Logout
 * - Organization switch (before navigating to the new org context)
 */
export function clearPermissions(): void {
  _permissions = [];
  _permissionsOrgId = null;
  _permissionsLoaded = false;
  _permissionsLoading = false;
  _loadPromise = null;
  notifyListeners();
}

// ── Query Functions ─────────────────────────────────────────────────

/**
 * Check if the current user has a specific permission in the active organization.
 * Returns false if permissions haven't been loaded yet.
 */
export function hasPermission(permission: string): boolean {
  return _permissions.includes(permission);
}

/**
 * Check if the current user has ANY of the specified permissions.
 * Returns true if at least one permission matches.
 */
export function hasAnyPermission(permissions: string[]): boolean {
  return permissions.some((p) => _permissions.includes(p));
}

/**
 * Check if the current user has ALL of the specified permissions.
 * Returns true only if every permission matches.
 */
export function hasAllPermissions(permissions: string[]): boolean {
  return permissions.every((p) => _permissions.includes(p));
}

/**
 * Whether permissions have been loaded (including error state).
 * Use this to show loading skeletons before rendering permission-aware UI.
 */
export function isPermissionsLoaded(): boolean {
  return _permissionsLoaded;
}

/**
 * Get the organization ID for which permissions are currently loaded.
 */
export function getPermissionsOrgId(): string | null {
  return _permissionsOrgId;
}

// ── React Hook ──────────────────────────────────────────────────────

/**
 * React hook that subscribes to permission state updates,
 * ensuring automatic component re-renders when permissions change.
 */
export function usePermissions() {
  const [permissions, setPermissions] = useState<string[]>(_permissions);
  const [loaded, setLoaded] = useState<boolean>(_permissionsLoaded);
  const [orgId, setOrgId] = useState<string | null>(_permissionsOrgId);

  useEffect(() => {
    // Synchronize initial state
    setPermissions(_permissions);
    setLoaded(_permissionsLoaded);
    setOrgId(_permissionsOrgId);

    const unsubscribe = subscribePermissions(() => {
      setPermissions(_permissions);
      setLoaded(_permissionsLoaded);
      setOrgId(_permissionsOrgId);
    });

    return unsubscribe;
  }, []);

  const checkHasPermission = useCallback((permission: string) => permissions.includes(permission), [permissions]);
  const checkHasAnyPermission = useCallback((pList: string[]) => pList.some((p) => permissions.includes(p)), [permissions]);
  const checkHasAllPermissions = useCallback((pList: string[]) => pList.every((p) => permissions.includes(p)), [permissions]);

  return {
    permissions,
    isLoaded: loaded,
    orgId,
    hasPermission: checkHasPermission,
    hasAnyPermission: checkHasAnyPermission,
    hasAllPermissions: checkHasAllPermissions,
  };
}
