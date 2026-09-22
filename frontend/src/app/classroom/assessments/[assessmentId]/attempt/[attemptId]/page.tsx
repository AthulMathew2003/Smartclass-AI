"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  fetchAssessmentAttempt,
  saveAttemptAnswer,
  submitAssessmentAttempt,
  AssessmentAttempt,
  StudentAttemptQuestion,
  StudentAttemptAnswer
} from "@/lib/assessments";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from "@/components/ui/dialog";

// ── Countdown Timer Hook ───────────────────────────────────────
// Returns remaining seconds derived from server-provided expires_at.
// The server is authoritative — this is display-only.
function useCountdown(expiresAt: string | null | undefined): number | null {
  const [remaining, setRemaining] = useState<number | null>(null);

  useEffect(() => {
    if (!expiresAt) {
      setRemaining(null);
      return;
    }

    const computeRemaining = () => {
      const now = Date.now();
      const expiry = new Date(expiresAt).getTime();
      return Math.max(0, Math.floor((expiry - now) / 1000));
    };

    setRemaining(computeRemaining());
    const id = setInterval(() => {
      const secs = computeRemaining();
      setRemaining(secs);
    }, 1000);

    return () => clearInterval(id);
  }, [expiresAt]);

  return remaining;
}

function formatCountdown(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

// ── Retry Autosave Helper ──────────────────────────────────────
const MAX_RETRIES = 3;

async function saveWithRetry(
  assessmentId: string,
  attemptId: string,
  questionId: string,
  answer: StudentAttemptAnswer,
  retries = 0
): Promise<void> {
  try {
    await saveAttemptAnswer(assessmentId, attemptId, questionId, answer);
  } catch (err: any) {
    // If the server explicitly says the attempt is expired, re-throw immediately
    if (err?.code === "ATTEMPT_EXPIRED" || err?.status === 410) {
      throw err;
    }
    if (retries < MAX_RETRIES) {
      const delay = Math.pow(2, retries) * 1000; // 1s → 2s → 4s
      await new Promise((resolve) => setTimeout(resolve, delay));
      return saveWithRetry(assessmentId, attemptId, questionId, answer, retries + 1);
    }
    throw err;
  }
}

// ── Component ─────────────────────────────────────────────────
export default function AssessmentAttemptTakingPage() {
  const params = useParams();
  const router = useRouter();
  const assessmentId = params.assessmentId as string;
  const attemptId = params.attemptId as string;

  const [attempt, setAttempt] = useState<AssessmentAttempt | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Current Question Navigation
  const [currentIndex, setCurrentIndex] = useState(0);

  // Local answers state keyed by assessment_question_id
  const [answers, setAnswers] = useState<Record<string, StudentAttemptAnswer>>({});

  // Global save status: "idle" | "saving" | "saved" | "error" | "retrying"
  const [globalSaveStatus, setGlobalSaveStatus] = useState<"idle" | "saving" | "saved" | "error" | "retrying">("idle");
  const globalSaveTimer = useRef<NodeJS.Timeout | null>(null);

  // Per-question save states for granular indicators
  const [saveStatus, setSaveStatus] = useState<Record<string, "idle" | "saving" | "saved" | "error">>({});

  // Submit Modal
  const [isSubmitModalOpen, setIsSubmitModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmittedSuccess, setIsSubmittedSuccess] = useState(false);

  // Expiry state
  const [isExpired, setIsExpired] = useState(false);
  const [autoSubmitting, setAutoSubmitting] = useState(false);
  const expiryHandled = useRef(false);

  // Auto-save debounce ref (for text answers)
  const debounceTimers = useRef<Record<string, NodeJS.Timeout>>({});

  // Countdown timer
  const remainingSeconds = useCountdown(attempt?.attempt_expires_at);

  // ── Auto-submit when timer reaches 0 ──────────────────────────
  useEffect(() => {
    if (
      remainingSeconds === 0 &&
      attempt &&
      attempt.attempt_status === "in_progress" &&
      !isExpired &&
      !isSubmittedSuccess &&
      !expiryHandled.current
    ) {
      expiryHandled.current = true;
      handleTimerExpiry();
    }
  }, [remainingSeconds]);

  // Handle expiry — attempt auto-submit, fall back to showing expired screen
  async function handleTimerExpiry() {
    setAutoSubmitting(true);
    try {
      const updated = await submitAssessmentAttempt(assessmentId, attemptId);
      setAttempt(updated);
      setIsSubmittedSuccess(true);
    } catch {
      // Server may return ATTEMPT_EXPIRED (410) — either way show expired screen
      setIsExpired(true);
    } finally {
      setAutoSubmitting(false);
    }
  }

  useEffect(() => {
    loadAttempt();
    return () => {
      Object.values(debounceTimers.current).forEach(clearTimeout);
      if (globalSaveTimer.current) clearTimeout(globalSaveTimer.current);
    };
  }, [assessmentId, attemptId]);

  async function loadAttempt() {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchAssessmentAttempt(assessmentId, attemptId);
      setAttempt(data);
      setAnswers(data.answers || {});
      if (data.attempt_status === "submitted") {
        setIsSubmittedSuccess(true);
      } else if (data.attempt_status === "expired") {
        setIsExpired(true);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load assessment attempt.");
    } finally {
      setLoading(false);
    }
  }

  // Update global save indicator
  const setGlobalSaving = () => {
    if (globalSaveTimer.current) clearTimeout(globalSaveTimer.current);
    setGlobalSaveStatus("saving");
  };

  const setGlobalSaved = () => {
    if (globalSaveTimer.current) clearTimeout(globalSaveTimer.current);
    setGlobalSaveStatus("saved");
    globalSaveTimer.current = setTimeout(() => setGlobalSaveStatus("idle"), 3000);
  };

  const setGlobalError = () => {
    if (globalSaveTimer.current) clearTimeout(globalSaveTimer.current);
    setGlobalSaveStatus("error");
  };

  // Persist answer with retry
  const persistAnswer = useCallback(async (questionId: string, answerPayload: StudentAttemptAnswer) => {
    setSaveStatus((prev) => ({ ...prev, [questionId]: "saving" }));
    setGlobalSaving();
    try {
      await saveWithRetry(assessmentId, attemptId, questionId, answerPayload);
      setSaveStatus((prev) => ({ ...prev, [questionId]: "saved" }));
      setGlobalSaved();
      setTimeout(() => {
        setSaveStatus((prev) => ({ ...prev, [questionId]: "idle" }));
      }, 2000);
    } catch (err: any) {
      const isExpiredError = err?.code === "ATTEMPT_EXPIRED" || err?.status === 410;
      setSaveStatus((prev) => ({ ...prev, [questionId]: "error" }));
      setGlobalError();
      if (isExpiredError && !expiryHandled.current) {
        expiryHandled.current = true;
        setIsExpired(true);
      }
    }
  }, [assessmentId, attemptId]);

  const handleSelectSingleOption = (questionId: string, optionId: string) => {
    if (attempt?.attempt_status !== "in_progress" || isExpired) return;
    const newAnswer: StudentAttemptAnswer = { selected_option_id: optionId };
    setAnswers((prev) => ({ ...prev, [questionId]: newAnswer }));
    persistAnswer(questionId, newAnswer);
  };

  const handleToggleMultipleOption = (questionId: string, optionId: string) => {
    if (attempt?.attempt_status !== "in_progress" || isExpired) return;
    const currentList = answers[questionId]?.selected_option_ids || [];
    const exists = currentList.includes(optionId);
    const updatedList = exists
      ? currentList.filter((id) => id !== optionId)
      : [...currentList, optionId];

    const newAnswer: StudentAttemptAnswer = { selected_option_ids: updatedList };
    setAnswers((prev) => ({ ...prev, [questionId]: newAnswer }));
    persistAnswer(questionId, newAnswer);
  };

  const handleTextAnswerChange = (questionId: string, text: string) => {
    if (attempt?.attempt_status !== "in_progress" || isExpired) return;
    const newAnswer: StudentAttemptAnswer = { text_answer: text };
    setAnswers((prev) => ({ ...prev, [questionId]: newAnswer }));

    if (debounceTimers.current[questionId]) clearTimeout(debounceTimers.current[questionId]);
    setSaveStatus((prev) => ({ ...prev, [questionId]: "saving" }));
    setGlobalSaving();
    debounceTimers.current[questionId] = setTimeout(() => {
      persistAnswer(questionId, newAnswer);
    }, 700);
  };

  const handleSubmitAttempt = async () => {
    try {
      setSubmitting(true);
      setSubmitError(null);
      const updated = await submitAssessmentAttempt(assessmentId, attemptId);
      setAttempt(updated);
      setIsSubmitModalOpen(false);
      setIsSubmittedSuccess(true);
    } catch (err: any) {
      const isExpiredError = err?.code === "ATTEMPT_EXPIRED" || err?.status === 410;
      if (isExpiredError) {
        setIsSubmitModalOpen(false);
        setIsExpired(true);
      } else {
        setSubmitError(err.message || "Failed to submit assessment.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  // ── Render: Loading ──
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex items-center gap-3 text-sm font-semibold text-[var(--on-surface-variant)]">
          <div className="w-6 h-6 border-2 border-t-transparent border-[var(--primary)] rounded-full animate-spin" />
          Loading assessment session...
        </div>
      </div>
    );
  }

  // ── Render: Error ──
  if (error || !attempt) {
    return (
      <div className="p-8 text-center max-w-lg mx-auto space-y-4">
        <span className="material-symbols-outlined text-[48px] text-red-500 block">error</span>
        <h2 className="text-xl font-bold text-[var(--on-surface)]">Assessment Attempt Unavailable</h2>
        <p className="text-sm text-[var(--on-surface-variant)]">{error || "Unable to load this attempt."}</p>
        <Button
          onClick={() => router.push(`/classroom/assessments/${assessmentId}`)}
          variant="outline"
          className="mt-2"
        >
          Back to Assessment Overview
        </Button>
      </div>
    );
  }

  const questions = attempt.questions || [];
  const currentQ: StudentAttemptQuestion | undefined = questions[currentIndex];

  const isQuestionAnswered = (qId: string) => {
    const ans = answers[qId];
    if (!ans) return false;
    if (ans.selected_option_id) return true;
    if (ans.selected_option_ids && ans.selected_option_ids.length > 0) return true;
    if (ans.text_answer && ans.text_answer.trim().length > 0) return true;
    return false;
  };

  const answeredCount = questions.filter((q) => isQuestionAnswered(q.assessment_question_id)).length;
  const unansweredCount = questions.length - answeredCount;

  // ── Render: Expired Overlay Screen ──
  if (isExpired || attempt.attempt_status === "expired") {
    return (
      <div className="p-6 md:p-12 max-w-3xl mx-auto space-y-6 animate-in fade-in duration-300">
        <div className="bg-[var(--surface-container-lowest)] border border-red-500/30 rounded-3xl p-8 md:p-12 text-center shadow-lg space-y-6">
          {autoSubmitting ? (
            <div className="w-20 h-20 rounded-3xl flex items-center justify-center mx-auto bg-amber-500/10">
              <div className="w-10 h-10 border-4 border-t-transparent border-amber-500 rounded-full animate-spin" />
            </div>
          ) : (
            <div className="w-20 h-20 bg-red-500/10 text-red-500 rounded-3xl flex items-center justify-center mx-auto shadow-inner">
              <span className="material-symbols-outlined text-[42px]">timer_off</span>
            </div>
          )}

          <div className="space-y-2">
            <h1 className="text-2xl md:text-3xl font-bold text-[var(--on-surface)]">
              {autoSubmitting ? "Submitting your answers..." : "Time's Up!"}
            </h1>
            <p className="text-sm text-[var(--on-surface-variant)] max-w-md mx-auto">
              {autoSubmitting
                ? "Your attempt is being saved. Please wait."
                : "Your assessment time has expired. All saved answers have been recorded."}
            </p>
          </div>

          {!autoSubmitting && (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-sm mx-auto text-left">
                <div className="bg-[var(--surface-container-low)] p-4 rounded-2xl border border-[var(--outline-variant)]">
                  <span className="text-xs text-[var(--on-surface-variant)] font-medium">Attempt</span>
                  <div className="text-lg font-bold text-[var(--on-surface)] mt-0.5">#{attempt.attempt_number}</div>
                </div>
                <div className="bg-[var(--surface-container-low)] p-4 rounded-2xl border border-[var(--outline-variant)]">
                  <span className="text-xs text-[var(--on-surface-variant)] font-medium">Answers Saved</span>
                  <div className="text-lg font-bold text-red-500 mt-0.5">{answeredCount} / {questions.length}</div>
                </div>
              </div>

              <div className="pt-4 flex items-center justify-center gap-3">
                <Button
                  onClick={() => router.push(`/classroom/assessments/${assessmentId}/attempt/${attemptId}/result`)}
                  className="px-6 rounded-xl font-semibold shadow-sm bg-blue-600 hover:bg-blue-700 text-white flex items-center gap-2"
                >
                  <span className="material-symbols-outlined text-[18px]">analytics</span>
                  View Results
                </Button>
                <Button
                  onClick={() => router.push(`/classroom/assessments/${assessmentId}`)}
                  variant="outline"
                  className="px-6 rounded-xl font-semibold shadow-sm"
                >
                  <span className="material-symbols-outlined mr-2 text-[18px]">arrow_back</span>
                  Back to Assessment
                </Button>
              </div>
            </>
          )}
        </div>
      </div>
    );
  }

  // ── Render: Submitted Success View ──
  if (isSubmittedSuccess || attempt.attempt_status === "submitted") {
    return (
      <div className="p-6 md:p-12 max-w-3xl mx-auto space-y-6 animate-in fade-in duration-300">
        <div className="bg-[var(--surface-container-lowest)] border border-[var(--outline-variant)] rounded-3xl p-8 md:p-12 text-center shadow-lg space-y-6">
          <div className="w-20 h-20 bg-emerald-500/10 text-emerald-600 rounded-3xl flex items-center justify-center mx-auto shadow-inner">
            <span className="material-symbols-outlined text-[42px]">check_circle</span>
          </div>

          <div className="space-y-2">
            <h1 className="text-2xl md:text-3xl font-bold text-[var(--on-surface)]">
              Attempt Submitted Successfully!
            </h1>
            <p className="text-sm text-[var(--on-surface-variant)] max-w-md mx-auto">
              Your responses for Attempt #{attempt.attempt_number} have been safely recorded and evaluated.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-md mx-auto text-left">
            <div className="bg-[var(--surface-container-low)] p-4 rounded-2xl border border-[var(--outline-variant)]">
              <span className="text-xs text-[var(--on-surface-variant)] font-medium">Attempt</span>
              <div className="text-lg font-bold text-[var(--on-surface)] mt-0.5">#{attempt.attempt_number}</div>
            </div>
            <div className="bg-[var(--surface-container-low)] p-4 rounded-2xl border border-[var(--outline-variant)]">
              <span className="text-xs text-[var(--on-surface-variant)] font-medium">Questions Answered</span>
              <div className="text-lg font-bold text-emerald-600 mt-0.5">{answeredCount} / {questions.length}</div>
            </div>
            <div className="bg-[var(--surface-container-low)] p-4 rounded-2xl border border-[var(--outline-variant)]">
              <span className="text-xs text-[var(--on-surface-variant)] font-medium">Submitted At</span>
              <div className="text-xs font-bold text-[var(--on-surface)] mt-1 truncate">
                {attempt.attempt_submitted_at
                  ? new Date(attempt.attempt_submitted_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                  : "Just now"}
              </div>
            </div>
          </div>

          <div className="pt-4 flex items-center justify-center gap-3">
            <Button
              onClick={() => router.push(`/classroom/assessments/${assessmentId}/attempt/${attemptId}/result`)}
              className="px-6 rounded-xl font-semibold shadow-sm bg-emerald-600 hover:bg-emerald-700 text-white flex items-center gap-2"
            >
              <span className="material-symbols-outlined text-[18px]">assignment_turned_in</span>
              View Results
            </Button>
            <Button
              onClick={() => router.push(`/classroom/assessments/${assessmentId}`)}
              variant="outline"
              className="px-6 rounded-xl font-semibold shadow-sm"
            >
              <span className="material-symbols-outlined mr-2 text-[18px]">arrow_back</span>
              Back to Assessment Details
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // ── Timer Color Logic ──
  const timerIsWarning = remainingSeconds !== null && remainingSeconds <= 300 && remainingSeconds > 60;
  const timerIsCritical = remainingSeconds !== null && remainingSeconds <= 60;

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-6">
      {/* Top Header Bar */}
      <div className="bg-[var(--surface-container-lowest)] border border-[var(--outline-variant)] rounded-2xl p-4 md:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-sm">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push(`/classroom/assessments/${assessmentId}`)}
            className="w-9 h-9 rounded-xl bg-[var(--surface-container-low)] hover:bg-[var(--surface-container-high)] flex items-center justify-center text-[var(--on-surface-variant)] transition-colors"
            title="Exit to assessment overview"
          >
            <span className="material-symbols-outlined text-[20px]">arrow_back</span>
          </button>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-bold px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-600 dark:text-blue-400">
                Attempt #{attempt.attempt_number}
              </span>
              <Badge variant="outline" className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 text-xs">
                In Progress
              </Badge>
            </div>
            <h1 className="text-base sm:text-lg font-bold text-[var(--on-surface)] mt-0.5">
              Question {currentIndex + 1} of {questions.length}
            </h1>
          </div>
        </div>

        {/* Right: Countdown + Global Save + Submit */}
        <div className="flex items-center gap-3 flex-wrap justify-end">
          {/* Global Autosave Status */}
          <div className="text-xs font-medium min-w-[90px] text-right">
            {globalSaveStatus === "saving" && (
              <span className="text-amber-500 flex items-center gap-1 justify-end">
                <span className="material-symbols-outlined text-[14px] animate-spin">sync</span>
                Saving...
              </span>
            )}
            {globalSaveStatus === "saved" && (
              <span className="text-emerald-500 flex items-center gap-1 justify-end">
                <span className="material-symbols-outlined text-[14px]">cloud_done</span>
                All saved
              </span>
            )}
            {globalSaveStatus === "error" && (
              <span className="text-red-500 flex items-center gap-1 justify-end">
                <span className="material-symbols-outlined text-[14px]">cloud_off</span>
                Save failed
              </span>
            )}
          </div>

          {/* Countdown Timer */}
          {remainingSeconds !== null && (
            <div
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl font-mono font-bold text-sm border transition-colors ${
                timerIsCritical
                  ? "bg-red-500/15 text-red-600 border-red-500/30 animate-pulse"
                  : timerIsWarning
                  ? "bg-amber-500/15 text-amber-600 border-amber-500/30"
                  : "bg-[var(--surface-container-low)] text-[var(--on-surface)] border-[var(--outline-variant)]"
              }`}
              title="Time remaining"
            >
              <span className="material-symbols-outlined text-[16px]">
                {timerIsCritical ? "timer_off" : "timer"}
              </span>
              {formatCountdown(remainingSeconds)}
            </div>
          )}

          {/* Answered count */}
          <div className="text-right hidden sm:block">
            <div className="text-xs text-[var(--on-surface-variant)] font-medium">Answered</div>
            <div className="text-sm font-bold text-[var(--on-surface)]">
              {answeredCount} / {questions.length}
            </div>
          </div>

          <Button
            onClick={() => setIsSubmitModalOpen(true)}
            className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-xl px-5 shadow-sm flex items-center gap-2"
          >
            <span className="material-symbols-outlined text-[18px]">send</span>
            Submit
          </Button>
        </div>
      </div>

      {/* Main Content: Question Area + Navigator */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">
        {/* Left: Current Question */}
        <div className="lg:col-span-3 space-y-4">
          {currentQ ? (
            <div className="bg-[var(--surface-container-lowest)] border border-[var(--outline-variant)] rounded-3xl p-6 md:p-8 shadow-sm space-y-6">
              {/* Question Header */}
              <div className="flex items-center justify-between pb-4 border-b border-[var(--outline-variant)]">
                <div className="flex items-center gap-2.5">
                  <span className="text-xs font-bold px-3 py-1 rounded-xl bg-[var(--primary)] text-[var(--on-primary)] shadow-sm">
                    Question {currentIndex + 1}
                  </span>
                  <span className="text-xs font-semibold px-2.5 py-1 rounded-lg bg-[var(--surface-container-high)] text-[var(--on-surface-variant)]">
                    {currentQ.question_type === "mcq_single" && "Single Choice"}
                    {currentQ.question_type === "mcq_multiple" && "Multiple Choice"}
                    {currentQ.question_type === "true_false" && "True / False"}
                    {currentQ.question_type === "short_answer" && "Short Answer"}
                  </span>
                </div>

                <div className="flex items-center gap-3">
                  {/* Per-question save indicator */}
                  <div className="text-xs font-medium">
                    {saveStatus[currentQ.assessment_question_id] === "saving" && (
                      <span className="text-amber-500 flex items-center gap-1">
                        <span className="material-symbols-outlined text-[14px] animate-spin">sync</span>
                        Saving...
                      </span>
                    )}
                    {saveStatus[currentQ.assessment_question_id] === "saved" && (
                      <span className="text-emerald-500 flex items-center gap-1">
                        <span className="material-symbols-outlined text-[14px]">check</span>
                        Saved
                      </span>
                    )}
                    {saveStatus[currentQ.assessment_question_id] === "error" && (
                      <span className="text-red-500 flex items-center gap-1">
                        <span className="material-symbols-outlined text-[14px]">error</span>
                        Save failed
                      </span>
                    )}
                  </div>

                  <span className="text-xs font-bold px-2.5 py-1 rounded-lg bg-[var(--surface-container-low)] text-[var(--on-surface)] border border-[var(--outline-variant)]">
                    {currentQ.marks} {Number(currentQ.marks) === 1 ? "Mark" : "Marks"}
                  </span>
                </div>
              </div>

              {/* Question Text */}
              <div className="text-base sm:text-lg font-medium text-[var(--on-surface)] leading-relaxed whitespace-pre-wrap">
                {currentQ.question_text}
              </div>

              {/* Answer Options */}
              <div className="pt-2">
                {/* 1. Single Choice */}
                {currentQ.question_type === "mcq_single" && (
                  <div className="space-y-3">
                    {currentQ.options.map((opt) => {
                      const isSelected = answers[currentQ.assessment_question_id]?.selected_option_id === opt.option_id;
                      return (
                        <button
                          key={opt.option_id}
                          type="button"
                          onClick={() => handleSelectSingleOption(currentQ.assessment_question_id, opt.option_id!)}
                          disabled={isExpired}
                          className={`w-full text-left p-4 rounded-2xl border transition-all flex items-center gap-4 ${
                            isSelected
                              ? "border-[var(--primary)] bg-blue-500/10 shadow-sm"
                              : "border-[var(--outline-variant)] bg-[var(--surface-container-low)] hover:border-[var(--primary)] hover:bg-[var(--surface-container-high)]"
                          } disabled:opacity-50 disabled:cursor-not-allowed`}
                        >
                          <div
                            className={`w-6 h-6 rounded-full border-2 flex-shrink-0 flex items-center justify-center transition-all ${
                              isSelected
                                ? "border-[var(--primary)] bg-[var(--primary)] text-white"
                                : "border-[var(--outline-variant)]"
                            }`}
                          >
                            {isSelected && <div className="w-2 h-2 rounded-full bg-white" />}
                          </div>
                          <span className="text-sm font-medium text-[var(--on-surface)]">{opt.option_text}</span>
                        </button>
                      );
                    })}
                  </div>
                )}

                {/* 2. Multiple Choice */}
                {currentQ.question_type === "mcq_multiple" && (
                  <div className="space-y-3">
                    <p className="text-xs text-[var(--on-surface-variant)] mb-2">(Select all that apply)</p>
                    {currentQ.options.map((opt) => {
                      const selectedList = answers[currentQ.assessment_question_id]?.selected_option_ids || [];
                      const isSelected = selectedList.includes(opt.option_id!);
                      return (
                        <button
                          key={opt.option_id}
                          type="button"
                          onClick={() => handleToggleMultipleOption(currentQ.assessment_question_id, opt.option_id!)}
                          disabled={isExpired}
                          className={`w-full text-left p-4 rounded-2xl border transition-all flex items-center gap-4 ${
                            isSelected
                              ? "border-[var(--primary)] bg-blue-500/10 shadow-sm"
                              : "border-[var(--outline-variant)] bg-[var(--surface-container-low)] hover:border-[var(--primary)] hover:bg-[var(--surface-container-high)]"
                          } disabled:opacity-50 disabled:cursor-not-allowed`}
                        >
                          <div
                            className={`w-6 h-6 rounded-lg border-2 flex-shrink-0 flex items-center justify-center transition-all ${
                              isSelected
                                ? "border-[var(--primary)] bg-[var(--primary)] text-white"
                                : "border-[var(--outline-variant)]"
                            }`}
                          >
                            {isSelected && <span className="material-symbols-outlined text-[16px]">check</span>}
                          </div>
                          <span className="text-sm font-medium text-[var(--on-surface)]">{opt.option_text}</span>
                        </button>
                      );
                    })}
                  </div>
                )}

                {/* 3. True / False */}
                {currentQ.question_type === "true_false" && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {currentQ.options.map((opt) => {
                      const isSelected = answers[currentQ.assessment_question_id]?.selected_option_id === opt.option_id;
                      const isTrue = opt.option_text.toLowerCase() === "true";
                      return (
                        <button
                          key={opt.option_id}
                          type="button"
                          onClick={() => handleSelectSingleOption(currentQ.assessment_question_id, opt.option_id!)}
                          disabled={isExpired}
                          className={`p-6 rounded-2xl border font-bold text-base transition-all flex items-center justify-center gap-3 ${
                            isSelected
                              ? isTrue
                                ? "border-emerald-500 bg-emerald-500/15 text-emerald-600 shadow-sm"
                                : "border-red-500 bg-red-500/15 text-red-600 shadow-sm"
                              : "border-[var(--outline-variant)] bg-[var(--surface-container-low)] hover:border-[var(--primary)] text-[var(--on-surface)]"
                          } disabled:opacity-50 disabled:cursor-not-allowed`}
                        >
                          <span className="material-symbols-outlined text-[24px]">
                            {isTrue ? "check_circle" : "cancel"}
                          </span>
                          {opt.option_text}
                        </button>
                      );
                    })}
                  </div>
                )}

                {/* 4. Short Answer */}
                {currentQ.question_type === "short_answer" && (
                  <div className="space-y-2">
                    <Textarea
                      rows={4}
                      value={answers[currentQ.assessment_question_id]?.text_answer || ""}
                      onChange={(e) => handleTextAnswerChange(currentQ.assessment_question_id, e.target.value)}
                      placeholder="Type your answer here..."
                      disabled={isExpired}
                      className="bg-[var(--surface-container-low)] border-[var(--outline-variant)] rounded-2xl p-4 text-sm leading-relaxed disabled:opacity-50"
                    />
                    <div className="flex justify-between text-xs text-[var(--on-surface-variant)]">
                      <span>Responses are automatically saved</span>
                      <span>{(answers[currentQ.assessment_question_id]?.text_answer || "").length} characters</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Navigation Footer */}
              <div className="pt-6 border-t border-[var(--outline-variant)] flex items-center justify-between gap-4">
                <Button
                  variant="outline"
                  disabled={currentIndex === 0}
                  onClick={() => setCurrentIndex((prev) => Math.max(0, prev - 1))}
                  className="rounded-xl px-5 font-semibold"
                >
                  <span className="material-symbols-outlined mr-1.5 text-[18px]">chevron_left</span>
                  Previous
                </Button>

                {currentIndex < questions.length - 1 ? (
                  <Button
                    onClick={() => setCurrentIndex((prev) => Math.min(questions.length - 1, prev + 1))}
                    style={{ backgroundColor: "var(--primary)", color: "var(--on-primary)" }}
                    className="rounded-xl px-6 font-semibold shadow-sm"
                  >
                    Next Question
                    <span className="material-symbols-outlined ml-1.5 text-[18px]">chevron_right</span>
                  </Button>
                ) : (
                  <Button
                    onClick={() => setIsSubmitModalOpen(true)}
                    className="bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl px-6 font-semibold shadow-sm"
                  >
                    Review & Submit
                    <span className="material-symbols-outlined ml-1.5 text-[18px]">send</span>
                  </Button>
                )}
              </div>
            </div>
          ) : (
            <div className="text-center py-12 bg-[var(--surface-container-low)] rounded-3xl border border-[var(--outline-variant)]">
              <p className="text-sm text-[var(--on-surface-variant)]">No question selected.</p>
            </div>
          )}
        </div>

        {/* Right: Question Navigator */}
        <div className="lg:col-span-1 space-y-4">
          <div className="bg-[var(--surface-container-lowest)] border border-[var(--outline-variant)] rounded-3xl p-5 shadow-sm space-y-5">
            <h3 className="text-sm font-bold text-[var(--on-surface)] flex items-center gap-2">
              <span className="material-symbols-outlined text-[18px] text-[var(--primary)]">grid_view</span>
              Question Navigator
            </h3>

            {/* Timer in sidebar (compact) */}
            {remainingSeconds !== null && (
              <div
                className={`flex items-center justify-between px-3 py-2 rounded-xl border text-xs font-bold font-mono ${
                  timerIsCritical
                    ? "bg-red-500/15 text-red-600 border-red-500/30 animate-pulse"
                    : timerIsWarning
                    ? "bg-amber-500/15 text-amber-600 border-amber-500/30"
                    : "bg-[var(--surface-container-low)] text-[var(--on-surface)] border-[var(--outline-variant)]"
                }`}
              >
                <span className="flex items-center gap-1">
                  <span className="material-symbols-outlined text-[14px]">
                    {timerIsCritical ? "timer_off" : "timer"}
                  </span>
                  Time Left
                </span>
                <span>{formatCountdown(remainingSeconds)}</span>
              </div>
            )}

            {/* Questions Grid */}
            <div className="grid grid-cols-5 gap-2">
              {questions.map((q, idx) => {
                const isCurrent = idx === currentIndex;
                const isAnswered = isQuestionAnswered(q.assessment_question_id);

                let btnClass = "border-[var(--outline-variant)] bg-[var(--surface-container-low)] text-[var(--on-surface)] hover:bg-[var(--surface-container-high)]";
                if (isAnswered) {
                  btnClass = "border-emerald-500/40 bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 font-bold";
                }
                if (isCurrent) {
                  btnClass = "border-[var(--primary)] bg-[var(--primary)] text-[var(--on-primary)] font-bold shadow-md ring-2 ring-[var(--primary)]/30";
                }

                return (
                  <button
                    key={q.assessment_question_id}
                    type="button"
                    onClick={() => setCurrentIndex(idx)}
                    className={`h-10 rounded-xl border text-xs font-semibold flex items-center justify-center transition-all ${btnClass}`}
                  >
                    {idx + 1}
                  </button>
                );
              })}
            </div>

            {/* Legend */}
            <div className="space-y-2 pt-3 border-t border-[var(--outline-variant)] text-xs text-[var(--on-surface-variant)]">
              <div className="flex items-center gap-2">
                <div className="w-3.5 h-3.5 rounded-md bg-[var(--primary)]" />
                <span>Current Question</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3.5 h-3.5 rounded-md bg-emerald-500/20 border border-emerald-500/40" />
                <span>Answered ({answeredCount})</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3.5 h-3.5 rounded-md bg-[var(--surface-container-low)] border border-[var(--outline-variant)]" />
                <span>Unanswered ({unansweredCount})</span>
              </div>
            </div>

            {/* Submit Button */}
            <div className="pt-2">
              <Button
                onClick={() => setIsSubmitModalOpen(true)}
                className="w-full bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl py-5 font-semibold shadow-sm flex items-center justify-center gap-2"
              >
                <span className="material-symbols-outlined text-[18px]">send</span>
                Submit Exam
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* ── SUBMIT CONFIRMATION DIALOG ─────────────────────────── */}
      <Dialog open={isSubmitModalOpen} onOpenChange={setIsSubmitModalOpen}>
        <DialogContent className="max-w-md rounded-3xl bg-white dark:bg-[#1b211e] border-[var(--outline-variant)] p-6 shadow-2xl">
          <DialogHeader>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-emerald-500/10 text-emerald-600 flex items-center justify-center flex-shrink-0">
                <span className="material-symbols-outlined text-[24px]">send</span>
              </div>
              <div>
                <DialogTitle className="text-base font-bold text-[var(--on-surface)]">
                  Submit Assessment Attempt #{attempt.attempt_number}?
                </DialogTitle>
                <DialogDescription className="text-xs text-[var(--on-surface-variant)]">
                  Once submitted, you will not be able to modify your answers for this attempt.
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          {submitError && (
            <div className="p-3 bg-red-500/10 text-red-600 dark:text-red-400 text-xs border border-red-500/20 rounded-xl">
              {submitError}
            </div>
          )}

          <div className="space-y-3 bg-[var(--surface-container-low)] p-4 rounded-2xl text-xs border border-[var(--outline-variant)]">
            <div className="flex items-center justify-between">
              <span className="text-[var(--on-surface-variant)]">Total Questions:</span>
              <span className="font-bold text-[var(--on-surface)]">{questions.length}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[var(--on-surface-variant)]">Answered:</span>
              <span className="font-bold text-emerald-600">{answeredCount}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[var(--on-surface-variant)]">Unanswered:</span>
              <span className={`font-bold ${unansweredCount > 0 ? "text-amber-500" : "text-[var(--on-surface)]"}`}>
                {unansweredCount}
              </span>
            </div>
            {/* Show remaining time in modal if timed */}
            {remainingSeconds !== null && (
              <div className={`flex items-center justify-between pt-2 border-t border-[var(--outline-variant)] ${timerIsCritical ? "text-red-600" : timerIsWarning ? "text-amber-600" : "text-[var(--on-surface-variant)]"}`}>
                <span>Time Remaining:</span>
                <span className="font-bold font-mono">{formatCountdown(remainingSeconds)}</span>
              </div>
            )}
            {unansweredCount > 0 && (
              <div className="pt-2 border-t border-[var(--outline-variant)] text-amber-600 dark:text-amber-400 flex items-center gap-1.5 font-medium">
                <span className="material-symbols-outlined text-[16px]">warning</span>
                You have {unansweredCount} unanswered question{unansweredCount > 1 ? "s" : ""}.
              </div>
            )}
          </div>

          <DialogFooter className="pt-2 flex gap-2">
            <Button variant="outline" size="sm" onClick={() => setIsSubmitModalOpen(false)}>
              Keep Working
            </Button>
            <Button
              size="sm"
              disabled={submitting}
              onClick={handleSubmitAttempt}
              className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold"
            >
              {submitting && <div className="w-3.5 h-3.5 border-2 border-t-transparent border-white rounded-full animate-spin mr-1.5" />}
              Confirm & Submit
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
