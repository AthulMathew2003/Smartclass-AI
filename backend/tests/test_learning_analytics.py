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
from app.modules.assessments.schemas import ObservedDifficultyBand
from app.core.exceptions import (
    NotFoundException,
    ForbiddenException
)


async def setup_learning_analytics_env(db_session):
    teacher = User(user_email=f"prof_{uuid.uuid4().hex[:6]}@test.com", user_password_hash="hash", user_first_name="Prof", user_last_name="Analytics")
    unassigned_teacher = User(user_email=f"unassigned_{uuid.uuid4().hex[:6]}@test.com", user_password_hash="hash", user_first_name="Other", user_last_name="Teacher")
    student1 = User(user_email=f"student1_{uuid.uuid4().hex[:6]}@test.com", user_password_hash="hash", user_first_name="Alice", user_last_name="Smith")
    student2 = User(user_email=f"student2_{uuid.uuid4().hex[:6]}@test.com", user_password_hash="hash", user_first_name="Bob", user_last_name="Jones")
    
    db_session.add_all([teacher, unassigned_teacher, student1, student2])
    await db_session.flush()

    roles_res = await db_session.execute(select(Role).where(Role.role_is_system == True))
    roles_by_name = {r.role_name: r.role_id for r in roles_res.scalars().all()}

    org = Organization(organization_name="Learning Analytics Academy", organization_slug=f"learning-acad-{uuid.uuid4().hex[:6]}", organization_owner_user_id=teacher.user_id)
    db_session.add(org)
    await db_session.flush()

    ws = Workspace(workspace_organization_id=org.organization_id, workspace_name="Analytics Workspace", workspace_created_by=teacher.user_id)
    db_session.add(ws)
    await db_session.flush()

    subj1 = Subject(subject_workspace_id=ws.workspace_id, subject_name="Mathematics 101")
    subj2 = Subject(subject_workspace_id=ws.workspace_id, subject_name="Physics 101")
    db_session.add_all([subj1, subj2])
    await db_session.flush()

    st = SubjectTeacher(subject_teacher_subject_id=subj1.subject_id, subject_teacher_user_id=teacher.user_id)
    st2 = SubjectTeacher(subject_teacher_subject_id=subj2.subject_teacher_user_id if hasattr(subj2, 'subject_teacher_user_id') else subj2.subject_id, subject_teacher_user_id=teacher.user_id)
    wm_teacher = WorkspaceMember(workspace_member_workspace_id=ws.workspace_id, workspace_member_user_id=teacher.user_id, workspace_member_role_id=roles_by_name["Teacher"])
    wm_unassigned = WorkspaceMember(workspace_member_workspace_id=ws.workspace_id, workspace_member_user_id=unassigned_teacher.user_id, workspace_member_role_id=roles_by_name["Teacher"])
    wm_s1 = WorkspaceMember(workspace_member_workspace_id=ws.workspace_id, workspace_member_user_id=student1.user_id, workspace_member_role_id=roles_by_name["Student"])
    wm_s2 = WorkspaceMember(workspace_member_workspace_id=ws.workspace_id, workspace_member_user_id=student2.user_id, workspace_member_role_id=roles_by_name["Student"])
    
    db_session.add_all([st, st2, wm_teacher, wm_unassigned, wm_s1, wm_s2])
    await db_session.flush()

    return teacher, unassigned_teacher, student1, student2, org, ws, subj1, subj2


@pytest.mark.asyncio
async def test_student_learning_analytics_empty_state(db_session):
    teacher, _, student1, _, org, _, _, _ = await setup_learning_analytics_env(db_session)
    service = AssessmentService(db_session)

    res = await service.get_student_learning_analytics(
        org_id=org.organization_id,
        target_student_id=student1.user_id,
        requesting_user_id=student1.user_id,
        is_org_admin=False
    )

    assert res.student_id == student1.user_id
    assert res.overview.total_assessments_completed == 0
    assert res.overview.average_percentage is None
    assert len(res.performance_progression) == 0
    assert len(res.subject_performance) == 0
    assert len(res.question_type_performance) == 4
    assert res.trend.improvement_from_previous is None


