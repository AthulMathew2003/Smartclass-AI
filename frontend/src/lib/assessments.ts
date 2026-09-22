import { apiFetch } from "./api";

export type AssessmentType = "quiz" | "exam" | "practice";
export type AssessmentStatus = "draft" | "published" | "active" | "closed" | "archived";
export type QuestionType = "mcq_single" | "mcq_multiple" | "true_false" | "short_answer";
export type QuestionStatus = "active" | "archived";

export interface Assessment {
  assessment_id: string;
  assessment_subject_id: string;
  assessment_title: string;
  assessment_description?: string | null;
  assessment_type: AssessmentType;
  assessment_status: AssessmentStatus;
  assessment_duration_minutes?: number | null;
  assessment_start_at?: string | null;
  assessment_end_at?: string | null;
  assessment_total_marks: number | string;
  assessment_passing_marks?: number | string | null;
  assessment_attempt_limit: number;
  assessment_randomize_questions: boolean;
  assessment_created_by?: string | null;
  assessment_created_at: string;
  assessment_updated_at: string;

  // Enriched fields
  total_questions?: number;
  subject_name?: string | null;
  workspace_id?: string | null;
  workspace_name?: string | null;
}

export interface AssessmentCreateInput {
  subject_id: string;
  title: string;
  description?: string | null;
  type?: AssessmentType;
  duration_minutes?: number | null;
  start_at?: string | null;
  end_at?: string | null;
  total_marks?: number;
  passing_marks?: number | null;
  attempt_limit?: number;
  randomize_questions?: boolean;
}

export interface AssessmentUpdateInput {
  title?: string;
  description?: string | null;
  type?: AssessmentType;
  duration_minutes?: number | null;
  start_at?: string | null;
  end_at?: string | null;
  total_marks?: number;
  passing_marks?: number | null;
  attempt_limit?: number;
  randomize_questions?: boolean;
}

export interface FetchAssessmentsOptions {
  subjectId?: string;
  workspaceId?: string;
  status?: AssessmentStatus | "all";
  search?: string;
}

export interface QuestionOption {
  option_id?: string;
  option_question_id?: string;
  option_text: string;
  option_order: number;
  option_is_correct?: boolean;
  is_correct?: boolean;
}

export interface QuestionBankItem {
  question_id: string;
  question_subject_id: string;
  question_type: QuestionType;
  question_text: string;
  question_default_marks: number | string;
  question_explanation?: string | null;
  question_status: QuestionStatus;
  question_created_by?: string | null;
  question_created_at: string;
  question_updated_at: string;
  options: QuestionOption[];
}

export interface QuestionOptionCreateInput {
  option_text: string;
  option_order: number;
  is_correct?: boolean;
  option_is_correct?: boolean;
}

export interface QuestionBankItemCreateInput {
  question_type: QuestionType;
  question_text: string;
  default_marks?: number;
  question_explanation?: string | null;
  options?: QuestionOptionCreateInput[];
}

export interface QuestionBankItemUpdateInput {
  question_type?: QuestionType;
  question_text?: string;
  default_marks?: number;
  question_explanation?: string | null;
  options?: QuestionOptionCreateInput[];
}

export interface AssessmentQuestion {
  assessment_question_id: string;
  assessment_question_assessment_id: string;
  assessment_question_question_id?: string | null;
  assessment_question_order: number;
  assessment_question_marks: number | string;
  assessment_question_created_at: string;
  question_type: QuestionType;
  question_text: string;
  question_explanation?: string | null;
  options: QuestionOption[];

  // Compatibility aliases
  question_id?: string;
  question_order?: number;
  question_marks?: number | string;
}

export interface AssessmentAddQuestionInput {
  question_id: string;
  marks?: number;
  order?: number;
}

export interface AssessmentCreateAndAddQuestionInput {
  question_type: QuestionType;
  question_text: string;
  marks: number;
  question_explanation?: string | null;
  options?: QuestionOptionCreateInput[];
  order?: number;
}

// ── Assessment API Functions ───────────────────────────────────

