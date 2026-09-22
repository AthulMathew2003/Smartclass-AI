import uuid
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import select

from app.modules.users.models import User
from app.modules.organizations.models import (
    Organization,
    Workspace,
    Role,
    WorkspaceMember
)
from app.modules.subjects.models import Subject, SubjectTeacher
from app.modules.assessments.models import (
    Assessment,
    AssessmentType,
    AssessmentStatus,
    QuestionType,
    AttemptStatus,
    ResultStatus,
    GradingStatus,
    CorrectnessStatus,
    AssessmentQuestion,
    AssessmentAttempt,
    AssessmentAttemptAnswer,
    AssessmentResult,
    AssessmentResultQuestion
)
from app.modules.assessments.service import AssessmentService
from app.modules.assessments.schemas import (
    QuestionBankItemCreate,
    QuestionOptionCreate,
    StudentAttemptAnswerInput,
    ManualGradeInput
)
from app.core.exceptions import (
    NotFoundException,
    ForbiddenException,
    ConflictException,
    ValidationException
)


async def setup_env(db_session):
    teacher = User(user_email=f"prof_{uuid.uuid4().hex[:6]}@test.com", user_password_hash="hash", user_first_name="Prof", user_last_name="Grader")
    student = User(user_email=f"student_{uuid.uuid4().hex[:6]}@test.com", user_password_hash="hash", user_first_name="Alice", user_last_name="Learner")
    db_session.add_all([teacher, student])
    await db_session.flush()

    roles_res = await db_session.execute(select(Role).where(Role.role_is_system == True))
    roles_by_name = {r.role_name: r.role_id for r in roles_res.scalars().all()}

    org = Organization(organization_name="Grading Academy", organization_slug=f"grading-acad-{uuid.uuid4().hex[:6]}", organization_owner_user_id=teacher.user_id)
    db_session.add(org)
    await db_session.flush()

    ws = Workspace(workspace_organization_id=org.organization_id, workspace_name="Grading Workspace", workspace_created_by=teacher.user_id)
    db_session.add(ws)
    await db_session.flush()

    subj = Subject(subject_workspace_id=ws.workspace_id, subject_name="Computer Science 101")
    db_session.add(subj)
    await db_session.flush()

    st = SubjectTeacher(subject_teacher_subject_id=subj.subject_id, subject_teacher_user_id=teacher.user_id)
    wm_teacher = WorkspaceMember(workspace_member_workspace_id=ws.workspace_id, workspace_member_user_id=teacher.user_id, workspace_member_role_id=roles_by_name["Teacher"])
    wm_student = WorkspaceMember(workspace_member_workspace_id=ws.workspace_id, workspace_member_user_id=student.user_id, workspace_member_role_id=roles_by_name["Student"])
    db_session.add_all([st, wm_teacher, wm_student])
    await db_session.flush()

    return teacher, student, org, ws, subj


