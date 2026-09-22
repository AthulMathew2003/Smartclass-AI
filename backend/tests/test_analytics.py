import uuid
import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
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
    StudentAttemptAnswerInput,
    ManualGradeInput
)
from app.core.exceptions import (
    NotFoundException,
    ForbiddenException,
    ConflictException
)


async def setup_analytics_env(db_session):
    teacher = User(user_email=f"prof_{uuid.uuid4().hex[:6]}@test.com", user_password_hash="hash", user_first_name="Prof", user_last_name="Analytics")
    unassigned_teacher = User(user_email=f"unassigned_{uuid.uuid4().hex[:6]}@test.com", user_password_hash="hash", user_first_name="Other", user_last_name="Teacher")
    student1 = User(user_email=f"student1_{uuid.uuid4().hex[:6]}@test.com", user_password_hash="hash", user_first_name="Alice", user_last_name="Smith")
    student2 = User(user_email=f"student2_{uuid.uuid4().hex[:6]}@test.com", user_password_hash="hash", user_first_name="Bob", user_last_name="Jones")
    student3 = User(user_email=f"student3_{uuid.uuid4().hex[:6]}@test.com", user_password_hash="hash", user_first_name="Charlie", user_last_name="Brown")
    
    db_session.add_all([teacher, unassigned_teacher, student1, student2, student3])
    await db_session.flush()

    roles_res = await db_session.execute(select(Role).where(Role.role_is_system == True))
    roles_by_name = {r.role_name: r.role_id for r in roles_res.scalars().all()}

    org = Organization(organization_name="Analytics Academy", organization_slug=f"analytics-acad-{uuid.uuid4().hex[:6]}", organization_owner_user_id=teacher.user_id)
    db_session.add(org)
    await db_session.flush()

    ws = Workspace(workspace_organization_id=org.organization_id, workspace_name="Analytics Workspace", workspace_created_by=teacher.user_id)
    db_session.add(ws)
    await db_session.flush()

    subj = Subject(subject_workspace_id=ws.workspace_id, subject_name="Data Analytics 101")
    db_session.add(subj)
    await db_session.flush()

    st = SubjectTeacher(subject_teacher_subject_id=subj.subject_id, subject_teacher_user_id=teacher.user_id)
    wm_teacher = WorkspaceMember(workspace_member_workspace_id=ws.workspace_id, workspace_member_user_id=teacher.user_id, workspace_member_role_id=roles_by_name["Teacher"])
    wm_unassigned = WorkspaceMember(workspace_member_workspace_id=ws.workspace_id, workspace_member_user_id=unassigned_teacher.user_id, workspace_member_role_id=roles_by_name["Teacher"])
    wm_s1 = WorkspaceMember(workspace_member_workspace_id=ws.workspace_id, workspace_member_user_id=student1.user_id, workspace_member_role_id=roles_by_name["Student"])
    wm_s2 = WorkspaceMember(workspace_member_workspace_id=ws.workspace_id, workspace_member_user_id=student2.user_id, workspace_member_role_id=roles_by_name["Student"])
    wm_s3 = WorkspaceMember(workspace_member_workspace_id=ws.workspace_id, workspace_member_user_id=student3.user_id, workspace_member_role_id=roles_by_name["Student"])
    
    db_session.add_all([st, wm_teacher, wm_unassigned, wm_s1, wm_s2, wm_s3])
    await db_session.flush()

    return teacher, unassigned_teacher, student1, student2, student3, org, ws, subj


@pytest.mark.asyncio
async def test_analytics_zero_attempts_empty_state(db_session):
    """Assessment with zero attempts safely returns empty statistics without division by zero errors."""
    teacher, _, _, _, _, org, ws, subj = await setup_analytics_env(db_session)
    service = AssessmentService(db_session)

    assessment = await service.repo.create_assessment(
        subject_id=subj.subject_id,
        title="Empty Assessment",
        description="No attempts yet",
        type=AssessmentType.QUIZ,
        status=AssessmentStatus.PUBLISHED,
        duration_minutes=30,
        start_at=None,
        end_at=None,
        total_marks=Decimal("20.00"),
        passing_marks=Decimal("10.00"),
        attempt_limit=2,
        randomize_questions=False,
        created_by=teacher.user_id
    )

    analytics = await service.get_assessment_analytics(
        org_id=org.organization_id,
        assessment_id=assessment.assessment_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False
    )

    assert analytics.assessment_id == assessment.assessment_id
    assert analytics.overview.total_attempts == 0
    assert analytics.overview.total_students_attempted == 0
    assert analytics.overview.total_completed_evaluations == 0
    assert analytics.overview.pass_percentage is None
    assert analytics.overview.participation_rate == 0.0 or analytics.overview.participation_rate is not None
    assert analytics.score_statistics.average_percentage is None
    assert analytics.score_statistics.median_percentage is None
    assert analytics.score_statistics.highest_percentage is None
    assert analytics.score_statistics.lowest_percentage is None
    assert analytics.score_statistics.total_marks == 20.0
    assert analytics.attempt_statistics.total_attempts == 0
    assert analytics.attempt_statistics.average_attempts_per_student is None
    assert len(analytics.student_statistics) == 0


