import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.modules.users.service import UserService
from app.modules.organizations.models import Organization, WorkspaceStatus
from app.modules.organizations.repository import OrganizationRepository
from app.modules.organizations.workspace_schemas import WorkspaceCreateRequest
from app.modules.organizations.workspace_service import WorkspaceService
from app.modules.organizations.member_service import MemberService
from app.modules.organizations.member_schemas import MemberCreateRequest
from app.modules.rbac.constants import SystemRole

from app.modules.subjects.service import SubjectService
from app.modules.subjects.schemas import (
    SubjectCreateRequest,
    SubjectUpdateRequest,
    SubjectTeacherAddRequest
)
from app.modules.subjects.models import SubjectStatus, Subject
from app.core.exceptions import ConflictException, NotFoundException, ForbiddenException


@pytest.fixture
async def setup_org_and_users(db_session: AsyncSession):
    user_svc = UserService(db_session)
    # Create Owner, Teacher, Student
    owner = await user_svc.create_user(email="subj_owner@example.com", password="Password123!")
    teacher1 = await user_svc.create_user(email="subj_teacher1@example.com", password="Password123!")
    teacher2 = await user_svc.create_user(email="subj_teacher2@example.com", password="Password123!")
    student = await user_svc.create_user(email="subj_student@example.com", password="Password123!")
    non_member = await user_svc.create_user(email="subj_non_member@example.com", password="Password123!")
    await db_session.commit()

    # Create Org directly via Repo
    org_repo = OrganizationRepository(db_session)
    org = await org_repo.create_organization(
        name="Test Org",
        slug="test-org-subj",
        owner_user_id=owner.user_id
    )
    
    # Get system roles
    from app.modules.organizations.models import Role
    roles = (await db_session.execute(select(Role).where(Role.role_organization_id.is_(None)))).scalars().all()
    owner_role = next(r for r in roles if r.role_name == SystemRole.OWNER)
    teacher_role = next(r for r in roles if r.role_name == SystemRole.TEACHER)
    student_role = next(r for r in roles if r.role_name == SystemRole.STUDENT)

    # Add Org Members
    member_svc = MemberService(db_session)
    await member_svc.create_member(org.organization_id, MemberCreateRequest(
        email=owner.user_email, first_name="O", last_name="W", role_id=owner_role.role_id, workspace_ids=[]
    ))
    await member_svc.create_member(org.organization_id, MemberCreateRequest(
        email=teacher1.user_email, first_name="T", last_name="1", role_id=teacher_role.role_id, workspace_ids=[]
    ))
    await member_svc.create_member(org.organization_id, MemberCreateRequest(
        email=teacher2.user_email, first_name="T", last_name="2", role_id=teacher_role.role_id, workspace_ids=[]
    ))
    await member_svc.create_member(org.organization_id, MemberCreateRequest(
        email=student.user_email, first_name="S", last_name="1", role_id=student_role.role_id, workspace_ids=[]
    ))
    await member_svc.create_member(org.organization_id, MemberCreateRequest(
        email=non_member.user_email, first_name="O", last_name="1", role_id=student_role.role_id, workspace_ids=[]
    ))
    await db_session.commit()

    # Create Workspace
    ws_svc = WorkspaceService(db_session)
    ws = await ws_svc.create_workspace(
        org_id=org.organization_id,
        created_by_user_id=owner.user_id,
        payload=WorkspaceCreateRequest(workspace_name="Test Workspace")
    )
    
    # Add members to Workspace
    await org_repo.create_workspace_member(ws.workspace_id, teacher1.user_id, teacher_role.role_id)
    await org_repo.create_workspace_member(ws.workspace_id, teacher2.user_id, teacher_role.role_id)
    await org_repo.create_workspace_member(ws.workspace_id, student.user_id, student_role.role_id)
    await db_session.commit()

    return {
        "owner": owner,
        "teacher1": teacher1,
        "teacher2": teacher2,
        "student": student,
        "non_member": non_member,
        "org": org,
        "workspace": ws
    }


