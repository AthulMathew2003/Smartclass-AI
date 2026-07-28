"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import AuthLayout from "../components/AuthLayout";
import SocialLoginButtons from "../components/SocialLoginButtons";
import { Country } from "country-state-city";

export default function RegisterPage() {
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  if (!isClient) return null; // Avoid hydration mismatch

  return (
    <AuthLayout>
      {/* Heading */}
      <header className="mb-10">
        <div className="flex items-center gap-2 mb-4">
          <span className="w-8 h-1 bg-[var(--secondary-container)] rounded-full"></span>
          <span className="text-xs uppercase tracking-widest font-bold text-[var(--secondary)]">Get Started</span>
        </div>
        <h1 className="text-4xl md:text-5xl font-bold leading-tight tracking-tight text-[var(--on-surface)] mb-2">Create your organisation</h1>
        <p className="text-base text-[var(--on-surface-variant)] leading-relaxed">Join us and set up your digital atelier in minutes.</p>
      </header>

      {/* Form */}
      <form className="space-y-6" onSubmit={(e) => e.preventDefault()}>
        <div className="space-y-2 group">
          <label htmlFor="orgName" className="text-sm font-semibold tracking-wide text-[var(--on-surface-variant)] px-4 group-focus-within:text-[var(--primary)] transition-colors">Organisation Name *</label>
          <input 
            type="text" 
            id="orgName" 
            placeholder="e.g. Acme Academy"
            className="w-full px-6 py-4 bg-[var(--surface-container)] border-2 border-transparent focus:border-[var(--primary)] focus:ring-0 rounded-full transition-all duration-200 outline-none text-[var(--on-surface)] placeholder:text-[var(--on-surface-variant)]/50" 
            required
          />
        </div>

        <div className="space-y-2 group">
          <label htmlFor="orgType" className="text-sm font-semibold tracking-wide text-[var(--on-surface-variant)] px-4 group-focus-within:text-[var(--primary)] transition-colors">Organisation Type *</label>
          <div className="relative">
            <select 
              id="orgType"
              className="w-full px-6 py-4 bg-[var(--surface-container)] border-2 border-transparent focus:border-[var(--primary)] focus:ring-0 rounded-full transition-all duration-200 outline-none text-[var(--on-surface)] appearance-none cursor-pointer"
              required
              defaultValue=""
            >
              <option value="" disabled>Select Type...</option>
              <option value="school">School</option>
              <option value="college">College</option>
              <option value="university">University</option>
              <option value="coaching">Coaching Centre</option>
              <option value="training">Training Institute</option>
              <option value="corporate">Corporate</option>
            </select>
            <span className="material-symbols-outlined absolute right-6 top-1/2 -translate-y-1/2 pointer-events-none text-[var(--on-surface-variant)]">expand_more</span>
          </div>
        </div>
        
        <div className="space-y-2 group">
          <label htmlFor="country" className="text-sm font-semibold tracking-wide text-[var(--on-surface-variant)] px-4 group-focus-within:text-[var(--primary)] transition-colors">Country *</label>
          <div className="relative">
            <select 
              id="country"
              className="w-full px-6 py-4 bg-[var(--surface-container)] border-2 border-transparent focus:border-[var(--primary)] focus:ring-0 rounded-full transition-all duration-200 outline-none text-[var(--on-surface)] appearance-none cursor-pointer"
              required
              defaultValue="IN"
            >
              <option value="" disabled>Select Country...</option>
              {Country.getAllCountries().map((country) => (
                <option key={country.isoCode} value={country.isoCode}>
                  {country.name}
                </option>
              ))}
            </select>
            <span className="material-symbols-outlined absolute right-6 top-1/2 -translate-y-1/2 pointer-events-none text-[var(--on-surface-variant)]">expand_more</span>
          </div>
        </div>
        
        <hr className="border-[var(--outline-variant)]/30 my-8" />

        <div className="space-y-2 group">
          <label htmlFor="name" className="text-sm font-semibold tracking-wide text-[var(--on-surface-variant)] px-4 group-focus-within:text-[var(--primary)] transition-colors">Full Name *</label>
          <input 
            type="text" 
            id="name" 
            placeholder="Jane Doe"
            className="w-full px-6 py-4 bg-[var(--surface-container)] border-2 border-transparent focus:border-[var(--primary)] focus:ring-0 rounded-full transition-all duration-200 outline-none text-[var(--on-surface)] placeholder:text-[var(--on-surface-variant)]/50" 
            required
          />
        </div>

        <div className="space-y-2 group">
          <label htmlFor="email" className="text-sm font-semibold tracking-wide text-[var(--on-surface-variant)] px-4 group-focus-within:text-[var(--primary)] transition-colors">Work Email *</label>
          <input 
            type="email" 
            id="email" 
            placeholder="jane.doe@example.com"
            className="w-full px-6 py-4 bg-[var(--surface-container)] border-2 border-transparent focus:border-[var(--primary)] focus:ring-0 rounded-full transition-all duration-200 outline-none text-[var(--on-surface)] placeholder:text-[var(--on-surface-variant)]/50" 
            required
          />
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2 group">
            <label htmlFor="password" className="text-sm font-semibold tracking-wide text-[var(--on-surface-variant)] px-4 group-focus-within:text-[var(--primary)] transition-colors">Password *</label>
            <input 
              type="password" 
              id="password" 
              placeholder="••••••••"
              className="w-full px-6 py-4 bg-[var(--surface-container)] border-2 border-transparent focus:border-[var(--primary)] focus:ring-0 rounded-full transition-all duration-200 outline-none text-[var(--on-surface)] placeholder:text-[var(--on-surface-variant)]/50" 
              required
            />
          </div>
          
          <div className="space-y-2 group">
            <label htmlFor="confirmPassword" className="text-sm font-semibold tracking-wide text-[var(--on-surface-variant)] px-4 group-focus-within:text-[var(--primary)] transition-colors">Confirm Password *</label>
            <input 
              type="password" 
              id="confirmPassword" 
              placeholder="••••••••"
              className="w-full px-6 py-4 bg-[var(--surface-container)] border-2 border-transparent focus:border-[var(--primary)] focus:ring-0 rounded-full transition-all duration-200 outline-none text-[var(--on-surface)] placeholder:text-[var(--on-surface-variant)]/50" 
              required
            />
          </div>
        </div>
        
        <div className="space-y-4 pt-2 px-4">
          <div className="flex items-start gap-3">
            <input 
              type="checkbox" 
              id="terms" 
              className="w-5 h-5 mt-0.5 rounded-md border-[var(--outline-variant)] text-[var(--primary)] focus:ring-[var(--primary)] accent-[var(--primary)]" 
              required
            />
            <label htmlFor="terms" className="text-sm font-semibold tracking-wide text-[var(--on-surface-variant)]">
              I agree to the Terms of Service and Privacy Policy *
            </label>
          </div>
          
          <div className="flex items-start gap-3">
            <input 
              type="checkbox" 
              id="updates" 
              className="w-5 h-5 mt-0.5 rounded-md border-[var(--outline-variant)] text-[var(--primary)] focus:ring-[var(--primary)] accent-[var(--primary)]" 
            />
            <label htmlFor="updates" className="text-sm font-semibold tracking-wide text-[var(--on-surface-variant)]">
              Receive product updates (optional)
            </label>
          </div>
        </div>
        
        <button className="w-full bg-[var(--primary)] text-[var(--on-primary)] py-5 rounded-full text-lg font-semibold hover:bg-[var(--primary-container)] transition-all active:scale-[0.98] duration-150 flex items-center justify-center gap-3 mt-4">
          <span>Create Organisation</span>
          <span className="material-symbols-outlined">arrow_forward</span>
        </button>
      </form>

      {/* Alternative Login */}
      <SocialLoginButtons actionText="continue with" />

      {/* Footer Link */}
      <footer className="mt-16 text-center space-y-4 flex flex-col items-center">
        <p className="text-[var(--on-surface-variant)] text-base">
          Already have an account? <Link href="/login" className="text-[var(--primary)] font-bold hover:underline">Sign In</Link>
        </p>
        <Link href="/" className="inline-flex items-center gap-2 text-[var(--on-surface-variant)] hover:text-[var(--primary)] font-semibold transition-colors">
          <span className="material-symbols-outlined text-[20px]">arrow_back</span>
          Back to Home
        </Link>
      </footer>
    </AuthLayout>
  );
}
