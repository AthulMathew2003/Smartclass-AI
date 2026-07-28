"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import AuthLayout from "../components/AuthLayout";
import SocialLoginButtons from "../components/SocialLoginButtons";

export default function LoginPage() {
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  if (!isClient) return null; // Avoid hydration mismatch

  return (
    <AuthLayout>
      {/* Heading */}
      <header className="mb-12">
        <div className="flex items-center gap-2 mb-4">
          <span className="w-8 h-1 bg-[var(--secondary-container)] rounded-full"></span>
          <span className="text-xs uppercase tracking-widest font-bold text-[var(--secondary)]">Member Access</span>
        </div>
        <h1 className="text-4xl md:text-5xl font-bold leading-tight tracking-tight text-[var(--on-surface)] mb-2">Welcome Back</h1>
        <p className="text-base text-[var(--on-surface-variant)] leading-relaxed">Sign in to continue your learning journey.</p>
      </header>

      {/* Form */}
      <form className="space-y-6" onSubmit={(e) => e.preventDefault()}>
        <div className="space-y-2 group">
          <label htmlFor="email" className="text-sm font-semibold tracking-wide text-[var(--on-surface-variant)] px-4 group-focus-within:text-[var(--primary)] transition-colors">Email Address</label>
          <input 
            type="email" 
            id="email" 
            placeholder="jane.doe@example.com"
            className="w-full px-6 py-4 bg-[var(--surface-container)] border-2 border-transparent focus:border-[var(--primary)] focus:ring-0 rounded-full transition-all duration-200 outline-none text-[var(--on-surface)] placeholder:text-[var(--on-surface-variant)]/50" 
          />
        </div>
        
        <div className="space-y-2 group">
          <div className="flex justify-between px-4">
            <label htmlFor="password" className="text-sm font-semibold tracking-wide text-[var(--on-surface-variant)] group-focus-within:text-[var(--primary)] transition-colors">Password</label>
            <Link href="#" className="text-sm font-semibold tracking-wide text-[var(--primary)] hover:underline transition-all">Forgot?</Link>
          </div>
          <input 
            type="password" 
            id="password" 
            placeholder="••••••••"
            className="w-full px-6 py-4 bg-[var(--surface-container)] border-2 border-transparent focus:border-[var(--primary)] focus:ring-0 rounded-full transition-all duration-200 outline-none text-[var(--on-surface)] placeholder:text-[var(--on-surface-variant)]/50" 
          />
        </div>
        
        <div className="flex items-center gap-3 px-4 py-2">
          <input 
            type="checkbox" 
            id="remember" 
            className="w-5 h-5 rounded-md border-[var(--outline-variant)] text-[var(--primary)] focus:ring-[var(--primary)] accent-[var(--primary)]" 
          />
          <label htmlFor="remember" className="text-sm font-semibold tracking-wide text-[var(--on-surface-variant)]">Keep me logged in</label>
        </div>
        
        <button className="w-full bg-[var(--primary)] text-[var(--on-primary)] py-5 rounded-full text-lg font-semibold hover:bg-[var(--primary-container)] transition-all active:scale-[0.98] duration-150 flex items-center justify-center gap-3 mt-4">
          <span>Sign In</span>
          <span className="material-symbols-outlined">arrow_forward</span>
        </button>
      </form>

      {/* Alternative Login */}
      <SocialLoginButtons actionText="continue with" />

      {/* Footer Link */}
      <footer className="mt-16 text-center">
        <Link href="/" className="inline-flex items-center gap-2 text-[var(--on-surface-variant)] hover:text-[var(--primary)] font-semibold transition-colors">
          <span className="material-symbols-outlined text-[20px]">arrow_back</span>
          Back to Home
        </Link>
      </footer>
    </AuthLayout>
  );
}