@pytest.mark.asyncio
async def test_subject_crud(db_session: AsyncSession, setup_org_and_users):
    """Test Subject CRUD operations and business rules."""
    data = setup_org_and_users
    subj_svc = SubjectService(db_session)
    org_id = data["org"].organization_id
    ws_id = data["workspace"].workspace_id
    owner = data["owner"]

    # ✓ create subject
    subj = await subj_svc.create_subject(
        org_id=org_id,
        workspace_id=ws_id,
        created_by_user_id=owner.user_id,
        payload=SubjectCreateRequest(workspace_id=ws_id, subject_name="Artificial Intelligence", subject_description="Intro to AI")
    )
    assert subj.subject_name == "Artificial Intelligence"
    assert subj.subject_status == SubjectStatus.ACTIVE

    # ✓ duplicate subject name rejected (case insensitive)
    with pytest.raises(ConflictException):
        await subj_svc.create_subject(
            org_id=org_id,
            workspace_id=ws_id,
            created_by_user_id=owner.user_id,
            payload=SubjectCreateRequest(workspace_id=ws_id, subject_name="artificial intelligence")
        )

    # ✓ update active subject
    updated = await subj_svc.update_subject(
        subject_id=subj.subject_id,
        org_id=org_id,
        workspace_id=ws_id,
        payload=SubjectUpdateRequest(subject_name="Advanced AI")
    )
    assert updated.subject_name == "Advanced AI"

    # ✓ archive subject
    archived = await subj_svc.archive_subject(
        subject_id=subj.subject_id,
        org_id=org_id,
        workspace_id=ws_id
    )
    assert archived.subject_status == SubjectStatus.ARCHIVED

    # ✓ archived subject remains in DB
    db_subj = (await db_session.execute(select(Subject).where(Subject.subject_id == subj.subject_id))).scalars().first()
    assert db_subj is not None
    assert db_subj.subject_status == SubjectStatus.ARCHIVED

    # ✓ archived subject cannot be updated
    with pytest.raises(ForbiddenException, match="Cannot update an archived subject."):
        await subj_svc.update_subject(
            subject_id=subj.subject_id,
            org_id=org_id,
            workspace_id=ws_id,
            payload=SubjectUpdateRequest(subject_name="Hacked Name")
        )

    # ✓ archived subject cannot receive teachers
    with pytest.raises(ForbiddenException, match="Cannot assign teachers to an archived subject."):
        await subj_svc.add_subject_teacher(
            subject_id=subj.subject_id,
            org_id=org_id,
            workspace_id=ws_id,
            payload=SubjectTeacherAddRequest(user_id=data["teacher1"].user_id)
        )

    # ✓ organization isolation: wrong org_id raises NotFoundException
    with pytest.raises(NotFoundException):
        await subj_svc.create_subject(
            org_id=uuid.uuid4(),
            workspace_id=ws_id,
            created_by_user_id=owner.user_id,
            payload=SubjectCreateRequest(workspace_id=ws_id, subject_name="Should Fail")
        )


@pytest.mark.asyncio
async def test_subject_workspace_visibility(db_session: AsyncSession, setup_org_and_users):
    """All workspace members automatically see all subjects — no per-subject enrollment."""
    data = setup_org_and_users
    subj_svc = SubjectService(db_session)
    org_id = data["org"].organization_id
    ws_id = data["workspace"].workspace_id
    owner = data["owner"]

    # Create 3 subjects
    for name in ["AI", "DBMS", "Machine Learning"]:
        await subj_svc.create_subject(
            org_id=org_id,
            workspace_id=ws_id,
            created_by_user_id=owner.user_id,
            payload=SubjectCreateRequest(workspace_id=ws_id, subject_name=name)
        )

    # ✓ Owner (admin) sees all 3
    admin_list = await subj_svc.list_accessible_subjects(
        user_id=owner.user_id,
        org_id=org_id,
        workspace_id=ws_id,
        is_org_admin=True
    )
    assert len(admin_list) == 3

    # ✓ Teacher sees all 3 (workspace member, no subject-level enrollment required)
    teacher_list = await subj_svc.list_accessible_subjects(
        user_id=data["teacher1"].user_id,
        org_id=org_id,
        workspace_id=ws_id,
        is_org_admin=False
    )
    assert len(teacher_list) == 3

    # ✓ Student sees all 3 (workspace member, automatic access)
    student_list = await subj_svc.list_accessible_subjects(
        user_id=data["student"].user_id,
        org_id=org_id,
        workspace_id=ws_id,
        is_org_admin=False
    )
    assert len(student_list) == 3

    # ✓ Non-workspace-member cannot access
    with pytest.raises(ForbiddenException, match="You are not a member of this workspace"):
        await subj_svc.list_accessible_subjects(
            user_id=data["non_member"].user_id,
            org_id=org_id,
            workspace_id=ws_id,
            is_org_admin=False
        )


