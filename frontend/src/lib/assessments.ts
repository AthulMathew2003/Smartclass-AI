import { apiFetch, getAuthenticatedToken } from "./api";
import { API_BASE_URL } from "./auth";

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
  assessment_leaderboard_enabled?: boolean;
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
  leaderboard_enabled?: boolean;
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
  leaderboard_enabled?: boolean;
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
  question_expected_answer?: string | null;
  question_rubric?: string | null;
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
  question_expected_answer?: string | null;
  question_rubric?: string | null;
  options?: QuestionOptionCreateInput[];
}

export interface QuestionBankItemUpdateInput {
  question_type?: QuestionType;
  question_text?: string;
  default_marks?: number;
  question_explanation?: string | null;
  question_expected_answer?: string | null;
  question_rubric?: string | null;
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

// ── Exam Attempts & Taking Flow Types & Functions ─────────────

export type AttemptStatus = "in_progress" | "submitted" | "expired";

export interface StudentQuestionOption {
  option_id?: string;
  option_text: string;
  option_order: number;
}

export interface StudentAttemptQuestion {
  assessment_question_id: string;
  order_index: number;
  question_type: QuestionType;
  question_text: string;
  marks: number | string;
  options: StudentQuestionOption[];
}

export interface StudentAttemptAnswer {
  selected_option_id?: string;
  selected_option_ids?: string[];
  text_answer?: string;
}

export interface AssessmentAttempt {
  attempt_id: string;
  attempt_assessment_id: string;
  attempt_student_id: string;
  attempt_number: number;
  attempt_status: AttemptStatus;
  attempt_started_at: string;
  attempt_expires_at?: string | null;
  attempt_submitted_at?: string | null;
  attempt_question_order: string[];
  questions: StudentAttemptQuestion[];
  answers: Record<string, StudentAttemptAnswer>;
}

export interface AssessmentAttemptSummary {
  attempt_id: string;
  attempt_assessment_id: string;
  attempt_student_id: string;
  attempt_number: number;
  attempt_status: AttemptStatus;
  attempt_started_at: string;
  attempt_expires_at?: string | null;
  attempt_submitted_at?: string | null;
  answers_count: number;
}

export async function startAssessmentAttempt(
  assessmentId: string
): Promise<AssessmentAttempt> {
  return await apiFetch<AssessmentAttempt>(
    `/assessments/${encodeURIComponent(assessmentId)}/start`,
    {
      method: "POST",
    }
  );
}

export async function fetchStudentAttempts(
  assessmentId: string
): Promise<AssessmentAttemptSummary[]> {
  return await apiFetch<AssessmentAttemptSummary[]>(
    `/assessments/${encodeURIComponent(assessmentId)}/attempts`
  );
}

export async function fetchAssessmentAttempt(
  assessmentId: string,
  attemptId: string
): Promise<AssessmentAttempt> {
  return await apiFetch<AssessmentAttempt>(
    `/assessments/${encodeURIComponent(assessmentId)}/attempts/${encodeURIComponent(attemptId)}`
  );
}

export async function saveAttemptAnswer(
  assessmentId: string,
  attemptId: string,
  questionId: string,
  answer: StudentAttemptAnswer
): Promise<{ status: string; attempt_id: string; assessment_question_id: string }> {
  return await apiFetch<{ status: string; attempt_id: string; assessment_question_id: string }>(
    `/assessments/${encodeURIComponent(assessmentId)}/attempts/${encodeURIComponent(attemptId)}/answers/${encodeURIComponent(questionId)}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(answer),
    }
  );
}

export async function submitAssessmentAttempt(
  assessmentId: string,
  attemptId: string
): Promise<AssessmentAttempt> {
  return await apiFetch<AssessmentAttempt>(
    `/assessments/${encodeURIComponent(assessmentId)}/attempts/${encodeURIComponent(attemptId)}/submit`,
    {
      method: "POST",
    }
  );
}

// ── Assessment Evaluation & Result Types & Functions ──────────

export type ResultStatus = "pending_manual_grading" | "completed";
export type GradingStatus = "pending" | "graded";
export type CorrectnessStatus = "correct" | "incorrect" | "unanswered" | "pending";
export type GradingSource = "objective" | "ai" | "teacher";
export type AiEvaluationStatus = "none" | "completed" | "review_required" | "failed" | "skipped";

export interface AiEvaluationDetail {
  suggested_marks?: number;
  max_marks?: number;
  explanation?: string;
  strengths?: string[];
  missing_concepts?: string[];
  confidence?: number;
  review_recommended?: boolean;
  student_feedback?: string;
  evaluation_status?: string;
  grading_source?: string;
  sources?: Array<{
    material_id?: string;
    material_title?: string;
    filename?: string;
    score?: number;
  }>;
}

export interface AssessmentResultQuestion {
  result_question_id: string;
  assessment_question_id: string;
  order: number;
  question_type: QuestionType;
  question_text: string;
  question_explanation?: string | null;
  question_expected_answer?: string | null;
  question_rubric?: string | null;
  options: QuestionOption[];
  answer_value?: StudentAttemptAnswer | null;
  marks_available: number | string;
  marks_awarded: number | string;
  correctness: CorrectnessStatus;
  grading_status: GradingStatus;
  feedback?: string | null;
  grading_source?: GradingSource;
  ai_evaluation_status?: AiEvaluationStatus;
  ai_suggested_marks?: number | string | null;
  ai_confidence?: number | null;
  ai_explanation?: string | null;
  ai_evaluation?: AiEvaluationDetail | null;
  teacher_reviewed?: boolean;
  graded_by?: string | null;
  graded_at?: string | null;
}

export interface AssessmentResult {
  result_id: string;
  attempt_id: string;
  assessment_id: string;
  student_id: string;
  assessment_title?: string;
  attempt_number: number;
  attempt_status: AttemptStatus;
  attempt_started_at: string;
  attempt_submitted_at?: string | null;
  total_marks: number | string;
  obtained_marks: number | string;
  percentage: number | string;
  passed?: boolean | null;
  status: ResultStatus;
  correct_count: number;
  incorrect_count: number;
  unanswered_count: number;
  pending_count: number;
  graded_at?: string | null;
  questions: AssessmentResultQuestion[];
}

export interface TeacherAssessmentResultSummary {
  result_id?: string | null;
  attempt_id: string;
  student_id: string;
  student_name?: string | null;
  student_email?: string | null;
  attempt_number: number;
  attempt_status: AttemptStatus;
  total_marks: number | string;
  obtained_marks: number | string;
  percentage: number | string;
  passed?: boolean | null;
  status: ResultStatus;
  pending_count: number;
  started_at: string;
  submitted_at?: string | null;
}

export interface ManualGradeInput {
  marks_awarded: number;
  feedback?: string | null;
}

export interface TeacherApproveGradeInput {
  marks_awarded?: number;
  feedback?: string | null;
}

export async function fetchAttemptResult(
  assessmentId: string,
  attemptId: string
): Promise<AssessmentResult> {
  return await apiFetch<AssessmentResult>(
    `/assessments/${encodeURIComponent(assessmentId)}/attempts/${encodeURIComponent(attemptId)}/result`
  );
}

export async function gradeAssessmentQuestion(
  assessmentId: string,
  attemptId: string,
  questionId: string,
  input: ManualGradeInput
): Promise<AssessmentResult> {
  return await apiFetch<AssessmentResult>(
    `/assessments/${encodeURIComponent(assessmentId)}/attempts/${encodeURIComponent(attemptId)}/questions/${encodeURIComponent(questionId)}/grade`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }
  );
}

export async function approveAssessmentQuestionGrade(
  assessmentId: string,
  attemptId: string,
  questionId: string,
  input?: TeacherApproveGradeInput
): Promise<AssessmentResult> {
  return await apiFetch<AssessmentResult>(
    `/assessments/${encodeURIComponent(assessmentId)}/attempts/${encodeURIComponent(attemptId)}/questions/${encodeURIComponent(questionId)}/approve`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input || {}),
    }
  );
}

export async function fetchAssessmentResults(
  assessmentId: string
): Promise<TeacherAssessmentResultSummary[]> {
  return await apiFetch<TeacherAssessmentResultSummary[]>(
    `/assessments/${encodeURIComponent(assessmentId)}/results`
  );
}

// ── Assessment Analytics Types & Functions (Step 10.11) ────────

export interface AssessmentAnalyticsOverview {
  total_enrolled_students: number;
  total_students_attempted: number;
  total_attempts: number;
  total_submitted_attempts: number;
  total_expired_attempts: number;
  total_in_progress_attempts: number;
  total_completed_evaluations: number;
  total_pending_manual_grading: number;
  total_passed: number;
  total_failed: number;
  pass_percentage?: number | null;
  participation_rate?: number | null;
}

export interface AssessmentScoreStatistics {
  average_percentage?: number | null;
  median_percentage?: number | null;
  highest_percentage?: number | null;
  lowest_percentage?: number | null;
  average_obtained_marks?: number | null;
  total_marks: number;
  passing_marks?: number | null;
}

export interface AssessmentAttemptStatistics {
  total_attempts: number;
  average_attempts_per_student?: number | null;
  single_attempt_student_count: number;
  multiple_attempts_student_count: number;
}

export interface AssessmentQuestionAnalyticsItem {
  assessment_question_id: string;
  question_order: number;
  question_type: QuestionType;
  question_text: string;
  marks_available: number;
  evaluated_count: number;
  correct_count: number;
  incorrect_count: number;
  unanswered_count: number;
  pending_count: number;
  average_marks_awarded?: number | null;
  accuracy_percentage?: number | null;
}

export interface AssessmentStudentAttemptItem {
  attempt_id: string;
  attempt_number: number;
  attempt_status: AttemptStatus;
  started_at: string;
  submitted_at?: string | null;
  duration_seconds?: number | null;
  obtained_marks?: number | null;
  percentage?: number | null;
  passed?: boolean | null;
  status?: ResultStatus | null;
  pending_count: number;
}

export interface AssessmentStudentPerformanceItem {
  student_id: string;
  student_name?: string | null;
  student_email?: string | null;
  total_attempts: number;
  latest_attempt_number: number;
  latest_attempt_status: AttemptStatus;
  latest_percentage?: number | null;
  latest_obtained_marks?: number | null;
  latest_passed?: boolean | null;
  latest_result_status?: ResultStatus | null;
  best_percentage?: number | null;
  best_obtained_marks?: number | null;
  has_pending_grading: boolean;
  attempts: AssessmentStudentAttemptItem[];
}

export interface AssessmentAnalyticsResponse {
  assessment_id: string;
  assessment_title: string;
  assessment_type: string;
  assessment_status: AssessmentStatus;
  overview: AssessmentAnalyticsOverview;
  score_statistics: AssessmentScoreStatistics;
  attempt_statistics: AssessmentAttemptStatistics;
  question_statistics: AssessmentQuestionAnalyticsItem[];
  student_statistics: AssessmentStudentPerformanceItem[];
}

export interface StudentSelfAnalyticsResponse {
  assessment_id: string;
  assessment_title: string;
  assessment_total_marks: number;
  attempt_limit: number;
  total_attempts_used: number;
  attempts_remaining: number;
  latest_percentage?: number | null;
  latest_obtained_marks?: number | null;
  best_percentage?: number | null;
  best_obtained_marks?: number | null;
  passed?: boolean | null;
  has_pending_grading: boolean;
  attempts: AssessmentStudentAttemptItem[];
}

export async function fetchAssessmentAnalytics(
  assessmentId: string
): Promise<AssessmentAnalyticsResponse> {
  return await apiFetch<AssessmentAnalyticsResponse>(
    `/assessments/${encodeURIComponent(assessmentId)}/analytics`
  );
}

export async function fetchStudentSelfAnalytics(
  assessmentId: string
): Promise<StudentSelfAnalyticsResponse> {
  return await apiFetch<StudentSelfAnalyticsResponse>(
    `/assessments/${encodeURIComponent(assessmentId)}/analytics/self`
  );
}

// ── Step 10.12 Longitudinal Learning & Question Difficulty Analytics ──

export type ObservedDifficultyBand =
  | "easier_observed"
  | "moderate_observed"
  | "harder_observed"
  | "insufficient_sample";

export interface StudentLearningOverview {
  total_assessments_attempted: number;
  total_assessments_completed: number;
  total_assessments_pending_grading: number;
  total_attempts_count: number;
  average_percentage?: number | null;
  best_percentage?: number | null;
  latest_percentage?: number | null;
  total_passed_count: number;
  total_failed_count: number;
}

export interface StudentPerformanceTrendPoint {
  assessment_id: string;
  assessment_title: string;
  subject_id: string;
  subject_name: string;
  attempt_id: string;
  attempt_number: number;
  date: string;
  percentage?: number | null;
  obtained_marks?: number | null;
  total_marks: number;
  passed?: boolean | null;
  status: ResultStatus;
}

export interface StudentLearningTrend {
  recent_average_percentage?: number | null;
  historical_average_percentage?: number | null;
  improvement_from_previous?: number | null;
  recent_window_size: number;
}

export interface StudentSubjectPerformanceItem {
  subject_id: string;
  subject_name: string;
  assessments_attempted: number;
  assessments_completed: number;
  average_percentage?: number | null;
  best_percentage?: number | null;
  latest_percentage?: number | null;
  objective_accuracy_percentage?: number | null;
  passed_count: number;
  failed_count: number;
}

export interface StudentQuestionTypePerformanceItem {
  question_type: QuestionType;
  evaluated_count: number;
  correct_count: number;
  incorrect_count: number;
  unanswered_count: number;
  pending_count: number;
  accuracy_percentage?: number | null;
}

export interface StudentLearningAnalyticsResponse {
  student_id: string;
  student_name?: string | null;
  student_email?: string | null;
  overview: StudentLearningOverview;
  trend: StudentLearningTrend;
  performance_progression: StudentPerformanceTrendPoint[];
  subject_performance: StudentSubjectPerformanceItem[];
  question_type_performance: StudentQuestionTypePerformanceItem[];
  recent_assessments: StudentPerformanceTrendPoint[];
}

export interface QuestionDifficultyAnalyticsItem {
  question_id: string;
  source_question_id?: string | null;
  question_text: string;
  question_type: QuestionType;
  marks_available: number;
  evaluated_count: number;
  correct_count: number;
  incorrect_count: number;
  unanswered_count: number;
  pending_count: number;
  average_marks_awarded?: number | null;
  accuracy_percentage?: number | null;
  difficulty_band: ObservedDifficultyBand;
  difficulty_label: string;
  is_insufficient_sample: boolean;
  assessment_count: number;
}

export interface SubjectQuestionDifficultyResponse {
  subject_id: string;
  subject_name: string;
  total_questions_analyzed: number;
  easier_count: number;
  moderate_count: number;
  harder_count: number;
  insufficient_sample_count: number;
  questions: QuestionDifficultyAnalyticsItem[];
}

export interface SubjectLearningAnalyticsResponse {
  subject_id: string;
  subject_name: string;
  total_assessments: number;
  total_students_enrolled: number;
  total_students_attempted: number;
  average_subject_percentage?: number | null;
  pass_rate_percentage?: number | null;
  total_evaluations_completed: number;
  total_pending_manual_grading: number;
  assessment_trends: Array<{
    assessment_id: string;
    assessment_title: string;
    created_at: string;
    total_attempts: number;
    completed_evaluations: number;
    pending_manual_grading: number;
    average_percentage?: number | null;
    pass_rate?: number | null;
  }>;
  question_difficulty_summary: Record<string, number>;
}

export async function fetchMyLearningAnalytics(): Promise<StudentLearningAnalyticsResponse> {
  return await apiFetch<StudentLearningAnalyticsResponse>("/assessments/analytics/learning/me");
}

export async function fetchStudentLearningAnalytics(
  studentId: string
): Promise<StudentLearningAnalyticsResponse> {
  return await apiFetch<StudentLearningAnalyticsResponse>(
    `/assessments/analytics/learning/students/${encodeURIComponent(studentId)}`
  );
}

export async function fetchSubjectLearningAnalytics(
  subjectId: string
): Promise<SubjectLearningAnalyticsResponse> {
  return await apiFetch<SubjectLearningAnalyticsResponse>(
    `/subjects/${encodeURIComponent(subjectId)}/analytics/learning`
  );
}

export async function fetchSubjectQuestionDifficulty(
  subjectId: string
): Promise<SubjectQuestionDifficultyResponse> {
  return await apiFetch<SubjectQuestionDifficultyResponse>(
    `/subjects/${encodeURIComponent(subjectId)}/analytics/question-difficulty`
  );
}

// ── Step 10.13: Leaderboard & Class Performance Dashboard ────────────

export interface LeaderboardStudentBrief {
  id: string;
  display_name: string;
  profile_image_url?: string | null;
}

export interface AssessmentLeaderboardEntry {
  rank: number;
  student: LeaderboardStudentBrief;
  percentage: number;
  obtained_marks: number;
  total_marks: number;
  attempts_used: number;
  completed_at: string;
  is_current_user: boolean;
}

export interface AssessmentLeaderboardResponse {
  assessment_id: string;
  assessment_title: string;
  leaderboard_enabled: boolean;
  total_ranked_students: number;
  enabled?: boolean;
  total_students?: number;
  my_rank?: number | null;
  my_entry?: AssessmentLeaderboardEntry | null;
  entries: AssessmentLeaderboardEntry[];
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ClassStudentPerformanceItem {
  student_id: string;
  student_name: string;
  student_email?: string | null;
  assessments_completed: number;
  average_percentage?: number | null;
  latest_percentage?: number | null;
  best_percentage?: number | null;
  passed_count: number;
  pending_grading_count: number;
  status_label: string;
}

export interface ClassPerformanceDashboardResponse {
  subject_id: string;
  subject_name: string;
  workspace_id: string;
  workspace_name: string;
  total_students: number;
  participating_students: number;
  participation_rate_percentage: number;
  total_assessments: number;
  completed_evaluations: number;
  class_average_percentage?: number | null;
  class_median_percentage?: number | null;
  class_pass_rate_percentage?: number | null;
  total_pending_manual_grading: number;
  performance_trend: Array<{
    assessment_id: string;
    title: string;
    status: string;
    total_attempts: number;
    participants: number;
    completed_evaluations: number;
    pending_grading: number;
    average_percentage?: number | null;
    median_percentage?: number | null;
    highest_percentage?: number | null;
    lowest_percentage?: number | null;
    pass_rate_percentage?: number | null;
    leaderboard_enabled: boolean;
    created_at: string;
  }>;
  assessment_summaries: Array<{
    assessment_id: string;
    title: string;
    status: string;
    total_attempts: number;
    participants: number;
    completed_evaluations: number;
    pending_grading: number;
    average_percentage?: number | null;
    median_percentage?: number | null;
    highest_percentage?: number | null;
    lowest_percentage?: number | null;
    pass_rate_percentage?: number | null;
    leaderboard_enabled: boolean;
    created_at: string;
  }>;
  student_roster: ClassStudentPerformanceItem[];
  question_difficulty_summary: Record<string, number>;
}

export async function fetchAssessmentLeaderboard(
  assessmentId: string,
  page: number = 1,
  pageSize: number = 20
): Promise<AssessmentLeaderboardResponse> {
  return await apiFetch<AssessmentLeaderboardResponse>(
    `/assessments/${encodeURIComponent(assessmentId)}/leaderboard?page=${page}&page_size=${pageSize}`
  );
}

export async function updateAssessmentLeaderboardSettings(
  assessmentId: string,
  enabled: boolean
): Promise<AssessmentLeaderboardResponse> {
  return await apiFetch<AssessmentLeaderboardResponse>(
    `/assessments/${encodeURIComponent(assessmentId)}/leaderboard-settings`,
    {
      method: "PATCH",
      body: JSON.stringify({ enabled })
    }
  );
}

export async function fetchClassPerformanceDashboard(
  subjectId: string
): Promise<ClassPerformanceDashboardResponse> {
  return await apiFetch<ClassPerformanceDashboardResponse>(
    `/subjects/${encodeURIComponent(subjectId)}/performance`
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


// ── Bulk Question Upload Types & Functions ──────────────────────

export interface BulkUploadValidationErrorItem {
  row: number;
  field?: string | null;
  message: string;
}

export interface BulkUploadPreviewItem {
  row: number;
  question_text: string;
  question_type: QuestionType;
  marks: number | string;
  options_count: number;
  correct_answer?: string | null;
  explanation?: string | null;
  order?: number | null;
  status: string;
}

export interface BulkUploadValidateResponse {
  valid: boolean;
  total_rows: number;
  valid_rows: number;
  error_count: number;
  total_marks: number | string;
  errors: BulkUploadValidationErrorItem[];
  preview: BulkUploadPreviewItem[];
}

export interface BulkUploadImportResponse {
  success: boolean;
  imported_count: number;
  total_marks_added: number | string;
  assessment_total_marks: number | string;
  questions: AssessmentQuestion[];
}

export async function downloadExcelQuestionTemplate(assessmentId?: string): Promise<void> {
  const token = await getAuthenticatedToken();
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
  };
  if (typeof window !== "undefined") {
    const activeOrgId = localStorage.getItem("activeOrganizationId");
    if (activeOrgId) {
      headers["X-Organization-Id"] = activeOrgId;
    }
  }

  const endpoint = assessmentId
    ? `/assessments/${encodeURIComponent(assessmentId)}/questions/bulk-upload/template`
    : `/assessments/bulk-upload/template`;

  const res = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: "GET",
    headers,
    credentials: "include",
  });

  if (!res.ok) {
    let errMsg = "Failed to download Excel template.";
    try {
      const err = await res.json();
      errMsg = err.detail || err.message || errMsg;
    } catch {}
    throw new Error(errMsg);
  }

  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "smartclass_questions_template.xlsx";
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

export async function validateBulkQuestions(
  assessmentId: string,
  file: File
): Promise<BulkUploadValidateResponse> {
  const formData = new FormData();
  formData.append("file", file);

  return await apiFetch<BulkUploadValidateResponse>(
    `/assessments/${encodeURIComponent(assessmentId)}/questions/bulk-upload/validate`,
    {
      method: "POST",
      body: formData,
    }
  );
}

export async function importBulkQuestions(
  assessmentId: string,
  file: File
): Promise<BulkUploadImportResponse> {
  const formData = new FormData();
  formData.append("file", file);

  return await apiFetch<BulkUploadImportResponse>(
    `/assessments/${encodeURIComponent(assessmentId)}/questions/bulk-upload/import`,
    {
      method: "POST",
      body: formData,
    }
  );
}

// ── Question Paper Generator (Step 10.16) ─────────────────────────

export type QpDifficulty = "easy" | "medium" | "hard" | "mixed";
export type QpQuestionType = "mcq_single" | "true_false" | "short_answer";
export type QpDraftStatus = "generating" | "ready" | "failed" | "converted";

export interface QpSectionConfig {
  section_title: string;
  section_instructions?: string | null;
  question_types: QpQuestionType[];
  question_count: number;
  marks_per_question?: number | null;
  difficulty?: QpDifficulty;
}

export interface QpGenerateRequest {
  title: string;
  description?: string | null;
  material_ids: string[];
  topics?: string[] | null;
  total_marks: number;
  duration_minutes?: number | null;
  difficulty?: QpDifficulty;
  total_questions?: number | null;
  question_types?: QpQuestionType[] | null;
  sections?: QpSectionConfig[] | null;
  generate_answer_key?: boolean;
  generate_rubrics?: boolean;
  additional_instructions?: string | null;
}

export interface QpOptionInput {
  text: string;
  is_correct: boolean;
}

export interface QpDraftQuestionUpdateInput {
  question_text?: string;
  marks?: number;
  difficulty?: QpDifficulty;
  options?: QpOptionInput[];
  expected_answer?: string;
  rubric?: string;
  explanation?: string;
  is_flagged?: boolean;
}

export interface QpRegenerateQuestionRequest {
  question_type?: QpQuestionType;
  difficulty?: QpDifficulty;
  marks?: number;
  additional_instructions?: string;
}

export interface QpConvertRequest {
  assessment_type: string;
  passing_marks?: number | null;
  attempt_limit?: number;
  randomize_questions?: boolean;
  start_at?: string | null;
  end_at?: string | null;
}

export interface QpConvertResponse {
  assessment_id: string;
  status: string;
  message: string;
}

export interface QpSourceChunk {
  material_id: string;
  material_title: string;
  chunk_index: number;
  page_number?: number | null;
  slide_number?: number | null;
  content_preview?: string;
}

export interface QpDraftQuestionResponse {
  dq_id: string;
  dq_order: number;
  dq_question_type: string;
  dq_question_text: string;
  dq_marks: number;
  dq_difficulty: string;
  dq_options?: Array<{ text: string; is_correct: boolean }> | null;
  dq_expected_answer?: string | null;
  dq_rubric?: string | null;
  dq_explanation?: string | null;
  dq_source_material_ids: string[];
  dq_source_chunks?: QpSourceChunk[] | null;
  dq_is_flagged: boolean;
  dq_created_at: string;
  dq_updated_at: string;
}

export interface QpValidationIssue {
  severity: "error" | "warning";
  question_index?: number | null;
  message: string;
}

export interface QpValidationResult {
  is_valid: boolean;
  total_marks_actual: number;
  total_marks_expected: number;
  question_count_actual: number;
  issues: QpValidationIssue[];
  flagged_count: number;
}

export interface QpMaterialSummary {
  material_id: string;
  title: string;
  original_filename: string;
  index_status: string;
  chunk_count: number;
}

export interface QpDraftResponse {
  draft_id: string;
  draft_subject_id: string;
  draft_title: string;
  draft_description?: string | null;
  draft_status: QpDraftStatus;
  draft_config: Record<string, any>;
  draft_validation_result?: QpValidationResult | null;
  draft_generation_error?: string | null;
  draft_converted_assessment_id?: string | null;
  draft_created_at: string;
  draft_updated_at: string;
  questions: QpDraftQuestionResponse[];
  subject_name?: string | null;
  material_summaries?: QpMaterialSummary[] | null;
}

export interface QpDraftListItem {
  draft_id: string;
  draft_subject_id: string;
  draft_title: string;
  draft_status: string;
  question_count: number;
  total_marks?: number | null;
  draft_converted_assessment_id?: string | null;
  draft_created_at: string;
  draft_updated_at: string;
}

export interface QpMaterialListResponse {
  subject_id: string;
  subject_name: string;
  materials: QpMaterialSummary[];
}

export async function fetchSubjectMaterialsForQp(
  subjectId: string
): Promise<QpMaterialListResponse> {
  return await apiFetch<QpMaterialListResponse>(
    `/subjects/${encodeURIComponent(subjectId)}/question-paper-drafts/materials`
  );
}

export async function fetchQpDrafts(
  subjectId: string
): Promise<QpDraftListItem[]> {
  return await apiFetch<QpDraftListItem[]>(
    `/subjects/${encodeURIComponent(subjectId)}/question-paper-drafts`
  );
}

export async function generateQpDraft(
  subjectId: string,
  payload: QpGenerateRequest
): Promise<QpDraftResponse> {
  return await apiFetch<QpDraftResponse>(
    `/subjects/${encodeURIComponent(subjectId)}/question-paper-drafts/generate`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function getQpDraft(
  subjectId: string,
  draftId: string
): Promise<QpDraftResponse> {
  return await apiFetch<QpDraftResponse>(
    `/subjects/${encodeURIComponent(subjectId)}/question-paper-drafts/${encodeURIComponent(draftId)}`
  );
}

export async function updateQpDraftMetadata(
  subjectId: string,
  draftId: string,
  title?: string,
  description?: string
): Promise<QpDraftResponse> {
  const params = new URLSearchParams();
  if (title) params.append("title", title);
  if (description !== undefined) params.append("description", description || "");

  return await apiFetch<QpDraftResponse>(
    `/subjects/${encodeURIComponent(subjectId)}/question-paper-drafts/${encodeURIComponent(draftId)}?${params.toString()}`,
    {
      method: "PATCH",
    }
  );
}

export async function updateQpDraftQuestion(
  subjectId: string,
  draftId: string,
  dqId: string,
  payload: QpDraftQuestionUpdateInput
): Promise<QpDraftResponse> {
  return await apiFetch<QpDraftResponse>(
    `/subjects/${encodeURIComponent(subjectId)}/question-paper-drafts/${encodeURIComponent(draftId)}/questions/${encodeURIComponent(dqId)}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    }
  );
}

