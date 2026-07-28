"use client";

import React, { useState } from "react";
import Link from "next/link";

export default function RolePreviewSection() {
  const [activeRole, setActiveRole] = useState<"student" | "teacher" | "admin">("student");

  const roleDetails = {
    student: {
      title: "Student Learning Experience",
      subtitle: "Personalized 24/7 AI tutor, progress tracking, live classes, and interactive quizzes.",
      stats: [
        { label: "AI Study Assistance", val: "24/7 RAG Tutor" },
        { label: "Knowledge Progress", val: "94.2% Mastery" },
        { label: "Live Classroom", val: "WebRTC HD Rooms" },
      ],
      features: [
        "Ask AI Tutor questions grounded in course materials",
        "View personal Learning Twin cognitive progress map",
        "Submit assignments & receive automated teacher feedback",
        "Attempt AI-proctored MCQ & coding examinations",
        "Review auto-generated flashcards & lecture summaries"
      ],
      ctaText: "Launch Student Portal",
      ctaRoute: "/dashboard?role=student",
      image: "https://lh3.googleusercontent.com/aida-public/AB6AXuBYnXXVkR5IkuJrgSTCTyU3y1oaQ0kOQGbdiiIaVAQAkdCdrs0VKlWJRkVANdDbLMJ2m1dMuFPIU8D6FI2KRWNEzTgjU29qYbmHKmu3byt1TuVOsPixKxc0sH_GSH3CWLGyRCjpfsiRkAsFLPv3iPsSGNh55x2L7PzRjxJlyxcWuVonFynFWrQWNzyGswl05yXiz-pmGWDlZwqqLr0U0RcMjg5QFcnvBaZEE6Us2vaH_NA9Z43avZ_c_OCx8BIM1J5cy1yjdGHt4AJu"
    },
    teacher: {
      title: "Educator & Teacher Suite",
      subtitle: "Automate grading, monitor real-time classroom engagement, and generate study content in seconds.",
      stats: [
        { label: "Prep Time Saved", val: "80% Reduction" },
        { label: "Attendance Accuracy", val: "99.8% Facial AI" },
        { label: "Live Class Tools", val: "Whiteboard & Polls" },
      ],
      features: [
        "Schedule & host WebRTC live classes with cloud recording",
        "Automate student attendance via facial recognition check-in",
        "Monitor head-pose & eye-gaze engagement during lectures",
        "Generate quizzes, summaries & flashcards from PDFs in 1-click",
        "Review proctoring violation reports for online exams"
      ],
      ctaText: "Launch Educator Portal",
      ctaRoute: "/dashboard?role=teacher",
      image: "https://lh3.googleusercontent.com/aida-public/AB6AXuCyTbmIM6GaMaCtLq6grG5rxLk5qV4S2OR_tghfGFJHfjpQe_-MGKBmEILSPWIct9gSJJwl2qAfDkKMontCkSw1xgddQ4MSQ_g6wQaZie42dhBwOriRTi2ld9iSP-CtTeWxB2yPRjpFbix803MkaX6uAUQC-vNQ7r6Xh3AyJL8X2XEzc6f6aDukDEVGk6CEWq4M9oaygNr58eiFxHaClNM8hhrDTs0nYfjTHEKMKsarb6yQSJqrNZ4u58pg4wOnqdmz69P76eLL5SFH"
    },
    admin: {
      title: "Institutional Administrator OS",
      subtitle: "Multi-tenant governance, department scheduling, custom RBAC permissions, and system analytics.",
      stats: [
        { label: "Tenant Architecture", val: "Multi-Tenant SaaS" },
        { label: "RBAC Security", val: "Custom Roles" },
        { label: "Academic Control", val: "Full Department OS" },
      ],
      features: [
        "Manage departments, degree programs, semesters & batches",
        "Define granular Custom Roles & permissions (HOD, Exam Controller)",
        "Oversee institutional usage, faculty allocation & storage",
        "View macro academic performance & risk dashboards",
        "Configure AI model guardrails & institutional settings"
      ],
      ctaText: "Launch Admin Console",
      ctaRoute: "/dashboard?role=admin",
      image: "https://lh3.googleusercontent.com/aida-public/AB6AXuC0anBl1K2YHYIJA2wj-Jlgb9X_6tnFsrgUWo--pDmwHINVsLY5_IVMWzdqdCAU6S9Aqgo5TAR1DDguGOvNnHm2c6XBjslBFsMvWheuOQjZ5OZEVYKojBLlwmSnpLr5AxvaPj3QNcsldx0_H2cePJ4wUFNUvV-8VWzcmtw9B7hbUSIe9OJiBecBfHkjuueihrM0zPhN_gEw7jBaEjNLEOb26Kzoefiybwcm2RNymu3jiY-cHZdgYXZ40J5-aIRGM5Tk3Ou6ttBwdK7u"
    }
  };

  const active = roleDetails[activeRole];

  return (
    <section className="w-full max-w-[1920px] mx-auto px-4 sm:px-8 md:px-12 lg:px-16 py-16 md:py-24">
      <div className="bg-[#f0edec] dark:bg-[#1b211e] rounded-3xl p-6 sm:p-10 border border-[#e5e2e1] dark:border-[#2f3732] shadow-xl">
        {/* Header and Role Tabs */}
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6 mb-10 pb-6 border-b border-[#e5e2e1] dark:border-[#2f3732]">
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-[#154539] dark:text-[#a0d1c0]">
              Customized For Every Stakeholder
            </span>
            <h2 className="text-3xl font-extrabold text-[#1c1b1b] dark:text-[#e1e4e1] mt-1">
              Role-Based Adaptive Workspaces
            </h2>
          </div>

          <div className="flex bg-[#e5e2e1] dark:bg-[#252c28] p-1.5 rounded-full">
            <button
              onClick={() => setActiveRole("student")}
              className={`px-5 py-2 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 ${
                activeRole === "student"
                  ? "bg-[#154539] text-white dark:bg-[#a0d1c0] dark:text-[#00372d] shadow-md"
                  : "text-[#404945] dark:text-[#c0c8c4] hover:text-[#1c1b1b]"
              }`}
            >
              <span className="material-symbols-outlined text-sm">person</span>
              <span>Student</span>
            </button>

            <button
              onClick={() => setActiveRole("teacher")}
              className={`px-5 py-2 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 ${
                activeRole === "teacher"
                  ? "bg-[#154539] text-white dark:bg-[#a0d1c0] dark:text-[#00372d] shadow-md"
                  : "text-[#404945] dark:text-[#c0c8c4] hover:text-[#1c1b1b]"
              }`}
            >
              <span className="material-symbols-outlined text-sm">co_present</span>
              <span>Educator</span>
            </button>

            <button
              onClick={() => setActiveRole("admin")}
              className={`px-5 py-2 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 ${
                activeRole === "admin"
                  ? "bg-[#154539] text-white dark:bg-[#a0d1c0] dark:text-[#00372d] shadow-md"
                  : "text-[#404945] dark:text-[#c0c8c4] hover:text-[#1c1b1b]"
              }`}
            >
              <span className="material-symbols-outlined text-sm">admin_panel_settings</span>
              <span>Administrator</span>
            </button>
          </div>
        </div>

        {/* Dynamic Details Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
          <div>
            <h3 className="text-2xl font-bold text-[#1c1b1b] dark:text-[#e1e4e1] mb-2">
              {active.title}
            </h3>
            <p className="text-sm text-[#404945] dark:text-[#c0c8c4] mb-6 leading-relaxed">
              {active.subtitle}
            </p>

            {/* Metrics */}
            <div className="grid grid-cols-3 gap-3 mb-6">
              {active.stats.map((s, i) => (
                <div
                  key={i}
                  className="bg-[#fcf9f8] dark:bg-[#141816] p-3 rounded-2xl border border-[#e5e2e1] dark:border-[#2f3732]"
                >
                  <p className="text-xs text-[#717975] dark:text-[#c0c8c4] font-medium">
                    {s.label}
                  </p>
                  <p className="text-sm sm:text-base font-extrabold text-[#154539] dark:text-[#a0d1c0] mt-0.5">
                    {s.val}
                  </p>
                </div>
              ))}
            </div>

            {/* Features Bullet List */}
            <div className="space-y-2.5 mb-8">
              {active.features.map((f, i) => (
                <div key={i} className="flex items-start gap-2 text-xs sm:text-sm text-[#1c1b1b] dark:text-[#e1e4e1]">
                  <span className="material-symbols-outlined text-[#154539] dark:text-[#a0d1c0] text-base mt-0.5">
                    check_circle
                  </span>
                  <span>{f}</span>
                </div>
              ))}
            </div>

            <Link
              href={active.ctaRoute}
              className="inline-flex items-center gap-2 bg-[#154539] hover:bg-[#2f5d50] text-white dark:bg-[#a0d1c0] dark:text-[#00372d] px-7 py-3 rounded-full font-bold text-sm shadow-md hover:scale-105 transition-all"
            >
              <span>{active.ctaText}</span>
              <span className="material-symbols-outlined text-base">arrow_forward</span>
            </Link>
          </div>

          <div className="relative rounded-2xl overflow-hidden aspect-video shadow-xl border border-[#e5e2e1] dark:border-[#2f3732] group">
            <img
              src={active.image}
              alt={active.title}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent flex items-end p-6">
              <span className="bg-[#c3f185] text-[#112000] px-3.5 py-1 rounded-full text-xs font-extrabold">
                Live Interactive Dashboard Preview
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
