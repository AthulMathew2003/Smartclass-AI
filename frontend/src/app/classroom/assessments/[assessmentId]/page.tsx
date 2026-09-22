"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  fetchAssessment,
  fetchAssessmentQuestions,
  updateAssessment,
  publishAssessment,
  closeAssessment,
  archiveAssessment,
  addQuestionToAssessment,
  createAndAddQuestionToAssessment,
  updateAssessmentQuestion,
  removeAssessmentQuestion,
  reorderAssessmentQuestions,
  fetchSubjectQuestions,
  Assessment,
  AssessmentQuestion,
  QuestionBankItem,
  QuestionType,
  QuestionOptionCreateInput
} from "@/lib/assessments";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { usePermissions } from "@/lib/permissions";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

export default function AssessmentBuilderPage() {
  const params = useParams();
  const router = useRouter();
  const assessmentId = params.assessmentId as string;
  const { hasPermission, isLoaded: permLoaded } = usePermissions();

  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [questions, setQuestions] = useState<AssessmentQuestion[]>([]);
  const [subjectQuestions, setSubjectQuestions] = useState<QuestionBankItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>("builder");

  const canManage = hasPermission("assessment.update") || hasPermission("assessment.publish") || hasPermission("question.create");

  // Question Bank Picker Modal
  const [isPickerOpen, setIsPickerOpen] = useState(false);
  const [pickerSearch, setPickerSearch] = useState("");
  const [pickerType, setPickerType] = useState<string>("all");
  const [selectedBankIds, setSelectedBankIds] = useState<string[]>([]);
  const [addingFromBank, setAddingFromBank] = useState(false);

  // Inline Question Creator Modal
  const [isInlineCreateOpen, setIsInlineCreateOpen] = useState(false);
  const [inlineType, setInlineType] = useState<QuestionType>("mcq_single");
  const [inlineText, setInlineText] = useState("");
  const [inlineMarks, setInlineMarks] = useState("5.00");
  const [inlineExplanation, setInlineExplanation] = useState("");
  const [inlineOptions, setInlineOptions] = useState<QuestionOptionCreateInput[]>([
    { option_text: "", option_order: 1, is_correct: true },
    { option_text: "", option_order: 2, is_correct: false },
    { option_text: "", option_order: 3, is_correct: false },
    { option_text: "", option_order: 4, is_correct: false },
  ]);
  const [inlineSaving, setInlineSaving] = useState(false);
  const [inlineError, setInlineError] = useState<string | null>(null);

  // Settings Tab State
  const [settingsTitle, setSettingsTitle] = useState("");
  const [settingsDescription, setSettingsDescription] = useState("");
  const [settingsDuration, setSettingsDuration] = useState("");
  const [settingsPassingMarks, setSettingsPassingMarks] = useState("");
  const [settingsAttemptLimit, setSettingsAttemptLimit] = useState(1);
  const [settingsRandomize, setSettingsRandomize] = useState(false);
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [settingsSuccess, setSettingsSuccess] = useState(false);

  // Publish Dialog State
  const [isPublishModalOpen, setIsPublishModalOpen] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [publishError, setPublishError] = useState<string | null>(null);

  useEffect(() => {
    if (permLoaded) {
      loadAssessmentData();
    }
  }, [assessmentId, permLoaded]);

  async function loadAssessmentData() {
    try {
      setLoading(true);
      setError(null);
      const [asm, qList] = await Promise.all([
        fetchAssessment(assessmentId),
        fetchAssessmentQuestions(assessmentId)
      ]);
      setAssessment(asm);
      setQuestions(qList);

      // Populate settings form
      setSettingsTitle(asm.assessment_title);
      setSettingsDescription(asm.assessment_description || "");
      setSettingsDuration(asm.assessment_duration_minutes ? String(asm.assessment_duration_minutes) : "");
      setSettingsPassingMarks(asm.assessment_passing_marks ? String(asm.assessment_passing_marks) : "");
      setSettingsAttemptLimit(asm.assessment_attempt_limit || 1);
      setSettingsRandomize(asm.assessment_randomize_questions || false);

      // Load Subject Question Bank only for teachers/admins
      if (asm.assessment_subject_id && canManage) {
        try {
          const bank = await fetchSubjectQuestions(asm.assessment_subject_id);
          setSubjectQuestions(bank);
        } catch {
          // Handled gracefully for students / non-teachers
        }
      }
    } catch (err: any) {
      setError(err.message || "Failed to load assessment details.");
    } finally {
      setLoading(false);
    }
  }

  // ── Question Bank Picker Actions ─────────────────────────────

  async function handleAddSelectedFromBank() {
    if (selectedBankIds.length === 0) return;
    try {
      setAddingFromBank(true);
      for (const qid of selectedBankIds) {
        const bankItem = subjectQuestions.find((sq) => sq.question_id === qid);
        const marks = bankItem ? Number(bankItem.question_default_marks) : 1;
        await addQuestionToAssessment(assessmentId, qid, marks);
      }
      await loadAssessmentData();
      setIsPickerOpen(false);
      setSelectedBankIds([]);
    } catch (err: any) {
      alert(err.message || "Failed to add questions from bank.");
    } finally {
      setAddingFromBank(false);
    }
  }

  function toggleSelectBankId(id: string) {
    setSelectedBankIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  }

  // ── Inline Question Creation ─────────────────────────────────

  function handleOpenInlineCreate() {
    setInlineType("mcq_single");
    setInlineText("");
    setInlineMarks("5.00");
    setInlineExplanation("");
    setInlineOptions([
      { option_text: "", option_order: 1, is_correct: true },
      { option_text: "", option_order: 2, is_correct: false },
      { option_text: "", option_order: 3, is_correct: false },
      { option_text: "", option_order: 4, is_correct: false },
    ]);
    setInlineError(null);
    setIsInlineCreateOpen(true);
  }

  async function handleSaveInlineQuestion(e: React.FormEvent) {
    e.preventDefault();
    setInlineError(null);

    const trimmedText = inlineText.trim();
    if (!trimmedText) {
      setInlineError("Question text is required.");
      return;
    }

    const marksNum = parseFloat(inlineMarks);
    if (isNaN(marksNum) || marksNum <= 0) {
      setInlineError("Marks must be a positive number.");
      return;
    }

    if (inlineType === "mcq_single" || inlineType === "mcq_multiple") {
      const validOptions = inlineOptions.filter((o) => o.option_text.trim());
      if (validOptions.length < 2) {
        setInlineError("Choice questions must have at least 2 options.");
        return;
      }
      const correctCount = validOptions.filter((o) => o.is_correct).length;
      if (inlineType === "mcq_single" && correctCount !== 1) {
        setInlineError("Single choice questions must have exactly 1 correct option.");
        return;
      }
      if (inlineType === "mcq_multiple" && correctCount < 1) {
        setInlineError("Multiple choice questions must have at least 1 correct option.");
        return;
      }
    }

    const cleanedOptions = inlineType === "short_answer"
      ? []
      : inlineOptions.map((o, idx) => ({
          option_text: o.option_text.trim(),
          option_order: idx + 1,
          is_correct: o.is_correct || false,
        }));

    try {
      setInlineSaving(true);
      await createAndAddQuestionToAssessment(assessmentId, {
        question_type: inlineType,
        question_text: trimmedText,
        marks: marksNum,
        question_explanation: inlineExplanation.trim() || null,
        options: cleanedOptions,
      });
      await loadAssessmentData();
      setIsInlineCreateOpen(false);
    } catch (err: any) {
      setInlineError(err.message || "Failed to create question.");
    } finally {
      setInlineSaving(false);
    }
  }

  // ── Reorder Questions ────────────────────────────────────────

  async function handleMoveQuestion(index: number, direction: "up" | "down") {
    if (direction === "up" && index === 0) return;
    if (direction === "down" && index === questions.length - 1) return;

    const targetIndex = direction === "up" ? index - 1 : index + 1;
    const reordered = [...questions];
    const temp = reordered[index];
    reordered[index] = reordered[targetIndex];
    reordered[targetIndex] = temp;

    const newIds = reordered.map((q) => q.assessment_question_id);
    try {
      const updated = await reorderAssessmentQuestions(assessmentId, newIds);
      setQuestions(updated);
    } catch (err: any) {
      alert(err.message || "Failed to reorder questions.");
    }
  }

  async function handleUpdateMarks(aqId: string, newMarks: number) {
    if (isNaN(newMarks) || newMarks <= 0) return;
    try {
      await updateAssessmentQuestion(assessmentId, aqId, { marks: newMarks });
      await loadAssessmentData();
    } catch (err: any) {
      alert(err.message || "Failed to update question marks.");
    }
  }

  async function handleRemoveQuestion(aqId: string) {
    if (!confirm("Remove this question from the assessment? (It will remain in your Question Bank).")) return;
    try {
      await removeAssessmentQuestion(assessmentId, aqId);
      await loadAssessmentData();
    } catch (err: any) {
      alert(err.message || "Failed to remove question.");
    }
  }

  // ── Settings Save ────────────────────────────────────────────

  async function handleSaveSettings(e: React.FormEvent) {
    e.preventDefault();
    setSettingsSaving(true);
    setSettingsSuccess(false);
    try {
      const durationVal = settingsDuration ? parseInt(settingsDuration) : null;
      const passingMarksVal = settingsPassingMarks ? parseFloat(settingsPassingMarks) : null;

      const updated = await updateAssessment(assessmentId, {
        title: settingsTitle.trim(),
        description: settingsDescription.trim() || null,
        duration_minutes: durationVal,
        passing_marks: passingMarksVal,
        attempt_limit: settingsAttemptLimit,
        randomize_questions: settingsRandomize,
      });
      setAssessment(updated);
      setSettingsSuccess(true);
      setTimeout(() => setSettingsSuccess(false), 3000);
    } catch (err: any) {
      alert(err.message || "Failed to update assessment settings.");
    } finally {
      setSettingsSaving(false);
    }
  }

  // ── Publish / Close / Archive ────────────────────────────────

  async function handleConfirmPublish() {
    setPublishing(true);
    setPublishError(null);
    try {
      const pub = await publishAssessment(assessmentId);
      setAssessment(pub);
      setIsPublishModalOpen(false);
      await loadAssessmentData();
    } catch (err: any) {
      setPublishError(err.message || "Failed to publish assessment.");
    } finally {
      setPublishing(false);
    }
  }

  async function handleCloseAssessment() {
    if (!confirm("Close this assessment? Students will no longer be able to start new attempts.")) return;
    try {
      const closed = await closeAssessment(assessmentId);
      setAssessment(closed);
    } catch (err: any) {
      alert(err.message || "Failed to close assessment.");
    }
  }

  async function handleArchiveAssessment() {
    if (!confirm("Archive this assessment? It will be hidden from students and archived.")) return;
    try {
      const arch = await archiveAssessment(assessmentId);
      setAssessment(arch);
    } catch (err: any) {
      alert(err.message || "Failed to archive assessment.");
    }
  }

  const isDraft = assessment?.assessment_status === "draft";
  const isPublished = assessment?.assessment_status === "published" || assessment?.assessment_status === "active";

  const totalCalculatedMarks = questions.reduce(
    (acc, q) => acc + Number(q.assessment_question_marks || 0),
    0
  );

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "draft":
        return <Badge variant="outline" className="bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20">Draft</Badge>;
      case "published":
        return <Badge variant="outline" className="bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20">Published</Badge>;
      case "active":
        return <Badge variant="outline" className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20">Active</Badge>;
      case "closed":
        return <Badge variant="outline" className="bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/20">Closed</Badge>;
      case "archived":
        return <Badge variant="outline" className="bg-zinc-500/10 text-zinc-500 border-zinc-500/20">Archived</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const getTypeBadge = (type: string) => {
    switch (type) {
      case "exam":
        return <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-lg bg-purple-500/10 text-purple-600 dark:text-purple-400"><span className="material-symbols-outlined text-[15px]">school</span>Exam</span>;
      case "quiz":
        return <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-lg bg-sky-500/10 text-sky-600 dark:text-sky-400"><span className="material-symbols-outlined text-[15px]">timer</span>Quiz</span>;
      case "practice":
        return <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"><span className="material-symbols-outlined text-[15px]">psychology</span>Practice</span>;
      default:
        return <span className="text-xs font-semibold uppercase">{type}</span>;
    }
  };

  const getQuestionTypeBadge = (type: string) => {
    switch (type) {
      case "mcq_single":
        return <span className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded bg-blue-500/10 text-blue-600 dark:text-blue-400">Single Choice</span>;
      case "mcq_multiple":
        return <span className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded bg-purple-500/10 text-purple-600 dark:text-purple-400">Multiple Choice</span>;
      case "true_false":
        return <span className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">True / False</span>;
      case "short_answer":
        return <span className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded bg-amber-500/10 text-amber-600 dark:text-amber-400">Short Answer</span>;
      default:
        return <span className="text-xs font-semibold uppercase">{type}</span>;
    }
  };

  // Filtered Subject Questions for Picker
  const existingQuestionIds = new Set(questions.map((q) => q.assessment_question_question_id).filter(Boolean));
  const availableBankQuestions = subjectQuestions.filter((sq) => {
    const isAlreadyAdded = existingQuestionIds.has(sq.question_id);
    const matchesType = pickerType === "all" || sq.question_type === pickerType;
    const matchesSearch =
      !pickerSearch.trim() ||
      sq.question_text.toLowerCase().includes(pickerSearch.toLowerCase());
    return !isAlreadyAdded && matchesType && matchesSearch;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="flex items-center gap-3 text-sm font-semibold text-[var(--on-surface-variant)]">
          <div className="w-6 h-6 border-2 border-t-transparent border-[var(--primary)] rounded-full animate-spin" />
          Loading assessment builder...
        </div>
      </div>
    );
  }

  if (error || !assessment) {
    return (
      <div className="p-8 text-center max-w-lg mx-auto space-y-4">
        <span className="material-symbols-outlined text-[48px] text-red-500 block">error</span>
        <h2 className="text-xl font-bold text-[var(--on-surface)]">Failed to load assessment</h2>
        <p className="text-sm text-[var(--on-surface-variant)]">{error || "Assessment not found."}</p>
        <Button
          onClick={() => router.push("/classroom/assessments")}
          variant="outline"
          className="mt-2"
        >
          Return to Assessments
        </Button>
      </div>
    );
  }

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-6">
      {/* Top Breadcrumb & Status Navigation */}
      <div>
        <button
          onClick={() => {
            if (assessment.assessment_subject_id) {
              const query = assessment.workspace_id ? `?workspace_id=${assessment.workspace_id}` : "";
              router.push(`/classroom/subjects/${assessment.assessment_subject_id}${query}`);
            } else {
              router.push("/classroom/assessments");
            }
          }}
          className="text-sm font-medium text-[var(--primary)] hover:underline mb-3 inline-flex items-center gap-1 transition-colors"
        >
          <span className="material-symbols-outlined text-[16px]">arrow_back</span>
          Back to {assessment.subject_name || "Subject"}
        </button>

        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mt-1">
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-[var(--on-surface)]">
                {assessment.assessment_title}
              </h1>
              {getStatusBadge(assessment.assessment_status)}
              {getTypeBadge(assessment.assessment_type)}
            </div>
            {assessment.assessment_description && (
              <p className="text-sm text-[var(--on-surface-variant)] mt-2 max-w-2xl">
                {assessment.assessment_description}
              </p>
            )}
          </div>

          {/* Action Controls (Teachers / Admins only) */}
          {canManage && (
            <div className="flex items-center gap-2 self-start sm:self-auto flex-shrink-0">
              {isDraft && (
                <Button
                  onClick={() => setIsPublishModalOpen(true)}
                  className="flex items-center gap-2 shadow-sm font-medium"
                  style={{ backgroundColor: "var(--primary)", color: "var(--on-primary)" }}
                >
                  <span className="material-symbols-outlined text-[18px]">verified</span>
                  Publish Assessment
                </Button>
              )}
              {isPublished && (
                <Button
                  onClick={handleCloseAssessment}
                  variant="outline"
                  className="flex items-center gap-1.5"
                >
                  <span className="material-symbols-outlined text-[18px] text-amber-500">lock</span>
                  Close Exam
                </Button>
              )}
              {assessment.assessment_status !== "archived" && (
                <Button
                  onClick={handleArchiveAssessment}
                  variant="outline"
                  size="icon"
                  title="Archive Assessment"
                >
                  <span className="material-symbols-outlined text-[18px] text-[var(--on-surface-variant)] hover:text-red-500">archive</span>
                </Button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Metrics Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
        <div className="bg-[var(--surface-container-low)] p-4 rounded-2xl border border-[var(--outline-variant)] flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-500/10 text-blue-600 flex items-center justify-center flex-shrink-0">
            <span className="material-symbols-outlined text-[20px]">layers</span>
          </div>
          <div>
            <div className="text-xs text-[var(--on-surface-variant)] font-medium">Questions</div>
            <div className="text-lg font-bold text-[var(--on-surface)]">{questions.length}</div>
          </div>
        </div>

        <div className="bg-[var(--surface-container-low)] p-4 rounded-2xl border border-[var(--outline-variant)] flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-purple-500/10 text-purple-600 flex items-center justify-center flex-shrink-0">
            <span className="material-symbols-outlined text-[20px]">workspace_premium</span>
          </div>
          <div>
            <div className="text-xs text-[var(--on-surface-variant)] font-medium">Total Marks</div>
            <div className="text-lg font-bold text-[var(--on-surface)]">{totalCalculatedMarks}</div>
          </div>
        </div>

        <div className="bg-[var(--surface-container-low)] p-4 rounded-2xl border border-[var(--outline-variant)] flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-600 flex items-center justify-center flex-shrink-0">
            <span className="material-symbols-outlined text-[20px]">schedule</span>
          </div>
          <div>
            <div className="text-xs text-[var(--on-surface-variant)] font-medium">Duration</div>
            <div className="text-lg font-bold text-[var(--on-surface)]">
              {assessment.assessment_duration_minutes ? `${assessment.assessment_duration_minutes}m` : "No limit"}
            </div>
          </div>
        </div>

        <div className="bg-[var(--surface-container-low)] p-4 rounded-2xl border border-[var(--outline-variant)] flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-600 flex items-center justify-center flex-shrink-0">
            <span className="material-symbols-outlined text-[20px]">check_circle</span>
          </div>
          <div>
            <div className="text-xs text-[var(--on-surface-variant)] font-medium">Passing Marks</div>
            <div className="text-lg font-bold text-[var(--on-surface)]">
              {assessment.assessment_passing_marks ?? "None"}
            </div>
          </div>
        </div>

        <div className="bg-[var(--surface-container-low)] p-4 rounded-2xl border border-[var(--outline-variant)] flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-sky-500/10 text-sky-600 flex items-center justify-center flex-shrink-0">
            <span className="material-symbols-outlined text-[20px]">shuffle</span>
          </div>
          <div>
            <div className="text-xs text-[var(--on-surface-variant)] font-medium">Randomize</div>
            <div className="text-lg font-bold text-[var(--on-surface)]">
              {assessment.assessment_randomize_questions ? "Enabled" : "Disabled"}
            </div>
          </div>
        </div>
      </div>

      {/* ── STUDENT VIEW (When user does not have manage permissions) ── */}
      {!canManage ? (
        <div className="space-y-6">
          {assessment.assessment_description && (
            <div className="bg-[var(--surface-container-low)] border border-[var(--outline-variant)] rounded-2xl p-5 space-y-2">
              <h3 className="text-sm font-bold text-[var(--on-surface)] flex items-center gap-2">
                <span className="material-symbols-outlined text-[18px] text-[var(--primary)]">info</span>
                Instructions & Details
              </h3>
              <p className="text-xs sm:text-sm text-[var(--on-surface-variant)] leading-relaxed whitespace-pre-wrap">
                {assessment.assessment_description}
              </p>
            </div>
          )}

          {questions.length === 0 ? (
            <div className="text-center py-16 px-4 rounded-3xl border border-dashed border-[var(--outline-variant)] bg-[var(--surface-container-lowest)]">
              <span className="material-symbols-outlined text-[48px] text-[var(--on-surface-variant)] opacity-40 mb-3 block">
                quiz
              </span>
              <h3 className="text-base font-semibold text-[var(--on-surface)]">No questions available yet</h3>
              <p className="text-sm text-[var(--on-surface-variant)] mt-1">
                Questions will appear once the teacher publishes the exam.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-bold text-[var(--on-surface)] flex items-center gap-2">
                  <span className="material-symbols-outlined text-[20px] text-[var(--primary)]">assignment</span>
                  Assessment Questions ({questions.length})
                </h2>
                <span className="text-xs font-semibold text-[var(--on-surface-variant)]">
                  Total {totalCalculatedMarks} Marks
                </span>
              </div>

              {questions.map((q, idx) => (
                <div
                  key={q.assessment_question_id}
                  className="bg-[var(--surface-container-lowest)] border border-[var(--outline-variant)] rounded-2xl p-6 shadow-sm space-y-4"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold px-2.5 py-1 rounded-lg bg-[var(--primary)] text-[var(--on-primary)]">
                        Question {idx + 1}
                      </span>
                      {getQuestionTypeBadge(q.question_type)}
                    </div>
                    <span className="text-xs font-semibold text-[var(--on-surface-variant)]">
                      {q.assessment_question_marks} {Number(q.assessment_question_marks) === 1 ? "Mark" : "Marks"}
                    </span>
                  </div>

                  <h3 className="text-base font-semibold text-[var(--on-surface)] whitespace-pre-wrap">
                    {q.question_text}
                  </h3>

                  {q.options && q.options.length > 0 ? (
                    <div className="space-y-2 pt-1">
                      {q.options.map((opt) => (
                        <label
                          key={opt.option_id || opt.option_order}
                          className="flex items-center gap-3 p-3.5 rounded-xl border border-[var(--outline-variant)] hover:bg-[var(--surface-container-high)] cursor-pointer transition text-sm text-[var(--on-surface)]"
                        >
                          <input
                            type={q.question_type === "mcq_multiple" ? "checkbox" : "radio"}
                            name={`student_q_${q.assessment_question_id}`}
                            className="w-4 h-4 text-[var(--primary)] focus:ring-[var(--primary)]"
                          />
                          <span>{opt.option_text}</span>
                        </label>
                      ))}
                    </div>
                  ) : (
                    <Textarea
                      rows={3}
                      placeholder="Type your response here..."
                      className="w-full bg-[var(--surface-container-low)] text-sm"
                    />
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        /* ── TEACHER / ADMIN BUILDER TABS ── */
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="bg-[var(--surface-container-low)] border border-[var(--outline-variant)] p-1 rounded-2xl">
            <TabsTrigger value="builder" className="rounded-xl px-4 py-2 text-xs font-semibold data-[state=active]:bg-[var(--primary)] data-[state=active]:text-[var(--on-primary)] transition-all">
              <span className="material-symbols-outlined text-[16px] mr-1.5">quiz</span>
              Question Builder ({questions.length})
            </TabsTrigger>
            <TabsTrigger value="preview" className="rounded-xl px-4 py-2 text-xs font-semibold data-[state=active]:bg-[var(--primary)] data-[state=active]:text-[var(--on-primary)] transition-all">
              <span className="material-symbols-outlined text-[16px] mr-1.5">visibility</span>
              Student Preview Mode
            </TabsTrigger>
            <TabsTrigger value="settings" className="rounded-xl px-4 py-2 text-xs font-semibold data-[state=active]:bg-[var(--primary)] data-[state=active]:text-[var(--on-primary)] transition-all">
              <span className="material-symbols-outlined text-[16px] mr-1.5">settings</span>
              Assessment Specs & Settings
            </TabsTrigger>
          </TabsList>

        {/* ── TAB 1: QUESTION BUILDER ─────────────────────────────── */}
        <TabsContent value="builder" className="space-y-4 outline-none">
          {/* Builder Controls */}
          {isDraft && (
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-[var(--surface-container-low)] p-4 rounded-2xl border border-[var(--outline-variant)]">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[20px] text-[var(--primary)]">auto_awesome</span>
                <span className="text-xs sm:text-sm font-medium text-[var(--on-surface)]">
                  Pick questions from your Subject Question Bank or craft custom questions with frozen snapshots.
                </span>
              </div>

              <div className="flex items-center gap-2 flex-shrink-0">
                <Button
                  onClick={() => setIsPickerOpen(true)}
                  className="flex items-center gap-1.5 text-xs font-semibold shadow-sm"
                  style={{ backgroundColor: "var(--primary)", color: "var(--on-primary)" }}
                >
                  <span className="material-symbols-outlined text-[16px]">menu_book</span>
                  Pick from Question Bank
                </Button>
                <Button
                  onClick={handleOpenInlineCreate}
                  variant="outline"
                  className="flex items-center gap-1.5 text-xs font-semibold"
                >
                  <span className="material-symbols-outlined text-[16px]">add</span>
                  Create Question
                </Button>
              </div>
            </div>
          )}

          {!isDraft && (
            <div className="p-3.5 bg-[var(--surface-container-low)] border border-[var(--outline-variant)] rounded-xl text-xs text-[var(--on-surface-variant)] flex items-center gap-2">
              <span className="material-symbols-outlined text-[18px] text-amber-500 flex-shrink-0">lock</span>
              <span>Assessment is {assessment.assessment_status}. Question content, options, and marks are locked and immutable.</span>
            </div>
          )}

          {/* Question Cards */}
          {questions.length === 0 ? (
            <div className="text-center py-16 px-4 rounded-3xl border border-dashed border-[var(--outline-variant)] bg-[var(--surface-container-lowest)]">
              <span className="material-symbols-outlined text-[48px] text-[var(--on-surface-variant)] opacity-40 mb-3 block">
                menu_book
              </span>
              <h3 className="text-base font-semibold text-[var(--on-surface)]">No questions in this assessment</h3>
              <p className="text-sm text-[var(--on-surface-variant)] mt-1 max-w-sm mx-auto">
                Add questions from your Subject Question Bank or craft new ones to publish this assessment.
              </p>
              {isDraft && (
                <div className="mt-4 flex justify-center gap-3">
                  <Button
                    onClick={() => setIsPickerOpen(true)}
                    className="flex items-center gap-2 shadow-sm font-medium"
                    style={{ backgroundColor: "var(--primary)", color: "var(--on-primary)" }}
                  >
                    <span className="material-symbols-outlined text-[18px]">menu_book</span>
                    Browse Question Bank
                  </Button>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              {questions.map((q, idx) => (
                <div
                  key={q.assessment_question_id}
                  className="bg-[var(--surface-container-lowest)] border border-[var(--outline-variant)] rounded-2xl p-5 shadow-sm space-y-3 hover:border-[var(--outline)] transition"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-2 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-bold px-2 py-0.5 rounded-md bg-[var(--surface-container-high)] text-[var(--on-surface)]">
                          Q{idx + 1}
                        </span>
                        {getQuestionTypeBadge(q.question_type)}
                        <div className="flex items-center gap-1.5 text-xs text-[var(--on-surface-variant)]">
                          <span>Marks:</span>
                          {isDraft ? (
                            <input
                              type="number"
                              step="0.5"
                              min="0.5"
                              defaultValue={Number(q.assessment_question_marks)}
                              onBlur={(e) => handleUpdateMarks(q.assessment_question_id, parseFloat(e.target.value))}
                              className="w-16 px-1.5 py-0.5 text-xs font-bold bg-[var(--surface-container-low)] border border-[var(--outline-variant)] rounded text-center text-[var(--on-surface)] focus:ring-1 focus:ring-[var(--primary)]"
                            />
                          ) : (
                            <span className="font-bold text-[var(--on-surface)]">
                              {q.assessment_question_marks}
                            </span>
                          )}
                        </div>
                      </div>

                      <p className="text-base font-semibold text-[var(--on-surface)] whitespace-pre-wrap">
                        {q.question_text}
                      </p>

                      {/* Options with answer keys */}
                      {q.options && q.options.length > 0 && (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2">
                          {q.options.map((opt) => (
                            <div
                              key={opt.option_id || opt.option_order}
                              className={`flex items-center gap-2.5 p-2.5 rounded-xl border text-sm ${
                                opt.option_is_correct || opt.is_correct
                                  ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300 font-medium"
                                  : "bg-[var(--surface-container-low)] border-[var(--outline-variant)] text-[var(--on-surface)]"
                              }`}
                            >
                              <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs ${
                                opt.option_is_correct || opt.is_correct
                                  ? "bg-emerald-600 text-white"
                                  : "bg-[var(--surface-container-high)] text-[var(--on-surface-variant)]"
                              }`}>
                                {opt.option_is_correct || opt.is_correct ? <span className="material-symbols-outlined text-[13px]">check</span> : opt.option_order}
                              </span>
                              <span className="flex-1">{opt.option_text}</span>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Teacher Explanation */}
                      {q.question_explanation && (
                        <div className="mt-2.5 p-3 bg-blue-500/10 border border-blue-500/20 rounded-xl text-xs text-blue-700 dark:text-blue-300 flex items-start gap-2">
                          <span className="material-symbols-outlined text-[16px] text-blue-600 flex-shrink-0 mt-0.5">lightbulb</span>
                          <div>
                            <span className="font-semibold">Explanation:</span> {q.question_explanation}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Builder Controls: Up / Down / Remove */}
                    {isDraft && (
                      <div className="flex flex-col items-center gap-1 flex-shrink-0">
                        <Button
                          size="icon"
                          variant="ghost"
                          disabled={idx === 0}
                          onClick={() => handleMoveQuestion(idx, "up")}
                          className="h-8 w-8 text-[var(--on-surface-variant)] hover:text-[var(--on-surface)]"
                          title="Move up"
                        >
                          <span className="material-symbols-outlined text-[18px]">arrow_upward</span>
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          disabled={idx === questions.length - 1}
                          onClick={() => handleMoveQuestion(idx, "down")}
                          className="h-8 w-8 text-[var(--on-surface-variant)] hover:text-[var(--on-surface)]"
                          title="Move down"
                        >
                          <span className="material-symbols-outlined text-[18px]">arrow_downward</span>
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => handleRemoveQuestion(q.assessment_question_id)}
                          className="h-8 w-8 text-[var(--on-surface-variant)] hover:text-red-600 hover:bg-red-500/10 mt-1"
                          title="Remove from assessment"
                        >
                          <span className="material-symbols-outlined text-[18px]">delete</span>
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </TabsContent>

        {/* ── TAB 2: STUDENT PREVIEW MODE ─────────────────────────── */}
        <TabsContent value="preview" className="space-y-6 outline-none">
          <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl text-emerald-800 dark:text-emerald-300 text-xs sm:text-sm flex items-center gap-3">
            <span className="material-symbols-outlined text-[22px] text-emerald-600 flex-shrink-0">visibility</span>
            <span>
              <strong>Student Preview Mode:</strong> Questions are rendered exactly as students will see them. Correct answers and teacher explanations are strictly sanitized.
            </span>
          </div>

          <div className="space-y-4">
            {questions.map((q, idx) => (
              <div
                key={q.assessment_question_id}
                className="bg-[var(--surface-container-lowest)] border border-[var(--outline-variant)] rounded-2xl p-6 shadow-sm space-y-4"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold px-2.5 py-1 rounded-lg bg-[var(--primary)] text-[var(--on-primary)]">
                      Question {idx + 1}
                    </span>
                    <span className="text-xs font-semibold text-[var(--on-surface-variant)]">
                      {q.assessment_question_marks} {Number(q.assessment_question_marks) === 1 ? "Mark" : "Marks"}
                    </span>
                  </div>
                </div>

                <h3 className="text-base font-semibold text-[var(--on-surface)] whitespace-pre-wrap">
                  {q.question_text}
                </h3>

                {/* Simulated Student Options */}
                {q.options && q.options.length > 0 ? (
                  <div className="space-y-2">
                    {q.options.map((opt) => (
                      <label
                        key={opt.option_id || opt.option_order}
                        className="flex items-center gap-3 p-3.5 rounded-xl border border-[var(--outline-variant)] hover:bg-[var(--surface-container-high)] cursor-pointer transition text-sm text-[var(--on-surface)]"
                      >
                        <input
                          type={q.question_type === "mcq_multiple" ? "checkbox" : "radio"}
                          name={`preview_q_${q.assessment_question_id}`}
                          className="w-4 h-4 text-[var(--primary)] focus:ring-[var(--primary)]"
                        />
                        <span>{opt.option_text}</span>
                      </label>
                    ))}
                  </div>
                ) : (
                  <Textarea
                    rows={3}
                    placeholder="Student types short answer response here..."
                    disabled
                    className="w-full bg-[var(--surface-container-low)] text-[var(--on-surface-variant)] italic"
                  />
                )}
              </div>
            ))}
          </div>
        </TabsContent>

        {/* ── TAB 3: ASSESSMENT SPECS & SETTINGS ───────────────────── */}
        <TabsContent value="settings" className="outline-none">
          <div className="bg-[var(--surface-container-lowest)] rounded-2xl border border-[var(--outline-variant)] p-6 md:p-8 shadow-sm">
            <form onSubmit={handleSaveSettings} className="max-w-2xl space-y-5">
              {settingsSuccess && (
                <div className="p-3.5 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-800 dark:text-emerald-300 text-xs flex items-center gap-2">
                  <span className="material-symbols-outlined text-[18px]">check_circle</span>
                  <span>Assessment settings updated successfully.</span>
                </div>
              )}

              <div>
                <Label className="text-xs font-semibold uppercase tracking-wider text-[var(--on-surface-variant)] mb-1.5 block">
                  Assessment Title *
                </Label>
                <Input
                  value={settingsTitle}
                  onChange={(e) => setSettingsTitle(e.target.value)}
                  required
                  className="bg-[var(--surface-container-low)]"
                />
              </div>

              <div>
                <Label className="text-xs font-semibold uppercase tracking-wider text-[var(--on-surface-variant)] mb-1.5 block">
                  Description & Instructions
                </Label>
                <Textarea
                  rows={3}
                  value={settingsDescription}
                  onChange={(e) => setSettingsDescription(e.target.value)}
                  className="bg-[var(--surface-container-low)]"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <Label className="text-xs font-semibold uppercase tracking-wider text-[var(--on-surface-variant)] mb-1.5 block">
                    Duration (Minutes)
                  </Label>
                  <Input
                    type="number"
                    min="1"
                    max="1440"
                    value={settingsDuration}
                    onChange={(e) => setSettingsDuration(e.target.value)}
                    disabled={!isDraft}
                    placeholder="Optional (e.g. 60)"
                    className="bg-[var(--surface-container-low)] disabled:opacity-50"
                  />
                </div>

                <div>
                  <Label className="text-xs font-semibold uppercase tracking-wider text-[var(--on-surface-variant)] mb-1.5 block">
                    Passing Marks
                  </Label>
                  <Input
                    type="number"
                    step="0.5"
                    min="0"
                    value={settingsPassingMarks}
                    onChange={(e) => setSettingsPassingMarks(e.target.value)}
                    placeholder="Optional threshold"
                    className="bg-[var(--surface-container-low)]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <Label className="text-xs font-semibold uppercase tracking-wider text-[var(--on-surface-variant)] mb-1.5 block">
                    Attempt Limit
                  </Label>
                  <Input
                    type="number"
                    min="1"
                    value={settingsAttemptLimit}
                    onChange={(e) => setSettingsAttemptLimit(parseInt(e.target.value) || 1)}
                    className="bg-[var(--surface-container-low)]"
                  />
                </div>

                <div className="flex items-center pt-6">
                  <label className="flex items-center gap-2.5 text-sm text-[var(--on-surface)] cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settingsRandomize}
                      onChange={(e) => setSettingsRandomize(e.target.checked)}
                      className="w-4 h-4 text-[var(--primary)] rounded border-[var(--outline-variant)]"
                    />
                    <span>Randomize Question Order for Students</span>
                  </label>
                </div>
              </div>

              <div className="pt-4 border-t border-[var(--outline-variant)]">
                <Button
                  type="submit"
                  disabled={settingsSaving}
                  className="flex items-center gap-2 font-medium"
                  style={{ backgroundColor: "var(--primary)", color: "var(--on-primary)" }}
                >
                  {settingsSaving && <div className="w-4 h-4 border-2 border-t-transparent border-white rounded-full animate-spin" />}
                  Save Settings
                </Button>
              </div>
            </form>
          </div>
        </TabsContent>
      </Tabs>
      )}

      {/* ── QUESTION BANK PICKER DIALOG ──────────────────────────── */}
      <Dialog open={isPickerOpen} onOpenChange={setIsPickerOpen}>
        <DialogContent className="max-w-3xl rounded-3xl bg-white dark:bg-[#1b211e] border-[var(--outline-variant)] p-6 shadow-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-lg font-bold text-[var(--on-surface)]">
              <span className="material-symbols-outlined text-[22px] text-[var(--primary)]">menu_book</span>
              Select Questions from Question Bank
            </DialogTitle>
            <DialogDescription className="text-xs text-[var(--on-surface-variant)]">
              Select questions to include in this assessment. Snapshots will be automatically frozen.
            </DialogDescription>
          </DialogHeader>

          {/* Search and Filters */}
          <div className="flex flex-col sm:flex-row gap-3 pt-2">
            <div className="relative flex-1">
              <span className="material-symbols-outlined absolute left-3 top-2 text-[18px] text-[var(--on-surface-variant)]">
                search
              </span>
              <Input
                type="text"
                placeholder="Search available questions..."
                value={pickerSearch}
                onChange={(e) => setPickerSearch(e.target.value)}
                className="pl-9 h-9 text-xs bg-[var(--surface-container-low)]"
              />
            </div>
            <div className="flex gap-1 overflow-x-auto pb-1 sm:pb-0">
              {(["all", "mcq_single", "mcq_multiple", "true_false", "short_answer"] as const).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setPickerType(t)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition ${
                    pickerType === t
                      ? "bg-[var(--primary)] text-[var(--on-primary)] shadow-sm"
                      : "bg-[var(--surface-container-low)] text-[var(--on-surface-variant)] hover:bg-[var(--surface-container-high)]"
                  }`}
                >
                  {t === "all" ? "All" : t.replace("_", " ")}
                </button>
              ))}
            </div>
          </div>

          {/* Question Bank Items List */}
          <div className="max-h-80 overflow-y-auto space-y-2 border border-[var(--outline-variant)] rounded-2xl p-3 bg-[var(--surface-container-low)]">
            {availableBankQuestions.length === 0 ? (
              <p className="text-center text-xs text-[var(--on-surface-variant)] py-8">
                No available questions found in this subject's question bank.
              </p>
            ) : (
              availableBankQuestions.map((bq) => (
                <div
                  key={bq.question_id}
                  onClick={() => toggleSelectBankId(bq.question_id)}
                  className={`p-3 rounded-xl border text-sm cursor-pointer transition flex items-start gap-3 ${
                    selectedBankIds.includes(bq.question_id)
                      ? "bg-blue-500/10 border-blue-500/40 text-[var(--on-surface)]"
                      : "bg-[var(--surface-container-lowest)] border-[var(--outline-variant)] hover:border-[var(--outline)]"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedBankIds.includes(bq.question_id)}
                    onChange={() => {}}
                    className="mt-1 w-4 h-4 text-[var(--primary)] rounded"
                  />
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center gap-2">
                      {getQuestionTypeBadge(bq.question_type)}
                      <span className="text-xs text-[var(--on-surface-variant)] font-medium">
                        {bq.question_default_marks} marks
                      </span>
                    </div>
                    <p className="text-xs font-medium text-[var(--on-surface)]">
                      {bq.question_text}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>

          <DialogFooter className="flex items-center justify-between sm:justify-between pt-2">
            <span className="text-xs font-semibold text-[var(--on-surface-variant)]">
              {selectedBankIds.length} selected
            </span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => setIsPickerOpen(false)}>
                Cancel
              </Button>
              <Button
                size="sm"
                disabled={selectedBankIds.length === 0 || addingFromBank}
                onClick={handleAddSelectedFromBank}
                style={{ backgroundColor: "var(--primary)", color: "var(--on-primary)" }}
              >
                {addingFromBank && <div className="w-3.5 h-3.5 border-2 border-t-transparent border-white rounded-full animate-spin mr-1.5" />}
                Add to Assessment
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── INLINE QUESTION CREATOR DIALOG ───────────────────────── */}
      <Dialog open={isInlineCreateOpen} onOpenChange={setIsInlineCreateOpen}>
        <DialogContent className="max-w-2xl rounded-3xl bg-white dark:bg-[#1b211e] border-[var(--outline-variant)] p-6 shadow-2xl">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold text-[var(--on-surface)]">
              Create & Attach Question
            </DialogTitle>
            <DialogDescription className="text-xs text-[var(--on-surface-variant)]">
              Creates a question in the Subject Question Bank and attaches its snapshot directly to this assessment.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSaveInlineQuestion} className="space-y-4 pt-2">
            {inlineError && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-600 dark:text-red-400 text-xs">
                {inlineError}
              </div>
            )}

            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-[var(--on-surface-variant)] mb-1.5 block">
                Question Type
              </Label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {[
                  { type: "mcq_single", label: "Single Choice" },
                  { type: "mcq_multiple", label: "Multiple Choice" },
                  { type: "true_false", label: "True / False" },
                  { type: "short_answer", label: "Short Answer" },
                ].map((item) => (
                  <button
                    type="button"
                    key={item.type}
                    onClick={() => setInlineType(item.type as QuestionType)}
                    className={`py-2 px-3 text-xs font-semibold rounded-xl border text-center transition ${
                      inlineType === item.type
                        ? "bg-[var(--primary)] text-[var(--on-primary)] border-transparent shadow-sm"
                        : "bg-[var(--surface-container-low)] border-[var(--outline-variant)] text-[var(--on-surface)] hover:bg-[var(--surface-container-high)]"
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-[var(--on-surface-variant)] mb-1.5 block">
                Question Prompt *
              </Label>
              <Textarea
                rows={2}
                value={inlineText}
                onChange={(e) => setInlineText(e.target.value)}
                placeholder="Enter prompt..."
                className="bg-[var(--surface-container-low)] text-sm"
                required
              />
            </div>

            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-[var(--on-surface-variant)] mb-1.5 block">
                Marks *
              </Label>
              <Input
                type="number"
                step="0.5"
                min="0.5"
                value={inlineMarks}
                onChange={(e) => setInlineMarks(e.target.value)}
                className="w-28 bg-[var(--surface-container-low)] text-sm"
                required
              />
            </div>

            {/* Options */}
            {inlineType !== "short_answer" && (
              <div className="space-y-2 pt-2 border-t border-[var(--outline-variant)]">
                <Label className="text-xs font-semibold uppercase tracking-wider text-[var(--on-surface-variant)] block">
                  Options & Answer Key (Click checkmark to mark correct)
                </Label>
                {inlineOptions.map((opt, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        setInlineOptions((prev) =>
                          prev.map((o, i) =>
                            inlineType === "mcq_single" || inlineType === "true_false"
                              ? { ...o, is_correct: i === idx }
                              : i === idx ? { ...o, is_correct: !o.is_correct } : o
                          )
                        );
                      }}
                      className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs flex-shrink-0 transition ${
                        opt.is_correct ? "bg-emerald-600 text-white" : "bg-[var(--surface-container-high)] text-[var(--on-surface-variant)]"
                      }`}
                    >
                      <span className="material-symbols-outlined text-[16px]">check</span>
                    </button>
                    <Input
                      type="text"
                      value={opt.option_text}
                      onChange={(e) => {
                        const val = e.target.value;
                        setInlineOptions((prev) => {
                          const next = [...prev];
                          next[idx].option_text = val;
                          return next;
                        });
                      }}
                      placeholder={`Option ${idx + 1}...`}
                      className="bg-[var(--surface-container-low)] text-xs h-9"
                      required
                    />
                  </div>
                ))}
              </div>
            )}

            <DialogFooter className="pt-3 border-t border-[var(--outline-variant)]">
              <Button type="button" variant="outline" size="sm" onClick={() => setIsInlineCreateOpen(false)}>
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={inlineSaving}
                style={{ backgroundColor: "var(--primary)", color: "var(--on-primary)" }}
              >
                {inlineSaving && <div className="w-3.5 h-3.5 border-2 border-t-transparent border-white rounded-full animate-spin mr-1.5" />}
                Create & Attach
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ── PUBLISH CONFIRMATION DIALOG ──────────────────────────── */}
      <Dialog open={isPublishModalOpen} onOpenChange={setIsPublishModalOpen}>
        <DialogContent className="max-w-md rounded-3xl bg-white dark:bg-[#1b211e] border-[var(--outline-variant)] p-6 shadow-2xl">
          <DialogHeader>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-emerald-500/10 text-emerald-600 flex items-center justify-center flex-shrink-0">
                <span className="material-symbols-outlined text-[24px]">verified</span>
              </div>
              <div>
                <DialogTitle className="text-base font-bold text-[var(--on-surface)]">Publish Assessment</DialogTitle>
                <DialogDescription className="text-xs text-[var(--on-surface-variant)]">
                  Verify checklist before publishing exam
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          {publishError && (
            <div className="p-3 bg-red-500/10 text-red-600 dark:text-red-400 text-xs border border-red-500/20 rounded-xl">
              {publishError}
            </div>
          )}

          <div className="space-y-2.5 bg-[var(--surface-container-low)] p-4 rounded-2xl text-xs border border-[var(--outline-variant)]">
            <div className="flex items-center gap-2">
              <span className={`material-symbols-outlined text-[18px] ${questions.length > 0 ? "text-emerald-600" : "text-red-500"}`}>
                {questions.length > 0 ? "check_circle" : "cancel"}
              </span>
              <span className="text-[var(--on-surface)]">At least 1 question added ({questions.length} questions)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className={`material-symbols-outlined text-[18px] ${totalCalculatedMarks > 0 ? "text-emerald-600" : "text-red-500"}`}>
                {totalCalculatedMarks > 0 ? "check_circle" : "cancel"}
              </span>
              <span className="text-[var(--on-surface)]">Total marks greater than 0 ({totalCalculatedMarks} marks)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[18px] text-emerald-600">lock</span>
              <span className="text-[var(--on-surface)]">Snapshots will be permanently locked</span>
            </div>
          </div>

          <DialogFooter className="pt-2">
            <Button variant="outline" size="sm" onClick={() => setIsPublishModalOpen(false)}>
              Cancel
            </Button>
            <Button
              size="sm"
              disabled={publishing || questions.length === 0}
              onClick={handleConfirmPublish}
              style={{ backgroundColor: "var(--primary)", color: "var(--on-primary)" }}
            >
              {publishing && <div className="w-3.5 h-3.5 border-2 border-t-transparent border-white rounded-full animate-spin mr-1.5" />}
              Confirm & Publish
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
