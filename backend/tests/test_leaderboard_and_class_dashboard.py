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
    AssessmentCreateRequest,
    AssessmentLeaderboardSettingsUpdateRequest
)
from app.core.exceptions import (
    NotFoundException,
    ForbiddenException
)


async def setup_dashboard_leaderboard_env(db_session):
    teacher = User(user_email=f"prof_{uuid.uuid4().hex[:6]}@test.com", user_password_hash="hash", user_first_name="Prof", user_last_name="Leader")
    unassigned_teacher = User(user_email=f"unassigned_{uuid.uuid4().hex[:6]}@test.com", user_password_hash="hash", user_first_name="Other", user_last_name="Teacher")
    student1 = User(user_email=f"alice_{uuid.uuid4().hex[:6]}@test.com", user_password_hash="hash", user_first_name="Alice", user_last_name="Smith")
    student2 = User(user_email=f"bob_{uuid.uuid4().hex[:6]}@test.com", user_password_hash="hash", user_first_name="Bob", user_last_name="Jones")
    student3 = User(user_email=f"charlie_{uuid.uuid4().hex[:6]}@test.com", user_password_hash="hash", user_first_name="Charlie", user_last_name="Brown")
    student4 = User(user_email=f"david_{uuid.uuid4().hex[:6]}@test.com", user_password_hash="hash", user_first_name="David", user_last_name="Miller")
    
    db_session.add_all([teacher, unassigned_teacher, student1, student2, student3, student4])
    await db_session.flush()

    roles_res = await db_session.execute(select(Role).where(Role.role_is_system == True))
    roles_by_name = {r.role_name: r.role_id for r in roles_res.scalars().all()}

    org = Organization(organization_name="Leaderboard Academy", organization_slug=f"leader-acad-{uuid.uuid4().hex[:6]}", organization_owner_user_id=teacher.user_id)
    db_session.add(org)
    await db_session.flush()

    ws = Workspace(workspace_organization_id=org.organization_id, workspace_name="Leaderboard Workspace", workspace_created_by=teacher.user_id)
    db_session.add(ws)
    await db_session.flush()

    subj = Subject(subject_workspace_id=ws.workspace_id, subject_name="Competitive Math")
    db_session.add(subj)
    await db_session.flush()

    st = SubjectTeacher(subject_teacher_subject_id=subj.subject_id, subject_teacher_user_id=teacher.user_id)
    wm_teacher = WorkspaceMember(workspace_member_workspace_id=ws.workspace_id, workspace_member_user_id=teacher.user_id, workspace_member_role_id=roles_by_name["Teacher"])
    wm_unassigned = WorkspaceMember(workspace_member_workspace_id=ws.workspace_id, workspace_member_user_id=unassigned_teacher.user_id, workspace_member_role_id=roles_by_name["Teacher"])
    wm_s1 = WorkspaceMember(workspace_member_workspace_id=ws.workspace_id, workspace_member_user_id=student1.user_id, workspace_member_role_id=roles_by_name["Student"])
    wm_s2 = WorkspaceMember(workspace_member_workspace_id=ws.workspace_id, workspace_member_user_id=student2.user_id, workspace_member_role_id=roles_by_name["Student"])
    wm_s3 = WorkspaceMember(workspace_member_workspace_id=ws.workspace_id, workspace_member_user_id=student3.user_id, workspace_member_role_id=roles_by_name["Student"])
    wm_s4 = WorkspaceMember(workspace_member_workspace_id=ws.workspace_id, workspace_member_user_id=student4.user_id, workspace_member_role_id=roles_by_name["Student"])
    
    db_session.add_all([st, wm_teacher, wm_unassigned, wm_s1, wm_s2, wm_s3, wm_s4])
    await db_session.flush()

    return teacher, unassigned_teacher, student1, student2, student3, student4, org, ws, subj


