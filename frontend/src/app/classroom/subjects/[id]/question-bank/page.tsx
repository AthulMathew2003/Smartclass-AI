"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  fetchSubjectQuestions,
  createSubjectQuestion,
  updateSubjectQuestion,
  deleteSubjectQuestion,
  QuestionBankItem,
  QuestionType,
  QuestionOptionCreateInput
} from "@/lib/assessments";
import { fetchSubject, Subject } from "@/lib/subjects";
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

export default function SubjectQuestionBankPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const workspaceIdFromQuery = searchParams.get("workspace_id");
  const subjectId = (params.id || params.subjectId) as string;

  const [subject, setSubject] = useState<Subject | null>(null);
  const [questions, setQuestions] = useState<QuestionBankItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedType, setSelectedType] = useState<string>("all");

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingQuestion, setEditingQuestion] = useState<QuestionBankItem | null>(null);
  const [saving, setSaving] = useState(false);

  // Form State
  const [formType, setFormType] = useState<QuestionType>("mcq_single");
  const [formText, setFormText] = useState("");
  const [formMarks, setFormMarks] = useState("1.00");
  const [formExplanation, setFormExplanation] = useState("");
  const [formOptions, setFormOptions] = useState<QuestionOptionCreateInput[]>([
    { option_text: "", option_order: 1, is_correct: true },
    { option_text: "", option_order: 2, is_correct: false },
    { option_text: "", option_order: 3, is_correct: false },
    { option_text: "", option_order: 4, is_correct: false },
  ]);
  const [formError, setFormError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!subjectId) return;
    try {
      setLoading(true);
      setError(null);
      const [subjData, qData] = await Promise.all([
        fetchSubject(subjectId, workspaceIdFromQuery || undefined),
        fetchSubjectQuestions(subjectId)
      ]);
      setSubject(subjData);
      setQuestions(qData);
    } catch (err: any) {
      setError(err.message || "Failed to load question bank.");
    } finally {
      setLoading(false);
    }
  }, [subjectId, workspaceIdFromQuery]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  function handleOpenCreate() {
    setEditingQuestion(null);
    setFormType("mcq_single");
    setFormText("");
    setFormMarks("1.00");
    setFormExplanation("");
    setFormOptions([
      { option_text: "", option_order: 1, is_correct: true },
      { option_text: "", option_order: 2, is_correct: false },
      { option_text: "", option_order: 3, is_correct: false },
      { option_text: "", option_order: 4, is_correct: false },
    ]);
    setFormError(null);
    setIsModalOpen(true);
  }

  function handleOpenEdit(q: QuestionBankItem) {
    setEditingQuestion(q);
    setFormType(q.question_type);
    setFormText(q.question_text);
    setFormMarks(String(q.question_default_marks));
    setFormExplanation(q.question_explanation || "");
    setFormOptions(
      q.options.map((opt, idx) => ({
        option_text: opt.option_text,
        option_order: opt.option_order || idx + 1,
        is_correct: opt.option_is_correct ?? opt.is_correct ?? false,
      }))
    );
    setFormError(null);
    setIsModalOpen(true);
  }

  function handleTypeChange(newType: QuestionType) {
    setFormType(newType);
    if (newType === "true_false") {
      setFormOptions([
        { option_text: "True", option_order: 1, is_correct: true },
        { option_text: "False", option_order: 2, is_correct: false },
      ]);
    } else if (newType === "short_answer") {
      setFormOptions([]);
    } else if (newType === "mcq_single" || newType === "mcq_multiple") {
      setFormOptions([
        { option_text: "", option_order: 1, is_correct: true },
        { option_text: "", option_order: 2, is_correct: false },
        { option_text: "", option_order: 3, is_correct: false },
        { option_text: "", option_order: 4, is_correct: false },
      ]);
    }
  }

  function updateOptionText(index: number, text: string) {
    setFormOptions((prev) => {
      const next = [...prev];
      next[index].option_text = text;
      return next;
    });
  }

  function toggleOptionCorrect(index: number) {
    setFormOptions((prev) => {
      if (formType === "mcq_single" || formType === "true_false") {
        return prev.map((opt, idx) => ({
          ...opt,
          is_correct: idx === index,
        }));
      } else {
        return prev.map((opt, idx) => (idx === index ? { ...opt, is_correct: !opt.is_correct } : opt));
      }
    });
  }

  function addOption() {
    setFormOptions((prev) => [
      ...prev,
      {
        option_text: "",
        option_order: prev.length + 1,
        is_correct: false,
      },
    ]);
  }

  function removeOption(index: number) {
    setFormOptions((prev) =>
      prev
        .filter((_, idx) => idx !== index)
        .map((opt, idx) => ({ ...opt, option_order: idx + 1 }))
    );
  }

  async function handleSaveQuestion(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);

    const trimmedText = formText.trim();
    if (!trimmedText) {
      setFormError("Question text is required.");
      return;
    }

    const marksNum = parseFloat(formMarks);
    if (isNaN(marksNum) || marksNum <= 0) {
      setFormError("Marks must be a positive number.");
      return;
    }

    if (formType === "mcq_single") {
      const validOptions = formOptions.filter((o) => o.option_text.trim());
      if (validOptions.length < 2) {
        setFormError("Single choice questions must have at least 2 options.");
        return;
      }
      const correctCount = validOptions.filter((o) => o.is_correct).length;
      if (correctCount !== 1) {
        setFormError("Single choice questions must have exactly 1 correct option marked.");
        return;
      }
    } else if (formType === "mcq_multiple") {
      const validOptions = formOptions.filter((o) => o.option_text.trim());
      if (validOptions.length < 2) {
        setFormError("Multiple choice questions must have at least 2 options.");
        return;
      }
      const correctCount = validOptions.filter((o) => o.is_correct).length;
      if (correctCount < 1) {
        setFormError("Multiple choice questions must have at least 1 correct option marked.");
        return;
      }
    } else if (formType === "true_false") {
      const correctCount = formOptions.filter((o) => o.is_correct).length;
      if (correctCount !== 1) {
        setFormError("True/False questions must have exactly 1 correct answer.");
        return;
      }
    }

    const cleanedOptions = formType === "short_answer"
      ? []
      : formOptions.map((o, idx) => ({
          option_text: o.option_text.trim(),
          option_order: idx + 1,
          is_correct: o.is_correct || false,
        }));

    try {
      setSaving(true);
      if (editingQuestion) {
        const updated = await updateSubjectQuestion(subjectId, editingQuestion.question_id, {
          question_type: formType,
          question_text: trimmedText,
          default_marks: marksNum,
          question_explanation: formExplanation.trim() || null,
          options: cleanedOptions,
        });
        setQuestions((prev) => prev.map((q) => (q.question_id === updated.question_id ? updated : q)));
      } else {
        const created = await createSubjectQuestion(subjectId, {
          question_type: formType,
          question_text: trimmedText,
          default_marks: marksNum,
          question_explanation: formExplanation.trim() || null,
          options: cleanedOptions,
        });
        setQuestions((prev) => [created, ...prev]);
      }
      setIsModalOpen(false);
    } catch (err: any) {
      setFormError(err.message || "Failed to save question.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteQuestion(questionId: string) {
    if (!confirm("Are you sure you want to delete this question from the Question Bank?")) return;
    try {
      await deleteSubjectQuestion(subjectId, questionId);
      setQuestions((prev) => prev.filter((q) => q.question_id !== questionId));
    } catch (err: any) {
      alert(err.message || "Failed to delete question.");
    }
  }

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

  // Filtered Questions
  const filteredQuestions = questions.filter((q) => {
    const matchesType = selectedType === "all" || q.question_type === selectedType;
    const matchesSearch =
      !searchQuery.trim() ||
      q.question_text.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (q.question_explanation && q.question_explanation.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesType && matchesSearch;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="flex items-center gap-3 text-sm font-semibold text-[var(--on-surface-variant)]">
          <div className="w-6 h-6 border-2 border-t-transparent border-[var(--primary)] rounded-full animate-spin" />
          Loading Question Bank...
        </div>
      </div>
    );
  }

  const effectiveWorkspaceId = workspaceIdFromQuery || subject?.subject_workspace_id;

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <button
          onClick={() => {
            const query = effectiveWorkspaceId ? `?workspace_id=${effectiveWorkspaceId}` : "";
            router.push(`/classroom/subjects/${subjectId}${query}`);
          }}
          className="text-sm font-medium text-[var(--primary)] hover:underline mb-3 inline-flex items-center gap-1 transition-colors"
        >
          <span className="material-symbols-outlined text-[16px]">arrow_back</span>
          Back to {subject?.subject_name || "Subject"}
        </button>

        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mt-1">
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-[var(--on-surface)] flex items-center gap-2">
                <span className="material-symbols-outlined text-[28px] text-[var(--primary)]">menu_book</span>
                Question Bank
              </h1>
              <Badge variant="outline" className="bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20">
                {questions.length} {questions.length === 1 ? "Question" : "Questions"}
              </Badge>
            </div>
            <p className="text-sm text-[var(--on-surface-variant)] mt-1">
              Reusable question repository for {subject?.subject_name}. Add questions to assessments with frozen snapshots.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Button
              onClick={handleOpenCreate}
              className="flex items-center gap-2 shadow-sm font-medium"
              style={{ backgroundColor: "var(--primary)", color: "var(--on-primary)" }}
            >
              <span className="material-symbols-outlined text-[18px]">add</span>
              Create Question
            </Button>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-2xl border border-red-500/20 bg-red-500/5 text-red-600 dark:text-red-400 text-sm flex items-center gap-2">
          <span className="material-symbols-outlined text-[20px]">error</span>
          <span>{error}</span>
        </div>
      )}

      {/* Control Bar: Search & Type Filter Pills */}
      <div className="flex flex-col md:flex-row gap-4 justify-between items-start md:items-center bg-[var(--surface-container-low)] p-3 rounded-2xl border border-[var(--outline-variant)]">
        <div className="relative w-full md:w-80">
          <span className="material-symbols-outlined absolute left-3 top-2 text-[18px] text-[var(--on-surface-variant)]">
            search
          </span>
          <Input
            type="text"
            placeholder="Search questions by prompt or explanation..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 h-9 text-xs bg-[var(--surface-container-lowest)]"
          />
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0 w-full md:w-auto">
          <span className="material-symbols-outlined text-[18px] text-[var(--on-surface-variant)] mr-1">tune</span>
          {(["all", "mcq_single", "mcq_multiple", "true_false", "short_answer"] as const).map((type) => (
            <button
              key={type}
              onClick={() => setSelectedType(type)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
                selectedType === type
                  ? "bg-[var(--primary)] text-[var(--on-primary)] shadow-sm"
                  : "text-[var(--on-surface-variant)] hover:bg-[var(--surface-container-high)]"
              }`}
            >
              {type === "all" ? "All Types" : type === "mcq_single" ? "Single Choice" : type === "mcq_multiple" ? "Multiple Choice" : type === "true_false" ? "True/False" : "Short Answer"}
            </button>
          ))}
        </div>
      </div>

      {/* Questions Grid/List */}
      {filteredQuestions.length === 0 ? (
        <div className="text-center py-16 px-4 rounded-3xl border border-dashed border-[var(--outline-variant)] bg-[var(--surface-container-lowest)]">
          <span className="material-symbols-outlined text-[48px] text-[var(--on-surface-variant)] opacity-40 mb-3 block">
            help_outline
          </span>
          <h3 className="text-base font-semibold text-[var(--on-surface)]">No questions found</h3>
          <p className="text-sm text-[var(--on-surface-variant)] mt-1 max-w-sm mx-auto">
            {searchQuery || selectedType !== "all"
              ? "No questions match your search or filter criteria."
              : "Your question bank is empty. Create questions here to use them in assessments."}
          </p>
          {!searchQuery && selectedType === "all" && (
            <Button
              onClick={handleOpenCreate}
              className="mt-4 shadow-sm font-medium"
              style={{ backgroundColor: "var(--primary)", color: "var(--on-primary)" }}
            >
              <span className="material-symbols-outlined text-[18px] mr-1.5">add</span>
              Add First Question
            </Button>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {filteredQuestions.map((q, idx) => (
            <div
              key={q.question_id}
              className="bg-[var(--surface-container-lowest)] border border-[var(--outline-variant)] rounded-2xl p-5 shadow-sm hover:border-[var(--outline)] transition"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="space-y-2 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-bold px-2 py-0.5 rounded-md bg-[var(--surface-container-high)] text-[var(--on-surface)]">
                      #{idx + 1}
                    </span>
                    {getQuestionTypeBadge(q.question_type)}
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-[var(--surface-container-low)] text-[var(--on-surface-variant)]">
                      {q.question_default_marks} {Number(q.question_default_marks) === 1 ? "mark" : "marks"}
                    </span>
                  </div>

                  <p className="text-base font-semibold text-[var(--on-surface)] whitespace-pre-wrap">
                    {q.question_text}
                  </p>

                  {/* Options list */}
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

                  {/* Explanation */}
                  {q.question_explanation && (
                    <div className="mt-2.5 p-3 bg-blue-500/10 border border-blue-500/20 rounded-xl text-xs text-blue-700 dark:text-blue-300 flex items-start gap-2">
                      <span className="material-symbols-outlined text-[16px] text-blue-600 flex-shrink-0 mt-0.5">lightbulb</span>
                      <div>
                        <span className="font-semibold">Explanation:</span> {q.question_explanation}
                      </div>
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-1 flex-shrink-0">
                  <Button
                    size="icon"
                    variant="ghost"
                    onClick={() => handleOpenEdit(q)}
                    className="h-8 w-8 text-[var(--on-surface-variant)] hover:text-[var(--on-surface)]"
                    title="Edit question"
                  >
                    <span className="material-symbols-outlined text-[18px]">edit</span>
                  </Button>
                  <Button
                    size="icon"
                    variant="ghost"
                    onClick={() => handleDeleteQuestion(q.question_id)}
                    className="h-8 w-8 text-[var(--on-surface-variant)] hover:text-red-600 hover:bg-red-500/10"
                    title="Delete question"
                  >
                    <span className="material-symbols-outlined text-[18px]">delete</span>
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Question Create/Edit Dialog */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-2xl rounded-3xl bg-white dark:bg-[#1b211e] border-[var(--outline-variant)] p-6 shadow-2xl">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold text-[var(--on-surface)]">
              {editingQuestion ? "Edit Question" : "Create New Question"}
            </DialogTitle>
            <DialogDescription className="text-xs text-[var(--on-surface-variant)]">
              Configure question prompt, answer options, default marks, and teacher explanation.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSaveQuestion} className="space-y-4 pt-2">
            {formError && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-600 dark:text-red-400 text-xs">
                {formError}
              </div>
            )}

            {/* Question Type */}
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
                    onClick={() => handleTypeChange(item.type as QuestionType)}
                    className={`py-2 px-3 text-xs font-semibold rounded-xl border text-center transition ${
                      formType === item.type
                        ? "bg-[var(--primary)] text-[var(--on-primary)] border-transparent shadow-sm"
                        : "bg-[var(--surface-container-low)] border-[var(--outline-variant)] text-[var(--on-surface)] hover:bg-[var(--surface-container-high)]"
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Question Text */}
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-[var(--on-surface-variant)] mb-1.5 block">
                Question Prompt / Text *
              </Label>
              <Textarea
                rows={3}
                value={formText}
                onChange={(e) => setFormText(e.target.value)}
                placeholder="Enter the question prompt here..."
                className="bg-[var(--surface-container-low)] text-sm"
                required
              />
            </div>

            {/* Default Marks */}
            <div>
              <Label className="text-xs font-semibold uppercase tracking-wider text-[var(--on-surface-variant)] mb-1.5 block">
                Default Marks *
              </Label>
              <Input
                type="number"
                step="0.5"
                min="0.5"
                value={formMarks}
                onChange={(e) => setFormMarks(e.target.value)}
                className="w-28 bg-[var(--surface-container-low)] text-sm"
                required
              />
            </div>

            {/* Options Section */}
            {formType !== "short_answer" && (
              <div className="space-y-2.5 pt-2 border-t border-[var(--outline-variant)]">
                <div className="flex items-center justify-between">
                  <Label className="text-xs font-semibold uppercase tracking-wider text-[var(--on-surface-variant)] block">
                    {formType === "true_false"
                      ? "Select Correct Answer *"
                      : "Options & Answer Key (Click checkmark to mark correct)"}
                  </Label>
                  {(formType === "mcq_single" || formType === "mcq_multiple") && (
                    <button
                      type="button"
                      onClick={addOption}
                      className="text-xs text-[var(--primary)] hover:underline inline-flex items-center gap-1 font-semibold"
                    >
                      <span className="material-symbols-outlined text-[14px]">add</span>
                      Add Option
                    </button>
                  )}
                </div>

                {formType === "true_false" ? (
                  <div className="grid grid-cols-2 gap-3 pt-1">
                    {[
                      { label: "True", isCorrectDefault: true },
                      { label: "False", isCorrectDefault: false },
                    ].map((choice) => {
                      const isSelected =
                        formOptions.find(
                          (o) => o.option_text.toLowerCase() === choice.label.toLowerCase()
                        )?.is_correct ?? choice.isCorrectDefault;

                      return (
                        <button
                          type="button"
                          key={choice.label}
                          onClick={() => {
                            setFormOptions([
                              { option_text: "True", option_order: 1, is_correct: choice.label === "True" },
                              { option_text: "False", option_order: 2, is_correct: choice.label === "False" },
                            ]);
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
                    {formOptions.map((opt, idx) => (
                      <div key={idx} className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => toggleOptionCorrect(idx)}
                          className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 transition ${
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
                          onChange={(e) => updateOptionText(idx, e.target.value)}
                          placeholder={`Option ${idx + 1} text...`}
                          className="bg-[var(--surface-container-low)] text-xs h-9"
                          required
                        />
                        {formOptions.length > 2 && (
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            onClick={() => removeOption(idx)}
                            className="h-8 w-8 text-[var(--on-surface-variant)] hover:text-red-600 hover:bg-red-500/10"
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

            {/* Teacher Explanation */}
            <div className="pt-2 border-t border-[var(--outline-variant)]">
              <Label className="text-xs font-semibold uppercase tracking-wider text-[var(--on-surface-variant)] mb-1.5 block">
                Explanation / Solution Guide (Teacher Only)
              </Label>
              <Textarea
                rows={2}
                value={formExplanation}
                onChange={(e) => setFormExplanation(e.target.value)}
                placeholder="Optional rationale or solution guide for teachers..."
                className="bg-[var(--surface-container-low)] text-xs"
              />
            </div>

            <DialogFooter className="pt-3 border-t border-[var(--outline-variant)]">
              <Button type="button" variant="outline" size="sm" onClick={() => setIsModalOpen(false)}>
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={saving}
                style={{ backgroundColor: "var(--primary)", color: "var(--on-primary)" }}
              >
                {saving && <div className="w-3.5 h-3.5 border-2 border-t-transparent border-white rounded-full animate-spin mr-1.5" />}
                {editingQuestion ? "Update Question" : "Save to Question Bank"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
