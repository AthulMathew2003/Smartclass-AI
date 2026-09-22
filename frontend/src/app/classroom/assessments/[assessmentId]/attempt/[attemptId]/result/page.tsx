"use client";

import React, { useEffect, useState, use } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AssessmentResult,
  AssessmentResultQuestion,
  fetchAttemptResult,
  gradeAssessmentQuestion,
  ManualGradeInput,
} from "@/lib/assessments";
import { usePermissions } from "@/lib/permissions";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

export default function AssessmentAttemptResultPage({
  params,
}: {
  params: Promise<{ assessmentId: string; attemptId: string }>;
}) {
  const resolvedParams = use(params);
  const { assessmentId, attemptId } = resolvedParams;
  const router = useRouter();
  const searchParams = useSearchParams();
  const { hasPermission } = usePermissions();

  const canGrade =
    hasPermission("assessment.update") ||
    hasPermission("assessment.grade") ||
    hasPermission("assessment.publish");

  const [result, setResult] = useState<AssessmentResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Manual grading state for teachers
  const [gradingDrafts, setGradingDrafts] = useState<
    Record<string, { marks: string; feedback: string; saving?: boolean; error?: string }>
  >({});

  const loadResult = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchAttemptResult(assessmentId, attemptId);
      setResult(data);

      // Initialize grading drafts for pending/graded questions
      const drafts: Record<string, { marks: string; feedback: string }> = {};
      data.questions.forEach((q) => {
        drafts[q.assessment_question_id] = {
          marks: String(q.marks_awarded ?? "0"),
          feedback: q.feedback || "",
        };
      });
      setGradingDrafts(drafts);
    } catch (err: any) {
      setError(err.message || "Failed to load assessment result.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadResult();
  }, [assessmentId, attemptId]);

  const handleSaveGrade = async (questionId: string, marksAvailable: number | string) => {
    const draft = gradingDrafts[questionId];
    if (!draft) return;

    const numMarks = parseFloat(draft.marks);
    const maxMarks = parseFloat(String(marksAvailable));

    if (isNaN(numMarks) || numMarks < 0) {
      setGradingDrafts((prev) => ({
        ...prev,
        [questionId]: { ...prev[questionId], error: "Please enter a valid non-negative mark." },
      }));
      return;
    }

    if (numMarks > maxMarks) {
      setGradingDrafts((prev) => ({
        ...prev,
        [questionId]: { ...prev[questionId], error: `Mark cannot exceed ${maxMarks}.` },
      }));
      return;
    }

    setGradingDrafts((prev) => ({
      ...prev,
      [questionId]: { ...prev[questionId], saving: true, error: undefined },
    }));

    try {
      const updated = await gradeAssessmentQuestion(assessmentId, attemptId, questionId, {
        marks_awarded: numMarks,
        feedback: draft.feedback.trim() || undefined,
      });
      setResult(updated);
      setGradingDrafts((prev) => ({
        ...prev,
        [questionId]: {
          marks: String(numMarks),
          feedback: draft.feedback,
          saving: false,
          error: undefined,
        },
      }));
    } catch (err: any) {
      setGradingDrafts((prev) => ({
        ...prev,
        [questionId]: { ...prev[questionId], saving: false, error: err.message || "Failed to save grade." },
      }));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex items-center gap-3 text-sm font-semibold text-[var(--on-surface-variant)]">
          <div className="w-6 h-6 border-2 border-t-transparent border-[var(--primary)] rounded-full animate-spin" />
          Loading assessment evaluation...
        </div>
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className="p-8 text-center max-w-lg mx-auto space-y-4">
        <span className="material-symbols-outlined text-[48px] text-red-500 block">error</span>
        <h2 className="text-xl font-bold text-[var(--on-surface)]">Result Unavailable</h2>
        <p className="text-sm text-[var(--on-surface-variant)]">{error || "Unable to load evaluation result."}</p>
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

  const isPending = result.status === "pending_manual_grading" || result.pending_count > 0;
  const isPassed = result.passed === true;

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-16 animate-in fade-in duration-300">
      {/* ── Top Navigation ── */}
      <div>
        <button
          onClick={() => router.push(`/classroom/assessments/${assessmentId}`)}
          className="text-sm font-medium text-[var(--primary)] hover:underline inline-flex items-center gap-1 transition-colors mb-2"
        >
          <span className="material-symbols-outlined text-[16px]">arrow_back</span>
          Back to Assessment Overview
        </button>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[var(--on-surface)]">
              {result.assessment_title || "Assessment Result"}
            </h1>
            <p className="text-xs sm:text-sm text-[var(--on-surface-variant)] mt-1">
              Attempt #{result.attempt_number} • Submitted{" "}
              {result.attempt_submitted_at
                ? new Date(result.attempt_submitted_at).toLocaleString()
                : "Recently"}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {isPending ? (
              <Badge variant="outline" className="bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20 px-3 py-1 text-xs font-bold">
                Pending Manual Grading
              </Badge>
            ) : isPassed ? (
              <Badge variant="outline" className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 px-3 py-1 text-xs font-bold">
                Passed
              </Badge>
            ) : (
              <Badge variant="outline" className="bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20 px-3 py-1 text-xs font-bold">
                Needs Improvement
              </Badge>
            )}
          </div>
        </div>
      </div>

      {/* ── Hero Score Summary Card ── */}
      <div className="bg-[var(--surface-container-lowest)] border border-[var(--outline-variant)] rounded-3xl p-6 sm:p-8 shadow-sm space-y-6">
        {isPending && (
          <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-2xl flex items-start gap-3 text-xs sm:text-sm text-amber-700 dark:text-amber-400">
            <span className="material-symbols-outlined text-[20px] text-amber-500 flex-shrink-0 mt-0.5">
              pending_actions
            </span>
            <div>
              <span className="font-bold block">Short-Answer Response(s) Pending Teacher Review</span>
              Your provisional score is shown below. Final marks and pass/fail determination will be finalized once your teacher completes manual grading.
            </div>
          </div>
        )}

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
          <div>
            <span className="text-xs uppercase tracking-wider font-bold text-[var(--on-surface-variant)]">
              Total Score Obtained
            </span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-4xl sm:text-5xl font-black text-[var(--on-surface)]">
                {parseFloat(String(result.obtained_marks)).toFixed(2)}
              </span>
              <span className="text-xl sm:text-2xl font-bold text-[var(--on-surface-variant)]">
                / {parseFloat(String(result.total_marks)).toFixed(2)}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="text-right">
              <span className="text-xs uppercase tracking-wider font-bold text-[var(--on-surface-variant)] block">
                Percentage
              </span>
              <span className="text-2xl sm:text-3xl font-black text-[var(--primary)] mt-0.5 block">
                {parseFloat(String(result.percentage)).toFixed(1)}%
              </span>
            </div>
          </div>
        </div>

        {/* Breakdown Metric Chips */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-4 border-t border-[var(--outline-variant)]">
          <div className="bg-[var(--surface-container-low)] p-3.5 rounded-2xl border border-[var(--outline-variant)] flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-emerald-500/10 text-emerald-600 flex items-center justify-center font-bold text-sm">
              ✓
            </div>
            <div>
              <div className="text-[11px] text-[var(--on-surface-variant)] font-medium">Correct</div>
              <div className="text-base font-bold text-emerald-600">{result.correct_count}</div>
            </div>
          </div>

          <div className="bg-[var(--surface-container-low)] p-3.5 rounded-2xl border border-[var(--outline-variant)] flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-red-500/10 text-red-600 flex items-center justify-center font-bold text-sm">
              ✕
            </div>
            <div>
              <div className="text-[11px] text-[var(--on-surface-variant)] font-medium">Incorrect</div>
              <div className="text-base font-bold text-red-600">{result.incorrect_count}</div>
            </div>
          </div>

          <div className="bg-[var(--surface-container-low)] p-3.5 rounded-2xl border border-[var(--outline-variant)] flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-slate-500/10 text-slate-600 dark:text-slate-400 flex items-center justify-center font-bold text-sm">
              —
            </div>
            <div>
              <div className="text-[11px] text-[var(--on-surface-variant)] font-medium">Unanswered</div>
              <div className="text-base font-bold text-[var(--on-surface)]">{result.unanswered_count}</div>
            </div>
          </div>

          <div className="bg-[var(--surface-container-low)] p-3.5 rounded-2xl border border-[var(--outline-variant)] flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-amber-500/10 text-amber-600 flex items-center justify-center font-bold text-sm">
              ⏳
            </div>
            <div>
              <div className="text-[11px] text-[var(--on-surface-variant)] font-medium">Pending Review</div>
              <div className="text-base font-bold text-amber-600">{result.pending_count}</div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Question by Question Review ── */}
      <div className="space-y-6">
        <h2 className="text-lg sm:text-xl font-bold text-[var(--on-surface)] flex items-center gap-2">
          <span className="material-symbols-outlined text-[22px] text-[var(--primary)]">checklist</span>
          Question-by-Question Review ({result.questions.length})
        </h2>

        <div className="space-y-4">
          {result.questions.map((q, idx) => {
            const isQCorrect = q.correctness === "correct";
            const isQIncorrect = q.correctness === "incorrect";
            const isQUnanswered = q.correctness === "unanswered";
            const isQPending = q.grading_status === "pending" || q.correctness === "pending";

            const studentSelectedOptId = q.answer_value?.selected_option_id;
            const studentSelectedOptIds = q.answer_value?.selected_option_ids || [];
            const studentText = q.answer_value?.text_answer;

            return (
              <div
                key={q.result_question_id || q.assessment_question_id}
                className={`bg-[var(--surface-container-lowest)] border rounded-3xl p-6 shadow-sm space-y-4 transition-all ${
                  isQCorrect
                    ? "border-emerald-500/30"
                    : isQIncorrect
                    ? "border-red-500/30"
                    : isQPending
                    ? "border-amber-500/30"
                    : "border-[var(--outline-variant)]"
                }`}
              >
                {/* Question Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-[var(--outline-variant)]">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-bold px-2.5 py-1 rounded-lg bg-[var(--surface-container-high)] text-[var(--on-surface)]">
                      Question {idx + 1}
                    </span>
                    <span className="text-xs font-medium px-2.5 py-1 rounded-lg bg-blue-500/10 text-blue-600 capitalize">
                      {q.question_type.replace("_", " ")}
                    </span>
                    {isQCorrect && (
                      <Badge className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 text-xs font-semibold">
                        Correct (+{parseFloat(String(q.marks_awarded)).toFixed(2)})
                      </Badge>
                    )}
                    {isQIncorrect && (
                      <Badge className="bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20 text-xs font-semibold">
                        Incorrect (0.00)
                      </Badge>
                    )}
                    {isQUnanswered && (
                      <Badge className="bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20 text-xs font-semibold">
                        Unanswered (0.00)
                      </Badge>
                    )}
                    {isQPending && (
                      <Badge className="bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20 text-xs font-semibold">
                        Pending Manual Grading
                      </Badge>
                    )}
                  </div>

                  <div className="text-xs font-semibold text-[var(--on-surface-variant)]">
                    Marks: <span className="text-[var(--on-surface)] font-bold">{parseFloat(String(q.marks_awarded)).toFixed(2)}</span> / {parseFloat(String(q.marks_available)).toFixed(2)}
                  </div>
                </div>

                {/* Question Text */}
                <div className="text-sm font-semibold text-[var(--on-surface)] whitespace-pre-wrap">
                  {q.question_text}
                </div>

                {/* Question Options Review (For MCQ and True/False) */}
                {(q.question_type === "mcq_single" || q.question_type === "true_false" || q.question_type === "mcq_multiple") && (
                  <div className="space-y-2 pt-1">
                    {q.options.map((opt) => {
                      const optIdStr = String(opt.option_id || "");
                      const isSelected =
                        studentSelectedOptId === optIdStr || studentSelectedOptIds.includes(optIdStr);
                      const isCorrectAnswer = opt.option_is_correct === true || opt.is_correct === true;

                      let rowClass = "bg-[var(--surface-container-low)] border-[var(--outline-variant)] text-[var(--on-surface)]";
                      if (isSelected && isCorrectAnswer) {
                        rowClass = "bg-emerald-500/10 border-emerald-500/40 text-emerald-800 dark:text-emerald-300 font-semibold";
                      } else if (isSelected && !isCorrectAnswer) {
                        rowClass = "bg-red-500/10 border-red-500/40 text-red-800 dark:text-red-300 font-semibold";
                      } else if (isCorrectAnswer) {
                        rowClass = "bg-emerald-500/5 border-dashed border-emerald-500/30 text-emerald-700 dark:text-emerald-400";
                      }

                      return (
                        <div
                          key={opt.option_id || opt.option_order}
                          className={`p-3 rounded-2xl border text-xs sm:text-sm flex items-center justify-between gap-3 ${rowClass}`}
                        >
                          <div className="flex items-center gap-3">
                            <span className="w-6 h-6 rounded-lg bg-[var(--surface-container-high)] flex items-center justify-center font-bold text-xs">
                              {String.fromCharCode(64 + opt.option_order)}
                            </span>
                            <span>{opt.option_text}</span>
                          </div>

                          <div className="flex items-center gap-2 flex-shrink-0">
                            {isSelected && (
                              <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-[var(--surface-container-high)]">
                                Your Choice
                              </span>
                            )}
                            {isCorrectAnswer && (
                              <span className="text-[11px] font-bold text-emerald-600 flex items-center gap-1">
                                <span className="material-symbols-outlined text-[14px]">check</span> Correct
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Short Answer Review */}
                {q.question_type === "short_answer" && (
                  <div className="space-y-3 pt-1">
                    <div className="bg-[var(--surface-container-low)] border border-[var(--outline-variant)] p-4 rounded-2xl">
                      <span className="text-xs text-[var(--on-surface-variant)] font-medium block mb-1">
                        Student Written Response:
                      </span>
                      {studentText ? (
                        <p className="text-xs sm:text-sm text-[var(--on-surface)] whitespace-pre-wrap">
                          {studentText}
                        </p>
                      ) : (
                        <span className="text-xs text-slate-400 italic">No response submitted.</span>
                      )}
                    </div>

                    {/* Teacher Feedback if already graded */}
                    {q.feedback && (
                      <div className="bg-blue-500/10 border border-blue-500/20 p-4 rounded-2xl text-xs sm:text-sm">
                        <span className="font-bold text-blue-700 dark:text-blue-300 block mb-1 flex items-center gap-1">
                          <span className="material-symbols-outlined text-[16px]">comment</span> Teacher Feedback:
                        </span>
                        <p className="text-[var(--on-surface)] whitespace-pre-wrap">{q.feedback}</p>
                      </div>
                    )}

                    {/* Teacher Manual Grading Action Drawer / Box */}
                    {canGrade && (
                      <div className="bg-[var(--surface-container-low)] border border-[var(--outline-variant)] p-4 rounded-2xl space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-[var(--on-surface)] flex items-center gap-1.5">
                            <span className="material-symbols-outlined text-[16px] text-[var(--primary)]">edit_note</span>
                            {q.grading_status === "graded" ? "Update Grade / Regrade" : "Enter Manual Grade"}
                          </span>
                          <span className="text-xs text-[var(--on-surface-variant)]">
                            Max: {parseFloat(String(q.marks_available)).toFixed(2)} pts
                          </span>
                        </div>

                        {gradingDrafts[q.assessment_question_id]?.error && (
                          <div className="p-2 bg-red-500/10 text-red-600 text-xs rounded-xl border border-red-500/20">
                            {gradingDrafts[q.assessment_question_id].error}
                          </div>
                        )}

                        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                          <div className="sm:col-span-1">
                            <label className="text-[11px] font-semibold text-[var(--on-surface-variant)] block mb-1">
                              Marks Awarded
                            </label>
                            <Input
                              type="number"
                              step="0.25"
                              min="0"
                              max={parseFloat(String(q.marks_available))}
                              value={gradingDrafts[q.assessment_question_id]?.marks ?? ""}
                              onChange={(e) =>
                                setGradingDrafts((prev) => ({
                                  ...prev,
                                  [q.assessment_question_id]: {
                                    ...prev[q.assessment_question_id],
                                    marks: e.target.value,
                                  },
                                }))
                              }
                              className="bg-[var(--surface-container-lowest)] h-9 text-sm"
                            />
                          </div>

                          <div className="sm:col-span-3">
                            <label className="text-[11px] font-semibold text-[var(--on-surface-variant)] block mb-1">
                              Feedback / Notes (Optional)
                            </label>
                            <Textarea
                              rows={1}
                              placeholder="Add comments for the student..."
                              value={gradingDrafts[q.assessment_question_id]?.feedback ?? ""}
                              onChange={(e) =>
                                setGradingDrafts((prev) => ({
                                  ...prev,
                                  [q.assessment_question_id]: {
                                    ...prev[q.assessment_question_id],
                                    feedback: e.target.value,
                                  },
                                }))
                              }
                              className="bg-[var(--surface-container-lowest)] text-xs min-h-[36px] resize-y"
                            />
                          </div>
                        </div>

                        <div className="flex justify-end">
                          <Button
                            size="sm"
                            disabled={gradingDrafts[q.assessment_question_id]?.saving}
                            onClick={() => handleSaveGrade(q.assessment_question_id, q.marks_available)}
                            style={{ backgroundColor: "var(--primary)", color: "var(--on-primary)" }}
                            className="font-semibold text-xs rounded-xl shadow-sm"
                          >
                            {gradingDrafts[q.assessment_question_id]?.saving && (
                              <div className="w-3.5 h-3.5 border-2 border-t-transparent border-white rounded-full animate-spin mr-1.5" />
                            )}
                            Save Grade
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Explanation */}
                {q.question_explanation && (
                  <div className="p-3 bg-[var(--surface-container-low)] rounded-xl text-xs text-[var(--on-surface-variant)] border border-[var(--outline-variant)]">
                    <span className="font-bold text-[var(--on-surface)] block mb-0.5">Explanation:</span>
                    {q.question_explanation}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
