"use client";

import React from "react";
import Link from "next/link";

export default function PlatformOverviewSection() {
  const cards = [
    {
      title: "Live Virtual Classroom",
      icon: "videocam",
      accent: "bg-[#154539] text-white dark:bg-[#a0d1c0] dark:text-[#00372d]",
      desc: "Conduct interactive WebRTC HD video classes with digital whiteboards, screen sharing, live polls, and automated cloud recordings.",
      badge: "WebRTC HD Video",
    },
    {
      title: "24/7 Smart Tutor",
      icon: "auto_stories",
      accent: "bg-[#ff9a5c] text-[#733200]",
      desc: "Retrieval-Augmented Generation (RAG) powered AI tutor giving context-aware answers from lecture PDFs, notes, and textbooks.",
      badge: "RAG Context Engine",
    },
    {
      title: "Assignments & Submissions",
      icon: "assignment",
      accent: "bg-[#2f5d50] text-[#bceddc]",
      desc: "Create homework assignments with deadlines, multi-file uploads, automated grading criteria, and instant feedback publishing.",
      badge: "Auto Grading",
    },
    {
      title: "Learning Resources Library",
      icon: "library_books",
      accent: "bg-[#c3f185] text-[#112000]",
      desc: "Organize PDFs, slides, and recorded lectures in a searchable cloud repository backed by AI natural language semantic search.",
      badge: "Semantic Search",
    },
    {
      title: "Learning Twin & Skill Model",
      icon: "hub",
      accent: "bg-[#97480f] text-white",
      desc: "A cognitive digital reflection modeling every student's topic mastery, identifying weak areas, and recommending custom study plans.",
      badge: "Cognitive AI",
    },
    {
      title: "Analytics Dashboards",
      icon: "insights",
      accent: "bg-[#3b5f00] text-[#abd970]",
      desc: "Comprehensive analytics for teachers, students, and administrators tracking attendance, grade distributions, and class engagement.",
      badge: "Real-time Metrics",
    },
  ];

  return (
    <section className="w-full max-w-[1920px] mx-auto px-4 sm:px-8 md:px-12 lg:px-16 py-16 md:py-24">
      <div className="text-center max-w-3xl mx-auto mb-16">
        <span className="bg-[#154539] text-[#c3f185] dark:bg-[#a0d1c0] dark:text-[#00372d] px-4 py-1.5 rounded-full text-xs font-extrabold uppercase tracking-wider inline-block mb-3">
          Beyond Traditional LMS
        </span>
        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#1c1b1b] dark:text-[#e1e4e1] tracking-tight">
          Everything You Need for Modern Education
        </h2>
        <p className="text-base sm:text-lg text-[#404945] dark:text-[#c0c8c4] mt-4 leading-relaxed">
          SmartClass AI combines live WebRTC teaching, automated assessment workflows, and generative cognitive AI into a unified platform.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        {cards.map((card, idx) => (
          <div
            key={idx}
            className="bg-[#fcf9f8] dark:bg-[#1b211e] border border-[#e5e2e1] dark:border-[#2f3732] rounded-3xl p-8 shadow-lg hover:shadow-2xl transition-all duration-300 flex flex-col justify-between group hover:-translate-y-1.5"
          >
            <div>
              <div className="flex items-center justify-between mb-6">
                <div className={`w-12 h-12 rounded-2xl flex items-center justify-center shadow-md ${card.accent}`}>
                  <span className="material-symbols-outlined text-2xl">
                    {card.icon}
                  </span>
                </div>
                <span className={`px-3 py-1 rounded-full text-[11px] font-extrabold ${card.accent}`}>
                  {card.badge}
                </span>
              </div>
              <h3 className="text-2xl font-extrabold text-[#1c1b1b] dark:text-[#e1e4e1] mb-3 tracking-tight group-hover:text-[#154539] dark:group-hover:text-[#a0d1c0] transition-colors">
                {card.title}
              </h3>
              <p className="text-sm text-[#404945] dark:text-[#c0c8c4] leading-relaxed mb-6">
                {card.desc}
              </p>
            </div>

            <Link
              href="#ai-features"
              className="inline-flex items-center gap-1.5 text-xs font-extrabold text-[#154539] dark:text-[#a0d1c0] group-hover:underline pt-4 border-t border-[#e5e2e1]/60 dark:border-[#2f3732]"
            >
              <span>Explore Capability</span>
              <span className="material-symbols-outlined text-base transition-transform group-hover:translate-x-1">
                arrow_forward
              </span>
            </Link>
          </div>
        ))}
      </div>
    </section>
  );
}
