"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";

// 15 Standard Sections Components
import Navbar from "./components/Navbar";
import HeroSection from "./components/HeroSection";
import TrustedBySection from "./components/TrustedBySection";
import PlatformOverviewSection from "./components/PlatformOverviewSection";
import CoreFeaturesSection from "./components/CoreFeaturesSection";
import HowItWorksSection from "./components/HowItWorksSection";
import SolutionsSection from "./components/SolutionsSection";
import AiFeaturesShowcase from "./components/AiFeaturesShowcase";
import BenefitsSection from "./components/BenefitsSection";
import TestimonialsSection from "./components/TestimonialsSection";
import PricingSection from "./components/PricingSection";
import FaqSection from "./components/FaqSection";
import FinalCtaSection from "./components/FinalCtaSection";
import Footer from "./components/Footer";


export default function Home() {
  const [darkMode, setDarkMode] = useState(false);

  // Sync dark mode class with root html element
  useEffect(() => {
    const htmlEl = document.documentElement;
    if (darkMode) {
      htmlEl.classList.add("dark");
      htmlEl.classList.remove("light");
    } else {
      htmlEl.classList.add("light");
      htmlEl.classList.remove("dark");
    }
  }, [darkMode]);

  return (
    <div className="min-h-screen flex flex-col bg-[#fcf9f8] dark:bg-[#141816] text-[#1c1b1b] dark:text-[#e1e4e1] transition-colors duration-300 font-sans">
      {/* 1. Navigation Bar */}
      <Navbar
        darkMode={darkMode}
        setDarkMode={setDarkMode}
      />

      <main className="flex-grow">
        {/* 2. Hero Section */}
        <HeroSection />

        {/* 3. Trusted By */}
        <TrustedBySection />

        {/* 4. Platform Overview */}
        <PlatformOverviewSection />

        {/* 5. Core Features */}
        <CoreFeaturesSection />

        {/* 6. How It Works */}
        <HowItWorksSection />

        {/* 7. Solutions */}
        <SolutionsSection />

        {/* 8. AI Features Showcase */}
        <AiFeaturesShowcase />

        {/* 9. Benefits */}
        <BenefitsSection />

        {/* 11. Testimonials */}
        <TestimonialsSection />

        {/* 12. Pricing */}
        <PricingSection />

        {/* 13. FAQ */}
        <FaqSection />

        {/* 14. Final Call to Action */}
        <FinalCtaSection />
      </main>

      {/* 15. Footer */}
      <Footer />
    </div>
  );
}
