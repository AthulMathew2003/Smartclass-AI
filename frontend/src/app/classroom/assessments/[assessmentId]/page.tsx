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
  startAssessmentAttempt,
  fetchStudentAttempts,
  fetchAssessmentResults,
  fetchAssessmentAnalytics,
  fetchStudentSelfAnalytics,
  Assessment,
  AssessmentQuestion,
  QuestionBankItem,
  QuestionType,
  QuestionOptionCreateInput,
  AssessmentAttemptSummary,
  TeacherAssessmentResultSummary,
  AssessmentAnalyticsResponse,
  StudentSelfAnalyticsResponse,
  AssessmentQuestionAnalyticsItem,
  AssessmentStudentPerformanceItem,
  AssessmentLeaderboardResponse,
  AssessmentLeaderboardEntry,
  fetchAssessmentLeaderboard,
  updateAssessmentLeaderboardSettings
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

  const [studentAttempts, setStudentAttempts] = useState<AssessmentAttemptSummary[]>([]);
  const [submissions, setSubmissions] = useState<TeacherAssessmentResultSummary[]>([]);
  const [loadingSubmissions, setLoadingSubmissions] = useState(false);
  const [analyticsData, setAnalyticsData] = useState<AssessmentAnalyticsResponse | null>(null);
  const [studentSelfAnalytics, setStudentSelfAnalytics] = useState<StudentSelfAnalyticsResponse | null>(null);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);
  const [studentSearch, setStudentSearch] = useState("");
  const [startingAttempt, setStartingAttempt] = useState(false);
  const [startAttemptError, setStartAttemptError] = useState<string | null>(null);

  const canManage = hasPermission("assessment.update") || hasPermission("assessment.publish") || hasPermission("question.create") || hasPermission("assessment.grade");

  // Question Bank Picker Modal
  const [isPickerOpen, setIsPickerOpen] = useState(false);
  const [pickerSearch, setPickerSearch] = useState("");
  const [pickerType, setPickerType] = useState<string>("all");
  const [selectedBankIds, setSelectedBankIds] = useState<string[]>([]);
  const [addingFromBank, setAddingFromBank] = useState(false);

  // Inline Question Creator Modal
  const [isInlineCreateOpen, setIsInlineCreateOpen] = useState(false);
  
  interface InlineQuestionState {
    id: string;
    type: QuestionType;
    text: string;
    marks: string;
    explanation: string;
    options: QuestionOptionCreateInput[];
  }
  
  const createEmptyInlineQuestion = (type: QuestionType = "mcq_single"): InlineQuestionState => ({
    id: crypto.randomUUID(),
    type,
    text: "",
    marks: "5.00",
    explanation: "",
    options:
      type === "true_false"
        ? [
            { option_text: "True", option_order: 1, is_correct: true },
            { option_text: "False", option_order: 2, is_correct: false },
          ]
        : type === "short_answer"
        ? []
        : [
            { option_text: "", option_order: 1, is_correct: true },
            { option_text: "", option_order: 2, is_correct: false },
            { option_text: "", option_order: 3, is_correct: false },
            { option_text: "", option_order: 4, is_correct: false },
          ],
  });

  const [inlineQuestions, setInlineQuestions] = useState<InlineQuestionState[]>([]);
  const [inlineSaving, setInlineSaving] = useState(false);
  const [inlineError, setInlineError] = useState<string | null>(null);

  // Settings Tab State
  const [settingsTitle, setSettingsTitle] = useState("");
  const [settingsDescription, setSettingsDescription] = useState("");
  const [settingsDuration, setSettingsDuration] = useState("");
  const [settingsPassingMarks, setSettingsPassingMarks] = useState("");
  const [settingsAttemptLimit, setSettingsAttemptLimit] = useState(1);
  const [settingsRandomize, setSettingsRandomize] = useState(false);
  const [settingsLeaderboardEnabled, setSettingsLeaderboardEnabled] = useState(false);
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [settingsSuccess, setSettingsSuccess] = useState(false);

  // Leaderboard State
  const [leaderboardData, setLeaderboardData] = useState<AssessmentLeaderboardResponse | null>(null);
  const [loadingLeaderboard, setLoadingLeaderboard] = useState(false);
  const [leaderboardPage, setLeaderboardPage] = useState(1);
  const [togglingLeaderboard, setTogglingLeaderboard] = useState(false);

  // Publish Dialog State
  const [isPublishModalOpen, setIsPublishModalOpen] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [publishError, setPublishError] = useState<string | null>(null);

  useEffect(() => {
    if (permLoaded) {
      loadAssessmentData();
    }
  }, [assessmentId, permLoaded]);

  async function loadLeaderboardData(page: number = 1) {
    try {
      setLoadingLeaderboard(true);
      const res = await fetchAssessmentLeaderboard(assessmentId, page, 20);
      setLeaderboardData(res);
      setLeaderboardPage(page);
    } catch {
      // Gracefully handled (e.g. if disabled or unauthenticated)
    } finally {
      setLoadingLeaderboard(false);
    }
  }

  async function handleToggleLeaderboard(newEnabled: boolean) {
    try {
      setTogglingLeaderboard(true);
      const res = await updateAssessmentLeaderboardSettings(assessmentId, newEnabled);
      setAssessment((prev) => (prev ? { ...prev, assessment_leaderboard_enabled: res.leaderboard_enabled } : null));
      setSettingsLeaderboardEnabled(res.leaderboard_enabled);
      await loadLeaderboardData(1);
    } catch (err: any) {
      alert(err.message || "Failed to update leaderboard settings.");
    } finally {
      setTogglingLeaderboard(false);
    }
  }

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
      setSettingsLeaderboardEnabled(asm.assessment_leaderboard_enabled || false);

      // Load Leaderboard data
      loadLeaderboardData(1);

      // Load Subject Question Bank, Submissions, and Analytics for teachers/admins
      if (canManage) {
        if (asm.assessment_subject_id) {
          try {
            const bank = await fetchSubjectQuestions(asm.assessment_subject_id);
            setSubjectQuestions(bank);
          } catch {
            // Handled gracefully
          }
        }
        try {
          const subs = await fetchAssessmentResults(assessmentId);
          setSubmissions(subs);
        } catch {
          // Handled gracefully
        }
        try {
          setLoadingAnalytics(true);
          const analytics = await fetchAssessmentAnalytics(assessmentId);
          setAnalyticsData(analytics);
        } catch {
          // Handled gracefully
        } finally {
          setLoadingAnalytics(false);
        }
      } else {
        // Load student attempts and self-analytics
        try {
          const atts = await fetchStudentAttempts(assessmentId);
          setStudentAttempts(atts);
        } catch {
          // Handled gracefully
        }
        try {
          setLoadingAnalytics(true);
          const selfStats = await fetchStudentSelfAnalytics(assessmentId);
          setStudentSelfAnalytics(selfStats);
        } catch {
          // Handled gracefully
        } finally {
          setLoadingAnalytics(false);
        }
      }
    } catch (err: any) {
      setError(err.message || "Failed to load assessment details.");
    } finally {
      setLoading(false);
    }
  }

  async function handleStartOrResumeAttempt(existingAttemptId?: string) {
    if (existingAttemptId) {
      router.push(`/classroom/assessments/${assessmentId}/attempt/${existingAttemptId}`);
      return;
    }
    try {
      setStartingAttempt(true);
      setStartAttemptError(null);
      const res = await startAssessmentAttempt(assessmentId);
      router.push(`/classroom/assessments/${assessmentId}/attempt/${res.attempt_id}`);
    } catch (err: any) {
      setStartAttemptError(err.message || "Failed to start assessment attempt.");
    } finally {
      setStartingAttempt(false);
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
    setInlineQuestions([createEmptyInlineQuestion()]);
    setInlineError(null);
    setIsInlineCreateOpen(true);
  }

  function handleInlineTypeChange(questionId: string, newType: QuestionType) {
    setInlineQuestions((prev) =>
      prev.map((q) => {
        if (q.id !== questionId) return q;
        let newOptions: QuestionOptionCreateInput[] = q.options;
        if (newType === "true_false") {
          newOptions = [
            { option_text: "True", option_order: 1, is_correct: true },
            { option_text: "False", option_order: 2, is_correct: false },
          ];
        } else if (newType === "short_answer") {
          newOptions = [];
        } else if (newType === "mcq_single" || newType === "mcq_multiple") {
          if (q.type === "true_false" || q.type === "short_answer" || newOptions.length < 2) {
            newOptions = [
              { option_text: "", option_order: 1, is_correct: true },
              { option_text: "", option_order: 2, is_correct: false },
              { option_text: "", option_order: 3, is_correct: false },
              { option_text: "", option_order: 4, is_correct: false },
            ];
          }
        }
        return {
          ...q,
          type: newType,
          options: newOptions,
        };
      })
    );
  }

  function addOptionToInlineQuestion(questionId: string) {
    setInlineQuestions((prev) =>
      prev.map((q) => {
        if (q.id !== questionId) return q;
        if (q.type === "true_false" || q.type === "short_answer") return q;
        if (q.options.length >= 6) return q;
        return {
          ...q,
          options: [
            ...q.options,
            {
              option_text: "",
              option_order: q.options.length + 1,
              is_correct: false,
            },
          ],
        };
      })
    );
  }

  function removeOptionFromInlineQuestion(questionId: string, optionIndex: number) {
    setInlineQuestions((prev) =>
      prev.map((q) => {
        if (q.id !== questionId) return q;
        if (q.options.length <= 2) return q;
        const newOpts = q.options.filter((_, idx) => idx !== optionIndex).map((opt, idx) => ({
          ...opt,
          option_order: idx + 1,
        }));
        return { ...q, options: newOpts };
      })
    );
  }

  async function handleSaveInlineQuestion(e: React.FormEvent) {
    e.preventDefault();
    setInlineError(null);

    if (inlineQuestions.length === 0) {
      setInlineError("Please add at least one question.");
      return;
    }

    // Validation
    for (let i = 0; i < inlineQuestions.length; i++) {
      const q = inlineQuestions[i];
      const trimmedText = q.text.trim();
      if (!trimmedText) {
        setInlineError(`Question ${i + 1}: Question prompt is required.`);
        return;
      }

      const marksNum = parseFloat(q.marks);
      if (isNaN(marksNum) || marksNum <= 0) {
        setInlineError(`Question ${i + 1}: Marks must be a positive number.`);
        return;
      }

      if (q.type === "mcq_single" || q.type === "mcq_multiple") {
        const validOptions = q.options.filter((o) => o.option_text.trim());
        if (validOptions.length < 2) {
          setInlineError(`Question ${i + 1}: Choice questions must have at least 2 options.`);
          return;
        }
        const correctCount = validOptions.filter((o) => o.is_correct).length;
        if (q.type === "mcq_single" && correctCount !== 1) {
          setInlineError(`Question ${i + 1}: Single choice questions must have exactly 1 correct option.`);
          return;
        }
        if (q.type === "mcq_multiple" && correctCount < 1) {
          setInlineError(`Question ${i + 1}: Multiple choice questions must have at least 1 correct option.`);
          return;
        }
      } else if (q.type === "true_false") {
        const correctCount = q.options.filter((o) => o.is_correct).length;
        if (correctCount !== 1) {
          setInlineError(`Question ${i + 1}: Please select whether True or False is the correct answer.`);
          return;
        }
      }
    }

    try {
      setInlineSaving(true);
      const promises = inlineQuestions.map(async (q) => {
        let cleanedOptions: QuestionOptionCreateInput[] = [];
        if (q.type === "true_false") {
          const isTrueCorrect = q.options.find((o) => o.option_text.toLowerCase() === "true")?.is_correct ?? true;
          cleanedOptions = [
            { option_text: "True", option_order: 1, is_correct: isTrueCorrect },
            { option_text: "False", option_order: 2, is_correct: !isTrueCorrect },
          ];
        } else if (q.type === "mcq_single" || q.type === "mcq_multiple") {
          cleanedOptions = q.options
            .filter((o) => o.option_text.trim())
            .map((o, idx) => ({
              option_text: o.option_text.trim(),
              option_order: idx + 1,
              is_correct: o.is_correct || false,
            }));
        }

        return createAndAddQuestionToAssessment(assessmentId, {
          question_type: q.type,
          question_text: q.text.trim(),
          marks: parseFloat(q.marks),
          question_explanation: q.explanation.trim() || null,
          options: cleanedOptions,
        });
      });

      await Promise.all(promises);
      
      await loadAssessmentData();
      setIsInlineCreateOpen(false);
    } catch (err: any) {
      setInlineError(err.message || "Failed to create questions.");
    } finally {
      setInlineSaving(false);
    }
  }

  function addAnotherInlineQuestion() {
    setInlineQuestions((prev) => [...prev, createEmptyInlineQuestion()]);
  }

  function removeInlineQuestion(id: string) {
    setInlineQuestions((prev) => prev.filter((q) => q.id !== id));
  }

  function updateInlineQuestion(id: string, updates: Partial<InlineQuestionState>) {
    setInlineQuestions((prev) => prev.map((q) => q.id === id ? { ...q, ...updates } : q));
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
        leaderboard_enabled: settingsLeaderboardEnabled,
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
          {/* Start / Resume Attempt Hero Card */}
          {(() => {
            const inProgressAttempt = studentAttempts.find((a) => a.attempt_status === "in_progress");
            const attemptsCount = studentAttempts.length;
            const attemptLimit = assessment.assessment_attempt_limit || 1;
            const canStartNew = attemptsCount < attemptLimit && isPublished;

            return (
              <div className="bg-[var(--surface-container-lowest)] border border-[var(--outline-variant)] rounded-3xl p-6 sm:p-8 shadow-sm space-y-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold px-2.5 py-1 rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400">
                        {attemptsCount} of {attemptLimit} Attempts Used
                      </span>
                      {inProgressAttempt && (
                        <Badge variant="outline" className="bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20">
                          Active Attempt in Progress
                        </Badge>
                      )}
                    </div>
                    <h2 className="text-xl font-bold text-[var(--on-surface)]">
                      {inProgressAttempt
                        ? `Resume Attempt #${inProgressAttempt.attempt_number}`
                        : canStartNew
                        ? `Ready to take this ${assessment.assessment_type}?`
                        : "Assessment Attempt Summary"}
                    </h2>
                    <p className="text-xs sm:text-sm text-[var(--on-surface-variant)]">
                      {inProgressAttempt
                        ? `You have an unfinished attempt started on ${new Date(inProgressAttempt.attempt_started_at).toLocaleDateString()}. You can continue anytime.`
                        : canStartNew
                        ? `You have ${attemptLimit - attemptsCount} attempt${attemptLimit - attemptsCount > 1 ? "s" : ""} remaining. Answers are saved as you go.`
                        : "You have completed the maximum number of attempts allowed for this assessment."}
                    </p>
                  </div>

                  <div className="flex-shrink-0">
                    {startAttemptError && (
                      <div className="p-2 mb-2 bg-red-500/10 text-red-600 dark:text-red-400 text-xs rounded-xl border border-red-500/20">
                        {startAttemptError}
                      </div>
                    )}
                    {inProgressAttempt ? (
                      <Button
                        onClick={() => handleStartOrResumeAttempt(inProgressAttempt.attempt_id)}
                        className="bg-amber-600 hover:bg-amber-700 text-white font-semibold rounded-2xl px-6 py-6 shadow-md flex items-center gap-2 text-sm"
                      >
                        <span className="material-symbols-outlined text-[20px]">play_arrow</span>
                        Resume Attempt #{inProgressAttempt.attempt_number}
                      </Button>
                    ) : canStartNew ? (
                      <Button
                        onClick={() => handleStartOrResumeAttempt()}
                        disabled={startingAttempt || questions.length === 0}
                        style={{ backgroundColor: "var(--primary)", color: "var(--on-primary)" }}
                        className="font-semibold rounded-2xl px-8 py-6 shadow-md flex items-center gap-2 text-sm"
                      >
                        {startingAttempt ? (
                          <div className="w-4 h-4 border-2 border-t-transparent border-white rounded-full animate-spin mr-1" />
                        ) : (
                          <span className="material-symbols-outlined text-[20px]">play_arrow</span>
                        )}
                        Start Assessment (Attempt #{attemptsCount + 1})
                      </Button>
                    ) : (
                      <Badge variant="outline" className="px-4 py-2 text-xs font-semibold bg-[var(--surface-container-high)] text-[var(--on-surface-variant)]">
                        No Attempts Remaining
                      </Badge>
                    )}
                  </div>
                </div>
              </div>
            );
          })()}

          {/* Student Performance Self-Analytics (When student has attempts) */}
          {studentSelfAnalytics && studentSelfAnalytics.total_attempts_used > 0 && (
            <div className="bg-[var(--surface-container-lowest)] border border-[var(--outline-variant)] rounded-3xl p-6 shadow-sm space-y-4">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <h3 className="text-base font-bold text-[var(--on-surface)] flex items-center gap-2">
                  <span className="material-symbols-outlined text-[20px] text-[var(--primary)]">insights</span>
                  Your Performance Summary
                </h3>
                {studentSelfAnalytics.has_pending_grading ? (
                  <Badge
                    variant="outline"
                    className="text-xs font-semibold bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20"
                  >
                    Manual Grading Pending
                  </Badge>
                ) : (
                  <Badge
                    variant="outline"
                    className="text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20"
                  >
                    Evaluation Final
                  </Badge>
                )}
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-[var(--surface-container-low)] p-3.5 rounded-2xl border border-[var(--outline-variant)]">
                  <div className="text-xs text-[var(--on-surface-variant)] font-medium">Attempts Used</div>
                  <div className="text-lg font-bold text-[var(--on-surface)] mt-0.5">
                    {studentSelfAnalytics.total_attempts_used} / {studentSelfAnalytics.attempt_limit ?? "∞"}
                  </div>
                  <div className="text-[11px] text-[var(--on-surface-variant)] mt-0.5">
                    {studentSelfAnalytics.attempts_remaining !== null
                      ? `${studentSelfAnalytics.attempts_remaining} remaining`
                      : "Unlimited"}
                  </div>
                </div>

                <div className="bg-[var(--surface-container-low)] p-3.5 rounded-2xl border border-[var(--outline-variant)]">
                  <div className="text-xs text-[var(--on-surface-variant)] font-medium">Best Score</div>
                  <div className="text-lg font-bold text-emerald-600 mt-0.5">
                    {studentSelfAnalytics.best_percentage !== null && studentSelfAnalytics.best_percentage !== undefined
                      ? `${Number(studentSelfAnalytics.best_percentage).toFixed(1)}%`
                      : "N/A"}
                  </div>
                  <div className="text-[11px] text-[var(--on-surface-variant)] mt-0.5">
                    {studentSelfAnalytics.best_obtained_marks !== null && studentSelfAnalytics.best_obtained_marks !== undefined
                      ? `${Number(studentSelfAnalytics.best_obtained_marks).toFixed(1)} / ${Number(studentSelfAnalytics.assessment_total_marks).toFixed(1)} marks`
                      : "Pending"}
                  </div>
                </div>

                <div className="bg-[var(--surface-container-low)] p-3.5 rounded-2xl border border-[var(--outline-variant)]">
                  <div className="text-xs text-[var(--on-surface-variant)] font-medium">Latest Score</div>
                  <div className="text-lg font-bold text-blue-600 mt-0.5">
                    {studentSelfAnalytics.latest_percentage !== null && studentSelfAnalytics.latest_percentage !== undefined
                      ? `${Number(studentSelfAnalytics.latest_percentage).toFixed(1)}%`
                      : "N/A"}
                  </div>
                  <div className="text-[11px] text-[var(--on-surface-variant)] mt-0.5">
                    {studentSelfAnalytics.latest_obtained_marks !== null && studentSelfAnalytics.latest_obtained_marks !== undefined
                      ? `${Number(studentSelfAnalytics.latest_obtained_marks).toFixed(1)} / ${Number(studentSelfAnalytics.assessment_total_marks).toFixed(1)} marks`
                      : "Pending"}
                  </div>
                </div>

                <div className="bg-[var(--surface-container-low)] p-3.5 rounded-2xl border border-[var(--outline-variant)]">
                  <div className="text-xs text-[var(--on-surface-variant)] font-medium">Result Status</div>
                  <div className="text-lg font-bold mt-0.5">
                    {studentSelfAnalytics.passed === true && <span className="text-emerald-600">Passed</span>}
                    {studentSelfAnalytics.passed === false && <span className="text-red-600">Failed</span>}
                    {studentSelfAnalytics.passed === null && <span className="text-amber-600">Provisional</span>}
                  </div>
                  <div className="text-[11px] text-[var(--on-surface-variant)] mt-0.5">
                    {assessment.assessment_passing_marks
                      ? `Pass mark: ${assessment.assessment_passing_marks}`
                      : "No threshold set"}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Attempt History Section */}
          {studentAttempts.length > 0 && (
            <div className="bg-[var(--surface-container-lowest)] border border-[var(--outline-variant)] rounded-3xl p-6 shadow-sm space-y-4">
              <h3 className="text-base font-bold text-[var(--on-surface)] flex items-center gap-2">
                <span className="material-symbols-outlined text-[20px] text-[var(--primary)]">history</span>
                Your Attempts ({studentAttempts.length})
              </h3>

              <div className="space-y-3">
                {studentAttempts.map((att) => (
                  <div
                    key={att.attempt_id}
                    className="p-4 rounded-2xl bg-[var(--surface-container-low)] border border-[var(--outline-variant)] flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-xl bg-blue-500/10 text-blue-600 font-bold flex items-center justify-center text-sm flex-shrink-0">
                        #{att.attempt_number}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-bold text-[var(--on-surface)]">
                            Attempt #{att.attempt_number}
                          </span>
                          {att.attempt_status === "in_progress" ? (
                            <Badge variant="outline" className="bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20 text-xs">
                              In Progress
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 text-xs">
                              Submitted
                            </Badge>
                          )}
                        </div>
                        <div className="text-xs text-[var(--on-surface-variant)] mt-0.5">
                          Started: {new Date(att.attempt_started_at).toLocaleString()}
                          {att.attempt_submitted_at && ` • Submitted: ${new Date(att.attempt_submitted_at).toLocaleString()}`}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className="text-xs font-medium text-[var(--on-surface-variant)]">
                        {att.answers_count} Questions Answered
                      </span>
                      {att.attempt_status === "in_progress" ? (
                        <Button
                          size="sm"
                          onClick={() => router.push(`/classroom/assessments/${assessmentId}/attempt/${att.attempt_id}`)}
                          className="bg-amber-600 hover:bg-amber-700 text-white rounded-xl text-xs font-semibold"
                        >
                          Resume
                        </Button>
                      ) : (
                        <div className="flex items-center gap-2">
                          <Button
                            size="sm"
                            onClick={() => router.push(`/classroom/assessments/${assessmentId}/attempt/${att.attempt_id}/result`)}
                            className="bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-sm"
                          >
                            <span className="material-symbols-outlined text-[16px]">analytics</span>
                            View Result
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => router.push(`/classroom/assessments/${assessmentId}/attempt/${att.attempt_id}`)}
                            className="rounded-xl text-xs font-semibold"
                          >
                            View Answers
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Student Leaderboard Section */}
          {leaderboardData && (
            <div className="bg-[var(--surface-container-lowest)] border border-[var(--outline-variant)] rounded-3xl p-6 shadow-sm space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-[22px] text-amber-500">emoji_events</span>
                  <h3 className="text-base font-bold text-[var(--on-surface)]">
                    Assessment Leaderboard
                  </h3>
                  {leaderboardData.leaderboard_enabled ? (
                    <Badge variant="outline" className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 text-xs">
                      Rankings Live
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="bg-zinc-500/10 text-zinc-500 border-zinc-500/20 text-xs">
                      Disabled
                    </Badge>
                  )}
                </div>
                {leaderboardData.leaderboard_enabled && leaderboardData.my_rank !== null && leaderboardData.my_rank !== undefined && (
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-900 dark:text-amber-200 text-xs font-bold shadow-sm">
                    <span className="material-symbols-outlined text-[16px] text-amber-600 dark:text-amber-400">military_tech</span>
                    <span>Your Rank: #{leaderboardData.my_rank} of {leaderboardData.total_ranked_students}</span>
                  </div>
                )}
              </div>

              {!leaderboardData.leaderboard_enabled ? (
                <div className="p-4 rounded-2xl bg-[var(--surface-container-low)] border border-[var(--outline-variant)] text-center text-xs text-[var(--on-surface-variant)]">
                  Leaderboard rankings are not enabled for this assessment.
                </div>
              ) : leaderboardData.entries.length === 0 ? (
                <div className="p-4 rounded-2xl bg-[var(--surface-container-low)] border border-[var(--outline-variant)] text-center text-xs text-[var(--on-surface-variant)]">
                  No students have completed this assessment yet. Complete an attempt to earn your rank!
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="overflow-x-auto rounded-2xl border border-[var(--outline-variant)]">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-[var(--surface-container-low)] text-[var(--on-surface-variant)] font-semibold border-b border-[var(--outline-variant)]">
                        <tr>
                          <th className="py-2.5 px-3">Rank</th>
                          <th className="py-2.5 px-3">Student</th>
                          <th className="py-2.5 px-3 text-right">Best Score</th>
                          <th className="py-2.5 px-3 text-right">Marks</th>
                          <th className="py-2.5 px-3 text-right">Attempts</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[var(--outline-variant)] bg-[var(--surface-container-lowest)]">
                        {leaderboardData.entries.slice(0, 10).map((entry) => {
                          const isTop1 = entry.rank === 1;
                          const isTop2 = entry.rank === 2;
                          const isTop3 = entry.rank === 3;

                          return (
                            <tr key={`${entry.rank}-${entry.student.id}`} className="hover:bg-[var(--surface-container-low)]/60 transition-colors">
                              <td className="py-2.5 px-3 font-bold">
                                {isTop1 ? (
                                  <span className="inline-flex items-center gap-1 text-amber-500 font-extrabold">🥇 #1</span>
                                ) : isTop2 ? (
                                  <span className="inline-flex items-center gap-1 text-slate-400 font-bold">🥈 #2</span>
                                ) : isTop3 ? (
                                  <span className="inline-flex items-center gap-1 text-amber-700 dark:text-amber-600 font-bold">🥉 #3</span>
                                ) : (
                                  <span className="text-[var(--on-surface-variant)] font-medium">#{entry.rank}</span>
                                )}
                              </td>
                              <td className="py-2.5 px-3">
                                <div className="flex items-center gap-2">
                                  <div className="w-6 h-6 rounded-full bg-[var(--primary)]/10 text-[var(--primary)] font-bold text-[10px] flex items-center justify-center flex-shrink-0">
                                    {entry.student.display_name.slice(0, 1).toUpperCase()}
                                  </div>
                                  <span className="font-semibold text-[var(--on-surface)]">
                                    {entry.student.display_name}
                                  </span>
                                </div>
                              </td>
                              <td className="py-2.5 px-3 text-right font-bold text-emerald-600">
                                {Number(entry.percentage).toFixed(1)}%
                              </td>
                              <td className="py-2.5 px-3 text-right text-[var(--on-surface-variant)] font-medium">
                                {Number(entry.obtained_marks).toFixed(1)}
                              </td>
                              <td className="py-2.5 px-3 text-right text-[var(--on-surface-variant)]">
                                {entry.attempts_used}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                  {leaderboardData.total_ranked_students > 10 && (
                    <p className="text-[11px] text-[var(--on-surface-variant)] text-center pt-1">
                      Showing top 10 of {leaderboardData.total_ranked_students} ranked participants.
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Instructions & Details */}
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
        </div>
      ) : (
        /* ── TEACHER / ADMIN BUILDER TABS ── */
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="bg-[var(--surface-container-low)] border border-[var(--outline-variant)] p-1.5 rounded-2xl h-auto w-full flex-wrap sm:flex-nowrap overflow-x-auto justify-start gap-1 custom-scrollbar">
            <TabsTrigger value="builder" className="rounded-xl px-3.5 py-2 text-xs font-semibold data-[state=active]:bg-[var(--primary)] data-[state=active]:text-[var(--on-primary)] transition-all flex-shrink-0">
              <span className="material-symbols-outlined text-[16px] mr-1.5">quiz</span>
              Questions ({questions.length})
            </TabsTrigger>
            <TabsTrigger value="submissions" className="rounded-xl px-3.5 py-2 text-xs font-semibold data-[state=active]:bg-[var(--primary)] data-[state=active]:text-[var(--on-primary)] transition-all flex-shrink-0">
              <span className="material-symbols-outlined text-[16px] mr-1.5">fact_check</span>
              Submissions ({submissions.length})
            </TabsTrigger>
            <TabsTrigger value="analytics" className="rounded-xl px-3.5 py-2 text-xs font-semibold data-[state=active]:bg-[var(--primary)] data-[state=active]:text-[var(--on-primary)] transition-all flex-shrink-0">
              <span className="material-symbols-outlined text-[16px] mr-1.5">insights</span>
              Analytics
            </TabsTrigger>
            <TabsTrigger value="leaderboard" className="rounded-xl px-3.5 py-2 text-xs font-semibold data-[state=active]:bg-[var(--primary)] data-[state=active]:text-[var(--on-primary)] transition-all flex-shrink-0">
              <span className="material-symbols-outlined text-[16px] mr-1.5">emoji_events</span>
              Leaderboard
            </TabsTrigger>
            <TabsTrigger value="preview" className="rounded-xl px-3.5 py-2 text-xs font-semibold data-[state=active]:bg-[var(--primary)] data-[state=active]:text-[var(--on-primary)] transition-all flex-shrink-0">
              <span className="material-symbols-outlined text-[16px] mr-1.5">visibility</span>
              Preview
            </TabsTrigger>
            <TabsTrigger value="settings" className="rounded-xl px-3.5 py-2 text-xs font-semibold data-[state=active]:bg-[var(--primary)] data-[state=active]:text-[var(--on-primary)] transition-all flex-shrink-0">
              <span className="material-symbols-outlined text-[16px] mr-1.5">settings</span>
              Settings
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

              {/* Leaderboard Config */}
              <div className="p-4 rounded-2xl bg-[var(--surface-container-low)] border border-[var(--outline-variant)] flex items-start gap-3">
                <input
                  type="checkbox"
                  id="settings-leaderboard"
                  checked={settingsLeaderboardEnabled}
                  onChange={(e) => setSettingsLeaderboardEnabled(e.target.checked)}
                  className="mt-1 w-4 h-4 text-[var(--primary)] rounded border-[var(--outline-variant)]"
                />
                <div>
                  <Label htmlFor="settings-leaderboard" className="text-sm font-semibold text-[var(--on-surface)] cursor-pointer">
                    Enable Assessment Leaderboard & Ranking
                  </Label>
                  <p className="text-xs text-[var(--on-surface-variant)] mt-0.5 leading-relaxed">
                    When enabled, students with completed results will be ranked using their best completed score. Students can view their personal rank and top leaderboard standings.
                  </p>
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

        {/* ── TAB 4: SUBMISSIONS & GRADING ──────────────────────────── */}
        <TabsContent value="submissions" className="space-y-6 outline-none">
          {/* Submissions Overview Metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-[var(--surface-container-low)] p-4 rounded-2xl border border-[var(--outline-variant)] flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-blue-500/10 text-blue-600 flex items-center justify-center flex-shrink-0">
                <span className="material-symbols-outlined text-[20px]">assignment</span>
              </div>
              <div>
                <div className="text-xs text-[var(--on-surface-variant)] font-medium">Submissions</div>
                <div className="text-lg font-bold text-[var(--on-surface)]">{submissions.length}</div>
              </div>
            </div>

            <div className="bg-[var(--surface-container-low)] p-4 rounded-2xl border border-[var(--outline-variant)] flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-600 flex items-center justify-center flex-shrink-0">
                <span className="material-symbols-outlined text-[20px]">check_circle</span>
              </div>
              <div>
                <div className="text-xs text-[var(--on-surface-variant)] font-medium">Fully Graded</div>
                <div className="text-lg font-bold text-emerald-600">
                  {submissions.filter((s) => s.status === "completed").length}
                </div>
              </div>
            </div>

            <div className="bg-[var(--surface-container-low)] p-4 rounded-2xl border border-[var(--outline-variant)] flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-600 flex items-center justify-center flex-shrink-0">
                <span className="material-symbols-outlined text-[20px]">pending_actions</span>
              </div>
              <div>
                <div className="text-xs text-[var(--on-surface-variant)] font-medium">Pending Review</div>
                <div className="text-lg font-bold text-amber-600">
                  {submissions.filter((s) => s.status === "pending_manual_grading" || s.pending_count > 0).length}
                </div>
              </div>
            </div>

            <div className="bg-[var(--surface-container-low)] p-4 rounded-2xl border border-[var(--outline-variant)] flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-purple-500/10 text-purple-600 flex items-center justify-center flex-shrink-0">
                <span className="material-symbols-outlined text-[20px]">percent</span>
              </div>
              <div>
                <div className="text-xs text-[var(--on-surface-variant)] font-medium">Pass Rate</div>
                <div className="text-lg font-bold text-[var(--on-surface)]">
                  {(() => {
                    const completed = submissions.filter((s) => s.status === "completed" && s.passed !== null);
                    if (completed.length === 0) return "N/A";
                    const passedCount = completed.filter((s) => s.passed === true).length;
                    return `${Math.round((passedCount / completed.length) * 100)}%`;
                  })()}
                </div>
              </div>
            </div>
          </div>

          {/* Submissions List */}
          <div className="bg-[var(--surface-container-lowest)] border border-[var(--outline-variant)] rounded-3xl p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-[var(--on-surface)]">
                  Student Submissions ({submissions.length})
                </h3>
                <p className="text-xs text-[var(--on-surface-variant)]">
                  Review student answers, evaluate pending short-answer questions, and inspect automated scores.
                </p>
              </div>

              <Button
                variant="outline"
                size="sm"
                onClick={async () => {
                  setLoadingSubmissions(true);
                  try {
                    const subs = await fetchAssessmentResults(assessmentId);
                    setSubmissions(subs);
                  } finally {
                    setLoadingSubmissions(false);
                  }
                }}
                disabled={loadingSubmissions}
                className="rounded-xl text-xs flex items-center gap-1.5"
              >
                <span className={`material-symbols-outlined text-[16px] ${loadingSubmissions ? "animate-spin" : ""}`}>
                  sync
                </span>
                Refresh
              </Button>
            </div>

            {submissions.length === 0 ? (
              <div className="text-center py-16 px-4 rounded-2xl border border-dashed border-[var(--outline-variant)] bg-[var(--surface-container-low)]">
                <span className="material-symbols-outlined text-[42px] text-[var(--on-surface-variant)] opacity-40 mb-2 block">
                  inbox
                </span>
                <p className="text-sm font-semibold text-[var(--on-surface)]">No student submissions yet</p>
                <p className="text-xs text-[var(--on-surface-variant)] mt-1">
                  When students complete or submit their attempts, their evaluations will appear here.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {submissions.map((sub) => {
                  const hasPending = sub.status === "pending_manual_grading" || sub.pending_count > 0;
                  return (
                    <div
                      key={sub.attempt_id}
                      className="p-4 rounded-2xl bg-[var(--surface-container-low)] border border-[var(--outline-variant)] flex flex-col md:flex-row md:items-center justify-between gap-4 hover:border-[var(--primary)]/40 transition-all"
                    >
                      {/* Student Info */}
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-2xl bg-[var(--primary)]/10 text-[var(--primary)] font-bold flex items-center justify-center text-sm flex-shrink-0 shadow-inner">
                          {sub.student_name ? sub.student_name.slice(0, 2).toUpperCase() : "ST"}
                        </div>
                        <div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-sm font-bold text-[var(--on-surface)]">
                              {sub.student_name || "Student"}
                            </span>
                            <span className="text-xs font-semibold px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-600 dark:text-blue-400">
                              Attempt #{sub.attempt_number}
                            </span>
                            {hasPending ? (
                              <Badge variant="outline" className="bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20 text-xs flex items-center gap-1">
                                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
                                {sub.pending_count} Pending Review
                              </Badge>
                            ) : (
                              <Badge variant="outline" className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 text-xs">
                                Graded
                              </Badge>
                            )}
                          </div>
                          <div className="text-xs text-[var(--on-surface-variant)] mt-0.5 flex items-center gap-2">
                            <span>{sub.student_email || "No email"}</span>
                            <span>•</span>
                            <span>
                              {sub.submitted_at
                                ? `Submitted: ${new Date(sub.submitted_at).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}`
                                : `Started: ${new Date(sub.started_at).toLocaleString([], { month: "short", day: "numeric" })}`}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Marks and Score */}
                      <div className="flex items-center gap-4 self-end md:self-center">
                        <div className="text-right">
                          <div className="text-sm font-bold text-[var(--on-surface)]">
                            {Number(sub.obtained_marks).toFixed(1)} / {Number(sub.total_marks).toFixed(1)}
                            <span className="text-xs text-[var(--on-surface-variant)] ml-1 font-normal">
                              ({Number(sub.percentage).toFixed(1)}%)
                            </span>
                          </div>
                          <div className="text-xs mt-0.5 font-semibold">
                            {sub.passed === true && <span className="text-emerald-600">Passed</span>}
                            {sub.passed === false && <span className="text-red-600">Failed</span>}
                            {sub.passed === null && <span className="text-amber-600">Provisional</span>}
                          </div>
                        </div>

                        {/* Action: Review / Grade */}
                        <Button
                          size="sm"
                          onClick={() => router.push(`/classroom/assessments/${assessmentId}/attempt/${sub.attempt_id}/result`)}
                          className={`rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-sm ${
                            hasPending
                              ? "bg-amber-600 hover:bg-amber-700 text-white"
                              : "bg-[var(--primary)] text-[var(--on-primary)]"
                          }`}
                        >
                          <span className="material-symbols-outlined text-[16px]">
                            {hasPending ? "draw" : "visibility"}
                          </span>
                          {hasPending ? "Grade Short Answers" : "Review Result"}
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </TabsContent>

        {/* ── TAB 5: ANALYTICS & INSIGHTS ───────────────────────────── */}
        <TabsContent value="analytics" className="space-y-6 outline-none">
          {/* Header & Refresh */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[var(--surface-container-low)] p-4 rounded-2xl border border-[var(--outline-variant)]">
            <div className="space-y-0.5">
              <h3 className="text-base font-bold text-[var(--on-surface)] flex items-center gap-2">
                <span className="material-symbols-outlined text-[20px] text-[var(--primary)]">insights</span>
                Assessment Analytics & Insights
              </h3>
              <p className="text-xs text-[var(--on-surface-variant)]">
                Class-wide evaluation metrics, accuracy breakdowns, and student performance matrix.
              </p>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={async () => {
                setLoadingAnalytics(true);
                try {
                  const data = await fetchAssessmentAnalytics(assessmentId);
                  setAnalyticsData(data);
                } finally {
                  setLoadingAnalytics(false);
                }
              }}
              disabled={loadingAnalytics}
              className="rounded-xl text-xs flex items-center gap-1.5 self-start sm:self-auto"
            >
              <span className={`material-symbols-outlined text-[16px] ${loadingAnalytics ? "animate-spin" : ""}`}>
                sync
              </span>
              Refresh Analytics
            </Button>
          </div>

          {loadingAnalytics && !analyticsData ? (
            <div className="flex items-center justify-center py-16">
              <div className="flex items-center gap-3 text-sm font-semibold text-[var(--on-surface-variant)]">
                <div className="w-6 h-6 border-2 border-t-transparent border-[var(--primary)] rounded-full animate-spin" />
                Computing assessment analytics...
              </div>
            </div>
          ) : !analyticsData || analyticsData.overview.total_students_attempted === 0 ? (
            <div className="text-center py-16 px-4 rounded-3xl border border-dashed border-[var(--outline-variant)] bg-[var(--surface-container-lowest)]">
              <span className="material-symbols-outlined text-[48px] text-[var(--on-surface-variant)] opacity-40 mb-3 block">
                analytics
              </span>
              <h3 className="text-base font-semibold text-[var(--on-surface)]">No Analytics Data Available Yet</h3>
              <p className="text-xs sm:text-sm text-[var(--on-surface-variant)] mt-1 max-w-md mx-auto">
                Once students begin and submit attempts for this assessment, comprehensive participation and score statistics will appear here.
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* 4-Card Overview KPIs */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-[var(--surface-container-lowest)] p-5 rounded-2xl border border-[var(--outline-variant)] shadow-sm space-y-2">
                  <div className="flex items-center justify-between text-[var(--on-surface-variant)]">
                    <span className="text-xs font-semibold uppercase tracking-wider">Participation</span>
                    <span className="material-symbols-outlined text-[20px] text-blue-500">groups</span>
                  </div>
                  <div className="text-2xl font-black text-[var(--on-surface)]">
                    {analyticsData.overview.participation_rate !== null && analyticsData.overview.participation_rate !== undefined
                      ? `${analyticsData.overview.participation_rate}%`
                      : "0%"}
                  </div>
                  <div className="text-xs text-[var(--on-surface-variant)]">
                    {analyticsData.overview.total_students_attempted} of {analyticsData.overview.total_enrolled_students} enrolled students
                  </div>
                </div>

                <div className="bg-[var(--surface-container-lowest)] p-5 rounded-2xl border border-[var(--outline-variant)] shadow-sm space-y-2">
                  <div className="flex items-center justify-between text-[var(--on-surface-variant)]">
                    <span className="text-xs font-semibold uppercase tracking-wider">Average Score</span>
                    <span className="material-symbols-outlined text-[20px] text-purple-500">calculate</span>
                  </div>
                  <div className="text-2xl font-black text-purple-600 dark:text-purple-400">
                    {analyticsData.score_statistics.average_percentage !== null && analyticsData.score_statistics.average_percentage !== undefined
                      ? `${analyticsData.score_statistics.average_percentage}%`
                      : "N/A"}
                  </div>
                  <div className="text-xs text-[var(--on-surface-variant)]">
                    Mean: {analyticsData.score_statistics.average_obtained_marks !== null && analyticsData.score_statistics.average_obtained_marks !== undefined
                      ? `${analyticsData.score_statistics.average_obtained_marks} / ${analyticsData.score_statistics.total_marks}`
                      : "Pending"}
                  </div>
                </div>

                <div className="bg-[var(--surface-container-lowest)] p-5 rounded-2xl border border-[var(--outline-variant)] shadow-sm space-y-2">
                  <div className="flex items-center justify-between text-[var(--on-surface-variant)]">
                    <span className="text-xs font-semibold uppercase tracking-wider">Median Score</span>
                    <span className="material-symbols-outlined text-[20px] text-sky-500">show_chart</span>
                  </div>
                  <div className="text-2xl font-black text-sky-600 dark:text-sky-400">
                    {analyticsData.score_statistics.median_percentage !== null && analyticsData.score_statistics.median_percentage !== undefined
                      ? `${analyticsData.score_statistics.median_percentage}%`
                      : "N/A"}
                  </div>
                  <div className="text-xs text-[var(--on-surface-variant)]">
                    Median benchmark score
                  </div>
                </div>

                <div className="bg-[var(--surface-container-lowest)] p-5 rounded-2xl border border-[var(--outline-variant)] shadow-sm space-y-2">
                  <div className="flex items-center justify-between text-[var(--on-surface-variant)]">
                    <span className="text-xs font-semibold uppercase tracking-wider">Class Pass Rate</span>
                    <span className="material-symbols-outlined text-[20px] text-emerald-500">verified</span>
                  </div>
                  <div className="text-2xl font-black text-emerald-600 dark:text-emerald-400">
                    {analyticsData.overview.pass_percentage !== null && analyticsData.overview.pass_percentage !== undefined
                      ? `${analyticsData.overview.pass_percentage}%`
                      : "N/A"}
                  </div>
                  <div className="text-xs text-[var(--on-surface-variant)]">
                    {analyticsData.overview.total_passed} passed • {analyticsData.overview.total_failed} failed
                  </div>
                </div>
              </div>

              {/* Score Statistics & Attempt Metrics Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Score Statistics */}
                <div className="bg-[var(--surface-container-lowest)] border border-[var(--outline-variant)] rounded-3xl p-6 shadow-sm space-y-4">
                  <h4 className="text-sm font-bold text-[var(--on-surface)] flex items-center gap-2">
                    <span className="material-symbols-outlined text-[18px] text-[var(--primary)]">bar_chart</span>
                    Score Extremes & Criteria
                  </h4>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3.5 rounded-2xl bg-[var(--surface-container-low)] border border-[var(--outline-variant)]">
                      <div className="text-xs text-[var(--on-surface-variant)] font-medium">Highest Score</div>
                      <div className="text-lg font-bold text-emerald-600 mt-1">
                        {analyticsData.score_statistics.highest_percentage !== null && analyticsData.score_statistics.highest_percentage !== undefined
                          ? `${analyticsData.score_statistics.highest_percentage}%`
                          : "N/A"}
                      </div>
                      <div className="text-[11px] text-[var(--on-surface-variant)]">
                        Max recorded score
                      </div>
                    </div>

                    <div className="p-3.5 rounded-2xl bg-[var(--surface-container-low)] border border-[var(--outline-variant)]">
                      <div className="text-xs text-[var(--on-surface-variant)] font-medium">Lowest Score</div>
                      <div className="text-lg font-bold text-red-600 mt-1">
                        {analyticsData.score_statistics.lowest_percentage !== null && analyticsData.score_statistics.lowest_percentage !== undefined
                          ? `${analyticsData.score_statistics.lowest_percentage}%`
                          : "N/A"}
                      </div>
                      <div className="text-[11px] text-[var(--on-surface-variant)]">
                        Min recorded score
                      </div>
                    </div>

                    <div className="p-3.5 rounded-2xl bg-[var(--surface-container-low)] border border-[var(--outline-variant)]">
                      <div className="text-xs text-[var(--on-surface-variant)] font-medium">Passing Threshold</div>
                      <div className="text-lg font-bold text-[var(--on-surface)] mt-1">
                        {analyticsData.score_statistics.passing_marks !== null && analyticsData.score_statistics.passing_marks !== undefined
                          ? `${analyticsData.score_statistics.passing_marks} marks`
                          : "None"}
                      </div>
                      <div className="text-[11px] text-[var(--on-surface-variant)]">
                        {assessment.assessment_passing_marks ? `Set at ${assessment.assessment_passing_marks}` : "No cutoff configured"}
                      </div>
                    </div>

                    <div className="p-3.5 rounded-2xl bg-[var(--surface-container-low)] border border-[var(--outline-variant)]">
                      <div className="text-xs text-[var(--on-surface-variant)] font-medium">Passing Distribution</div>
                      <div className="text-sm font-bold text-[var(--on-surface)] mt-1 flex items-center gap-1.5">
                        <span className="text-emerald-600">{analyticsData.overview.total_passed} Passed</span>
                        <span>/</span>
                        <span className="text-red-600">{analyticsData.overview.total_failed} Failed</span>
                      </div>
                      <div className="text-[11px] text-[var(--on-surface-variant)]">
                        {analyticsData.overview.total_pending_manual_grading > 0
                          ? `${analyticsData.overview.total_pending_manual_grading} pending review`
                          : "All evaluated"}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Attempt Statistics */}
                <div className="bg-[var(--surface-container-lowest)] border border-[var(--outline-variant)] rounded-3xl p-6 shadow-sm space-y-4">
                  <h4 className="text-sm font-bold text-[var(--on-surface)] flex items-center gap-2">
                    <span className="material-symbols-outlined text-[18px] text-[var(--primary)]">repeat</span>
                    Attempt Distribution & Grading
                  </h4>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3.5 rounded-2xl bg-[var(--surface-container-low)] border border-[var(--outline-variant)]">
                      <div className="text-xs text-[var(--on-surface-variant)] font-medium">Total Attempts</div>
                      <div className="text-lg font-bold text-[var(--on-surface)] mt-1">
                        {analyticsData.attempt_statistics.total_attempts}
                      </div>
                      <div className="text-[11px] text-[var(--on-surface-variant)]">
                        Across {analyticsData.overview.total_students_attempted} students
                      </div>
                    </div>

                    <div className="p-3.5 rounded-2xl bg-[var(--surface-container-low)] border border-[var(--outline-variant)]">
                      <div className="text-xs text-[var(--on-surface-variant)] font-medium">Avg Attempts / Student</div>
                      <div className="text-lg font-bold text-[var(--on-surface)] mt-1">
                        {analyticsData.attempt_statistics.average_attempts_per_student !== null && analyticsData.attempt_statistics.average_attempts_per_student !== undefined
                          ? analyticsData.attempt_statistics.average_attempts_per_student
                          : "0"}
                      </div>
                      <div className="text-[11px] text-[var(--on-surface-variant)]">
                        Limit: {assessment.assessment_attempt_limit || 1} allowed
                      </div>
                    </div>

                    <div className="p-3.5 rounded-2xl bg-[var(--surface-container-low)] border border-[var(--outline-variant)]">
                      <div className="text-xs text-[var(--on-surface-variant)] font-medium">Graded Submissions</div>
                      <div className="text-lg font-bold text-emerald-600 mt-1">
                        {analyticsData.overview.total_completed_evaluations}
                      </div>
                      <div className="text-[11px] text-[var(--on-surface-variant)]">
                        Final score computed
                      </div>
                    </div>

                    <div className="p-3.5 rounded-2xl bg-[var(--surface-container-low)] border border-[var(--outline-variant)]">
                      <div className="text-xs text-[var(--on-surface-variant)] font-medium">Pending Manual Grading</div>
                      <div className="text-lg font-bold text-amber-600 mt-1">
                        {analyticsData.overview.total_pending_manual_grading}
                      </div>
                      <div className="text-[11px] text-[var(--on-surface-variant)]">
                        Awaiting teacher review
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Question Accuracy & Performance Breakdown */}
              <div className="bg-[var(--surface-container-lowest)] border border-[var(--outline-variant)] rounded-3xl p-6 shadow-sm space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div>
                    <h4 className="text-base font-bold text-[var(--on-surface)] flex items-center gap-2">
                      <span className="material-symbols-outlined text-[20px] text-[var(--primary)]">rule</span>
                      Question Accuracy Analysis ({analyticsData.question_statistics.length} questions)
                    </h4>
                    <p className="text-xs text-[var(--on-surface-variant)]">
                      Identify difficult questions, common misconceptions, and accuracy rates across student attempts.
                    </p>
                  </div>
                </div>

                <div className="space-y-3">
                  {analyticsData.question_statistics.map((qa: AssessmentQuestionAnalyticsItem) => {
                    const accuracy = qa.accuracy_percentage;
                    let accuracyColor = "text-emerald-600 bg-emerald-500/10 border-emerald-500/20";
                    let progressColor = "bg-emerald-500";
                    if (accuracy !== null && accuracy !== undefined) {
                      if (accuracy < 40) {
                        accuracyColor = "text-red-600 bg-red-500/10 border-red-500/20";
                        progressColor = "bg-red-500";
                      } else if (accuracy < 70) {
                        accuracyColor = "text-amber-600 bg-amber-500/10 border-amber-500/20";
                        progressColor = "bg-amber-500";
                      }
                    }

                    return (
                      <div
                        key={qa.assessment_question_id}
                        className="p-4 rounded-2xl bg-[var(--surface-container-low)] border border-[var(--outline-variant)] space-y-3"
                      >
                        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                          <div className="space-y-1.5 flex-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="text-xs font-bold px-2 py-0.5 rounded-md bg-[var(--surface-container-high)] text-[var(--on-surface)]">
                                Q{qa.question_order}
                              </span>
                              {getQuestionTypeBadge(qa.question_type)}
                              <span className="text-xs text-[var(--on-surface-variant)]">
                                Max Marks: {qa.marks_available}
                              </span>
                            </div>
                            <p className="text-sm font-semibold text-[var(--on-surface)] line-clamp-2">
                              {qa.question_text}
                            </p>
                          </div>

                          <div className="flex sm:flex-col items-center sm:items-end justify-between gap-2 flex-shrink-0">
                            <div className={`px-3 py-1 rounded-xl text-xs font-bold border ${accuracyColor}`}>
                              {accuracy !== null && accuracy !== undefined ? `${accuracy}% Accuracy` : "Pending Grading"}
                            </div>
                            <div className="text-xs text-[var(--on-surface-variant)]">
                              Avg: {qa.average_marks_awarded !== null && qa.average_marks_awarded !== undefined
                                ? `${qa.average_marks_awarded} / ${qa.marks_available}`
                                : "N/A"}
                            </div>
                          </div>
                        </div>

                        {/* Visual Accuracy Bar */}
                        {accuracy !== null && accuracy !== undefined && (
                          <div className="w-full bg-[var(--surface-container-high)] h-2 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all ${progressColor}`}
                              style={{ width: `${Math.min(100, Math.max(0, accuracy))}%` }}
                            />
                          </div>
                        )}

                        {/* Response Breakdown Badges */}
                        <div className="flex items-center gap-2 flex-wrap text-xs pt-1 border-t border-[var(--outline-variant)]">
                          <span className="inline-flex items-center gap-1 font-medium text-emerald-600 dark:text-emerald-400">
                            <span className="w-2 h-2 rounded-full bg-emerald-500" />
                            {qa.correct_count} Correct
                          </span>
                          <span className="text-[var(--outline)]">•</span>
                          <span className="inline-flex items-center gap-1 font-medium text-red-600 dark:text-red-400">
                            <span className="w-2 h-2 rounded-full bg-red-500" />
                            {qa.incorrect_count} Incorrect
                          </span>
                          <span className="text-[var(--outline)]">•</span>
                          <span className="inline-flex items-center gap-1 font-medium text-[var(--on-surface-variant)]">
                            <span className="w-2 h-2 rounded-full bg-zinc-400" />
                            {qa.unanswered_count} Unanswered
                          </span>
                          {qa.pending_count > 0 && (
                            <>
                              <span className="text-[var(--outline)]">•</span>
                              <span className="inline-flex items-center gap-1 font-medium text-amber-600 dark:text-amber-400">
                                <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                                {qa.pending_count} Pending Review
                              </span>
                            </>
                          )}
                          <span className="text-[var(--outline)]">•</span>
                          <span className="text-[var(--on-surface-variant)] font-medium">
                            Evaluated Attempts: {qa.evaluated_count}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Student Performance Matrix */}
              <div className="bg-[var(--surface-container-lowest)] border border-[var(--outline-variant)] rounded-3xl p-6 shadow-sm space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <h4 className="text-base font-bold text-[var(--on-surface)] flex items-center gap-2">
                      <span className="material-symbols-outlined text-[20px] text-[var(--primary)]">leaderboard</span>
                      Student Performance Matrix ({analyticsData.student_statistics.length} students)
                    </h4>
                    <p className="text-xs text-[var(--on-surface-variant)]">
                      Student attempt progression, best vs latest scores, and individual evaluation links.
                    </p>
                  </div>

                  {/* Search Filter */}
                  <div className="relative w-full sm:w-64">
                    <span className="material-symbols-outlined absolute left-3 top-2.5 text-[16px] text-[var(--on-surface-variant)]">
                      search
                    </span>
                    <Input
                      type="text"
                      placeholder="Search student name or email..."
                      value={studentSearch}
                      onChange={(e) => setStudentSearch(e.target.value)}
                      className="pl-8 h-9 text-xs bg-[var(--surface-container-low)]"
                    />
                  </div>
                </div>

                {/* Performance Matrix Table */}
                {(() => {
                  const filteredStudents = analyticsData.student_statistics.filter((sp: AssessmentStudentPerformanceItem) => {
                    const q = studentSearch.toLowerCase().trim();
                    if (!q) return true;
                    return (
                      (sp.student_name && sp.student_name.toLowerCase().includes(q)) ||
                      (sp.student_email && sp.student_email.toLowerCase().includes(q))
                    );
                  });

                  if (filteredStudents.length === 0) {
                    return (
                      <p className="text-center text-xs text-[var(--on-surface-variant)] py-8">
                        No students match the search filter.
                      </p>
                    );
                  }

                  return (
                    <div className="space-y-3">
                      {filteredStudents.map((sp: AssessmentStudentPerformanceItem) => {
                        const latestAttempt = sp.attempts && sp.attempts.length > 0 ? sp.attempts[sp.attempts.length - 1] : null;

                        return (
                          <div
                            key={sp.student_id}
                            className="p-4 rounded-2xl bg-[var(--surface-container-low)] border border-[var(--outline-variant)] flex flex-col md:flex-row md:items-center justify-between gap-4 hover:border-[var(--primary)]/40 transition-all"
                          >
                            <div className="flex items-center gap-3">
                              <div className="w-10 h-10 rounded-2xl bg-[var(--primary)]/10 text-[var(--primary)] font-bold flex items-center justify-center text-sm flex-shrink-0 shadow-inner">
                                {sp.student_name ? sp.student_name.slice(0, 2).toUpperCase() : "ST"}
                              </div>
                              <div>
                                <div className="flex items-center gap-2 flex-wrap">
                                  <span className="text-sm font-bold text-[var(--on-surface)]">
                                    {sp.student_name || "Student"}
                                  </span>
                                  <Badge variant="outline" className="bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20 text-xs">
                                    {sp.total_attempts} {sp.total_attempts === 1 ? "Attempt" : "Attempts"}
                                  </Badge>
                                  {sp.has_pending_grading ? (
                                    <Badge variant="outline" className="bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20 text-xs">
                                      Pending Review
                                    </Badge>
                                  ) : sp.latest_passed === true ? (
                                    <Badge variant="outline" className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 text-xs">
                                      Passed
                                    </Badge>
                                  ) : sp.latest_passed === false ? (
                                    <Badge variant="outline" className="bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20 text-xs">
                                      Failed
                                    </Badge>
                                  ) : null}
                                </div>
                                <div className="text-xs text-[var(--on-surface-variant)] mt-0.5">
                                  {sp.student_email || "No email"}
                                </div>
                              </div>
                            </div>

                            <div className="flex items-center gap-4 self-end md:self-center">
                              {/* Score comparison */}
                              <div className="flex items-center gap-4 text-right">
                                <div>
                                  <div className="text-[11px] font-semibold text-[var(--on-surface-variant)] uppercase tracking-wider">
                                    Latest Score
                                  </div>
                                  <div className="text-sm font-bold text-[var(--on-surface)]">
                                    {sp.latest_percentage !== null && sp.latest_percentage !== undefined
                                      ? `${sp.latest_percentage}%`
                                      : "Pending"}
                                  </div>
                                  <div className="text-[11px] text-[var(--on-surface-variant)]">
                                    {sp.latest_obtained_marks !== null && sp.latest_obtained_marks !== undefined
                                      ? `${sp.latest_obtained_marks} / ${analyticsData.score_statistics.total_marks}`
                                      : ""}
                                  </div>
                                </div>

                                <div className="border-l border-[var(--outline-variant)] pl-4">
                                  <div className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">
                                    Best Score
                                  </div>
                                  <div className="text-sm font-bold text-emerald-600 dark:text-emerald-400">
                                    {sp.best_percentage !== null && sp.best_percentage !== undefined
                                      ? `${sp.best_percentage}%`
                                      : "Pending"}
                                  </div>
                                  <div className="text-[11px] text-[var(--on-surface-variant)]">
                                    {sp.best_obtained_marks !== null && sp.best_obtained_marks !== undefined
                                      ? `${sp.best_obtained_marks} / ${analyticsData.score_statistics.total_marks}`
                                      : ""}
                                  </div>
                                </div>
                              </div>

                              {/* Action to review latest attempt */}
                              {latestAttempt && (
                                <Button
                                  size="sm"
                                  onClick={() => router.push(`/classroom/assessments/${assessmentId}/attempt/${latestAttempt.attempt_id}/result`)}
                                  className="rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-sm bg-[var(--primary)] text-[var(--on-primary)]"
                                >
                                  <span className="material-symbols-outlined text-[16px]">
                                    {sp.has_pending_grading ? "draw" : "visibility"}
                                  </span>
                                  {sp.has_pending_grading ? "Grade" : "Review"}
                                </Button>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  );
                })()}
              </div>
            </div>
          )}
        </TabsContent>

        {/* ── TAB 6: LEADERBOARD & RANKINGS ─────────────────────────── */}
        <TabsContent value="leaderboard" className="space-y-6 outline-none">
          {/* Header Card & Toggle */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[var(--surface-container-low)] p-6 rounded-3xl border border-[var(--outline-variant)]">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[24px] text-amber-500">emoji_events</span>
                <h3 className="text-lg font-bold text-[var(--on-surface)]">
                  Assessment Leaderboard & Rankings
                </h3>
                {assessment.assessment_leaderboard_enabled ? (
                  <Badge variant="outline" className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 text-xs">
                    Leaderboard Active
                  </Badge>
                ) : (
                  <Badge variant="outline" className="bg-zinc-500/10 text-zinc-500 border-zinc-500/20 text-xs">
                    Disabled
                  </Badge>
                )}
              </div>
              <p className="text-xs text-[var(--on-surface-variant)] max-w-xl">
                Deterministic competition ranking ("1-2-2-4") using each student's best completed score. Uncompleted or pending manual grading attempts are excluded from rankings until evaluated.
              </p>
            </div>

            <div className="flex items-center gap-2 self-start sm:self-auto flex-shrink-0">
              <Button
                size="sm"
                variant={assessment.assessment_leaderboard_enabled ? "outline" : "default"}
                onClick={() => handleToggleLeaderboard(!assessment.assessment_leaderboard_enabled)}
                disabled={togglingLeaderboard}
                className={`rounded-2xl px-5 py-2.5 text-xs font-bold flex items-center gap-2 shadow-sm transition-all ${
                  !assessment.assessment_leaderboard_enabled
                    ? "bg-amber-600 hover:bg-amber-700 text-white"
                    : "border-[var(--outline-variant)] text-[var(--on-surface)]"
                }`}
              >
                {togglingLeaderboard && <div className="w-3.5 h-3.5 border-2 border-t-transparent border-current rounded-full animate-spin" />}
                <span className="material-symbols-outlined text-[18px]">
                  {assessment.assessment_leaderboard_enabled ? "visibility_off" : "military_tech"}
                </span>
                {assessment.assessment_leaderboard_enabled ? "Disable Leaderboard" : "Enable Leaderboard"}
              </Button>
            </div>
          </div>

          {!assessment.assessment_leaderboard_enabled ? (
            <div className="text-center py-16 px-6 rounded-3xl border border-dashed border-[var(--outline-variant)] bg-[var(--surface-container-low)] space-y-3">
              <div className="w-14 h-14 rounded-2xl bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center mx-auto">
                <span className="material-symbols-outlined text-[32px]">military_tech</span>
              </div>
              <h4 className="text-base font-bold text-[var(--on-surface)]">Leaderboard is Disabled</h4>
              <p className="text-xs text-[var(--on-surface-variant)] max-w-md mx-auto">
                Rankings are currently hidden from students. Enable the leaderboard whenever you are ready to publish rankings.
              </p>
              <Button
                size="sm"
                onClick={() => handleToggleLeaderboard(true)}
                disabled={togglingLeaderboard}
                style={{ backgroundColor: "var(--primary)", color: "var(--on-primary)" }}
                className="rounded-xl px-5 py-2 text-xs font-semibold shadow-sm mt-2"
              >
                Enable for This Assessment
              </Button>
            </div>
          ) : loadingLeaderboard ? (
            <div className="flex items-center justify-center py-16">
              <div className="flex items-center gap-3 text-xs font-semibold text-[var(--on-surface-variant)]">
                <div className="w-5 h-5 border-2 border-t-transparent border-[var(--primary)] rounded-full animate-spin" />
                Loading rankings...
              </div>
            </div>
          ) : !leaderboardData || leaderboardData.entries.length === 0 ? (
            <div className="text-center py-16 px-6 rounded-3xl border border-dashed border-[var(--outline-variant)] bg-[var(--surface-container-low)] space-y-3">
              <span className="material-symbols-outlined text-[42px] text-[var(--on-surface-variant)] opacity-40 block">
                emoji_events
              </span>
              <h4 className="text-base font-bold text-[var(--on-surface)]">No Ranked Students Yet</h4>
              <p className="text-xs text-[var(--on-surface-variant)] max-w-md mx-auto">
                Students will appear on the leaderboard as soon as they complete an attempt and all questions (including short answers) are evaluated.
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Podium for Top Ranked */}
              {leaderboardData.entries.length >= 1 && (
                <div
                  className={`gap-4 pt-2 ${
                    leaderboardData.entries.length === 1
                      ? "max-w-md mx-auto"
                      : leaderboardData.entries.length === 2
                      ? "grid grid-cols-1 md:grid-cols-2 max-w-2xl mx-auto"
                      : "grid grid-cols-1 md:grid-cols-3"
                  }`}
                >
                  {/* 2nd Place */}
                  {leaderboardData.entries.length >= 2 && (
                    <div className="p-5 rounded-3xl bg-[var(--surface-container-low)] border border-[var(--outline-variant)] flex flex-col items-center text-center relative overflow-hidden order-2 md:order-1 shadow-sm">
                      <div className="w-12 h-12 rounded-2xl bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-200 font-extrabold text-base flex items-center justify-center shadow-inner mb-3">
                        🥈 #2
                      </div>
                      <h4 className="text-sm font-bold text-[var(--on-surface)] truncate max-w-[200px]">
                        {leaderboardData.entries[1].student.display_name}
                      </h4>
                      <div className="text-2xl font-black text-slate-700 dark:text-slate-300 mt-1">
                        {Number(leaderboardData.entries[1].percentage).toFixed(1)}%
                      </div>
                      <div className="text-xs text-[var(--on-surface-variant)] mt-1">
                        {Number(leaderboardData.entries[1].obtained_marks).toFixed(1)} marks • {leaderboardData.entries[1].attempts_used} attempt(s)
                      </div>
                    </div>
                  )}

                  {/* 1st Place */}
                  <div
                    className={`p-6 rounded-3xl bg-amber-500/10 border-2 border-amber-500/40 flex flex-col items-center text-center relative overflow-hidden shadow-md ${
                      leaderboardData.entries.length >= 3 ? "order-1 md:order-2" : "order-1"
                    }`}
                  >
                    <div className="w-14 h-14 rounded-2xl bg-amber-500 text-white font-black text-xl flex items-center justify-center shadow-md mb-3">
                      🥇 #1
                    </div>
                    <Badge variant="outline" className="bg-amber-500/20 text-amber-800 dark:text-amber-200 border-amber-500/40 text-[10px] font-bold uppercase tracking-wider mb-1">
                      Top Scorer
                    </Badge>
                    <h4 className="text-base font-extrabold text-[var(--on-surface)] truncate max-w-[220px]">
                      {leaderboardData.entries[0].student.display_name}
                    </h4>
                    <div className="text-3xl font-black text-amber-600 dark:text-amber-400 mt-1">
                      {Number(leaderboardData.entries[0].percentage).toFixed(1)}%
                    </div>
                    <div className="text-xs text-[var(--on-surface-variant)] mt-1 font-medium">
                      {Number(leaderboardData.entries[0].obtained_marks).toFixed(1)} marks • {leaderboardData.entries[0].attempts_used} attempt(s)
                    </div>
                  </div>

                  {/* 3rd Place */}
                  {leaderboardData.entries.length >= 3 && (
                    <div className="p-5 rounded-3xl bg-[var(--surface-container-low)] border border-[var(--outline-variant)] flex flex-col items-center text-center relative overflow-hidden order-3 shadow-sm">
                      <div className="w-12 h-12 rounded-2xl bg-amber-900/10 text-amber-800 dark:text-amber-400 font-extrabold text-base flex items-center justify-center shadow-inner mb-3">
                        🥉 #3
                      </div>
                      <h4 className="text-sm font-bold text-[var(--on-surface)] truncate max-w-[200px]">
                        {leaderboardData.entries[2].student.display_name}
                      </h4>
                      <div className="text-2xl font-black text-amber-800 dark:text-amber-500 mt-1">
                        {Number(leaderboardData.entries[2].percentage).toFixed(1)}%
                      </div>
                      <div className="text-xs text-[var(--on-surface-variant)] mt-1">
                        {Number(leaderboardData.entries[2].obtained_marks).toFixed(1)} marks • {leaderboardData.entries[2].attempts_used} attempt(s)
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Full Roster Ranking Table */}
              <div className="bg-[var(--surface-container-lowest)] border border-[var(--outline-variant)] rounded-3xl p-6 shadow-sm space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-base font-bold text-[var(--on-surface)] flex items-center gap-2">
                    <span className="material-symbols-outlined text-[20px] text-[var(--primary)]">format_list_numbered</span>
                    All Ranked Participants ({leaderboardData.total_ranked_students})
                  </h4>
                  <span className="text-xs text-[var(--on-surface-variant)]">
                    Competition Tie-Breaking Active
                  </span>
                </div>

                <div className="overflow-x-auto rounded-2xl border border-[var(--outline-variant)]">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-[var(--surface-container-low)] text-[var(--on-surface-variant)] font-semibold border-b border-[var(--outline-variant)]">
                      <tr>
                        <th className="py-3 px-4">Rank</th>
                        <th className="py-3 px-4">Student</th>
                        <th className="py-3 px-4 text-right">Best Score</th>
                        <th className="py-3 px-4 text-right">Obtained Marks</th>
                        <th className="py-3 px-4 text-right">Attempts Used</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--outline-variant)] bg-[var(--surface-container-lowest)]">
                      {leaderboardData.entries.map((entry) => {
                        const isTop1 = entry.rank === 1;
                        const isTop2 = entry.rank === 2;
                        const isTop3 = entry.rank === 3;

                        return (
                          <tr key={`${entry.rank}-${entry.student.id}`} className="hover:bg-[var(--surface-container-low)]/60 transition-colors">
                            <td className="py-3 px-4 font-bold">
                              {isTop1 ? (
                                <span className="inline-flex items-center gap-1 text-amber-500 font-extrabold text-sm">🥇 #1</span>
                              ) : isTop2 ? (
                                <span className="inline-flex items-center gap-1 text-slate-400 font-bold text-sm">🥈 #2</span>
                              ) : isTop3 ? (
                                <span className="inline-flex items-center gap-1 text-amber-700 dark:text-amber-500 font-bold text-sm">🥉 #3</span>
                              ) : (
                                <span className="text-[var(--on-surface-variant)] font-semibold">#{entry.rank}</span>
                              )}
                            </td>
                            <td className="py-3 px-4">
                              <div className="flex items-center gap-2.5">
                                <div className="w-7 h-7 rounded-full bg-[var(--primary)]/10 text-[var(--primary)] font-bold text-xs flex items-center justify-center flex-shrink-0 shadow-inner">
                                  {entry.student.display_name.slice(0, 1).toUpperCase()}
                                </div>
                                <span className="font-semibold text-[var(--on-surface)] text-sm">
                                  {entry.student.display_name}
                                </span>
                              </div>
                            </td>
                            <td className="py-3 px-4 text-right font-bold text-emerald-600 text-sm">
                              {Number(entry.percentage).toFixed(1)}%
                            </td>
                            <td className="py-3 px-4 text-right text-[var(--on-surface-variant)] font-medium text-xs">
                              {Number(entry.obtained_marks).toFixed(1)}
                            </td>
                            <td className="py-3 px-4 text-right text-[var(--on-surface-variant)] text-xs">
                              {entry.attempts_used}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                {leaderboardData.total_ranked_students > 20 && (
                  <div className="flex items-center justify-between pt-3 border-t border-[var(--outline-variant)]">
                    <span className="text-xs text-[var(--on-surface-variant)]">
                      Showing page {leaderboardPage} of {Math.ceil(leaderboardData.total_ranked_students / 20)}
                    </span>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={leaderboardPage <= 1 || loadingLeaderboard}
                        onClick={() => loadLeaderboardData(leaderboardPage - 1)}
                        className="rounded-xl text-xs"
                      >
                        Previous
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={leaderboardPage * 20 >= leaderboardData.total_ranked_students || loadingLeaderboard}
                        onClick={() => loadLeaderboardData(leaderboardPage + 1)}
                        className="rounded-xl text-xs"
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
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

          <form onSubmit={handleSaveInlineQuestion} className="flex flex-col h-full max-h-[75vh]">
            {inlineError && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-600 dark:text-red-400 text-xs mb-4">
                {inlineError}
              </div>
            )}

            <div className="flex-1 overflow-y-auto space-y-6 pr-2 custom-scrollbar">
              {inlineQuestions.map((q, qIndex) => (
                <div key={q.id} className="p-4 rounded-2xl bg-[var(--surface-container-lowest)] border border-[var(--outline-variant)] relative space-y-4 shadow-sm">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-bold text-[var(--on-surface)]">Question {qIndex + 1}</h4>
                    {inlineQuestions.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeInlineQuestion(q.id)}
                        className="text-[var(--on-surface-variant)] hover:text-red-500 transition-colors p-1"
                        title="Remove Question"
                      >
                        <span className="material-symbols-outlined text-[18px]">close</span>
                      </button>
                    )}
                  </div>
                  
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
                          onClick={() => handleInlineTypeChange(q.id, item.type as QuestionType)}
                          className={`py-2 px-3 text-xs font-semibold rounded-xl border text-center transition ${
                            q.type === item.type
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
                      value={q.text}
                      onChange={(e) => updateInlineQuestion(q.id, { text: e.target.value })}
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
                      value={q.marks}
                      onChange={(e) => updateInlineQuestion(q.id, { marks: e.target.value })}
                      className="w-28 bg-[var(--surface-container-low)] text-sm"
                      required
                    />
                  </div>

                  {/* Options */}
                  {q.type !== "short_answer" && (
                    <div className="space-y-2.5 pt-2 border-t border-[var(--outline-variant)]">
                      <div className="flex items-center justify-between">
                        <Label className="text-xs font-semibold uppercase tracking-wider text-[var(--on-surface-variant)] block">
                          {q.type === "true_false"
                            ? "Select Correct Answer *"
                            : "Options & Answer Key (Click checkmark to mark correct)"}
                        </Label>
                        {q.type !== "true_false" && q.options.length < 6 && (
                          <button
                            type="button"
                            onClick={() => addOptionToInlineQuestion(q.id)}
                            className="text-xs text-[var(--primary)] hover:underline inline-flex items-center gap-1 font-semibold"
                          >
                            <span className="material-symbols-outlined text-[14px]">add</span>
                            Add Option
                          </button>
                        )}
                      </div>

                      {q.type === "true_false" ? (
                        <div className="grid grid-cols-2 gap-3 pt-1">
                          {[
                            { label: "True", isCorrectDefault: true },
                            { label: "False", isCorrectDefault: false },
                          ].map((choice) => {
                            const isSelected =
                              q.options.find(
                                (o) => o.option_text.toLowerCase() === choice.label.toLowerCase()
                              )?.is_correct ?? choice.isCorrectDefault;

                            return (
                              <button
                                type="button"
                                key={choice.label}
                                onClick={() => {
                                  updateInlineQuestion(q.id, {
                                    options: [
                                      { option_text: "True", option_order: 1, is_correct: choice.label === "True" },
                                      { option_text: "False", option_order: 2, is_correct: choice.label === "False" },
                                    ],
                                  });
                                }}
                                className={`flex items-center justify-between p-3.5 rounded-xl border text-sm font-semibold transition ${
                                  isSelected
                                    ? "bg-emerald-500/15 border-emerald-500 text-emerald-800 dark:text-emerald-300 shadow-sm ring-1 ring-emerald-500"
                                    : "bg-[var(--surface-container-low)] border-[var(--outline-variant)] text-[var(--on-surface-variant)] hover:bg-[var(--surface-container-high)]"
                                }`}
                              >
                                <span className="font-bold">{choice.label}</span>
                                <div
                                  className={`w-6 h-6 rounded-lg flex items-center justify-center transition ${
                                    isSelected
                                      ? "bg-emerald-600 text-white"
                                      : "bg-[var(--surface-container-high)] text-[var(--on-surface-variant)]"
                                  }`}
                                >
                                  {isSelected && <span className="material-symbols-outlined text-[16px]">check</span>}
                                </div>
                              </button>
                            );
                          })}
                        </div>
                      ) : (
                        <div className="space-y-2">
                          {q.options.map((opt, idx) => (
                            <div key={idx} className="flex items-center gap-2">
                              <button
                                type="button"
                                onClick={() => {
                                  const newOptions = [...q.options];
                                  newOptions.forEach((o, i) => {
                                    if (q.type === "mcq_single") {
                                      o.is_correct = i === idx;
                                    } else if (i === idx) {
                                      o.is_correct = !o.is_correct;
                                    }
                                  });
                                  updateInlineQuestion(q.id, { options: newOptions });
                                }}
                                className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs flex-shrink-0 transition ${
                                  opt.is_correct
                                    ? "bg-emerald-600 text-white shadow-sm"
                                    : "bg-[var(--surface-container-high)] text-[var(--on-surface-variant)]"
                                }`}
                                title={opt.is_correct ? "Correct Answer" : "Mark as Correct"}
                              >
                                <span className="material-symbols-outlined text-[16px]">check</span>
                              </button>
                              <Input
                                type="text"
                                value={opt.option_text}
                                onChange={(e) => {
                                  const newOptions = [...q.options];
                                  newOptions[idx].option_text = e.target.value;
                                  updateInlineQuestion(q.id, { options: newOptions });
                                }}
                                placeholder={`Option ${idx + 1}...`}
                                className="bg-[var(--surface-container-low)] text-xs h-9"
                                required
                              />
                              {q.options.length > 2 && (
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="icon"
                                  onClick={() => removeOptionFromInlineQuestion(q.id, idx)}
                                  className="h-8 w-8 text-[var(--on-surface-variant)] hover:text-red-600 hover:bg-red-500/10 flex-shrink-0"
                                  title="Delete Option"
                                >
                                  <span className="material-symbols-outlined text-[16px]">delete</span>
                                </Button>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
              
              <div className="pt-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={addAnotherInlineQuestion}
                  className="w-full border-dashed py-6 text-[var(--on-surface-variant)] hover:text-[var(--primary)] hover:border-[var(--primary)] hover:bg-blue-500/5 transition-all"
                >
                  <span className="material-symbols-outlined mr-2">add</span>
                  Add Another Question
                </Button>
              </div>
            </div>

            <DialogFooter className="pt-4 mt-4 border-t border-[var(--outline-variant)]">
              <div className="flex items-center justify-between w-full">
                <span className="text-xs font-semibold text-[var(--on-surface-variant)]">
                  {inlineQuestions.length} {inlineQuestions.length === 1 ? "question" : "questions"}
                </span>
                <div className="flex gap-2">
                  <Button type="button" variant="outline" size="sm" onClick={() => setIsInlineCreateOpen(false)}>
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    size="sm"
                    disabled={inlineSaving || inlineQuestions.length === 0}
                    style={{ backgroundColor: "var(--primary)", color: "var(--on-primary)" }}
                  >
                    {inlineSaving && <div className="w-3.5 h-3.5 border-2 border-t-transparent border-white rounded-full animate-spin mr-1.5" />}
                    Save {inlineQuestions.length > 1 ? "All " : ""}Questions
                  </Button>
                </div>
              </div>
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