@pytest.mark.asyncio
async def test_subject_teacher_assignment(db_session: AsyncSession, setup_org_and_users):
    """Test teacher assignment: validation, multiple teachers, duplicate rejection."""
    data = setup_org_and_users
    subj_svc = SubjectService(db_session)
    org_id = data["org"].organization_id
    ws_id = data["workspace"].workspace_id
    owner = data["owner"]

    subj = await subj_svc.create_subject(
        org_id=org_id,
        workspace_id=ws_id,
        created_by_user_id=owner.user_id,
        payload=SubjectCreateRequest(workspace_id=ws_id, subject_name="Web Development")
    )

    # ✓ Assign teacher1 (admin acting)
    t1_resp = await subj_svc.add_subject_teacher(
        subject_id=subj.subject_id,
        org_id=org_id,
        workspace_id=ws_id,
        payload=SubjectTeacherAddRequest(user_id=data["teacher1"].user_id),
        is_org_admin=True
    )
    assert t1_resp.subject_teacher_user_id == data["teacher1"].user_id

    # ✓ Assign teacher2 (multiple teachers)
    t2_resp = await subj_svc.add_subject_teacher(
        subject_id=subj.subject_id,
        org_id=org_id,
        workspace_id=ws_id,
        payload=SubjectTeacherAddRequest(user_id=data["teacher2"].user_id),
        is_org_admin=True
    )
    assert t2_resp.subject_teacher_user_id == data["teacher2"].user_id

    # ✓ List teachers shows 2
    teachers = await subj_svc.get_subject_teachers(
        subject_id=subj.subject_id,
        org_id=org_id,
        workspace_id=ws_id,
        is_org_admin=True
    )
    assert len(teachers) == 2

    # ✓ Duplicate teacher assignment rejected
    with pytest.raises(ConflictException, match="already assigned"):
        await subj_svc.add_subject_teacher(
            subject_id=subj.subject_id,
            org_id=org_id,
            workspace_id=ws_id,
            payload=SubjectTeacherAddRequest(user_id=data["teacher1"].user_id),
            is_org_admin=True
        )

    # ✓ Student cannot be assigned as teacher (no Teacher role in workspace)
    with pytest.raises(ForbiddenException, match="Teacher role"):
        await subj_svc.add_subject_teacher(
            subject_id=subj.subject_id,
            org_id=org_id,
            workspace_id=ws_id,
            payload=SubjectTeacherAddRequest(user_id=data["student"].user_id),
            is_org_admin=True
        )

    # ✓ Non-workspace-member cannot be assigned
    with pytest.raises(ForbiddenException, match="member of the workspace"):
        await subj_svc.add_subject_teacher(
            subject_id=subj.subject_id,
            org_id=org_id,
            workspace_id=ws_id,
            payload=SubjectTeacherAddRequest(user_id=data["non_member"].user_id),
            is_org_admin=True
        )

    # ✓ Remove teacher
    await subj_svc.remove_subject_teacher(
        subject_id=subj.subject_id,
        user_id=data["teacher1"].user_id,
        org_id=org_id,
        workspace_id=ws_id,
        is_org_admin=True
    )
    teachers_after = await subj_svc.get_subject_teachers(
        subject_id=subj.subject_id,
        org_id=org_id,
        workspace_id=ws_id,
        is_org_admin=True
    )
    assert len(teachers_after) == 1


@pytest.mark.asyncio
async def test_subject_archived_workspace_protection(db_session: AsyncSession, setup_org_and_users):
    """Archived workspace blocks subject creation, mutation, and teacher assignment."""
    data = setup_org_and_users
    subj_svc = SubjectService(db_session)
    org_id = data["org"].organization_id
    ws_id = data["workspace"].workspace_id
    owner = data["owner"]

    # Create subject before archiving workspace
    subj = await subj_svc.create_subject(
        org_id=org_id,
        workspace_id=ws_id,
        created_by_user_id=owner.user_id,
        payload=SubjectCreateRequest(workspace_id=ws_id, subject_name="Data Structures")
    )

    # Archive workspace
    from app.modules.organizations.workspace_schemas import WorkspaceUpdateRequest
    ws_svc = WorkspaceService(db_session)
    await ws_svc.update_workspace(ws_id, org_id, WorkspaceUpdateRequest(workspace_status=WorkspaceStatus.ARCHIVED))
    await db_session.commit()

    # ✓ Cannot create subject in archived workspace
    with pytest.raises(ForbiddenException, match="Cannot create a subject in an archived workspace."):
        await subj_svc.create_subject(
            org_id=org_id,
            workspace_id=ws_id,
            created_by_user_id=owner.user_id,
            payload=SubjectCreateRequest(workspace_id=ws_id, subject_name="Algorithms")
        )

    # ✓ Cannot assign teacher in archived workspace
    with pytest.raises(ForbiddenException, match="Cannot assign teachers in an archived workspace."):
        await subj_svc.add_subject_teacher(
            subject_id=subj.subject_id,
            org_id=org_id,
            workspace_id=ws_id,
            payload=SubjectTeacherAddRequest(user_id=data["teacher1"].user_id),
            is_org_admin=True
        )


