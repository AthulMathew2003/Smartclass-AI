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
    QuestionStatus,
    AttemptStatus
)
from app.modules.assessments.service import AssessmentService
from app.modules.assessments.schemas import (
    AssessmentCreateRequest,
    QuestionBankItemCreate,
    AssessmentAddQuestionRequest,
    QuestionOptionCreate,
    StudentAttemptAnswerInput
)
from app.core.exceptions import (
    ConflictException,
    NotFoundException,
    ForbiddenException,
    ValidationException
)


@pytest.mark.asyncio
async def test_attempt_creation_lifecycle_and_answering(db_session):
    """Test full exam attempt flow: idempotency, question sanitization, answering, submission, and attempt limits."""
    # 1. Setup Teacher, Student, Org, Workspace, Subject
    teacher = User(user_email="prof_take@test.com", user_password_hash="hash", user_first_name="Prof", user_last_name="Taking")
    student = User(user_email="student_take@test.com", user_password_hash="hash", user_first_name="Alice", user_last_name="Learner")
    db_session.add_all([teacher, student])
    await db_session.flush()

    roles_res = await db_session.execute(select(Role).where(Role.role_is_system == True))
    roles_by_name = {r.role_name: r.role_id for r in roles_res.scalars().all()}

    org = Organization(organization_name="Take Academy", organization_slug="take-acad", organization_owner_user_id=teacher.user_id)
    db_session.add(org)
    await db_session.flush()

    ws = Workspace(workspace_organization_id=org.organization_id, workspace_name="Physics 101 WS", workspace_created_by=teacher.user_id)
    db_session.add(ws)
    await db_session.flush()

    subj = Subject(subject_workspace_id=ws.workspace_id, subject_name="Physics 101")
    db_session.add(subj)
    await db_session.flush()

    st = SubjectTeacher(subject_teacher_subject_id=subj.subject_id, subject_teacher_user_id=teacher.user_id)
    wm_teacher = WorkspaceMember(workspace_member_workspace_id=ws.workspace_id, workspace_member_user_id=teacher.user_id, workspace_member_role_id=roles_by_name["Teacher"])
    wm_student = WorkspaceMember(workspace_member_workspace_id=ws.workspace_id, workspace_member_user_id=student.user_id, workspace_member_role_id=roles_by_name["Student"])
    db_session.add_all([st, wm_teacher, wm_student])
    await db_session.flush()

    service = AssessmentService(db_session)

    # 2. Add Questions to Question Bank & Build Assessment
    q1_item = await service.create_question_bank_item(
        org_id=org.organization_id,
        subject_id=subj.subject_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False,
        payload=QuestionBankItemCreate(
            question_type=QuestionType.MCQ_SINGLE,
            question_text="What is Newton's second law?",
            default_marks=Decimal("5.00"),
            question_explanation="Force equals mass times acceleration (F=ma).",
            options=[
                QuestionOptionCreate(option_text="F = ma", option_order=1, option_is_correct=True),
                QuestionOptionCreate(option_text="E = mc^2", option_order=2, option_is_correct=False),
                QuestionOptionCreate(option_text="V = IR", option_order=3, option_is_correct=False),
            ]
        )
    )

    q2_item = await service.create_question_bank_item(
        org_id=org.organization_id,
        subject_id=subj.subject_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False,
        payload=QuestionBankItemCreate(
            question_type=QuestionType.TRUE_FALSE,
            question_text="Gravity attracts objects toward mass centers.",
            default_marks=Decimal("3.00"),
            options=[
                QuestionOptionCreate(option_text="True", option_order=1, option_is_correct=True),
                QuestionOptionCreate(option_text="False", option_order=2, option_is_correct=False),
            ]
        )
    )

    # 3. Create Assessment with attempt_limit = 2 and publish
    asm = await service.create_assessment(
        org_id=org.organization_id,
        created_by_user_id=teacher.user_id,
        is_org_admin=False,
        payload=AssessmentCreateRequest(
            subject_id=subj.subject_id,
            title="Midterm Exam",
            type=AssessmentType.EXAM,
            attempt_limit=2,
            randomize_questions=False
        )
    )

    await service.add_question_from_bank(
        org_id=org.organization_id,
        assessment_id=asm.assessment_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False,
        payload=AssessmentAddQuestionRequest(question_id=q1_item.question_id, marks=Decimal("5.00"), order=1)
    )
    await service.add_question_from_bank(
        org_id=org.organization_id,
        assessment_id=asm.assessment_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False,
        payload=AssessmentAddQuestionRequest(question_id=q2_item.question_id, marks=Decimal("3.00"), order=2)
    )

    # Draft assessment cannot be started by student
    with pytest.raises(ConflictException) as exc:
        await service.start_or_get_in_progress_attempt(
            org_id=org.organization_id,
            assessment_id=asm.assessment_id,
            student_user_id=student.user_id
        )
    assert "not open for taking" in str(exc.value)

    # Publish assessment
    await service.publish_assessment(
        org_id=org.organization_id,
        assessment_id=asm.assessment_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False
    )

    # 4. Student starts Attempt 1
    attempt1 = await service.start_or_get_in_progress_attempt(
        org_id=org.organization_id,
        assessment_id=asm.assessment_id,
        student_user_id=student.user_id
    )
    assert attempt1.attempt_number == 1
    assert attempt1.attempt_status == AttemptStatus.IN_PROGRESS
    assert len(attempt1.questions) == 2
    assert len(attempt1.attempt_question_order) == 2

    # Verify answers/explanations are sanitized for students
    for q in attempt1.questions:
        assert not hasattr(q, "question_explanation")
        for opt in q.options:
            assert not hasattr(opt, "option_is_correct")
            assert not hasattr(opt, "is_correct")

    # 5. Idempotent start: calling start again returns same attempt #1
    attempt1_retry = await service.start_or_get_in_progress_attempt(
        org_id=org.organization_id,
        assessment_id=asm.assessment_id,
        student_user_id=student.user_id
    )
    assert attempt1_retry.attempt_id == attempt1.attempt_id
    assert attempt1_retry.attempt_number == 1

    # 6. Student answers questions
    q1_id = attempt1.questions[0].assessment_question_id
    q1_opt_id = attempt1.questions[0].options[0].option_id

    save_res1 = await service.save_attempt_answer(
        org_id=org.organization_id,
        assessment_id=asm.assessment_id,
        attempt_id=attempt1.attempt_id,
        question_id=q1_id,
        student_user_id=student.user_id,
        payload=StudentAttemptAnswerInput(selected_option_id=q1_opt_id)
    )
    assert save_res1["status"] == "saved"

    q2_id = attempt1.questions[1].assessment_question_id
    q2_opt_id = attempt1.questions[1].options[0].option_id

    save_res2 = await service.save_attempt_answer(
        org_id=org.organization_id,
        assessment_id=asm.assessment_id,
        attempt_id=attempt1.attempt_id,
        question_id=q2_id,
        student_user_id=student.user_id,
        payload=StudentAttemptAnswerInput(selected_option_id=q2_opt_id)
    )
    assert save_res2["status"] == "saved"

    # Verify get_attempt shows saved answers
    fetched_att = await service.get_attempt(
        org_id=org.organization_id,
        assessment_id=asm.assessment_id,
        attempt_id=attempt1.attempt_id,
        requesting_user_id=student.user_id,
        is_org_admin=False
    )
    assert str(q1_id) in fetched_att.answers
    assert fetched_att.answers[str(q1_id)]["selected_option_id"] == str(q1_opt_id)

    # 7. Submit Attempt 1
    submitted_att1 = await service.submit_attempt(
        org_id=org.organization_id,
        assessment_id=asm.assessment_id,
        attempt_id=attempt1.attempt_id,
        student_user_id=student.user_id
    )
    assert submitted_att1.attempt_status == AttemptStatus.SUBMITTED
    assert submitted_att1.attempt_submitted_at is not None

    # Cannot save answers after submission
    with pytest.raises(ConflictException) as exc:
        await service.save_attempt_answer(
            org_id=org.organization_id,
            assessment_id=asm.assessment_id,
            attempt_id=attempt1.attempt_id,
            question_id=q1_id,
            student_user_id=student.user_id,
            payload=StudentAttemptAnswerInput(selected_option_id=q1_opt_id)
        )
    assert "Cannot save answer" in str(exc.value)

    # 8. Start Attempt 2 (within limit of 2)
    attempt2 = await service.start_or_get_in_progress_attempt(
        org_id=org.organization_id,
        assessment_id=asm.assessment_id,
        student_user_id=student.user_id
    )
    assert attempt2.attempt_id != attempt1.attempt_id
    assert attempt2.attempt_number == 2
    assert attempt2.attempt_status == AttemptStatus.IN_PROGRESS

    # Submit Attempt 2
    await service.submit_attempt(
        org_id=org.organization_id,
        assessment_id=asm.assessment_id,
        attempt_id=attempt2.attempt_id,
        student_user_id=student.user_id
    )

    # 9. Attempt 3 should fail due to attempt limit = 2
    with pytest.raises(ConflictException) as exc:
        await service.start_or_get_in_progress_attempt(
            org_id=org.organization_id,
            assessment_id=asm.assessment_id,
            student_user_id=student.user_id
        )
    assert "Maximum attempt limit (2) reached" in str(exc.value)

    # 10. Verify List Student Attempts
    history = await service.list_student_attempts(
        org_id=org.organization_id,
        assessment_id=asm.assessment_id,
        student_user_id=student.user_id
    )
    assert len(history) == 2
    assert history[0].attempt_number == 1
    assert history[1].attempt_number == 2


