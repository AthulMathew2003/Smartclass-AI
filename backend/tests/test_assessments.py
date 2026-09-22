import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta
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
    QuestionType,
    QuestionStatus
)
from app.modules.assessments.service import AssessmentService
from app.modules.assessments.schemas import (
    AssessmentCreateRequest,
    AssessmentUpdateRequest,
    QuestionBankItemCreate,
    QuestionBankItemUpdate,
    AssessmentAddQuestionRequest,
    AssessmentQuestionUpdateRequest,
    QuestionReorderRequest,
    QuestionOptionCreate
)
from app.core.exceptions import (
    ConflictException,
    NotFoundException,
    ForbiddenException,
    ValidationException
)


@pytest.mark.asyncio
async def test_assessment_builder_and_question_bank_flow(db_session):
    """Test Question Bank CRUD, snapshot freezing, immutability, builder reordering, server-side mark calculation, and lifecycle."""
    now = datetime.now(timezone.utc)

    # 1. Setup Teacher, Org, Workspace, Subject
    teacher = User(user_email="teacher_builder@test.com", user_password_hash="hash", user_first_name="Prof", user_last_name="Turing")
    db_session.add(teacher)
    await db_session.flush()

    roles_res = await db_session.execute(select(Role).where(Role.role_is_system == True))
    roles_by_name = {r.role_name: r.role_id for r in roles_res.scalars().all()}

    org = Organization(organization_name="Builder Academy", organization_slug="builder-acad", organization_owner_user_id=teacher.user_id)
    db_session.add(org)
    await db_session.flush()

    ws = Workspace(workspace_organization_id=org.organization_id, workspace_name="CS Dept", workspace_created_by=teacher.user_id)
    db_session.add(ws)
    await db_session.flush()

    subj = Subject(subject_workspace_id=ws.workspace_id, subject_name="Algorithms 101")
    db_session.add(subj)
    await db_session.flush()

    st = SubjectTeacher(subject_teacher_subject_id=subj.subject_id, subject_teacher_user_id=teacher.user_id)
    db_session.add(st)
    wm = WorkspaceMember(workspace_member_workspace_id=ws.workspace_id, workspace_member_user_id=teacher.user_id, workspace_member_role_id=roles_by_name["Teacher"])
    db_session.add(wm)
    await db_session.flush()

    service = AssessmentService(db_session)

    # 2. Add Questions to Subject Question Bank
    q1_payload = QuestionBankItemCreate(
        question_type=QuestionType.MCQ_SINGLE,
        question_text="What is the time complexity of binary search?",
        default_marks=Decimal("5.00"),
        question_explanation="Binary search halves the search space each step.",
        options=[
            QuestionOptionCreate(option_text="O(n)", option_order=1, option_is_correct=False),
            QuestionOptionCreate(option_text="O(log n)", option_order=2, option_is_correct=True),
            QuestionOptionCreate(option_text="O(n^2)", option_order=3, option_is_correct=False),
        ]
    )
    q1 = await service.create_question_bank_item(
        org_id=org.organization_id,
        subject_id=subj.subject_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False,
        payload=q1_payload
    )
    assert q1.question_text == "What is the time complexity of binary search?"
    assert len(q1.options) == 3

    q2_payload = QuestionBankItemCreate(
        question_type=QuestionType.TRUE_FALSE,
        question_text="Merge sort is a divide and conquer algorithm.",
        default_marks=Decimal("3.00"),
        options=[
            QuestionOptionCreate(option_text="True", option_order=1, option_is_correct=True),
            QuestionOptionCreate(option_text="False", option_order=2, option_is_correct=False),
        ]
    )
    q2 = await service.create_question_bank_item(
        org_id=org.organization_id,
        subject_id=subj.subject_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False,
        payload=q2_payload
    )
    assert q2.question_default_marks == Decimal("3.00")

    # 3. Create Draft Assessment
    create_assessment_payload = AssessmentCreateRequest(
        subject_id=subj.subject_id,
        title="Algorithms Midterm",
        description="Midterm examination covering search and sort",
        type=AssessmentType.EXAM,
        duration_minutes=90,
        start_at=now + timedelta(hours=2),
        end_at=now + timedelta(hours=4),
        passing_marks=Decimal("5.00"),
        attempt_limit=2,
        randomize_questions=True
    )
    assessment = await service.create_assessment(
        org_id=org.organization_id,
        created_by_user_id=teacher.user_id,
        is_org_admin=False,
        payload=create_assessment_payload
    )
    assert assessment.assessment_status == AssessmentStatus.DRAFT
    assert assessment.assessment_attempt_limit == 2
    assert assessment.assessment_randomize_questions is True
    assert assessment.assessment_total_marks == Decimal("0.00")

    # 4. Add Questions from Question Bank to Assessment
    aq1 = await service.add_question_from_bank(
        org_id=org.organization_id,
        assessment_id=assessment.assessment_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False,
        payload=AssessmentAddQuestionRequest(question_id=q1.question_id, marks=Decimal("5.00"))
    )
    assert aq1.assessment_question_order == 1
    assert aq1.assessment_question_marks == Decimal("5.00")
    assert aq1.question_text == q1.question_text
    assert len(aq1.options) == 3

    aq2 = await service.add_question_from_bank(
        org_id=org.organization_id,
        assessment_id=assessment.assessment_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False,
        payload=AssessmentAddQuestionRequest(question_id=q2.question_id, marks=Decimal("5.00"))
    )
    assert aq2.assessment_question_order == 2
    assert aq2.assessment_question_marks == Decimal("5.00")

    # Assessment total marks automatically calculated = 5.00 + 5.00 = 10.00
    fetched_assessment = await service.get_assessment(
        org_id=org.organization_id,
        assessment_id=assessment.assessment_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False
    )
    assert fetched_assessment.assessment_total_marks == Decimal("10.00")
    assert fetched_assessment.total_questions == 2

    # 5. Prevent Duplicate Question in Assessment
    with pytest.raises(ConflictException):
        await service.add_question_from_bank(
            org_id=org.organization_id,
            assessment_id=assessment.assessment_id,
            requesting_user_id=teacher.user_id,
            is_org_admin=False,
            payload=AssessmentAddQuestionRequest(question_id=q1.question_id)
        )

    # 6. Snapshot Immutability Test:
    # Update the question in the Question Bank -> Assessment Question Snapshot MUST NOT change!
    await service.update_question_bank_item(
        org_id=org.organization_id,
        subject_id=subj.subject_id,
        question_id=q1.question_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False,
        payload=QuestionBankItemUpdate(question_text="MUTATED TEXT: What is complexity?")
    )
    # Check that Question Bank is updated
    updated_bank_q1 = await service.get_question_bank_item(
        org_id=org.organization_id,
        subject_id=subj.subject_id,
        question_id=q1.question_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False
    )
    assert updated_bank_q1.question_text == "MUTATED TEXT: What is complexity?"

    # Check that Assessment Question snapshot is unchanged!
    aq_list = await service.list_assessment_questions(
        org_id=org.organization_id,
        assessment_id=assessment.assessment_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False
    )
    assert aq_list[0]["question_text"] == "What is the time complexity of binary search?"

    # 7. Reorder Questions (Swap order)
    reorder_res = await service.reorder_assessment_questions(
        org_id=org.organization_id,
        assessment_id=assessment.assessment_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False,
        payload=QuestionReorderRequest(question_ids=[aq2.assessment_question_id, aq1.assessment_question_id])
    )
    assert reorder_res[0]["assessment_question_id"] == aq2.assessment_question_id
    assert reorder_res[0]["assessment_question_order"] == 1
    assert reorder_res[1]["assessment_question_id"] == aq1.assessment_question_id
    assert reorder_res[1]["assessment_question_order"] == 2

    # 8. Publish Assessment
    published = await service.publish_assessment(
        org_id=org.organization_id,
        assessment_id=assessment.assessment_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False
    )
    assert published.assessment_status == AssessmentStatus.PUBLISHED
    assert published.assessment_total_marks == Decimal("10.00")

    # 9. Published Assessment cannot have questions added/removed/reordered
    with pytest.raises(ConflictException):
        await service.add_question_from_bank(
            org_id=org.organization_id,
            assessment_id=assessment.assessment_id,
            requesting_user_id=teacher.user_id,
            is_org_admin=False,
            payload=AssessmentAddQuestionRequest(question_id=q1.question_id)
        )

    with pytest.raises(ConflictException):
        await service.remove_assessment_question(
            org_id=org.organization_id,
            assessment_id=assessment.assessment_id,
            assessment_question_id=aq1.assessment_question_id,
            requesting_user_id=teacher.user_id,
            is_org_admin=False
        )

    # 10. Close and Archive Assessment
    closed = await service.close_assessment(
        org_id=org.organization_id,
        assessment_id=assessment.assessment_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False
    )
    assert closed.assessment_status == AssessmentStatus.CLOSED

    archived = await service.archive_assessment(
        org_id=org.organization_id,
        assessment_id=assessment.assessment_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False
    )
    assert archived.assessment_status == AssessmentStatus.ARCHIVED


