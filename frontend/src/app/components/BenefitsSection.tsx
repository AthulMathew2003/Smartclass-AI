"use client";

import React from "react";

export default function BenefitsSection() {
  const benefits = [
    {
      title: "Reduce Administrative Work",
      desc: "Save 80% of preparation time per lecture. GenAI automatically creates lecture summaries, flashcards, and MCQ quizzes from uploaded PDFs.",
      icon: "bolt",
      stat: "80% Less Prep",
      accent: "bg-[#c3f185] text-[#112000]",
    },
    {
      title: "Improve Student Engagement",
      desc: "Boost active participation with interactive polls, live whiteboards, and AI eye-gaze attention monitoring to detect distraction early.",
      icon: "trending_up",
      stat: "94% Active Rate",
      accent: "bg-[#ff9a5c] text-[#733200]",
    },
    {
      title: "Conduct Interactive Live Classes",
      desc: "Stream low-latency HD video with built-in screen sharing, whiteboards, breakout Q&A, and automated cloud recording transcriptions.",
      icon: "videocam",
      accent: "bg-[#bceddc] text-[#002019]",
      stat: "HD WebRTC",
    },
    {
      title: "Automate Attendance",
      desc: "Biometric 1-to-N face verification automatically checks in students as they join, tracking join time, exit time, and duration.",
      icon: "center_focus_strong",
      stat: "0 Proxy Check-ins",
      accent: "bg-[#c3f185] text-[#112000]",
    },
    {
      title: "Generate Learning Content Instantly",
      desc: "Upload textbook chapters or lecture recordings and instantly produce spaced-repetition study cards, summaries, and self-evaluating tests.",
      icon: "edit_note",
      stat: "Instant GenAI",
      accent: "bg-[#ff9a5c] text-[#733200]",
    },
    {
      title: "Track Learning Progress",
      desc: "Student Learning Twins and concept Learning Graphs continuously model topic mastery, identifying weak areas before final exams.",
      icon: "hub",
      stat: "Cognitive Radar",
      accent: "bg-[#bceddc] text-[#002019]",
    },
  ];

  return (
    <section className="w-full max-w-[1920px] mx-auto px-4 sm:px-8 md:px-12 lg:px-16 py-16 md:py-24">
      <div className="text-center max-w-3xl mx-auto mb-16">
        <span className="bg-[#154539] text-[#c3f185] dark:bg-[#a0d1c0] dark:text-[#00372d] px-4 py-1.5 rounded-full text-xs font-extrabold uppercase tracking-wider inline-block mb-3">
          Proven Outcomes
        </span>
        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#1c1b1b] dark:text-[#e1e4e1] tracking-tight">
          Why Educational Leaders Choose SmartClass AI
        </h2>
        <p className="text-base sm:text-lg text-[#404945] dark:text-[#c0c8c4] mt-3">
          Move away from fragmented software stacks to a single system that yields tangible academic results.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        {benefits.map((b, idx) => (
          <div
            key={idx}
            className="bg-[#fcf9f8] dark:bg-[#1b211e] border border-[#e5e2e1] dark:border-[#2f3732] rounded-3xl p-8 shadow-lg hover:shadow-2xl transition-all duration-300 flex flex-col justify-between group hover:-translate-y-1"
          >
            <div>
              <div className="flex items-center justify-between mb-6">
                <div className="w-12 h-12 rounded-2xl bg-[#154539] text-[#c3f185] flex items-center justify-center shadow-md">
                  <span className="material-symbols-outlined text-2xl">
                    {b.icon}
                  </span>
                </div>
                <span className={`px-3 py-1 rounded-full text-[11px] font-extrabold ${b.accent}`}>
                  {b.stat}
                </span>
              </div>

              <div className="flex items-center gap-2 mb-2">
                <span className="material-symbols-outlined text-[#154539] dark:text-[#a0d1c0] text-xl font-bold">
                  check_circle
                </span>
                <h3 className="text-xl font-extrabold text-[#1c1b1b] dark:text-[#e1e4e1] tracking-tight">
                  {b.title}
                </h3>
              </div>

              <p className="text-sm text-[#404945] dark:text-[#c0c8c4] leading-relaxed mt-2">
                {b.desc}
              </p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
