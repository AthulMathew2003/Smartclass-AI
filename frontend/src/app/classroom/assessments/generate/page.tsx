"use client";

import React, { useEffect, useState, useCallback, useMemo } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  fetchSubjects,
  Subject,
} from "@/lib/subjects";
import {
  fetchSubjectMaterialsForQp,
  fetchQpDrafts,
  generateQpDraft,
  getQpDraft,
  updateQpDraftMetadata,
  updateQpDraftQuestion,
  regenerateQpQuestion,
  validateQpDraft,
  convertQpDraftToAssessment,
  deleteQpDraft,
  QpMaterialSummary,
  QpDraftResponse,
  QpDraftListItem,
  QpDraftQuestionResponse,
  QpDifficulty,
  QpQuestionType,
  QpGenerateRequest,
  QpSectionConfig,
} from "@/lib/assessments";
import { usePermissions } from "@/lib/permissions";
import ForbiddenState from "../../components/ForbiddenState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function QuestionPaperGeneratorPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialSubjectId = searchParams.get("subject_id") || "";
  const initialDraftId = searchParams.get("draft_id") || "";

  const { hasPermission, isLoaded: permLoaded, orgId } = usePermissions();
  const isTeacherOrAdmin =
    hasPermission("assessment.create") ||
    hasPermission("subject.create") ||
    hasPermission("member.update");

  // Global Navigation / Mode State
  const [activeTab, setActiveTab] = useState<"generator" | "drafts">("generator");
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [selectedSubjectId, setSelectedSubjectId] = useState<string>(initialSubjectId);
  const [loadingSubjects, setLoadingSubjects] = useState(true);

  // Materials State (Step A)
  const [materials, setMaterials] = useState<QpMaterialSummary[]>([]);
  const [selectedMaterialIds, setSelectedMaterialIds] = useState<string[]>([]);
  const [loadingMaterials, setLoadingMaterials] = useState(false);
  const [materialSearch, setMaterialSearch] = useState("");

  // Configuration State (Step B)
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [totalMarks, setTotalMarks] = useState<string>("50");
  const [durationMinutes, setDurationMinutes] = useState<string>("60");
  const [difficulty, setDifficulty] = useState<QpDifficulty>("mixed");
  const [selectedQuestionTypes, setSelectedQuestionTypes] = useState<QpQuestionType[]>([
    "mcq_single",
    "short_answer",
  ]);
  const [totalQuestions, setTotalQuestions] = useState<string>("10");
  const [generateAnswerKey, setGenerateAnswerKey] = useState(true);
  const [generateRubrics, setGenerateRubrics] = useState(true);
  const [additionalInstructions, setAdditionalInstructions] = useState("");
  const [topicsInput, setTopicsInput] = useState("");

  // Sections (Advanced mode)
  const [useSections, setUseSections] = useState(false);
  const [sections, setSections] = useState<QpSectionConfig[]>([
    {
      section_title: "Part A - Objective Questions",
      section_instructions: "Answer all questions. Each carries 2 marks.",
      question_types: ["mcq_single"],
      question_count: 5,
      marks_per_question: 2,
      difficulty: "easy",
    },
    {
      section_title: "Part B - Conceptual Questions",
      section_instructions: "Answer in detail with relevant examples.",
      question_types: ["short_answer"],
      question_count: 4,
      marks_per_question: 10,
      difficulty: "medium",
    },
  ]);

  // Generation & Active Draft State (Step C & Review)
  const [generating, setGenerating] = useState(false);
  const [generationStepText, setGenerationStepText] = useState("");
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [activeDraft, setActiveDraft] = useState<QpDraftResponse | null>(null);
  const [loadingDraft, setLoadingDraft] = useState(false);

  // Drafts List State (Tab 2)
  const [draftsList, setDraftsList] = useState<QpDraftListItem[]>([]);
  const [loadingDraftsList, setLoadingDraftsList] = useState(false);

  // Question Editing State
  const [editingQuestionId, setEditingQuestionId] = useState<string | null>(null);
  const [editQText, setEditQText] = useState("");
  const [editQMarks, setEditQMarks] = useState<string>("5");
  const [editQDifficulty, setEditQDifficulty] = useState<QpDifficulty>("medium");
  const [editQOptions, setEditQOptions] = useState<Array<{ text: string; is_correct: boolean }>>([]);
  const [editQExpectedAnswer, setEditQExpectedAnswer] = useState("");
  const [editQRubric, setEditQRubric] = useState("");
  const [editQExplanation, setEditQExplanation] = useState("");
  const [savingQuestion, setSavingQuestion] = useState(false);

  // Single Question Regeneration State
  const [regeneratingQId, setRegeneratingQId] = useState<string | null>(null);
  const [regenInstructions, setRegenInstructions] = useState("");
  const [regenType, setRegenType] = useState<QpQuestionType | "">("");
  const [isRegenModalOpen, setIsRegenModalOpen] = useState(false);

  // Convert to Assessment Modal State
  const [isConvertModalOpen, setIsConvertModalOpen] = useState(false);
  const [convertType, setConvertType] = useState<string>("exam");
  const [convertPassingMarks, setConvertPassingMarks] = useState<string>("");
  const [convertAttemptLimit, setConvertAttemptLimit] = useState<string>("1");
  const [convertRandomize, setConvertRandomize] = useState(false);
  const [converting, setConverting] = useState(false);
  const [convertError, setConvertError] = useState<string | null>(null);

  // ── 1. Initial Load: Subjects ─────────────────────────────────────
  useEffect(() => {
    async function loadInitialSubjects() {
      if (!permLoaded || !orgId) return;
      try {
        setLoadingSubjects(true);
        const data = await fetchSubjects();
        setSubjects(data);
        if (data.length > 0 && !selectedSubjectId) {
          setSelectedSubjectId(data[0].subject_id);
        }
      } catch (err) {
        console.error("Failed to load subjects", err);
      } finally {
        setLoadingSubjects(false);
      }
    }
    loadInitialSubjects();
  }, [permLoaded, orgId, selectedSubjectId]);

  // ── 2. Load Materials When Subject Changes ─────────────────────────
  const loadMaterials = useCallback(async (subjId: string) => {
    if (!subjId) return;
    setLoadingMaterials(true);
    setGenerationError(null);
    try {
      const resp = await fetchSubjectMaterialsForQp(subjId);
      setMaterials(resp.materials || []);
      // Auto-select indexed materials by default (up to 3)
      const indexed = (resp.materials || []).filter(
        (m) => m.index_status === "indexed" && m.chunk_count > 0
      );
      setSelectedMaterialIds(indexed.slice(0, 3).map((m) => m.material_id));
    } catch (err: any) {
      console.error("Failed to load materials for subject:", err);
      setMaterials([]);
    } finally {
      setLoadingMaterials(false);
    }
  }, []);

  useEffect(() => {
    if (selectedSubjectId) {
      loadMaterials(selectedSubjectId);
    }
  }, [selectedSubjectId, loadMaterials]);

  // ── 3. Load Draft If Query Param Provided ─────────────────────────
  useEffect(() => {
    async function loadExistingDraft() {
      if (initialSubjectId && initialDraftId) {
        try {
          setLoadingDraft(true);
          const draft = await getQpDraft(initialSubjectId, initialDraftId);
          setActiveDraft(draft);
          setSelectedSubjectId(initialSubjectId);
        } catch (err: any) {
          console.error("Failed to load specified draft:", err);
        } finally {
          setLoadingDraft(false);
        }
      }
    }
    loadExistingDraft();
  }, [initialSubjectId, initialDraftId]);

  // ── 4. Load Drafts List for Subject ────────────────────────────────
  const loadDraftsList = useCallback(async (subjId: string) => {
    if (!subjId) return;
    setLoadingDraftsList(true);
    try {
      const list = await fetchQpDrafts(subjId);
      setDraftsList(list);
    } catch (err) {
      console.error("Failed to load drafts list:", err);
    } finally {
      setLoadingDraftsList(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === "drafts" && selectedSubjectId) {
      loadDraftsList(selectedSubjectId);
    }
  }, [activeTab, selectedSubjectId, loadDraftsList]);

  // Filtered materials based on search term
  const filteredMaterials = useMemo(() => {
    if (!materialSearch.trim()) return materials;
    const q = materialSearch.toLowerCase();
    return materials.filter(
      (m) =>
        m.title.toLowerCase().includes(q) ||
        m.original_filename.toLowerCase().includes(q)
    );
  }, [materials, materialSearch]);

  const toggleMaterialSelection = (materialId: string) => {
    setSelectedMaterialIds((prev) =>
      prev.includes(materialId)
        ? prev.filter((id) => id !== materialId)
        : [...prev, materialId]
    );
  };

  const toggleQuestionType = (qtype: QpQuestionType) => {
    setSelectedQuestionTypes((prev) =>
      prev.includes(qtype)
        ? prev.filter((t) => t !== qtype)
        : [...prev, qtype]
    );
  };

  // ── 5. Generation Handler ─────────────────────────────────────────
  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setGenerationError(null);

    if (!selectedSubjectId) {
      setGenerationError("Please select a subject.");
      return;
    }
    if (selectedMaterialIds.length === 0) {
      setGenerationError("Please select at least one course material for question grounding.");
      return;
    }
    if (!title.trim()) {
      setGenerationError("Please enter a question paper title.");
      return;
    }
    const marksNum = parseFloat(totalMarks);
    if (isNaN(marksNum) || marksNum <= 0) {
      setGenerationError("Total marks must be a positive number.");
      return;
    }

    if (!useSections && selectedQuestionTypes.length === 0) {
      setGenerationError("Please select at least one question type.");
      return;
    }

    // Check if any selected material is unindexed
    const unindexedSelected = materials.filter(
      (m) => selectedMaterialIds.includes(m.material_id) && m.index_status !== "indexed"
    );
    if (unindexedSelected.length > 0) {
      setGenerationError(
        `Selected material '${unindexedSelected[0].title}' is not indexed. Please re-index it from the Materials tab before generating.`
      );
      return;
    }

    const payload: QpGenerateRequest = {
      title: title.trim(),
      description: description.trim() || null,
      material_ids: selectedMaterialIds,
      total_marks: marksNum,
      duration_minutes: durationMinutes ? parseInt(durationMinutes, 10) : null,
      difficulty,
      generate_answer_key: generateAnswerKey,
      generate_rubrics: generateRubrics,
      additional_instructions: additionalInstructions.trim() || null,
      topics: topicsInput.trim()
        ? topicsInput
            .split(",")
            .map((t) => t.trim())
            .filter(Boolean)
        : null,
    };

    if (useSections) {
      payload.sections = sections;
    } else {
      payload.total_questions = totalQuestions ? parseInt(totalQuestions, 10) : 10;
      payload.question_types = selectedQuestionTypes;
    }

    setGenerating(true);
    setGenerationStepText("Retrieving grounded chunks from selected course materials...");

    try {
      setTimeout(() => {
        setGenerationStepText("Formulating questions with Google Gemini & generating rubrics...");
      }, 3000);
      setTimeout(() => {
        setGenerationStepText("Performing deterministic validation and rubric checks...");
      }, 7000);

      const draftResp = await generateQpDraft(selectedSubjectId, payload);
      setActiveDraft(draftResp);
      // Scroll to draft preview
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err: any) {
      setGenerationError(
        err.message || "Question paper generation failed. Please check Gemini settings or try again."
      );
    } finally {
      setGenerating(false);
      setGenerationStepText("");
    }
  };

  // ── 6. Question Edit Handlers ─────────────────────────────────────
  const startEditingQuestion = (q: QpDraftQuestionResponse) => {
    setEditingQuestionId(q.dq_id);
    setEditQText(q.dq_question_text);
    setEditQMarks(String(q.dq_marks));
    setEditQDifficulty(q.dq_difficulty as QpDifficulty);
    setEditQOptions(q.dq_options ? JSON.parse(JSON.stringify(q.dq_options)) : []);
    setEditQExpectedAnswer(q.dq_expected_answer || "");
    setEditQRubric(q.dq_rubric || "");
    setEditQExplanation(q.dq_explanation || "");
  };

  const cancelEditingQuestion = () => {
    setEditingQuestionId(null);
  };

  const saveQuestionChanges = async (dqId: string) => {
    if (!activeDraft || !selectedSubjectId) return;
    setSavingQuestion(true);
    try {
      const updated = await updateQpDraftQuestion(
        selectedSubjectId,
        activeDraft.draft_id,
        dqId,
        {
          question_text: editQText.trim(),
          marks: parseFloat(editQMarks),
          difficulty: editQDifficulty,
          options: editQOptions.length > 0 ? editQOptions : undefined,
          expected_answer: editQExpectedAnswer.trim() || undefined,
          rubric: editQRubric.trim() || undefined,
          explanation: editQExplanation.trim() || undefined,
        }
      );
      setActiveDraft(updated);
      setEditingQuestionId(null);
    } catch (err: any) {
      alert(err.message || "Failed to update question.");
    } finally {
      setSavingQuestion(false);
    }
  };

  // ── 7. Single Question Regeneration ───────────────────────────────
  const openRegenerateModal = (q: QpDraftQuestionResponse) => {
    setRegeneratingQId(q.dq_id);
    setRegenInstructions("");
    setRegenType(q.dq_question_type as QpQuestionType);
    setIsRegenModalOpen(true);
  };

  const handleRegenerateQuestion = async () => {
    if (!activeDraft || !selectedSubjectId || !regeneratingQId) return;
    setIsRegenModalOpen(false);
    setLoadingDraft(true);
    try {
      const updated = await regenerateQpQuestion(
        selectedSubjectId,
        activeDraft.draft_id,
        regeneratingQId,
        {
          question_type: regenType || undefined,
          additional_instructions: regenInstructions.trim() || undefined,
        }
      );
      setActiveDraft(updated);
    } catch (err: any) {
      alert(err.message || "Failed to regenerate question.");
    } finally {
      setLoadingDraft(false);
      setRegeneratingQId(null);
    }
  };

  // ── 8. Revalidate Draft ───────────────────────────────────────────
  const handleRevalidate = async () => {
    if (!activeDraft || !selectedSubjectId) return;
    setLoadingDraft(true);
    try {
      const updated = await validateQpDraft(selectedSubjectId, activeDraft.draft_id);
      setActiveDraft(updated);
    } catch (err: any) {
      alert(err.message || "Validation failed.");
    } finally {
      setLoadingDraft(false);
    }
  };

  // ── 9. Convert to Assessment ───────────────────────────────────────
  const handleConvert = async () => {
    if (!activeDraft || !selectedSubjectId) return;
    setConvertError(null);
    setConverting(true);
    try {
      const res = await convertQpDraftToAssessment(
        selectedSubjectId,
        activeDraft.draft_id,
        {
          assessment_type: convertType,
          passing_marks: convertPassingMarks ? parseFloat(convertPassingMarks) : null,
          attempt_limit: parseInt(convertAttemptLimit, 10) || 1,
          randomize_questions: convertRandomize,
        }
      );
      setIsConvertModalOpen(false);
      // Redirect to the assessment builder page for full review & publishing!
      router.push(`/classroom/assessments/${res.assessment_id}`);
    } catch (err: any) {
      setConvertError(err.message || "Failed to convert draft to assessment.");
    } finally {
      setConverting(false);
    }
  };

  // ── 10. Discard Draft ─────────────────────────────────────────────
  const handleDiscard = async () => {
    if (!activeDraft || !selectedSubjectId) return;
    if (!confirm("Are you sure you want to discard this question paper draft? This cannot be undone.")) {
      return;
    }
    try {
      await deleteQpDraft(selectedSubjectId, activeDraft.draft_id);
      setActiveDraft(null);
      await loadDraftsList(selectedSubjectId);
    } catch (err: any) {
      alert(err.message || "Failed to delete draft.");
    }
  };

  if (permLoaded && !isTeacherOrAdmin) {
    return <ForbiddenState message="Only teachers and administrators can generate question papers." />;
  }

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-6">
      {/* ── Breadcrumb & Top Bar ──────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[var(--outline-variant)] pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs text-[var(--on-surface-variant)] mb-1">
            <Link href="/classroom/assessments" className="hover:underline flex items-center gap-1">
              <span className="material-symbols-outlined text-[14px]">arrow_back</span>
              Assessments
            </Link>
            <span>/</span>
            <span className="font-medium text-[var(--on-surface)]">AI Question Paper Generator</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-[var(--on-surface)] flex items-center gap-2">
            <span className="material-symbols-outlined text-amber-500 text-[28px]">auto_awesome</span>
            AI Question Paper Generator
          </h1>
          <p className="text-sm text-[var(--on-surface-variant)] mt-1">
            Generate balanced, curriculum-aligned exam papers grounded in your course materials with ChromaDB RAG & Gemini.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center gap-2 bg-[var(--surface-container-low)] p-1 rounded-xl border border-[var(--outline-variant)]">
          <Button
            variant={activeTab === "generator" ? "default" : "ghost"}
            size="sm"
            onClick={() => setActiveTab("generator")}
            className="flex items-center gap-1.5 text-xs font-semibold"
          >
            <span className="material-symbols-outlined text-[16px]">edit_document</span>
            Paper Generator
          </Button>
          <Button
            variant={activeTab === "drafts" ? "default" : "ghost"}
            size="sm"
            onClick={() => setActiveTab("drafts")}
            className="flex items-center gap-1.5 text-xs font-semibold"
          >
            <span className="material-symbols-outlined text-[16px]">history</span>
            Saved Drafts
          </Button>
        </div>
      </div>

      {/* ── SUBJECT SELECTOR (Always Visible) ────────────────────── */}
      <div className="bg-[var(--surface-container-low)] p-4 rounded-2xl border border-[var(--outline-variant)] flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined text-[20px] text-[var(--primary)]">school</span>
          <div>
            <Label className="text-xs font-semibold uppercase tracking-wider text-[var(--on-surface-variant)]">
              Target Subject
            </Label>
            <div className="mt-1">
              <Select
                value={selectedSubjectId}
                onValueChange={(val) => {
                  setSelectedSubjectId(val);
                  setActiveDraft(null);
                }}
                disabled={loadingSubjects || generating}
              >
                <SelectTrigger className="w-[280px] h-9 text-sm font-medium">
                  <SelectValue placeholder="Select a subject..." />
                </SelectTrigger>
                <SelectContent>
                  {subjects.map((s) => (
                    <SelectItem key={s.subject_id} value={s.subject_id}>
                      {s.subject_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        {activeDraft && (
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="bg-amber-500/10 text-amber-600 border-amber-500/30">
              Editing Draft: {activeDraft.draft_title}
            </Badge>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setActiveDraft(null)}
              className="text-xs"
            >
              Start New Paper
            </Button>
          </div>
        )}
      </div>

      {/* ── TAB 2: SAVED DRAFTS LIST ──────────────────────────────── */}
      {activeTab === "drafts" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-[var(--on-surface)]">
              Saved Question Paper Drafts
            </h2>
            <Button
              variant="outline"
              size="sm"
              onClick={() => loadDraftsList(selectedSubjectId)}
              disabled={loadingDraftsList}
              className="text-xs flex items-center gap-1"
            >
              <span className="material-symbols-outlined text-[16px]">refresh</span>
              Refresh
            </Button>
          </div>

          {loadingDraftsList ? (
            <div className="p-12 text-center text-sm text-[var(--on-surface-variant)]">
              Loading drafts...
            </div>
          ) : draftsList.length === 0 ? (
            <div className="p-12 text-center bg-[var(--surface-container-low)] rounded-2xl border border-[var(--outline-variant)]">
              <span className="material-symbols-outlined text-[36px] text-[var(--on-surface-variant)] mb-2">
                drafts
              </span>
              <p className="text-sm font-semibold text-[var(--on-surface)]">No question paper drafts yet</p>
              <p className="text-xs text-[var(--on-surface-variant)] mt-1">
                Configure and generate a draft using course materials above.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {draftsList.map((d) => (
                <div
                  key={d.draft_id}
                  className="bg-[var(--surface-container-low)] p-5 rounded-2xl border border-[var(--outline-variant)] hover:border-[var(--primary)]/50 transition-all flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-semibold text-base text-[var(--on-surface)] line-clamp-1">
                        {d.draft_title}
                      </h3>
                      <Badge
                        variant="outline"
                        className={
                          d.draft_status === "ready"
                            ? "bg-emerald-500/10 text-emerald-600 border-emerald-500/30"
                            : d.draft_status === "converted"
                            ? "bg-purple-500/10 text-purple-600 border-purple-500/30"
                            : "bg-amber-500/10 text-amber-600 border-amber-500/30"
                        }
                      >
                        {d.draft_status}
                      </Badge>
                    </div>

                    <div className="flex items-center gap-4 text-xs text-[var(--on-surface-variant)] mt-3">
                      <span className="flex items-center gap-1">
                        <span className="material-symbols-outlined text-[14px]">format_list_numbered</span>
                        {d.question_count} Questions
                      </span>
                      {d.total_marks !== null && (
                        <span className="flex items-center gap-1">
                          <span className="material-symbols-outlined text-[14px]">grade</span>
                          {d.total_marks} Marks
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="mt-5 pt-3 border-t border-[var(--outline-variant)] flex items-center justify-between">
                    <span className="text-[11px] text-[var(--on-surface-variant)]">
                      {new Date(d.draft_created_at).toLocaleDateString()}
                    </span>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="default"
                        className="text-xs h-8"
                        onClick={async () => {
                          try {
                            setLoadingDraft(true);
                            const loaded = await getQpDraft(d.draft_subject_id, d.draft_id);
                            setActiveDraft(loaded);
                            setActiveTab("generator");
                          } catch (err: any) {
                            alert(err.message || "Failed to load draft.");
                          } finally {
                            setLoadingDraft(false);
                          }
                        }}
                      >
                        Open Draft
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── TAB 1: GENERATOR & DRAFT REVIEW ──────────────────────── */}
      {activeTab === "generator" && (
        <>
          {/* Active Draft Review Workspace (if draft exists) */}
          {activeDraft ? (
            <div className="space-y-6">
              {/* Draft Header & Action Ribbon */}
              <div className="bg-[var(--surface-container-low)] p-6 rounded-2xl border border-[var(--outline-variant)] flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <h2 className="text-xl font-bold text-[var(--on-surface)]">
                      {activeDraft.draft_title}
                    </h2>
                    <Badge
                      variant="outline"
                      className="bg-emerald-500/10 text-emerald-600 border-emerald-500/30 text-xs font-semibold"
                    >
                      {activeDraft.draft_status.toUpperCase()}
                    </Badge>
                  </div>
                  {activeDraft.draft_description && (
                    <p className="text-xs text-[var(--on-surface-variant)]">
                      {activeDraft.draft_description}
                    </p>
                  )}
                  <div className="flex items-center gap-4 text-xs font-medium text-[var(--on-surface-variant)] pt-1">
                    <span className="flex items-center gap-1">
                      <span className="material-symbols-outlined text-[15px] text-[var(--primary)]">
                        format_list_numbered
                      </span>
                      {activeDraft.questions.length} Questions
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="material-symbols-outlined text-[15px] text-amber-500">grade</span>
                      {activeDraft.questions.reduce((sum, q) => sum + q.dq_marks, 0)} Total Marks
                    </span>
                    {activeDraft.draft_config.duration_minutes && (
                      <span className="flex items-center gap-1">
                        <span className="material-symbols-outlined text-[15px] text-sky-500">timer</span>
                        {activeDraft.draft_config.duration_minutes} Mins
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleRevalidate}
                    disabled={loadingDraft}
                    className="flex items-center gap-1 text-xs"
                  >
                    <span className="material-symbols-outlined text-[16px]">verified</span>
                    Revalidate
                  </Button>

                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={handleDiscard}
                    disabled={loadingDraft}
                    className="text-xs"
                  >
                    Discard Draft
                  </Button>

                  {activeDraft.draft_status !== "converted" ? (
                    <Button
                      size="sm"
                      onClick={() => setIsConvertModalOpen(true)}
                      className="flex items-center gap-1.5 text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white"
                    >
                      <span className="material-symbols-outlined text-[16px]">publish</span>
                      Convert to Assessment
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        if (activeDraft.draft_converted_assessment_id) {
                          router.push(`/classroom/assessments/${activeDraft.draft_converted_assessment_id}`);
                        }
                      }}
                      className="text-xs"
                    >
                      View Converted Assessment
                    </Button>
                  )}
                </div>
              </div>

              {/* ── Deterministic Validation Banner ──────────────── */}
              {activeDraft.draft_validation_result && (
                <div
                  className={`p-4 rounded-2xl border text-xs ${
                    activeDraft.draft_validation_result.is_valid
                      ? "bg-emerald-500/5 border-emerald-500/30 text-emerald-800 dark:text-emerald-300"
                      : "bg-amber-500/5 border-amber-500/30 text-amber-800 dark:text-amber-300"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 font-semibold">
                      <span className="material-symbols-outlined text-[18px]">
                        {activeDraft.draft_validation_result.is_valid ? "check_circle" : "warning"}
                      </span>
                      <span>
                        Deterministic Validation Report:{" "}
                        {activeDraft.draft_validation_result.is_valid
                          ? "All Paper Constraints Satisfied"
                          : "Attention Required"}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span>
                        Marks: {activeDraft.draft_validation_result.total_marks_actual} /{" "}
                        {activeDraft.draft_validation_result.total_marks_expected}
                      </span>
                      <span>
                        Questions: {activeDraft.draft_validation_result.question_count_actual}
                      </span>
                    </div>
                  </div>

                  {activeDraft.draft_validation_result.issues?.length > 0 && (
                    <div className="mt-2 pl-6 space-y-1">
                      {activeDraft.draft_validation_result.issues.map((iss, i) => (
                        <p key={i} className="flex items-center gap-1.5">
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              iss.severity === "error" ? "bg-red-500" : "bg-amber-500"
                            }`}
                          />
                          {iss.question_index !== null && iss.question_index !== undefined
                            ? `Q${iss.question_index + 1}: `
                            : ""}
                          {iss.message}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* ── Questions List ──────────────────────────────── */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-bold text-[var(--on-surface)]">
                    Generated Paper Questions ({activeDraft.questions.length})
                  </h3>
                  <span className="text-xs text-[var(--on-surface-variant)]">
                    Review, edit, or regenerate individual questions before converting.
                  </span>
                </div>

                {activeDraft.questions.map((q, idx) => {
                  const isEditing = editingQuestionId === q.dq_id;

                  return (
                    <div
                      key={q.dq_id}
                      className="bg-[var(--surface-container-low)] rounded-2xl border border-[var(--outline-variant)] overflow-hidden transition-all shadow-sm"
                    >
                      {/* Question Header Bar */}
                      <div className="p-4 bg-[var(--surface-container)] flex items-center justify-between gap-4 border-b border-[var(--outline-variant)]">
                        <div className="flex items-center gap-3">
                          <span className="w-7 h-7 rounded-full bg-[var(--primary)] text-[var(--on-primary)] flex items-center justify-center font-bold text-xs shadow-sm">
                            {idx + 1}
                          </span>
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className="text-[11px] uppercase font-semibold">
                              {q.dq_question_type.replace("_", " ")}
                            </Badge>
                            <Badge
                              variant="outline"
                              className={`text-[11px] uppercase font-semibold ${
                                q.dq_difficulty === "easy"
                                  ? "bg-emerald-500/10 text-emerald-600 border-emerald-500/20"
                                  : q.dq_difficulty === "hard"
                                  ? "bg-red-500/10 text-red-600 border-red-500/20"
                                  : "bg-amber-500/10 text-amber-600 border-amber-500/20"
                              }`}
                            >
                              {q.dq_difficulty}
                            </Badge>
                            <span className="text-xs font-semibold text-[var(--on-surface-variant)]">
                              {q.dq_marks} {q.dq_marks === 1 ? "mark" : "marks"}
                            </span>
                          </div>
                        </div>

                        {/* Action buttons */}
                        <div className="flex items-center gap-2">
                          {!isEditing ? (
                            <>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => startEditingQuestion(q)}
                                className="h-8 text-xs flex items-center gap-1"
                              >
                                <span className="material-symbols-outlined text-[15px]">edit</span>
                                Edit
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => openRegenerateModal(q)}
                                className="h-8 text-xs flex items-center gap-1 text-sky-600 hover:text-sky-700 hover:bg-sky-50 dark:hover:bg-sky-950"
                              >
                                <span className="material-symbols-outlined text-[15px]">autorenew</span>
                                Regenerate
                              </Button>
                            </>
                          ) : (
                            <>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={cancelEditingQuestion}
                                className="h-8 text-xs"
                              >
                                Cancel
                              </Button>
                              <Button
                                size="sm"
                                onClick={() => saveQuestionChanges(q.dq_id)}
                                disabled={savingQuestion}
                                className="h-8 text-xs bg-[var(--primary)] text-[var(--on-primary)]"
                              >
                                {savingQuestion ? "Saving..." : "Save Changes"}
                              </Button>
                            </>
                          )}
                        </div>
                      </div>

                      {/* Question Body */}
                      <div className="p-5 space-y-4">
                        {isEditing ? (
                          /* Edit Form */
                          <div className="space-y-4">
                            <div>
                              <Label className="text-xs font-medium">Question Text</Label>
                              <Textarea
                                value={editQText}
                                onChange={(e) => setEditQText(e.target.value)}
                                className="mt-1 text-sm font-medium"
                                rows={3}
                              />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                              <div>
                                <Label className="text-xs font-medium">Marks</Label>
                                <Input
                                  type="number"
                                  step="0.5"
                                  value={editQMarks}
                                  onChange={(e) => setEditQMarks(e.target.value)}
                                  className="mt-1 h-8 text-xs"
                                />
                              </div>
                              <div>
                                <Label className="text-xs font-medium">Difficulty</Label>
                                <Select
                                  value={editQDifficulty}
                                  onValueChange={(val) => setEditQDifficulty(val as QpDifficulty)}
                                >
                                  <SelectTrigger className="mt-1 h-8 text-xs">
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="easy">Easy</SelectItem>
                                    <SelectItem value="medium">Medium</SelectItem>
                                    <SelectItem value="hard">Hard</SelectItem>
                                  </SelectContent>
                                </Select>
                              </div>
                            </div>

                            {/* Options Editor (for MCQ) */}
                            {editQOptions.length > 0 && (
                              <div className="space-y-2 pt-2 border-t border-[var(--outline-variant)]">
                                <Label className="text-xs font-semibold">Options (Select the correct answer)</Label>
                                {editQOptions.map((opt, optIdx) => (
                                  <div key={optIdx} className="flex items-center gap-2">
                                    <input
                                      type="radio"
                                      name={`correct_opt_${q.dq_id}`}
                                      checked={opt.is_correct}
                                      onChange={() => {
                                        setEditQOptions((prev) =>
                                          prev.map((o, idx) => ({
                                            ...o,
                                            is_correct: idx === optIdx,
                                          }))
                                        );
                                      }}
                                    />
                                    <Input
                                      value={opt.text}
                                      onChange={(e) => {
                                        const newText = e.target.value;
                                        setEditQOptions((prev) =>
                                          prev.map((o, idx) =>
                                            idx === optIdx ? { ...o, text: newText } : o
                                          )
                                        );
                                      }}
                                      className="h-8 text-xs flex-1"
                                    />
                                  </div>
                                ))}
                              </div>
                            )}

                            {/* Expected Answer / Rubric Editor */}
                            {q.dq_question_type === "short_answer" && (
                              <div className="space-y-3 pt-2 border-t border-[var(--outline-variant)]">
                                <div>
                                  <Label className="text-xs font-medium">Expected Answer Key</Label>
                                  <Textarea
                                    value={editQExpectedAnswer}
                                    onChange={(e) => setEditQExpectedAnswer(e.target.value)}
                                    className="mt-1 text-xs"
                                    rows={2}
                                  />
                                </div>
                                <div>
                                  <Label className="text-xs font-medium">Marking Rubric / Criteria</Label>
                                  <Textarea
                                    value={editQRubric}
                                    onChange={(e) => setEditQRubric(e.target.value)}
                                    className="mt-1 text-xs"
                                    rows={2}
                                  />
                                </div>
                              </div>
                            )}
                          </div>
                        ) : (
                          /* View Mode */
                          <div className="space-y-3">
                            <p className="text-sm font-semibold text-[var(--on-surface)] leading-relaxed">
                              {q.dq_question_text}
                            </p>

                            {/* MCQ Options Display */}
                            {q.dq_options && q.dq_options.length > 0 && (
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-1">
                                {q.dq_options.map((opt, oIdx) => (
                                  <div
                                    key={oIdx}
                                    className={`p-2.5 rounded-xl border text-xs flex items-center justify-between ${
                                      opt.is_correct
                                        ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-800 dark:text-emerald-300 font-semibold"
                                        : "bg-[var(--surface-container)] border-[var(--outline-variant)] text-[var(--on-surface)]"
                                    }`}
                                  >
                                    <span className="flex items-center gap-2">
                                      <span className="w-5 h-5 rounded-full bg-[var(--surface-container-high)] flex items-center justify-center font-bold text-[10px]">
                                        {String.fromCharCode(65 + oIdx)}
                                      </span>
                                      {opt.text}
                                    </span>
                                    {opt.is_correct && (
                                      <Badge variant="outline" className="bg-emerald-500/20 text-emerald-700 text-[10px]">
                                        Correct
                                      </Badge>
                                    )}
                                  </div>
                                ))}
                              </div>
                            )}

                            {/* Teacher-Only Expected Answer & Rubric Panel */}
                            {(q.dq_expected_answer || q.dq_rubric) && (
                              <div className="mt-3 p-3.5 rounded-xl bg-amber-500/5 border border-amber-500/20 text-xs space-y-2">
                                <div className="flex items-center gap-1.5 text-amber-700 dark:text-amber-400 font-semibold">
                                  <span className="material-symbols-outlined text-[15px]">lock</span>
                                  <span>Teacher-Only: Answer Key & Grading Rubric</span>
                                </div>
                                {q.dq_expected_answer && (
                                  <div>
                                    <span className="font-semibold text-[var(--on-surface)]">Expected Answer: </span>
                                    <span className="text-[var(--on-surface-variant)]">{q.dq_expected_answer}</span>
                                  </div>
                                )}
                                {q.dq_rubric && (
                                  <div>
                                    <span className="font-semibold text-[var(--on-surface)]">Rubric: </span>
                                    <span className="text-[var(--on-surface-variant)]">{q.dq_rubric}</span>
                                  </div>
                                )}
                              </div>
                            )}

                            {/* Source Provenance Info */}
                            {q.dq_source_chunks && q.dq_source_chunks.length > 0 && (
                              <div className="pt-2 flex items-center gap-2 text-[11px] text-[var(--on-surface-variant)]">
                                <span className="material-symbols-outlined text-[13px] text-[var(--primary)]">
                                  menu_book
                                </span>
                                <span>Grounded in: </span>
                                <span className="font-medium text-[var(--on-surface)]">
                                  {q.dq_source_chunks[0].material_title || "Course Material"}
                                </span>
                                {q.dq_source_chunks[0].page_number && (
                                  <span>(Page {q.dq_source_chunks[0].page_number})</span>
                                )}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            /* ── NEW GENERATION WORKFLOW (Step A + Step B) ────────── */
            <form onSubmit={handleGenerate} className="space-y-8">
              {/* STEP A: Select Course Materials */}
              <div className="bg-[var(--surface-container-low)] p-6 rounded-2xl border border-[var(--outline-variant)] space-y-4">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-[var(--outline-variant)] pb-3">
                  <div>
                    <h2 className="text-base font-bold text-[var(--on-surface)] flex items-center gap-2">
                      <span className="w-6 h-6 rounded-full bg-[var(--primary)] text-[var(--on-primary)] flex items-center justify-center text-xs font-bold">
                        1
                      </span>
                      Step A — Select Course Materials
                    </h2>
                    <p className="text-xs text-[var(--on-surface-variant)] mt-0.5">
                      Select one or more uploaded course documents. Questions will be strictly grounded in these materials.
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <Input
                      placeholder="Filter materials..."
                      value={materialSearch}
                      onChange={(e) => setMaterialSearch(e.target.value)}
                      className="h-8 text-xs w-48"
                    />
                    <Badge variant="outline" className="text-xs">
                      {selectedMaterialIds.length} Selected
                    </Badge>
                  </div>
                </div>

                {loadingMaterials ? (
                  <div className="p-8 text-center text-xs text-[var(--on-surface-variant)]">
                    Loading course materials for this subject...
                  </div>
                ) : filteredMaterials.length === 0 ? (
                  <div className="p-8 text-center text-xs text-[var(--on-surface-variant)] bg-[var(--surface-container)] rounded-xl border border-[var(--outline-variant)]">
                    <span className="material-symbols-outlined text-[28px] text-[var(--on-surface-variant)] mb-1">
                      folder_off
                    </span>
                    <p className="font-semibold text-[var(--on-surface)]">No course materials found</p>
                    <p className="mt-0.5">
                      Upload course materials under this subject first to enable AI question generation.
                    </p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {filteredMaterials.map((mat) => {
                      const isSelected = selectedMaterialIds.includes(mat.material_id);
                      const isIndexed = mat.index_status === "indexed" && mat.chunk_count > 0;

                      return (
                        <div
                          key={mat.material_id}
                          onClick={() => {
                            if (isIndexed) toggleMaterialSelection(mat.material_id);
                          }}
                          className={`p-3.5 rounded-xl border transition-all cursor-pointer flex items-start gap-3 ${
                            !isIndexed
                              ? "opacity-60 bg-gray-500/5 border-gray-300 dark:border-gray-800 cursor-not-allowed"
                              : isSelected
                              ? "bg-[var(--primary)]/5 border-[var(--primary)] shadow-sm"
                              : "bg-[var(--surface-container)] border-[var(--outline-variant)] hover:border-[var(--outline)]"
                          }`}
                        >
                          <Checkbox
                            checked={isSelected}
                            disabled={!isIndexed}
                            onCheckedChange={() => {
                              if (isIndexed) toggleMaterialSelection(mat.material_id);
                            }}
                            className="mt-0.5"
                          />
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-bold text-[var(--on-surface)] truncate">
                              {mat.title}
                            </p>
                            <p className="text-[11px] text-[var(--on-surface-variant)] truncate mt-0.5">
                              {mat.original_filename}
                            </p>
                            <div className="flex items-center gap-2 mt-2">
                              {isIndexed ? (
                                <Badge variant="outline" className="text-[10px] bg-emerald-500/10 text-emerald-600 border-emerald-500/30">
                                  {mat.chunk_count} RAG Chunks
                                </Badge>
                              ) : (
                                <Badge variant="outline" className="text-[10px] bg-amber-500/10 text-amber-600 border-amber-500/30">
                                  Not Indexed
                                </Badge>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* STEP B: Configure the Paper */}
              <div className="bg-[var(--surface-container-low)] p-6 rounded-2xl border border-[var(--outline-variant)] space-y-6">
                <div className="border-b border-[var(--outline-variant)] pb-3">
                  <h2 className="text-base font-bold text-[var(--on-surface)] flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-[var(--primary)] text-[var(--on-primary)] flex items-center justify-center text-xs font-bold">
                      2
                    </span>
                    Step B — Configure Question Paper Dimensions
                  </h2>
                  <p className="text-xs text-[var(--on-surface-variant)] mt-0.5">
                    Define marks, duration, question types, difficulty, and optional topical guidance.
                  </p>
                </div>

                {/* Title & Instructions */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <Label className="text-xs font-semibold">Paper Title *</Label>
                    <Input
                      placeholder="e.g. Midterm Examination — Computer Architecture"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      className="text-sm"
                      required
                    />
                  </div>

                  <div className="space-y-1">
                    <Label className="text-xs font-semibold">Optional Focus Topics / Chapters</Label>
                    <Input
                      placeholder="e.g. Pipelining, Cache Memory, Instruction Sets"
                      value={topicsInput}
                      onChange={(e) => setTopicsInput(e.target.value)}
                      className="text-sm"
                    />
                  </div>
                </div>

                <div className="space-y-1">
                  <Label className="text-xs font-semibold">General Instructions / Description</Label>
                  <Textarea
                    placeholder="Instructions for students (e.g. All questions are compulsory. Calculator permitted.)"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    rows={2}
                    className="text-xs"
                  />
                </div>

                {/* Marks, Duration, Difficulty */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                  <div className="space-y-1">
                    <Label className="text-xs font-semibold">Total Marks *</Label>
                    <Input
                      type="number"
                      step="1"
                      min="1"
                      value={totalMarks}
                      onChange={(e) => setTotalMarks(e.target.value)}
                      className="text-sm font-semibold"
                      required
                    />
                  </div>

                  <div className="space-y-1">
                    <Label className="text-xs font-semibold">Duration (Minutes)</Label>
                    <Input
                      type="number"
                      step="5"
                      min="10"
                      value={durationMinutes}
                      onChange={(e) => setDurationMinutes(e.target.value)}
                      className="text-sm"
                    />
                  </div>

                  <div className="space-y-1">
                    <Label className="text-xs font-semibold">Difficulty Distribution</Label>
                    <Select
                      value={difficulty}
                      onValueChange={(val) => setDifficulty(val as QpDifficulty)}
                    >
                      <SelectTrigger className="h-9 text-xs font-medium">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="mixed">Mixed (Balanced)</SelectItem>
                        <SelectItem value="easy">Easy (Foundational)</SelectItem>
                        <SelectItem value="medium">Medium (Standard)</SelectItem>
                        <SelectItem value="hard">Hard (Advanced / Analytical)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {/* Question Types & Mode */}
                <div className="space-y-3 pt-2 border-t border-[var(--outline-variant)]">
                  <div className="flex items-center justify-between">
                    <Label className="text-xs font-semibold uppercase tracking-wider text-[var(--on-surface-variant)]">
                      Question Structure
                    </Label>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-[var(--on-surface-variant)]">Use Section Organization</span>
                      <Checkbox
                        checked={useSections}
                        onCheckedChange={(checked) => setUseSections(!!checked)}
                      />
                    </div>
                  </div>

                  {!useSections ? (
                    <div className="space-y-4">
                      <div>
                        <Label className="text-xs font-medium">Question Types to Include</Label>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-1.5">
                          {[
                            { id: "mcq_single", label: "Multiple Choice (MCQ)", icon: "check_circle" },
                            { id: "true_false", label: "True / False", icon: "toggle_on" },
                            { id: "short_answer", label: "Short Answer / Descriptive", icon: "notes" },
                          ].map((t) => {
                            const isChecked = selectedQuestionTypes.includes(t.id as QpQuestionType);
                            return (
                              <button
                                key={t.id}
                                type="button"
                                onClick={() => toggleQuestionType(t.id as QpQuestionType)}
                                className={`p-3 rounded-xl border text-xs font-semibold flex items-center gap-2 transition-all ${
                                  isChecked
                                    ? "bg-[var(--primary)] text-[var(--on-primary)] border-[var(--primary)] shadow-sm"
                                    : "bg-[var(--surface-container)] text-[var(--on-surface-variant)] border-[var(--outline-variant)] hover:bg-[var(--surface-container-high)]"
                                }`}
                              >
                                <span className="material-symbols-outlined text-[16px]">{t.icon}</span>
                                {t.label}
                              </button>
                            );
                          })}
                        </div>
                      </div>

                      <div className="w-48">
                        <Label className="text-xs font-medium">Target Question Count</Label>
                        <Input
                          type="number"
                          min="1"
                          max="50"
                          value={totalQuestions}
                          onChange={(e) => setTotalQuestions(e.target.value)}
                          className="mt-1 text-sm font-semibold"
                        />
                      </div>
                    </div>
                  ) : (
                    /* Sections Mode */
                    <div className="space-y-3">
                      {sections.map((sec, idx) => (
                        <div
                          key={idx}
                          className="p-3.5 bg-[var(--surface-container)] rounded-xl border border-[var(--outline-variant)] space-y-3"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-[var(--on-surface)]">
                              Section {idx + 1}: {sec.section_title}
                            </span>
                            <Badge variant="outline" className="text-[10px]">
                              {sec.question_count} Questions
                            </Badge>
                          </div>
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                            <Input
                              placeholder="Section Title"
                              value={sec.section_title}
                              onChange={(e) => {
                                const val = e.target.value;
                                setSections((prev) =>
                                  prev.map((s, i) => (i === idx ? { ...s, section_title: val } : s))
                                );
                              }}
                              className="h-8 text-xs"
                            />
                            <Input
                              type="number"
                              placeholder="Question Count"
                              value={sec.question_count}
                              onChange={(e) => {
                                const val = parseInt(e.target.value, 10) || 1;
                                setSections((prev) =>
                                  prev.map((s, i) => (i === idx ? { ...s, question_count: val } : s))
                                );
                              }}
                              className="h-8 text-xs"
                            />
                            <Input
                              type="number"
                              placeholder="Marks per question"
                              value={sec.marks_per_question || ""}
                              onChange={(e) => {
                                const val = parseFloat(e.target.value) || null;
                                setSections((prev) =>
                                  prev.map((s, i) => (i === idx ? { ...s, marks_per_question: val } : s))
                                );
                              }}
                              className="h-8 text-xs"
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Additional Guidance & Toggles */}
                <div className="space-y-4 pt-2 border-t border-[var(--outline-variant)]">
                  <div className="flex flex-wrap items-center gap-6">
                    <label className="flex items-center gap-2 cursor-pointer text-xs font-medium">
                      <Checkbox
                        checked={generateAnswerKey}
                        onCheckedChange={(checked) => setGenerateAnswerKey(!!checked)}
                      />
                      <span>Generate Answer Key for Teachers</span>
                    </label>

                    <label className="flex items-center gap-2 cursor-pointer text-xs font-medium">
                      <Checkbox
                        checked={generateRubrics}
                        onCheckedChange={(checked) => setGenerateRubrics(!!checked)}
                      />
                      <span>Generate Marking Rubrics for Descriptive Questions</span>
                    </label>
                  </div>

                  <div className="space-y-1">
                    <Label className="text-xs font-semibold">
                      Additional Teacher Instructions (Optional)
                    </Label>
                    <Textarea
                      placeholder="e.g. Include 1 scenario-based question, emphasize practical applications, avoid overly mathematical proofs."
                      value={additionalInstructions}
                      onChange={(e) => setAdditionalInstructions(e.target.value)}
                      rows={2}
                      className="text-xs"
                    />
                  </div>
                </div>

                {/* Error Banner */}
                {generationError && (
                  <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/30 text-xs text-red-600 dark:text-red-400 flex items-center gap-2">
                    <span className="material-symbols-outlined text-[18px]">error</span>
                    <span>{generationError}</span>
                  </div>
                )}

                {/* Submit / Generate Button */}
                <div className="pt-2 flex items-center justify-end">
                  <Button
                    type="submit"
                    disabled={generating || selectedMaterialIds.length === 0}
                    className="flex items-center gap-2 px-6 shadow-md font-semibold"
                    style={{ backgroundColor: "var(--primary)", color: "var(--on-primary)" }}
                  >
                    <span className="material-symbols-outlined text-[18px]">
                      {generating ? "autorenew" : "auto_awesome"}
                    </span>
                    {generating ? "Generating Question Paper..." : "Generate Question Paper with AI"}
                  </Button>
                </div>

                {/* Generating Progress State */}
                {generating && (
                  <div className="p-6 rounded-2xl bg-[var(--surface-container)] border border-[var(--primary)]/30 text-center space-y-3 animate-pulse">
                    <div className="flex justify-center">
                      <span className="material-symbols-outlined text-amber-500 text-[36px] animate-spin">
                        progress_activity
                      </span>
                    </div>
                    <p className="text-sm font-semibold text-[var(--on-surface)]">
                      SmartClass RAG & Gemini Generating Questions
                    </p>
                    <p className="text-xs text-[var(--on-surface-variant)]">{generationStepText}</p>
                  </div>
                )}
              </div>
            </form>
          )}
        </>
      )}

      {/* ── CONVERT TO ASSESSMENT MODAL ───────────────────────────── */}
      <Dialog open={isConvertModalOpen} onOpenChange={setIsConvertModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base font-bold">
              <span className="material-symbols-outlined text-emerald-600">publish</span>
              Convert Draft to Assessment
            </DialogTitle>
            <DialogDescription className="text-xs">
              This will create a SmartClass Assessment in Draft status, persist all questions to the question bank, and prepare it for scheduling or publishing.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2 text-xs">
            {convertError && (
              <div className="p-2.5 rounded-lg bg-red-500/10 border border-red-500/30 text-red-600">
                {convertError}
              </div>
            )}

            <div className="space-y-1">
              <Label className="text-xs font-medium">Assessment Type</Label>
              <Select value={convertType} onValueChange={setConvertType}>
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="exam">Midterm / Final Exam</SelectItem>
                  <SelectItem value="quiz">Class Quiz</SelectItem>
                  <SelectItem value="practice">Practice Assessment</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs font-medium">Passing Marks</Label>
                <Input
                  type="number"
                  placeholder="e.g. 40"
                  value={convertPassingMarks}
                  onChange={(e) => setConvertPassingMarks(e.target.value)}
                  className="h-8 text-xs"
                />
              </div>

              <div className="space-y-1">
                <Label className="text-xs font-medium">Attempt Limit</Label>
                <Input
                  type="number"
                  min="1"
                  max="10"
                  value={convertAttemptLimit}
                  onChange={(e) => setConvertAttemptLimit(e.target.value)}
                  className="h-8 text-xs"
                />
              </div>
            </div>

            <label className="flex items-center gap-2 cursor-pointer pt-1">
              <Checkbox
                checked={convertRandomize}
                onCheckedChange={(checked) => setConvertRandomize(!!checked)}
              />
              <span>Randomize question order for students</span>
            </label>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsConvertModalOpen(false)}
              className="text-xs"
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleConvert}
              disabled={converting}
              className="text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-semibold"
            >
              {converting ? "Converting..." : "Convert & Open Assessment"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── REGENERATE SINGLE QUESTION MODAL ──────────────────────── */}
      <Dialog open={isRegenModalOpen} onOpenChange={setIsRegenModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base font-bold">
              <span className="material-symbols-outlined text-sky-600">autorenew</span>
              Regenerate Question
            </DialogTitle>
            <DialogDescription className="text-xs">
              Gemini will regenerate this question using the same material RAG grounding constraints.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2 text-xs">
            <div className="space-y-1">
              <Label className="text-xs font-medium">Question Type Override (Optional)</Label>
              <Select value={regenType} onValueChange={(v) => setRegenType(v as QpQuestionType)}>
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue placeholder="Keep current type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="mcq_single">Multiple Choice (MCQ)</SelectItem>
                  <SelectItem value="true_false">True / False</SelectItem>
                  <SelectItem value="short_answer">Short Answer</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-medium">Specific Guidance for this Question</Label>
              <Textarea
                placeholder="e.g. Focus on memory cache hierarchy; make the question slightly more challenging."
                value={regenInstructions}
                onChange={(e) => setRegenInstructions(e.target.value)}
                rows={3}
                className="text-xs"
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsRegenModalOpen(false)}
              className="text-xs"
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleRegenerateQuestion}
              className="text-xs bg-sky-600 hover:bg-sky-700 text-white font-semibold"
            >
              Regenerate with Gemini
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