export async function regenerateQpQuestion(
  subjectId: string,
  draftId: string,
  dqId: string,
  payload: QpRegenerateQuestionRequest
): Promise<QpDraftResponse> {
  return await apiFetch<QpDraftResponse>(
    `/subjects/${encodeURIComponent(subjectId)}/question-paper-drafts/${encodeURIComponent(draftId)}/questions/${encodeURIComponent(dqId)}/regenerate`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function validateQpDraft(
  subjectId: string,
  draftId: string
): Promise<QpDraftResponse> {
  return await apiFetch<QpDraftResponse>(
    `/subjects/${encodeURIComponent(subjectId)}/question-paper-drafts/${encodeURIComponent(draftId)}/validate`,
    {
      method: "POST",
    }
  );
}

export async function convertQpDraftToAssessment(
  subjectId: string,
  draftId: string,
  payload: QpConvertRequest
): Promise<QpConvertResponse> {
  return await apiFetch<QpConvertResponse>(
    `/subjects/${encodeURIComponent(subjectId)}/question-paper-drafts/${encodeURIComponent(draftId)}/convert`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function deleteQpDraft(
  subjectId: string,
  draftId: string
): Promise<void> {
  await apiFetch<void>(
    `/subjects/${encodeURIComponent(subjectId)}/question-paper-drafts/${encodeURIComponent(draftId)}`,
    {
      method: "DELETE",
    }
  );
}