@pytest.mark.asyncio
async def test_analytics_scores_overview_and_questions(db_session):
    """Test full score aggregation, median, mean, question accuracy, and pass rates across multiple students."""
    teacher, _, s1, s2, s3, org, ws, subj = await setup_analytics_env(db_session)
    service = AssessmentService(db_session)

    assessment = await service.repo.create_assessment(
        subject_id=subj.subject_id,
        title="Midterm Exam",
        description="Comprehensive exam",
        type=AssessmentType.EXAM,
        status=AssessmentStatus.PUBLISHED,
        duration_minutes=60,
        start_at=None,
        end_at=None,
        total_marks=Decimal("10.00"),
        passing_marks=Decimal("6.00"),
        attempt_limit=2,
        randomize_questions=False,
        created_by=teacher.user_id
    )

    # Add 2 questions: Q1 (MCQ single, 5 marks), Q2 (True/False, 5 marks)
    opt1_a = uuid.uuid4()
    opt1_b = uuid.uuid4()
    q1 = AssessmentQuestion(
        assessment_question_assessment_id=assessment.assessment_id,
        assessment_question_order=1,
        assessment_question_marks=Decimal("5.00"),
        assessment_question_snapshot={
            "question_type": "mcq_single",
            "question_text": "What is Python?",
            "options": [
                {"option_id": str(opt1_a), "option_text": "A programming language", "option_order": 1, "is_correct": True},
                {"option_id": str(opt1_b), "option_text": "A snake only", "option_order": 2, "is_correct": False},
            ]
        }
    )
    opt2_t = uuid.uuid4()
    opt2_f = uuid.uuid4()
    q2 = AssessmentQuestion(
        assessment_question_assessment_id=assessment.assessment_id,
        assessment_question_order=2,
        assessment_question_marks=Decimal("5.00"),
        assessment_question_snapshot={
            "question_type": "true_false",
            "question_text": "Is Postgres ACID compliant?",
            "options": [
                {"option_id": str(opt2_t), "option_text": "True", "option_order": 1, "is_correct": True},
                {"option_id": str(opt2_f), "option_text": "False", "option_order": 2, "is_correct": False},
            ]
        }
    )
    db_session.add_all([q1, q2])
    await db_session.flush()

    # Student 1: 10/10 (100%), Passed
    att1 = await service.repo.create_assessment_attempt(assessment.assessment_id, s1.user_id, 1, [str(q1.assessment_question_id), str(q2.assessment_question_id)])
    await service.save_attempt_answer(org.organization_id, assessment.assessment_id, att1.attempt_id, q1.assessment_question_id, s1.user_id, StudentAttemptAnswerInput(selected_option_id=opt1_a))
    await service.save_attempt_answer(org.organization_id, assessment.assessment_id, att1.attempt_id, q2.assessment_question_id, s1.user_id, StudentAttemptAnswerInput(selected_option_id=opt2_t))
    await service.submit_attempt(org.organization_id, assessment.assessment_id, att1.attempt_id, s1.user_id)

    # Student 2: 5/10 (50%), Failed (since passing is 6.00)
    att2 = await service.repo.create_assessment_attempt(assessment.assessment_id, s2.user_id, 1, [str(q1.assessment_question_id), str(q2.assessment_question_id)])
    await service.save_attempt_answer(org.organization_id, assessment.assessment_id, att2.attempt_id, q1.assessment_question_id, s2.user_id, StudentAttemptAnswerInput(selected_option_id=opt1_a))
    await service.save_attempt_answer(org.organization_id, assessment.assessment_id, att2.attempt_id, q2.assessment_question_id, s2.user_id, StudentAttemptAnswerInput(selected_option_id=opt2_f)) # Incorrect
    await service.submit_attempt(org.organization_id, assessment.assessment_id, att2.attempt_id, s2.user_id)

    # Student 3: 0/10 (0%), Failed (Unanswered)
    att3 = await service.repo.create_assessment_attempt(assessment.assessment_id, s3.user_id, 1, [str(q1.assessment_question_id), str(q2.assessment_question_id)])
    await service.submit_attempt(org.organization_id, assessment.assessment_id, att3.attempt_id, s3.user_id)

    analytics = await service.get_assessment_analytics(
        org_id=org.organization_id,
        assessment_id=assessment.assessment_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False
    )

    # Overview assertions
    assert analytics.overview.total_attempts == 3
    assert analytics.overview.total_students_attempted == 3
    assert analytics.overview.total_submitted_attempts == 3
    assert analytics.overview.total_completed_evaluations == 3
    assert analytics.overview.total_passed == 1
    assert analytics.overview.total_failed == 2
    assert analytics.overview.pass_percentage == 33.33

    # Score Statistics assertions: percentages are [100.0, 50.0, 0.0]
    assert analytics.score_statistics.average_percentage == 50.0
    assert analytics.score_statistics.median_percentage == 50.0
    assert analytics.score_statistics.highest_percentage == 100.0
    assert analytics.score_statistics.lowest_percentage == 0.0
    assert analytics.score_statistics.average_obtained_marks == 5.0
    assert analytics.score_statistics.total_marks == 10.0
    assert analytics.score_statistics.passing_marks == 6.0

    # Question statistics assertions
    q_stats = {qs.question_order: qs for qs in analytics.question_statistics}
    # Q1: S1 correct, S2 correct, S3 unanswered -> 2 correct, 0 incorrect, 1 unanswered. Accuracy = 2/2 = 100%
    assert q_stats[1].correct_count == 2
    assert q_stats[1].incorrect_count == 0
    assert q_stats[1].unanswered_count == 1
    assert q_stats[1].accuracy_percentage == 100.0
    assert q_stats[1].average_marks_awarded == 3.33

    # Q2: S1 correct, S2 incorrect, S3 unanswered -> 1 correct, 1 incorrect, 1 unanswered. Accuracy = 1/2 = 50%
    assert q_stats[2].correct_count == 1
    assert q_stats[2].incorrect_count == 1
    assert q_stats[2].unanswered_count == 1
    assert q_stats[2].accuracy_percentage == 50.0