@pytest.mark.asyncio
async def test_mcq_single_correct_and_incorrect(db_session):
    """MCQ single answer: correct gets full marks, incorrect gets zero, unanswered gets zero."""
    teacher, student, org, ws, subj = await setup_env(db_session)
    service = AssessmentService(db_session)

    assessment = await service.repo.create_assessment(
        subject_id=subj.subject_id,
        title="MCQ Single Test",
        description="Testing MCQ single grading",
        type=AssessmentType.QUIZ,
        status=AssessmentStatus.PUBLISHED,
        duration_minutes=30,
        start_at=None,
        end_at=None,
        total_marks=Decimal("10.00"),
        passing_marks=Decimal("5.00"),
        attempt_limit=3,
        randomize_questions=False,
        created_by=teacher.user_id
    )

    opt1_id = uuid.uuid4()
    opt2_id = uuid.uuid4()
    snapshot = {
        "question_type": "mcq_single",
        "question_text": "What is 2 + 2?",
        "options": [
            {"option_id": str(opt1_id), "option_text": "4", "option_order": 1, "option_is_correct": True},
            {"option_id": str(opt2_id), "option_text": "5", "option_order": 2, "option_is_correct": False}
        ]
    }
    q = AssessmentQuestion(
        assessment_question_assessment_id=assessment.assessment_id,
        assessment_question_order=1,
        assessment_question_marks=Decimal("5.00"),
        assessment_question_snapshot=snapshot
    )
    db_session.add(q)
    await db_session.flush()

    # 1. Student answers correctly
    att1 = await service.repo.create_assessment_attempt(
        assessment_id=assessment.assessment_id,
        student_id=student.user_id,
        attempt_number=1,
        question_order=[str(q.assessment_question_id)],
        expires_at=None
    )
    await service.repo.upsert_attempt_answer(
        attempt_id=att1.attempt_id,
        question_id=q.assessment_question_id,
        answer_value={"selected_option_id": str(opt1_id)}
    )
    await service.repo.submit_attempt(att1)
    res1 = await service.evaluate_attempt(att1.attempt_id)

    assert res1.result_total_marks == Decimal("5.00")
    assert res1.result_obtained_marks == Decimal("5.00")
    assert res1.result_percentage == Decimal("100.00")
    assert res1.result_correct_count == 1
    assert res1.result_incorrect_count == 0
    assert res1.result_unanswered_count == 0
    assert res1.result_status == ResultStatus.COMPLETED
    assert res1.result_passed is True

    # 2. Student answers incorrectly
    att2 = await service.repo.create_assessment_attempt(
        assessment_id=assessment.assessment_id,
        student_id=student.user_id,
        attempt_number=2,
        question_order=[str(q.assessment_question_id)],
        expires_at=None
    )
    await service.repo.upsert_attempt_answer(
        attempt_id=att2.attempt_id,
        question_id=q.assessment_question_id,
        answer_value={"selected_option_id": str(opt2_id)}
    )
    await service.repo.submit_attempt(att2)
    res2 = await service.evaluate_attempt(att2.attempt_id)

    assert res2.result_obtained_marks == Decimal("0.00")
    assert res2.result_percentage == Decimal("0.00")
    assert res2.result_correct_count == 0
    assert res2.result_incorrect_count == 1
    assert res2.result_passed is False

    # 3. Student leaves unanswered
    att3 = await service.repo.create_assessment_attempt(
        assessment_id=assessment.assessment_id,
        student_id=student.user_id,
        attempt_number=3,
        question_order=[str(q.assessment_question_id)],
        expires_at=None
    )
    await service.repo.submit_attempt(att3)
    res3 = await service.evaluate_attempt(att3.attempt_id)

    assert res3.result_obtained_marks == Decimal("0.00")
    assert res3.result_correct_count == 0
    assert res3.result_unanswered_count == 1
    assert res3.result_passed is False


@pytest.mark.asyncio
async def test_true_false_evaluation(db_session):
    """True/False question evaluation."""
    teacher, student, org, ws, subj = await setup_env(db_session)
    service = AssessmentService(db_session)

    assessment = await service.repo.create_assessment(
        subject_id=subj.subject_id,
        title="TF Assessment",
        description="Testing TF",
        type=AssessmentType.QUIZ,
        status=AssessmentStatus.PUBLISHED,
        duration_minutes=30,
        start_at=None,
        end_at=None,
        total_marks=Decimal("5.00"),
        passing_marks=Decimal("3.00"),
        attempt_limit=2,
        randomize_questions=False,
        created_by=teacher.user_id
    )

    t_id = uuid.uuid4()
    f_id = uuid.uuid4()
    snapshot = {
        "question_type": "true_false",
        "question_text": "The Earth is round.",
        "options": [
            {"option_id": str(t_id), "option_text": "True", "option_order": 1, "option_is_correct": True},
            {"option_id": str(f_id), "option_text": "False", "option_order": 2, "option_is_correct": False}
        ]
    }
    q = AssessmentQuestion(
        assessment_question_assessment_id=assessment.assessment_id,
        assessment_question_order=1,
        assessment_question_marks=Decimal("5.00"),
        assessment_question_snapshot=snapshot
    )
    db_session.add(q)
    await db_session.flush()

    # True answer
    att = await service.repo.create_assessment_attempt(
        assessment_id=assessment.assessment_id,
        student_id=student.user_id,
        attempt_number=1,
        question_order=[str(q.assessment_question_id)],
        expires_at=None
    )
    await service.repo.upsert_attempt_answer(
        attempt_id=att.attempt_id,
        question_id=q.assessment_question_id,
        answer_value={"selected_option_id": str(t_id)}
    )
    await service.repo.submit_attempt(att)
    res = await service.evaluate_attempt(att.attempt_id)

    assert res.result_obtained_marks == Decimal("5.00")
    assert res.result_correct_count == 1
    assert res.result_passed is True