@pytest.mark.asyncio
async def test_leaderboard_disabled_by_default(db_session):
    teacher, _, student1, _, _, _, org, _, subj = await setup_dashboard_leaderboard_env(db_session)
    service = AssessmentService(db_session)

    # 1. Create assessment without specifying leaderboard_enabled -> must be False
    create_req = AssessmentCreateRequest(
        subject_id=subj.subject_id,
        title="Math Quiz 1",
        type=AssessmentType.QUIZ,
        total_marks=Decimal("100.00"),
        passing_marks=Decimal("50.00")
    )
    asm_resp = await service.create_assessment(org.organization_id, teacher.user_id, False, create_req)
    assert asm_resp.assessment_leaderboard_enabled is False

    # 2. Query leaderboard as student -> should return disabled with 0 entries
    lb_resp = await service.get_assessment_leaderboard(
        org_id=org.organization_id,
        assessment_id=asm_resp.assessment_id,
        requesting_user_id=student1.user_id,
        is_org_admin=False
    )
    assert lb_resp.leaderboard_enabled is False
    assert lb_resp.total_ranked_students == 0
    assert len(lb_resp.entries) == 0
    assert lb_resp.my_rank is None


@pytest.mark.asyncio
async def test_leaderboard_teacher_toggle_rbac(db_session):
    teacher, unassigned_teacher, student1, _, _, _, org, _, subj = await setup_dashboard_leaderboard_env(db_session)
    service = AssessmentService(db_session)

    asm = Assessment(
        assessment_subject_id=subj.subject_id,
        assessment_title="Championship Exam",
        assessment_type=AssessmentType.EXAM,
        assessment_status=AssessmentStatus.PUBLISHED,
        assessment_total_marks=Decimal("100.00"),
        assessment_passing_marks=Decimal("50.00"),
        assessment_leaderboard_enabled=False
    )
    db_session.add(asm)
    await db_session.flush()

    # Student cannot toggle leaderboard
    with pytest.raises(ForbiddenException):
        await service.update_assessment_leaderboard_settings(
            org_id=org.organization_id,
            assessment_id=asm.assessment_id,
            requesting_user_id=student1.user_id,
            is_org_admin=False,
            payload=AssessmentLeaderboardSettingsUpdateRequest(enabled=True)
        )

    # Unassigned teacher cannot toggle leaderboard
    with pytest.raises(ForbiddenException):
        await service.update_assessment_leaderboard_settings(
            org_id=org.organization_id,
            assessment_id=asm.assessment_id,
            requesting_user_id=unassigned_teacher.user_id,
            is_org_admin=False,
            payload=AssessmentLeaderboardSettingsUpdateRequest(enabled=True)
        )

    # Assigned teacher can enable leaderboard
    updated = await service.update_assessment_leaderboard_settings(
        org_id=org.organization_id,
        assessment_id=asm.assessment_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False,
        payload=AssessmentLeaderboardSettingsUpdateRequest(enabled=True)
    )
    assert updated.leaderboard_enabled is True


