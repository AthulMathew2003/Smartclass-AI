import uuid
from decimal import Decimal
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.users.models import User
from app.modules.organizations.models import Organization, Workspace, WorkspaceMember, OrganizationMember, Role
from app.modules.subjects.models import Subject, SubjectTeacher, SubjectStatus
from app.modules.assessments.models import (
    Assessment,
    AssessmentType,
    AssessmentStatus,
    QuestionBankItem,
    AssessmentQuestion,
    QuestionOption,
    QuestionType,
    QuestionStatus
)
from app.modules.assessments.schemas import (
    AssessmentCreateRequest,
    QuestionBankItemCreate,
    QuestionBankItemUpdate,
    QuestionOptionCreate,
    AssessmentAddQuestionRequest,
    AssessmentQuestionUpdateRequest,
    QuestionReorderRequest,
    validate_question_options_rules
)
from app.modules.assessments.service import AssessmentService
from app.core.exceptions import ConflictException, NotFoundException, ForbiddenException, ValidationException


@pytest.mark.asyncio
async def test_question_models_and_options_crud(db_session: AsyncSession):
    """Test model creation, cascading deletes, and SET NULL on creator delete."""
    owner = User(user_email="q_owner_mod@example.com", user_password_hash="pw", user_first_name="O", user_last_name="1")
    creator = User(user_email="q_teacher_mod@example.com", user_password_hash="pw", user_first_name="C", user_last_name="1")
    db_session.add_all([owner, creator])
    await db_session.flush()

    org = Organization(organization_name="Q Org", organization_slug="q-org", organization_owner_user_id=owner.user_id)
    db_session.add(org)
    await db_session.flush()

    ws = Workspace(workspace_name="Q WS", workspace_organization_id=org.organization_id, workspace_created_by=owner.user_id)
    db_session.add(ws)
    await db_session.flush()

    subj = Subject(subject_name="Physics", subject_workspace_id=ws.workspace_id)
    db_session.add(subj)
    await db_session.flush()

    # Create Question in Subject Question Bank with Options
    q = QuestionBankItem(
        question_subject_id=subj.subject_id,
        question_type=QuestionType.MCQ_SINGLE,
        question_text="What is the unit of force?",
        question_default_marks=Decimal("5.00"),
        question_explanation="Newton is the SI unit of force.",
        question_created_by=creator.user_id
    )
    db_session.add(q)
    await db_session.flush()

    opt1 = QuestionOption(option_question_id=q.question_id, option_text="Joule", option_order=1, option_is_correct=False)
    opt2 = QuestionOption(option_question_id=q.question_id, option_text="Newton", option_order=2, option_is_correct=True)
    db_session.add_all([opt1, opt2])
    await db_session.commit()

    # Query Question with Options
    stmt = select(QuestionBankItem).options(selectinload(QuestionBankItem.options)).where(QuestionBankItem.question_id == q.question_id)
    fetched_q = (await db_session.execute(stmt)).scalar_one()
    assert fetched_q.question_text == "What is the unit of force?"
    assert len(fetched_q.options) == 2
    assert fetched_q.options[1].option_is_correct is True

    # Test creator deletion sets question_created_by to NULL
    await db_session.delete(creator)
    await db_session.commit()

    await db_session.refresh(fetched_q)
    assert fetched_q.question_created_by is None

    # Test cascade delete: deleting subject deletes question bank questions and options
    await db_session.delete(subj)
    await db_session.commit()

    q_check = (await db_session.execute(select(QuestionBankItem).where(QuestionBankItem.question_id == q.question_id))).scalar_one_or_none()
    assert q_check is None
    opt_check = (await db_session.execute(select(QuestionOption).where(QuestionOption.option_id == opt1.option_id))).scalar_one_or_none()
    assert opt_check is None


