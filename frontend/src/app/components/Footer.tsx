"use client";

import React from "react";
import Link from "next/link";

export default function Footer() {
  return (
    <footer className="bg-[#f0edec] dark:bg-[#171d1a] border-t border-[#e5e2e1] dark:border-[#2f3732] mt-auto">
      <div className="w-full max-w-[1920px] mx-auto px-4 sm:px-8 md:px-12 lg:px-16 py-16">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-10 mb-16">
          {/* Col 1: Brand Info */}
          <div className="lg:col-span-2 space-y-4">
            <Link href="/" className="flex items-center gap-2.5">
              <div className="w-10 h-10 rounded-full bg-[#154539] text-[#c3f185] flex items-center justify-center font-bold shadow-md">
                <span className="material-symbols-outlined material-symbols-filled text-2xl">
                  school
                </span>
              </div>
              <span className="text-2xl font-extrabold tracking-tight text-[#1c1b1b] dark:text-[#e1e4e1]">
                SmartClass <span className="text-[#154539] dark:text-[#a0d1c0]">AI</span>
              </span>
            </Link>
            <p className="text-xs text-[#717975] dark:text-[#c0c8c4] leading-relaxed max-w-sm font-medium">
              The AI-powered platform for modern education. Integrating WebRTC virtual classrooms, Retrieval-Augmented Generation (RAG) AI tutoring, facial attendance, and Learning Twin cognitive analytics.
            </p>
            <div className="flex items-center gap-2 text-[11px] text-[#154539] dark:text-[#a0d1c0] font-bold pt-2">
              <span className="w-2 h-2 rounded-full bg-[#c3f185] animate-ping"></span>
              <span>Cloud-Native • Scandinavian Design • Multi-Tenant RBAC</span>
            </div>
          </div>

          {/* Col 2: Product */}
          <div>
            <h4 className="text-xs font-extrabold uppercase tracking-wider text-[#1c1b1b] dark:text-[#e1e4e1] mb-4">
              Product
            </h4>
            <ul className="space-y-2.5 text-xs text-[#404945] dark:text-[#c0c8c4] font-medium">
              <li>
                <Link href="#features" className="hover:text-[#154539] dark:hover:text-[#a0d1c0] transition-colors">
                  Live Virtual Classroom
                </Link>
              </li>
              <li>
                <Link href="#ai-features" className="hover:text-[#154539] dark:hover:text-[#a0d1c0] transition-colors">
                  24/7 AI Tutor (RAG)
                </Link>
              </li>
              <li>
                <Link href="#ai-features" className="hover:text-[#154539] dark:hover:text-[#a0d1c0] transition-colors">
                  AI Facial Attendance
                </Link>
              </li>
              <li>
                <Link href="#ai-features" className="hover:text-[#154539] dark:hover:text-[#a0d1c0] transition-colors">
                  Learning Twin Radar
                </Link>
              </li>
              <li>
                <Link href="#ai-features" className="hover:text-[#154539] dark:hover:text-[#a0d1c0] transition-colors">
                  GenAI Content Engine
                </Link>
              </li>
            </ul>
          </div>

          {/* Col 3: Solutions */}
          <div>
            <h4 className="text-xs font-extrabold uppercase tracking-wider text-[#1c1b1b] dark:text-[#e1e4e1] mb-4">
              Solutions
            </h4>
            <ul className="space-y-2.5 text-xs text-[#404945] dark:text-[#c0c8c4] font-medium">
              <li>
                <Link href="#solutions" className="hover:text-[#154539] dark:hover:text-[#a0d1c0] transition-colors">
                  Schools (K-12)
                </Link>
              </li>
              <li>
                <Link href="#solutions" className="hover:text-[#154539] dark:hover:text-[#a0d1c0] transition-colors">
                  Colleges & Universities
                </Link>
              </li>
              <li>
                <Link href="#solutions" className="hover:text-[#154539] dark:hover:text-[#a0d1c0] transition-colors">
                  Individual Teachers
                </Link>
              </li>
              <li>
                <Link href="#solutions" className="hover:text-[#154539] dark:hover:text-[#a0d1c0] transition-colors">
                  Coaching Centres
                </Link>
              </li>
              <li>
                <Link href="#solutions" className="hover:text-[#154539] dark:hover:text-[#a0d1c0] transition-colors">
                  Corporate Training
                </Link>
              </li>
            </ul>
          </div>

          {/* Col 4: Resources & Legal */}
          <div>
            <h4 className="text-xs font-extrabold uppercase tracking-wider text-[#1c1b1b] dark:text-[#e1e4e1] mb-4">
              Resources & Legal
            </h4>
            <ul className="space-y-2.5 text-xs text-[#404945] dark:text-[#c0c8c4] font-medium">
              <li>
                <Link href="#faq" className="hover:text-[#154539] dark:hover:text-[#a0d1c0] transition-colors">
                  Documentation & FAQ
                </Link>
              </li>
              <li>
                <Link href="#pricing" className="hover:text-[#154539] dark:hover:text-[#a0d1c0] transition-colors">
                  Pricing Plans
                </Link>
              </li>
              <li>
                <Link href="/privacy" className="hover:text-[#154539] dark:hover:text-[#a0d1c0] transition-colors">
                  Privacy Policy
                </Link>
              </li>
              <li>
                <Link href="/terms" className="hover:text-[#154539] dark:hover:text-[#a0d1c0] transition-colors">
                  Terms of Service
                </Link>
              </li>
              <li>
                <Link href="/security" className="hover:text-[#154539] dark:hover:text-[#a0d1c0] transition-colors">
                  Security & Compliance
                </Link>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="pt-8 border-t border-[#e5e2e1] dark:border-[#2f3732] flex flex-col sm:flex-row justify-between items-center gap-4 text-xs text-[#717975] dark:text-[#c0c8c4]">
          <p>© {new Date().getFullYear()} SmartClass AI Operating System. All rights reserved.</p>

          <div className="flex items-center gap-6">
            <a href="#" className="hover:text-[#154539] dark:hover:text-[#a0d1c0] transition-colors">
              Twitter / X
            </a>
            <a href="#" className="hover:text-[#154539] dark:hover:text-[#a0d1c0] transition-colors">
              LinkedIn
            </a>
            <a href="#" className="hover:text-[#154539] dark:hover:text-[#a0d1c0] transition-colors">
              GitHub
            </a>
            <a href="#" className="hover:text-[#154539] dark:hover:text-[#a0d1c0] transition-colors">
              YouTube
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