@pytest.mark.asyncio
async def test_leaderboard_ranking_deterministic_and_tie_breaking(db_session):
    """
    Test deterministic competition ranking ("1-2-2-4"):
    Student 1 (Alice): 95% (completed at t0) -> Rank 1
    Student 2 (Bob): 85% (completed at t1) -> Rank 2
    Student 3 (Charlie): 85% (completed at t1) -> Rank 2 (Tie with Bob)
    Student 4 (David): 70% (completed at t3) -> Rank 4 (Competition ranking skips 3)
    """
    teacher, _, s1, s2, s3, s4, org, _, subj = await setup_dashboard_leaderboard_env(db_session)
    service = AssessmentService(db_session)

    asm = Assessment(
        assessment_subject_id=subj.subject_id,
        assessment_title="Math Olympiad",
        assessment_type=AssessmentType.EXAM,
        assessment_status=AssessmentStatus.PUBLISHED,
        assessment_total_marks=Decimal("100.00"),
        assessment_passing_marks=Decimal("50.00"),
        assessment_leaderboard_enabled=True
    )
    db_session.add(asm)
    await db_session.flush()

    base_time = datetime(2026, 9, 22, 10, 0, 0, tzinfo=timezone.utc)
    t0 = base_time
    t1 = base_time + timedelta(minutes=10)
    t3 = base_time + timedelta(minutes=30)

    # Attempts & Results
    # S1: 95%
    att1 = AssessmentAttempt(attempt_assessment_id=asm.assessment_id, attempt_student_id=s1.user_id, attempt_status=AttemptStatus.SUBMITTED, attempt_number=1)
    db_session.add(att1)
    await db_session.flush()
    r1 = AssessmentResult(result_attempt_id=att1.attempt_id, result_assessment_id=asm.assessment_id, result_student_id=s1.user_id, result_total_marks=Decimal("100.00"), result_obtained_marks=Decimal("95.00"), result_percentage=Decimal("95.00"), result_passed=True, result_status=ResultStatus.COMPLETED, result_graded_at=t0)

    # S2: 85% (at t1)
    att2 = AssessmentAttempt(attempt_assessment_id=asm.assessment_id, attempt_student_id=s2.user_id, attempt_status=AttemptStatus.SUBMITTED, attempt_number=1)
    db_session.add(att2)
    await db_session.flush()
    r2 = AssessmentResult(result_attempt_id=att2.attempt_id, result_assessment_id=asm.assessment_id, result_student_id=s2.user_id, result_total_marks=Decimal("100.00"), result_obtained_marks=Decimal("85.00"), result_percentage=Decimal("85.00"), result_passed=True, result_status=ResultStatus.COMPLETED, result_graded_at=t1)

    # S3: 85% (at t1 - identical score and timestamp)
    att3 = AssessmentAttempt(attempt_assessment_id=asm.assessment_id, attempt_student_id=s3.user_id, attempt_status=AttemptStatus.SUBMITTED, attempt_number=1)
    db_session.add(att3)
    await db_session.flush()
    r3 = AssessmentResult(result_attempt_id=att3.attempt_id, result_assessment_id=asm.assessment_id, result_student_id=s3.user_id, result_total_marks=Decimal("100.00"), result_obtained_marks=Decimal("85.00"), result_percentage=Decimal("85.00"), result_passed=True, result_status=ResultStatus.COMPLETED, result_graded_at=t1)

    # S4: 70% (at t3)
    att4 = AssessmentAttempt(attempt_assessment_id=asm.assessment_id, attempt_student_id=s4.user_id, attempt_status=AttemptStatus.SUBMITTED, attempt_number=1)
    db_session.add(att4)
    await db_session.flush()
    r4 = AssessmentResult(result_attempt_id=att4.attempt_id, result_assessment_id=asm.assessment_id, result_student_id=s4.user_id, result_total_marks=Decimal("100.00"), result_obtained_marks=Decimal("70.00"), result_percentage=Decimal("70.00"), result_passed=True, result_status=ResultStatus.COMPLETED, result_graded_at=t3)

    db_session.add_all([r1, r2, r3, r4])
    await db_session.flush()

    # Query leaderboard as s4 (David)
    lb = await service.get_assessment_leaderboard(
        org_id=org.organization_id,
        assessment_id=asm.assessment_id,
        requesting_user_id=s4.user_id,
        is_org_admin=False
    )

    assert lb.total_ranked_students == 4
    assert len(lb.entries) == 4
    assert lb.my_rank == 4
    assert lb.my_entry.rank == 4
    assert lb.my_entry.percentage == 70.0

    # Ranks must be 1, 2, 2, 4
    ranks = [e.rank for e in lb.entries]
    assert ranks == [1, 2, 2, 4]
    assert lb.entries[0].student.display_name == "Alice S."  # sanitized peer name for s4
    assert lb.entries[3].student.display_name == "David Miller"  # current user's own display name