@pytest.mark.asyncio
async def test_question_lifecycle_and_reordering(db_session: AsyncSession):
    """Test Question Bank CRUD and assessment builder inline operations."""
    owner = User(user_email="q_teacher_reorder@example.com", user_password_hash="pw", user_first_name="T", user_last_name="R")
    db_session.add(owner)
    await db_session.flush()

    roles_res = await db_session.execute(select(Role).where(Role.role_is_system == True))
    roles_by_name = {r.role_name: r.role_id for r in roles_res.scalars().all()}

    org = Organization(organization_name="Q Reorder Org", organization_slug="q-reorder-org", organization_owner_user_id=owner.user_id)
    db_session.add(org)
    await db_session.flush()

    ws = Workspace(workspace_name="Q Reorder WS", workspace_organization_id=org.organization_id, workspace_created_by=owner.user_id)
    db_session.add(ws)
    await db_session.flush()

    subj = Subject(subject_name="Math Reorder", subject_workspace_id=ws.workspace_id)
    db_session.add(subj)
    await db_session.flush()

    db_session.add(SubjectTeacher(subject_teacher_subject_id=subj.subject_id, subject_teacher_user_id=owner.user_id))
    db_session.add(WorkspaceMember(workspace_member_workspace_id=ws.workspace_id, workspace_member_user_id=owner.user_id, workspace_member_role_id=roles_by_name["Teacher"]))
    await db_session.flush()

    service = AssessmentService(db_session)

    # 1. Create Assessment
    assessment = await service.create_assessment(
        org_id=org.organization_id,
        created_by_user_id=owner.user_id,
        is_org_admin=False,
        payload=AssessmentCreateRequest(
            subject_id=subj.subject_id,
            title="Reorder Test Quiz",
            type=AssessmentType.QUIZ
        )
    )

    # 2. Add Questions directly to Assessment via service
    q1 = await service.create_and_add_question(
        org_id=org.organization_id,
        assessment_id=assessment.assessment_id,
        requesting_user_id=owner.user_id,
        is_org_admin=False,
        payload=QuestionBankItemCreate(
            question_type=QuestionType.MCQ_SINGLE,
            question_text="Q1: What is 1+1?",
            default_marks=Decimal("2.00"),
            options=[
                QuestionOptionCreate(option_text="2", option_order=1, option_is_correct=True),
                QuestionOptionCreate(option_text="3", option_order=2, option_is_correct=False),
            ]
        )
    )
    assert q1.assessment_question_order == 1

    q2 = await service.create_and_add_question(
        org_id=org.organization_id,
        assessment_id=assessment.assessment_id,
        requesting_user_id=owner.user_id,
        is_org_admin=False,
        payload=QuestionBankItemCreate(
            question_type=QuestionType.TRUE_FALSE,
            question_text="Q2: Is pi > 3?",
            default_marks=Decimal("3.00"),
            options=[
                QuestionOptionCreate(option_text="True", option_order=1, option_is_correct=True),
                QuestionOptionCreate(option_text="False", option_order=2, option_is_correct=False),
            ]
        )
    )
    assert q2.assessment_question_order == 2

    # Reorder questions
    reordered = await service.reorder_assessment_questions(
        org_id=org.organization_id,
        assessment_id=assessment.assessment_id,
        requesting_user_id=owner.user_id,
        is_org_admin=False,
        payload=QuestionReorderRequest(question_ids=[q2.assessment_question_id, q1.assessment_question_id])
    )
    assert reordered[0]["assessment_question_id"] == q2.assessment_question_id
    assert reordered[0]["assessment_question_order"] == 1
    assert reordered[1]["assessment_question_id"] == q1.assessment_question_id
    assert reordered[1]["assessment_question_order"] == 2


