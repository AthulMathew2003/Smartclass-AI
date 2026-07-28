"use client";

import React, { useState } from "react";
import Link from "next/link";

export default function PricingSection() {
  const [annualBilling, setAnnualBilling] = useState<boolean>(true);

  const plans = [
    {
      name: "Starter Plan",
      subtitle: "Ideal for individual teachers, tutors & small groups.",
      monthlyPrice: "$0",
      annualPrice: "$0",
      period: "Free Forever",
      badge: "Individual Educator",
      accent: "bg-[#f0edec] dark:bg-[#252c28] text-[#1c1b1b] dark:text-[#e1e4e1]",
      btnText: "Start Free",
      btnStyle: "bg-[#154539] text-white dark:bg-[#a0d1c0] dark:text-[#00372d]",
      features: [
        "Up to 50 active students",
        "WebRTC Live Classroom (HD Video)",
        "24/7 RAG AI Tutor (100 queries/mo)",
        "Basic assignment management",
        "Community & email support",
      ],
    },
    {
      name: "Professional Plan",
      subtitle: "For coaching centers, departments & growing schools.",
      monthlyPrice: "$99",
      annualPrice: "$79",
      period: "per month, billed annually",
      badge: "Most Popular",
      accent: "bg-[#154539] text-white dark:bg-[#a0d1c0] dark:text-[#00372d] ring-2 ring-[#c3f185]",
      popular: true,
      btnText: "Get Started Free",
      btnStyle: "bg-[#c3f185] text-[#112000] hover:bg-[#a7d56c]",
      features: [
        "Up to 500 active students",
        "Unlimited WebRTC Live Classrooms & Recording",
        "Unlimited RAG AI Tutor & GenAI Summarizer",
        "AI Facial Attendance & Attention Metrics",
        "Automated MCQ & Subjective Exam Grader",
        "Custom RBAC Roles & Audit Logs",
        "Priority 24/7 support",
      ],
    },
    {
      name: "Enterprise Plan",
      subtitle: "For universities, colleges & multi-school networks.",
      monthlyPrice: "Custom",
      annualPrice: "Custom",
      period: "Tailored for your scale",
      badge: "University Scale",
      accent: "bg-[#f0edec] dark:bg-[#252c28] text-[#1c1b1b] dark:text-[#e1e4e1]",
      btnText: "Book a Demo / Contact Sales",
      btnStyle: "bg-[#2f5d50] text-[#bceddc] hover:bg-[#154539]",
      features: [
        "Unlimited students & faculty accounts",
        "Multi-Tenant Department & Campus Containers",
        "Full AI Exam Proctoring Suite",
        "Student Learning Twin & Skill Radar Analytics",
        "Custom API, SSO & LMS Integrations",
        "Dedicated Customer Success Manager",
        "SLA 99.99% Uptime Guarantee",
      ],
    },
  ];

  return (
    <section id="pricing" className="w-full max-w-[1920px] mx-auto px-4 sm:px-8 md:px-12 lg:px-16 py-16 md:py-24">
      <div className="text-center max-w-3xl mx-auto mb-16">
        <span className="bg-[#154539] text-[#c3f185] dark:bg-[#a0d1c0] dark:text-[#00372d] px-4 py-1.5 rounded-full text-xs font-extrabold uppercase tracking-wider inline-block mb-3">
          Transparent Pricing
        </span>
        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#1c1b1b] dark:text-[#e1e4e1] tracking-tight">
          Flexible Plans for Every Scale
        </h2>
        <p className="text-base sm:text-lg text-[#404945] dark:text-[#c0c8c4] mt-3">
          Start for free as an individual teacher or select an institutional plan built to scale with your university.
        </p>

        {/* Toggle Billing */}
        <div className="flex items-center justify-center gap-4 mt-8">
          <span className={`text-xs font-bold ${!annualBilling ? "text-[#154539] dark:text-[#a0d1c0]" : "text-[#717975]"}`}>
            Monthly Billing
          </span>
          <button
            onClick={() => setAnnualBilling(!annualBilling)}
            className="w-14 h-8 bg-[#154539] dark:bg-[#a0d1c0] rounded-full p-1 transition-colors relative"
          >
            <div
              className={`w-6 h-6 bg-[#c3f185] dark:bg-[#00372d] rounded-full transition-transform ${
                annualBilling ? "translate-x-6" : "translate-x-0"
              }`}
            ></div>
          </button>
          <span className={`text-xs font-bold flex items-center gap-1.5 ${annualBilling ? "text-[#154539] dark:text-[#a0d1c0]" : "text-[#717975]"}`}>
            <span>Annual Billing</span>
            <span className="bg-[#c3f185] text-[#112000] px-2 py-0.5 rounded-full text-[10px] font-extrabold">
              Save 20%
            </span>
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-stretch">
        {plans.map((plan, idx) => {
          const price = annualBilling ? plan.annualPrice : plan.monthlyPrice;
          return (
            <div
              key={idx}
              className={`rounded-3xl p-8 shadow-xl flex flex-col justify-between relative border transition-all duration-300 ${
                plan.popular
                  ? "bg-[#154539] text-white border-[#c3f185] scale-[1.03] z-10"
                  : "bg-[#fcf9f8] dark:bg-[#1b211e] text-[#1c1b1b] dark:text-[#e1e4e1] border-[#e5e2e1] dark:border-[#2f3732]"
              }`}
            >
              {plan.popular && (
                <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 bg-[#c3f185] text-[#112000] px-4 py-1 rounded-full text-[11px] font-extrabold uppercase tracking-wider shadow-md">
                  ★ Most Popular Choice
                </div>
              )}

              <div>
                <div className="flex justify-between items-start mb-4">
                  <span className={`px-3 py-1 rounded-full text-[10px] font-extrabold ${plan.popular ? "bg-[#c3f185] text-[#112000]" : "bg-[#f0edec] dark:bg-[#252c28] text-[#154539] dark:text-[#a0d1c0]"}`}>
                    {plan.badge}
                  </span>
                </div>

                <h3 className="text-2xl font-extrabold tracking-tight mb-2">
                  {plan.name}
                </h3>
                <p className={`text-xs mb-6 ${plan.popular ? "text-[#bceddc]" : "text-[#717975] dark:text-[#c0c8c4]"}`}>
                  {plan.subtitle}
                </p>

                <div className="mb-8">
                  <span className="text-4xl font-extrabold tracking-tight">
                    {price}
                  </span>
                  {price !== "Custom" && price !== "$0" && (
                    <span className={`text-xs ml-2 ${plan.popular ? "text-[#bceddc]" : "text-[#717975]"}`}>
                      /{plan.period}
                    </span>
                  )}
                  {price === "$0" && (
                    <span className={`text-xs ml-2 ${plan.popular ? "text-[#bceddc]" : "text-[#717975]"}`}>
                      / Free Forever
                    </span>
                  )}
                </div>

                <ul className="space-y-3.5 mb-8">
                  {plan.features.map((f, i) => (
                    <li key={i} className="flex items-center gap-3 text-xs font-medium">
                      <span className={`material-symbols-outlined text-base ${plan.popular ? "text-[#c3f185]" : "text-[#154539] dark:text-[#a0d1c0]"}`}>
                        check_circle
                      </span>
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <Link
                href="/login"
                className={`w-full text-center py-4 rounded-full font-extrabold text-sm shadow-md transition-all ${plan.btnStyle}`}
              >
                {plan.btnText}
              </Link>
            </div>
          );
        })}
      </div>
    </section>
  );
}