@pytest.mark.asyncio
async def test_student_learning_analytics_multi_assessment_progression(db_session):
    teacher, _, student1, _, org, _, subj1, subj2 = await setup_learning_analytics_env(db_session)
    service = AssessmentService(db_session)

    # Create 3 assessments
    now = datetime.now(timezone.utc)
    a1 = Assessment(
        assessment_subject_id=subj1.subject_id,
        assessment_created_by=teacher.user_id,
        assessment_title="Math Quiz 1",
        assessment_type=AssessmentType.QUIZ,
        assessment_status=AssessmentStatus.PUBLISHED,
        assessment_total_marks=Decimal("10.00"),
        assessment_passing_marks=Decimal("5.00")
    )
    a2 = Assessment(
        assessment_subject_id=subj1.subject_id,
        assessment_created_by=teacher.user_id,
        assessment_title="Math Quiz 2",
        assessment_type=AssessmentType.QUIZ,
        assessment_status=AssessmentStatus.PUBLISHED,
        assessment_total_marks=Decimal("20.00"),
        assessment_passing_marks=Decimal("10.00")
    )
    a3 = Assessment(
        assessment_subject_id=subj2.subject_id,
        assessment_created_by=teacher.user_id,
        assessment_title="Physics Exam 1",
        assessment_type=AssessmentType.EXAM,
        assessment_status=AssessmentStatus.PUBLISHED,
        assessment_total_marks=Decimal("50.00"),
        assessment_passing_marks=Decimal("25.00")
    )
    db_session.add_all([a1, a2, a3])
    await db_session.flush()

    # Create questions for a1
    q1 = AssessmentQuestion(
        assessment_question_assessment_id=a1.assessment_id,
        assessment_question_marks=Decimal("5.00"),
        assessment_question_order=0,
        assessment_question_snapshot={
            "question_text": "2 + 2 = ?",
            "question_type": QuestionType.MCQ_SINGLE.value,
            "options": []
        }
    )
    q2 = AssessmentQuestion(
        assessment_question_assessment_id=a1.assessment_id,
        assessment_question_marks=Decimal("5.00"),
        assessment_question_order=1,
        assessment_question_snapshot={
            "question_text": "Is math fun?",
            "question_type": QuestionType.TRUE_FALSE.value,
            "options": []
        }
    )
    q3 = AssessmentQuestion(
        assessment_question_assessment_id=a1.assessment_id,
        assessment_question_marks=Decimal("5.00"),
        assessment_question_order=2,
        assessment_question_snapshot={
            "question_text": "Explain gravity in one sentence.",
            "question_type": QuestionType.SHORT_ANSWER.value,
            "options": []
        }
    )
    db_session.add_all([q1, q2, q3])
    await db_session.flush()

    # Create attempts and results
    att1 = AssessmentAttempt(
        attempt_assessment_id=a1.assessment_id,
        attempt_student_id=student1.user_id,
        attempt_number=1,
        attempt_status=AttemptStatus.SUBMITTED,
        attempt_submitted_at=now - timedelta(days=5)
    )
    att2 = AssessmentAttempt(
        attempt_assessment_id=a2.assessment_id,
        attempt_student_id=student1.user_id,
        attempt_number=1,
        attempt_status=AttemptStatus.SUBMITTED,
        attempt_submitted_at=now - timedelta(days=3)
    )
    att3 = AssessmentAttempt(
        attempt_assessment_id=a3.assessment_id,
        attempt_student_id=student1.user_id,
        attempt_number=1,
        attempt_status=AttemptStatus.SUBMITTED,
        attempt_submitted_at=now - timedelta(days=1)
    )
    db_session.add_all([att1, att2, att3])
    await db_session.flush()

    res1 = AssessmentResult(
        result_attempt_id=att1.attempt_id,
        result_assessment_id=a1.assessment_id,
        result_student_id=student1.user_id,
        result_obtained_marks=Decimal("8.00"),
        result_total_marks=Decimal("10.00"),
        result_percentage=Decimal("80.00"),
        result_passed=True,
        result_status=ResultStatus.COMPLETED,
        result_created_at=now - timedelta(days=5)
    )
    res2 = AssessmentResult(
        result_attempt_id=att2.attempt_id,
        result_assessment_id=a2.assessment_id,
        result_student_id=student1.user_id,
        result_obtained_marks=Decimal("18.00"),
        result_total_marks=Decimal("20.00"),
        result_percentage=Decimal("90.00"),
        result_passed=True,
        result_status=ResultStatus.COMPLETED,
        result_created_at=now - timedelta(days=3)
    )
    res3 = AssessmentResult(
        result_attempt_id=att3.attempt_id,
        result_assessment_id=a3.assessment_id,
        result_student_id=student1.user_id,
        result_obtained_marks=Decimal("45.00"),
        result_total_marks=Decimal("50.00"),
        result_percentage=Decimal("90.00"),
        result_passed=True,
        result_status=ResultStatus.COMPLETED,
        result_created_at=now - timedelta(days=1)
    )
    db_session.add_all([res1, res2, res3])
    await db_session.flush()

    # Add question result items for a1
    rq1 = AssessmentResultQuestion(
        result_question_result_id=res1.result_id,
        result_question_assessment_question_id=q1.assessment_question_id,
        result_question_marks_awarded=Decimal("5.00"),
        result_question_marks_available=Decimal("5.00"),
        result_question_correctness=CorrectnessStatus.CORRECT,
        result_question_grading_status=GradingStatus.GRADED
    )
    rq2 = AssessmentResultQuestion(
        result_question_result_id=res1.result_id,
        result_question_assessment_question_id=q2.assessment_question_id,
        result_question_marks_awarded=Decimal("0.00"),
        result_question_marks_available=Decimal("5.00"),
        result_question_correctness=CorrectnessStatus.INCORRECT,
        result_question_grading_status=GradingStatus.GRADED
    )
    rq3 = AssessmentResultQuestion(
        result_question_result_id=res1.result_id,
        result_question_assessment_question_id=q3.assessment_question_id,
        result_question_marks_awarded=Decimal("3.00"),
        result_question_marks_available=Decimal("5.00"),
        result_question_correctness=CorrectnessStatus.CORRECT,
        result_question_grading_status=GradingStatus.GRADED
    )
    db_session.add_all([rq1, rq2, rq3])
    await db_session.flush()

    # Get student analytics
    analytics = await service.get_student_learning_analytics(
        org_id=org.organization_id,
        target_student_id=student1.user_id,
        requesting_user_id=student1.user_id,
        is_org_admin=False
    )

    # Validate overview
    assert analytics.overview.total_assessments_completed == 3
    assert analytics.overview.total_passed_count == 3
    # Average: (80 + 90 + 90) / 3 = 86.67
    assert round(analytics.overview.average_percentage, 2) == 86.67
    assert analytics.overview.best_percentage == 90.0

    # Validate trend points
    assert len(analytics.performance_progression) == 3
    assert analytics.performance_progression[0].assessment_title == "Math Quiz 1"
    assert analytics.performance_progression[0].percentage == 80.0
    assert analytics.performance_progression[1].percentage == 90.0
    assert analytics.performance_progression[2].percentage == 90.0

    # Validate trend metrics
    # Improvement from previous: 90.0 - 90.0 = 0.0 (or comparing res3 to res2)
    assert analytics.trend.improvement_from_previous == 0.0
    assert round(analytics.trend.recent_average_percentage, 2) == 86.67
    assert round(analytics.trend.historical_average_percentage, 2) == 86.67

    # Validate subject performance (Math has 2 assessments, Physics has 1)
    assert len(analytics.subject_performance) == 2
    math_perf = next(s for s in analytics.subject_performance if s.subject_id == subj1.subject_id)
    phys_perf = next(s for s in analytics.subject_performance if s.subject_id == subj2.subject_id)
    assert math_perf.assessments_completed == 2
    assert round(math_perf.average_percentage, 2) == 85.0
    assert phys_perf.assessments_completed == 1
    assert phys_perf.average_percentage == 90.0

    # Validate question type matrix
    assert len(analytics.question_type_performance) == 4
    mcq = next((qt for qt in analytics.question_type_performance if qt.question_type == QuestionType.MCQ_SINGLE), None)
    tf = next((qt for qt in analytics.question_type_performance if qt.question_type == QuestionType.TRUE_FALSE), None)
    sa = next((qt for qt in analytics.question_type_performance if qt.question_type == QuestionType.SHORT_ANSWER), None)
    assert mcq is not None and mcq.accuracy_percentage == 100.0
    assert tf is not None and tf.accuracy_percentage == 0.0
    assert sa is not None and sa.accuracy_percentage == 60.0  # 3.0 / 5.0 = 60.0%


