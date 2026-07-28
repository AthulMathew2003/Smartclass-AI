"use client";

import React, { useState } from "react";

export default function FaqSection() {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  const faqs = [
    {
      q: "Can individual teachers use SmartClass AI?",
      a: "Yes! Individual teachers and tutors can sign up for our Starter Plan for free. You can launch WebRTC live classes, share PDFs, and use the 24/7 AI Tutor with zero infrastructure setup.",
    },
    {
      q: "Does it support schools and colleges?",
      a: "Absolutely. SmartClass AI is engineered with a multi-tenant architecture supporting Departments, Semesters, Batches, and Timetables, along with custom RBAC roles for Admins, HODs, Teachers, TAs, and Students.",
    },
    {
      q: "Do students need to install software?",
      a: "No installation required! SmartClass AI is 100% web-native and runs seamlessly inside any standard browser (Chrome, Firefox, Safari, Edge) on laptops, tablets, and smartphones.",
    },
    {
      q: "Does it support live video classes?",
      a: "Yes. SmartClass AI includes built-in WebRTC low-latency HD video streaming with screen sharing, collaborative whiteboards, live polls, Q&A chat, and automated cloud recording transcription.",
    },
    {
      q: "How does AI attendance work?",
      a: "AI Attendance utilizes computer vision 1-to-N facial recognition. When students join a live virtual or physical classroom, their face is verified in seconds, logging precise join/exit timestamps and calculating attendance percentages automatically with anti-spoofing liveness checks.",
    },
    {
      q: "Is student data & AI interaction secure?",
      a: "Yes. All data is encrypted in transit (TLS 1.3) and at rest (AES-256). Our Retrieval-Augmented Generation (RAG) models operate with strict institutional guardrails ensuring AI responses remain strictly within approved course materials.",
    },
  ];

  const toggleFaq = (idx: number) => {
    setOpenIndex(openIndex === idx ? null : idx);
  };

  return (
    <section id="faq" className="w-full max-w-[1920px] mx-auto px-4 sm:px-8 md:px-12 lg:px-16 py-16 md:py-24">
      <div className="text-center max-w-3xl mx-auto mb-16">
        <span className="bg-[#154539] text-[#c3f185] dark:bg-[#a0d1c0] dark:text-[#00372d] px-4 py-1.5 rounded-full text-xs font-extrabold uppercase tracking-wider inline-block mb-3">
          Frequently Asked Questions
        </span>
        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#1c1b1b] dark:text-[#e1e4e1] tracking-tight">
          Everything You Need to Know
        </h2>
        <p className="text-base sm:text-lg text-[#404945] dark:text-[#c0c8c4] mt-3">
          Got questions? We've got answers. If you need further details, feel free to contact our support team.
        </p>
      </div>

      <div className="max-w-4xl mx-auto space-y-4">
        {faqs.map((faq, idx) => {
          const isOpen = openIndex === idx;
          return (
            <div
              key={idx}
              className="bg-[#fcf9f8] dark:bg-[#1b211e] border border-[#e5e2e1] dark:border-[#2f3732] rounded-3xl overflow-hidden transition-all duration-200 shadow-sm"
            >
              <button
                onClick={() => toggleFaq(idx)}
                className="w-full text-left p-6 sm:p-7 flex justify-between items-center gap-4 hover:bg-[#f0edec]/50 dark:hover:bg-[#252c28]/50 transition-colors"
              >
                <span className="text-base sm:text-lg font-extrabold text-[#1c1b1b] dark:text-[#e1e4e1]">
                  {faq.q}
                </span>
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center bg-[#f0edec] dark:bg-[#252c28] text-[#154539] dark:text-[#a0d1c0] transition-transform duration-200 ${
                    isOpen ? "rotate-180 bg-[#154539] text-white dark:bg-[#a0d1c0] dark:text-[#00372d]" : ""
                  }`}
                >
                  <span className="material-symbols-outlined text-lg">
                    keyboard_arrow_down
                  </span>
                </div>
              </button>

              {isOpen && (
                <div className="px-6 pb-7 sm:px-7 text-sm text-[#404945] dark:text-[#c0c8c4] leading-relaxed border-t border-[#e5e2e1]/60 dark:border-[#2f3732] pt-4 animate-in fade-in duration-150">
                  {faq.a}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
