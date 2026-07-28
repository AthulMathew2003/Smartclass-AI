"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";

export default function HeroSection() {
  const [starRotation, setStarRotation] = useState(0);
  const [studentCount, setStudentCount] = useState(34);
  const [activeBadge, setActiveBadge] = useState("#AITutor");

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const star = document.getElementById("hero-rotating-star");
      if (star) {
        const rect = star.getBoundingClientRect();
        const starCenterX = rect.left + rect.width / 2;
        const starCenterY = rect.top + rect.height / 2;
        const angle =
          Math.atan2(e.clientY - starCenterY, e.clientX - starCenterX) *
          (180 / Math.PI);
        setStarRotation(angle / 6);
      }
    };

    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  return (
    <section className="relative w-full max-w-[1920px] mx-auto px-4 sm:px-8 md:px-12 lg:px-16 pt-28 pb-16 md:py-24 overflow-hidden">
      {/* Background Organic Animated SVG Path */}
      <svg
        className="absolute top-0 right-0 -z-10 w-full lg:w-1/2 h-full opacity-30 pointer-events-none"
        viewBox="0 0 400 600"
      >
        <path
          className="organic-path"
          d="M300,50 C350,150 50,250 100,400 C150,550 350,500 380,450"
        />
      </svg>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center">
        {/* Hero Visual Container (Bento Style with Live Class & AI Tutor Overlay) */}
        <div className="relative order-2 lg:order-1">
          <div className="bg-[#2f5d50] dark:bg-[#154539] rounded-3xl aspect-square sm:aspect-[4/3] lg:aspect-square flex items-center justify-center p-4 sm:p-8 overflow-hidden shadow-2xl relative group">
            <div className="relative w-full h-full rounded-2xl overflow-hidden group">
              <img
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuBYnXXVkR5IkuJrgSTCTyU3y1oaQ0kOQGbdiiIaVAQAkdCdrs0VKlWJRkVANdDbLMJ2m1dMuFPIU8D6FI2KRWNEzTgjU29qYbmHKmu3byt1TuVOsPixKxc0sH_GSH3CWLGyRCjpfsiRkAsFLPv3iPsSGNh55x2L7PzRjxJlyxcWuVonFynFWrQWNzyGswl05yXiz-pmGWDlZwqqLr0U0RcMjg5QFcnvBaZEE6Us2vaH_NA9Z43avZ_c_OCx8BIM1J5cy1yjdGHt4AJu"
                alt="Teacher conducting live WebRTC class with connected students"
                className="w-full h-full object-cover rounded-2xl group-hover:scale-105 transition-transform duration-700 filter brightness-95 contrast-105"
              />

              {/* Live WebRTC Overlay Card */}
              <div className="absolute top-4 left-4 bg-black/60 backdrop-blur-md px-3.5 py-2 rounded-2xl border border-white/20 flex items-center gap-2.5 text-white text-xs font-semibold shadow-lg">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping"></span>
                <span>Live WebRTC Class Active</span>
              </div>

              {/* Floating AI Tutor Chat Snippet Overlay Top Right */}
              <div className="absolute top-4 right-4 bg-[#141816]/90 backdrop-blur-md text-[#c3f185] p-3 rounded-2xl border border-white/20 text-[11px] max-w-[200px] shadow-2xl hidden sm:block">
                <div className="flex items-center gap-1.5 font-bold mb-1 text-white">
                  <span className="material-symbols-outlined text-xs text-[#c3f185]">auto_stories</span>
                  <span>24/7 Smart Tutor</span>
                </div>
                <p className="text-[10px] text-[#a3d4c3]">"Physics_101.pdf (p.42): F = m*a derived successfully."</p>
              </div>

              {/* Floating Tags */}
              <div className="absolute bottom-6 left-6 right-6 flex flex-wrap gap-2 z-10">
                <button
                  onClick={() => setActiveBadge("#SmartTutor")}
                  className={`px-4 py-1.5 rounded-full text-xs font-bold transition-all backdrop-blur-md ${
                    activeBadge === "#SmartTutor"
                      ? "bg-[#ff9a5c] text-[#733200] scale-105 shadow-md"
                      : "bg-[#fcf9f8]/80 text-[#1c1b1b] hover:bg-[#ff9a5c]"
                  }`}
                >
                  #SmartTutor
                </button>
                <button
                  onClick={() => setActiveBadge("#LiveClassroom")}
                  className={`px-4 py-1.5 rounded-full text-xs font-bold transition-all backdrop-blur-md ${
                    activeBadge === "#LiveClassroom"
                      ? "bg-[#c3f185] text-[#112000] scale-105 shadow-md"
                      : "bg-[#fcf9f8]/80 text-[#1c1b1b] hover:bg-[#c3f185]"
                  }`}
                >
                  #LiveClassroom
                </button>
                <button
                  onClick={() => setActiveBadge("#LearningTwin")}
                  className={`px-4 py-1.5 rounded-full text-xs font-bold transition-all backdrop-blur-md ${
                    activeBadge === "#LearningTwin"
                      ? "bg-[#bceddc] text-[#002019] scale-105 shadow-md"
                      : "bg-[#fcf9f8]/80 text-[#1c1b1b] hover:bg-[#bceddc]"
                  }`}
                >
                  #LearningTwin
                </button>
              </div>
            </div>
          </div>

          {/* Clean Floating Institutional Badge */}
          <div
            className="absolute -top-4 -right-4 bg-[#154539] text-[#c3f185] p-3 rounded-2xl shadow-xl border border-white/20 flex items-center gap-2 text-xs font-bold"
          >
            <span className="material-symbols-outlined text-lg">verified</span>
            <span>Next-Gen Academic Suite</span>
          </div>

          {/* Floating Interactive Badge bottom left */}
          <div className="absolute -bottom-6 -left-4 bg-[#fcf9f8] dark:bg-[#1b211e] p-3 px-4 rounded-2xl shadow-xl border border-[#e5e2e1] dark:border-[#2f3732] flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#c3f185] flex items-center justify-center text-[#112000] font-extrabold text-sm">
              99.8%
            </div>
            <div>
              <p className="text-xs font-extrabold text-[#1c1b1b] dark:text-[#e1e4e1]">
                Facial Attendance Engine
              </p>
              <p className="text-[11px] text-[#717975] dark:text-[#c0c8c4]">
                Biometric Verification Active
              </p>
            </div>
          </div>
        </div>

        {/* Hero Text Content */}
        <div className="order-1 lg:order-2 lg:pl-6">
          <div className="flex items-center gap-2 mb-6">
            <span className="material-symbols-outlined text-[#154539] dark:text-[#a0d1c0] text-xl">
              school
            </span>
            <span className="bg-[#f0edec] dark:bg-[#252c28] text-[#154539] dark:text-[#a0d1c0] px-3.5 py-1 rounded-full text-xs font-extrabold uppercase tracking-wider">
              Smart Academic & Virtual Learning Platform
            </span>
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-[#1c1b1b] dark:text-[#e1e4e1] mb-6 leading-[1.1] tracking-tight">
            The AI-Powered Platform for <br />
            <span className="text-[#154539] dark:text-[#a0d1c0] italic font-serif underline decoration-[#c3f185] decoration-wavy">
              Modern Education
            </span>
          </h1>

          <p className="text-base sm:text-lg text-[#404945] dark:text-[#c0c8c4] max-w-xl mb-8 leading-relaxed font-medium">
            Conduct live classes, manage assignments and exams, automate attendance, generate study materials with AI, and gain personalized learning insights—all in one place.
          </p>

          {/* Primary Action Buttons */}
          <div className="flex flex-wrap items-center gap-4 mb-8">
            <Link
              href="/login"
              className="bg-[#154539] hover:bg-[#2f5d50] text-white dark:bg-[#a0d1c0] dark:text-[#00372d] dark:hover:bg-[#bceddc] px-8 py-4 rounded-full font-extrabold text-sm shadow-xl hover:scale-105 active:scale-95 transition-all flex items-center gap-2"
            >
              <span>Get Started</span>
              <span className="material-symbols-outlined text-lg">arrow_forward</span>
            </Link>

            <Link
              href="/login"
              className="bg-[#f0edec] dark:bg-[#252c28] text-[#1c1b1b] dark:text-[#e1e4e1] hover:bg-[#e5e2e1] dark:hover:bg-[#2f3732] px-8 py-4 rounded-full font-extrabold text-sm transition-all flex items-center gap-2 border border-[#e5e2e1] dark:border-[#2f3732]"
            >
              <span className="material-symbols-outlined text-lg text-[#ff9a5c]">play_circle</span>
              <span>Book a Demo</span>
            </Link>
          </div>

          {/* Group B2 Batch Card */}
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="bg-[#ff9a5c] text-[#733200] p-5 rounded-2xl flex-1 min-w-[240px] shadow-lg relative overflow-hidden group">
              <div className="flex -space-x-3 mb-3">
                <img
                  className="w-9 h-9 rounded-full border-2 border-[#ff9a5c] object-cover"
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuCyTbmIM6GaMaCtLq6grG5rxLk5qV4S2OR_tghfGFJHfjpQe_-MGKBmEILSPWIct9gSJJwl2qAfDkKMontCkSw1xgddQ4MSQ_g6wQaZie42dhBwOriRTi2ld9iSP-CtTeWxB2yPRjpFbix803MkaX6uAUQC-vNQ7r6Xh3AyJL8X2XEzc6f6aDukDEVGk6CEWq4M9oaygNr58eiFxHaClNM8hhrDTs0nYfjTHEKMKsarb6yQSJqrNZ4u58pg4wOnqdmz69P76eLL5SFH"
                  alt="Educator"
                />
                <img
                  className="w-9 h-9 rounded-full border-2 border-[#ff9a5c] object-cover"
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuClG2nPS72bOlkYtHRZXUi_uWN7n4lmLWzWyHho8a9EyMhPkP7j6XnKXcVT-2XutmxA6NQm4zZF6RYwR1OK3HBc-z5iwvNDTWKnc8pN6rBrBEZzu_Wx8EUVXKvCEXOyCTHefAOY1hjVioQIUDeAOnRFzlOkHTnP03U1v3UoJo0tsNHqD0sAoz-h9iDvk4rhEN4uzy4rvt3LmcOhVTY9Yzl5u5fUmSwyf2tONZo_4WYD6udb3V2EhhrDhh3GGME60gLXjqxyLp2IPcqs"
                  alt="Student 1"
                />
                <img
                  className="w-9 h-9 rounded-full border-2 border-[#ff9a5c] object-cover"
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuC0anBl1K2YHYIJA2wj-Jlgb9X_6tnFsrgUWo--pDmwHINVsLY5_IVMWzdqdCAU6S9Aqgo5TAR1DDguGOvNnHm2c6XBjslBFsMvWheuOQjZ5OZEVYKojBLlwmSnpLr5AxvaPj3QNcsldx0_H2cePJ4wUFNUvV-8VWzcmtw9B7hbUSIe9OJiBecBfHkjuueihrM0zPhN_gEw7jBaEjNLEOb26Kzoefiybwcm2RNymu3jiY-cHZdgYXZ40J5-aIRGM5Tk3Ou6ttBwdK7u"
                  alt="Student 2"
                />
                <div className="w-9 h-9 rounded-full border-2 border-[#ff9a5c] bg-[#733200] text-white text-[11px] font-bold flex items-center justify-center">
                  +31
                </div>
              </div>
              <h3 className="text-lg font-extrabold text-[#733200] mb-0.5">
                Batch 2026-A: AI & ML
              </h3>
              <div className="flex justify-between items-end">
                <p className="text-[11px] font-bold text-[#733200]/80">
                  Connected Students: {studentCount}
                </p>
                <button
                  onClick={() => setStudentCount((prev) => prev + 1)}
                  className="bg-[#fcf9f8] hover:bg-white text-[#1c1b1b] rounded-full p-2 flex items-center justify-center transition-transform hover:rotate-45 shadow-md active:scale-95"
                  title="Simulate student join"
                >
                  <span className="material-symbols-outlined text-sm">
                    north_east
                  </span>
                </button>
              </div>
            </div>

            <Link
              href="/login"
              className="bg-[#c3f185] p-5 rounded-2xl w-full sm:w-36 flex flex-col items-center justify-center text-[#112000] shadow-lg group hover:bg-[#a7d56c] transition-colors cursor-pointer block text-center no-underline"
            >
              <span
                className="material-symbols-outlined text-[44px] group-hover:scale-110 transition-transform"
              >
                cloud_done
              </span>
              <span className="text-[10px] font-extrabold uppercase tracking-wide mt-1 text-center">
                Cloud Ecosystem
              </span>
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
