"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function RolesRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/classroom/settings/roles");
  }, [router]);

  return (
    <div className="p-12 text-center space-y-2">
      <div className="w-6 h-6 border-2 border-t-transparent border-[var(--primary)] rounded-full animate-spin mx-auto" />
      <p className="text-xs text-[var(--on-surface-variant)] font-semibold">Redirecting to Roles & Permissions settings...</p>
    </div>
  );
}
