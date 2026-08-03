"use client";

import React from "react";
import { UserProfile, OnboardingStatusResponse, logoutUser } from "../../../lib/auth";
import { useRouter } from "next/navigation";

export default function Header({
  user,
  status
}: {
  user: UserProfile | null;
  status: OnboardingStatusResponse | null;
}) {
  const router = useRouter();

  const handleLogout = async () => {
    await logoutUser();
    router.push("/login");
  };

  return (
    <header className="h-16 px-6 border-b border-[var(--outline-variant)]/20 bg-[var(--surface-container)]/60 backdrop-blur-xl flex items-center justify-between sticky top-0 z-10">
      {/* Search Bar */}
      <div className="flex items-center gap-3 w-72">
        <div className="relative w-full">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-[18px] text-[var(--on-surface-variant)]">
            search
          </span>
          <input
            type="text"
            placeholder="Search classes, members..."
            className="w-full pl-9 pr-4 py-2 bg-[var(--surface-container-high)] border border-transparent focus:border-[var(--primary)] rounded-full text-xs text-[var(--on-surface)] outline-none transition-all placeholder:text-[var(--on-surface-variant)]/60"
          />
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-4">
        {status?.has_organization && (
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full bg-[var(--primary)]/10 text-[var(--primary)] text-xs font-semibold">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>{status.organization_name}</span>
          </div>
        )}

        <div className="h-6 w-[1px] bg-[var(--outline-variant)]/30 hidden md:block"></div>

        {/* User Info */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-[var(--primary)] text-[var(--on-primary)] flex items-center justify-center font-bold text-xs shadow">
            {user?.first_name?.charAt(0) || user?.email?.charAt(0) || "U"}
          </div>
          <div className="hidden sm:block text-left">
            <span className="text-xs font-bold text-[var(--on-surface)] block leading-tight">
              {user?.first_name ? `${user.first_name} ${user.last_name || ""}` : user?.email}
            </span>
            <span className="text-[10px] text-[var(--on-surface-variant)] font-semibold block">
              {status?.role || "Organization Owner"}
            </span>
          </div>
        </div>

        {/* Logout */}
        <button
          onClick={handleLogout}
          className="p-2 rounded-full border border-[var(--outline-variant)]/40 hover:bg-[var(--surface-container-high)] text-[var(--on-surface-variant)] hover:text-[var(--on-surface)] transition-all cursor-pointer"
          title="Sign Out"
        >
          <span className="material-symbols-outlined text-[18px]">logout</span>
        </button>
      </div>
    </header>
  );
}
