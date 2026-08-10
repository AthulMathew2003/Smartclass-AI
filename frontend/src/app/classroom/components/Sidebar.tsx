"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { OnboardingStatusResponse } from "../../../lib/auth";
import { usePermissions } from "../../../lib/permissions";

/**
 * Centralized navigation configuration.
 * Each item optionally requires a permission string.
 * Items render only when: permission is null OR hasPermission(permission) is true.
 *
 * Permission strings correspond to the backend RBAC permission model.
 * Do NOT use role names here (e.g. "Admin", "Owner").
 */
const NAV_CONFIG = [
  { name: "Dashboard",           href: "/classroom",               icon: "dashboard",            permission: null },
  { name: "Workspaces",          href: "/classroom/workspaces",     icon: "workspaces",           permission: "workspace.read" },
  { name: "Members",             href: "/classroom/members",        icon: "group",                permission: "member.read" },
  { name: "Roles & Permissions", href: "/classroom/settings/roles", icon: "admin_panel_settings", permission: "member.update" },
  { name: "Analytics",           href: "/classroom/analytics",      icon: "analytics",            permission: "analytics.view" },
  { name: "Settings",            href: "/classroom/settings",       icon: "settings",             permission: "settings.manage" },
];

export default function Sidebar({ status }: { status: OnboardingStatusResponse | null }) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const { hasPermission, isLoaded: permLoaded } = usePermissions();

  const hasOrg = status?.has_organization || (status?.organizations && status.organizations.length > 0);

  // Filter nav items by organization presence and permission
  const visibleItems = NAV_CONFIG.filter((item) => {
    // Dashboard is always visible
    if (item.permission === null) return true;
    // Hide all org-gated items if no org
    if (!hasOrg) return false;
    // While permissions are loading, hide permission-gated items to prevent flash
    if (!permLoaded) return false;
    // Permission check
    return hasPermission(item.permission);
  });

  return (
    <aside
      className={`${
        collapsed ? "w-20" : "w-64"
      } transition-all duration-300 ease-in-out flex-shrink-0 flex flex-col min-h-screen relative z-20`}
      style={{ backgroundColor: "var(--primary)" }}
    >
      {/* Decorative orb */}
      <div
        className="absolute -top-16 -right-16 w-48 h-48 rounded-full opacity-10 pointer-events-none"
        style={{ backgroundColor: "var(--tertiary-fixed)" }}
      />

      {/* Brand Header */}
      <div className={`flex items-center justify-between py-8 ${collapsed ? "px-4" : "px-6"}`}>
        <Link href="/" className="flex items-center gap-3 overflow-hidden">
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center font-bold text-base shrink-0 shadow-lg"
            style={{ backgroundColor: "var(--tertiary-fixed)", color: "var(--on-tertiary-fixed)" }}
          >
            S
          </div>
          {!collapsed && (
            <div className="transition-opacity duration-200">
              <span className="font-bold text-base block tracking-tight" style={{ color: "var(--on-primary)" }}>
                SmartClass
              </span>
            </div>
          )}
        </Link>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1.5 rounded-lg transition-colors cursor-pointer"
          style={{ color: "rgba(255,255,255,0.5)" }}
          onMouseEnter={e => (e.currentTarget.style.backgroundColor = "rgba(255,255,255,0.08)")}
          onMouseLeave={e => (e.currentTarget.style.backgroundColor = "transparent")}
          title={collapsed ? "Expand Sidebar" : "Collapse Sidebar"}
        >
          <span className="material-symbols-outlined text-[20px]">
            {collapsed ? "chevron_right" : "chevron_left"}
          </span>
        </button>
      </div>

      {/* Institution badge */}
      {!collapsed && hasOrg && (
        <div className={`mx-4 mb-6 p-3 rounded-2xl`} style={{ backgroundColor: "rgba(255,255,255,0.08)" }}>
          <span className="text-[9px] uppercase font-bold tracking-widest block mb-1" style={{ color: "var(--tertiary-fixed)" }}>
            Active Organization
          </span>
          <p className="text-xs font-bold truncate" style={{ color: "var(--on-primary)" }}>{status?.organization_name}</p>
          <p className="text-[11px] truncate" style={{ color: "rgba(255,255,255,0.5)" }}>
            WS: {status?.workspace_name || "Main Campus"}
          </p>
        </div>
      )}

      {/* Navigation — permission-aware */}
      <nav className={`flex-1 space-y-1 mt-2 ${collapsed ? "px-2" : "px-3"}`}>
        {visibleItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center gap-3 py-3 rounded-xl font-semibold text-[13px] transition-all duration-200 ${
                collapsed ? "px-3 justify-center" : "px-4"
              } ${
                isActive
                  ? "translate-x-0.5"
                  : "cursor-pointer"
              }`}
              style={{
                backgroundColor: isActive ? "var(--tertiary-fixed)" : "transparent",
                color: isActive
                  ? "var(--on-tertiary-fixed)"
                  : "rgba(255,255,255,0.65)",
              }}
              onMouseEnter={e => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = "rgba(255,255,255,0.08)";
                  e.currentTarget.style.color = "rgba(255,255,255,0.9)";
                }
              }}
              onMouseLeave={e => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = "transparent";
                  e.currentTarget.style.color = "rgba(255,255,255,0.65)";
                }
              }}
            >
              <span className="material-symbols-outlined text-[20px] shrink-0">{item.icon}</span>
              {!collapsed && <span className="truncate">{item.name}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Footer CTA — only show for users with classroom.create permission */}
      {!collapsed && hasPermission("classroom.create") && (
        <div className="px-4 pb-6 mt-auto space-y-3">
          <button
            className="w-full py-3 rounded-full font-bold text-sm transition-all hover:scale-95"
            style={{
              backgroundColor: "var(--secondary-container)",
              color: "var(--on-secondary-container)",
            }}
          >
            New Lesson
          </button>
          <div
            className="flex items-center justify-between pt-3 border-t"
            style={{ borderColor: "rgba(255,255,255,0.1)" }}
          >
            <span className="text-[11px] font-semibold" style={{ color: "rgba(255,255,255,0.4)" }}>Status</span>
            <span
              className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                hasOrg ? "bg-emerald-500/15 text-emerald-400" : "bg-amber-500/15 text-amber-400"
              }`}
            >
              {hasOrg ? "Onboarded" : "Setup Pending"}
            </span>
          </div>
        </div>
      )}

      {/* Footer status for users without classroom.create */}
      {!collapsed && !hasPermission("classroom.create") && (
        <div className="px-4 pb-6 mt-auto">
          <div
            className="flex items-center justify-between pt-3 border-t"
            style={{ borderColor: "rgba(255,255,255,0.1)" }}
          >
            <span className="text-[11px] font-semibold" style={{ color: "rgba(255,255,255,0.4)" }}>Status</span>
            <span
              className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                hasOrg ? "bg-emerald-500/15 text-emerald-400" : "bg-amber-500/15 text-amber-400"
              }`}
            >
              {hasOrg ? "Onboarded" : "Setup Pending"}
            </span>
          </div>
        </div>
      )}
    </aside>
  );
}
