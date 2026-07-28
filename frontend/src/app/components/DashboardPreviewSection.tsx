"use client";

import React, { useState } from "react";
import Link from "next/link";

export default function DashboardPreviewSection() {
  const [activeTab, setActiveTab] = useState<"student" | "teacher" | "admin">("student");

  const previews = {
    student: {
      title: "Student Portal Dashboard",
      subtitle: "Personalized course hub with 24/7 AI tutor widget, Learning Twin skill radar, and assignment schedule.",
      badge: "Student View",
      badgeColor: "bg-[#c3f185] text-[#112000]",
      stat1: { label: "Course Mastery", val: "94.2%" },
      stat2: { label: "Assignments Due", val: "2 Pending" },
      stat3: { label: "AI Tutor Sessions", val: "18 Completed" },
      mockWidgetTitle: "Active WebRTC Session & AI Assistant",
      mockContent: [
        { label: "Advanced Physics 301", desc: "Live Session in Progress • Dr. Marcus Vance", status: "JOIN CLASS" },
        { label: "Calculus II Assignment", desc: "Due Tomorrow at 11:59 PM • 3 Problems Remaining", status: "SUBMIT NOW" },
        { label: "AI Learning Twin Insight", desc: "Suggested review: Integration by Parts (15 mins)", status: "START REVIEW" },
      ],
      route: "/dashboard?role=student",
    },
    teacher: {
      title: "Educator Suite Dashboard",
      subtitle: "Control room for conducting WebRTC classes, monitoring live facial attendance, and GenAI paper creation.",
      badge: "Teacher View",
      badgeColor: "bg-[#ff9a5c] text-[#733200]",
      stat1: { label: "Enrolled Students", val: "142 Active" },
      stat2: { label: "Avg Class Attention", val: "92.8%" },
      stat3: { label: "GenAI Prep Saved", val: "14.5 Hours" },
      mockWidgetTitle: "Classroom Management & Auto-Grader",
      mockContent: [
        { label: "Batch 2026-A: Machine Learning", desc: "34 Students Online • Facial Attendance 98.4%", status: "LAUNCH CLASSROOM" },
        { label: "Calculus II Quiz 4 Grading", desc: "Auto-graded 32 MCQs • 2 Subjective Pending", status: "REVIEW GRADES" },
        { label: "GenAI Material Generator", desc: "Create Quiz from Lecture_05.pdf", status: "GENERATE" },
      ],
      route: "/dashboard?role=teacher",
    },
    admin: {
      title: "Administrator Console",
      subtitle: "Macro academic health governance, RBAC role management, multi-tenant department overview, and audit trails.",
      badge: "Admin Console",
      badgeColor: "bg-[#bceddc] text-[#002019]",
      stat1: { label: "Total Departments", val: "12 Enrolled" },
      stat2: { label: "Active Users Today", val: "1,840 Users" },
      stat3: { label: "Platform Uptime", val: "99.99%" },
      mockWidgetTitle: "Institutional Security & Multi-Tenant Governance",
      mockContent: [
        { label: "Multi-Tenant Department Setup", desc: "Configure Semester & Academic Year timetables", status: "CONFIGURE" },
        { label: "RBAC Custom Role Creator", desc: "Manage permissions for HODs, TAs, & Faculty", status: "MANAGE ROLES" },
        { label: "AI Safety & Audit Trail", desc: "View system audit logs & RAG guardrail settings", status: "VIEW LOGS" },
      ],
      route: "/dashboard?role=admin",
    },
  };

  const active = previews[activeTab];

  return (
    <section className="w-full max-w-[1920px] mx-auto px-4 sm:px-8 md:px-12 lg:px-16 py-16 md:py-24">
      <div className="text-center max-w-3xl mx-auto mb-12">
        <span className="bg-[#154539] text-[#c3f185] dark:bg-[#a0d1c0] dark:text-[#00372d] px-4 py-1.5 rounded-full text-xs font-extrabold uppercase tracking-wider inline-block mb-3">
          Role-Based Interfaces
        </span>
        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#1c1b1b] dark:text-[#e1e4e1] tracking-tight">
          Tailored Dashboard Workspaces
        </h2>
        <p className="text-base sm:text-lg text-[#404945] dark:text-[#c0c8c4] mt-3">
          Experience purpose-built interfaces optimized specifically for students, teachers, and administrators.
        </p>

        {/* Tab Buttons */}
        <div className="flex justify-center bg-[#f0edec] dark:bg-[#252c28] p-1.5 rounded-full mt-8 max-w-md mx-auto border border-[#e5e2e1] dark:border-[#2f3732]">
          <button
            onClick={() => setActiveTab("student")}
            className={`flex-1 py-2.5 rounded-full text-xs font-extrabold transition-all flex items-center justify-center gap-1.5 ${
              activeTab === "student"
                ? "bg-[#154539] text-white dark:bg-[#a0d1c0] dark:text-[#00372d] shadow-md"
                : "text-[#404945] dark:text-[#c0c8c4] hover:text-[#1c1b1b]"
            }`}
          >
            <span className="material-symbols-outlined text-sm">person</span>
            <span>Student Dashboard</span>
          </button>
          <button
            onClick={() => setActiveTab("teacher")}
            className={`flex-1 py-2.5 rounded-full text-xs font-extrabold transition-all flex items-center justify-center gap-1.5 ${
              activeTab === "teacher"
                ? "bg-[#154539] text-white dark:bg-[#a0d1c0] dark:text-[#00372d] shadow-md"
                : "text-[#404945] dark:text-[#c0c8c4] hover:text-[#1c1b1b]"
            }`}
          >
            <span className="material-symbols-outlined text-sm">co_present</span>
            <span>Teacher Suite</span>
          </button>
          <button
            onClick={() => setActiveTab("admin")}
            className={`flex-1 py-2.5 rounded-full text-xs font-extrabold transition-all flex items-center justify-center gap-1.5 ${
              activeTab === "admin"
                ? "bg-[#154539] text-white dark:bg-[#a0d1c0] dark:text-[#00372d] shadow-md"
                : "text-[#404945] dark:text-[#c0c8c4] hover:text-[#1c1b1b]"
            }`}
          >
            <span className="material-symbols-outlined text-sm">admin_panel_settings</span>
            <span>Admin Console</span>
          </button>
        </div>
      </div>

      {/* Interactive Mockup Preview Card */}
      <div className="bg-[#f0edec] dark:bg-[#1b211e] border border-[#e5e2e1] dark:border-[#2f3732] rounded-3xl p-6 sm:p-10 shadow-2xl">
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6 pb-6 border-b border-[#e5e2e1] dark:border-[#2f3732] mb-8">
          <div>
            <span className={`px-3 py-1 rounded-full text-[10px] font-extrabold ${active.badgeColor}`}>
              {active.badge}
            </span>
            <h3 className="text-2xl font-extrabold text-[#1c1b1b] dark:text-[#e1e4e1] mt-2">
              {active.title}
            </h3>
            <p className="text-xs text-[#717975] dark:text-[#c0c8c4] mt-1 max-w-xl">
              {active.subtitle}
            </p>
          </div>

          <Link
            href={active.route}
            className="bg-[#154539] text-white dark:bg-[#a0d1c0] dark:text-[#00372d] px-6 py-3 rounded-full text-xs font-extrabold flex items-center gap-2 shadow-md hover:scale-105 transition-all"
          >
            <span>Launch Live {active.badge} Demo</span>
            <span className="material-symbols-outlined text-base">arrow_forward</span>
          </Link>
        </div>

        {/* Stats Grid Bar */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          <div className="bg-[#fcf9f8] dark:bg-[#252c28] p-5 rounded-2xl border border-[#e5e2e1] dark:border-[#2f3732]">
            <p className="text-[11px] font-bold text-[#717975] dark:text-[#c0c8c4] uppercase tracking-wider">
              {active.stat1.label}
            </p>
            <p className="text-2xl font-extrabold text-[#154539] dark:text-[#a0d1c0] mt-1">
              {active.stat1.val}
            </p>
          </div>
          <div className="bg-[#fcf9f8] dark:bg-[#252c28] p-5 rounded-2xl border border-[#e5e2e1] dark:border-[#2f3732]">
            <p className="text-[11px] font-bold text-[#717975] dark:text-[#c0c8c4] uppercase tracking-wider">
              {active.stat2.label}
            </p>
            <p className="text-2xl font-extrabold text-[#ff9a5c] dark:text-[#ffb68d] mt-1">
              {active.stat2.val}
            </p>
          </div>
          <div className="bg-[#fcf9f8] dark:bg-[#252c28] p-5 rounded-2xl border border-[#e5e2e1] dark:border-[#2f3732]">
            <p className="text-[11px] font-bold text-[#717975] dark:text-[#c0c8c4] uppercase tracking-wider">
              {active.stat3.label}
            </p>
            <p className="text-2xl font-extrabold text-[#3b5f00] dark:text-[#c3f185] mt-1">
              {active.stat3.val}
            </p>
          </div>
        </div>

        {/* Mock Widget List */}
        <div className="bg-[#fcf9f8] dark:bg-[#252c28] rounded-2xl p-6 border border-[#e5e2e1] dark:border-[#2f3732]">
          <h4 className="text-xs font-extrabold uppercase tracking-wider text-[#154539] dark:text-[#a0d1c0] mb-4">
            {active.mockWidgetTitle}
          </h4>

          <div className="space-y-3">
            {active.mockContent.map((item, i) => (
              <div
                key={i}
                className="flex flex-col sm:flex-row sm:items-center justify-between p-4 rounded-xl bg-[#f0edec] dark:bg-[#1b211e] gap-3 border border-[#e5e2e1]/60 dark:border-[#2f3732]"
              >
                <div>
                  <p className="text-sm font-extrabold text-[#1c1b1b] dark:text-[#e1e4e1]">
                    {item.label}
                  </p>
                  <p className="text-xs text-[#717975] dark:text-[#c0c8c4] mt-0.5">
                    {item.desc}
                  </p>
                </div>

                <Link
                  href={active.route}
                  className="bg-[#154539] text-white dark:bg-[#a0d1c0] dark:text-[#00372d] px-4 py-2 rounded-xl text-[11px] font-extrabold self-start sm:self-auto hover:opacity-90 transition-opacity"
                >
                  {item.status}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
