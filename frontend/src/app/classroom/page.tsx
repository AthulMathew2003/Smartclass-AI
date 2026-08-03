"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  fetchOnboardingStatus,
  OnboardingStatusResponse
} from "../../lib/auth";

export default function ClassroomDashboardPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<OnboardingStatusResponse | null>(null);

  useEffect(() => {
    const init = async () => {
      const st = await fetchOnboardingStatus();
      if (!st) {
        // Not logged in
        router.replace("/login");
        return;
      }
      if (!st.has_organization) {
        // Redirect to onboarding completion page
        router.replace("/register/complete");
        return;
      }
      if (st.multiple_organizations && !localStorage.getItem("activeOrganizationId")) {
        router.replace("/select-org");
        return;
      }
      if (st.organization_id) {
        localStorage.setItem("activeOrganizationId", st.organization_id);
      }
      setStatus(st);
      setLoading(false);
    };

    init();
  }, [router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12 min-h-screen bg-[var(--background)]">
        <div className="w-10 h-10 border-4 border-[var(--primary)] border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8 min-h-screen bg-[var(--background)] text-[var(--on-surface)]">
      {/* Top Banner / Welcome */}
      <div className="p-8 rounded-3xl bg-[var(--surface-container)] border border-[var(--outline-variant)]/20 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[var(--primary)]/10 text-[var(--primary)] text-xs font-bold uppercase tracking-wider">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>{status?.role || "Organization Owner"}</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight">
            {status?.organization_name}
          </h1>
          <p className="text-sm text-[var(--on-surface-variant)]">
            Active Workspace: <strong className="text-[var(--on-surface)]">{status?.workspace_name || "Main Campus"}</strong>
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {status?.multiple_organizations && (
            <button
              onClick={() => {
                localStorage.removeItem("activeOrganizationId");
                router.push("/select-org");
              }}
              className="px-5 py-2.5 rounded-full border border-[var(--outline-variant)]/40 hover:bg-[var(--surface-container-high)] text-xs font-bold transition-all cursor-pointer"
            >
              Switch Organization
            </button>
          )}
          <Link
            href="/register/complete"
            className="px-5 py-2.5 rounded-full border border-[var(--outline-variant)]/40 hover:bg-[var(--surface-container-high)] text-xs font-bold transition-all"
          >
            Edit Institution Settings
          </Link>
        </div>
      </div>

      {/* Metrics Overview Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="p-6 rounded-3xl bg-[var(--surface-container-low)] border border-[var(--outline-variant)]/20 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-[var(--on-surface-variant)] uppercase tracking-wider">Workspaces</span>
            <span className="material-symbols-outlined text-[20px] text-[var(--primary)]">workspaces</span>
          </div>
          <div className="text-3xl font-bold">1</div>
          <p className="text-[11px] text-emerald-500 font-semibold flex items-center gap-1">
            <span className="material-symbols-outlined text-[14px]">check_circle</span>
            <span>{status?.workspace_name}</span>
          </p>
        </div>

        <div className="p-6 rounded-3xl bg-[var(--surface-container-low)] border border-[var(--outline-variant)]/20 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-[var(--on-surface-variant)] uppercase tracking-wider">Organization Status</span>
            <span className="material-symbols-outlined text-[20px] text-emerald-500">verified</span>
          </div>
          <div className="text-xl font-bold text-emerald-500">Active</div>
          <p className="text-[11px] text-[var(--on-surface-variant)] font-semibold">
            Onboarding Completed
          </p>
        </div>

        <div className="p-6 rounded-3xl bg-[var(--surface-container-low)] border border-[var(--outline-variant)]/20 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-[var(--on-surface-variant)] uppercase tracking-wider">System Roles</span>
            <span className="material-symbols-outlined text-[20px] text-[var(--secondary)]">shield_person</span>
          </div>
          <div className="text-3xl font-bold">4</div>
          <p className="text-[11px] text-[var(--on-surface-variant)] font-semibold">
            Owner, Admin, Teacher, Student
          </p>
        </div>

        <div className="p-6 rounded-3xl bg-[var(--surface-container-low)] border border-[var(--outline-variant)]/20 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-[var(--on-surface-variant)] uppercase tracking-wider">Status Readiness</span>
            <span className="material-symbols-outlined text-[20px] text-[var(--primary)]">rocket_launch</span>
          </div>
          <div className="text-xl font-bold text-[var(--primary)]">Ready</div>
          <p className="text-[11px] text-[var(--on-surface-variant)] font-semibold">
            Onboarding Completed
          </p>
        </div>
      </div>

      {/* Quick Actions / Placeholders */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="p-8 rounded-3xl bg-[var(--surface-container)] border border-[var(--outline-variant)]/20 space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-[var(--primary)]/10 text-[var(--primary)] flex items-center justify-center font-bold">
              <span className="material-symbols-outlined text-[20px]">person_add</span>
            </div>
            <div>
              <h3 className="text-base font-bold">Member Management</h3>
              <p className="text-xs text-[var(--on-surface-variant)]">Step 5 Feature</p>
            </div>
          </div>
          <p className="text-xs text-[var(--on-surface-variant)] leading-relaxed">
            Organization owners and admins will create user accounts for Teachers, Students, Parents, and Staff in Step 5.
          </p>
          <div className="pt-2">
            <span className="inline-block px-3 py-1 rounded-full bg-[var(--surface-container-high)] text-[var(--on-surface-variant)] text-[11px] font-bold">
              Coming in Step 5
            </span>
          </div>
        </div>

        <div className="p-8 rounded-3xl bg-[var(--surface-container)] border border-[var(--outline-variant)]/20 space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-[var(--secondary-container)] text-[var(--on-secondary-container)] flex items-center justify-center font-bold">
              <span className="material-symbols-outlined text-[20px]">auto_awesome</span>
            </div>
            <div>
              <h3 className="text-base font-bold">AI Classroom Assistance</h3>
              <p className="text-xs text-[var(--on-surface-variant)]">SmartClass AI Core</p>
            </div>
          </div>
          <p className="text-xs text-[var(--on-surface-variant)] leading-relaxed">
            SmartClass AI modules will integrate with your workspace for automated grading, live class tracking, and intelligent analytics.
          </p>
          <div className="pt-2">
            <span className="inline-block px-3 py-1 rounded-full bg-[var(--surface-container-high)] text-[var(--on-surface-variant)] text-[11px] font-bold">
              Core AI Module
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