@pytest.mark.asyncio
async def test_attempt_security_and_tenant_isolation(db_session):
    """Test workspace membership requirement, cross-student attempt tampering prevention, and cross-subject protection."""
    # 1. Setup Teacher, Student A, Student B (different workspace)
    teacher = User(user_email="teacher_sec@test.com", user_password_hash="hash", user_first_name="Prof", user_last_name="Security")
    student_a = User(user_email="student_a@test.com", user_password_hash="hash", user_first_name="Student", user_last_name="A")
    student_b = User(user_email="student_b@test.com", user_password_hash="hash", user_first_name="Student", user_last_name="B")
    db_session.add_all([teacher, student_a, student_b])
    await db_session.flush()

    roles_res = await db_session.execute(select(Role).where(Role.role_is_system == True))
    roles_by_name = {r.role_name: r.role_id for r in roles_res.scalars().all()}

    org = Organization(organization_name="Security Univ", organization_slug="sec-univ", organization_owner_user_id=teacher.user_id)
    db_session.add(org)
    await db_session.flush()

    ws = Workspace(workspace_organization_id=org.organization_id, workspace_name="Sec Workspace", workspace_created_by=teacher.user_id)
    db_session.add(ws)
    await db_session.flush()

    subj = Subject(subject_workspace_id=ws.workspace_id, subject_name="Cybersecurity")
    db_session.add(subj)
    await db_session.flush()

    st = SubjectTeacher(subject_teacher_subject_id=subj.subject_id, subject_teacher_user_id=teacher.user_id)
    wm_teacher = WorkspaceMember(workspace_member_workspace_id=ws.workspace_id, workspace_member_user_id=teacher.user_id, workspace_member_role_id=roles_by_name["Teacher"])
    wm_student_a = WorkspaceMember(workspace_member_workspace_id=ws.workspace_id, workspace_member_user_id=student_a.user_id, workspace_member_role_id=roles_by_name["Student"])
    db_session.add_all([st, wm_teacher, wm_student_a])
    await db_session.flush()

    service = AssessmentService(db_session)

    # Create & Publish assessment with 1 question
    q_item = await service.create_question_bank_item(
        org_id=org.organization_id,
        subject_id=subj.subject_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False,
        payload=QuestionBankItemCreate(
            question_type=QuestionType.SHORT_ANSWER,
            question_text="Explain SQL injection.",
            default_marks=Decimal("10.00")
        )
    )

    asm = await service.create_assessment(
        org_id=org.organization_id,
        created_by_user_id=teacher.user_id,
        is_org_admin=False,
        payload=AssessmentCreateRequest(
            subject_id=subj.subject_id,
            title="Sec Quiz 1",
            type=AssessmentType.QUIZ,
            attempt_limit=1
        )
    )

    await service.add_question_from_bank(
        org_id=org.organization_id,
        assessment_id=asm.assessment_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False,
        payload=AssessmentAddQuestionRequest(question_id=q_item.question_id, marks=Decimal("10.00"), order=1)
    )

    await service.publish_assessment(
        org_id=org.organization_id,
        assessment_id=asm.assessment_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False
    )

    # Student B has no workspace membership -> starting attempt must fail
    with pytest.raises(ForbiddenException):
        await service.start_or_get_in_progress_attempt(
            org_id=org.organization_id,
            assessment_id=asm.assessment_id,
            student_user_id=student_b.user_id
        )

    # Student A starts attempt
    attempt_a = await service.start_or_get_in_progress_attempt(
        org_id=org.organization_id,
        assessment_id=asm.assessment_id,
        student_user_id=student_a.user_id
    )

    # Student B tries to submit answer to Student A's attempt -> Forbidden
    with pytest.raises(ForbiddenException):
        await service.save_attempt_answer(
            org_id=org.organization_id,
            assessment_id=asm.assessment_id,
            attempt_id=attempt_a.attempt_id,
            question_id=attempt_a.questions[0].assessment_question_id,
            student_user_id=student_b.user_id,
            payload=StudentAttemptAnswerInput(text_answer="Hacked answer")
        )

    # Student B tries to submit Student A's attempt -> Forbidden
    with pytest.raises(ForbiddenException):
        await service.submit_attempt(
            org_id=org.organization_id,
            assessment_id=asm.assessment_id,
            attempt_id=attempt_a.attempt_id,
            student_user_id=student_b.user_id
        )
