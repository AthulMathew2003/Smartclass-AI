"use client";

import React, { useState } from "react";

interface AiResponse {
  query: string;
  type: "explanation" | "flashcards" | "summary" | "quiz";
  markdown: string;
  sourceDoc?: string;
  flashcards?: { front: string; back: string }[];
}

export default function InteractiveAiSandbox() {
  const [prompt, setPrompt] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"tutor" | "generator" | "rag">("tutor");
  const [currentResponse, setCurrentResponse] = useState<AiResponse>({
    query: "Explain Newton's Second Law with an intuitive visual example",
    type: "explanation",
    sourceDoc: "Physics_101_Chapter3_Dynamics.pdf (Page 42)",
    markdown: `### **Newton's Second Law of Motion: Force & Acceleration**

Newton's Second Law establishes the fundamental mathematical relationship between force, mass, and acceleration:

$$\\mathbf{F} = m \\cdot \\mathbf{a}$$

#### **Key Takeaways from Course Materials:**
1. **Force ($F$):** Measured in Newtons ($N = \\text{kg}\\cdot\\text{m/s}^2$). Directly proportional to acceleration.
2. **Mass ($m$):** Inertial resistance to changes in motion (measured in kg).
3. **Acceleration ($a$):** Rate of change of velocity.

> **Visual Analogy:** Pushing a light shopping cart vs. a heavy freight car with the exact same muscular force. The lighter cart accelerates instantly because its mass $m$ is smaller!`,
  });

  const samplePrompts = [
    {
      label: "Physics: Newton's Law",
      text: "Explain Newton's Second Law with an intuitive visual example",
      type: "explanation" as const,
      sourceDoc: "Physics_101_Chapter3.pdf",
      res: {
        query: "Explain Newton's Second Law with an intuitive visual example",
        type: "explanation" as const,
        sourceDoc: "Physics_101_Chapter3.pdf (Page 42)",
        markdown: `### **Newton's Second Law of Motion: Force & Acceleration**

Newton's Second Law establishes the fundamental mathematical relationship between force, mass, and acceleration:

$$\\mathbf{F} = m \\cdot \\mathbf{a}$$

#### **Key Takeaways from Course Materials:**
1. **Force ($F$):** Measured in Newtons ($N = \\text{kg}\\cdot\\text{m/s}^2$).
2. **Mass ($m$):** Inertial resistance to changes in motion (in kg).
3. **Acceleration ($a$):** Rate of change of velocity over time.

> **Visual Analogy:** Pushing a light shopping cart vs. a heavy freight truck with equal strength!`,
      },
    },
    {
      label: "Chemistry: 3 Flashcards",
      text: "Generate 3 flashcards for Organic Chemistry - Alkanes vs Alkenes",
      type: "flashcards" as const,
      sourceDoc: "Organic_Chem_Lecture_Notes.pdf",
      res: {
        query: "Generate 3 flashcards for Organic Chemistry - Alkanes vs Alkenes",
        type: "flashcards" as const,
        sourceDoc: "Organic_Chem_Lecture_Notes.pdf",
        markdown: "Here are 3 AI-generated flashcards for rapid revision:",
        flashcards: [
          {
            front: "What is the key structural difference between Alkanes and Alkenes?",
            back: "Alkanes contain single C-C bonds (saturated), whereas Alkenes contain at least one double C=C bond (unsaturated).",
          },
          {
            front: "What is the general formula for Alkanes?",
            back: "C_n H_{2n+2}",
          },
          {
            front: "Which reaction test distinguishes Alkenes from Alkanes?",
            back: "Bromine Water Test: Alkenes rapidly decolorize bromine water from brown to clear.",
          },
        ],
      },
    },
    {
      label: "AI Lecture Summary",
      text: "Summarize uploaded lecture PDF on Deep Neural Networks",
      type: "summary" as const,
      sourceDoc: "CS402_Neural_Networks_Slides.pdf",
      res: {
        query: "Summarize uploaded lecture PDF on Deep Neural Networks",
        type: "summary" as const,
        sourceDoc: "CS402_Neural_Networks_Slides.pdf (Slides 1-28)",
        markdown: `### **Executive Lecture Summary: Deep Neural Networks**

* **Core Architecture:** Input Layer $\\rightarrow$ Hidden Layers (Weights & Biases) $\\rightarrow$ Activation Function $\\rightarrow$ Output.
* **Backpropagation:** Computes gradient of loss function with respect to weights using the Chain Rule.
* **Optimization Algorithms:** Stochastic Gradient Descent (SGD), Adam, and RMSprop.
* **Common Activation Functions:** ReLU ($f(x) = \\max(0, x)$), Sigmoid, Softmax for classification.`,
      },
    },
  ];

  const handleSelectSample = (sample: (typeof samplePrompts)[0]) => {
    setPrompt(sample.text);
    setIsLoading(true);
    setTimeout(() => {
      setCurrentResponse(sample.res);
      setIsLoading(false);
    }, 600);
  };

  const handleCustomSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    setIsLoading(true);
    setTimeout(() => {
      setCurrentResponse({
        query: prompt,
        type: "explanation",
        sourceDoc: "SmartClass_Knowledge_Base.pdf",
        markdown: `### **AI Tutor Response for:** *"${prompt}"*

Based on your enrolled course syllabus and uploaded textbook notes:

1. **Core Concept:** This concept connects directly to your previous lecture on foundational principles.
2. **Step-by-Step Breakdown:**
   - **Step A:** Formulate the input parameters and target objective.
   - **Step B:** Apply algorithmic constraints and evaluate performance.
   - **Step C:** Verify results against benchmark test cases.

> **Smart Tutor Recommendation:** You have a 92% mastery in prerequisite topics. Review Chapter 4 for practice problems!`,
      });
      setIsLoading(false);
    }, 800);
  };

  return (
    <section id="sandbox" className="w-full max-w-[1920px] mx-auto px-4 sm:px-8 md:px-12 lg:px-16 py-16 md:py-24">
      <div className="bg-[#154539] text-white rounded-3xl p-6 sm:p-10 lg:p-12 shadow-2xl relative overflow-hidden">
        {/* Background Subtle Gradient Circles */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-[#c3f185]/10 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-[#ff9a5c]/10 rounded-full blur-3xl pointer-events-none"></div>

        <div className="relative z-10">
          {/* Header */}
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8 border-b border-white/10 pb-6">
            <div>
              <span className="bg-[#c3f185] text-[#112000] px-3.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider">
                Live Interactive Sandbox
              </span>
              <h2 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold mt-2 tracking-tight">
                Try the SmartClass AI Learning Engine
              </h2>
            </div>

            {/* Mode Tabs */}
            <div className="flex bg-[#2f5d50] p-1.5 rounded-full border border-white/10">
              <button
                onClick={() => setActiveTab("tutor")}
                className={`px-4 py-1.5 rounded-full text-xs font-bold transition-all ${
                  activeTab === "tutor"
                    ? "bg-[#c3f185] text-[#112000] shadow"
                    : "text-white/80 hover:text-white"
                }`}
              >
                AI Tutor (RAG)
              </button>
              <button
                onClick={() => setActiveTab("generator")}
                className={`px-4 py-1.5 rounded-full text-xs font-bold transition-all ${
                  activeTab === "generator"
                    ? "bg-[#ff9a5c] text-[#733200] shadow"
                    : "text-white/80 hover:text-white"
                }`}
              >
                Content Generator
              </button>
            </div>
          </div>

          {/* Preset Prompts Buttons */}
          <div className="mb-6">
            <span className="text-xs text-[#a3d4c3] font-semibold block mb-2">
              Select a sample prompt or type custom query below:
            </span>
            <div className="flex flex-wrap gap-2">
              {samplePrompts.map((sample, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSelectSample(sample)}
                  className="bg-white/10 hover:bg-white/20 border border-white/15 px-3.5 py-1.5 rounded-full text-xs font-medium transition-all text-white flex items-center gap-1.5"
                >
                  <span className="material-symbols-outlined text-sm text-[#c3f185]">
                    lightbulb
                  </span>
                  <span>{sample.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Search Input Box */}
          <form onSubmit={handleCustomSubmit} className="relative mb-8">
            <input
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Ask AI Tutor anything about your syllabus, formula proofs, or request flashcards..."
              className="w-full bg-[#2f5d50] border border-[#a3d4c3]/30 rounded-2xl px-5 py-4 text-sm text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-[#c3f185] pr-28 shadow-inner"
            />
            <button
              type="submit"
              disabled={isLoading}
              className="absolute right-2 top-2 bottom-2 bg-[#c3f185] hover:bg-[#a7d56c] text-[#112000] px-5 rounded-xl text-xs font-extrabold transition-all flex items-center gap-1 shadow-md disabled:opacity-50"
            >
              {isLoading ? (
                <span>Processing...</span>
              ) : (
                <>
                  <span>Ask AI</span>
                  <span className="material-symbols-outlined text-sm">send</span>
                </>
              )}
            </button>
          </form>

          {/* Output Display Card */}
          <div className="bg-[#2f5d50]/80 border border-white/10 rounded-2xl p-6 relative">
            <div className="flex justify-between items-center border-b border-white/10 pb-3 mb-4 text-xs text-[#a3d4c3]">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-base text-[#c3f185]">
                  auto_stories
                </span>
                <span className="font-bold text-white">SmartClass AI Response</span>
              </div>
              {currentResponse.sourceDoc && (
                <div className="flex items-center gap-1 bg-white/10 px-3 py-1 rounded-full text-[11px]">
                  <span className="material-symbols-outlined text-xs">
                    description
                  </span>
                  <span>Grounding Source: {currentResponse.sourceDoc}</span>
                </div>
              )}
            </div>

            {isLoading ? (
              <div className="py-12 flex flex-col items-center justify-center gap-3">
                <div className="w-8 h-8 border-3 border-[#c3f185] border-t-transparent rounded-full animate-spin"></div>
                <p className="text-xs text-[#a3d4c3] animate-pulse">
                  Querying vector database & generating grounded response...
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="prose prose-invert max-w-none text-sm leading-relaxed text-white/95 whitespace-pre-line font-sans">
                  {currentResponse.markdown}
                </div>

                {/* Flashcards View if type is flashcards */}
                {currentResponse.flashcards && (
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4">
                    {currentResponse.flashcards.map((fc, i) => (
                      <div
                        key={i}
                        className="bg-[#154539] p-4 rounded-xl border border-[#c3f185]/30 hover:border-[#c3f185] transition-all flex flex-col justify-between"
                      >
                        <span className="text-[10px] font-extrabold text-[#c3f185] uppercase tracking-wider">
                          Flashcard #{i + 1}
                        </span>
                        <p className="text-xs font-bold text-white my-2">
                          Q: {fc.front}
                        </p>
                        <p className="text-[11px] text-[#a3d4c3] bg-black/20 p-2 rounded-lg mt-auto">
                          A: {fc.back}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
