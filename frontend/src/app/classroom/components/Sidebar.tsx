"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { OnboardingStatusResponse } from "../../../lib/auth";

export default function Sidebar({ status }: { status: OnboardingStatusResponse | null }) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  const navItems = [
    { name: "Dashboard", href: "/classroom", icon: "dashboard" },
    { name: "Workspaces", href: status?.has_organization ? "/classroom/workspaces" : "#", icon: "workspaces", disabled: !status?.has_organization },
    { name: "Members", href: status?.has_organization ? "/classroom/members" : "#", icon: "group", disabled: !status?.has_organization },
    { name: "Analytics", href: status?.has_organization ? "/classroom/analytics" : "#", icon: "analytics", disabled: !status?.has_organization },
    { name: "Settings", href: status?.has_organization ? "/classroom/settings" : "#", icon: "settings", disabled: !status?.has_organization },
  ];

  return (
    <aside
      className={`${
        collapsed ? "w-20" : "w-64"
      } transition-all duration-300 ease-in-out bg-[var(--surface-container)] border-r border-[var(--outline-variant)]/20 flex flex-col justify-between p-4 min-h-screen relative z-20`}
    >
      <div>
        {/* Brand Header */}
        <div className="flex items-center justify-between pb-6 border-b border-[var(--outline-variant)]/20 mb-6">
          <Link href="/" className="flex items-center gap-3 overflow-hidden">
            <div className="w-10 h-10 rounded-2xl bg-[var(--primary)] text-[var(--on-primary)] flex items-center justify-center font-bold text-lg shadow-md shrink-0">
              S
            </div>
            {!collapsed && (
              <div className="transition-opacity duration-200">
                <span className="font-bold text-base text-[var(--on-surface)] block tracking-tight">SmartClass AI</span>
                <span className="text-[10px] uppercase font-bold text-[var(--primary)] tracking-widest block">v2.0 Enterprise</span>
              </div>
            )}
          </Link>
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-1.5 rounded-lg hover:bg-[var(--surface-container-high)] text-[var(--on-surface-variant)] transition-colors cursor-pointer"
            title={collapsed ? "Expand Sidebar" : "Collapse Sidebar"}
          >
            <span className="material-symbols-outlined text-[20px]">
              {collapsed ? "chevron_right" : "chevron_left"}
            </span>
          </button>
        </div>

        {/* Institution / Workspace Badge */}
        {!collapsed && status?.has_organization && (
          <div className="mb-6 p-3 rounded-2xl bg-[var(--surface-container-high)] border border-[var(--outline-variant)]/30">
            <span className="text-[10px] uppercase font-bold text-[var(--primary)] tracking-wider block mb-1">
              Active Organization
            </span>
            <p className="text-xs font-bold text-[var(--on-surface)] truncate">{status.organization_name}</p>
            <p className="text-[11px] text-[var(--on-surface-variant)] truncate">
              WS: {status.workspace_name || "Main Campus"}
            </p>
          </div>
        )}

        {/* Navigation Items */}
        <nav className="space-y-1.5">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.name}
                href={item.disabled ? "#" : item.href}
                className={`flex items-center gap-3 px-3.5 py-3 rounded-2xl font-semibold text-xs transition-all duration-150 ${
                  isActive
                    ? "bg-[var(--primary)] text-[var(--on-primary)] shadow-md"
                    : item.disabled
                    ? "opacity-40 cursor-not-allowed text-[var(--on-surface-variant)]"
                    : "text-[var(--on-surface-variant)] hover:bg-[var(--surface-container-high)] hover:text-[var(--on-surface)]"
                }`}
              >
                <span className="material-symbols-outlined text-[20px] shrink-0">{item.icon}</span>
                {!collapsed && <span className="truncate">{item.name}</span>}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer Info */}
      {!collapsed && (
        <div className="pt-4 border-t border-[var(--outline-variant)]/20">
          <div className="flex items-center justify-between text-[11px] text-[var(--on-surface-variant)] font-semibold">
            <span>Status:</span>
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${status?.has_organization ? "bg-emerald-500/10 text-emerald-500" : "bg-amber-500/10 text-amber-500"}`}>
              {status?.has_organization ? "Onboarded" : "Setup Pending"}
            </span>
          </div>
        </div>
      )}
    </aside>
  );
}
