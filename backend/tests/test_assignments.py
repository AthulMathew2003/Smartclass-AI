import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User
from app.modules.organizations.models import Organization, Workspace
from app.modules.subjects.models import Subject, SubjectStatus
from app.modules.assignments.models import (
    Assignment,
    AssignmentSubmission,
    AssignmentStatus,
    SubmissionStatus,
)


@pytest.mark.asyncio
async def test_assignment_model_and_subject_cascade(db_session: AsyncSession):
    # 1. Create User, Organization, Workspace, and Subject step by step
    creator = User(
        user_id=uuid.uuid4(),
        user_email="teacher_creator@example.com",
        user_password_hash="fakehash",
        user_first_name="Jane",
        user_last_name="Doe",
    )
    db_session.add(creator)
    await db_session.flush()

    org = Organization(
        organization_id=uuid.uuid4(),
        organization_name="Test Academy",
        organization_slug="test-academy",
        organization_owner_user_id=creator.user_id,
    )
    db_session.add(org)
    await db_session.flush()

    workspace = Workspace(
        workspace_id=uuid.uuid4(),
        workspace_organization_id=org.organization_id,
        workspace_name="Grade 10",
        workspace_created_by=creator.user_id,
    )
    db_session.add(workspace)
    await db_session.flush()

    subject = Subject(
        subject_id=uuid.uuid4(),
        subject_workspace_id=workspace.workspace_id,
        subject_name="Physics",
        subject_created_by=creator.user_id,
    )
    db_session.add(subject)
    await db_session.flush()

    # 2. Create Assignment
    due_date = datetime.now(timezone.utc)
    assignment = Assignment(
        assignment_id=uuid.uuid4(),
        assignment_subject_id=subject.subject_id,
        assignment_title="Newton's Laws Lab",
        assignment_description="Complete the simulation lab report.",
        assignment_status=AssignmentStatus.DRAFT,
        assignment_due_at=due_date,
        assignment_created_by=creator.user_id,
    )
    db_session.add(assignment)
    await db_session.flush()

    # Verify assignment created and relationships populated
    fetched_a = await db_session.get(Assignment, assignment.assignment_id)
    assert fetched_a is not None
    assert fetched_a.assignment_title == "Newton's Laws Lab"
    assert fetched_a.assignment_status == AssignmentStatus.DRAFT
    assert fetched_a.subject.subject_name == "Physics"
    assert fetched_a.creator.user_email == "teacher_creator@example.com"

    # 3. Verify Subject Deletion Cascades to Assignments
    await db_session.delete(subject)
    await db_session.flush()

    cascaded_a = await db_session.get(Assignment, assignment.assignment_id)
    assert cascaded_a is None


@pytest.mark.asyncio
async def test_submission_model_and_unique_constraint(db_session: AsyncSession):
    # 1. Setup Base Records
    teacher = User(
        user_id=uuid.uuid4(),
        user_email="grader@example.com",
        user_password_hash="fakehash",
        user_first_name="Prof",
        user_last_name="X",
    )
    student = User(
        user_id=uuid.uuid4(),
        user_email="student@example.com",
        user_password_hash="fakehash",
        user_first_name="Peter",
        user_last_name="Parker",
    )
    db_session.add_all([teacher, student])
    await db_session.flush()

    org = Organization(
        organization_id=uuid.uuid4(),
        organization_name="Hero High",
        organization_slug="hero-high",
        organization_owner_user_id=teacher.user_id,
    )
    db_session.add(org)
    await db_session.flush()

    workspace = Workspace(
        workspace_id=uuid.uuid4(),
        workspace_organization_id=org.organization_id,
        workspace_name="Cohort A",
        workspace_created_by=teacher.user_id,
    )
    db_session.add(workspace)
    await db_session.flush()

    subject = Subject(
        subject_id=uuid.uuid4(),
        subject_workspace_id=workspace.workspace_id,
        subject_name="Chemistry",
        subject_created_by=teacher.user_id,
    )
    db_session.add(subject)
    await db_session.flush()

    assignment = Assignment(
        assignment_id=uuid.uuid4(),
        assignment_subject_id=subject.subject_id,
        assignment_title="Chemical Bonding",
        assignment_status=AssignmentStatus.PUBLISHED,
        assignment_created_by=teacher.user_id,
    )
    db_session.add(assignment)
    await db_session.flush()

    # 2. Create Submission
    submission = AssignmentSubmission(
        submission_id=uuid.uuid4(),
        submission_assignment_id=assignment.assignment_id,
        submission_student_id=student.user_id,
        submission_status=SubmissionStatus.SUBMITTED,
        submission_submitted_at=datetime.now(timezone.utc),
        submission_grade=95.50,
        submission_feedback="Excellent analysis.",
        submission_graded_by=teacher.user_id,
        submission_graded_at=datetime.now(timezone.utc),
    )
    db_session.add(submission)
    await db_session.flush()

    fetched_s = await db_session.get(AssignmentSubmission, submission.submission_id)
    assert fetched_s is not None
    assert fetched_s.submission_grade == 95.50
    assert fetched_s.student.user_email == "student@example.com"
    assert fetched_s.grader.user_email == "grader@example.com"
    assert fetched_s.assignment.assignment_title == "Chemical Bonding"

    # 3. Test Unique Constraint on (submission_assignment_id, submission_student_id)
    dup_submission = AssignmentSubmission(
        submission_id=uuid.uuid4(),
        submission_assignment_id=assignment.assignment_id,
        submission_student_id=student.user_id,
        submission_status=SubmissionStatus.DRAFT,
    )
    db_session.add(dup_submission)
    with pytest.raises(IntegrityError):
        await db_session.flush()

    await db_session.rollback()