@pytest.mark.asyncio
async def test_leaderboard_multiple_attempts_best_score_selected(db_session):
    """
    Test multiple attempts rule:
    Student A has Attempt 1 (60%), Attempt 2 (90%), Attempt 3 (75%).
    Leaderboard must only rank the student once with their best score (90%) and attempts_used=3.
    """
    teacher, _, s1, _, _, _, org, _, subj = await setup_dashboard_leaderboard_env(db_session)
    service = AssessmentService(db_session)

    asm = Assessment(
        assessment_subject_id=subj.subject_id,
        assessment_title="Multi-Attempt Quiz",
        assessment_type=AssessmentType.QUIZ,
        assessment_status=AssessmentStatus.PUBLISHED,
        assessment_attempt_limit=3,
        assessment_total_marks=Decimal("100.00"),
        assessment_passing_marks=Decimal("50.00"),
        assessment_leaderboard_enabled=True
    )
    db_session.add(asm)
    await db_session.flush()

    # Attempt 1: 60%
    att1 = AssessmentAttempt(attempt_assessment_id=asm.assessment_id, attempt_student_id=s1.user_id, attempt_status=AttemptStatus.SUBMITTED, attempt_number=1)
    db_session.add(att1)
    await db_session.flush()
    r1 = AssessmentResult(result_attempt_id=att1.attempt_id, result_assessment_id=asm.assessment_id, result_student_id=s1.user_id, result_total_marks=Decimal("100.00"), result_obtained_marks=Decimal("60.00"), result_percentage=Decimal("60.00"), result_passed=True, result_status=ResultStatus.COMPLETED, result_graded_at=datetime.now(timezone.utc))

    # Attempt 2: 90% (Best)
    att2 = AssessmentAttempt(attempt_assessment_id=asm.assessment_id, attempt_student_id=s1.user_id, attempt_status=AttemptStatus.SUBMITTED, attempt_number=2)
    db_session.add(att2)
    await db_session.flush()
    r2 = AssessmentResult(result_attempt_id=att2.attempt_id, result_assessment_id=asm.assessment_id, result_student_id=s1.user_id, result_total_marks=Decimal("100.00"), result_obtained_marks=Decimal("90.00"), result_percentage=Decimal("90.00"), result_passed=True, result_status=ResultStatus.COMPLETED, result_graded_at=datetime.now(timezone.utc))

    # Attempt 3: 75%
    att3 = AssessmentAttempt(attempt_assessment_id=asm.assessment_id, attempt_student_id=s1.user_id, attempt_status=AttemptStatus.SUBMITTED, attempt_number=3)
    db_session.add(att3)
    await db_session.flush()
    r3 = AssessmentResult(result_attempt_id=att3.attempt_id, result_assessment_id=asm.assessment_id, result_student_id=s1.user_id, result_total_marks=Decimal("100.00"), result_obtained_marks=Decimal("75.00"), result_percentage=Decimal("75.00"), result_passed=True, result_status=ResultStatus.COMPLETED, result_graded_at=datetime.now(timezone.utc))

    db_session.add_all([r1, r2, r3])
    await db_session.flush()

    lb = await service.get_assessment_leaderboard(
        org_id=org.organization_id,
        assessment_id=asm.assessment_id,
        requesting_user_id=s1.user_id,
        is_org_admin=False
    )

    assert lb.total_ranked_students == 1
    assert len(lb.entries) == 1
    entry = lb.entries[0]
    assert entry.percentage == 90.0
    assert entry.obtained_marks == 90.0
    assert entry.attempts_used == 3
    assert entry.rank == 1