@pytest.mark.asyncio
async def test_mcq_multiple_exact_match_and_order_insensitivity(db_session):
    """MCQ Multiple: exact set matching, order-insensitive, partial/extra gives zero."""
    teacher, student, org, ws, subj = await setup_env(db_session)
    service = AssessmentService(db_session)

    assessment = await service.repo.create_assessment(
        subject_id=subj.subject_id,
        title="MCQ Multiple Assessment",
        description="Testing multiple options",
        type=AssessmentType.QUIZ,
        status=AssessmentStatus.PUBLISHED,
        duration_minutes=30,
        start_at=None,
        end_at=None,
        total_marks=Decimal("10.00"),
        passing_marks=Decimal("5.00"),
        attempt_limit=5,
        randomize_questions=False,
        created_by=teacher.user_id
    )

    optA = uuid.uuid4()
    optB = uuid.uuid4()
    optC = uuid.uuid4()
    optD = uuid.uuid4()
    # Correct: A, C, D
    snapshot = {
        "question_type": "mcq_multiple",
        "question_text": "Select prime numbers under 10",
        "options": [
            {"option_id": str(optA), "option_text": "2", "option_order": 1, "option_is_correct": True},
            {"option_id": str(optB), "option_text": "4", "option_order": 2, "option_is_correct": False},
            {"option_id": str(optC), "option_text": "3", "option_order": 3, "option_is_correct": True},
            {"option_id": str(optD), "option_text": "5", "option_order": 4, "option_is_correct": True}
        ]
    }
    q = AssessmentQuestion(
        assessment_question_assessment_id=assessment.assessment_id,
        assessment_question_order=1,
        assessment_question_marks=Decimal("10.00"),
        assessment_question_snapshot=snapshot
    )
    db_session.add(q)
    await db_session.flush()

    # 1. Exact match in different order: [D, A, C]
    att1 = await service.repo.create_assessment_attempt(
        assessment_id=assessment.assessment_id,
        student_id=student.user_id,
        attempt_number=1,
        question_order=[str(q.assessment_question_id)],
        expires_at=None
    )
    await service.repo.upsert_attempt_answer(
        attempt_id=att1.attempt_id,
        question_id=q.assessment_question_id,
        answer_value={"selected_option_ids": [str(optD), str(optA), str(optC)]}
    )
    await service.repo.submit_attempt(att1)
    res1 = await service.evaluate_attempt(att1.attempt_id)
    assert res1.result_obtained_marks == Decimal("10.00")
    assert res1.result_correct_count == 1

    # 2. Missing option (partial credit not supported in V1): [A, C] -> 0 marks
    att2 = await service.repo.create_assessment_attempt(
        assessment_id=assessment.assessment_id,
        student_id=student.user_id,
        attempt_number=2,
        question_order=[str(q.assessment_question_id)],
        expires_at=None
    )
    await service.repo.upsert_attempt_answer(
        attempt_id=att2.attempt_id,
        question_id=q.assessment_question_id,
        answer_value={"selected_option_ids": [str(optA), str(optC)]}
    )
    await service.repo.submit_attempt(att2)
    res2 = await service.evaluate_attempt(att2.attempt_id)
    assert res2.result_obtained_marks == Decimal("0.00")
    assert res2.result_incorrect_count == 1

    # 3. Extra incorrect option: [A, B, C, D] -> 0 marks
    att3 = await service.repo.create_assessment_attempt(
        assessment_id=assessment.assessment_id,
        student_id=student.user_id,
        attempt_number=3,
        question_order=[str(q.assessment_question_id)],
        expires_at=None
    )
    await service.repo.upsert_attempt_answer(
        attempt_id=att3.attempt_id,
        question_id=q.assessment_question_id,
        answer_value={"selected_option_ids": [str(optA), str(optB), str(optC), str(optD)]}
    )
    await service.repo.submit_attempt(att3)
    res3 = await service.evaluate_attempt(att3.attempt_id)
    assert res3.result_obtained_marks == Decimal("0.00")
    assert res3.result_incorrect_count == 1