@pytest.mark.asyncio
async def test_cascades_and_foreign_key_set_null(db_session: AsyncSession):
    # 1. Setup Base Records
    org_owner = User(
        user_id=uuid.uuid4(),
        user_email="org_owner@example.com",
        user_password_hash="fakehash",
    )
    author = User(
        user_id=uuid.uuid4(),
        user_email="author@example.com",
        user_password_hash="fakehash",
    )
    grader = User(
        user_id=uuid.uuid4(),
        user_email="evaluator@example.com",
        user_password_hash="fakehash",
    )
    student = User(
        user_id=uuid.uuid4(),
        user_email="scholar@example.com",
        user_password_hash="fakehash",
    )
    db_session.add_all([org_owner, author, grader, student])
    await db_session.flush()

    org = Organization(
        organization_id=uuid.uuid4(),
        organization_name="Cascade College",
        organization_slug="cascade-college",
        organization_owner_user_id=org_owner.user_id,
    )
    db_session.add(org)
    await db_session.flush()

    workspace = Workspace(
        workspace_id=uuid.uuid4(),
        workspace_organization_id=org.organization_id,
        workspace_name="Hall B",
        workspace_created_by=org_owner.user_id,
    )
    db_session.add(workspace)
    await db_session.flush()

    subject = Subject(
        subject_id=uuid.uuid4(),
        subject_workspace_id=workspace.workspace_id,
        subject_name="Biology",
        subject_created_by=org_owner.user_id,
    )
    db_session.add(subject)
    await db_session.flush()

    assignment = Assignment(
        assignment_id=uuid.uuid4(),
        assignment_subject_id=subject.subject_id,
        assignment_title="Genetics Quiz",
        assignment_created_by=author.user_id,
    )
    db_session.add(assignment)
    await db_session.flush()

    submission = AssignmentSubmission(
        submission_id=uuid.uuid4(),
        submission_assignment_id=assignment.assignment_id,
        submission_student_id=student.user_id,
        submission_graded_by=grader.user_id,
        submission_status=SubmissionStatus.GRADED,
    )
    db_session.add(submission)
    await db_session.flush()

    # 2. Test Author Deletion -> sets assignment_created_by to NULL
    await db_session.delete(author)
    await db_session.flush()
    await db_session.refresh(assignment)
    assert assignment.assignment_created_by is None

    # 3. Test Grader Deletion -> sets submission_graded_by to NULL
    await db_session.delete(grader)
    await db_session.flush()
    await db_session.refresh(submission)
    assert submission.submission_graded_by is None

    # 4. Test Student Deletion -> cascades and deletes submission
    sub_id = submission.submission_id
    assign_id = assignment.assignment_id
    await db_session.delete(student)
    await db_session.flush()
    db_session.expire_all()
    deleted_sub = await db_session.get(AssignmentSubmission, sub_id)
    assert deleted_sub is None

    # 5. Test Assignment Deletion -> cascades to submissions
    student2 = User(
        user_id=uuid.uuid4(),
        user_email="scholar2@example.com",
        user_password_hash="fakehash",
    )
    db_session.add(student2)
    await db_session.flush()

    sub2 = AssignmentSubmission(
        submission_id=uuid.uuid4(),
        submission_assignment_id=assign_id,
        submission_student_id=student2.user_id,
    )
    db_session.add(sub2)
    await db_session.flush()

    sub2_id = sub2.submission_id
    assignment_obj = await db_session.get(Assignment, assign_id)
    await db_session.delete(assignment_obj)
    await db_session.flush()
    db_session.expire_all()

    assert (await db_session.get(AssignmentSubmission, sub2_id)) is None
