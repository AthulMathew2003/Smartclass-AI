import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.modules.subjects.models import SubjectStatus
from app.modules.subjects.repository import SubjectRepository
from app.modules.subjects.schemas import (
    SubjectCreateRequest,
    SubjectUpdateRequest,
    SubjectResponse,
    SubjectTeacherAddRequest,
    SubjectTeacherResponse
)
from app.modules.users.models import User
from app.modules.organizations.models import WorkspaceStatus
from app.core.exceptions import ConflictException, NotFoundException, ForbiddenException


class SubjectService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SubjectRepository(db)

    async def _verify_workspace_context(self, workspace_id: uuid.UUID, org_id: uuid.UUID):
        """Verify the workspace exists and belongs to the given organization."""
        workspace = await self.repo.get_workspace(workspace_id)
        if not workspace or workspace.workspace_organization_id != org_id:
            raise NotFoundException("Workspace not found in the current organization.")
        return workspace

    def _populate_teacher_response(self, resp: SubjectResponse, teachers: List) -> None:
        resp.teacher_count = len(teachers)
        resp.teachers = []
        for t in teachers:
            item = SubjectTeacherResponse.model_validate(t)
            if hasattr(t, "user") and t.user:
                item.user_email = t.user.user_email
                item.user_first_name = t.user.user_first_name
                item.user_last_name = t.user.user_last_name
            resp.teachers.append(item)

    # ── Subject CRUD ────────────────────────────────────────────────────

    async def list_accessible_subjects(
        self,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        workspace_id: uuid.UUID,
        is_org_admin: bool
    ) -> List[SubjectResponse]:
        """
        Visibility logic:
        - All workspace members see all subjects in their workspace.
        - Admin/Owner access is verified by RBAC at the API layer.
        - Non-admin users must be workspace members (verified here).
        """
        await self._verify_workspace_context(workspace_id, org_id)

        if not is_org_admin:
            is_ws_member = await self.repo.is_user_workspace_member(user_id, workspace_id)
            if not is_ws_member:
                raise ForbiddenException("Access denied. You are not a member of this workspace.")

        subjects = await self.repo.list_subjects_by_workspace(workspace_id)

        result = []
        for s in subjects:
            resp = SubjectResponse.model_validate(s)
            teachers = await self.repo.get_subject_teachers(s.subject_id)
            self._populate_teacher_response(resp, teachers)
            result.append(resp)
        return result

    async def get_subject(
        self,
        subject_id: uuid.UUID,
        workspace_id: uuid.UUID,
        org_id: uuid.UUID,
        requesting_user_id: Optional[uuid.UUID] = None,
        is_org_admin: bool = False
    ) -> SubjectResponse:
        await self._verify_workspace_context(workspace_id, org_id)

        subject = await self.repo.get_subject_by_id(subject_id)
        if not subject or subject.subject_workspace_id != workspace_id:
            raise NotFoundException("Subject not found.")

        # Access check: workspace membership (not subject-level membership)
        if not is_org_admin and requesting_user_id:
            is_ws_member = await self.repo.is_user_workspace_member(requesting_user_id, workspace_id)
            if not is_ws_member:
                raise ForbiddenException("Access denied. You are not a member of this workspace.")

        resp = SubjectResponse.model_validate(subject)
        teachers = await self.repo.get_subject_teachers(subject_id)
        self._populate_teacher_response(resp, teachers)
        return resp

    async def create_subject(
        self,
        org_id: uuid.UUID,
        workspace_id: uuid.UUID,
        created_by_user_id: uuid.UUID,
        payload: SubjectCreateRequest
    ) -> SubjectResponse:
        workspace = await self._verify_workspace_context(workspace_id, org_id)

        if workspace.workspace_status == WorkspaceStatus.ARCHIVED:
            raise ForbiddenException("Cannot create a subject in an archived workspace.")

        if await self.repo.exists_subject_name(workspace_id, payload.subject_name):
            raise ConflictException(f"A subject named '{payload.subject_name}' already exists in this workspace.")

        subject = await self.repo.create_subject(
            workspace_id=workspace_id,
            name=payload.subject_name,
            description=payload.subject_description,
            created_by=created_by_user_id
        )

        resp = SubjectResponse.model_validate(subject)
        self._populate_teacher_response(resp, [])
        return resp

    async def update_subject(
        self,
        subject_id: uuid.UUID,
        org_id: uuid.UUID,
        workspace_id: uuid.UUID,
        payload: SubjectUpdateRequest,
        requesting_user_id: Optional[uuid.UUID] = None,
        is_org_admin: bool = False
    ) -> SubjectResponse:
        await self._verify_workspace_context(workspace_id, org_id)

        subject = await self.repo.get_subject_by_id(subject_id)
        if not subject or subject.subject_workspace_id != workspace_id:
            raise NotFoundException("Subject not found.")

        if subject.subject_status == SubjectStatus.ARCHIVED:
            raise ForbiddenException("Cannot update an archived subject.")

        # Access: admin/owner OR assigned teacher of this subject
        if not is_org_admin and requesting_user_id:
            teacher = await self.repo.get_subject_teacher(subject_id, requesting_user_id)
            if not teacher:
                raise ForbiddenException("Access denied. Only assigned teachers of this subject can update it.")

        if payload.subject_name and payload.subject_name.strip().lower() != subject.subject_name.lower():
            if await self.repo.exists_subject_name(workspace_id, payload.subject_name, exclude_subject_id=subject_id):
                raise ConflictException(f"A subject named '{payload.subject_name}' already exists in this workspace.")

        updated_subject = await self.repo.update_subject(
            subject=subject,
            name=payload.subject_name,
            description=payload.subject_description
        )

        resp = SubjectResponse.model_validate(updated_subject)
        teachers = await self.repo.get_subject_teachers(subject_id)
        self._populate_teacher_response(resp, teachers)
        return resp

    async def archive_subject(
        self,
        subject_id: uuid.UUID,
        org_id: uuid.UUID,
        workspace_id: uuid.UUID
    ) -> SubjectResponse:
        await self._verify_workspace_context(workspace_id, org_id)

        subject = await self.repo.get_subject_by_id(subject_id)
        if not subject or subject.subject_workspace_id != workspace_id:
            raise NotFoundException("Subject not found.")

        if subject.subject_status == SubjectStatus.ARCHIVED:
            resp = SubjectResponse.model_validate(subject)
            teachers = await self.repo.get_subject_teachers(subject_id)
            self._populate_teacher_response(resp, teachers)
            return resp

        archived_subject = await self.repo.archive_subject(subject)
        resp = SubjectResponse.model_validate(archived_subject)
        teachers = await self.repo.get_subject_teachers(subject_id)
        self._populate_teacher_response(resp, teachers)
        return resp

    # ── Subject Teacher management ──────────────────────────────────────

    async def get_subject_teachers(
        self,
        subject_id: uuid.UUID,
        org_id: uuid.UUID,
        workspace_id: uuid.UUID,
        requesting_user_id: Optional[uuid.UUID] = None,
        is_org_admin: bool = False
    ) -> List[SubjectTeacherResponse]:
        await self._verify_workspace_context(workspace_id, org_id)

        subject = await self.repo.get_subject_by_id(subject_id)
        if not subject or subject.subject_workspace_id != workspace_id:
            raise NotFoundException("Subject not found.")

        # Access: workspace membership check (all ws members can view teachers)
        if not is_org_admin and requesting_user_id:
            is_ws_member = await self.repo.is_user_workspace_member(requesting_user_id, workspace_id)
            if not is_ws_member:
                raise ForbiddenException("Access denied. You are not a member of this workspace.")

        teachers = await self.repo.get_subject_teachers(subject_id)
        res = []
        for t in teachers:
            item = SubjectTeacherResponse.model_validate(t)
            if hasattr(t, "user") and t.user:
                item.user_email = t.user.user_email
                item.user_first_name = t.user.user_first_name
                item.user_last_name = t.user.user_last_name
            res.append(item)
        return res

    async def add_subject_teacher(
        self,
        subject_id: uuid.UUID,
        org_id: uuid.UUID,
        workspace_id: uuid.UUID,
        payload: SubjectTeacherAddRequest,
        requesting_user_id: Optional[uuid.UUID] = None,
        is_org_admin: bool = False
    ) -> SubjectTeacherResponse:
        workspace = await self._verify_workspace_context(workspace_id, org_id)
        if workspace.workspace_status == WorkspaceStatus.ARCHIVED:
            raise ForbiddenException("Cannot assign teachers in an archived workspace.")

        subject = await self.repo.get_subject_by_id(subject_id)
        if not subject or subject.subject_workspace_id != workspace_id:
            raise NotFoundException("Subject not found.")

        if subject.subject_status == SubjectStatus.ARCHIVED:
            raise ForbiddenException("Cannot assign teachers to an archived subject.")

        # Verify requesting user has authority (admin or assigned teacher of this subject)
        if not is_org_admin and requesting_user_id:
            req_teacher = await self.repo.get_subject_teacher(subject_id, requesting_user_id)
            if not req_teacher:
                raise ForbiddenException("Access denied. Only assigned teachers of this subject can add other teachers.")

        # Validate the target user
        is_org_member = await self.repo.is_user_active_organization_member(payload.user_id, org_id)
        if not is_org_member:
            raise ForbiddenException("User must be an active member of the organization.")

        is_ws_member = await self.repo.is_user_workspace_member(payload.user_id, workspace_id)
        if not is_ws_member:
            raise ForbiddenException("User must be a member of the workspace.")

        # Validate user has Teacher role in the workspace (tenant-bounded)
        is_teacher = await self.repo.is_user_teacher_in_workspace(payload.user_id, workspace_id)
        if not is_teacher:
            raise ForbiddenException("User must have a Teacher role in this workspace.")

        # Check for duplicate
        existing = await self.repo.get_subject_teacher(subject_id, payload.user_id)
        if existing:
            raise ConflictException("User is already assigned as a teacher of this subject.")

        teacher = await self.repo.add_subject_teacher(
            subject_id=subject_id,
            user_id=payload.user_id
        )
        item = SubjectTeacherResponse.model_validate(teacher)
        user = await self.db.get(User, payload.user_id)
        if user:
            item.user_email = user.user_email
            item.user_first_name = user.user_first_name
            item.user_last_name = user.user_last_name
        return item

    async def remove_subject_teacher(
        self,
        subject_id: uuid.UUID,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        workspace_id: uuid.UUID,
        requesting_user_id: Optional[uuid.UUID] = None,
        is_org_admin: bool = False
    ) -> None:
        workspace = await self._verify_workspace_context(workspace_id, org_id)
        if workspace.workspace_status == WorkspaceStatus.ARCHIVED:
            raise ForbiddenException("Cannot modify subject teachers in an archived workspace.")

        subject = await self.repo.get_subject_by_id(subject_id)
        if not subject or subject.subject_workspace_id != workspace_id:
            raise NotFoundException("Subject not found.")

        if subject.subject_status == SubjectStatus.ARCHIVED:
            raise ForbiddenException("Cannot remove teachers from an archived subject.")

        teacher = await self.repo.get_subject_teacher(subject_id, user_id)
        if not teacher:
            raise NotFoundException("User is not assigned as a teacher of this subject.")

        if not is_org_admin and requesting_user_id:
            req_teacher = await self.repo.get_subject_teacher(subject_id, requesting_user_id)
            if not req_teacher:
                raise ForbiddenException("Access denied. Only assigned teachers of this subject can remove other teachers.")

            if await self.repo.is_user_org_admin(user_id, org_id):
                raise ForbiddenException("Teachers cannot remove organization administrators from a subject.")

        await self.repo.remove_subject_teacher(teacher)