export async function fetchAssessments(
  optionsOrSubjectId?: string | FetchAssessmentsOptions,
  status?: AssessmentStatus | "all"
): Promise<Assessment[]> {
  const params = new URLSearchParams();
  if (typeof optionsOrSubjectId === "object" && optionsOrSubjectId !== null) {
    if (optionsOrSubjectId.subjectId) params.append("subject_id", optionsOrSubjectId.subjectId);
    if (optionsOrSubjectId.workspaceId) params.append("workspace_id", optionsOrSubjectId.workspaceId);
    if (optionsOrSubjectId.status && optionsOrSubjectId.status !== "all") {
      params.append("status", optionsOrSubjectId.status);
    }
    if (optionsOrSubjectId.search) params.append("search", optionsOrSubjectId.search.trim());
  } else {
    if (optionsOrSubjectId) {
      params.append("subject_id", optionsOrSubjectId);
    }
    if (status && status !== "all") {
      params.append("status", status);
    }
  }
  const queryStr = params.toString() ? `?${params.toString()}` : "";
  return await apiFetch<Assessment[]>(`/assessments${queryStr}`);
}

export async function fetchAssessment(
  assessmentId: string,
  subjectId?: string
): Promise<Assessment> {
  const queryStr = subjectId ? `?subject_id=${encodeURIComponent(subjectId)}` : "";
  return await apiFetch<Assessment>(`/assessments/${encodeURIComponent(assessmentId)}${queryStr}`);
}

export async function createAssessment(
  payload: AssessmentCreateInput
): Promise<Assessment> {
  return await apiFetch<Assessment>("/assessments", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function updateAssessment(
  assessmentId: string,
  payload: AssessmentUpdateInput,
  subjectId?: string
): Promise<Assessment> {
  const queryStr = subjectId ? `?subject_id=${encodeURIComponent(subjectId)}` : "";
  return await apiFetch<Assessment>(`/assessments/${encodeURIComponent(assessmentId)}${queryStr}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function publishAssessment(
  assessmentId: string,
  subjectId?: string
): Promise<Assessment> {
  const queryStr = subjectId ? `?subject_id=${encodeURIComponent(subjectId)}` : "";
  return await apiFetch<Assessment>(`/assessments/${encodeURIComponent(assessmentId)}/publish${queryStr}`, {
    method: "POST",
  });
}

export async function closeAssessment(
  assessmentId: string,
  subjectId?: string
): Promise<Assessment> {
  const queryStr = subjectId ? `?subject_id=${encodeURIComponent(subjectId)}` : "";
  return await apiFetch<Assessment>(`/assessments/${encodeURIComponent(assessmentId)}/close${queryStr}`, {
    method: "POST",
  });
}

export async function archiveAssessment(
  assessmentId: string,
  subjectId?: string
): Promise<Assessment> {
  const queryStr = subjectId ? `?subject_id=${encodeURIComponent(subjectId)}` : "";
  return await apiFetch<Assessment>(`/assessments/${encodeURIComponent(assessmentId)}/archive${queryStr}`, {
    method: "POST",
  });
}

export async function deleteAssessment(
  assessmentId: string,
  subjectId?: string
): Promise<{ message: string; assessment_id: string }> {
  const queryStr = subjectId ? `?subject_id=${encodeURIComponent(subjectId)}` : "";
  return await apiFetch<{ message: string; assessment_id: string }>(
    `/assessments/${encodeURIComponent(assessmentId)}${queryStr}`,
    { method: "DELETE" }
  );
}

// ── Assessment Question Builder API Functions ─────────────────

export async function fetchAssessmentQuestions(
  assessmentId: string
): Promise<AssessmentQuestion[]> {
  return await apiFetch<AssessmentQuestion[]>(
    `/assessments/${encodeURIComponent(assessmentId)}/questions`
  );
}

export async function addQuestionToAssessment(
  assessmentId: string,
  questionId: string,
  marks?: number,
  order?: number
): Promise<AssessmentQuestion> {
  return await apiFetch<AssessmentQuestion>(
    `/assessments/${encodeURIComponent(assessmentId)}/questions/from-bank`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question_id: questionId, marks, order }),
    }
  );
}

export async function createAndAddQuestionToAssessment(
  assessmentId: string,
  payload: AssessmentCreateAndAddQuestionInput
): Promise<AssessmentQuestion> {
  return await apiFetch<AssessmentQuestion>(
    `/assessments/${encodeURIComponent(assessmentId)}/questions`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );
}

export async function updateAssessmentQuestion(
  assessmentId: string,
  assessmentQuestionId: string,
  payload: { marks?: number; order?: number }
): Promise<AssessmentQuestion> {
  return await apiFetch<AssessmentQuestion>(
    `/assessments/${encodeURIComponent(assessmentId)}/questions/${encodeURIComponent(assessmentQuestionId)}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );
}

export async function removeAssessmentQuestion(
  assessmentId: string,
  assessmentQuestionId: string
): Promise<{ message: string; assessment_question_id: string }> {
  return await apiFetch<{ message: string; assessment_question_id: string }>(
    `/assessments/${encodeURIComponent(assessmentId)}/questions/${encodeURIComponent(assessmentQuestionId)}`,
    { method: "DELETE" }
  );
}

export async function reorderAssessmentQuestions(
  assessmentId: string,
  questionIds: string[]
): Promise<AssessmentQuestion[]> {
  return await apiFetch<AssessmentQuestion[]>(
    `/assessments/${encodeURIComponent(assessmentId)}/questions/reorder`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question_ids: questionIds }),
    }
  );
}