@pytest.mark.asyncio
async def test_short_answer_pending_and_manual_grading(db_session):
    """Short answer questions: pending status, teacher grading, recalculation, feedback."""
    teacher, student, org, ws, subj = await setup_env(db_session)
    service = AssessmentService(db_session)
    org_id = org.organization_id

    # Create assessment with passing mark 8.00 out of 10.00
    assessment = await service.repo.create_assessment(
        subject_id=subj.subject_id,
        title="Mixed Exam",
        description="MCQ + Short Answer",
        type=AssessmentType.EXAM,
        status=AssessmentStatus.PUBLISHED,
        duration_minutes=60,
        start_at=None,
        end_at=None,
        total_marks=Decimal("10.00"),
        passing_marks=Decimal("8.00"),
        attempt_limit=1,
        randomize_questions=False,
        created_by=teacher.user_id
    )

    # Q1: MCQ (5 marks)
    opt1 = uuid.uuid4()
    opt2 = uuid.uuid4()
    q1 = AssessmentQuestion(
        assessment_question_assessment_id=assessment.assessment_id,
        assessment_question_order=1,
        assessment_question_marks=Decimal("5.00"),
        assessment_question_snapshot={
            "question_type": "mcq_single",
            "question_text": "What is Python?",
            "options": [
                {"option_id": str(opt1), "option_text": "A programming language", "option_is_correct": True},
                {"option_id": str(opt2), "option_text": "A snake only", "option_is_correct": False}
            ]
        }
    )
    # Q2: Short Answer (5 marks)
    q2 = AssessmentQuestion(
        assessment_question_assessment_id=assessment.assessment_id,
        assessment_question_order=2,
        assessment_question_marks=Decimal("5.00"),
        assessment_question_snapshot={
            "question_type": "short_answer",
            "question_text": "Explain polymorphism in OOP in your own words."
        }
    )
    db_session.add_all([q1, q2])
    await db_session.flush()

    # Student answers Q1 correctly and answers Q2 with essay text
    attempt = await service.repo.create_assessment_attempt(
        assessment_id=assessment.assessment_id,
        student_id=student.user_id,
        attempt_number=1,
        question_order=[str(q1.assessment_question_id), str(q2.assessment_question_id)],
        expires_at=None
    )
    await service.repo.upsert_attempt_answer(
        attempt_id=attempt.attempt_id,
        question_id=q1.assessment_question_id,
        answer_value={"selected_option_id": str(opt1)}
    )
    await service.repo.upsert_attempt_answer(
        attempt_id=attempt.attempt_id,
        question_id=q2.assessment_question_id,
        answer_value={"text_answer": "Polymorphism allows different classes to define their own implementations of methods with the same name."}
    )

    # Submit attempt -> auto-evaluates
    await service.submit_attempt(
        org_id=org_id,
        assessment_id=assessment.assessment_id,
        attempt_id=attempt.attempt_id,
        student_user_id=student.user_id
    )

    # Result state before manual grading
    res = await service.get_attempt_result(
        org_id=org_id,
        assessment_id=assessment.assessment_id,
        attempt_id=attempt.attempt_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=True
    )
    assert res.total_marks == Decimal("10.00")
    assert res.obtained_marks == Decimal("5.00")
    assert res.pending_count == 1
    assert res.status == ResultStatus.PENDING_MANUAL_GRADING
    # Result must not falsely show passed/failed while pending!
    assert res.passed is None

    # Teacher grades Q2: invalid score (> 5.00) must be rejected
    with pytest.raises(ValidationException):
        await service.grade_question(
            org_id=org_id,
            assessment_id=assessment.assessment_id,
            attempt_id=attempt.attempt_id,
            question_id=q2.assessment_question_id,
            grader_user_id=teacher.user_id,
            is_org_admin=True,
            payload=ManualGradeInput(marks_awarded=Decimal("6.00"), feedback="Too high")
        )

    # Teacher awards 4.00 / 5.00
    graded_res = await service.grade_question(
        org_id=org_id,
        assessment_id=assessment.assessment_id,
        attempt_id=attempt.attempt_id,
        question_id=q2.assessment_question_id,
        grader_user_id=teacher.user_id,
        is_org_admin=True,
        payload=ManualGradeInput(marks_awarded=Decimal("4.00"), feedback="Great explanation!")
    )

    assert graded_res.status == ResultStatus.COMPLETED
    assert graded_res.pending_count == 0
    assert graded_res.obtained_marks == Decimal("9.00")
    assert graded_res.percentage == Decimal("90.00")
    assert graded_res.passed is True  # 9.00 >= passing_marks 8.00

    # Teacher regrades: changes mark to 2.00 -> total becomes 7.00 (< 8.00 passing) -> passed is False
    regraded_res = await service.grade_question(
        org_id=org_id,
        assessment_id=assessment.assessment_id,
        attempt_id=attempt.attempt_id,
        question_id=q2.assessment_question_id,
        grader_user_id=teacher.user_id,
        is_org_admin=True,
        payload=ManualGradeInput(marks_awarded=Decimal("2.00"), feedback="Needs more detail.")
    )

    assert regraded_res.obtained_marks == Decimal("7.00")
    assert regraded_res.percentage == Decimal("70.00")
    assert regraded_res.passed is False