@pytest.mark.asyncio
async def test_question_validation_rules_and_types():
    """Test schema validation rules for all question types (MCQ Single, Multiple, True/False, Short Answer)."""
    # 1. MCQ Single: valid
    validate_question_options_rules(QuestionType.MCQ_SINGLE, [
        QuestionOptionCreate(option_text="A", option_order=1, is_correct=True),
        QuestionOptionCreate(option_text="B", option_order=2, is_correct=False),
    ])

    # 1a. MCQ Single: 0 correct -> Error
    with pytest.raises(ValidationException, match="exactly 1 correct option"):
        validate_question_options_rules(QuestionType.MCQ_SINGLE, [
            QuestionOptionCreate(option_text="A", option_order=1, is_correct=False),
            QuestionOptionCreate(option_text="B", option_order=2, is_correct=False),
        ])

    # 1b. MCQ Single: 2 correct -> Error
    with pytest.raises(ValidationException, match="exactly 1 correct option"):
        validate_question_options_rules(QuestionType.MCQ_SINGLE, [
            QuestionOptionCreate(option_text="A", option_order=1, is_correct=True),
            QuestionOptionCreate(option_text="B", option_order=2, is_correct=True),
        ])

    # 1c. MCQ Single: < 2 options -> Error
    with pytest.raises(ValidationException, match="at least 2 options"):
        validate_question_options_rules(QuestionType.MCQ_SINGLE, [
            QuestionOptionCreate(option_text="A", option_order=1, is_correct=True),
        ])

    # 2. MCQ Multiple: valid with multiple correct
    validate_question_options_rules(QuestionType.MCQ_MULTIPLE, [
        QuestionOptionCreate(option_text="A", option_order=1, is_correct=True),
        QuestionOptionCreate(option_text="B", option_order=2, is_correct=True),
        QuestionOptionCreate(option_text="C", option_order=3, is_correct=False),
    ])

    # 2a. MCQ Multiple: 0 correct -> Error
    with pytest.raises(ValidationException, match="at least 1 correct option"):
        validate_question_options_rules(QuestionType.MCQ_MULTIPLE, [
            QuestionOptionCreate(option_text="A", option_order=1, is_correct=False),
            QuestionOptionCreate(option_text="B", option_order=2, is_correct=False),
        ])

    # 3. True / False: valid
    validate_question_options_rules(QuestionType.TRUE_FALSE, [
        QuestionOptionCreate(option_text="True", option_order=1, is_correct=True),
        QuestionOptionCreate(option_text="False", option_order=2, is_correct=False),
    ])

    # 3a. True / False: wrong count -> Error
    with pytest.raises(ValidationException, match="exactly 2 options"):
        validate_question_options_rules(QuestionType.TRUE_FALSE, [
            QuestionOptionCreate(option_text="True", option_order=1, is_correct=True),
        ])

    # 3b. True / False: 0 correct -> Error
    with pytest.raises(ValidationException, match="exactly 1 correct option"):
        validate_question_options_rules(QuestionType.TRUE_FALSE, [
            QuestionOptionCreate(option_text="True", option_order=1, is_correct=False),
            QuestionOptionCreate(option_text="False", option_order=2, is_correct=False),
        ])

    # 3c. True / False: 2 correct -> Error
    with pytest.raises(ValidationException, match="exactly 1 correct option"):
        validate_question_options_rules(QuestionType.TRUE_FALSE, [
            QuestionOptionCreate(option_text="True", option_order=1, is_correct=True),
            QuestionOptionCreate(option_text="False", option_order=2, is_correct=True),
        ])

    # 3d. True / False: invalid text names -> Error
    with pytest.raises(ValidationException, match="must be 'True' and 'False'"):
        validate_question_options_rules(QuestionType.TRUE_FALSE, [
            QuestionOptionCreate(option_text="Yes", option_order=1, is_correct=True),
            QuestionOptionCreate(option_text="No", option_order=2, is_correct=False),
        ])

    # 4. Short Answer: valid (no options)
    validate_question_options_rules(QuestionType.SHORT_ANSWER, [])

    # 4a. Short Answer: with options -> Error
    with pytest.raises(ValidationException, match="must not contain options"):
        validate_question_options_rules(QuestionType.SHORT_ANSWER, [
            QuestionOptionCreate(option_text="Some text", option_order=1, is_correct=True)
        ])

    # 5. Duplicate option orders -> Error
    with pytest.raises(ValidationException, match="Option order numbers must be unique"):
        validate_question_options_rules(QuestionType.MCQ_SINGLE, [
            QuestionOptionCreate(option_text="A", option_order=1, is_correct=True),
            QuestionOptionCreate(option_text="B", option_order=1, is_correct=False),
        ])

    # 6. Empty question text / whitespace -> Error
    with pytest.raises(Exception):
        QuestionBankItemCreate(
            question_type=QuestionType.SHORT_ANSWER,
            question_text="   ",
            default_marks=Decimal("5.00"),
            options=[]
        )

    # 7. Invalid marks <= 0 -> Error
    with pytest.raises(Exception):
        QuestionBankItemCreate(
            question_type=QuestionType.SHORT_ANSWER,
            question_text="Valid question?",
            default_marks=Decimal("0.00"),
            options=[]
        )