@pytest.mark.asyncio
async def test_assessment_and_question_validation_rules(db_session):
    """Test validation rules for assessment and question models."""
    now = datetime.now(timezone.utc)

    # 1. Invalid schedule (end_at before start_at)
    with pytest.raises(ValidationException):
        AssessmentCreateRequest(
            subject_id=uuid.uuid4(),
            title="Invalid Schedule Quiz",
            start_at=now + timedelta(hours=3),
            end_at=now + timedelta(hours=1),
            total_marks=Decimal("50.00")
        )

    # 2. Invalid duration
    with pytest.raises((ValidationException, Exception)):
        AssessmentCreateRequest(
            subject_id=uuid.uuid4(),
            title="Invalid Duration Quiz",
            duration_minutes=0,
            total_marks=Decimal("50.00")
        )

    # 3. Passing marks > total marks
    with pytest.raises(ValidationException):
        AssessmentCreateRequest(
            subject_id=uuid.uuid4(),
            title="Invalid Passing Marks",
            total_marks=Decimal("50.00"),
            passing_marks=Decimal("60.00")
        )

    # 4. MCQ Single Choice with no correct option
    with pytest.raises(ValidationException):
        QuestionBankItemCreate(
            question_type=QuestionType.MCQ_SINGLE,
            question_text="Which one is correct?",
            default_marks=Decimal("2.00"),
            options=[
                QuestionOptionCreate(option_text="A", option_order=1, option_is_correct=False),
                QuestionOptionCreate(option_text="B", option_order=2, option_is_correct=False),
            ]
        )

    # 5. MCQ Single Choice with multiple correct options
    with pytest.raises(ValidationException):
        QuestionBankItemCreate(
            question_type=QuestionType.MCQ_SINGLE,
            question_text="Which one is correct?",
            default_marks=Decimal("2.00"),
            options=[
                QuestionOptionCreate(option_text="A", option_order=1, option_is_correct=True),
                QuestionOptionCreate(option_text="B", option_order=2, option_is_correct=True),
            ]
        )

    # 6. True/False with invalid option texts
    with pytest.raises(ValidationException):
        QuestionBankItemCreate(
            question_type=QuestionType.TRUE_FALSE,
            question_text="Is earth round?",
            default_marks=Decimal("1.00"),
            options=[
                QuestionOptionCreate(option_text="Yes", option_order=1, option_is_correct=True),
                QuestionOptionCreate(option_text="No", option_order=2, option_is_correct=False),
            ]
        )


