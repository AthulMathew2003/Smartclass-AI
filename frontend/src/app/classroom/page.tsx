"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  fetchOnboardingStatus,
  fetchUserMemberships,
  OnboardingStatusResponse,
} from "../../lib/auth";
import { usePermissions } from "../../lib/permissions";

// ─── Circular Progress Widget ───────────────────────────────────────────────
function CircularProgress({ value, label }: { value: number; label: string }) {
  const r = 45;
  const circ = 2 * Math.PI * r;
  const offset = circ - (value / 100) * circ;
  return (
    <div className="relative w-44 h-44 flex items-center justify-center">
      <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r={r} fill="none" stroke="currentColor" strokeOpacity="0.12" strokeWidth="8" />
        <circle
          cx="50" cy="50" r={r} fill="none"
          stroke="currentColor"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          strokeLinecap="round"
          strokeWidth="8"
          style={{ transition: "stroke-dashoffset 0.8s ease" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-4xl font-bold leading-none">{value}%</span>
        <span className="text-[11px] font-semibold opacity-60 mt-1">{label}</span>
      </div>
    </div>
  );
}

// ─── Metric Card ─────────────────────────────────────────────────────────────
function MetricCard({
  icon,
  label,
  value,
  sub,
  iconColor,
  iconBg,
}: {
  icon: string;
  label: string;
  value: string;
  sub: string;
  iconColor: string;
  iconBg: string;
}) {
  return (
    <div
      className="p-6 rounded-2xl flex flex-col gap-3 border transition-all hover:-translate-y-0.5 duration-200"
      style={{ backgroundColor: "var(--surface-container-low)", borderColor: "var(--outline-variant)" }}
    >
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-bold uppercase tracking-wider" style={{ color: "var(--on-surface-variant)" }}>
          {label}
        </span>
        <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ backgroundColor: iconBg }}>
          <span className="material-symbols-outlined text-[20px]" style={{ color: iconColor }}>
            {icon}
          </span>
        </div>
      </div>
      <div className="text-3xl font-bold" style={{ color: "var(--on-surface)" }}>{value}</div>
      <p className="text-[11px] font-semibold" style={{ color: "var(--on-surface-variant)" }}>{sub}</p>
    </div>
  );
}