@pytest.mark.asyncio
async def test_evaluation_idempotency_and_duplicate_submits(db_session):
    """Calling evaluation multiple times or duplicate submits returns the exact same stable result."""
    teacher, student, org, ws, subj = await setup_env(db_session)
    service = AssessmentService(db_session)
    org_id = org.organization_id

    assessment = await service.repo.create_assessment(
        subject_id=subj.subject_id,
        title="Idempotency Assessment",
        description="Testing idempotency",
        type=AssessmentType.QUIZ,
        status=AssessmentStatus.PUBLISHED,
        duration_minutes=15,
        start_at=None,
        end_at=None,
        total_marks=Decimal("5.00"),
        passing_marks=None,
        attempt_limit=1,
        randomize_questions=False,
        created_by=teacher.user_id
    )

    opt1 = uuid.uuid4()
    q = AssessmentQuestion(
        assessment_question_assessment_id=assessment.assessment_id,
        assessment_question_order=1,
        assessment_question_marks=Decimal("5.00"),
        assessment_question_snapshot={
            "question_type": "mcq_single",
            "question_text": "Sample Q",
            "options": [{"option_id": str(opt1), "option_text": "A", "option_is_correct": True}]
        }
    )
    db_session.add(q)
    await db_session.flush()

    attempt = await service.repo.create_assessment_attempt(
        assessment_id=assessment.assessment_id,
        student_id=student.user_id,
        attempt_number=1,
        question_order=[str(q.assessment_question_id)],
        expires_at=None
    )
    await service.repo.upsert_attempt_answer(
        attempt_id=attempt.attempt_id,
        question_id=q.assessment_question_id,
        answer_value={"selected_option_id": str(opt1)}
    )

    # First submit
    sub1 = await service.submit_attempt(
        org_id=org_id,
        assessment_id=assessment.assessment_id,
        attempt_id=attempt.attempt_id,
        student_user_id=student.user_id
    )

    res1 = await service.get_attempt_result(
        org_id=org_id,
        assessment_id=assessment.assessment_id,
        attempt_id=attempt.attempt_id,
        requesting_user_id=student.user_id,
        is_org_admin=False
    )

    # Duplicate submit
    sub2 = await service.submit_attempt(
        org_id=org_id,
        assessment_id=assessment.assessment_id,
        attempt_id=attempt.attempt_id,
        student_user_id=student.user_id
    )

    res2 = await service.get_attempt_result(
        org_id=org_id,
        assessment_id=assessment.assessment_id,
        attempt_id=attempt.attempt_id,
        requesting_user_id=student.user_id,
        is_org_admin=False
    )

    assert res1.result_id == res2.result_id
    assert res1.obtained_marks == res2.obtained_marks


