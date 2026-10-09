# SmartClass AI — Bulk Question Upload for Assessments

## Overview

The Bulk Question Upload feature enables teachers and administrators to import multiple assessment questions with marks, options, answers, and explanations into an assessment from a standardized Excel (`.xlsx`) workbook.

The implementation is **audit-first** and fully adheres to the SmartClass AI question architecture:
1. Reuses existing `tbl_questions` (Subject Question Bank) and `tbl_question_options`.
2. Preserves the immutable snapshot mechanism (`tbl_assessment_questions.assessment_question_snapshot`).
3. Enforces atomic imports (if any validation error exists, 0 questions are imported).
4. Re-calculates assessment `total_marks` server-side upon successful import.
5. Preserves existing RBAC and assessment lifecycle rules (`DRAFT` assessments only).

---

## Supported Question Types

| Type Identifier | User-Friendly Aliases | Options Required | Correct Answer Format | Manual Grading |
|---|---|---|---|---|
| `mcq_single` | `MCQ`, `single_choice`, `single` | At least 2 options (Option A, Option B) | Exactly 1 option key (`A`, `B`, `C`, etc.) or option text | No (Auto-graded) |
| `mcq_multiple` | `mcq_multiple`, `multiple_choice`, `multi` | At least 2 options (Option A, Option B) | Comma-separated keys (e.g. `A, C` or `A,B,D`) | No (Auto-graded) |
| `true_false` | `tf`, `true/false`, `boolean` | Automatic (`True` / `False`) | `TRUE` or `FALSE` (`True`, `False`, `T`, `F`) | No (Auto-graded) |
| `short_answer` | `short`, `sa`, `text`, `essay` | None | Leave empty or teacher reference | Yes (Manual evaluation) |

---

## Excel Template Structure

The template contains 2 sheets:

### Sheet 1: `Questions`
Columns:
1. `question` *(Required)*: The question prompt text (max 5,000 characters).
2. `question_type` *(Required)*: `mcq_single`, `mcq_multiple`, `true_false`, `short_answer`.
3. `marks` *(Required)*: Numeric marks awarded (> 0, e.g. 1.0, 2.5, 5.0).
4. `option_a` *(Conditional)*: Text for Option A (Required for MCQ).
5. `option_b` *(Conditional)*: Text for Option B (Required for MCQ).
6. `option_c` *(Optional)*: Text for Option C.
7. `option_d` *(Optional)*: Text for Option D.
8. `correct_answer` *(Conditional)*: Key(s) corresponding to the correct answer.
9. `explanation` *(Optional)*: Teacher explanation / solution guide.
10. `order` *(Optional)*: Question order index. If omitted, rows preserve the spreadsheet order.

### Sheet 2: `Instructions`
Comprehensive guidelines, formatting rules, required columns, and example questions for all question types.

---

## Example Spreadsheet Data

| question | question_type | marks | option_a | option_b | option_c | option_d | correct_answer | explanation |
|---|---|---|---|---|---|---|---|---|
| What is the capital of India? | mcq_single | 2.0 | New Delhi | Mumbai | Kolkata | Chennai | A | New Delhi is the capital of India. |
| Which are compiled programming languages? | mcq_multiple | 3.0 | C++ | Python | Rust | HTML | A, C | C++ and Rust are compiled languages. |
| In Python, tuples are immutable data structures. | true_false | 1.0 | | | | | TRUE | Tuples cannot be modified after creation. |
| Explain the difference between process and thread. | short_answer | 5.0 | | | | | | Processes have independent memory spaces. |

---

## API Endpoints

### 1. Download Excel Template
- **Method**: `GET`
- **Route**: `/api/v1/assessments/bulk-upload/template` or `/api/v1/assessments/{assessment_id}/questions/bulk-upload/template`
- **Permissions**: `question.create`
- **Response**: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

### 2. Validate Questions Spreadsheet
- **Method**: `POST`
- **Route**: `/api/v1/assessments/{assessment_id}/questions/bulk-upload/validate`
- **Body**: `multipart/form-data` with `file=<excel_file>`
- **Response**:
```json
{
  "valid": true,
  "total_rows": 4,
  "valid_rows": 4,
  "error_count": 0,
  "total_marks": "11.00",
  "errors": [],
  "preview": [
    {
      "row": 2,
      "question_text": "What is the capital of India?",
      "question_type": "mcq_single",
      "marks": "2.00",
      "options_count": 4,
      "correct_answer": "A",
      "explanation": "New Delhi is the capital of India.",
      "order": 1,
      "status": "valid"
    }
  ]
}
```

### 3. Import Questions
- **Method**: `POST`
- **Route**: `/api/v1/assessments/{assessment_id}/questions/bulk-upload/import`
- **Body**: `multipart/form-data` with `file=<excel_file>`
- **Behavior**:
  - Full atomic execution.
  - Returns `422` with validation errors if spreadsheet has errors.
  - Automatically creates Question Bank items (`tbl_questions` + `tbl_question_options`).
  - Attaches immutable Assessment Question snapshots (`tbl_assessment_questions`).
  - Recalculates assessment `assessment_total_marks`.
- **Response**:
```json
{
  "success": true,
  "imported_count": 4,
  "total_marks_added": "11.00",
  "assessment_total_marks": "11.00",
  "questions": [...]
}
```

---

## Security & Reliability Protections

1. **Format & Formula Safety**: `openpyxl` with `data_only=True` avoids execution of Excel macros, formulas, or external links.
2. **File & Batch Limits**: 10 MB maximum upload size; max 500 questions per batch.
3. **Lifecycle Protection**: Imports are strictly rejected with `409 Conflict` if the assessment is `published`, `active`, `closed`, or `archived`.
4. **Tenant Isolation**: Verifies `Organization -> Workspace -> Subject -> Assessment` hierarchy; rejects foreign subject cross-injection.
5. **RBAC**: Requires teacher assignment to the Subject or Organization Owner/Admin role.