// ── Subject Question Bank API Functions ───────────────────────

export async function fetchSubjectQuestions(
  subjectId: string,
  options?: { questionType?: QuestionType; search?: string; includeArchived?: boolean }
): Promise<QuestionBankItem[]> {
  const params = new URLSearchParams();
  if (options?.questionType) params.append("question_type", options.questionType);
  if (options?.search) params.append("search", options.search.trim());
  if (options?.includeArchived) params.append("include_archived", "true");
  const queryStr = params.toString() ? `?${params.toString()}` : "";
  return await apiFetch<QuestionBankItem[]>(
    `/subjects/${encodeURIComponent(subjectId)}/questions${queryStr}`
  );
}

export async function createSubjectQuestion(
  subjectId: string,
  payload: QuestionBankItemCreateInput
): Promise<QuestionBankItem> {
  return await apiFetch<QuestionBankItem>(
    `/subjects/${encodeURIComponent(subjectId)}/questions`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );
}

export async function getSubjectQuestion(
  subjectId: string,
  questionId: string
): Promise<QuestionBankItem> {
  return await apiFetch<QuestionBankItem>(
    `/subjects/${encodeURIComponent(subjectId)}/questions/${encodeURIComponent(questionId)}`
  );
}

export async function updateSubjectQuestion(
  subjectId: string,
  questionId: string,
  payload: QuestionBankItemUpdateInput
): Promise<QuestionBankItem> {
  return await apiFetch<QuestionBankItem>(
    `/subjects/${encodeURIComponent(subjectId)}/questions/${encodeURIComponent(questionId)}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );
}

export async function deleteSubjectQuestion(
  subjectId: string,
  questionId: string
): Promise<{ message: string; question_id: string }> {
  return await apiFetch<{ message: string; question_id: string }>(
    `/subjects/${encodeURIComponent(subjectId)}/questions/${encodeURIComponent(questionId)}`,
    { method: "DELETE" }
  );
}

// Backwards compatibility aliases
export type Question = AssessmentQuestion;
export type QuestionCreateInput = AssessmentCreateAndAddQuestionInput;
export type QuestionUpdateInput = { marks?: number; order?: number };
export const fetchQuestions = fetchAssessmentQuestions;
export const createQuestion = createAndAddQuestionToAssessment;
export const updateQuestion = updateAssessmentQuestion;
export const deleteQuestion = removeAssessmentQuestion;
export const reorderQuestions = reorderAssessmentQuestions;
