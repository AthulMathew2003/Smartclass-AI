"use client";

import React, { useEffect, useState, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { loginWithPassword, getGoogleOAuthUrl, getGitHubOAuthUrl } from "../../lib/auth";

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  useEffect(() => {
    const errParam = searchParams.get("error");
    if (errParam) {
      setError(decodeURIComponent(errParam));
    }
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

  const handleGoogleLogin = () => {
    window.location.href = `${getGoogleOAuthUrl()}?action=login`;
  };

  const handleGitHubLogin = () => {
    window.location.href = `${getGitHubOAuthUrl()}?action=login`;
  };

  return (
    <main className="min-h-screen flex flex-col md:flex-row p-4 md:p-8 lg:p-12 gap-8 lg:gap-gutter bg-[var(--background)] text-[var(--on-surface)] font-body-md overflow-x-hidden transition-colors duration-300">
      {/* Left Side: Visual & Identity (60% Forest Green Brand Space) */}
      <section className="relative w-full md:w-[60%] bg-[var(--primary)] min-h-[500px] rounded-lg overflow-hidden flex flex-col justify-between p-8 lg:p-16">
        {/* Brand Mark */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-[var(--primary-fixed)] rounded-full flex items-center justify-center">
            <span className="material-symbols-outlined text-[var(--primary)] text-[24px]">school</span>
          </div>
          <span className="text-headline-md font-headline-md font-bold text-[var(--on-primary)]">SmartClass AI</span>
        </div>

        {/* Content Container */}
        <div className="relative z-10 space-y-8">
          {/* Image Container with Scandi Shape */}
          <div className="relative w-full aspect-square max-w-[520px] mx-auto">
            <div className="absolute inset-0 bg-[var(--primary-container)] rounded-lg scandi-mask shadow-none overflow-hidden" style={{ borderRadius: "4rem 4rem 12rem 4rem" }}>
              <img
                className="w-full h-full object-cover mix-blend-overlay opacity-80"
                alt="A warm, candid photograph of university students collaborating"
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuD764NQ_EZqUFWpftjzB5mM7mcXmWqDY11OIM4X447JilVDRCZfWJQhiAZIjCa9TGDcOTC9XDXAoQGOKDu67_-14pjbdPQQrw5AsQfznS6L_TQDsayDipstZtuIPrFnd3AlnBVm34ECZtBnG05YBOjbf3x0ia6T4rzZMF-hz9QiQE7LQc5ZjYstXjvlcatKNCUqVqHKeKsDP8_INfRoBgMSXN0y85DJhTllJb62JCiO5nYFsFT33a9JLN5PHUBgG5HjiT7m14kHZTt2"
              />
            </div>
            {/* Decorative Pills */}
            <div className="absolute -bottom-4 -left-4 bg-[var(--tertiary-fixed)] text-[var(--on-tertiary-fixed)] px-6 py-3 rounded-full font-label-md flex items-center gap-2 transform -rotate-3 shadow-md">
              <span className="material-symbols-outlined text-[18px]">auto_awesome</span>
              <span>Personalized Learning</span>
            </div>
            <div className="absolute top-12 -right-6 bg-[var(--secondary-container)] text-[var(--on-secondary-container)] px-6 py-3 rounded-full font-label-md flex items-center gap-2 transform rotate-6 shadow-md">
              <span className="material-symbols-outlined text-[18px]">group</span>
              <span>Design Community</span>
            </div>
          </div>

          <div className="max-w-md">
            <h2 className="text-headline-lg font-headline-lg text-[var(--primary-fixed)] mb-4 leading-tight">Master your craft in our digital atelier.</h2>
            <p className="text-body-lg text-[var(--on-primary)]/80">Join thousands of students shaping the future of design through data-driven creativity.</p>
          </div>
        </div>

        {/* Background organic elements */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-20" preserveAspectRatio="none" viewBox="0 0 400 400">
          <path className="organic-path" d="M0,200 C100,50 300,350 400,200" fill="none" stroke="white" strokeWidth="2"></path>
          <path className="organic-path" d="M-50,300 C150,450 250,50 450,250" fill="none" stroke="#bceddc" strokeWidth="1"></path>
        </svg>
      </section>

      {/* Right Side: Login Form (40% Off-white Workspace) */}
      <section className="w-full md:w-[40%] flex flex-col justify-center px-4 md:px-8 lg:px-12 py-12">
        <div className="max-w-md mx-auto w-full">
          {/* Heading */}
          <header className="mb-12">
            <div className="flex items-center gap-2 mb-4">
              <span className="w-8 h-1 bg-[var(--secondary-container)] rounded-full"></span>
              <span className="text-label-sm uppercase tracking-widest text-[var(--secondary)]">Member Access</span>
            </div>
            <h1 className="text-3xl font-headline-lg text-[var(--on-surface)] mb-2">Welcome Back</h1>
            <p className="text-[var(--on-surface-variant)] font-body-md">Sign in to continue your learning journey.</p>
          </header>

          {error && (
            <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-500 text-sm font-semibold flex items-center gap-2">
              <span className="material-symbols-outlined text-[20px]">error</span>
              <span>{error}</span>
            </div>
          )}

          {/* Form */}
          <form className="space-y-6" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <label className="text-label-md text-[var(--on-surface-variant)] px-4" htmlFor="email">Email Address</label>
              <input
                className="w-full px-6 py-4 bg-[var(--surface-container)] border-2 border-transparent focus:border-[var(--primary)] focus:ring-0 rounded-full transition-all duration-200 outline-none text-[var(--on-surface)]"
                id="email"
                type="email"
                placeholder="jane.doe@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <div className="flex justify-between px-4">
                <label className="text-label-md text-[var(--on-surface-variant)]" htmlFor="password">Password</label>
                <a className="text-label-md text-[var(--primary)] hover:underline transition-all" href="#">Forgot?</a>
              </div>
              <input
                className="w-full px-6 py-4 bg-[var(--surface-container)] border-2 border-transparent focus:border-[var(--primary)] focus:ring-0 rounded-full transition-all duration-200 outline-none text-[var(--on-surface)]"
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <div className="flex items-center gap-3 px-4 py-2">
              <input
                className="w-5 h-5 rounded-md border-[var(--outline-variant)] text-[var(--primary)] focus:ring-[var(--primary)] cursor-pointer"
                id="remember"
                type="checkbox"
              />
              <label className="text-label-md text-[var(--on-surface-variant)] cursor-pointer select-none" htmlFor="remember">Keep me logged in</label>
            </div>
            
            <button
              className="w-full bg-[var(--primary)] text-[var(--on-primary)] py-5 rounded-full font-headline-md hover:bg-[var(--primary-container)] transition-all active:scale-[0.98] duration-150 flex items-center justify-center gap-3 mt-4 cursor-pointer"
              type="submit"
              disabled={loading}
            >
              <span>{loading ? "Signing In..." : "Sign In"}</span>
              <span className="material-symbols-outlined">arrow_forward</span>
            </button>
          </form>

          {/* Alternative Login */}
          <div className="mt-12 space-y-6">
            <div className="flex items-center gap-4 text-[var(--outline-variant)]">
              <div className="h-[1px] flex-grow bg-[var(--outline-variant)]/30"></div>
              <span className="text-label-sm uppercase tracking-widest font-bold">Or continue with</span>
              <div className="h-[1px] flex-grow bg-[var(--outline-variant)]/30"></div>
            </div>
          <div className="grid grid-cols-2 gap-4">
            <button
              type="button"
              onClick={handleGoogleLogin}
              className="flex items-center justify-center gap-2.5 py-4 border border-[var(--outline-variant)] rounded-full hover:bg-[var(--surface-container)] transition-colors cursor-pointer"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"></path>
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"></path>
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"></path>
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.66l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"></path>
              </svg>
              <span className="text-label-md text-[var(--on-surface)]">Google</span>
            </button>
            <button
              type="button"
              onClick={handleGitHubLogin}
              className="flex items-center justify-center gap-2.5 py-4 border border-[var(--outline-variant)] rounded-full hover:bg-[var(--surface-container)] transition-colors cursor-pointer"
            >
              <svg className="w-5 h-5 fill-current text-[var(--on-surface)]" viewBox="0 0 24 24">
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
              </svg>
              <span className="text-label-md text-[var(--on-surface)]">GitHub</span>
            </button>
          </div>
          </div>

          {/* Footer Link */}
          <footer className="mt-16 text-center">
            <p className="text-[var(--on-surface-variant)] text-body-md">
              Don't have an account?{" "}
              <Link className="text-[var(--primary)] font-bold hover:underline" href="/register">Create Account</Link>
            </p>
          </footer>
        </div>
      </section>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-[var(--background)] text-[var(--on-surface)] flex items-center justify-center p-6">
        <div className="max-w-md w-full p-8 rounded-3xl bg-[var(--surface-container)] border border-[var(--outline-variant)]/30 text-center space-y-4 shadow-xl animate-pulse">
          <div className="w-12 h-12 border-4 border-[var(--primary)] border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p className="text-sm font-semibold">Loading Sign In...</p>
        </div>
      </div>
    }>
      <LoginContent />
    </Suspense>
  );
}
