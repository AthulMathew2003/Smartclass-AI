"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import {
  fetchCurrentUser,
  fetchOnboardingStatus,
  UserProfile,
  OnboardingStatusResponse
} from "../../lib/auth";

export default function ClassroomLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [status, setStatus] = useState<OnboardingStatusResponse | null>(null);

  useEffect(() => {
    const init = async () => {
      const currentUser = await fetchCurrentUser();
      if (!currentUser) {
        router.push("/login");
        return;
      }
      setUser(currentUser);

      const onboardingStatus = await fetchOnboardingStatus();
      setStatus(onboardingStatus);
      setLoading(false);
    };

    init();
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--surface)] text-[var(--on-surface)] flex items-center justify-center p-6">
        <div className="max-w-md w-full p-8 rounded-3xl bg-[var(--surface-container)] border border-[var(--outline-variant)]/30 text-center space-y-4 shadow-xl">
          <div className="w-12 h-12 border-4 border-[var(--primary)] border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p className="text-sm font-semibold text-[var(--on-surface-variant)]">Loading SmartClass AI Portal...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--surface)] text-[var(--on-surface)] flex">
      {/* Sidebar Navigation */}
      <Sidebar status={status} />

      {/* Main Viewport */}
      <div className="flex-1 flex flex-col min-w-0">
        <Header user={user} status={status} />
        <main className="flex-1 p-6 md:p-10 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
