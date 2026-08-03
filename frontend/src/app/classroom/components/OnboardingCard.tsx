"use client";

import React from "react";
import Link from "next/link";

export default function OnboardingCard() {
  return (
    <div className="p-8 md:p-12 rounded-3xl bg-gradient-to-br from-[var(--surface-container-high)] via-[var(--surface-container)] to-[var(--surface-container-low)] border border-[var(--primary)]/30 shadow-2xl space-y-8 relative overflow-hidden group">
      {/* Background Glow */}
      <div className="absolute -top-24 -right-24 w-72 h-72 bg-[var(--primary)]/10 rounded-full blur-3xl group-hover:bg-[var(--primary)]/20 transition-all duration-500"></div>

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
        <div className="space-y-3 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[var(--secondary-container)] text-[var(--on-secondary-container)] text-xs font-bold uppercase tracking-wider">
            <span className="material-symbols-outlined text-[16px]">domain_add</span>
            <span>Step 2 Required</span>
          </div>

          <h2 className="text-3xl md:text-4xl font-bold text-[var(--on-surface)] tracking-tight">
            Complete Your Organization Setup
          </h2>

          <p className="text-sm text-[var(--on-surface-variant)] leading-relaxed">
            Welcome to SmartClass AI! As an Organization Owner, configure your institution details, contact profile, and initial classroom workspace to launch your portal.
          </p>
        </div>

        <Link
          href="/register/complete"
          className="inline-flex items-center justify-center gap-3 px-8 py-4 bg-[var(--primary)] text-[var(--on-primary)] rounded-full font-bold text-sm hover:opacity-90 active:scale-95 transition-all shadow-lg shadow-[var(--primary)]/20 shrink-0 cursor-pointer"
        >
          <span>Complete Setup Now</span>
          <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
        </Link>
      </div>

      {/* Feature Highlights Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-[var(--outline-variant)]/20 relative z-10">
        <div className="p-4 rounded-2xl bg-[var(--surface-container-low)]/80 border border-[var(--outline-variant)]/20 space-y-1">
          <div className="flex items-center gap-2 text-[var(--primary)] font-bold text-xs">
            <span className="material-symbols-outlined text-[18px]">school</span>
            <span>Institution Profile</span>
          </div>
          <p className="text-xs text-[var(--on-surface-variant)]">
            Define your institution type, location, timezone, and custom URL slug.
          </p>
        </div>

        <div className="p-4 rounded-2xl bg-[var(--surface-container-low)]/80 border border-[var(--outline-variant)]/20 space-y-1">
          <div className="flex items-center gap-2 text-[var(--primary)] font-bold text-xs">
            <span className="material-symbols-outlined text-[18px]">workspaces</span>
            <span>Initial Workspace</span>
          </div>
          <p className="text-xs text-[var(--on-surface-variant)]">
            Set up your first classroom workspace for academic management.
          </p>
        </div>

        <div className="p-4 rounded-2xl bg-[var(--surface-container-low)]/80 border border-[var(--outline-variant)]/20 space-y-1">
          <div className="flex items-center gap-2 text-[var(--primary)] font-bold text-xs">
            <span className="material-symbols-outlined text-[18px]">shield_person</span>
            <span>Default System Roles</span>
          </div>
          <p className="text-xs text-[var(--on-surface-variant)]">
            Automatically seeded with Owner, Admin, Teacher, Student, Parent, & Staff roles.
          </p>
        </div>
      </div>
    </div>
  );
}
