"use client";

import React, { useState } from "react";

export default function ImpactCalculator() {
  const [students, setStudents] = useState<number>(350);
  const [faculty, setFaculty] = useState<number>(18);
  const [courses, setCourses] = useState<number>(12);

  // Calculations
  const hoursSavedPerTeacher = Math.round(18 + (students / faculty) * 0.4);
  const totalInstitutionHoursSaved = hoursSavedPerTeacher * faculty;
  const attendanceAccuracy = "99.8%";
  const gradingSpeedup = "4.2x Faster";

  return (
    <section className="w-full max-w-[1920px] mx-auto px-4 sm:px-8 md:px-12 lg:px-16 py-16 md:py-24">
      <div className="bg-[#154539] text-white rounded-3xl p-6 sm:p-10 lg:p-12 shadow-2xl relative overflow-hidden">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 items-center">
          <div>
            <span className="bg-[#c3f185] text-[#112000] px-3.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider">
              Institutional ROI & Impact
            </span>
            <h2 className="text-3xl sm:text-4xl font-extrabold mt-3 mb-4 tracking-tight">
              Calculate Your Institutional Productivity Boost
            </h2>
            <p className="text-sm text-[#a3d4c3] leading-relaxed mb-8">
              Consolidate separate video class software, quiz tools, attendance hardware, and LMS software into one unified AI system.
            </p>

            {/* Range Sliders */}
            <div className="space-y-6">
              <div>
                <div className="flex justify-between text-xs font-bold mb-2">
                  <span>Enrolled Students</span>
                  <span className="text-[#c3f185]">{students.toLocaleString()} Students</span>
                </div>
                <input
                  type="range"
                  min={50}
                  max={5000}
                  step={50}
                  value={students}
                  onChange={(e) => setStudents(Number(e.target.value))}
                  className="w-full accent-[#c3f185] bg-[#2f5d50] h-2 rounded-lg cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs font-bold mb-2">
                  <span>Faculty Members</span>
                  <span className="text-[#c3f185]">{faculty} Educators</span>
                </div>
                <input
                  type="range"
                  min={2}
                  max={200}
                  step={1}
                  value={faculty}
                  onChange={(e) => setFaculty(Number(e.target.value))}
                  className="w-full accent-[#c3f185] bg-[#2f5d50] h-2 rounded-lg cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs font-bold mb-2">
                  <span>Active Courses & Subjects</span>
                  <span className="text-[#c3f185]">{courses} Learning Spaces</span>
                </div>
                <input
                  type="range"
                  min={2}
                  max={100}
                  step={1}
                  value={courses}
                  onChange={(e) => setCourses(Number(e.target.value))}
                  className="w-full accent-[#c3f185] bg-[#2f5d50] h-2 rounded-lg cursor-pointer"
                />
              </div>
            </div>
          </div>

          {/* Results Box */}
          <div className="bg-[#2f5d50] border border-[#a3d4c3]/20 p-8 rounded-3xl shadow-xl flex flex-col justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[#a3d4c3] mb-6 border-b border-white/10 pb-3">
              Estimated Monthly Efficiency Gain
            </h3>

            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="bg-[#154539] p-4 rounded-2xl border border-white/10">
                <span className="text-xs text-[#a3d4c3]">Hours Saved / Faculty</span>
                <p className="text-3xl font-extrabold text-[#c3f185] mt-1">
                  {hoursSavedPerTeacher} hrs
                </p>
                <span className="text-[10px] text-white/70">per teacher / month</span>
              </div>

              <div className="bg-[#154539] p-4 rounded-2xl border border-white/10">
                <span className="text-xs text-[#a3d4c3]">Total Institution Hours</span>
                <p className="text-3xl font-extrabold text-[#ff9a5c] mt-1">
                  {totalInstitutionHoursSaved.toLocaleString()} hrs
                </p>
                <span className="text-[10px] text-white/70">saved across faculty</span>
              </div>

              <div className="bg-[#154539] p-4 rounded-2xl border border-white/10">
                <span className="text-xs text-[#a3d4c3]">Attendance Accuracy</span>
                <p className="text-2xl font-extrabold text-[#bceddc] mt-1">
                  {attendanceAccuracy}
                </p>
                <span className="text-[10px] text-white/70">facial verification</span>
              </div>

              <div className="bg-[#154539] p-4 rounded-2xl border border-white/10">
                <span className="text-xs text-[#a3d4c3]">Grading Speedup</span>
                <p className="text-2xl font-extrabold text-[#c3f185] mt-1">
                  {gradingSpeedup}
                </p>
                <span className="text-[10px] text-white/70">AI evaluation engine</span>
              </div>
            </div>

            <div className="bg-[#154539]/60 p-4 rounded-2xl flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[#c3f185]">
                  verified
                </span>
                <span>Includes Multi-Tenant SaaS License & RAG Indexing</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
