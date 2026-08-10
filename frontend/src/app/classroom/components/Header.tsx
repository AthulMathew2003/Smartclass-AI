"use client";

import React from "react";
import { UserProfile, OnboardingStatusResponse, logoutUser } from "../../../lib/auth";
import { useRouter } from "next/navigation";

export default function Header({
  user,
  status,
}: {
  user: UserProfile | null;
  status: OnboardingStatusResponse | null;
}) {
  const router = useRouter();

  const handleLogout = async () => {
    await logoutUser();
    router.push("/login");
  };

  const initials =
    user?.first_name && user?.last_name
      ? `${user.first_name[0]}${user.last_name[0]}`
      : user?.first_name
      ? user.first_name[0]
      : user?.email?.[0]?.toUpperCase() ?? "U";

  const displayName = user?.first_name
    ? `${user.first_name}${user.last_name ? " " + user.last_name : ""}`
    : user?.email ?? "";

  const greeting = (() => {
    const h = new Date().getHours();
    if (h < 12) return "Good morning";
    if (h < 18) return "Good afternoon";
    return "Good evening";
  })();

  return (
    <header
      className="h-16 px-6 flex items-center justify-between sticky top-0 z-10 border-b"
      style={{
        backgroundColor: "var(--surface)",
        borderColor: "var(--outline-variant)",
      }}
    >
      {/* Greeting */}
      <div className="flex items-center gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--on-surface-variant)" }}>
            {greeting}
          </p>
          <h2 className="text-sm font-bold leading-tight" style={{ color: "var(--on-surface)" }}>
            {displayName || status?.organization_name || "SmartClass AI"}
          </h2>
        </div>
        {status?.organization_name && (
          <>
            <div className="hidden md:block w-px h-6" style={{ backgroundColor: "var(--outline-variant)" }} />
            <div
              className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold"
              style={{
                backgroundColor: "rgba(21,69,57,0.08)",
                color: "var(--primary)",
              }}
            >
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>{status.organization_name}</span>
            </div>
          </>
        )}
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3">
        {/* Search */}
        <div className="relative hidden md:block w-56">
          <span
            className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-[18px]"
            style={{ color: "var(--on-surface-variant)" }}
          >
            search
          </span>
          <input
            type="text"
            placeholder="Search..."
            className="w-full pl-9 pr-4 py-2 rounded-full text-xs outline-none transition-all"
            style={{
              backgroundColor: "var(--surface-container)",
              color: "var(--on-surface)",
              border: "1px solid transparent",
            }}
            onFocus={e => (e.currentTarget.style.borderColor = "var(--primary)")}
            onBlur={e => (e.currentTarget.style.borderColor = "transparent")}
          />
        </div>

        {/* Notification bell */}
        <button
          className="relative w-9 h-9 rounded-full flex items-center justify-center transition-colors cursor-pointer"
          style={{ color: "var(--on-surface-variant)" }}
          onMouseEnter={e => (e.currentTarget.style.backgroundColor = "var(--surface-container-high)")}
          onMouseLeave={e => (e.currentTarget.style.backgroundColor = "transparent")}
        >
          <span className="material-symbols-outlined text-[20px]">notifications</span>
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full" style={{ backgroundColor: "var(--error)" }} />
        </button>

        <div className="w-px h-6 hidden md:block" style={{ backgroundColor: "var(--outline-variant)" }} />

        {/* User chip */}
        <div className="flex items-center gap-2.5">
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs shadow"
            style={{ backgroundColor: "var(--primary)", color: "var(--on-primary)" }}
          >
            {initials}
          </div>
          <div className="hidden sm:block text-left">
            <span className="text-xs font-bold block leading-tight" style={{ color: "var(--on-surface)" }}>
              {displayName}
            </span>
            <span className="text-[10px] font-semibold block" style={{ color: "var(--on-surface-variant)" }}>
              {status?.role || "Organization Owner"}
            </span>
          </div>
        </div>

        {/* Logout */}
        <button
          onClick={handleLogout}
          className="w-9 h-9 rounded-full flex items-center justify-center border transition-all cursor-pointer"
          style={{
            borderColor: "var(--outline-variant)",
            color: "var(--on-surface-variant)",
          }}
          onMouseEnter={e => {
            e.currentTarget.style.backgroundColor = "var(--surface-container-high)";
            e.currentTarget.style.color = "var(--on-surface)";
          }}
          onMouseLeave={e => {
            e.currentTarget.style.backgroundColor = "transparent";
            e.currentTarget.style.color = "var(--on-surface-variant)";
          }}
          title="Sign Out"
        >
          <span className="material-symbols-outlined text-[18px]">logout</span>
        </button>
      </div>
    </header>
  );
}
