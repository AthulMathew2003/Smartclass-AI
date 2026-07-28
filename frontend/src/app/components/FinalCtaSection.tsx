"use client";

import React from "react";
import Link from "next/link";

export default function FinalCtaSection() {
  return (
    <section className="w-full max-w-[1920px] mx-auto px-4 sm:px-8 md:px-12 lg:px-16 py-16 md:py-24">
      <div className="bg-[#154539] text-[#ffffff] rounded-3xl p-10 sm:p-16 lg:p-20 relative overflow-hidden flex flex-col items-center text-center shadow-2xl">
        {/* Background Rings & Glow */}
        <div className="absolute top-0 left-0 w-full h-full overflow-hidden opacity-10 pointer-events-none">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] border border-white rounded-full"></div>
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] border border-white rounded-full"></div>
        </div>

        <div className="relative z-10 max-w-3xl">
          <span className="bg-[#c3f185] text-[#112000] px-4 py-1.5 rounded-full text-xs font-extrabold uppercase tracking-wider mb-6 inline-block shadow-md">
            Start Transforming Education Today
          </span>

          <h2 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold mb-6 tracking-tight leading-tight">
            Ready to Transform Learning?
          </h2>

          <p className="text-base sm:text-xl mb-10 text-white/80 leading-relaxed max-w-2xl mx-auto">
            Join thousands of educators, students, and academic administrators using SmartClass AI to shape the future of modern education.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/login"
              className="bg-[#c3f185] hover:bg-[#a7d56c] text-[#112000] px-10 py-4 rounded-full text-sm font-extrabold shadow-xl hover:scale-105 active:scale-95 transition-all flex items-center justify-center gap-2"
            >
              <span>Start Free</span>
              <span className="material-symbols-outlined text-lg">arrow_forward</span>
            </Link>
            <Link
              href="/login"
              className="bg-[#2f5d50] text-[#bceddc] hover:bg-white/10 border border-white/20 px-10 py-4 rounded-full text-sm font-bold transition-all flex items-center justify-center gap-2"
            >
              <span className="material-symbols-outlined text-lg">headset_mic</span>
              <span>Contact Sales</span>
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