@pytest.mark.asyncio
async def test_analytics_multiple_attempts_tracking(db_session):
    """Test that multiple attempts per student distinguish latest attempt from best attempt."""
    teacher, _, s1, _, _, org, ws, subj = await setup_analytics_env(db_session)
    service = AssessmentService(db_session)

    assessment = await service.repo.create_assessment(
        subject_id=subj.subject_id,
        title="Multi-Attempt Quiz",
        description="Testing multiple attempts",
        type=AssessmentType.QUIZ,
        status=AssessmentStatus.PUBLISHED,
        duration_minutes=30,
        start_at=None,
        end_at=None,
        total_marks=Decimal("10.00"),
        passing_marks=Decimal("7.00"),
        attempt_limit=3,
        randomize_questions=False,
        created_by=teacher.user_id
    )

    opt_correct = uuid.uuid4()
    opt_wrong = uuid.uuid4()
    q = AssessmentQuestion(
        assessment_question_assessment_id=assessment.assessment_id,
        assessment_question_order=1,
        assessment_question_marks=Decimal("10.00"),
        assessment_question_snapshot={
            "question_type": "mcq_single",
            "question_text": "Sample Question",
            "options": [
                {"option_id": str(opt_correct), "option_text": "Correct", "option_order": 1, "is_correct": True},
                {"option_id": str(opt_wrong), "option_text": "Wrong", "option_order": 2, "is_correct": False},
            ]
        }
    )
    db_session.add(q)
    await db_session.flush()

    # Attempt 1: Student gets 0/10 (Wrong option)
    att1 = await service.repo.create_assessment_attempt(assessment.assessment_id, s1.user_id, 1, [str(q.assessment_question_id)])
    await service.save_attempt_answer(org.organization_id, assessment.assessment_id, att1.attempt_id, q.assessment_question_id, s1.user_id, StudentAttemptAnswerInput(selected_option_id=opt_wrong))
    await service.submit_attempt(org.organization_id, assessment.assessment_id, att1.attempt_id, s1.user_id)

    # Attempt 2: Student gets 10/10 (Correct option)
    att2 = await service.repo.create_assessment_attempt(assessment.assessment_id, s1.user_id, 2, [str(q.assessment_question_id)])
    await service.save_attempt_answer(org.organization_id, assessment.assessment_id, att2.attempt_id, q.assessment_question_id, s1.user_id, StudentAttemptAnswerInput(selected_option_id=opt_correct))
    await service.submit_attempt(org.organization_id, assessment.assessment_id, att2.attempt_id, s1.user_id)

    analytics = await service.get_assessment_analytics(
        org_id=org.organization_id,
        assessment_id=assessment.assessment_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False
    )

    assert analytics.attempt_statistics.total_attempts == 2
    assert analytics.attempt_statistics.average_attempts_per_student == 2.0
    assert analytics.attempt_statistics.multiple_attempts_student_count == 1
    assert analytics.attempt_statistics.single_attempt_student_count == 0

    student_stat = analytics.student_statistics[0]
    assert student_stat.student_id == s1.user_id
    assert student_stat.total_attempts == 2
    assert student_stat.latest_attempt_number == 2
    assert student_stat.latest_percentage == 100.0
    assert student_stat.best_percentage == 100.0
    assert len(student_stat.attempts) == 2
    assert student_stat.attempts[0].percentage == 0.0
    assert student_stat.attempts[1].percentage == 100.0


