"use client";

import React, { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import {
  fetchCurrentUser,
  fetchOnboardingStatus,
  fetchUserMemberships,
  UserProfile,
  OnboardingStatusResponse
} from "../../lib/auth";
import { loadPermissions, clearPermissions, getPermissionsOrgId, isPermissionsLoaded } from "../../lib/permissions";

export default function ClassroomLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [status, setStatus] = useState<OnboardingStatusResponse | null>(null);
  const [permissionsReady, setPermissionsReady] = useState(false);

  useEffect(() => {
    const init = async () => {
      const currentUser = await fetchCurrentUser();
      if (!currentUser) {
        router.push("/login");
        return;
      }
      setUser(currentUser);

      const onboardingStatus = await fetchOnboardingStatus();
      if (onboardingStatus) {
        const mems = await fetchUserMemberships();
        const activeOrgId = typeof window !== "undefined" ? localStorage.getItem("activeOrganizationId") : null;
        const activeMem = mems?.find(m => m.organization_id === activeOrgId) || (mems && mems.length > 0 ? mems[0] : null);

        if (activeMem && typeof window !== "undefined") {
          localStorage.setItem("activeOrganizationId", activeMem.organization_id);
        }

        setStatus({
          has_organization: onboardingStatus.has_organization,
          organization_id: activeMem?.organization_id,
          organization_name: activeMem?.organization_name,
          workspace_name: activeMem?.workspace_name,
          role: activeMem?.role_name,
          multiple_organizations: mems ? mems.length > 1 : false,
          organizations: mems
        });

        // Load effective permissions for the active organization
        if (activeMem) {
          if (getPermissionsOrgId() !== activeMem.organization_id || !isPermissionsLoaded()) {
            await loadPermissions(true);
          }
        }
        setPermissionsReady(true);
      }
      setLoading(false);
    };

    init();
  }, [router, pathname]);

  if (loading || !permissionsReady) {
    return (
      <div className="min-h-screen bg-[var(--surface)] text-[var(--on-surface)] flex items-center justify-center p-6">
        <div className="max-w-md w-full p-8 rounded-3xl bg-[var(--surface-container)] border border-[var(--outline-variant)]/30 text-center space-y-4 shadow-xl">
          <div className="w-12 h-12 border-4 border-[var(--primary)] border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p className="text-sm font-semibold text-[var(--on-surface-variant)]">Loading SmartClass AI Portal...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--surface)] text-[var(--on-surface)] flex">
      {/* Sidebar Navigation */}
      <Sidebar status={status} />

      {/* Main Viewport */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen">
        <Header user={user} status={status} />
        <main className="flex-1 p-6 md:p-10 overflow-y-auto relative">
          {children}
        </main>
      </div>
    </div>
  );
}
