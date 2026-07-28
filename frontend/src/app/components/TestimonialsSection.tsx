"use client";

import React from "react";

export default function TestimonialsSection() {
  const testimonials = [
    {
      role: "Teacher Perspective",
      name: "Dr. Marcus Vance",
      title: "Professor of Computer Science, ABC University",
      quote: "SmartClass AI cut my lecture prep and quiz creation time from 4 hours to 30 minutes. The automated GenAI flashcards and AI proctored exams have completely modernized our department.",
      avatar: "https://lh3.googleusercontent.com/aida-public/AB6AXuCyTbmIM6GaMaCtLq6grG5rxLk5qV4S2OR_tghfGFJHfjpQe_-MGKBmEILSPWIct9gSJJwl2qAfDkKMontCkSw1xgddQ4MSQ_g6wQaZie42dhBwOriRTi2ld9iSP-CtTeWxB2yPRjpFbix803MkaX6uAUQC-vNQ7r6Xh3AyJL8X2XEzc6f6aDukDEVGk6CEWq4M9oaygNr58eiFxHaClNM8hhrDTs0nYfjTHEKMKsarb6yQSJqrNZ4u58pg4wOnqdmz69P76eLL5SFH",
      badge: "Educator Review",
      badgeColor: "bg-[#ff9a5c] text-[#733200]",
    },
    {
      role: "Student Perspective",
      name: "Sophia Chen",
      title: "Undergraduate Student, Class of 2026",
      quote: "The 24/7 AI Tutor is a lifesaver when studying late at night. Having answers grounded directly in my professor's lecture slides with page citations gave me complete confidence before finals.",
      avatar: "https://lh3.googleusercontent.com/aida-public/AB6AXuC0anBl1K2YHYIJA2wj-Jlgb9X_6tnFsrgUWo--pDmwHINVsLY5_IVMWzdqdCAU6S9Aqgo5TAR1DDguGOvNnHm2c6XBjslBFsMvWheuOQjZ5OZEVYKojBLlwmSnpLr5AxvaPj3QNcsldx0_H2cePJ4wUFNUvV-8VWzcmtw9B7hbUSIe9OJiBecBfHkjuueihrM0zPhN_gEw7jBaEjNLEOb26Kzoefiybwcm2RNymu3jiY-cHZdgYXZ40J5-aIRGM5Tk3Ou6ttBwdK7u",
      badge: "Student Review",
      badgeColor: "bg-[#c3f185] text-[#112000]",
    },
    {
      role: "Institution Perspective",
      name: "Dr. Aris Thorne",
      title: "Dean of Academic Affairs, Future Academy Network",
      quote: "Consolidating 4 different software subscriptions into SmartClass AI saved our institution over $45,000 annually while improving our attendance tracking accuracy to 99.8%.",
      avatar: "https://lh3.googleusercontent.com/aida-public/AB6AXuClG2nPS72bOlkYtHRZXUi_uWN7n4lmLWzWyHho8a9EyMhPkP7j6XnKXcVT-2XutmxA6NQm4zZF6RYwR1OK3HBc-z5iwvNDTWKnc8pN6rBrBEZzu_Wx8EUVXKvCEXOyCTHefAOY1hjVioQIUDeAOnRFzlOkHTnP03U1v3UoJo0tsNHqD0sAoz-h9iDvk4rhEN4uzy4rvt3LmcOhVTY9Yzl5u5fUmSwyf2tONZo_4WYD6udb3V2EhhrDhh3GGME60gLXjqxyLp2IPcqs",
      badge: "Institutional Review",
      badgeColor: "bg-[#bceddc] text-[#002019]",
    },
  ];

  return (
    <section className="w-full max-w-[1920px] mx-auto px-4 sm:px-8 md:px-12 lg:px-16 py-16 md:py-24 bg-[#f0edec]/60 dark:bg-[#171d1a]/60 my-8 rounded-3xl border border-[#e5e2e1] dark:border-[#2f3732]">
      <div className="text-center max-w-3xl mx-auto mb-16">
        <span className="bg-[#154539] text-[#c3f185] dark:bg-[#a0d1c0] dark:text-[#00372d] px-4 py-1.5 rounded-full text-xs font-extrabold uppercase tracking-wider inline-block mb-3">
          Community Testimonials
        </span>
        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#1c1b1b] dark:text-[#e1e4e1] tracking-tight">
          Loved by Teachers, Students, and Deans
        </h2>
        <p className="text-base sm:text-lg text-[#404945] dark:text-[#c0c8c4] mt-3">
          See how SmartClass AI is transforming daily educational experiences globally.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {testimonials.map((t, idx) => (
          <div
            key={idx}
            className="bg-[#fcf9f8] dark:bg-[#1b211e] border border-[#e5e2e1] dark:border-[#2f3732] rounded-3xl p-8 shadow-lg flex flex-col justify-between relative group hover:-translate-y-1 transition-all"
          >
            <div>
              <div className="flex items-center justify-between mb-6">
                <span className={`px-3 py-1 rounded-full text-[10px] font-extrabold ${t.badgeColor}`}>
                  {t.badge}
                </span>
                <div className="flex text-amber-400 gap-0.5">
                  <span className="material-symbols-outlined text-sm font-filled">star</span>
                  <span className="material-symbols-outlined text-sm font-filled">star</span>
                  <span className="material-symbols-outlined text-sm font-filled">star</span>
                  <span className="material-symbols-outlined text-sm font-filled">star</span>
                  <span className="material-symbols-outlined text-sm font-filled">star</span>
                </div>
              </div>

              <p className="text-sm text-[#1c1b1b] dark:text-[#e1e4e1] italic leading-relaxed mb-8">
                "{t.quote}"
              </p>
            </div>

            <div className="flex items-center gap-4 pt-6 border-t border-[#e5e2e1]/60 dark:border-[#2f3732]">
              <img
                src={t.avatar}
                alt={t.name}
                className="w-12 h-12 rounded-full object-cover border-2 border-[#154539] dark:border-[#a0d1c0]"
              />
              <div>
                <h4 className="text-sm font-extrabold text-[#1c1b1b] dark:text-[#e1e4e1]">
                  {t.name}
                </h4>
                <p className="text-[11px] text-[#717975] dark:text-[#c0c8c4]">
                  {t.title}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