// ─── Quick Action Card ────────────────────────────────────────────────────────
function ActionCard({
  icon,
  title,
  subtitle,
  description,
  badge,
  iconBg,
  iconColor,
}: {
  icon: string;
  title: string;
  subtitle: string;
  description: string;
  badge: string;
  iconBg: string;
  iconColor: string;
}) {
  return (
    <div
      className="p-7 rounded-2xl flex flex-col gap-4 border transition-all hover:-translate-y-0.5 duration-200"
      style={{ backgroundColor: "var(--surface-container)", borderColor: "var(--outline-variant)" }}
    >
      <div className="flex items-start gap-4">
        <div
          className="w-11 h-11 rounded-2xl flex items-center justify-center shrink-0"
          style={{ backgroundColor: iconBg }}
        >
          <span className="material-symbols-outlined text-[22px]" style={{ color: iconColor }}>{icon}</span>
        </div>
        <div>
          <h3 className="text-sm font-bold leading-tight" style={{ color: "var(--on-surface)" }}>{title}</h3>
          <p className="text-[11px] font-semibold mt-0.5" style={{ color: "var(--on-surface-variant)" }}>{subtitle}</p>
        </div>
      </div>
      <p className="text-xs leading-relaxed" style={{ color: "var(--on-surface-variant)" }}>{description}</p>
      <div className="pt-1">
        <span
          className="inline-block px-3 py-1 rounded-full text-[10px] font-bold"
          style={{
            backgroundColor: "var(--surface-container-high)",
            color: "var(--on-surface-variant)",
          }}
        >
          {badge}
        </span>
      </div>
    </div>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────────────
export default function ClassroomDashboardPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<OnboardingStatusResponse | null>(null);
  const { hasPermission, hasAnyPermission } = usePermissions();

  useEffect(() => {
    const init = async () => {
      const st = await fetchOnboardingStatus();
      if (!st) {
        router.replace("/login");
        return;
      }

      const mems = await fetchUserMemberships();
      const hasMemberships = mems && mems.length > 0;

      if (!st.has_organization && !hasMemberships) {
        router.replace("/register/complete");
        return;
      }

      if (hasMemberships && !localStorage.getItem("activeOrganizationId")) {
        router.replace("/select-org");
        return;
      }

      const activeOrgId =
        localStorage.getItem("activeOrganizationId") ||
        (mems && mems.length > 0 ? mems[0].organization_id : null);
      if (activeOrgId) localStorage.setItem("activeOrganizationId", activeOrgId);

      const activeMem = mems?.find((m) => m.organization_id === activeOrgId);

      setStatus({
        has_organization: st.has_organization,
        organization_id: activeMem?.organization_id,
        organization_name: activeMem?.organization_name,
        workspace_name: activeMem?.workspace_name,
        role: activeMem?.role_name,
        multiple_organizations: mems ? mems.length > 1 : false,
        organizations: mems,
      });
      setLoading(false);
    };
    init();
  }, [router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div
          className="w-10 h-10 border-4 border-t-transparent rounded-full animate-spin"
          style={{ borderColor: "var(--primary)", borderTopColor: "transparent" }}
        />
      </div>
    );
  }

  return (
    <div className="space-y-8 relative overflow-hidden">
      {/* Atmospheric background orb */}
      <svg
        className="absolute -right-24 -top-24 w-[480px] h-[480px] pointer-events-none opacity-20"
        viewBox="0 0 200 200"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M44.7,-76.4C58.1,-69.2,69.2,-58.1,76.4,-44.7C83.6,-31.3,86.9,-15.7,85.2,-0.9C83.6,13.8,77,27.7,69.1,40.4C61.2,53,52.1,64.3,40.5,72.4C28.8,80.5,14.4,85.4,-0.6,86.4C-15.6,87.4,-31.1,84.4,-44.8,77.3C-58.4,70.2,-70.2,59,-77.3,45.4C-84.4,31.7,-86.7,15.9,-86.1,0.4C-85.4,-15.1,-81.8,-30.2,-74.1,-43.3C-66.5,-56.3,-54.9,-67.2,-41.4,-74.3C-27.9,-81.4,-14,-84.7,0.4,-85.4C14.7,-86.1,29.4,-84.1,44.7,-76.4Z"
          fill="var(--tertiary-fixed)"
          transform="translate(100 100)"
        />
      </svg>

      {/* ── Hero Banner ───────────────────────────────────── */}
      <div
        className="relative rounded-3xl overflow-hidden p-8 md:p-10 flex flex-col md:flex-row md:items-center justify-between gap-6"
        style={{ backgroundColor: "var(--primary-container)" }}
      >
        {/* Decorative bubble */}
        <div
          className="absolute -right-16 -bottom-16 w-64 h-64 rounded-full opacity-10 pointer-events-none"
          style={{ backgroundColor: "var(--tertiary-fixed)" }}
        />
        <div
          className="absolute right-8 top-1/2 -translate-y-1/2 hidden lg:flex w-32 h-32 rounded-full items-center justify-center text-6xl font-black select-none"
          style={{ backgroundColor: "var(--secondary-container)", color: "var(--on-secondary-container)" }}
        >
          ✴
        </div>

        <div className="relative z-10 space-y-3">
          <span
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-[11px] font-bold uppercase tracking-wider"
            style={{
              backgroundColor: "var(--secondary-container)",
              color: "var(--on-secondary-container)",
            }}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            {status?.role || "Organization Owner"}
          </span>
          <h1 className="text-3xl md:text-4xl font-bold tracking-tight leading-tight max-w-lg" style={{ color: "var(--on-primary-container)" }}>
            {status?.organization_name ?? "Welcome to SmartClass AI"}
          </h1>
          <p className="text-sm" style={{ color: "var(--on-primary-container)", opacity: 0.75 }}>
            Active Workspace:{" "}
            <strong style={{ opacity: 1, color: "var(--on-primary-container)" }}>
              {status?.workspace_name || "Main Campus"}
            </strong>
          </p>
        </div>

        <div className="relative z-10 flex items-center gap-3 shrink-0 flex-wrap">
          {status?.multiple_organizations && (
            <button
              onClick={() => {
                localStorage.removeItem("activeOrganizationId");
                router.push("/select-org");
              }}
              className="px-5 py-2.5 rounded-full text-xs font-bold transition-all hover:scale-95 cursor-pointer border"
              style={{
                borderColor: "var(--outline-variant)",
                backgroundColor: "var(--surface)",
                color: "var(--on-surface)",
              }}
            >
              Switch Organization
            </button>
          )}
          {hasAnyPermission(["organization.update", "settings.manage"]) && (
            <Link
              href="/register/complete"
              className="px-5 py-2.5 rounded-full text-xs font-bold transition-all hover:scale-95 border"
              style={{
                backgroundColor: "var(--surface)",
                color: "var(--primary)",
                borderColor: "var(--outline-variant)",
              }}
            >
              Edit Settings
            </Link>
          )}
        </div>
      </div>

      {/* ── Metrics + Progress Bento Row ─────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Metrics grid */}
        <div className="lg:col-span-8 grid grid-cols-2 sm:grid-cols-4 gap-4">
          <MetricCard
            icon="workspaces"
            label="Workspaces"
            value="1"
            sub={status?.workspace_name || "Main Campus"}
            iconColor="var(--primary)"
            iconBg="rgba(21,69,57,0.1)"
          />
          <MetricCard
            icon="verified"
            label="Org Status"
            value="Active"
            sub="Onboarding Completed"
            iconColor="#10b981"
            iconBg="rgba(16,185,129,0.1)"
          />
          <MetricCard
            icon="shield_person"
            label="System Roles"
            value="6"
            sub="Owner · Admin · Teacher · Student · Parent · Staff"
            iconColor="var(--secondary)"
            iconBg="rgba(151,72,15,0.1)"
          />
          <MetricCard
            icon="rocket_launch"
            label="Readiness"
            value="Ready"
            sub="Foundation Complete"
            iconColor="var(--primary)"
            iconBg="rgba(21,69,57,0.1)"
          />
        </div>

        {/* Score Progress */}
        <div
          className="lg:col-span-4 rounded-2xl p-8 flex flex-col items-center justify-center text-center"
          style={{ backgroundColor: "var(--tertiary-fixed)", color: "var(--on-tertiary-fixed)" }}
        >
          <p className="text-[11px] font-bold uppercase tracking-widest mb-5" style={{ color: "var(--on-tertiary-fixed)", opacity: 0.6 }}>
            RBAC Coverage
          </p>
          <CircularProgress value={86} label="permissions mapped" />
          <p className="mt-6 text-xs font-semibold leading-snug max-w-[180px]" style={{ opacity: 0.8 }}>
            21 permissions across 6 global system roles
          </p>
        </div>
      </div>

      {/* ── Quick Actions Bento Row ───────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-6 gap-6">
        {/* AI Insight widget */}
        <div
          className="md:col-span-2 rounded-2xl p-7 flex flex-col justify-between"
          style={{ backgroundColor: "#E6E0FF" }}
        >
          <div className="space-y-3">
            <div
              className="w-10 h-10 bg-white rounded-full flex items-center justify-center"
              style={{ boxShadow: "0 2px 8px rgba(0,0,0,0.08)" }}
            >
              <span className="material-symbols-outlined text-[20px]" style={{ color: "var(--primary)" }}>
                auto_awesome
              </span>
            </div>
            <h4 className="text-xl font-bold" style={{ color: "var(--on-surface)" }}>AI Insights</h4>
            <p className="text-sm leading-relaxed" style={{ color: "var(--on-surface-variant)" }}>
              AI-assisted classroom tracking and grading will integrate with your workspace automatically.
            </p>
          </div>
          <button
            className="mt-6 flex items-center gap-2 text-sm font-bold transition-opacity hover:opacity-70"
            style={{ color: "var(--primary)" }}
          >
            View Plan <span className="material-symbols-outlined text-[18px]">trending_up</span>
          </button>
        </div>

        {/* Pending Assignments / Members card — only if user can view members */}
        {hasPermission("member.read") && (
          <div
            className="md:col-span-2 rounded-2xl p-7 flex flex-col justify-between"
            style={{ backgroundColor: "var(--tertiary-fixed)" }}
          >
            <div className="space-y-3">
              <div className="w-10 h-10 bg-white rounded-full flex items-center justify-center" style={{ boxShadow: "0 2px 8px rgba(0,0,0,0.08)" }}>
                <span className="material-symbols-outlined text-[20px]" style={{ color: "var(--tertiary)" }}>task</span>
              </div>
              <h4 className="text-xl font-bold" style={{ color: "var(--on-tertiary-fixed)" }}>Members</h4>
              <p className="text-sm leading-relaxed" style={{ color: "var(--on-tertiary-fixed)", opacity: 0.75 }}>
                Invite Teachers, Students, Parents and Staff to your organization.
              </p>
            </div>
            <Link
              href="/classroom/members"
              className="mt-6 inline-block px-5 py-2 rounded-full text-[11px] font-bold transition-all hover:scale-95 text-center"
              style={{ backgroundColor: "var(--on-tertiary-fixed)", color: "var(--on-tertiary)" }}
            >
              View Members
            </Link>
          </div>
        )}

        {/* If user can't view members, replace with a spacer card */}
        {!hasPermission("member.read") && (
          <div
            className="md:col-span-2 rounded-2xl p-7 flex flex-col justify-between"
            style={{ backgroundColor: "var(--tertiary-fixed)" }}
          >
            <div className="space-y-3">
              <div className="w-10 h-10 bg-white rounded-full flex items-center justify-center" style={{ boxShadow: "0 2px 8px rgba(0,0,0,0.08)" }}>
                <span className="material-symbols-outlined text-[20px]" style={{ color: "var(--tertiary)" }}>school</span>
              </div>
              <h4 className="text-xl font-bold" style={{ color: "var(--on-tertiary-fixed)" }}>Learning Hub</h4>
              <p className="text-sm leading-relaxed" style={{ color: "var(--on-tertiary-fixed)", opacity: 0.75 }}>
                Access your courses, assignments, and learning materials.
              </p>
            </div>
          </div>
        )}

        {/* Resource Spotlight — wide */}
        <div
          className="md:col-span-2 rounded-2xl p-7 relative overflow-hidden flex flex-col justify-between"
          style={{ backgroundColor: "var(--surface-container-high)" }}
        >
          <div className="space-y-3">
            <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ backgroundColor: "var(--secondary-fixed)" }}>
              <span className="material-symbols-outlined text-[20px]" style={{ color: "var(--secondary)" }}>library_books</span>
            </div>
            <h4 className="text-xl font-bold" style={{ color: "var(--on-surface)" }}>Resources</h4>
            <p className="text-sm leading-relaxed" style={{ color: "var(--on-surface-variant)" }}>
              Manage course materials, assets and workspaces for your institution.
            </p>
          </div>
          <button
            className="mt-6 border-2 px-5 py-2 rounded-full text-[11px] font-bold transition-all hover:scale-95"
            style={{ borderColor: "var(--primary)", color: "var(--primary)" }}
          >
            Explore Workspaces
          </button>
        </div>
      </div>

      {/* ── Feature Cards ─────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <ActionCard
          icon="person_add"
          title="Member Management"
          subtitle="Step 5 Feature"
          description="Organization owners and admins will create user accounts for Teachers, Students, Parents, and Staff in Step 5."
          badge="Coming in Step 5"
          iconBg="rgba(21,69,57,0.1)"
          iconColor="var(--primary)"
        />
        <ActionCard
          icon="auto_awesome"
          title="AI Classroom Assistance"
          subtitle="SmartClass AI Core"
          description="SmartClass AI modules will integrate with your workspace for automated grading, live class tracking, and intelligent analytics."
          badge="Core AI Module"
          iconBg="var(--secondary-fixed)"
          iconColor="var(--secondary)"
        />
      </div>

      {/* ── Student Progress Table ────────────────────────── */}
      <section>
        <div className="flex justify-between items-end mb-6">
          <div>
            <h3 className="text-xl font-bold" style={{ color: "var(--on-surface)" }}>Member Progress</h3>
            <p className="text-xs mt-1" style={{ color: "var(--on-surface-variant)" }}>Monitoring individual growth tracks</p>
          </div>
          <div className="flex gap-2">
            <button
              className="w-9 h-9 rounded-xl flex items-center justify-center transition-colors"
              style={{ backgroundColor: "var(--surface-container)", color: "var(--on-surface-variant)" }}
              onMouseEnter={e => (e.currentTarget.style.backgroundColor = "var(--surface-container-high)")}
              onMouseLeave={e => (e.currentTarget.style.backgroundColor = "var(--surface-container)")}
            >
              <span className="material-symbols-outlined text-[18px]">filter_list</span>
            </button>
            <button
              className="w-9 h-9 rounded-xl flex items-center justify-center transition-colors"
              style={{ backgroundColor: "var(--surface-container)", color: "var(--on-surface-variant)" }}
              onMouseEnter={e => (e.currentTarget.style.backgroundColor = "var(--surface-container-high)")}
              onMouseLeave={e => (e.currentTarget.style.backgroundColor = "var(--surface-container)")}
            >
              <span className="material-symbols-outlined text-[18px]">download</span>
            </button>
          </div>
        </div>

        <div
          className="rounded-2xl overflow-hidden border"
          style={{ borderColor: "var(--outline-variant)" }}
        >
          <table className="w-full text-left border-collapse">
            <thead>
              <tr style={{ backgroundColor: "var(--surface-container)" }}>
                {["Member", "Role", "Status", "Activity", ""].map((col) => (
                  <th
                    key={col}
                    className="px-6 py-4 text-[11px] font-bold uppercase tracking-wider"
                    style={{ color: "var(--on-surface-variant)" }}
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody style={{ backgroundColor: "var(--surface)" }}>
              {[
                { name: "Organization Owner", role: "Owner", status: "Active", pct: 95, color: "var(--primary)", bg: "var(--primary-fixed)" },
                { name: "New Members", role: "—", status: "Pending", pct: 0, color: "var(--secondary)", bg: "var(--secondary-fixed)" },
              ].map((row, i) => (
                <tr
                  key={i}
                  className="transition-colors border-t"
                  style={{ borderColor: "var(--outline-variant)" }}
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = "var(--surface-container-low)")}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = "transparent")}
                >
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div
                        className="w-9 h-9 rounded-full shrink-0 flex items-center justify-center text-xs font-bold"
                        style={{ backgroundColor: row.bg, color: "var(--on-surface)" }}
                      >
                        {row.name[0]}
                      </div>
                      <span className="text-sm font-bold" style={{ color: "var(--on-surface)" }}>{row.name}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className="px-3 py-1 rounded-full text-[11px] font-bold"
                      style={{ backgroundColor: "var(--surface-container)", color: "var(--on-surface-variant)" }}
                    >
                      {row.role}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="flex items-center gap-2 text-sm">
                      <span
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: row.status === "Active" ? "#10b981" : "var(--outline)" }}
                      />
                      <span style={{ color: "var(--on-surface)" }}>{row.status}</span>
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div
                      className="w-32 h-2 rounded-full overflow-hidden"
                      style={{ backgroundColor: "var(--surface-container-highest)" }}
                    >
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${row.pct}%`, backgroundColor: row.color }}
                      />
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      className="material-symbols-outlined text-[20px] transition-colors"
                      style={{ color: "var(--outline)" }}
                      onMouseEnter={e => (e.currentTarget.style.color = "var(--primary)")}
                      onMouseLeave={e => (e.currentTarget.style.color = "var(--outline)")}
                    >
                      more_vert
                    </button>
                  </td>
                </tr>
              ))}

              {/* Empty state row — only show members invite if user has permission */}
              {hasPermission("member.read") && (
                <tr
                  className="border-t"
                  style={{ borderColor: "var(--outline-variant)" }}
                >
                  <td colSpan={5} className="px-6 py-8 text-center">
                    <div className="flex flex-col items-center gap-2">
                      <span className="material-symbols-outlined text-[32px]" style={{ color: "var(--outline-variant)" }}>group_add</span>
                      <p className="text-xs font-semibold" style={{ color: "var(--on-surface-variant)" }}>
                        Invite members to see them here
                      </p>
                      <Link
                        href="/classroom/members"
                        className="mt-1 px-4 py-1.5 rounded-full text-[11px] font-bold transition-all hover:scale-95"
                        style={{ backgroundColor: "var(--primary)", color: "var(--on-primary)" }}
                      >
                        Go to Members
                      </Link>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
