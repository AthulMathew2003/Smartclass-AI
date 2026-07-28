"use client";

import React from "react";

export default function CoreFeaturesSection() {
  const featureCategories = [
    {
      category: "Live Teaching",
      icon: "videocam",
      accentBg: "bg-[#154539] text-white",
      badgeColor: "bg-[#c3f185] text-[#112000]",
      desc: "Low-latency WebRTC interactive classroom environment.",
      items: [
        { label: "HD Video & Audio", icon: "video_camera_front" },
        { label: "Collaborative Whiteboard", icon: "draw" },
        { label: "Screen Sharing", icon: "present_to_all" },
        { label: "Live Q&A & Chat", icon: "forum" },
        { label: "Instant Polls", icon: "poll" },
        { label: "Cloud Class Recording", icon: "videocam" },
      ],
    },
    {
      category: "Intelligent Learning",
      icon: "auto_stories",
      accentBg: "bg-[#ff9a5c] text-[#733200]",
      badgeColor: "bg-[#733200] text-white",
      desc: "Smart assistance helping students master concepts effortlessly.",
      items: [
        { label: "24/7 Interactive Tutor", icon: "menu_book" },
        { label: "Automated Flashcards", icon: "style" },
        { label: "Structured Lecture Notes", icon: "note_alt" },
        { label: "Smart Quiz & MCQ Generator", icon: "quiz" },
        { label: "1-Click PDF Summaries", icon: "summarize" },
      ],
    },
    {
      category: "Assessment & Proctoring",
      icon: "verified_user",
      accentBg: "bg-[#2f5d50] text-[#bceddc]",
      badgeColor: "bg-[#002019] text-[#bceddc]",
      desc: "Secure, automated online examinations and grading.",
      items: [
        { label: "Assignments & Submissions", icon: "assignment" },
        { label: "MCQ & Subjective Exams", icon: "fact_check" },
        { label: "Automated MCQ Grading", icon: "grading" },
        { label: "Webcam Face Proctoring", icon: "security" },
        { label: "Tab Switch & Focus Logger", icon: "tab_unselected" },
      ],
    },
    {
      category: "Student Insights & Analytics",
      icon: "analytics",
      accentBg: "bg-[#3b5f00] text-[#abd970]",
      badgeColor: "bg-[#112000] text-[#abd970]",
      desc: "Biometric attendance, cognitive twin modeling, and performance trees.",
      items: [
        { label: "Facial AI Attendance", icon: "center_focus_strong" },
        { label: "Eye-Gaze & Attention Metrics", icon: "monitoring" },
        { label: "Student Learning Twin", icon: "hub" },
        { label: "Concept Learning Graph", icon: "account_tree" },
        { label: "Predictive Risk Analytics", icon: "trending_up" },
      ],
    },
  ];

  return (
    <section id="features" className="w-full max-w-[1920px] mx-auto px-4 sm:px-8 md:px-12 lg:px-16 py-16 md:py-24">
      <div className="flex flex-col lg:flex-row lg:items-end justify-between mb-16 gap-6">
        <div className="max-w-2xl">
          <span className="bg-[#c3f185] text-[#112000] px-4 py-1.5 rounded-full text-xs font-extrabold uppercase tracking-wider inline-block mb-3">
            Core Capability Matrix
          </span>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#1c1b1b] dark:text-[#e1e4e1] tracking-tight">
            Comprehensive Suite for Every Educational Need
          </h2>
        </div>
        <p className="text-base text-[#404945] dark:text-[#c0c8c4] max-w-md">
          Organized into four core pillars so teachers can focus on teaching while AI handles administration, proctoring, and personalized tutoring.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-8">
        {featureCategories.map((cat, idx) => (
          <div
            key={idx}
            className="bg-[#fcf9f8] dark:bg-[#1b211e] border border-[#e5e2e1] dark:border-[#2f3732] rounded-3xl p-7 shadow-lg hover:shadow-xl transition-all duration-300 flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-6">
                <div className={`w-12 h-12 rounded-2xl flex items-center justify-center shadow-md ${cat.accentBg}`}>
                  <span className="material-symbols-outlined text-2xl">
                    {cat.icon}
                  </span>
                </div>
                <span className={`px-3 py-1 rounded-full text-[10px] font-bold ${cat.badgeColor}`}>
                  Pillar 0{idx + 1}
                </span>
              </div>

              <h3 className="text-2xl font-extrabold text-[#1c1b1b] dark:text-[#e1e4e1] mb-2 tracking-tight">
                {cat.category}
              </h3>
              <p className="text-xs text-[#717975] dark:text-[#c0c8c4] mb-6">
                {cat.desc}
              </p>

              <ul className="space-y-3">
                {cat.items.map((item, i) => (
                  <li
                    key={i}
                    className="flex items-center gap-3 p-2.5 rounded-xl bg-[#f0edec] dark:bg-[#252c28] text-xs font-bold text-[#1c1b1b] dark:text-[#e1e4e1]"
                  >
                    <span className="material-symbols-outlined text-base text-[#154539] dark:text-[#a0d1c0]">
                      {item.icon}
                    </span>
                    <span>{item.label}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