@pytest.mark.asyncio
async def test_snapshot_integrity_protects_historical_results(db_session):
    """Snapshot integrity: modifying the question bank does NOT change frozen assessment evaluation."""
    teacher, student, org, ws, subj = await setup_env(db_session)
    service = AssessmentService(db_session)
    org_id = org.organization_id

    qb_item = await service.repo.create_question_bank_item(
        subject_id=subj.subject_id,
        question_type=QuestionType.MCQ_SINGLE,
        question_text="What is the capital of France?",
        default_marks=Decimal("2.00"),
        question_explanation="Paris is the capital.",
        created_by=teacher.user_id,
        options_data=[
            {"option_text": "Paris", "option_order": 1, "option_is_correct": True},
            {"option_text": "Lyon", "option_order": 2, "option_is_correct": False}
        ]
    )

    # Assessment publishes with question snapshot
    assessment = await service.repo.create_assessment(
        subject_id=subj.subject_id,
        title="Geography Quiz",
        description="Europe capitals",
        type=AssessmentType.QUIZ,
        status=AssessmentStatus.PUBLISHED,
        duration_minutes=10,
        start_at=None,
        end_at=None,
        total_marks=Decimal("2.00"),
        passing_marks=Decimal("2.00"),
        attempt_limit=1,
        randomize_questions=False,
        created_by=teacher.user_id
    )
    aq = await service.repo.create_assessment_question(
        assessment_id=assessment.assessment_id,
        question_id=qb_item.question_id,
        order=1,
        marks=Decimal("2.00"),
        snapshot=service._build_question_snapshot(
            question_id=qb_item.question_id,
            question_type=qb_item.question_type,
            question_text=qb_item.question_text,
            marks=Decimal("2.00"),
            question_explanation=qb_item.question_explanation,
            options=qb_item.options
        )
    )

    optA = [opt["option_id"] for opt in aq.assessment_question_snapshot["options"] if opt["option_is_correct"]][0]

    # Student took the quiz and chose "Paris" (optA)
    attempt = await service.repo.create_assessment_attempt(
        assessment_id=assessment.assessment_id,
        student_id=student.user_id,
        attempt_number=1,
        question_order=[str(aq.assessment_question_id)],
        expires_at=None
    )
    await service.repo.upsert_attempt_answer(
        attempt_id=attempt.attempt_id,
        question_id=aq.assessment_question_id,
        answer_value={"selected_option_id": str(optA)}
    )
    await service.repo.submit_attempt(attempt)

    # Now teacher edits the Question Bank item later (e.g. changes options/marks in QB)
    await service.repo.update_question_bank_item(
        question=qb_item,
        question_type=QuestionType.MCQ_SINGLE,
        question_text="What is the capital of France? (Updated)",
        default_marks=Decimal("5.00"),
        question_explanation="Updated explanation",
        options_data=[
            {"option_text": "Marseille", "option_order": 1, "option_is_correct": False},
            {"option_text": "Nice", "option_order": 2, "option_is_correct": True}
        ]
    )

    # Re-evaluate / fetch student result — student's score must remain 2.00 and Correct based on snapshot!
    res = await service.get_attempt_result(
        org_id=org_id,
        assessment_id=assessment.assessment_id,
        attempt_id=attempt.attempt_id,
        requesting_user_id=student.user_id,
        is_org_admin=False
    )
    assert res.total_marks == Decimal("2.00")
    assert res.obtained_marks == Decimal("2.00")
    assert res.correct_count == 1
    assert res.passed is True


@pytest.mark.asyncio
async def test_malformed_and_cross_question_option_answers(db_session):
    """Evaluation safely handles random UUIDs, wrong question options, malformed payloads without crashing."""
    teacher, student, org, ws, subj = await setup_env(db_session)
    service = AssessmentService(db_session)

    assessment = await service.repo.create_assessment(
        subject_id=subj.subject_id,
        title="Safety Assessment",
        description="Testing malformed data",
        type=AssessmentType.QUIZ,
        status=AssessmentStatus.PUBLISHED,
        duration_minutes=10,
        start_at=None,
        end_at=None,
        total_marks=Decimal("5.00"),
        passing_marks=None,
        attempt_limit=1,
        randomize_questions=False,
        created_by=teacher.user_id
    )

    opt1 = uuid.uuid4()
    q = AssessmentQuestion(
        assessment_question_assessment_id=assessment.assessment_id,
        assessment_question_order=1,
        assessment_question_marks=Decimal("5.00"),
        assessment_question_snapshot={
            "question_type": "mcq_single",
            "question_text": "Sample Q",
            "options": [{"option_id": str(opt1), "option_text": "A", "option_is_correct": True}]
        }
    )
    db_session.add(q)
    await db_session.flush()

    attempt = await service.repo.create_assessment_attempt(
        assessment_id=assessment.assessment_id,
        student_id=student.user_id,
        attempt_number=1,
        question_order=[str(q.assessment_question_id)],
        expires_at=None
    )

    # Answer contains completely fake UUID
    fake_option_id = uuid.uuid4()
    await service.repo.upsert_attempt_answer(
        attempt_id=attempt.attempt_id,
        question_id=q.assessment_question_id,
        answer_value={"selected_option_id": str(fake_option_id)}
    )
    await service.repo.submit_attempt(attempt)

    res = await service.evaluate_attempt(attempt.attempt_id)
    assert res.result_obtained_marks == Decimal("0.00")
    assert res.result_incorrect_count == 1