@pytest.mark.asyncio
async def test_subject_teacher_update_authorization(db_session: AsyncSession, setup_org_and_users):
    """Only assigned teachers or admins can update a subject."""
    data = setup_org_and_users
    subj_svc = SubjectService(db_session)
    org_id = data["org"].organization_id
    ws_id = data["workspace"].workspace_id
    owner = data["owner"]

    subj = await subj_svc.create_subject(
        org_id=org_id,
        workspace_id=ws_id,
        created_by_user_id=owner.user_id,
        payload=SubjectCreateRequest(workspace_id=ws_id, subject_name="Operating Systems")
    )

    # Assign teacher1
    await subj_svc.add_subject_teacher(
        subject_id=subj.subject_id,
        org_id=org_id,
        workspace_id=ws_id,
        payload=SubjectTeacherAddRequest(user_id=data["teacher1"].user_id),
        is_org_admin=True
    )

    # ✓ Assigned teacher can update
    updated = await subj_svc.update_subject(
        subject_id=subj.subject_id,
        org_id=org_id,
        workspace_id=ws_id,
        payload=SubjectUpdateRequest(subject_name="Advanced OS"),
        requesting_user_id=data["teacher1"].user_id,
        is_org_admin=False
    )
    assert updated.subject_name == "Advanced OS"

    # ✓ Non-assigned teacher cannot update
    with pytest.raises(ForbiddenException, match="Only assigned teachers"):
        await subj_svc.update_subject(
            subject_id=subj.subject_id,
            org_id=org_id,
            workspace_id=ws_id,
            payload=SubjectUpdateRequest(subject_name="Hacked"),
            requesting_user_id=data["teacher2"].user_id,
            is_org_admin=False
        )


@pytest.mark.asyncio
async def test_subject_creator_deletion_sets_null(db_session: AsyncSession, setup_org_and_users):
    """When subject creator is deleted, subject_created_by should become NULL."""
    data = setup_org_and_users
    subj_svc = SubjectService(db_session)
    org_id = data["org"].organization_id
    ws_id = data["workspace"].workspace_id

    # Create a temporary user to be the creator
    user_svc = UserService(db_session)
    temp_user = await user_svc.create_user(email="subj_temp_creator@example.com", password="Password123!")
    await db_session.commit()

    # Add as org member and workspace member
    org_repo = OrganizationRepository(db_session)
    from app.modules.organizations.models import Role
    roles = (await db_session.execute(select(Role).where(Role.role_organization_id.is_(None)))).scalars().all()
    teacher_role = next(r for r in roles if r.role_name == SystemRole.TEACHER)

    member_svc = MemberService(db_session)
    await member_svc.create_member(org_id, MemberCreateRequest(
        email=temp_user.user_email, first_name="Temp", last_name="Creator", role_id=teacher_role.role_id, workspace_ids=[]
    ))
    await org_repo.create_workspace_member(ws_id, temp_user.user_id, teacher_role.role_id)
    await db_session.commit()

    subj = await subj_svc.create_subject(
        org_id=org_id,
        workspace_id=ws_id,
        created_by_user_id=temp_user.user_id,
        payload=SubjectCreateRequest(workspace_id=ws_id, subject_name="Temporary Subject")
    )
    await db_session.commit()
    assert subj.subject_created_by == temp_user.user_id

    # Delete the creator user
    from app.modules.users.models import User
    user_obj = await db_session.get(User, temp_user.user_id)
    await db_session.delete(user_obj)
    await db_session.commit()

    # Verify subject_created_by is now NULL
    db_subj = (await db_session.execute(select(Subject).where(Subject.subject_id == subj.subject_id))).scalars().first()
    assert db_subj is not None
    assert db_subj.subject_created_by is None
