"use client";

import React from "react";

export default function TrustedBySection() {
  const partners = [
    { name: "ABC University", tag: "Higher Ed", icon: "account_balance" },
    { name: "XYZ College", tag: "Engineering", icon: "school" },
    { name: "Future Academy", tag: "K-12 Network", icon: "workspace_premium" },
    { name: "Skill Hub", tag: "Coaching Center", icon: "menu_book" },
    { name: "Apex Institute", tag: "Medical Prep", icon: "local_hospital" },
    { name: "Global Edu", tag: "Global Campus", icon: "public" },
  ];

  return (
    <section className="w-full max-w-[1920px] mx-auto px-4 sm:px-8 md:px-12 lg:px-16 py-12 border-y border-[#e5e2e1]/60 dark:border-[#2f3732]/60 bg-[#f0edec]/50 dark:bg-[#171d1a]/50 transition-colors">
      <div className="flex flex-col md:flex-row items-center justify-between gap-8">
        <div className="md:w-1/4 text-center md:text-left">
          <p className="text-xs font-bold uppercase tracking-widest text-[#717975] dark:text-[#c0c8c4]">
            Trusted by Progressive Institutions
          </p>
          <p className="text-sm font-bold text-[#1c1b1b] dark:text-[#e1e4e1] mt-1">
            Empowering 250+ Schools & Colleges
          </p>
        </div>

        <div className="md:w-3/4 flex flex-wrap items-center justify-center md:justify-end gap-6 sm:gap-10">
          {partners.map((p, idx) => (
            <div
              key={idx}
              className="flex items-center gap-2.5 px-4 py-2 rounded-2xl bg-[#fcf9f8] dark:bg-[#1b211e] border border-[#e5e2e1] dark:border-[#2f3732] shadow-sm hover:shadow-md transition-all group"
            >
              <div className="w-8 h-8 rounded-xl bg-[#154539]/10 dark:bg-[#a0d1c0]/10 text-[#154539] dark:text-[#a0d1c0] flex items-center justify-center group-hover:scale-110 transition-transform">
                <span className="material-symbols-outlined text-lg">
                  {p.icon}
                </span>
              </div>
              <div className="text-left">
                <p className="text-xs font-extrabold text-[#1c1b1b] dark:text-[#e1e4e1]">
                  {p.name}
                </p>
                <p className="text-[10px] text-[#717975] dark:text-[#c0c8c4] font-medium">
                  {p.tag}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
