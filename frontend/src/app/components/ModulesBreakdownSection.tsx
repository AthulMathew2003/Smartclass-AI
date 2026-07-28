"use client";

import React, { useState } from "react";
import Link from "next/link";

interface ModuleData {
  num: number;
  name: string;
  category: string;
  icon: string;
  desc: string;
  features: string[];
  route: string;
}

export default function ModulesBreakdownSection() {
  const [filter, setFilter] = useState<string>("All");

  const modules: ModuleData[] = [
    {
      num: 1,
      name: "Authentication & Identity",
      category: "Security & Access",
      icon: "fingerprint",
      desc: "User registration, email verification, Google/Microsoft OAuth 2.0, multi-factor auth, and session security.",
      features: ["Google & Microsoft OAuth", "MFA Verification", "Password Reset Flow", "Session Management"],
      route: "/login",
    },
    {
      num: 2,
      name: "Organization Management",
      category: "Administration",
      icon: "domain",
      desc: "Multi-tenant containers for Schools, Colleges, Universities, Coaching Centers, and Solo Learners.",
      features: ["Academic Year Setup", "Semester & Department Config", "Batch & Class Scheduling", "Timetable Management"],
      route: "/organization",
    },
    {
      num: 3,
      name: "User & Role Management (RBAC)",
      category: "Administration",
      icon: "admin_panel_settings",
      desc: "Create custom roles, assign granular permissions, manage Student, Teacher, Admin, HOD, TA & Parent profiles.",
      features: ["Custom Role Creator", "Bulk CSV User Import", "Granular Permission Matrix", "User Activity Audit Logs"],
      route: "/organization",
    },
    {
      num: 4,
      name: "Virtual Classroom",
      category: "Live Teaching",
      icon: "videocam",
      desc: "WebRTC low-latency live class streaming, screen share, interactive whiteboard, live polls, chat & cloud recording.",
      features: ["Interactive Whiteboard", "Live Polls & Hand Raise", "Cloud Session Recording", "Automatic Attendance"],
      route: "/classroom",
    },
    {
      num: 5,
      name: "Learning Resource Hub",
      category: "Learning Management",
      icon: "folder_open",
      desc: "Centralized repository for uploading PDFs, PPTs, video lectures, documents, and lecture notes.",
      features: ["PDF & Video Library", "Resource Categorization", "Download Controls", "Recorded Lecture Storage"],
      route: "/resources",
    },
    {
      num: 6,
      name: "Assignment Portal",
      category: "Learning Management",
      icon: "assignment",
      desc: "Create assignments, set deadlines, process student submissions, publish marks, and track late submissions.",
      features: ["Multiple File Uploads", "Online Code & Doc Submission", "Teacher Feedback & Marks", "Resubmission Tracker"],
      route: "/assignments",
    },
    {
      num: 7,
      name: "Examination Management",
      category: "Assessments",
      icon: "quiz",
      desc: "Create MCQ, descriptive, and live coding exams with randomized question banks, time limits, and automated evaluation.",
      features: ["MCQ & Coding Exam Engine", "Random Question Selection", "Automated MCQ Grading", "Result Publishing"],
      route: "/examinations",
    },
    {
      num: 8,
      name: "AI Tutor (RAG Powered)",
      category: "Core AI",
      icon: "auto_stories",
      desc: "24/7 intelligent study companion answering student questions grounded directly in uploaded course materials.",
      features: ["Context-Aware Q&A", "Step-by-step Explanations", "Study Material Recommendations", "Multi-turn Dialogue"],
      route: "/ai-tutor",
    },
    {
      num: 9,
      name: "AI Content Generation",
      category: "Core AI",
      icon: "edit_note",
      desc: "Automatically synthesize lecture summaries, study notes, flashcard decks, MCQ quizzes, and revision lists.",
      features: ["One-click PDF Summaries", "Flashcard Deck Generator", "Quiz & Exam Paper Builder", "Important Topic Extraction"],
      route: "/ai-content",
    },
    {
      num: 10,
      name: "Learning Twin",
      category: "Core AI",
      icon: "hub",
      desc: "Digital cognitive model tracking individual student progress, detecting weak topics, and predicting academic risk.",
      features: ["Skill & Knowledge Tracker", "Weak Topic Alerts", "Personalized Study Plans", "Risk Prediction Engine"],
      route: "/learning-twin",
    },
    {
      num: 11,
      name: "Learning Graph",
      category: "Core AI",
      icon: "account_tree",
      desc: "Map relationships between concepts, identify prerequisite knowledge dependencies, and guide optimal study paths.",
      features: ["Concept Prerequisite Trees", "Topic Dependency Graph", "Visual Path Recommendations", "Knowledge Gap Detection"],
      route: "/learning-graph",
    },
    {
      num: 12,
      name: "AI Attendance & Engagement",
      category: "Vision & AI",
      icon: "center_focus_strong",
      desc: "Automated facial recognition check-ins, join/leave duration logs, head-pose estimation, and gaze attention index.",
      features: ["1-to-N Facial Recognition", "Join / Exit Time Logs", "Head Pose & Eye-Gaze Metrics", "Engagement Heatmaps"],
      route: "/attendance",
    },
    {
      num: 13,
      name: "Smart AI Proctoring",
      category: "Assessments",
      icon: "shield",
      desc: "Protect online exam integrity via webcam face verification, eye tracking, tab switch alerts, and typing analysis.",
      features: ["Secondary Person Alert", "Browser Focus & Tab Switch Log", "Eye Deviation Detection", "Proctor Violation Logs"],
      route: "/examinations",
    },
    {
      num: 14,
      name: "Analytics Dashboard",
      category: "Analytics",
      icon: "insights",
      desc: "Role-tailored dashboards for Students, Teachers, and Administrators showcasing attendance, grades, and engagement.",
      features: ["Student Progress Cards", "Teacher Class Analytics", "Institution Performance", "Real-time Metrics"],
      route: "/dashboard",
    },
    {
      num: 15,
      name: "Semantic Search Engine",
      category: "Learning Management",
      icon: "travel_explore",
      desc: "AI vector search querying across lecture PDFs, PPT presentations, video transcripts, and course notes.",
      features: ["Natural Language Queries", "Exact Document Citation", "Cross-format Search", "Instant Results"],
      route: "/resources",
    },
    {
      num: 16,
      name: "Notification & Alert System",
      category: "Communication",
      icon: "notifications_active",
      desc: "Automated push & email alerts for class schedules, upcoming exam deadlines, published grades, and announcements.",
      features: ["Assignment Reminders", "Live Class Start Alerts", "Grade Published Alerts", "Institutional Bulletins"],
      route: "/dashboard",
    },
    {
      num: 17,
      name: "Discussion & Forums",
      category: "Communication",
      icon: "forum",
      desc: "Subject discussion forums, class chat channels, teacher announcement boards, and AI-assisted Q&A threads.",
      features: ["Subject Discussion Boards", "Teacher Announcements", "AI Instant Auto-Replies", "Student Q&A Threads"],
      route: "/classroom",
    },
    {
      num: 18,
      name: "Reports & Analytics Export",
      category: "Analytics",
      icon: "file_download",
      desc: "Generate and export official PDF and Excel reports for attendance, assignments, exam grades, and faculty workloads.",
      features: ["PDF & Excel Exporter", "Attendance Transcripts", "Departmental Workload Reports", "Student Grade Sheets"],
      route: "/dashboard",
    },
    {
      num: 19,
      name: "Administration & System Governance",
      category: "Administration",
      icon: "settings_suggest",
      desc: "Institutional settings, security audit logs, storage management, AI model configuration, and system health checks.",
      features: ["Institution Storage Limits", "AI Model Hyperparameter Config", "System Health Monitoring", "Security Audit Trail"],
      route: "/organization",
    },
  ];

  const categories = ["All", "Core AI", "Live Teaching", "Learning Management", "Assessments", "Administration", "Vision & AI", "Analytics"];

  const filteredModules =
    filter === "All" ? modules : modules.filter((m) => m.category === filter);

  return (
    <section id="modules" className="w-full max-w-[1920px] mx-auto px-4 sm:px-8 md:px-12 lg:px-16 py-16 md:py-24">
      {/* Title */}
      <div className="text-center max-w-3xl mx-auto mb-12">
        <span className="bg-[#c3f185] text-[#112000] px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider">
          Complete Architecture Specs
        </span>
        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#1c1b1b] dark:text-[#e1e4e1] mt-3 tracking-tight">
          19 Core System Modules
        </h2>
        <p className="text-base text-[#404945] dark:text-[#c0c8c4] mt-3">
          100+ integrated functionalities consolidating virtual learning, generative AI, proctored assessments, and academic administration into a single cloud platform.
        </p>

        {/* Category Filters */}
        <div className="flex flex-wrap justify-center gap-2 mt-8">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setFilter(cat)}
              className={`px-4 py-1.5 rounded-full text-xs font-bold transition-all ${
                filter === cat
                  ? "bg-[#154539] text-white dark:bg-[#a0d1c0] dark:text-[#00372d] shadow-md scale-105"
                  : "bg-[#f0edec] dark:bg-[#252c28] text-[#404945] dark:text-[#c0c8c4] hover:bg-[#e5e2e1]"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Modules Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {filteredModules.map((m) => (
          <div
            key={m.num}
            className="bg-[#fcf9f8] dark:bg-[#1b211e] border border-[#e5e2e1] dark:border-[#2f3732] rounded-3xl p-6 shadow-md hover:shadow-xl transition-all duration-300 flex flex-col justify-between group hover:-translate-y-1"
          >
            <div>
              <div className="flex justify-between items-center mb-4">
                <div className="w-10 h-10 rounded-2xl bg-[#154539]/10 dark:bg-[#a0d1c0]/10 text-[#154539] dark:text-[#a0d1c0] flex items-center justify-center">
                  <span className="material-symbols-outlined text-xl">
                    {m.icon}
                  </span>
                </div>
                <span className="text-xs font-extrabold text-[#717975] dark:text-[#c0c8c4] bg-[#f0edec] dark:bg-[#252c28] px-2.5 py-1 rounded-full">
                  Module #{m.num < 10 ? `0${m.num}` : m.num}
                </span>
              </div>

              <span className="text-[10px] font-bold uppercase tracking-wider text-[#154539] dark:text-[#a0d1c0]">
                {m.category}
              </span>
              <h3 className="text-xl font-bold text-[#1c1b1b] dark:text-[#e1e4e1] mt-0.5 mb-2">
                {m.name}
              </h3>
              <p className="text-xs text-[#404945] dark:text-[#c0c8c4] leading-relaxed mb-4">
                {m.desc}
              </p>

              {/* Specs Pills */}
              <div className="flex flex-wrap gap-1.5 mb-6">
                {m.features.map((feat, i) => (
                  <span
                    key={i}
                    className="text-[10px] bg-[#f0edec] dark:bg-[#252c28] text-[#1c1b1b] dark:text-[#e1e4e1] px-2.5 py-1 rounded-lg font-medium"
                  >
                    • {feat}
                  </span>
                ))}
              </div>
            </div>

            <Link
              href={m.route}
              className="w-full bg-[#f0edec] hover:bg-[#154539] hover:text-white dark:bg-[#252c28] dark:hover:bg-[#a0d1c0] dark:hover:text-[#00372d] text-[#1c1b1b] dark:text-[#e1e4e1] py-2.5 rounded-2xl text-xs font-bold transition-all text-center flex items-center justify-center gap-1.5 shadow-sm"
            >
              <span>View Route Specs</span>
              <span className="material-symbols-outlined text-sm">arrow_forward</span>
            </Link>
          </div>
        ))}
      </div>
    </section>
  );
}
