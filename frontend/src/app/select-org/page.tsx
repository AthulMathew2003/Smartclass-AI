"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchOnboardingStatus, fetchUserMemberships, UserMembershipBrief } from "../../lib/auth";
import { clearPermissions, loadPermissions } from "../../lib/permissions";

export default function SelectOrganizationPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [memberships, setMemberships] = useState<UserMembershipBrief[]>([]);

  useEffect(() => {
    const init = async () => {
      if (typeof window !== "undefined") localStorage.removeItem("activeOrganizationId");
      clearPermissions();
      const st = await fetchOnboardingStatus();
      const mems = await fetchUserMemberships();
      const hasMemberships = mems && mems.length > 0;
      if (!st || (!st.has_organization && !hasMemberships)) { router.replace("/login"); return; }
      setMemberships(mems || []);
      setLoading(false);
    };
    init();
  }, [router]);

  const handleSelectOrg = async (orgId: string) => {
    clearPermissions();
    if (typeof window !== "undefined") localStorage.setItem("activeOrganizationId", orgId);
    await loadPermissions(true);
    router.replace("/classroom");
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--background)] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: "var(--primary)", borderTopColor: "transparent" }} />
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-[var(--background)] text-[var(--on-surface)] flex items-center justify-center p-6 relative overflow-hidden">
      {/* Atmospheric blob */}
      <svg className="absolute -top-32 -right-32 w-[480px] h-[480px] opacity-[0.04] pointer-events-none" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
        <path d="M44.7,-76.4C58.1,-69.2,69.2,-58.1,76.4,-44.7C83.6,-31.3,86.9,-15.7,85.2,-0.9C83.6,13.8,77,27.7,69.1,40.4C61.2,53,52.1,64.3,40.5,72.4C28.8,80.5,14.4,85.4,-0.6,86.4C-15.6,87.4,-31.1,84.4,-44.8,77.3C-58.4,70.2,-70.2,59,-77.3,45.4C-84.4,31.7,-86.7,15.9,-86.1,0.4C-85.4,-15.1,-81.8,-30.2,-74.1,-43.3C-66.5,-56.3,-54.9,-67.2,-41.4,-74.3C-27.9,-81.4,-14,-84.7,0.4,-85.4C14.7,-86.1,29.4,-84.1,44.7,-76.4Z" fill="var(--primary)" transform="translate(100 100)" />
      </svg>

      <div className="w-full max-w-md animate-slide-up">
        {/* Header card */}
        <div className="text-center mb-8">
          <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4" style={{ backgroundColor: "var(--primary)", color: "var(--on-primary)" }}>
            <span className="material-symbols-outlined text-[26px]">domain</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight" style={{ color: "var(--on-surface)" }}>Select Organization</h1>
          <p className="text-sm mt-2 max-w-xs mx-auto" style={{ color: "var(--on-surface-variant)" }}>
            Your account is linked to multiple organizations. Choose one to enter your workspace.
          </p>
        </div>

        {/* Organization list */}
        <div className="space-y-3">
          {memberships.map((org) => (
            <button
              key={org.organization_id}
              onClick={() => handleSelectOrg(org.organization_id)}
              className="w-full text-left p-5 ds-card cursor-pointer flex items-center justify-between gap-4 group transition-all duration-200"
              style={{ borderColor: "color-mix(in srgb, var(--outline-variant) 40%, transparent)" }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "var(--primary)";
                e.currentTarget.style.transform = "translateY(-1px)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "color-mix(in srgb, var(--outline-variant) 40%, transparent)";
                e.currentTarget.style.transform = "translateY(0)";
              }}
            >
              <div className="flex items-center gap-4 min-w-0">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center font-bold text-sm shrink-0" style={{ backgroundColor: "var(--primary)", color: "var(--on-primary)" }}>
                  {org.organization_name?.[0]?.toUpperCase() ?? "O"}
                </div>
                <div className="min-w-0">
                  <h3 className="font-bold text-sm truncate" style={{ color: "var(--on-surface)" }}>{org.organization_name}</h3>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ backgroundColor: "var(--primary)" }} />
                    <span className="text-xs font-semibold" style={{ color: "var(--on-surface-variant)" }}>
                      {org.role_name || "Member"}
                    </span>
                  </div>
                </div>
              </div>
              <span className="material-symbols-outlined text-[20px] shrink-0 transition-transform duration-200 group-hover:translate-x-1" style={{ color: "var(--outline)" }}>
                arrow_forward
              </span>
            </button>
          ))}
        </div>

        {/* Footer */}
        <div className="mt-6 text-center">
          <button
            onClick={() => {
              clearPermissions();
              if (typeof window !== "undefined") localStorage.clear();
              router.replace("/login");
            }}
            className="text-sm font-semibold hover:underline cursor-pointer"
            style={{ color: "var(--on-surface-variant)" }}
          >
            Sign in with a different account
          </button>
        </div>
      </div>
    </main>
  );
}
