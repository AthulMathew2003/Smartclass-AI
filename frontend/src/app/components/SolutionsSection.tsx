"use client";

import React from "react";
import Link from "next/link";

export default function SolutionsSection() {
  const solutions = [
    {
      title: "Schools (K-12)",
      icon: "school",
      tag: "K-12 Network",
      accent: "bg-[#154539] text-white dark:bg-[#a0d1c0] dark:text-[#00372d]",
      features: [
        "Automated facial attendance",
        "Parent portal & progress reports",
        "Gradebook & assignment tracking",
        "Interactive live virtual classrooms",
      ],
    },
    {
      title: "Colleges & Universities",
      icon: "account_balance",
      tag: "Higher Education",
      accent: "bg-[#ff9a5c] text-[#733200]",
      features: [
        "Multi-tenant department architecture",
        "AI proctored online examinations",
        "Learning Twin skill radar analytics",
        "Semantic search across research PDFs",
      ],
    },
    {
      title: "Individual Teachers",
      icon: "person",
      tag: "Solo Educators",
      accent: "bg-[#c3f185] text-[#112000]",
      features: [
        "Zero-infrastructure setup",
        "One-click GenAI quiz & note generation",
        "Live WebRTC classroom room links",
        "Automated student attendance logs",
      ],
    },
    {
      title: "Coaching Centres",
      icon: "lightbulb",
      tag: "Test Prep Hubs",
      accent: "bg-[#2f5d50] text-[#bceddc]",
      features: [
        "Batch & timetable scheduling",
        "MCQ test bank & mock exam generator",
        "Student ranking & leaderboard",
        "Doubt resolution AI Tutor bot",
      ],
    },
    {
      title: "Corporate Training",
      icon: "business",
      tag: "Enterprise Ops",
      accent: "bg-[#97480f] text-white",
      features: [
        "Employee onboarding pathways",
        "Skill gap matrix & twin analytics",
        "Proctored certification testing",
        "SSO & Microsoft/Google OAuth integration",
      ],
    },
    {
      title: "Self Learners",
      icon: "workspace_premium",
      tag: "Independent Study",
      accent: "bg-[#3b5f00] text-[#abd970]",
      features: [
        "24/7 Personal RAG AI Tutor",
        "Concept Learning Graph pathfinder",
        "Spaced repetition flashcards",
        "Custom PDF & video summarizer",
      ],
    },
  ];

  return (
    <section id="solutions" className="w-full max-w-[1920px] mx-auto px-4 sm:px-8 md:px-12 lg:px-16 py-16 md:py-24">
      <div className="text-center max-w-3xl mx-auto mb-16">
        <span className="bg-[#ff9a5c] text-[#733200] px-4 py-1.5 rounded-full text-xs font-extrabold uppercase tracking-wider inline-block mb-3">
          Tailored Architecture
        </span>
        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#1c1b1b] dark:text-[#e1e4e1] tracking-tight">
          Built for Every Learning Environment
        </h2>
        <p className="text-base sm:text-lg text-[#404945] dark:text-[#c0c8c4] mt-3">
          Whether you are a solo educator or a university network, SmartClass AI scales to your exact academic needs.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        {solutions.map((sol, idx) => (
          <div
            key={idx}
            className="bg-[#fcf9f8] dark:bg-[#1b211e] border border-[#e5e2e1] dark:border-[#2f3732] rounded-3xl p-8 shadow-lg hover:shadow-2xl transition-all duration-300 flex flex-col justify-between group hover:-translate-y-1"
          >
            <div>
              <div className="flex items-center justify-between mb-6">
                <div className={`w-12 h-12 rounded-2xl flex items-center justify-center shadow-md ${sol.accent}`}>
                  <span className="material-symbols-outlined text-2xl">
                    {sol.icon}
                  </span>
                </div>
                <span className={`px-3.5 py-1 rounded-full text-[11px] font-extrabold ${sol.accent}`}>
                  {sol.tag}
                </span>
              </div>

              <h3 className="text-2xl font-extrabold text-[#1c1b1b] dark:text-[#e1e4e1] mb-4 tracking-tight group-hover:text-[#154539] dark:group-hover:text-[#a0d1c0] transition-colors">
                {sol.title}
              </h3>

              <ul className="space-y-3 mb-8">
                {sol.features.map((feat, fIdx) => (
                  <li key={fIdx} className="flex items-center gap-2.5 text-xs text-[#404945] dark:text-[#c0c8c4]">
                    <span className="material-symbols-outlined text-[#154539] dark:text-[#a0d1c0] text-sm">
                      check_circle
                    </span>
                    <span>{feat}</span>
                  </li>
                ))}
              </ul>
            </div>

            <Link
              href="/login"
              className="inline-flex items-center justify-between bg-[#f0edec] dark:bg-[#252c28] hover:bg-[#154539] hover:text-white dark:hover:bg-[#a0d1c0] dark:hover:text-[#00372d] p-4 rounded-2xl transition-all font-bold text-xs group/btn"
            >
              <span>Explore Solution for {sol.title}</span>
              <span className="material-symbols-outlined text-base group-hover/btn:translate-x-1 transition-transform">
                arrow_forward
              </span>
            </Link>
          </div>
        ))}
      </div>
    </section>
  );
}
