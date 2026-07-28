"use client";

import React, { useState } from "react";

export default function AiFeaturesShowcase() {
  const [activeTab, setActiveTab] = useState<number>(0);

  const aiFeatures = [
    {
      id: "ai-tutor",
      title: "24/7 Smart Tutor (RAG)",
      icon: "auto_stories",
      badge: "Retrieval-Augmented Gen",
      tagline: "Context-aware AI assistant grounded in institution-specific textbooks, PDFs, and lecture notes.",
      points: [
        "Answers student questions with exact page number citations",
        "Breaks down complex formulas and coding problems step-by-step",
        "Supports multi-turn interactive conversations with topic memory",
      ],
      demoSnippet: `Q: Explain Newton's 2nd Law from Physics_101.pdf\n\nAI Tutor: According to Physics_101.pdf (Page 42), Newton's Second Law defines F = m * a. Force is directly proportional to acceleration...`,
    },
    {
      id: "ai-attendance",
      title: "Facial AI Attendance",
      icon: "center_focus_strong",
      badge: "Biometric Computer Vision",
      tagline: "Automated face recognition check-ins eliminate proxy attendance in live & physical classes.",
      points: [
        "1-to-N face detection upon entering virtual WebRTC classroom",
        "Logs join time, exit time, and calculated attendance percentage",
        "Anti-spoofing liveness detection prevents photo/video proxies",
      ],
      demoSnippet: `[AI Vision Log]\n✓ Verified: Sarah Jenkins (ID: 2026-8812)\n• Join Time: 09:00:04 AM\n• Match Confidence: 99.4%\n• Attendance Logged: Present (100%)`,
    },
    {
      id: "behaviour-analysis",
      title: "Classroom Engagement AI",
      icon: "monitoring",
      badge: "Eye-Gaze & Attention",
      tagline: "Measures real-time presence, head pose estimation, and gaze orientation for attention metrics.",
      points: [
        "Calculates class attention index without compromising student privacy",
        "Provides live feedback alerts to teachers during lectures",
        "Correlates engagement spikes with specific lecture topics",
      ],
      demoSnippet: `[Class Attention Index: 94.2%]\n• Face Presence: 34 / 34 Active\n• Avg Gaze On-screen: 91%\n• Top Active Topic: "Neural Networks Architecture"`,
    },
    {
      id: "learning-twin",
      title: "Student Learning Twin",
      icon: "hub",
      badge: "Cognitive Profile",
      tagline: "A continuous digital model representing knowledge, strengths, weaknesses, and risk factors.",
      points: [
        "Identifies foundational weak topics before final examinations",
        "Generates customized daily learning pathways and study plans",
        "Predicts student performance trajectory and flags at-risk learners",
      ],
      demoSnippet: `[Cognitive Profile - Calculus II]\n★ Strong: Differentiation (96%), Limits (92%)\n⚠ Needs Review: Integration by Parts (64%)\n➜ Action: Recommended 15-min practice quiz generated`,
    },
    {
      id: "learning-graph",
      title: "Concept Learning Graph",
      icon: "account_tree",
      badge: "Prerequisite Dependency",
      tagline: "Maps concept dependencies to visualize prerequisite topics and recommended study paths.",
      points: [
        "Interactive node-link graph showing how concepts interlock",
        "Detects missing foundational knowledge when students struggle",
        "Enables self-paced non-linear learning exploration",
      ],
      demoSnippet: `[Learning Graph Pathway]\nCalculus I ➔ Derivatives ➔ Integrals ➔ Differential Equations\n✓ Prerequisite Status: Clear\n➜ Ready for Advanced Dynamics`,
    },
    {
      id: "ai-gen",
      title: "AI Study Material Generator",
      icon: "edit_note",
      badge: "1-Click Content Engine",
      tagline: "Converts uploaded PDFs, slides, and video transcripts into summaries, flashcards, and quizzes.",
      points: [
        "Saves educators 80% of preparation time per lecture",
        "Generates self-evaluating MCQ and subjective question papers",
        "Creates spaced-repetition flashcards for quick student review",
      ],
      demoSnippet: `[GenAI Processing Output]\nInput: Lecture_04_Machine_Learning.pdf\n✓ Summary Generated (340 words)\n✓ 10 Spaced Repetition Flashcards Created\n✓ 5 MCQ Practice Questions Ready`,
    },
  ];

  const current = aiFeatures[activeTab];

  return (
    <section id="ai-features" className="w-full max-w-[1920px] mx-auto px-4 sm:px-8 md:px-12 lg:px-16 py-16 md:py-24">
      <div className="text-center max-w-3xl mx-auto mb-16">
        <span className="bg-[#c3f185] text-[#112000] px-4 py-1.5 rounded-full text-xs font-extrabold uppercase tracking-wider inline-block mb-3">
          Artificial Intelligence Suite
        </span>
        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#1c1b1b] dark:text-[#e1e4e1] tracking-tight">
          Pioneering GenAI & Computer Vision Features
        </h2>
        <p className="text-base sm:text-lg text-[#404945] dark:text-[#c0c8c4] mt-3">
          Explore how our custom AI models transform learning, assessment, and classroom engagement.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
        {/* Left Side: Tabs List */}
        <div className="lg:col-span-4 space-y-3">
          {aiFeatures.map((feat, idx) => (
            <button
              key={feat.id}
              onClick={() => setActiveTab(idx)}
              className={`w-full text-left p-5 rounded-2xl border transition-all flex items-center justify-between group ${
                activeTab === idx
                  ? "bg-[#154539] text-white border-[#154539] dark:bg-[#a0d1c0] dark:text-[#00372d] dark:border-[#a0d1c0] shadow-lg scale-[1.02]"
                  : "bg-[#fcf9f8] dark:bg-[#1b211e] text-[#1c1b1b] dark:text-[#e1e4e1] border-[#e5e2e1] dark:border-[#2f3732] hover:bg-[#f0edec] dark:hover:bg-[#252c28]"
              }`}
            >
              <div className="flex items-center gap-3.5">
                <div
                  className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold ${
                    activeTab === idx
                      ? "bg-[#c3f185] text-[#112000]"
                      : "bg-[#f0edec] dark:bg-[#252c28] text-[#154539] dark:text-[#a0d1c0]"
                  }`}
                >
                  <span className="material-symbols-outlined text-xl">
                    {feat.icon}
                  </span>
                </div>
                <div>
                  <p className="text-sm font-extrabold">{feat.title}</p>
                  <p className="text-[11px] opacity-75">{feat.badge}</p>
                </div>
              </div>

              <span className="material-symbols-outlined text-lg group-hover:translate-x-1 transition-transform">
                chevron_right
              </span>
            </button>
          ))}
        </div>

        {/* Right Side: Interactive Feature Visual Display */}
        <div className="lg:col-span-8 bg-[#f0edec] dark:bg-[#1b211e] border border-[#e5e2e1] dark:border-[#2f3732] rounded-3xl p-8 sm:p-10 shadow-2xl flex flex-col justify-between relative overflow-hidden">
          {/* Subtle Background Glow */}
          <div className="absolute top-0 right-0 w-80 h-80 bg-[#c3f185]/10 rounded-full blur-3xl pointer-events-none"></div>

          <div>
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-2xl bg-[#154539] text-[#c3f185] flex items-center justify-center shadow-md">
                  <span className="material-symbols-outlined text-2xl">
                    {current.icon}
                  </span>
                </div>
                <div>
                  <span className="bg-[#c3f185] text-[#112000] px-3 py-1 rounded-full text-[10px] font-extrabold uppercase tracking-wider">
                    {current.badge}
                  </span>
                  <h3 className="text-2xl font-extrabold text-[#1c1b1b] dark:text-[#e1e4e1] mt-1">
                    {current.title}
                  </h3>
                </div>
              </div>
            </div>

            <p className="text-base text-[#404945] dark:text-[#c0c8c4] leading-relaxed mb-6 font-medium">
              {current.tagline}
            </p>

            <div className="space-y-3 mb-8">
              {current.points.map((pt, i) => (
                <div
                  key={i}
                  className="flex items-start gap-3 p-3 rounded-2xl bg-[#fcf9f8] dark:bg-[#252c28] border border-[#e5e2e1] dark:border-[#2f3732]"
                >
                  <span className="material-symbols-outlined text-[#154539] dark:text-[#a0d1c0] text-lg mt-0.5">
                    check_circle
                  </span>
                  <span className="text-xs font-bold text-[#1c1b1b] dark:text-[#e1e4e1]">
                    {pt}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Interactive Simulated Terminal / Snippet Box */}
          <div className="bg-[#141816] text-[#c3f185] p-5 rounded-2xl font-mono text-xs shadow-inner border border-white/10 relative">
            <div className="flex items-center justify-between text-[10px] text-[#717975] pb-2 border-b border-white/10 mb-3">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500"></span>
                <span className="w-2.5 h-2.5 rounded-full bg-yellow-500"></span>
                <span className="w-2.5 h-2.5 rounded-full bg-green-500"></span>
                <span className="ml-2 font-sans font-bold text-white/60">Live AI Output Simulator</span>
              </div>
              <span className="text-[#a0d1c0]">STATUS: ACTIVE</span>
            </div>
            <pre className="whitespace-pre-wrap leading-relaxed font-mono">
              {current.demoSnippet}
            </pre>
          </div>
        </div>
      </div>
    </section>
  );
}
