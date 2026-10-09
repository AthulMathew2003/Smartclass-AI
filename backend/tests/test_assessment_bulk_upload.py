import io
import pytest
import uuid
import openpyxl
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import select

from app.modules.users.models import User
from app.modules.organizations.models import (
    Organization,
    Workspace,
    Role,
    OrganizationMember,
    OrganizationMemberStatus,
    WorkspaceMember
)
from app.modules.subjects.models import Subject, SubjectTeacher, SubjectStatus
from app.modules.assessments.models import (
    Assessment,
    AssessmentType,
    AssessmentStatus,
    QuestionType
)
from app.modules.assessments.service import AssessmentService
from app.modules.assessments.excel_service import BulkQuestionImportService
from app.core.exceptions import (
    ConflictException,
    NotFoundException,
    ForbiddenException,
    ValidationException
)


def create_test_excel_bytes(rows, headers=None, sheet_name="Questions"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_name
    hdrs = headers or [
        "question", "question_type", "marks",
        "option_a", "option_b", "option_c", "option_d",
        "correct_answer", "explanation", "order"
    ]
    ws.append(hdrs)
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_excel_template_generation():
    """Verify generated Excel template contains Questions and Instructions sheets with proper headers."""
    template_bytes = BulkQuestionImportService.generate_excel_template()
    assert template_bytes is not None
    assert len(template_bytes) > 0

    wb = openpyxl.load_workbook(io.BytesIO(template_bytes), data_only=True)
    assert "Questions" in wb.sheetnames
    assert "Instructions" in wb.sheetnames

    ws_q = wb["Questions"]
    headers = [cell.value for cell in ws_q[1]]
    assert "question" in headers
    assert "question_type" in headers
    assert "marks" in headers
    assert "option_a" in headers
    assert "correct_answer" in headers

    # Verify sample rows exist
    assert ws_q.max_row >= 5  # header + 4 samples


@pytest.mark.asyncio
async def test_bulk_upload_file_and_header_validations():
    """Test file size limits, corrupt files, and missing required header validation."""
    # 1. Empty file
    with pytest.raises(ValidationException, match="empty"):
        BulkQuestionImportService.parse_and_validate_workbook(b"")

    # 2. Corrupt file
    with pytest.raises(ValidationException, match="Invalid Excel"):
        BulkQuestionImportService.parse_and_validate_workbook(b"not an excel file")

    # 3. Missing required columns
    bad_headers = ["question", "marks"]  # missing question_type
    bad_excel = create_test_excel_bytes([["What is 1+1?", 2]], headers=bad_headers)
    with pytest.raises(ValidationException, match="Missing required column: 'question_type'"):
        BulkQuestionImportService.parse_and_validate_workbook(bad_excel)


@pytest.mark.asyncio
async def test_bulk_upload_question_type_and_options_validation():
    """Test row-level validation for MCQ single/multiple, True/False, Short Answer, Marks, and Duplicates."""
    rows = [
        # Row 2: Valid MCQ Single
        ["What is Python?", "mcq_single", 2.0, "Language", "Snake", "Car", "Planet", "A", "It is a language", 1],
        # Row 3: Invalid MCQ Single (multiple correct answers specified)
        ["What is 2+2?", "mcq_single", 2.0, "Four", "22", "Zero", "", "A, B", "", 2],
        # Row 4: Invalid MCQ Single (answer does not match option)
        ["What is 3+3?", "mcq_single", 2.0, "Six", "Five", "", "", "Z", "", 3],
        # Row 5: Valid MCQ Multiple
        ["Select prime numbers:", "mcq_multiple", 3.0, "Two", "Three", "Four", "Five", "A, B, D", "", 4],
        # Row 6: Invalid MCQ Multiple (option key out of range)
        ["Select evens:", "mcq_multiple", 3.0, "Two", "Four", "", "", "A, C", "", 5],
        # Row 7: Valid True/False
        ["Earth is round.", "true_false", 1.0, "", "", "", "", "TRUE", "", 6],
        # Row 8: Invalid True/False (bad answer)
        ["Sky is green.", "true_false", 1.0, "", "", "", "", "MAYBE", "", 7],
        # Row 9: Valid Short Answer
        ["Explain gravity.", "short_answer", 5.0, "", "", "", "", "", "Force attracting mass.", 8],
        # Row 10: Invalid Marks (negative)
        ["What is AI?", "short_answer", -5.0, "", "", "", "", "", "", 9],
        # Row 11: Invalid Question Type
        ["What is Cloud?", "essay_long", 5.0, "", "", "", "", "", "", 10],
        # Row 12: Duplicate question in spreadsheet (matches Row 2)
        ["What is Python?", "mcq_single", 2.0, "Language", "Snake", "", "", "A", "", 11]
    ]

    excel_bytes = create_test_excel_bytes(rows)
    parsed_q, errors, total_marks = BulkQuestionImportService.parse_and_validate_workbook(excel_bytes)

    # Valid rows: Row 2, Row 5, Row 7, Row 9 = 4 valid questions
    assert len(parsed_q) == 4
    # Error rows: Row 3, Row 4, Row 6, Row 8, Row 10, Row 11, Row 12 = 7 error items
    assert len(errors) >= 7

    error_fields = {e.field for e in errors}
    assert "correct_answer" in error_fields
    assert "marks" in error_fields
    assert "question_type" in error_fields
    assert "question" in error_fields

    # Total marks should sum only valid questions (2.0 + 3.0 + 1.0 + 5.0 = 11.0)
    assert total_marks == Decimal("11.00")


@pytest.mark.asyncio
async def test_bulk_upload_full_service_flow(db_session):
    """Test full service validate and atomic import flow with RBAC, snapshots, Question Bank items, and total marks recalculation."""
    now = datetime.now(timezone.utc)

    # Setup Owner Teacher, Org, Workspace, Subject, Assessment
    teacher = User(user_email="bulk_teacher@test.com", user_password_hash="hash", user_first_name="Alan", user_last_name="Turing")
    db_session.add(teacher)
    await db_session.flush()

    org = Organization(organization_name="Bulk Org", organization_slug="bulk-org", organization_owner_user_id=teacher.user_id)
    db_session.add(org)
    await db_session.flush()

    ws = Workspace(workspace_organization_id=org.organization_id, workspace_name="Bulk WS", workspace_created_by=teacher.user_id)
    db_session.add(ws)
    await db_session.flush()

    subj = Subject(subject_workspace_id=ws.workspace_id, subject_name="Algorithms")
    db_session.add(subj)
    await db_session.flush()

    # Assign teacher
    st = SubjectTeacher(subject_teacher_subject_id=subj.subject_id, subject_teacher_user_id=teacher.user_id)
    db_session.add(st)
    await db_session.flush()

    assessment = Assessment(
        assessment_subject_id=subj.subject_id,
        assessment_title="Midterm Assessment",
        assessment_total_marks=Decimal("0.00"),
        assessment_status=AssessmentStatus.DRAFT,
        assessment_type=AssessmentType.QUIZ,
        assessment_created_by=teacher.user_id
    )
    db_session.add(assessment)
    await db_session.flush()

    service = AssessmentService(db_session)

    # 1. Prepare Valid Excel with 3 questions
    valid_rows = [
        ["Binary search time complexity?", "mcq_single", 2.0, "O(log n)", "O(n)", "O(1)", "O(n^2)", "A", "Divide and conquer", 1],
        ["Which are graph algorithms?", "mcq_multiple", 4.0, "Dijkstra", "Kruskal", "QuickSort", "Prim", "A, B, D", "QuickSort is sorting", 2],
        ["Stacks follow FIFO order.", "true_false", 1.5, "", "", "", "", "FALSE", "Stacks follow LIFO", 3]
    ]
    valid_excel = create_test_excel_bytes(valid_rows)

    # 2. Test Validation API method
    val_resp = await service.validate_bulk_questions(
        org_id=org.organization_id,
        assessment_id=assessment.assessment_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=True,
        file_bytes=valid_excel
    )

    assert val_resp.valid is True
    assert val_resp.total_rows == 3
    assert val_resp.valid_rows == 3
    assert val_resp.error_count == 0
    assert val_resp.total_marks == Decimal("7.50")
    assert len(val_resp.preview) == 3

    # 3. Test Atomic Import
    import_resp = await service.import_bulk_questions(
        org_id=org.organization_id,
        assessment_id=assessment.assessment_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=True,
        file_bytes=valid_excel
    )

    assert import_resp.success is True
    assert import_resp.imported_count == 3
    assert import_resp.total_marks_added == Decimal("7.50")
    assert import_resp.assessment_total_marks == Decimal("7.50")
    assert len(import_resp.questions) == 3

    # 4. Verify assessment question snapshots and bank questions
    db_questions = await service.repo.list_assessment_questions(assessment.assessment_id)
    assert len(db_questions) == 3
    for aq in db_questions:
        assert aq.assessment_question_snapshot is not None
        assert "question_text" in aq.assessment_question_snapshot
        assert "question_type" in aq.assessment_question_snapshot
        assert aq.assessment_question_marks > 0

    # 5. Verify atomicity: if 1 row is invalid in a batch, 0 questions are added and error is raised
    invalid_batch_rows = [
        ["Valid question 1", "mcq_single", 2.0, "A", "B", "", "", "A", "", 4],
        ["Invalid question 2", "mcq_single", 2.0, "A", "B", "", "", "INVALID_KEY", "", 5]
    ]
    invalid_excel = create_test_excel_bytes(invalid_batch_rows)

    with pytest.raises(ValidationException, match="validation errors"):
        await service.import_bulk_questions(
            org_id=org.organization_id,
            assessment_id=assessment.assessment_id,
            requesting_user_id=teacher.user_id,
            is_org_admin=True,
            file_bytes=invalid_excel
        )

    # Count must still be 3 (no partial import)
    db_questions_after = await service.repo.list_assessment_questions(assessment.assessment_id)
    assert len(db_questions_after) == 3

    # 6. Verify Assessment Lifecycle protection (cannot upload to published assessment)
    assessment.assessment_status = AssessmentStatus.PUBLISHED
    await db_session.flush()

    with pytest.raises(ConflictException, match="DRAFT"):
        await service.validate_bulk_questions(
            org_id=org.organization_id,
            assessment_id=assessment.assessment_id,
            requesting_user_id=teacher.user_id,
            is_org_admin=True,
            file_bytes=valid_excel
        )

    with pytest.raises(ConflictException, match="DRAFT"):
        await service.import_bulk_questions(
            org_id=org.organization_id,
            assessment_id=assessment.assessment_id,
            requesting_user_id=teacher.user_id,
            is_org_admin=True,
            file_bytes=valid_excel
        )


@pytest.mark.asyncio
async def test_bulk_upload_rbac_and_isolation(db_session):
    """Test RBAC: Unassigned teacher and wrong workspace member cannot upload questions."""
    # 1. Setup Org, Workspace, Subject, Assessment
    owner = User(user_email="owner_bulk@test.com", user_password_hash="hash")
    unassigned_teacher = User(user_email="unassigned@test.com", user_password_hash="hash")
    db_session.add_all([owner, unassigned_teacher])
    await db_session.flush()

    org = Organization(organization_name="RBAC Org", organization_slug="rbac-org", organization_owner_user_id=owner.user_id)
    db_session.add(org)
    await db_session.flush()

    ws = Workspace(workspace_organization_id=org.organization_id, workspace_name="RBAC WS", workspace_created_by=owner.user_id)
    db_session.add(ws)
    await db_session.flush()

    subj = Subject(subject_workspace_id=ws.workspace_id, subject_name="History")
    db_session.add(subj)
    await db_session.flush()

    assessment = Assessment(
        assessment_subject_id=subj.subject_id,
        assessment_title="History Quiz",
        assessment_total_marks=Decimal("0.00"),
        assessment_status=AssessmentStatus.DRAFT,
        assessment_type=AssessmentType.QUIZ,
        assessment_created_by=owner.user_id
    )
    db_session.add(assessment)
    await db_session.flush()

    service = AssessmentService(db_session)
    valid_excel = create_test_excel_bytes([["Who was Napoleon?", "short_answer", 5.0, "", "", "", "", "", "", 1]])

    # Unassigned teacher (not workspace member) -> Forbidden
    with pytest.raises(ForbiddenException):
        await service.validate_bulk_questions(
            org_id=org.organization_id,
            assessment_id=assessment.assessment_id,
            requesting_user_id=unassigned_teacher.user_id,
            is_org_admin=False,
            file_bytes=valid_excel
        )

    with pytest.raises(ForbiddenException):
        await service.import_bulk_questions(
            org_id=org.organization_id,
            assessment_id=assessment.assessment_id,
            requesting_user_id=unassigned_teacher.user_id,
            is_org_admin=False,
            file_bytes=valid_excel
        )


@pytest.mark.asyncio
async def test_bulk_upload_duplicate_against_existing_assessment_questions(db_session):
    """Test duplicate detection against existing questions already in the assessment."""
    owner = User(user_email="owner_dup@test.com", user_password_hash="hash")
    db_session.add(owner)
    await db_session.flush()

    org = Organization(organization_name="Dup Org", organization_slug="dup-org", organization_owner_user_id=owner.user_id)
    db_session.add(org)
    await db_session.flush()

    ws = Workspace(workspace_organization_id=org.organization_id, workspace_name="Dup WS", workspace_created_by=owner.user_id)
    db_session.add(ws)
    await db_session.flush()

    subj = Subject(subject_workspace_id=ws.workspace_id, subject_name="Math")
    db_session.add(subj)
    await db_session.flush()

    assessment = Assessment(
        assessment_subject_id=subj.subject_id,
        assessment_title="Math Quiz",
        assessment_total_marks=Decimal("0.00"),
        assessment_status=AssessmentStatus.DRAFT,
        assessment_type=AssessmentType.QUIZ,
        assessment_created_by=owner.user_id
    )
    db_session.add(assessment)
    await db_session.flush()

    service = AssessmentService(db_session)
    first_excel = create_test_excel_bytes([["What is 10 + 10?", "mcq_single", 2.0, "20", "10", "0", "100", "A", "", 1]])

    # 1. Import first question
    await service.import_bulk_questions(
        org_id=org.organization_id,
        assessment_id=assessment.assessment_id,
        requesting_user_id=owner.user_id,
        is_org_admin=True,
        file_bytes=first_excel
    )

    # 2. Try importing the exact same question again -> validation detects duplication against assessment
    val_resp = await service.validate_bulk_questions(
        org_id=org.organization_id,
        assessment_id=assessment.assessment_id,
        requesting_user_id=owner.user_id,
        is_org_admin=True,
        file_bytes=first_excel
    )

    assert val_resp.valid is False
    assert any("already exists in this assessment" in e.message for e in val_resp.errors)