@pytest.mark.asyncio
async def test_student_self_analytics_endpoint_and_isolation(db_session):
    """Test that students can fetch their own progression, but are blocked from accessing class analytics."""
    teacher, _, s1, s2, _, org, ws, subj = await setup_analytics_env(db_session)
    service = AssessmentService(db_session)

    assessment = await service.repo.create_assessment(
        subject_id=subj.subject_id,
        title="Student Privacy Test",
        description="Testing student self analytics",
        type=AssessmentType.QUIZ,
        status=AssessmentStatus.PUBLISHED,
        duration_minutes=30,
        start_at=None,
        end_at=None,
        total_marks=Decimal("10.00"),
        passing_marks=Decimal("5.00"),
        attempt_limit=2,
        randomize_questions=False,
        created_by=teacher.user_id
    )

    opt_correct = uuid.uuid4()
    q = AssessmentQuestion(
        assessment_question_assessment_id=assessment.assessment_id,
        assessment_question_order=1,
        assessment_question_marks=Decimal("10.00"),
        assessment_question_snapshot={
            "question_type": "mcq_single",
            "question_text": "Sample Question",
            "options": [
                {"option_id": str(opt_correct), "option_text": "Correct", "option_order": 1, "is_correct": True}
            ]
        }
    )
    db_session.add(q)
    await db_session.flush()

    # S1 takes attempt
    att1 = await service.repo.create_assessment_attempt(assessment.assessment_id, s1.user_id, 1, [str(q.assessment_question_id)])
    await service.save_attempt_answer(org.organization_id, assessment.assessment_id, att1.attempt_id, q.assessment_question_id, s1.user_id, StudentAttemptAnswerInput(selected_option_id=opt_correct))
    await service.submit_attempt(org.organization_id, assessment.assessment_id, att1.attempt_id, s1.user_id)

    # 1. Student self analytics
    self_analytics = await service.get_student_self_analytics(
        org_id=org.organization_id,
        assessment_id=assessment.assessment_id,
        student_user_id=s1.user_id
    )

    assert self_analytics.assessment_id == assessment.assessment_id
    assert self_analytics.total_attempts_used == 1
    assert self_analytics.attempts_remaining == 1
    assert self_analytics.latest_percentage == 100.0
    assert self_analytics.best_percentage == 100.0
    assert self_analytics.passed is True
    assert len(self_analytics.attempts) == 1

    # 2. Student S2 self analytics (no attempts)
    s2_analytics = await service.get_student_self_analytics(
        org_id=org.organization_id,
        assessment_id=assessment.assessment_id,
        student_user_id=s2.user_id
    )
    assert s2_analytics.total_attempts_used == 0
    assert s2_analytics.attempts_remaining == 2
    assert s2_analytics.latest_percentage is None
    assert len(s2_analytics.attempts) == 0

    # 3. Student trying to access teacher class analytics -> Must raise ForbiddenException
    with pytest.raises(ForbiddenException):
        await service.get_assessment_analytics(
            org_id=org.organization_id,
            assessment_id=assessment.assessment_id,
            requesting_user_id=s1.user_id,
            is_org_admin=False
        )