@pytest.mark.asyncio
async def test_security_student_isolation_and_in_progress_protection(db_session):
    """Students cannot access other student results or view results while attempt is in progress."""
    teacher, student, org, ws, subj = await setup_env(db_session)
    service = AssessmentService(db_session)
    org_id = org.organization_id

    assessment = await service.repo.create_assessment(
        subject_id=subj.subject_id,
        title="Security Exam",
        description="Security test",
        type=AssessmentType.QUIZ,
        status=AssessmentStatus.PUBLISHED,
        duration_minutes=30,
        start_at=None,
        end_at=None,
        total_marks=Decimal("5.00"),
        passing_marks=None,
        attempt_limit=1,
        randomize_questions=False,
        created_by=teacher.user_id
    )

    attempt = await service.repo.create_assessment_attempt(
        assessment_id=assessment.assessment_id,
        student_id=student.user_id,
        attempt_number=1,
        question_order=[],
        expires_at=None
    )

    # 1. Viewing result during in_progress raises ConflictException
    with pytest.raises(ConflictException):
        await service.get_attempt_result(
            org_id=org_id,
            assessment_id=assessment.assessment_id,
            attempt_id=attempt.attempt_id,
            requesting_user_id=student.user_id,
            is_org_admin=False
        )

    # 2. Other unauthorized student cannot access result
    other_student_id = uuid.uuid4()
    await service.repo.submit_attempt(attempt)

    with pytest.raises(ForbiddenException):
        await service.get_attempt_result(
            org_id=org_id,
            assessment_id=assessment.assessment_id,
            attempt_id=attempt.attempt_id,
            requesting_user_id=other_student_id,
            is_org_admin=False
        )


@pytest.mark.asyncio
async def test_expired_attempt_evaluates_saved_answers(db_session):
    """Expired attempt evaluates with whatever answers were autosaved prior to expiry."""
    teacher, student, org, ws, subj = await setup_env(db_session)
    service = AssessmentService(db_session)
    org_id = org.organization_id

    assessment = await service.repo.create_assessment(
        subject_id=subj.subject_id,
        title="Timed Quiz",
        description="Timed test",
        type=AssessmentType.QUIZ,
        status=AssessmentStatus.PUBLISHED,
        duration_minutes=10,
        start_at=None,
        end_at=None,
        total_marks=Decimal("10.00"),
        passing_marks=Decimal("5.00"),
        attempt_limit=1,
        randomize_questions=False,
        created_by=teacher.user_id
    )

    opt1 = uuid.uuid4()
    opt2 = uuid.uuid4()
    q1 = AssessmentQuestion(
        assessment_question_assessment_id=assessment.assessment_id,
        assessment_question_order=1,
        assessment_question_marks=Decimal("5.00"),
        assessment_question_snapshot={
            "question_type": "mcq_single",
            "question_text": "Q1",
            "options": [{"option_id": str(opt1), "option_text": "Correct", "option_is_correct": True}]
        }
    )
    q2 = AssessmentQuestion(
        assessment_question_assessment_id=assessment.assessment_id,
        assessment_question_order=2,
        assessment_question_marks=Decimal("5.00"),
        assessment_question_snapshot={
            "question_type": "mcq_single",
            "question_text": "Q2",
            "options": [{"option_id": str(opt2), "option_text": "Correct", "option_is_correct": True}]
        }
    )
    db_session.add_all([q1, q2])
    await db_session.flush()

    attempt = await service.repo.create_assessment_attempt(
        assessment_id=assessment.assessment_id,
        student_id=student.user_id,
        attempt_number=1,
        question_order=[str(q1.assessment_question_id), str(q2.assessment_question_id)],
        expires_at=None
    )
    # Student answered Q1 but ran out of time before answering Q2
    await service.repo.upsert_attempt_answer(
        attempt_id=attempt.attempt_id,
        question_id=q1.assessment_question_id,
        answer_value={"selected_option_id": str(opt1)}
    )

    # Server expires attempt
    await service.repo.expire_attempt(attempt)
    res = await service.evaluate_attempt(attempt.attempt_id)

    assert res.result_total_marks == Decimal("10.00")
    assert res.result_obtained_marks == Decimal("5.00")
    assert res.result_percentage == Decimal("50.00")
    assert res.result_correct_count == 1
    assert res.result_unanswered_count == 1
    assert res.result_status == ResultStatus.COMPLETED
    assert res.result_passed is True