@pytest.mark.asyncio
async def test_leaderboard_pending_manual_grading_exclusion(db_session):
    """
    Students with PENDING_MANUAL_GRADING results are excluded from the leaderboard until finalized.
    """
    teacher, _, s1, s2, _, _, org, _, subj = await setup_dashboard_leaderboard_env(db_session)
    service = AssessmentService(db_session)

    asm = Assessment(
        assessment_subject_id=subj.subject_id,
        assessment_title="Essay Exam",
        assessment_type=AssessmentType.EXAM,
        assessment_status=AssessmentStatus.PUBLISHED,
        assessment_total_marks=Decimal("100.00"),
        assessment_passing_marks=Decimal("50.00"),
        assessment_leaderboard_enabled=True
    )
    db_session.add(asm)
    await db_session.flush()

    # S1 completed: 80%
    att1 = AssessmentAttempt(attempt_assessment_id=asm.assessment_id, attempt_student_id=s1.user_id, attempt_status=AttemptStatus.SUBMITTED, attempt_number=1)
    db_session.add(att1)
    await db_session.flush()
    r1 = AssessmentResult(result_attempt_id=att1.attempt_id, result_assessment_id=asm.assessment_id, result_student_id=s1.user_id, result_total_marks=Decimal("100.00"), result_obtained_marks=Decimal("80.00"), result_percentage=Decimal("80.00"), result_passed=True, result_status=ResultStatus.COMPLETED)

    # S2 pending manual grading
    att2 = AssessmentAttempt(attempt_assessment_id=asm.assessment_id, attempt_student_id=s2.user_id, attempt_status=AttemptStatus.SUBMITTED, attempt_number=1)
    db_session.add(att2)
    await db_session.flush()
    r2 = AssessmentResult(result_attempt_id=att2.attempt_id, result_assessment_id=asm.assessment_id, result_student_id=s2.user_id, result_total_marks=Decimal("100.00"), result_obtained_marks=Decimal("40.00"), result_percentage=Decimal("40.00"), result_passed=False, result_status=ResultStatus.PENDING_MANUAL_GRADING, result_pending_count=1)

    db_session.add_all([r1, r2])
    await db_session.flush()

    # Initial leaderboard -> S2 is excluded
    lb1 = await service.get_assessment_leaderboard(org.organization_id, asm.assessment_id, teacher.user_id, False)
    assert lb1.total_ranked_students == 1
    assert lb1.entries[0].student.id == s1.user_id

    # Now teacher completes manual grading for S2 -> 95%
    r2.result_status = ResultStatus.COMPLETED
    r2.result_obtained_marks = Decimal("95.00")
    r2.result_percentage = Decimal("95.00")
    r2.result_passed = True
    r2.result_pending_count = 0
    r2.result_graded_at = datetime.now(timezone.utc)
    db_session.add(r2)
    await db_session.flush()

    # Updated leaderboard -> S2 is now ranked #1
    lb2 = await service.get_assessment_leaderboard(org.organization_id, asm.assessment_id, teacher.user_id, False)
    assert lb2.total_ranked_students == 2
    assert lb2.entries[0].student.id == s2.user_id
    assert lb2.entries[0].rank == 1
    assert lb2.entries[1].student.id == s1.user_id
    assert lb2.entries[1].rank == 2