@pytest.mark.asyncio
async def test_question_security_and_tenant_isolation(db_session: AsyncSession):
    """Test tenant isolation, foreign subject rejection, unassigned teacher access, and lifecycle immutability."""
    owner = User(user_email="q_iso_owner@example.com", user_password_hash="pw", user_first_name="O", user_last_name="I")
    teacher1 = User(user_email="q_iso_t1@example.com", user_password_hash="pw", user_first_name="T", user_last_name="1")
    teacher2 = User(user_email="q_iso_t2@example.com", user_password_hash="pw", user_first_name="T", user_last_name="2")
    db_session.add_all([owner, teacher1, teacher2])
    await db_session.flush()

    roles_res = await db_session.execute(select(Role).where(Role.role_is_system == True))
    roles_by_name = {r.role_name: r.role_id for r in roles_res.scalars().all()}

    org = Organization(organization_name="Iso Org", organization_slug="iso-org", organization_owner_user_id=owner.user_id)
    db_session.add(org)
    await db_session.flush()

    ws = Workspace(workspace_name="Iso WS", workspace_organization_id=org.organization_id, workspace_created_by=owner.user_id)
    db_session.add(ws)
    await db_session.flush()

    subj_a = Subject(subject_name="Subject A", subject_workspace_id=ws.workspace_id)
    subj_b = Subject(subject_name="Subject B", subject_workspace_id=ws.workspace_id)
    db_session.add_all([subj_a, subj_b])
    await db_session.flush()

    # Teacher 1 assigned to Subject A, Teacher 2 assigned to Subject B
    db_session.add(WorkspaceMember(workspace_member_workspace_id=ws.workspace_id, workspace_member_user_id=teacher1.user_id, workspace_member_role_id=roles_by_name["Teacher"]))
    db_session.add(WorkspaceMember(workspace_member_workspace_id=ws.workspace_id, workspace_member_user_id=teacher2.user_id, workspace_member_role_id=roles_by_name["Teacher"]))
    db_session.add(SubjectTeacher(subject_teacher_subject_id=subj_a.subject_id, subject_teacher_user_id=teacher1.user_id))
    db_session.add(SubjectTeacher(subject_teacher_subject_id=subj_b.subject_id, subject_teacher_user_id=teacher2.user_id))
    await db_session.flush()

    service = AssessmentService(db_session)

    # Assessment in Subject A
    asm_a = await service.create_assessment(
        org_id=org.organization_id,
        created_by_user_id=teacher1.user_id,
        is_org_admin=False,
        payload=AssessmentCreateRequest(subject_id=subj_a.subject_id, title="Asm A", type=AssessmentType.QUIZ)
    )

    # Question in Subject B Question Bank
    q_b = await service.create_question_bank_item(
        org_id=org.organization_id,
        subject_id=subj_b.subject_id,
        requesting_user_id=teacher2.user_id,
        is_org_admin=False,
        payload=QuestionBankItemCreate(
            question_type=QuestionType.SHORT_ANSWER,
            question_text="Subject B Question",
            default_marks=Decimal("5.00"),
            options=[]
        )
    )

    # 1. Unassigned teacher cannot add question to Subject A Assessment
    with pytest.raises(ForbiddenException, match="not assigned to this subject"):
        await service.create_and_add_question(
            org_id=org.organization_id,
            assessment_id=asm_a.assessment_id,
            requesting_user_id=teacher2.user_id,
            is_org_admin=False,
            payload=QuestionBankItemCreate(
                question_type=QuestionType.SHORT_ANSWER,
                question_text="Unauthorized",
                default_marks=Decimal("1.00"),
                options=[]
            )
        )

    # 2. Cannot inject question from Subject B into Subject A assessment
    with pytest.raises(ForbiddenException, match="Cannot add questions from a different subject"):
        await service.add_question_from_bank(
            org_id=org.organization_id,
            assessment_id=asm_a.assessment_id,
            requesting_user_id=teacher1.user_id,
            is_org_admin=False,
            payload=AssessmentAddQuestionRequest(question_id=q_b.question_id)
        )

    # 3. Add valid question to Asm A
    qa1 = await service.create_and_add_question(
        org_id=org.organization_id,
        assessment_id=asm_a.assessment_id,
        requesting_user_id=teacher1.user_id,
        is_org_admin=False,
        payload=QuestionBankItemCreate(
            question_type=QuestionType.SHORT_ANSWER,
            question_text="Subject A Question",
            default_marks=Decimal("5.00"),
            options=[]
        )
    )

    # 4. Duplicate question in same assessment rejected
    with pytest.raises(ConflictException, match="already added"):
        await service.add_question_from_bank(
            org_id=org.organization_id,
            assessment_id=asm_a.assessment_id,
            requesting_user_id=teacher1.user_id,
            is_org_admin=False,
            payload=AssessmentAddQuestionRequest(question_id=qa1.assessment_question_question_id)
        )

    # 5. Publish Assessment A
    await service.publish_assessment(
        org_id=org.organization_id,
        assessment_id=asm_a.assessment_id,
        requesting_user_id=teacher1.user_id,
        is_org_admin=False
    )

    # 6. Structural modification rejected when published
    with pytest.raises(ConflictException, match="DRAFT assessments"):
        await service.create_and_add_question(
            org_id=org.organization_id,
            assessment_id=asm_a.assessment_id,
            requesting_user_id=teacher1.user_id,
            is_org_admin=False,
            payload=QuestionBankItemCreate(
                question_type=QuestionType.SHORT_ANSWER,
                question_text="New Question",
                default_marks=Decimal("1.00"),
                options=[]
            )
        )

    with pytest.raises(ConflictException, match="DRAFT status"):
        await service.reorder_assessment_questions(
            org_id=org.organization_id,
            assessment_id=asm_a.assessment_id,
            requesting_user_id=teacher1.user_id,
            is_org_admin=False,
            payload=QuestionReorderRequest(question_ids=[qa1.assessment_question_id])
        )

