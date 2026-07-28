"use client";

import React from "react";

export default function HowItWorksSection() {
  const steps = [
    {
      num: "01",
      title: "Create Workspace",
      desc: "Set up your institution, school, department, or individual teacher portal in under 2 minutes with customizable roles.",
      icon: "domain_add",
      badge: "Instant Setup",
    },
    {
      num: "02",
      title: "Invite Teachers & Students",
      desc: "Bulk import users via CSV or send direct email invitations. Assign RBAC roles (Teacher, Student, Admin, HOD, TA).",
      icon: "group_add",
      badge: "Bulk RBAC Import",
    },
    {
      num: "03",
      title: "Teach & Learn",
      desc: "Host WebRTC live classes, share PDFs/PPTs, let GenAI generate flashcards, and run proctored online assessments.",
      icon: "school",
      badge: "WebRTC & GenAI",
    },
    {
      num: "04",
      title: "Track Progress with AI",
      desc: "Monitor AI biometric facial attendance, review Learning Twins cognitive radar, and act on early risk alerts.",
      icon: "insights",
      badge: "Learning Twin AI",
    },
  ];

  return (
    <section className="w-full max-w-[1920px] mx-auto px-4 sm:px-8 md:px-12 lg:px-16 py-16 md:py-24 bg-[#154539] text-white rounded-3xl my-8 relative overflow-hidden shadow-2xl">
      {/* Background Decorative Rings */}
      <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-[#c3f185]/10 rounded-full blur-3xl pointer-events-none"></div>

      <div className="text-center max-w-3xl mx-auto mb-16 relative z-10">
        <span className="bg-[#c3f185] text-[#112000] px-4 py-1.5 rounded-full text-xs font-extrabold uppercase tracking-wider inline-block mb-3">
          Seamless Workflow
        </span>
        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight">
          How SmartClass AI Works
        </h2>
        <p className="text-base sm:text-lg text-[#a3d4c3] mt-3">
          Get your institution up and running in 4 straightforward steps.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 relative z-10">
        {steps.map((step, idx) => (
          <div
            key={idx}
            className="bg-[#2f5d50] border border-white/10 rounded-3xl p-7 flex flex-col justify-between relative group hover:bg-[#1f483d] transition-all duration-300"
          >
            {/* Step Number Floating Badge */}
            <div className="flex justify-between items-start mb-6">
              <span className="text-4xl font-extrabold text-[#c3f185] font-mono">
                {step.num}
              </span>
              <div className="w-10 h-10 rounded-2xl bg-white/10 flex items-center justify-center text-[#c3f185]">
                <span className="material-symbols-outlined text-2xl">
                  {step.icon}
                </span>
              </div>
            </div>

            <div>
              <span className="bg-white/10 text-[#bceddc] px-3 py-1 rounded-full text-[10px] font-bold inline-block mb-3">
                {step.badge}
              </span>
              <h3 className="text-xl font-extrabold mb-2">{step.title}</h3>
              <p className="text-xs text-[#bceddc]/80 leading-relaxed">
                {step.desc}
              </p>
            </div>

            {/* Connecting Arrow for Desktop */}
            {idx < steps.length - 1 && (
              <div className="hidden lg:block absolute top-1/2 -right-4 -translate-y-1/2 z-20 text-[#c3f185]">
                <span className="material-symbols-outlined text-2xl">
                  chevron_right
                </span>
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