@pytest.mark.asyncio
async def test_teacher_from_another_subject_cannot_grade(db_session):
    """Teacher not assigned to subject receives ForbiddenException when attempting to grade."""
    teacher1, student, org, ws, subj = await setup_env(db_session)
    service = AssessmentService(db_session)
    org_id = org.organization_id

    # Create second teacher not assigned to this subject
    other_teacher = User(user_email=f"other_prof_{uuid.uuid4().hex[:6]}@test.com", user_password_hash="hash", user_first_name="Other", user_last_name="Prof")
    db_session.add(other_teacher)
    await db_session.flush()

    roles_res = await db_session.execute(select(Role).where(Role.role_name == "Teacher"))
    t_role = roles_res.scalar_one()

    wm_other = WorkspaceMember(workspace_member_workspace_id=ws.workspace_id, workspace_member_user_id=other_teacher.user_id, workspace_member_role_id=t_role.role_id)
    db_session.add(wm_other)
    await db_session.flush()

    assessment = await service.repo.create_assessment(
        subject_id=subj.subject_id,
        title="Restricted Exam",
        description="Teacher RBAC test",
        type=AssessmentType.EXAM,
        status=AssessmentStatus.PUBLISHED,
        duration_minutes=30,
        start_at=None,
        end_at=None,
        total_marks=Decimal("5.00"),
        passing_marks=None,
        attempt_limit=1,
        randomize_questions=False,
        created_by=teacher1.user_id
    )
    q = AssessmentQuestion(
        assessment_question_assessment_id=assessment.assessment_id,
        assessment_question_order=1,
        assessment_question_marks=Decimal("5.00"),
        assessment_question_snapshot={
            "question_type": "short_answer",
            "question_text": "Short answer question"
        }
    )
    db_session.add(q)
    await db_session.flush()

    attempt = await service.repo.create_assessment_attempt(
        assessment_id=assessment.assessment_id,
        student_id=student.user_id,
        attempt_number=1,
        question_order=[str(q.assessment_question_id)],
        expires_at=None
    )
    await service.repo.upsert_attempt_answer(
        attempt_id=attempt.attempt_id,
        question_id=q.assessment_question_id,
        answer_value={"text_answer": "My answer"}
    )
    await service.submit_attempt(
        org_id=org_id,
        assessment_id=assessment.assessment_id,
        attempt_id=attempt.attempt_id,
        student_user_id=student.user_id
    )

    # Other unassigned teacher cannot grade (is_org_admin=False)
    with pytest.raises(ForbiddenException):
        await service.grade_question(
            org_id=org_id,
            assessment_id=assessment.assessment_id,
            attempt_id=attempt.attempt_id,
            question_id=q.assessment_question_id,
            grader_user_id=other_teacher.user_id,
            is_org_admin=False,
            payload=ManualGradeInput(marks_awarded=Decimal("5.00"))
        )


@pytest.mark.asyncio
async def test_teacher_list_assessment_results_overview(db_session):
    """Teacher can list all student attempt results for an assessment."""
    teacher, student, org, ws, subj = await setup_env(db_session)
    service = AssessmentService(db_session)
    org_id = org.organization_id

    assessment = await service.repo.create_assessment(
        subject_id=subj.subject_id,
        title="Class Results Exam",
        description="Listing results test",
        type=AssessmentType.QUIZ,
        status=AssessmentStatus.PUBLISHED,
        duration_minutes=30,
        start_at=None,
        end_at=None,
        total_marks=Decimal("5.00"),
        passing_marks=Decimal("3.00"),
        attempt_limit=2,
        randomize_questions=False,
        created_by=teacher.user_id
    )

    opt1 = uuid.uuid4()
    q = AssessmentQuestion(
        assessment_question_assessment_id=assessment.assessment_id,
        assessment_question_order=1,
        assessment_question_marks=Decimal("5.00"),
        assessment_question_snapshot={
            "question_type": "mcq_single",
            "question_text": "Sample",
            "options": [{"option_id": str(opt1), "option_text": "A", "option_is_correct": True}]
        }
    )
    db_session.add(q)
    await db_session.flush()

    att1 = await service.repo.create_assessment_attempt(
        assessment_id=assessment.assessment_id,
        student_id=student.user_id,
        attempt_number=1,
        question_order=[str(q.assessment_question_id)],
        expires_at=None
    )
    await service.repo.upsert_attempt_answer(
        attempt_id=att1.attempt_id,
        question_id=q.assessment_question_id,
        answer_value={"selected_option_id": str(opt1)}
    )
    await service.submit_attempt(
        org_id=org_id,
        assessment_id=assessment.assessment_id,
        attempt_id=att1.attempt_id,
        student_user_id=student.user_id
    )

    results = await service.list_assessment_results(
        org_id=org_id,
        assessment_id=assessment.assessment_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False
    )

    assert len(results) == 1
    assert results[0].student_id == student.user_id
    assert results[0].obtained_marks == Decimal("5.00")
    assert results[0].passed is True
    assert results[0].status == ResultStatus.COMPLETED

