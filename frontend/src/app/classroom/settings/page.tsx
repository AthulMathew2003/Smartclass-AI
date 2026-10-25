"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { fetchCurrentUser, fetchOnboardingStatus, UserProfile, OnboardingStatusResponse } from "@/lib/auth";
import { usePermissions, hasPermission, isPermissionsLoaded } from "@/lib/permissions";
import ForbiddenState from "../components/ForbiddenState";

export default function SettingsHubPage() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [status, setStatus] = useState<OnboardingStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const { hasPermission: checkPerm, isLoaded: permLoaded } = usePermissions();

  useEffect(() => {
    const init = async () => {
      try {
        const [userData, statusData] = await Promise.all([
          fetchCurrentUser(),
          fetchOnboardingStatus()
        ]);
        setUser(userData);
        setStatus(statusData);
      } catch (err) {
        console.error("Failed to load settings data", err);
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  if (loading || !permLoaded) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-10 h-10 border-4 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  // Permission Guard
  if (!checkPerm("settings.manage") && !checkPerm("organization.update")) {
    return (
      <ForbiddenState message="You do not have administrative permissions to view or manage system settings." />
    );
  }

  const settingsCards = [
    {
      title: "Roles & Permissions",
      desc: "Configure role-based access control, create custom institutional roles, and set granular resource privileges.",
      icon: "admin_panel_settings",
      href: "/classroom/settings/roles",
      badge: "RBAC Governance",
      permission: "member.update",
      primary: true,
    },
    {
      title: "Organization Profile",
      desc: "Update institution name, regional location, contact information, timezone, and academic configuration.",
      icon: "corporate_fare",
      href: "/register/complete",
      badge: "Institutional Info",
      permission: "organization.update",
      primary: false,
    },
    {
      title: "Academic Workspaces",
      desc: "Create and manage departmental partitions, schools, campuses, and academic cohorts.",
      icon: "workspaces",
      href: "/classroom/workspaces",
      badge: "Workspaces",
      permission: "workspace.read",
      primary: false,
    },
    {
      title: "Members & Staff",
      desc: "Invite educators, students, and staff members, manage active memberships and account assignments.",
      icon: "group",
      href: "/classroom/members",
      badge: "Directory",
      permission: "member.read",
      primary: false,
    },
  ];

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      {/* ── Page Header ────────────────────────────────────────── */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="w-2.5 h-2.5 rounded-full bg-[var(--primary)]" />
          <span className="text-xs font-bold uppercase tracking-wider text-[var(--on-surface-variant)]">
            Administration & Governance
          </span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-[var(--on-surface)]">
          System Settings
        </h1>
        <p className="text-sm text-[var(--on-surface-variant)] mt-1">
          Manage institution configuration, security roles, academic workspaces, and administrative access.
        </p>
      </div>

      {/* ── Organization Overview Card ────────────────────────── */}
      <div
        className="p-6 rounded-3xl border space-y-4"
        style={{
          backgroundColor: "var(--surface-container)",
          borderColor: "var(--outline-variant)",
        }}
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div
              className="w-12 h-12 rounded-2xl flex items-center justify-center text-lg font-bold shadow-md"
              style={{
                backgroundColor: "var(--primary)",
                color: "var(--on-primary)",
              }}
            >
              <span className="material-symbols-outlined text-[24px]">school</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-[var(--on-surface)]">
                  {status?.organization_name || "Institution Settings"}
                </h2>
                <span
                  className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/15 text-emerald-400"
                >
                  Active
                </span>
              </div>
              <p className="text-xs text-[var(--on-surface-variant)] mt-0.5">
                Current Workspace: <span className="font-semibold text-[var(--on-surface)]">{status?.workspace_name || "Main Campus"}</span>
                {status?.role && (
                  <span className="ml-2 font-medium">
                    &bull; Your Role: <span className="font-semibold text-[var(--primary)]">{status.role}</span>
                  </span>
                )}
              </p>
            </div>
          </div>
          {checkPerm("organization.update") && (
            <Link
              href="/register/complete"
              className="px-4 py-2 rounded-xl text-xs font-bold inline-flex items-center gap-2 transition-all hover:scale-95 border self-start sm:self-auto"
              style={{
                backgroundColor: "var(--surface)",
                color: "var(--primary)",
                borderColor: "var(--outline-variant)",
              }}
            >
              <span className="material-symbols-outlined text-[16px]">edit</span>
              Edit Organization Details
            </Link>
          )}
        </div>
      </div>

      {/* ── Navigation Cards Grid ────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {settingsCards
          .filter((card) => !card.permission || checkPerm(card.permission))
          .map((card) => (
            <Link
              key={card.title}
              href={card.href}
              className="group p-6 rounded-3xl border transition-all duration-200 hover:shadow-lg hover:border-[var(--primary)] flex flex-col justify-between"
              style={{
                backgroundColor: "var(--surface-container-low)",
                borderColor: "var(--outline-variant)",
              }}
            >
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div
                    className="w-11 h-11 rounded-2xl flex items-center justify-center transition-transform group-hover:scale-105"
                    style={{
                      backgroundColor: card.primary ? "var(--tertiary-fixed)" : "rgba(255,255,255,0.06)",
                      color: card.primary ? "var(--on-tertiary-fixed)" : "var(--primary)",
                    }}
                  >
                    <span className="material-symbols-outlined text-[24px]">{card.icon}</span>
                  </div>
                  <span
                    className="px-2.5 py-1 rounded-full text-[10px] font-bold"
                    style={{
                      backgroundColor: "rgba(255,255,255,0.06)",
                      color: "var(--on-surface-variant)",
                    }}
                  >
                    {card.badge}
                  </span>
                </div>

                <div>
                  <h3 className="text-base font-bold text-[var(--on-surface)] group-hover:text-[var(--primary)] transition-colors">
                    {card.title}
                  </h3>
                  <p className="text-xs text-[var(--on-surface-variant)] mt-1.5 leading-relaxed">
                    {card.desc}
                  </p>
                </div>
              </div>

              <div className="mt-6 pt-4 border-t flex items-center justify-between text-xs font-semibold" style={{ borderColor: "rgba(255,255,255,0.05)" }}>
                <span className="text-[var(--on-surface-variant)] group-hover:text-[var(--on-surface)] transition-colors">
                  Open module
                </span>
                <span className="material-symbols-outlined text-[18px] text-[var(--primary)] transform group-hover:translate-x-1 transition-transform">
                  arrow_forward
                </span>
              </div>
            </Link>
          ))}
      </div>
    </div>
  );
}
