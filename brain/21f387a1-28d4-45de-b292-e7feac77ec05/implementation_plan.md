# Step 10.10: Evaluation & Grading Implementation Plan

Implement server-side automatic evaluation, persistent result records, manual grading for short answers, secure student result review, and teacher grading workflows.

## User Review Required

> [!IMPORTANT]
> All grading calculations, mark assignments, percentages, and pass/fail thresholds are strictly executed on the server. Active in-progress attempts never leak answer keys or correct answers.

> [!NOTE]
> Evaluation is triggered automatically upon attempt submission or expiry, is completely idempotent, and relies strictly on frozen `assessment_question_snapshot` data to guarantee historical grading stability.

## Proposed Changes

### 1. Database & Migrations

#### [NEW] [b1f4a92c3d85_add_assessment_results_and_grading.py](file:///d:/Smartclass_AI/backend/alembic/versions/b1f4a92c3d85_add_assessment_results_and_grading.py)
- New alembic migration revising `a9f3b2c1d874`.
- Creates `tbl_assessment_results` with unique constraint on `result_attempt_id`.
- Creates `tbl_assessment_result_questions` with unique constraint on `(result_question_result_id, result_question_assessment_question_id)`.
- Foreign keys with `ondelete="CASCADE"`.

#### [MODIFY] [models.py](file:///d:/Smartclass_AI/backend/app/modules/assessments/models.py)
- Add `ResultStatus`, `GradingStatus`, `CorrectnessStatus` enums.
- Add `AssessmentResult` model mapped to `tbl_assessment_results`.
- Add `AssessmentResultQuestion` model mapped to `tbl_assessment_result_questions`.
- Wire relationships to `Assessment`, `AssessmentAttempt`, `AssessmentQuestion`, and `User`.

---

### 2. Backend Evaluation Domain, Service & Repository

#### [MODIFY] [repository.py](file:///d:/Smartclass_AI/backend/app/modules/assessments/repository.py)
- Add `get_result_by_attempt_id(attempt_id)`.
- Add `get_result_by_id(result_id)`.
- Add `create_result(...)`.
- Add `create_result_question(...)`.
- Add `update_result_question_grade(...)`.
- Add `update_result(...)`.
- Add `list_assessment_results(assessment_id)`.

#### [MODIFY] [service.py](file:///d:/Smartclass_AI/backend/app/modules/assessments/service.py)
- Implement `evaluate_attempt(attempt_id, org_id)`:
  - Extract question snapshots and student answers.
  - Grade MCQ Single / True-False (exact option match).
  - Grade MCQ Multiple (exact set match).
  - Grade Short Answer (set pending manual grading if text present, 0/graded if unanswered).
  - Calculate obtained marks, percentage, correct/incorrect/unanswered/pending counts, and pass/fail.
  - Persist `AssessmentResult` and question items.
- Integrate `evaluate_attempt` directly into `submit_attempt` and auto-expiry transitions.
- Implement `get_attempt_result(...)` with RBAC checks and student answer key sanitization during in-progress (and full review upon submission/expiry).
- Implement `grade_question(...)` for teacher manual grading and result recalculation.
- Implement `list_assessment_results(...)` for teacher overview.

#### [MODIFY] [schemas.py](file:///d:/Smartclass_AI/backend/app/modules/assessments/schemas.py)
- Add `ManualGradeInput` (marks_awarded, feedback).
- Add `AssessmentResultQuestionResponse`.
- Add `AssessmentResultResponse`.
- Add `TeacherAssessmentResultSummaryResponse`.

#### [MODIFY] [assessments.py](file:///d:/Smartclass_AI/backend/app/api/v1/assessments.py)
- `GET /{assessment_id}/attempts/{attempt_id}/result` — Get detailed attempt result.
- `PUT /{assessment_id}/attempts/{attempt_id}/questions/{question_id}/grade` — Teacher manual grading.
- `GET /{assessment_id}/results` — Teacher view of all results/attempts for an assessment.

---

### 3. Frontend Implementation

#### [MODIFY] [assessments.ts](file:///d:/Smartclass_AI/frontend/src/lib/assessments.ts)
- Add TypeScript interfaces: `ResultStatus`, `GradingStatus`, `CorrectnessStatus`, `AssessmentResultQuestion`, `AssessmentResult`, `ManualGradeInput`.
- Add API clients: `fetchAttemptResult`, `gradeAssessmentQuestion`, `fetchAssessmentResults`.

#### [NEW] [page.tsx (Result Page)](file:///d:/Smartclass_AI/frontend/src/app/classroom/assessments/[assessmentId]/attempt/[attemptId]/result/page.tsx)
- Student / Teacher assessment result screen:
  - Score summary card: Obtained marks, total marks, percentage, pass/fail status, and pending manual grading alert.
  - Metric chips: Correct, Incorrect, Unanswered, Pending counts.
  - Question-by-question review: Question text, student answer, correctness badge, marks breakdown, teacher feedback, and option explanations.

#### [MODIFY] [page.tsx (Attempt Taking)](file:///d:/Smartclass_AI/frontend/src/app/classroom/assessments/[assessmentId]/attempt/[attemptId]/page.tsx)
- Add "View Assessment Result" action button on the submitted & expired screens to navigate directly to the result page.

#### [MODIFY] [page.tsx (Assessment Overview)](file:///d:/Smartclass_AI/frontend/src/app/classroom/assessments/[assessmentId]/page.tsx)
- For students: In Attempt History, show obtained marks / result badge and "View Result" button.
- For teachers: Add "Submissions & Grading" tab showing student attempt list, score summary, grading status (Pending / Graded), and an inline/modal grading drawer to review and grade short-answer questions.

---

### 4. Comprehensive Testing

#### [NEW] [test_evaluation.py](file:///d:/Smartclass_AI/backend/tests/test_evaluation.py)
- 40+ tests covering:
  - MCQ Single (correct, incorrect, unanswered)
  - MCQ Multiple (exact match, different order, missing option, extra option)
  - True/False (correct, incorrect, unanswered)
  - Short Answer (pending manual grading, teacher grading, score recalculation, invalid score validation)
  - Result calculations (marks, percentage, counts, pass/fail thresholds)
  - Idempotency & duplicate submission safety
  - Security (student isolation, teacher authorization, cross-tenant protection)
  - Immutable question snapshot protection
  - Malformed answer safety

## Verification Plan

### Automated Tests
- Run `tests/test_evaluation.py`: `.venv\Scripts\python.exe -m pytest tests/test_evaluation.py -v`
- Run all backend tests: `.venv\Scripts\python.exe -m pytest tests/ -v`
- Run TypeScript typecheck: `npx tsc --noEmit` from `d:\Smartclass_AI\frontend`

### Manual Verification
- Test student taking exam with MCQ and Short Answer.
- Verify instant evaluation of MCQ single, MCQ multiple, True/False on submit.
- Verify short answer shows as "Pending Manual Grading".
- Verify teacher can grade the short answer, enter feedback, and see overall score/passed status immediately recalculate.
