"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";

interface SearchModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface SearchResult {
  title: string;
  type: "PDF Document" | "Recorded Lecture" | "AI Flashcards" | "Exam Question" | "Class Notes";
  space: string;
  snippet: string;
  route: string;
}

export default function SearchModal({ isOpen, onClose }: SearchModalProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  const mockDatabase: SearchResult[] = [
    {
      title: "Calculus I - Integration by Parts Proof & Notes",
      type: "PDF Document",
      space: "Calculus & Linear Algebra",
      snippet: "∫ u dv = uv - ∫ v du. Learn how to choose u using the LIATE rule...",
      route: "/resources",
    },
    {
      title: "Machine Learning Lecture 04: Backpropagation & SGD",
      type: "Recorded Lecture",
      space: "CS402 AI & Neural Networks",
      snippet: "Timestamp 14:22: Gradient computation through hidden layers using chain rule...",
      route: "/resources",
    },
    {
      title: "Organic Chemistry Flashcard Deck - Functional Groups",
      type: "AI Flashcards",
      space: "Chemistry 101",
      snippet: "32 Flashcards auto-generated from Chapter 5 PDF uploaded by Dr. Miller...",
      route: "/ai-content",
    },
    {
      title: "Physics Mechanics Midterm Exam - Question Bank",
      type: "Exam Question",
      space: "Physics 101: Dynamics",
      snippet: "Calculate angular momentum for a rigid rotating cylinder given friction coefficient...",
      route: "/examinations",
    },
  ];

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        if (isOpen) onClose();
        else {
          // Open search modal via keyboard trigger
        }
      }
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setQuery(val);
    if (!val.trim()) {
      setResults([]);
      return;
    }
    setIsSearching(true);
    setTimeout(() => {
      const filtered = mockDatabase.filter(
        (item) =>
          item.title.toLowerCase().includes(val.toLowerCase()) ||
          item.snippet.toLowerCase().includes(val.toLowerCase()) ||
          item.space.toLowerCase().includes(val.toLowerCase())
      );
      setResults(filtered.length > 0 ? filtered : mockDatabase);
      setIsSearching(false);
    }, 300);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-start justify-center pt-20 p-4 animate-in fade-in duration-200">
      <div className="bg-[#fcf9f8] dark:bg-[#1b211e] border border-[#e5e2e1] dark:border-[#2f3732] rounded-3xl max-w-2xl w-full p-6 shadow-2xl relative overflow-hidden">
        {/* Input Bar */}
        <div className="flex items-center gap-3 border-b border-[#e5e2e1] dark:border-[#2f3732] pb-4 mb-4">
          <span className="material-symbols-outlined text-2xl text-[#154539] dark:text-[#a0d1c0]">
            search
          </span>
          <input
            type="text"
            value={query}
            onChange={handleSearch}
            autoFocus
            placeholder="Semantic Search across PDFs, video transcripts, notes & exams..."
            className="w-full bg-transparent text-sm text-[#1c1b1b] dark:text-[#e1e4e1] placeholder-[#717975] focus:outline-none font-medium"
          />
          <button
            onClick={onClose}
            className="p-1 text-[#717975] hover:text-[#1c1b1b] rounded-full"
          >
            <span className="material-symbols-outlined text-xl">close</span>
          </button>
        </div>

        {/* Results Body */}
        {isSearching ? (
          <div className="py-10 text-center text-xs text-[#717975]">
            <div className="w-6 h-6 border-2 border-[#154539] border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
            Searching vector index across course repositories...
          </div>
        ) : results.length > 0 ? (
          <div className="space-y-3 max-h-[60vh] overflow-y-auto pr-1">
            {results.map((res, i) => (
              <Link
                key={i}
                href={res.route}
                onClick={onClose}
                className="block bg-[#f0edec] dark:bg-[#252c28] hover:bg-[#e5e2e1] dark:hover:bg-[#2f3732] p-4 rounded-2xl transition-all border border-[#e5e2e1]/50 dark:border-[#2f3732]/50 group"
              >
                <div className="flex justify-between items-center mb-1">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#154539] dark:text-[#a0d1c0]">
                    {res.space}
                  </span>
                  <span className="text-[10px] bg-[#c3f185] text-[#112000] px-2 py-0.5 rounded-full font-bold">
                    {res.type}
                  </span>
                </div>
                <h4 className="text-sm font-bold text-[#1c1b1b] dark:text-[#e1e4e1] group-hover:text-[#154539] dark:group-hover:text-[#a0d1c0] transition-colors">
                  {res.title}
                </h4>
                <p className="text-xs text-[#717975] dark:text-[#c0c8c4] mt-1 line-clamp-2">
                  {res.snippet}
                </p>
              </Link>
            ))}
          </div>
        ) : query ? (
          <div className="py-8 text-center text-xs text-[#717975]">
            No exact semantic match found for "{query}". Try searching "Calculus", "Physics", or "Neural Networks".
          </div>
        ) : (
          <div className="py-6 text-xs text-[#717975]">
            <p className="font-semibold text-[#1c1b1b] dark:text-[#e1e4e1] mb-2">
              Popular Quick Searches:
            </p>
            <div className="flex flex-wrap gap-2">
              {["Calculus I Notes", "AI Lecture Summary", "Chemistry Flashcards", "Proctoring Logs"].map((qs, i) => (
                <button
                  key={i}
                  onClick={() => handleSearch({ target: { value: qs } } as any)}
                  className="bg-[#f0edec] dark:bg-[#252c28] hover:bg-[#e5e2e1] px-3 py-1 rounded-full text-xs text-[#1c1b1b] dark:text-[#e1e4e1] transition-all"
                >
                  {qs}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