@pytest.mark.asyncio
async def test_analytics_rbac_unassigned_teacher_forbidden(db_session):
    """Unassigned teachers cannot access assessment analytics for subjects they do not teach."""
    teacher, unassigned_teacher, _, _, _, org, ws, subj = await setup_analytics_env(db_session)
    service = AssessmentService(db_session)

    assessment = await service.repo.create_assessment(
        subject_id=subj.subject_id,
        title="RBAC Teacher Test",
        description="Testing teacher assignment RBAC",
        type=AssessmentType.QUIZ,
        status=AssessmentStatus.PUBLISHED,
        duration_minutes=30,
        start_at=None,
        end_at=None,
        total_marks=Decimal("10.00"),
        passing_marks=Decimal("5.00"),
        attempt_limit=1,
        randomize_questions=False,
        created_by=teacher.user_id
    )

    # Assigned teacher succeeds
    res = await service.get_assessment_analytics(
        org_id=org.organization_id,
        assessment_id=assessment.assessment_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False
    )
    assert res.assessment_id == assessment.assessment_id

    # Unassigned teacher fails with 403 Forbidden
    with pytest.raises(ForbiddenException):
        await service.get_assessment_analytics(
            org_id=org.organization_id,
            assessment_id=assessment.assessment_id,
            requesting_user_id=unassigned_teacher.user_id,
            is_org_admin=False
        )


@pytest.mark.asyncio
async def test_analytics_pending_manual_grading_and_recalculation(db_session):
    """Analytics accurately reflect pending manual grading state and update dynamically after teacher grades."""
    teacher, _, s1, _, _, org, ws, subj = await setup_analytics_env(db_session)
    service = AssessmentService(db_session)

    assessment = await service.repo.create_assessment(
        subject_id=subj.subject_id,
        title="Essay Assessment",
        description="Short answer analytics test",
        type=AssessmentType.EXAM,
        status=AssessmentStatus.PUBLISHED,
        duration_minutes=60,
        start_at=None,
        end_at=None,
        total_marks=Decimal("10.00"),
        passing_marks=Decimal("5.00"),
        attempt_limit=1,
        randomize_questions=False,
        created_by=teacher.user_id
    )

    q = AssessmentQuestion(
        assessment_question_assessment_id=assessment.assessment_id,
        assessment_question_order=1,
        assessment_question_marks=Decimal("10.00"),
        assessment_question_snapshot={
            "question_type": "short_answer",
            "question_text": "Explain recursion.",
            "options": []
        }
    )
    db_session.add(q)
    await db_session.flush()

    att = await service.repo.create_assessment_attempt(assessment.assessment_id, s1.user_id, 1, [str(q.assessment_question_id)])
    await service.save_attempt_answer(org.organization_id, assessment.assessment_id, att.attempt_id, q.assessment_question_id, s1.user_id, StudentAttemptAnswerInput(text_answer="A function calling itself."))
    await service.submit_attempt(org.organization_id, assessment.assessment_id, att.attempt_id, s1.user_id)

    # 1. Check analytics while pending manual grading
    analytics_before = await service.get_assessment_analytics(
        org_id=org.organization_id,
        assessment_id=assessment.assessment_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False
    )
    assert analytics_before.overview.total_pending_manual_grading == 1
    assert analytics_before.overview.total_completed_evaluations == 0
    assert analytics_before.score_statistics.average_percentage is None
    assert analytics_before.question_statistics[0].pending_count == 1
    assert analytics_before.student_statistics[0].has_pending_grading is True

    # 2. Teacher grades the question (8 / 10)
    await service.grade_question(
        org_id=org.organization_id,
        assessment_id=assessment.assessment_id,
        attempt_id=att.attempt_id,
        question_id=q.assessment_question_id,
        grader_user_id=teacher.user_id,
        is_org_admin=False,
        payload=ManualGradeInput(marks_awarded=Decimal("8.00"), feedback="Good explanation.")
    )

    # 3. Check analytics after grading
    analytics_after = await service.get_assessment_analytics(
        org_id=org.organization_id,
        assessment_id=assessment.assessment_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False
    )
    assert analytics_after.overview.total_pending_manual_grading == 0
    assert analytics_after.overview.total_completed_evaluations == 1
    assert analytics_after.overview.total_passed == 1
    assert analytics_after.score_statistics.average_percentage == 80.0
    assert analytics_after.score_statistics.median_percentage == 80.0
    assert analytics_after.question_statistics[0].pending_count == 0
    assert analytics_after.question_statistics[0].average_marks_awarded == 8.0
    assert analytics_after.student_statistics[0].has_pending_grading is False
    assert analytics_after.student_statistics[0].latest_percentage == 80.0
    assert analytics_after.student_statistics[0].latest_passed is True