@pytest.mark.asyncio
async def test_cross_subject_question_injection_rejection(db_session):
    """Test that questions belonging to Subject A cannot be added to an Assessment in Subject B."""
    # Setup User & Org
    teacher = User(user_email="cross_teacher@test.com", user_password_hash="hash")
    db_session.add(teacher)
    await db_session.flush()

    roles_res = await db_session.execute(select(Role).where(Role.role_is_system == True))
    roles_by_name = {r.role_name: r.role_id for r in roles_res.scalars().all()}

    org = Organization(organization_name="Cross Org", organization_slug="cross-org", organization_owner_user_id=teacher.user_id)
    db_session.add(org)
    await db_session.flush()

    ws = Workspace(workspace_organization_id=org.organization_id, workspace_name="Main WS", workspace_created_by=teacher.user_id)
    db_session.add(ws)
    await db_session.flush()

    # Subject A and Subject B
    subj_a = Subject(subject_workspace_id=ws.workspace_id, subject_name="Physics")
    subj_b = Subject(subject_workspace_id=ws.workspace_id, subject_name="Chemistry")
    db_session.add_all([subj_a, subj_b])
    await db_session.flush()

    # Assign Teacher to both subjects
    db_session.add(SubjectTeacher(subject_teacher_subject_id=subj_a.subject_id, subject_teacher_user_id=teacher.user_id))
    db_session.add(SubjectTeacher(subject_teacher_subject_id=subj_b.subject_id, subject_teacher_user_id=teacher.user_id))
    db_session.add(WorkspaceMember(workspace_member_workspace_id=ws.workspace_id, workspace_member_user_id=teacher.user_id, workspace_member_role_id=roles_by_name["Teacher"]))
    await db_session.flush()

    service = AssessmentService(db_session)

    # 1. Create Question in Subject A Question Bank
    qa = await service.create_question_bank_item(
        org_id=org.organization_id,
        subject_id=subj_a.subject_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False,
        payload=QuestionBankItemCreate(
            question_type=QuestionType.SHORT_ANSWER,
            question_text="State Newton's second law of motion.",
            default_marks=Decimal("5.00")
        )
    )

    # 2. Create Assessment in Subject B
    assessment_b = await service.create_assessment(
        org_id=org.organization_id,
        created_by_user_id=teacher.user_id,
        is_org_admin=False,
        payload=AssessmentCreateRequest(
            subject_id=subj_b.subject_id,
            title="Chemistry Exam",
            type=AssessmentType.EXAM
        )
    )

    # 3. Attempt to inject Subject A's question into Subject B's Assessment -> 403 Forbidden
    with pytest.raises(ForbiddenException) as exc_info:
        await service.add_question_from_bank(
            org_id=org.organization_id,
            assessment_id=assessment_b.assessment_id,
            requesting_user_id=teacher.user_id,
            is_org_admin=False,
            payload=AssessmentAddQuestionRequest(question_id=qa.question_id)
        )
    assert "different subject" in str(exc_info.value).lower()