@pytest.mark.asyncio
async def test_class_performance_dashboard_aggregation(db_session):
    """
    Test consolidated Class Performance Dashboard:
    Aggregates class average, median, pass rate, participation rate, timeline trend, and student roster.
    """
    teacher, unassigned_teacher, s1, s2, s3, s4, org, ws, subj = await setup_dashboard_leaderboard_env(db_session)
    service = AssessmentService(db_session)

    # 1. Access control: Unassigned teacher cannot access dashboard
    with pytest.raises(ForbiddenException):
        await service.get_class_performance_dashboard(
            org_id=org.organization_id,
            subject_id=subj.subject_id,
            requesting_user_id=unassigned_teacher.user_id,
            is_org_admin=False
        )

    # 2. Setup assessments and results
    asm1 = Assessment(assessment_subject_id=subj.subject_id, assessment_title="Midterm", assessment_type=AssessmentType.EXAM, assessment_status=AssessmentStatus.PUBLISHED, assessment_total_marks=Decimal("100.00"), assessment_passing_marks=Decimal("50.00"))
    asm2 = Assessment(assessment_subject_id=subj.subject_id, assessment_title="Final", assessment_type=AssessmentType.EXAM, assessment_status=AssessmentStatus.PUBLISHED, assessment_total_marks=Decimal("100.00"), assessment_passing_marks=Decimal("50.00"))
    db_session.add_all([asm1, asm2])
    await db_session.flush()

    # S1: Midterm = 90% (Pass), Final = 80% (Pass)
    att1 = AssessmentAttempt(attempt_assessment_id=asm1.assessment_id, attempt_student_id=s1.user_id, attempt_status=AttemptStatus.SUBMITTED, attempt_number=1)
    att2 = AssessmentAttempt(attempt_assessment_id=asm2.assessment_id, attempt_student_id=s1.user_id, attempt_status=AttemptStatus.SUBMITTED, attempt_number=1)
    db_session.add_all([att1, att2])
    await db_session.flush()
    r1 = AssessmentResult(result_attempt_id=att1.attempt_id, result_assessment_id=asm1.assessment_id, result_student_id=s1.user_id, result_total_marks=Decimal("100.00"), result_obtained_marks=Decimal("90.00"), result_percentage=Decimal("90.00"), result_passed=True, result_status=ResultStatus.COMPLETED)
    r2 = AssessmentResult(result_attempt_id=att2.attempt_id, result_assessment_id=asm2.assessment_id, result_student_id=s1.user_id, result_total_marks=Decimal("100.00"), result_obtained_marks=Decimal("80.00"), result_percentage=Decimal("80.00"), result_passed=True, result_status=ResultStatus.COMPLETED)

    # S2: Midterm = 40% (Fail)
    att3 = AssessmentAttempt(attempt_assessment_id=asm1.assessment_id, attempt_student_id=s2.user_id, attempt_status=AttemptStatus.SUBMITTED, attempt_number=1)
    db_session.add(att3)
    await db_session.flush()
    r3 = AssessmentResult(result_attempt_id=att3.attempt_id, result_assessment_id=asm1.assessment_id, result_student_id=s2.user_id, result_total_marks=Decimal("100.00"), result_obtained_marks=Decimal("40.00"), result_percentage=Decimal("40.00"), result_passed=False, result_status=ResultStatus.COMPLETED)

    # S3: Final = Pending grading
    att4 = AssessmentAttempt(attempt_assessment_id=asm2.assessment_id, attempt_student_id=s3.user_id, attempt_status=AttemptStatus.SUBMITTED, attempt_number=1)
    db_session.add(att4)
    await db_session.flush()
    r4 = AssessmentResult(result_attempt_id=att4.attempt_id, result_assessment_id=asm2.assessment_id, result_student_id=s3.user_id, result_total_marks=Decimal("100.00"), result_obtained_marks=Decimal("50.00"), result_percentage=Decimal("50.00"), result_passed=True, result_status=ResultStatus.PENDING_MANUAL_GRADING, result_pending_count=1)

    db_session.add_all([r1, r2, r3, r4])
    await db_session.flush()

    # Query Dashboard
    dash = await service.get_class_performance_dashboard(
        org_id=org.organization_id,
        subject_id=subj.subject_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False
    )

    assert dash.total_students == 4  # s1, s2, s3, s4
    assert dash.participating_students == 3  # s1, s2, s3 attempted; s4 did not
    assert dash.participation_rate_percentage == 75.0
    assert dash.total_assessments == 2
    assert dash.completed_evaluations == 3  # r1, r2, r3 completed
    assert dash.total_pending_manual_grading == 1  # r4 pending

    # Completed scores: [40.0, 80.0, 90.0] -> avg = (40+80+90)/3 = 70.0, median = 80.0
    assert dash.class_average_percentage == 70.0
    assert dash.class_median_percentage == 80.0
    # Passed: 2 out of 3 -> 66.67%
    assert dash.class_pass_rate_percentage == 66.67

    # Student roster
    assert len(dash.student_roster) == 4
    s1_row = next(r for r in dash.student_roster if r.student_id == s1.user_id)
    assert s1_row.assessments_completed == 2
    assert s1_row.average_percentage == 85.0
    assert s1_row.status_label == "Passing"

    s2_row = next(r for r in dash.student_roster if r.student_id == s2.user_id)
    assert s2_row.assessments_completed == 1
    assert s2_row.average_percentage == 40.0
    assert s2_row.status_label == "Below Passing Threshold"

    s3_row = next(r for r in dash.student_roster if r.student_id == s3.user_id)
    assert s3_row.pending_grading_count == 1
    assert s3_row.status_label == "Pending Review"

    s4_row = next(r for r in dash.student_roster if r.student_id == s4.user_id)
    assert s4_row.assessments_completed == 0
    assert s4_row.status_label == "No Submissions"
