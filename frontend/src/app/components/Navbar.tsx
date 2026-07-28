"use client";

import React, { useState } from "react";
import Link from "next/link";

interface NavbarProps {
  darkMode: boolean;
  setDarkMode: React.Dispatch<React.SetStateAction<boolean>>;
}

export default function Navbar({
  darkMode,
  setDarkMode,
}: NavbarProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);

  return (
    <header className="fixed top-0 left-0 right-0 z-50 px-4 sm:px-8 md:px-12 lg:px-16 py-3 bg-[#fcf9f8]/90 dark:bg-[#141816]/90 glass-nav border-b border-[#e5e2e1]/50 dark:border-[#2f3732]/50 transition-colors duration-300">
      <nav className="w-full max-w-[1920px] mx-auto flex justify-between items-center">
        {/* Brand Logo */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="w-10 h-10 rounded-full bg-[#154539] dark:bg-[#a0d1c0] flex items-center justify-center text-[#c3f185] dark:text-[#00372d] shadow-md group-hover:scale-105 transition-transform">
            <span className="material-symbols-outlined material-symbols-filled text-2xl">
              school
            </span>
          </div>
          <div className="flex flex-col">
            <span className="text-xl font-bold tracking-tight text-[#1c1b1b] dark:text-[#e1e4e1] font-sans">
              SmartClass <span className="text-[#154539] dark:text-[#a0d1c0]">AI</span>
            </span>
            <span className="text-[10px] uppercase tracking-widest text-[#717975] dark:text-[#c0c8c4] font-semibold -mt-1">
              Modern Education OS
            </span>
          </div>
        </Link>

        {/* Centre Nav Links */}
        <div className="hidden lg:flex items-center space-x-1 bg-[#f0edec] dark:bg-[#1b211e] p-1.5 rounded-full border border-[#e5e2e1] dark:border-[#2f3732] shadow-inner">
          <Link
            href="#features"
            className="text-[#404945] dark:text-[#c0c8c4] hover:text-[#1c1b1b] dark:hover:text-[#e1e4e1] hover:bg-[#e5e2e1] dark:hover:bg-[#2f3732] rounded-full px-4 py-1.5 text-sm font-semibold transition-all"
          >
            Features
          </Link>
          <Link
            href="#solutions"
            className="text-[#404945] dark:text-[#c0c8c4] hover:text-[#1c1b1b] dark:hover:text-[#e1e4e1] hover:bg-[#e5e2e1] dark:hover:bg-[#2f3732] rounded-full px-4 py-1.5 text-sm font-semibold transition-all"
          >
            Solutions
          </Link>
          <Link
            href="#pricing"
            className="text-[#404945] dark:text-[#c0c8c4] hover:text-[#1c1b1b] dark:hover:text-[#e1e4e1] hover:bg-[#e5e2e1] dark:hover:bg-[#2f3732] rounded-full px-4 py-1.5 text-sm font-semibold transition-all"
          >
            Pricing
          </Link>
          <Link
            href="#ai-features"
            className="text-[#404945] dark:text-[#c0c8c4] hover:text-[#1c1b1b] dark:hover:text-[#e1e4e1] hover:bg-[#e5e2e1] dark:hover:bg-[#2f3732] rounded-full px-4 py-1.5 text-sm font-semibold transition-all flex items-center gap-1"
          >
            <span className="w-2 h-2 rounded-full bg-[#c3f185] animate-pulse"></span>
            AI Features
          </Link>
          <Link
            href="#faq"
            className="text-[#404945] dark:text-[#c0c8c4] hover:text-[#1c1b1b] dark:hover:text-[#e1e4e1] hover:bg-[#e5e2e1] dark:hover:bg-[#2f3732] rounded-full px-4 py-1.5 text-sm font-semibold transition-all"
          >
            FAQ
          </Link>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2 md:gap-3">
          {/* Dark Mode Toggle */}
          <button
            onClick={() => setDarkMode((prev) => !prev)}
            className="p-2.5 text-[#404945] dark:text-[#c0c8c4] hover:text-[#154539] dark:hover:text-[#a0d1c0] hover:bg-[#f0edec] dark:hover:bg-[#252c28] rounded-full transition-all"
            title={darkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}
          >
            <span className="material-symbols-outlined text-xl">
              {darkMode ? "light_mode" : "dark_mode"}
            </span>
          </button>

          {/* Login Link */}
          <Link
            href="/login"
            className="hidden sm:inline-flex text-[#154539] dark:text-[#a0d1c0] hover:bg-[#f0edec] dark:hover:bg-[#252c28] px-4 py-2 rounded-full text-xs md:text-sm font-semibold transition-all"
          >
            Login
          </Link>

          {/* Primary Get Started Button */}
          <Link
            href="/login"
            className="bg-[#154539] hover:bg-[#2f5d50] text-[#ffffff] dark:bg-[#a0d1c0] dark:hover:bg-[#bceddc] dark:text-[#00372d] px-5 py-2.5 rounded-full text-xs md:text-sm font-bold shadow-md hover:scale-105 active:scale-95 transition-all flex items-center gap-1.5"
          >
            <span>Get Started</span>
            <span className="material-symbols-outlined text-sm">
              arrow_forward
            </span>
          </Link>

          {/* Mobile Hamburger Toggle */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="lg:hidden p-2 text-[#1c1b1b] dark:text-[#e1e4e1]"
          >
            <span className="material-symbols-outlined text-2xl">
              {mobileMenuOpen ? "close" : "menu"}
            </span>
          </button>
        </div>
      </nav>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div className="lg:hidden pt-4 pb-6 px-4 border-t border-[#e5e2e1] dark:border-[#2f3732] mt-3 space-y-3 bg-[#fcf9f8] dark:bg-[#141816]">
          <Link
            href="#features"
            onClick={() => setMobileMenuOpen(false)}
            className="block text-sm font-semibold text-[#1c1b1b] dark:text-[#e1e4e1] py-2 px-3 hover:bg-[#f0edec] dark:hover:bg-[#1b211e] rounded-lg"
          >
            Features
          </Link>
          <Link
            href="#solutions"
            onClick={() => setMobileMenuOpen(false)}
            className="block text-sm font-semibold text-[#1c1b1b] dark:text-[#e1e4e1] py-2 px-3 hover:bg-[#f0edec] dark:hover:bg-[#1b211e] rounded-lg"
          >
            Solutions
          </Link>
          <Link
            href="#ai-features"
            onClick={() => setMobileMenuOpen(false)}
            className="block text-sm font-semibold text-[#1c1b1b] dark:text-[#e1e4e1] py-2 px-3 hover:bg-[#f0edec] dark:hover:bg-[#1b211e] rounded-lg"
          >
            AI Showcase
          </Link>
          <Link
            href="#pricing"
            onClick={() => setMobileMenuOpen(false)}
            className="block text-sm font-semibold text-[#1c1b1b] dark:text-[#e1e4e1] py-2 px-3 hover:bg-[#f0edec] dark:hover:bg-[#1b211e] rounded-lg"
          >
            Pricing
          </Link>
          <Link
            href="#faq"
            onClick={() => setMobileMenuOpen(false)}
            className="block text-sm font-semibold text-[#1c1b1b] dark:text-[#e1e4e1] py-2 px-3 hover:bg-[#f0edec] dark:hover:bg-[#1b211e] rounded-lg"
          >
            FAQ
          </Link>
          <div className="pt-2 flex flex-col gap-2">
            <Link
              href="/login"
              className="w-full text-center bg-[#f0edec] dark:bg-[#252c28] text-[#1c1b1b] dark:text-[#e1e4e1] py-2.5 rounded-full font-bold text-sm"
            >
              Login to Portal
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
