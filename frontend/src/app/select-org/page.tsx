"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchOnboardingStatus, OnboardingStatusResponse } from "../../lib/auth";

export default function SelectOrganizationPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<OnboardingStatusResponse | null>(null);

  useEffect(() => {
    const init = async () => {
      // Clear current choice so we load the raw list of all organizations
      if (typeof window !== "undefined") {
        localStorage.removeItem("activeOrganizationId");
      }
      const st = await fetchOnboardingStatus();
      if (!st || !st.has_organization) {
        router.replace("/login");
        return;
      }
      setStatus(st);
      setLoading(false);
    };

    init();
  }, [router]);

  const handleSelectOrg = (orgId: string) => {
    if (typeof window !== "undefined") {
      localStorage.setItem("activeOrganizationId", orgId);
    }
    router.replace("/classroom");
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--background)] text-[var(--on-surface)] flex items-center justify-center p-6">
        <div className="max-w-md w-full p-8 rounded-3xl bg-white dark:bg-[#1b211e] border border-[var(--outline-variant)]/30 text-center space-y-4 shadow-xl animate-pulse">
          <div className="w-12 h-12 border-4 border-[var(--primary)] border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p className="text-sm font-semibold">Loading your organizations...</p>
        </div>
      </div>
    );
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-6 bg-[var(--background)] text-[var(--on-surface)]">
      <div className="w-full max-w-lg bg-white dark:bg-[#1b211e] border border-[var(--outline-variant)]/30 p-8 md:p-12 rounded-[32px] shadow-2xl space-y-8">
        <header className="text-center space-y-3">
          <div className="w-12 h-12 bg-[var(--primary-fixed)] rounded-full flex items-center justify-center mx-auto">
            <span className="material-symbols-outlined text-[var(--primary)] text-[28px]">domain</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-[var(--primary)]">Select Organization</h1>
          <p className="text-sm text-[var(--on-surface-variant)]">
            Your account is associated with multiple organizations. Select one to proceed to your workspace.
          </p>
        </header>

        {/* List of Organizations */}
        <div className="space-y-4">
          {status?.organizations?.map((org) => (
            <button
              key={org.organization_id}
              onClick={() => handleSelectOrg(org.organization_id)}
              className="w-full text-left p-6 rounded-2xl border border-[var(--outline-variant)]/40 bg-[var(--surface-container)] hover:bg-[var(--surface-container-high)] hover:border-[var(--primary)] transition-all cursor-pointer flex items-center justify-between group"
            >
              <div className="space-y-1">
                <h3 className="font-bold text-lg text-[var(--on-surface)] group-hover:text-[var(--primary)] transition-colors">
                  {org.organization_name}
                </h3>
                <p className="text-xs text-[var(--on-surface-variant)] flex items-center gap-1.5">
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--primary)]"></span>
                  <span>Role: <strong>{org.role_name || "Member"}</strong></span>
                </p>
              </div>
              <span className="material-symbols-outlined text-[var(--on-surface-variant)] group-hover:text-[var(--primary)] transition-colors transform group-hover:translate-x-1 duration-200">
                arrow_forward
              </span>
            </button>
          ))}
        </div>

        <footer className="text-center pt-2">
          <button
            onClick={() => {
              if (typeof window !== "undefined") {
                localStorage.clear();
              }
              router.replace("/login");
            }}
            className="text-sm font-semibold text-[var(--primary)] hover:underline"
          >
            Sign in with a different account
          </button>
        </footer>
      </div>
    </main>
  );
}
