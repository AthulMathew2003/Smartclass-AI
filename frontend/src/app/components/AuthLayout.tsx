"use client";

import React from "react";
import { motion } from "framer-motion";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="min-h-screen flex flex-col md:flex-row p-4 md:p-8 lg:p-12 gap-8 lg:gap-[24px] bg-[var(--surface)] text-[var(--on-surface)] overflow-x-hidden font-sans">
      {/* Left Side: Visual & Identity (60% Forest Green Brand Space) */}
      <section className="relative w-full md:w-[60%] bg-[var(--primary)] min-h-[500px] rounded-2xl overflow-hidden flex flex-col justify-between p-8 lg:p-16">
        {/* Brand Mark */}
        <div className="flex items-center gap-3 relative z-10">
          <div className="w-10 h-10 bg-[var(--primary-fixed)] rounded-full flex items-center justify-center">
            <span className="material-symbols-outlined text-[var(--primary)] text-[24px]">school</span>
          </div>
          <span className="text-3xl font-semibold leading-tight font-sans text-[var(--on-primary)]">SmartClass AI</span>
        </div>

        {/* Content Container */}
        <div className="relative z-10 space-y-8 mt-12 mb-12">
          {/* Image Container with Scandi Shape */}
          <div className="relative w-full aspect-square max-w-[520px] mx-auto">
            <div 
              className="absolute inset-0 bg-[var(--primary-container)] shadow-none overflow-hidden flex items-center justify-center"
              style={{
                maskImage: "radial-gradient(circle at center, black 100%, transparent 100%)",
                borderRadius: "4rem 4rem 12rem 4rem",
                WebkitMaskImage: "radial-gradient(circle at center, black 100%, transparent 100%)",
              }}
            >
              <img 
                className="w-full h-full object-cover mix-blend-overlay opacity-80" 
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuD764NQ_EZqUFWpftjzB5mM7mcXmWqDY11OIM4X447JilVDRCZfWJQhiAZIjCa9TGDcOTC9XDXAoQGOKDu67_-14pjbdPQQrw5AsQfznS6L_TQDsayDipstZtuIPrFnd3AlnBVm34ECZtBnG05YBOjbf3x0ia6T4rzZMF-hz9QiQE7LQc5ZjYstXjvlcatKNCUqVqHKeKsDP8_INfRoBgMSXN0y85DJhTllJb62JCiO5nYFsFT33a9JLN5PHUBgG5HjiT7m14kHZTt2"
                alt="Students collaborating"
              />
            </div>
            
            {/* Decorative Pills (Layering Motif) */}
            <div className="absolute -bottom-4 -left-4 bg-[var(--tertiary-fixed)] text-[var(--on-tertiary-fixed)] px-6 py-3 rounded-full text-sm font-semibold tracking-wide flex items-center gap-2 transform -rotate-3 shadow-lg">
              <span className="material-symbols-outlined text-[18px]">auto_awesome</span>
              <span>Personalized Learning</span>
            </div>
            <div className="absolute top-12 -right-6 bg-[var(--secondary-container)] text-[var(--on-secondary-container)] px-6 py-3 rounded-full text-sm font-semibold tracking-wide flex items-center gap-2 transform rotate-6 shadow-lg">
              <span className="material-symbols-outlined text-[18px]">group</span>
              <span>Design Community</span>
            </div>
          </div>

          <div className="max-w-md mx-auto md:mx-0">
            <h2 className="text-5xl font-bold tracking-tight text-[var(--primary-fixed)] mb-4 leading-tight">Master your craft in our digital atelier.</h2>
            <p className="text-lg text-[var(--on-primary)]/80 leading-relaxed">Join thousands of students shaping the future of design through data-driven creativity.</p>
          </div>
        </div>

        {/* Background organic elements */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-20" preserveAspectRatio="none" viewBox="0 0 400 400">
          <path className="organic-path" d="M0,200 C100,50 300,350 400,200" fill="none" stroke="white" strokeWidth="2"></path>
          <path className="organic-path" d="M-50,300 C150,450 250,50 450,250" fill="none" stroke="#bceddc" strokeWidth="1" style={{animationDelay: '1s'}}></path>
        </svg>
      </section>

      {/* Right Side: Form Content (40% Off-white Workspace) */}
      <motion.section 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
        className="w-full md:w-[40%] flex flex-col justify-center px-4 md:px-8 lg:px-12 py-12"
      >
        <div className="max-w-md mx-auto w-full">
          {children}
        </div>
      </motion.section>
    </main>
  );
}
