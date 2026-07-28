"use client";

import React, { useState } from "react";
import Link from "next/link";

interface FeatureItem {
  id: string;
  title: string;
  category: string;
  icon: string;
  badge: string;
  badgeColor: string;
  shortDesc: string;
  fullDesc: string;
  capabilities: string[];
  route: string;
  accentBg: string;
}

export default function FeaturesBentoGrid() {
  const [selectedFeature, setSelectedFeature] = useState<FeatureItem | null>(null);

  const features: FeatureItem[] = [
    {
      id: "ai-tutor",
      title: "Smart Tutor (24/7 RAG)",
      category: "Personalized Learning",
      icon: "auto_stories",
      badge: "24/7 Context Aware",
      badgeColor: "bg-[#c3f185] text-[#112000]",
      shortDesc: "Personalized guidance adapting to your unique learning style and pace using course material context.",
      fullDesc: "The Smart Tutor utilizes Retrieval-Augmented Generation (RAG) to read lecture notes, PDFs, textbook chapters, and recorded lectures. Students can ask questions in natural language and receive precise, cited answers with step-by-step guidance.",
      capabilities: [
        "Natural language Q&A grounded in uploaded course materials",
        "Step-by-step problem solving & formula explanation",
        "Multi-turn interactive dialogue with concept memory",
        "Automated study material recommendations based on learning gaps"
      ],
      route: "/ai-tutor",
      accentBg: "bg-[#154539] text-white"
    },
    {
      id: "learning-twin",
      title: "Learning Twin & Profile",
      category: "Adaptive Analytics",
      icon: "hub",
      badge: "Digital Reflection",
      badgeColor: "bg-[#ff9a5c] text-[#733200]",
      shortDesc: "A digital reflection of student progress, identifying skill gaps and suggesting optimal paths to mastery.",
      fullDesc: "The Learning Twin constructs a real-time digital cognitive model of each student. By analyzing assignment scores, quiz speed, attendance, and video replay patterns, it highlights strong topics, flags at-risk topics, and predicts exam outcomes.",
      capabilities: [
        "Cognitive skill map & topic mastery percentage",
        "Weak topic detection & early risk alert for educators",
        "Dynamic personalized study plan generation",
        "Predictive performance modeling prior to final exams"
      ],
      route: "/learning-twin",
      accentBg: "bg-[#2f5d50] text-[#a3d4c3]"
    },
    {
      id: "virtual-labs",
      title: "Virtual Classroom & Labs",
      category: "Immersive WebRTC",
      icon: "science",
      badge: "Interactive WebRTC",
      badgeColor: "bg-[#bceddc] text-[#002019]",
      shortDesc: "Live video classes with collaborative whiteboards, screen sharing, real-time polls, and risk-free lab simulations.",
      fullDesc: "Built on WebRTC architecture with low-latency media streaming, SmartClass AI classrooms allow teachers to broadcast HD video, share screens, co-create on interactive whiteboards, run instant quizzes, and save cloud recordings.",
      capabilities: [
        "High-definition WebRTC video & multi-user audio",
        "Interactive collaborative whiteboard & screen share",
        "In-class live polls, hand raising & Q&A chat history",
        "Automatic cloud recording with instant AI transcription"
      ],
      route: "/classroom",
      accentBg: "bg-[#f0edec] dark:bg-[#1b211e] text-[#1c1b1b] dark:text-[#e1e4e1]"
    },
    {
      id: "ai-attendance",
      title: "AI Facial Attendance",
      category: "Computer Vision",
      icon: "center_focus_strong",
      badge: "Face Verification",
      badgeColor: "bg-[#c3f185] text-[#112000]",
      shortDesc: "Automated biometric face recognition check-ins with precise join/leave timestamp logging.",
      fullDesc: "Eliminate proxy attendance and roll-call delays. The AI Attendance engine uses face detection to automatically verify enrolled students when they join virtual or hybrid physical classrooms, computing accurate percentage logs.",
      capabilities: [
        "1-to-N facial recognition check-in",
        "Join time, exit time, and total duration tracking",
        "Anti-spoofing & liveness detection",
        "Automated attendance report exports (PDF / Excel)"
      ],
      route: "/attendance",
      accentBg: "bg-[#3b5f00] text-[#abd970]"
    },
    {
      id: "engagement-analysis",
      title: "Classroom Engagement AI",
      category: "Computer Vision & NLP",
      icon: "monitoring",
      badge: "Head & Gaze Tracking",
      badgeColor: "bg-[#ff9a5c] text-[#733200]",
      shortDesc: "Real-time presence detection, head pose estimation, and gaze tracking to measure student participation.",
      fullDesc: "Provide teachers with actionable insights into class engagement without invading privacy. The system aggregates head orientation, chat activity, hand raises, and speaking time into an overall Classroom Attention Score.",
      capabilities: [
        "Face presence & head pose estimation",
        "Eye-gaze attention metrics & distraction warnings",
        "Speaking activity & chat participation scoring",
        "Real-time teacher feedback dashboard during live lectures"
      ],
      route: "/attendance",
      accentBg: "bg-[#97480f] text-white"
    },
    {
      id: "ai-proctoring",
      title: "Smart AI Proctoring",
      category: "Assessment Security",
      icon: "security",
      badge: "Integrity Monitor",
      badgeColor: "bg-[#bceddc] text-[#002019]",
      shortDesc: "Maintain online exam integrity with multi-person detection, eye tracking, tab switch alerts, and typing pattern analysis.",
      fullDesc: "Secure high-stakes examinations. The proctoring suite monitors candidates via webcam and browser focus tracking, flagging suspicious behaviors like looking away, unauthorized tab switching, or second persons in frame.",
      capabilities: [
        "Continuous webcam face verification & secondary person alert",
        "Browser focus detection & tab switch logger",
        "Eye-gaze deviation & audio anomaly detection",
        "Comprehensive suspicious activity proctoring reports"
      ],
      route: "/examinations",
      accentBg: "bg-[#154539] text-[#bceddc]"
    },
    {
      id: "learning-graph",
      title: "Learning Graph",
      category: "Knowledge Mapping",
      icon: "account_tree",
      badge: "Prerequisite Tree",
      badgeColor: "bg-[#c3f185] text-[#112000]",
      shortDesc: "Map concept dependencies, detect prerequisite knowledge gaps, and plot optimal learning pathways.",
      fullDesc: "Education is non-linear. The Learning Graph maps dependencies between topics (e.g., Derivative → Integral → Differential Equation), enabling students to visualize prerequisite requirements and fill foundational gaps.",
      capabilities: [
        "Interactive node-link concept dependency maps",
        "Prerequisite gap detection prior to advanced topics",
        "Personalized path navigation for self-paced study",
        "Cross-subject concept correlation visualization"
      ],
      route: "/learning-graph",
      accentBg: "bg-[#2f5d50] text-[#a3d4c3]"
    },
    {
      id: "ai-content-gen",
      title: "AI Content Generator",
      category: "GenAI Productivity",
      icon: "edit_note",
      badge: "PDF to Quiz / Notes",
      badgeColor: "bg-[#ff9a5c] text-[#733200]",
      shortDesc: "Instantly generate lecture summaries, flashcards, MCQ quizzes, practice papers, and revision notes from course material.",
      fullDesc: "Reduce teacher preparation time by 80%. Upload any document or video transcript, and the GenAI module automatically creates structured lecture summaries, flashcards for quick revision, and self-evaluating MCQ tests.",
      capabilities: [
        "One-click PDF/Video lecture summarization",
        "Automatic flashcard generation with spaced repetition",
        "MCQ and subjective question bank generator",
        "Key concept highlighting & bulleted revision notes"
      ],
      route: "/ai-content",
      accentBg: "bg-[#f0edec] dark:bg-[#1b211e] text-[#1c1b1b] dark:text-[#e1e4e1]"
    }
  ];

  return (
    <section id="features" className="w-full max-w-[1920px] mx-auto px-4 sm:px-8 md:px-12 lg:px-16 py-16 md:py-24">
      {/* Header Title */}
      <div className="flex flex-col md:flex-row md:items-end justify-between mb-12 gap-6">
        <div className="max-w-2xl">
          <div className="flex items-center gap-2 mb-3">
            <span className="w-2.5 h-2.5 rounded-full bg-[#154539] dark:bg-[#a0d1c0]"></span>
            <span className="text-xs font-bold uppercase tracking-wider text-[#154539] dark:text-[#a0d1c0]">
              State of the Art Architecture
            </span>
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#1c1b1b] dark:text-[#e1e4e1] tracking-tight">
            Innovative Classrooms & <br className="hidden sm:inline" />
            <span className="text-[#154539] dark:text-[#a0d1c0]">AI Intelligence</span>
          </h2>
          <p className="text-base text-[#404945] dark:text-[#c0c8c4] mt-3">
            Designed to amplify human teaching, streamline administrative workflows, and provide students with personalized, 24/7 cognitive guidance.
          </p>
        </div>

        <Link
          href="#modules"
          className="inline-flex items-center justify-center gap-2 bg-[#2f5d50] text-[#a3d4c3] hover:bg-[#154539] dark:bg-[#a0d1c0] dark:text-[#00372d] px-6 py-3 rounded-full text-sm font-bold transition-all shadow-md self-start md:self-auto"
        >
          <span>Explore All 19 Modules</span>
          <span className="material-symbols-outlined text-base">arrow_downward</span>
        </Link>
      </div>

      {/* Bento Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {features.map((feature, idx) => {
          const isLarge = idx === 0 || idx === 1;
          return (
            <div
              key={feature.id}
              onClick={() => setSelectedFeature(feature)}
              className={`rounded-3xl p-7 relative overflow-hidden transition-all duration-300 cursor-pointer group hover:-translate-y-1.5 shadow-lg border border-[#e5e2e1]/60 dark:border-[#2f3732] flex flex-col justify-between ${
                feature.accentBg
              } ${isLarge ? "lg:col-span-2" : "lg:col-span-1"}`}
            >
              {/* Background Glow decorative element */}
              <div className="absolute -bottom-10 -right-10 w-40 h-40 rounded-full bg-white/5 transition-transform group-hover:scale-150 duration-500 pointer-events-none"></div>

              <div>
                <div className="flex justify-between items-start mb-6">
                  <div className="w-12 h-12 rounded-2xl bg-white/10 dark:bg-black/10 backdrop-blur-md flex items-center justify-center border border-white/20">
                    <span className="material-symbols-outlined text-2xl">
                      {feature.icon}
                    </span>
                  </div>
                  <span
                    className={`px-3 py-1 rounded-full text-[11px] font-bold ${feature.badgeColor}`}
                  >
                    {feature.badge}
                  </span>
                </div>

                <span className="text-[10px] uppercase tracking-widest opacity-75 font-semibold">
                  {feature.category}
                </span>
                <h3 className="text-2xl font-bold mt-1 mb-3 tracking-tight">
                  {feature.title}
                </h3>
                <p className="text-sm opacity-85 leading-relaxed mb-6">
                  {feature.shortDesc}
                </p>
              </div>

              <div className="flex items-center justify-between pt-4 border-t border-current/10 mt-auto">
                <span className="text-xs font-bold flex items-center gap-1 group-hover:underline">
                  View Specifications & Capabilities
                </span>
                <span className="material-symbols-outlined text-lg transition-transform group-hover:translate-x-1">
                  arrow_forward
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Feature Detail Modal */}
      {selectedFeature && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-[#fcf9f8] dark:bg-[#1b211e] border border-[#e5e2e1] dark:border-[#2f3732] rounded-3xl max-w-2xl w-full p-6 md:p-8 shadow-2xl relative max-h-[90vh] overflow-y-auto">
            <button
              onClick={() => setSelectedFeature(null)}
              className="absolute top-5 right-5 w-9 h-9 rounded-full bg-[#f0edec] dark:bg-[#252c28] text-[#1c1b1b] dark:text-[#e1e4e1] flex items-center justify-center hover:bg-[#e5e2e1] transition-colors"
            >
              <span className="material-symbols-outlined text-xl">close</span>
            </button>

            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-2xl bg-[#154539] text-[#c3f185] flex items-center justify-center">
                <span className="material-symbols-outlined text-2xl">
                  {selectedFeature.icon}
                </span>
              </div>
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-[#154539] dark:text-[#a0d1c0]">
                  {selectedFeature.category}
                </span>
                <h3 className="text-2xl font-bold text-[#1c1b1b] dark:text-[#e1e4e1]">
                  {selectedFeature.title}
                </h3>
              </div>
            </div>

            <p className="text-sm text-[#404945] dark:text-[#c0c8c4] leading-relaxed mb-6">
              {selectedFeature.fullDesc}
            </p>

            <div className="bg-[#f0edec] dark:bg-[#252c28] p-5 rounded-2xl mb-6">
              <h4 className="text-xs font-extrabold uppercase tracking-wider text-[#154539] dark:text-[#a0d1c0] mb-3">
                Key Technical Capabilities
              </h4>
              <ul className="space-y-2.5">
                {selectedFeature.capabilities.map((cap, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-[#1c1b1b] dark:text-[#e1e4e1]">
                    <span className="material-symbols-outlined text-[#154539] dark:text-[#a0d1c0] text-sm mt-0.5">
                      check_circle
                    </span>
                    <span>{cap}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setSelectedFeature(null)}
                className="px-5 py-2.5 rounded-full text-xs font-bold text-[#404945] dark:text-[#c0c8c4] hover:bg-[#f0edec] dark:hover:bg-[#252c28]"
              >
                Close Window
              </button>
              <Link
                href={selectedFeature.route}
                className="bg-[#154539] text-white dark:bg-[#a0d1c0] dark:text-[#00372d] px-6 py-2.5 rounded-full text-xs font-bold flex items-center gap-1.5 shadow-md hover:scale-105 transition-all"
              >
                <span>Launch {selectedFeature.title}</span>
                <span className="material-symbols-outlined text-sm">open_in_new</span>
              </Link>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
