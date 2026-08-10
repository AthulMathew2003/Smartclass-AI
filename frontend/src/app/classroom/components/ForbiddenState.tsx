"use client";

import React from "react";
import Link from "next/link";

/**
 * Reusable access-denied component for pages where the user
 * lacks the required permission. Displayed instead of the page content.
 *
 * This is a UX convenience only — the backend always enforces authorization.
 */
export default function ForbiddenState({
  message,
}: {
  message?: string;
}) {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div
        className="max-w-md w-full text-center p-10 rounded-3xl space-y-5"
        style={{
          backgroundColor: "var(--surface-container)",
          border: "1px solid color-mix(in srgb, var(--outline-variant) 30%, transparent)",
        }}
      >
        {/* Icon */}
        <div
          className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto"
          style={{
            backgroundColor: "rgba(186,26,26,0.08)",
          }}
        >
          <span
            className="material-symbols-outlined text-[32px]"
            style={{ color: "#ba1a1a" }}
          >
            lock
          </span>
        </div>

        {/* Heading */}
        <h2
          className="text-xl font-bold tracking-tight"
          style={{ color: "var(--on-surface)" }}
        >
          Access Denied
        </h2>

        {/* Description */}
        <p
          className="text-sm leading-relaxed"
          style={{ color: "var(--on-surface-variant)" }}
        >
          {message ||
            "You don\u2019t have permission to access this section. Contact your organization administrator if you believe this is a mistake."}
        </p>

        {/* Back to Dashboard */}
        <Link
          href="/classroom"
          className="inline-flex items-center gap-2 px-6 py-2.5 rounded-full text-xs font-bold transition-all hover:scale-95"
          style={{
            backgroundColor: "var(--primary)",
            color: "var(--on-primary)",
          }}
        >
          <span className="material-symbols-outlined text-[16px]">
            arrow_back
          </span>
          Go to Dashboard
        </Link>
      </div>
    </div>
  );
}
