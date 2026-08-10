"use client";

import React, { useEffect, useState, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { loginWithPassword, getGoogleOAuthUrl, getGitHubOAuthUrl } from "../../lib/auth";

// ── Google SVG ────────────────────────────────────────────────
const GoogleIcon = () => (
  <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24">
    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.66l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
  </svg>
);

const GitHubIcon = () => (
  <svg className="w-4 h-4 shrink-0 fill-current" viewBox="0 0 24 24">
    <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
  </svg>
);

// ── Features list for the left panel ─────────────────────────
const features = [
  { icon: "school", text: "AI-powered learning for every institution" },
  { icon: "shield_person", text: "Role-based access — Owner, Admin, Teacher, Student" },
  { icon: "analytics", text: "Real-time analytics and engagement tracking" },
];

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    const errParam = searchParams.get("error");
    if (errParam) setError(decodeURIComponent(errParam));
  }, [searchParams]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await loginWithPassword({ email, password });
      router.replace("/classroom");
    } catch (err: any) {
      setError(err.message || "Failed to sign in. Please check your credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen flex bg-[var(--background)] text-[var(--on-surface)]">
      {/* ── Left Panel ───────────────────────────────────────── */}
      <section className="hidden lg:flex w-[52%] bg-[var(--primary)] relative overflow-hidden flex-col justify-between p-14">
        {/* Organic SVG blob */}
        <svg className="absolute -top-32 -right-32 w-[520px] h-[520px] opacity-10 pointer-events-none" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
          <path d="M44.7,-76.4C58.1,-69.2,69.2,-58.1,76.4,-44.7C83.6,-31.3,86.9,-15.7,85.2,-0.9C83.6,13.8,77,27.7,69.1,40.4C61.2,53,52.1,64.3,40.5,72.4C28.8,80.5,14.4,85.4,-0.6,86.4C-15.6,87.4,-31.1,84.4,-44.8,77.3C-58.4,70.2,-70.2,59,-77.3,45.4C-84.4,31.7,-86.7,15.9,-86.1,0.4C-85.4,-15.1,-81.8,-30.2,-74.1,-43.3C-66.5,-56.3,-54.9,-67.2,-41.4,-74.3C-27.9,-81.4,-14,-84.7,0.4,-85.4C14.7,-86.1,29.4,-84.1,44.7,-76.4Z" fill="white" transform="translate(100 100)" />
        </svg>
        <svg className="absolute bottom-0 -left-16 w-[320px] h-[320px] opacity-5 pointer-events-none" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
          <path d="M44.7,-76.4C58.1,-69.2,69.2,-58.1,76.4,-44.7C83.6,-31.3,86.9,-15.7,85.2,-0.9C83.6,13.8,77,27.7,69.1,40.4C61.2,53,52.1,64.3,40.5,72.4C28.8,80.5,14.4,85.4,-0.6,86.4C-15.6,87.4,-31.1,84.4,-44.8,77.3C-58.4,70.2,-70.2,59,-77.3,45.4C-84.4,31.7,-86.7,15.9,-86.1,0.4C-85.4,-15.1,-81.8,-30.2,-74.1,-43.3C-66.5,-56.3,-54.9,-67.2,-41.4,-74.3C-27.9,-81.4,-14,-84.7,0.4,-85.4C14.7,-86.1,29.4,-84.1,44.7,-76.4Z" fill="white" transform="translate(100 100)" />
        </svg>

        {/* Brand */}
        <div className="flex items-center gap-3 relative z-10">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center font-bold text-sm" style={{ backgroundColor: "var(--tertiary-fixed)", color: "var(--on-tertiary-fixed)" }}>
            S
          </div>
          <span className="text-lg font-bold text-white">SmartClass AI</span>
        </div>

        {/* Center content */}
        <div className="relative z-10 space-y-10">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider" style={{ backgroundColor: "rgba(195,241,133,0.15)", color: "var(--tertiary-fixed)" }}>
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--tertiary-fixed)] animate-pulse" />
              Premium Education Platform
            </div>
            <h1 className="text-4xl font-bold leading-tight" style={{ color: "white" }}>
              Your complete<br />digital academy<br />awaits you.
            </h1>
            <p className="text-base leading-relaxed" style={{ color: "rgba(255,255,255,0.65)" }}>
              SmartClass AI powers thousands of educators with intelligent tools for modern learning.
            </p>
          </div>

          <div className="space-y-4">
            {features.map((f, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" style={{ backgroundColor: "rgba(255,255,255,0.08)" }}>
                  <span className="material-symbols-outlined text-[18px]" style={{ color: "var(--tertiary-fixed)" }}>{f.icon}</span>
                </div>
                <span className="text-sm font-medium" style={{ color: "rgba(255,255,255,0.8)" }}>{f.text}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom caption */}
        <p className="text-xs font-semibold relative z-10" style={{ color: "rgba(255,255,255,0.35)" }}>
          © 2024 SmartClass AI. Scandinavian Designed.
        </p>
      </section>

      {/* ── Right Panel: Form ────────────────────────────────── */}
      <section className="flex-1 flex flex-col items-center justify-center p-6 md:p-12">
        <div className="w-full max-w-md animate-slide-up">
          {/* Mobile brand */}
          <div className="flex items-center gap-2 mb-8 lg:hidden">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs" style={{ backgroundColor: "var(--primary)", color: "var(--on-primary)" }}>S</div>
            <span className="text-base font-bold">SmartClass AI</span>
          </div>

          {/* Header */}
          <div className="mb-8">
            <div className="flex items-center gap-2 mb-3">
              <span className="w-6 h-0.5 rounded-full" style={{ backgroundColor: "var(--secondary-container)" }} />
              <span className="text-xs font-bold uppercase tracking-widest" style={{ color: "var(--secondary)" }}>Member Access</span>
            </div>
            <h2 className="text-3xl font-bold tracking-tight" style={{ color: "var(--on-surface)" }}>Welcome back</h2>
            <p className="text-sm mt-1.5" style={{ color: "var(--on-surface-variant)" }}>Sign in to continue your journey.</p>
          </div>

          {/* Error */}
          {error && (
            <div className="mb-6 p-4 rounded-xl flex items-center gap-2.5 text-sm font-medium animate-fade-in" style={{ backgroundColor: "rgba(186,26,26,0.06)", border: "1px solid rgba(186,26,26,0.2)", color: "#ba1a1a" }}>
              <span className="material-symbols-outlined text-[18px]">error</span>
              <span>{error}</span>
            </div>
          )}

          {/* Form */}
          <form className="space-y-5" onSubmit={handleSubmit}>
            <div className="space-y-1.5">
              <label className="text-xs font-semibold" style={{ color: "var(--on-surface-variant)" }} htmlFor="email">Email Address</label>
              <input
                id="email"
                type="email"
                className="ds-input"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <label className="text-xs font-semibold" style={{ color: "var(--on-surface-variant)" }} htmlFor="password">Password</label>
                <a className="text-xs font-semibold hover:underline" style={{ color: "var(--primary)" }} href="#">Forgot password?</a>
              </div>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  className="ds-input pr-12"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 cursor-pointer"
                  style={{ color: "var(--on-surface-variant)" }}
                >
                  <span className="material-symbols-outlined text-[18px]">{showPassword ? "visibility_off" : "visibility"}</span>
                </button>
              </div>
            </div>

            <button type="submit" disabled={loading} className="ds-btn-primary w-full py-3.5 mt-2">
              {loading ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Signing In...
                </>
              ) : (
                <>Sign In <span className="material-symbols-outlined text-[18px]">arrow_forward</span></>
              )}
            </button>
          </form>

          {/* Divider */}
          <div className="my-6 flex items-center gap-3">
            <div className="ds-divider flex-1" />
            <span className="text-xs font-bold uppercase tracking-widest" style={{ color: "var(--on-surface-variant)" }}>or continue with</span>
            <div className="ds-divider flex-1" />
          </div>

          {/* Social */}
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => { window.location.href = `${getGoogleOAuthUrl()}?action=login`; }}
              className="ds-btn-secondary py-3 text-sm"
            >
              <GoogleIcon /> Google
            </button>
            <button
              type="button"
              onClick={() => { window.location.href = `${getGitHubOAuthUrl()}?action=login`; }}
              className="ds-btn-secondary py-3 text-sm"
              style={{ color: "var(--on-surface)" }}
            >
              <GitHubIcon /> GitHub
            </button>
          </div>

          {/* Footer */}
          <p className="mt-8 text-center text-sm" style={{ color: "var(--on-surface-variant)" }}>
            Don&apos;t have an account?{" "}
            <Link className="font-bold hover:underline" style={{ color: "var(--primary)" }} href="/register">Create Account</Link>
          </p>
        </div>
      </section>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-[var(--background)] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: "var(--primary)", borderTopColor: "transparent" }} />
      </div>
    }>
      <LoginContent />
    </Suspense>
  );
}