@pytest.mark.asyncio
async def test_student_learning_analytics_privacy_isolation(db_session):
    _, _, student1, student2, org, _, _, _ = await setup_learning_analytics_env(db_session)
    service = AssessmentService(db_session)

    # Student 1 attempts to view Student 2's analytics
    with pytest.raises(ForbiddenException):
        await service.get_student_learning_analytics(
            org_id=org.organization_id,
            target_student_id=student2.user_id,
            requesting_user_id=student1.user_id,
            is_org_admin=False
        )


@pytest.mark.asyncio
async def test_student_learning_analytics_teacher_access(db_session):
    teacher, unassigned_teacher, student1, _, org, _, _, _ = await setup_learning_analytics_env(db_session)
    service = AssessmentService(db_session)

    # Assigned teacher should succeed
    res = await service.get_student_learning_analytics(
        org_id=org.organization_id,
        target_student_id=student1.user_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False
    )
    assert res.student_id == student1.user_id

    # Org admin should succeed
    admin_res = await service.get_student_learning_analytics(
        org_id=org.organization_id,
        target_student_id=student1.user_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=True
    )
    assert admin_res.student_id == student1.user_id


@pytest.mark.asyncio
async def test_subject_question_difficulty_analytics(db_session):
    teacher, _, student1, student2, org, _, subj1, _ = await setup_learning_analytics_env(db_session)
    service = AssessmentService(db_session)

    # Create assessment
    a = Assessment(
        assessment_subject_id=subj1.subject_id,
        assessment_created_by=teacher.user_id,
        assessment_title="Comprehensive Math",
        assessment_type=AssessmentType.EXAM,
        assessment_status=AssessmentStatus.PUBLISHED,
        assessment_total_marks=Decimal("30.00"),
        assessment_passing_marks=Decimal("15.00")
    )
    db_session.add(a)
    await db_session.flush()

    q_easy = AssessmentQuestion(
        assessment_question_assessment_id=a.assessment_id,
        assessment_question_marks=Decimal("5.00"),
        assessment_question_order=0,
        assessment_question_snapshot={
            "question_text": "Easy Question (100% correct)",
            "question_type": QuestionType.MCQ_SINGLE.value,
            "options": []
        }
    )
    q_mod = AssessmentQuestion(
        assessment_question_assessment_id=a.assessment_id,
        assessment_question_marks=Decimal("5.00"),
        assessment_question_order=1,
        assessment_question_snapshot={
            "question_text": "Moderate Question (50% correct)",
            "question_type": QuestionType.MCQ_SINGLE.value,
            "options": []
        }
    )
    q_hard = AssessmentQuestion(
        assessment_question_assessment_id=a.assessment_id,
        assessment_question_marks=Decimal("5.00"),
        assessment_question_order=2,
        assessment_question_snapshot={
            "question_text": "Hard Question (20% correct)",
            "question_type": QuestionType.MCQ_SINGLE.value,
            "options": []
        }
    )
    q_small = AssessmentQuestion(
        assessment_question_assessment_id=a.assessment_id,
        assessment_question_marks=Decimal("5.00"),
        assessment_question_order=3,
        assessment_question_snapshot={
            "question_text": "Small Sample Question (3 responses)",
            "question_type": QuestionType.MCQ_SINGLE.value,
            "options": []
        }
    )
    db_session.add_all([q_easy, q_mod, q_hard, q_small])
    await db_session.flush()

    # Create 5 students responses for q_easy, q_mod, q_hard
    for i in range(5):
        u = User(user_email=f"s_batch_{i}_{uuid.uuid4().hex[:4]}@test.com", user_password_hash="hash", user_first_name=f"S{i}", user_last_name="Test")
        db_session.add(u)
        await db_session.flush()

        att = AssessmentAttempt(
            attempt_assessment_id=a.assessment_id,
            attempt_student_id=u.user_id,
            attempt_number=1,
            attempt_status=AttemptStatus.SUBMITTED
        )
        db_session.add(att)
        await db_session.flush()

        res = AssessmentResult(
            result_attempt_id=att.attempt_id,
            result_assessment_id=a.assessment_id,
            result_student_id=u.user_id,
            result_obtained_marks=Decimal("15.00"),
            result_total_marks=Decimal("30.00"),
            result_percentage=Decimal("50.00"),
            result_status=ResultStatus.COMPLETED
        )
        db_session.add(res)
        await db_session.flush()

        # q_easy: all awarded 5.00
        rq_easy = AssessmentResultQuestion(
            result_question_result_id=res.result_id,
            result_question_assessment_question_id=q_easy.assessment_question_id,
            result_question_marks_awarded=Decimal("5.00"),
            result_question_marks_available=Decimal("5.00"),
            result_question_correctness=CorrectnessStatus.CORRECT,
            result_question_grading_status=GradingStatus.GRADED
        )
        
        # q_mod: first 3 get 5.00, last 2 get 0.00 (avg 3.0/5 = 60%)
        mod_marks = Decimal("5.00") if i < 3 else Decimal("0.00")
        rq_mod = AssessmentResultQuestion(
            result_question_result_id=res.result_id,
            result_question_assessment_question_id=q_mod.assessment_question_id,
            result_question_marks_awarded=mod_marks,
            result_question_marks_available=Decimal("5.00"),
            result_question_correctness=CorrectnessStatus.CORRECT if i < 3 else CorrectnessStatus.INCORRECT,
            result_question_grading_status=GradingStatus.GRADED
        )

        # q_hard: only 1 gets 5.00, 4 get 0.00 (avg 1.0/5 = 20%)
        hard_marks = Decimal("5.00") if i == 0 else Decimal("0.00")
        rq_hard = AssessmentResultQuestion(
            result_question_result_id=res.result_id,
            result_question_assessment_question_id=q_hard.assessment_question_id,
            result_question_marks_awarded=hard_marks,
            result_question_marks_available=Decimal("5.00"),
            result_question_correctness=CorrectnessStatus.CORRECT if i == 0 else CorrectnessStatus.INCORRECT,
            result_question_grading_status=GradingStatus.GRADED
        )

        db_session.add_all([rq_easy, rq_mod, rq_hard])

        # q_small: only add for first 2 students
        if i < 2:
            rq_small = AssessmentResultQuestion(
                result_question_result_id=res.result_id,
                result_question_assessment_question_id=q_small.assessment_question_id,
                result_question_marks_awarded=Decimal("5.00"),
                result_question_marks_available=Decimal("5.00"),
                result_question_correctness=CorrectnessStatus.CORRECT,
                result_question_grading_status=GradingStatus.GRADED
            )
            db_session.add(rq_small)

        await db_session.flush()

    diff_res = await service.get_subject_question_difficulty_analytics(
        org_id=org.organization_id,
        subject_id=subj1.subject_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False
    )

    assert diff_res.total_questions_analyzed == 4
    
    easy_item = next(q for q in diff_res.questions if q.question_id == q_easy.assessment_question_id)
    assert easy_item.evaluated_count == 5
    assert easy_item.accuracy_percentage == 100.0
    assert easy_item.difficulty_band == ObservedDifficultyBand.EASIER_OBSERVED

    mod_item = next(q for q in diff_res.questions if q.question_id == q_mod.assessment_question_id)
    assert mod_item.evaluated_count == 5
    assert mod_item.accuracy_percentage == 60.0
    assert mod_item.difficulty_band == ObservedDifficultyBand.MODERATE_OBSERVED

    hard_item = next(q for q in diff_res.questions if q.question_id == q_hard.assessment_question_id)
    assert hard_item.evaluated_count == 5
    assert hard_item.accuracy_percentage == 20.0
    assert hard_item.difficulty_band == ObservedDifficultyBand.HARDER_OBSERVED

    small_item = next(q for q in diff_res.questions if q.question_id == q_small.assessment_question_id)
    assert small_item.evaluated_count == 2
    assert small_item.difficulty_band == ObservedDifficultyBand.INSUFFICIENT_SAMPLE

    # Distribution check
    assert diff_res.easier_count == 1
    assert diff_res.moderate_count == 1
    assert diff_res.harder_count == 1
    assert diff_res.insufficient_sample_count == 1


@pytest.mark.asyncio
async def test_subject_learning_analytics(db_session):
    teacher, _, student1, _, org, _, subj1, _ = await setup_learning_analytics_env(db_session)
    service = AssessmentService(db_session)

    subj_analytics = await service.get_subject_learning_analytics(
        org_id=org.organization_id,
        subject_id=subj1.subject_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False
    )

    assert subj_analytics.subject_id == subj1.subject_id
    assert subj_analytics.subject_name == "Mathematics 101"
    assert isinstance(subj_analytics.assessment_trends, list)

