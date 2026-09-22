import uuid
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage.s3 import S3StorageService
from app.core.exceptions import (
    NotFoundException,
    ForbiddenException,
    ValidationException,
    ConflictException
)
from app.modules.subjects.models import (
    Subject,
    SubjectStatus,
    SubjectMaterial,
    SubjectMaterialStatus
)
from app.modules.organizations.models import Workspace, WorkspaceStatus
from app.modules.subjects.material_repository import SubjectMaterialRepository
from app.modules.subjects.material_schemas import (
    MaterialUploadUrlRequest,
    MaterialUploadUrlResponse,
    MaterialConfirmRequest,
    MaterialUpdateRequest,
    MaterialResponse,
    MaterialUploaderSummary,
    MaterialDownloadUrlResponse
)
from app.modules.subjects.materials_validation import (
    validate_material_upload_request,
    sanitize_filename,
    generate_material_s3_key
)


class SubjectMaterialService:
    def __init__(self, db: AsyncSession, storage: Optional[S3StorageService] = None):
        self.db = db
        self.repo = SubjectMaterialRepository(db)
        self.storage = storage or S3StorageService()

    # ── Hierarchy and Context Verification ──────────────────────

    async def _verify_subject_hierarchy(
        self,
        subject_id: uuid.UUID,
        org_id: uuid.UUID,
        allow_archived_parent: bool = False
    ) -> Tuple[Subject, Workspace]:
        """
        Verify that:
        1. The subject exists.
        2. The subject belongs to a workspace in the active organization.
        3. Neither the subject nor the workspace is archived (unless allow_archived_parent is True).
        """
        subject = await self.repo.get_subject(subject_id)
        if not subject:
            raise NotFoundException("Subject not found.")

        if not allow_archived_parent and subject.subject_status == SubjectStatus.ARCHIVED:
            raise ConflictException("Subject is archived.")

        workspace = await self.repo.get_workspace(subject.subject_workspace_id)
        if not workspace or workspace.workspace_organization_id != org_id:
            raise NotFoundException("Subject not found in the current organization.")

        if not allow_archived_parent and workspace.workspace_status == WorkspaceStatus.ARCHIVED:
            raise ConflictException("Workspace is archived.")

        return subject, workspace

    async def _verify_material_hierarchy(
        self,
        material_id: uuid.UUID,
        subject_id: uuid.UUID,
        org_id: uuid.UUID,
        allow_archived_parent: bool = False
    ) -> Tuple[SubjectMaterial, Subject, Workspace]:
        """
        Verify that:
        1. The material exists and belongs to the specified subject.
        2. The subject belongs to a workspace in the active organization.
        """
        material = await self.repo.get_material_by_id(material_id)
        if not material or material.material_subject_id != subject_id:
            raise NotFoundException("Material not found in this subject.")

        subject, workspace = await self._verify_subject_hierarchy(
            subject_id,
            org_id,
            allow_archived_parent=allow_archived_parent
        )
        return material, subject, workspace

    async def _verify_teacher_or_admin(
        self,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        workspace_id: uuid.UUID,
        is_org_admin: bool
    ) -> None:
        """
        Verify that the user is an Organization Owner/Admin OR an assigned teacher of the subject.
        """
        if is_org_admin:
            return

        is_ws_member = await self.repo.is_user_workspace_member(user_id, workspace_id)
        if not is_ws_member:
            raise ForbiddenException("Access denied. You are not a member of this workspace.")

        is_assigned_teacher = await self.repo.is_user_subject_teacher(subject_id, user_id)
        if not is_assigned_teacher:
            raise ForbiddenException("Access denied. You are not assigned to this subject.")

    async def _verify_workspace_access(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        is_org_admin: bool
    ) -> None:
        """
        Verify that the user has workspace membership (or is an org owner/admin).
        """
        if is_org_admin:
            return

        is_ws_member = await self.repo.is_user_workspace_member(user_id, workspace_id)
        if not is_ws_member:
            raise ForbiddenException("Access denied. You are not a member of this workspace.")

    # ── Service Operations ──────────────────────────────────────

    async def request_upload_url(
        self,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        payload: MaterialUploadUrlRequest
    ) -> MaterialUploadUrlResponse:
        """
        Validate upload parameters, verify teacher authorization, create a material
        record with active/pending status, and return a presigned PUT URL.
        """
        subject, workspace = await self._verify_subject_hierarchy(subject_id, org_id)
        await self._verify_teacher_or_admin(
            user_id=requesting_user_id,
            org_id=org_id,
            subject_id=subject.subject_id,
            workspace_id=workspace.workspace_id,
            is_org_admin=is_org_admin
        )

        clean_filename = sanitize_filename(payload.original_filename)
        ext = validate_material_upload_request(
            content_type=payload.content_type,
            file_size=payload.file_size,
            filename=clean_filename
        )

        material_id = uuid.uuid4()
        s3_key = generate_material_s3_key(subject.subject_id, material_id, ext)

        upload_url = self.storage.generate_upload_url(
            key=s3_key,
            content_type=payload.content_type.strip().lower(),
            expires_in=900
        )

        # Create the initial material record (initially created with s3_key)
        await self.repo.create_material(
            subject_id=subject.subject_id,
            title=payload.title.strip(),
            description=payload.description.strip() if payload.description else None,
            category=payload.category.strip() if payload.category else "Notes",
            original_filename=clean_filename,
            content_type=payload.content_type.strip().lower(),
            file_size=payload.file_size,
            s3_key=s3_key,
            uploaded_by=requesting_user_id,
            status=SubjectMaterialStatus.ACTIVE,
            material_id=material_id
        )

        return MaterialUploadUrlResponse(
            material_id=material_id,
            s3_key=s3_key,
            upload_url=upload_url,
            expires_in=900
        )

    async def confirm_upload(
        self,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        material_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        payload: MaterialConfirmRequest
    ) -> MaterialResponse:
        """
        Verify the uploaded object exists in S3 and finalize active status.
        """
        material, subject, workspace = await self._verify_material_hierarchy(
            material_id, subject_id, org_id
        )
        await self._verify_teacher_or_admin(
            user_id=requesting_user_id,
            org_id=org_id,
            subject_id=subject.subject_id,
            workspace_id=workspace.workspace_id,
            is_org_admin=is_org_admin
        )

        # Validate S3 key prefix security
        expected_prefix = f"subjects/{subject.subject_id}/materials/{material.material_id}/"
        if not payload.s3_key.startswith(expected_prefix):
            raise ValidationException("Invalid S3 key for this material.")

        # Verify object actually exists in S3
        if not self.storage.object_exists(payload.s3_key):
            raise ValidationException("Uploaded file was not found in storage. Upload may have failed.")

        # Ensure s3_key is set and active
        material.material_s3_key = payload.s3_key
        material.material_status = SubjectMaterialStatus.ACTIVE
        await self.db.flush()

        return self._format_material_response(material)

    async def list_materials(
        self,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        category: Optional[str] = None,
        search: Optional[str] = None,
        status_filter: Optional[SubjectMaterialStatus] = None
    ) -> List[MaterialResponse]:
        """
        List materials for a subject.
        Students/unassigned workspace members can only view active materials.
        Assigned teachers and org admins can also view archived materials if requested.
        """
        subject, workspace = await self._verify_subject_hierarchy(subject_id, org_id)
        await self._verify_workspace_access(
            user_id=requesting_user_id,
            workspace_id=workspace.workspace_id,
            is_org_admin=is_org_admin
        )

        is_assigned_teacher = await self.repo.is_user_subject_teacher(subject.subject_id, requesting_user_id)
        can_manage = is_org_admin or is_assigned_teacher

        materials = await self.repo.list_materials_for_subject(
            subject_id=subject.subject_id,
            status_filter=status_filter,
            category=category,
            search=search,
            include_archived=can_manage
        )

        return [self._format_material_response(m) for m in materials]

    async def get_material(
        self,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        material_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool
    ) -> MaterialResponse:
        """
        Retrieve a single material record by ID.
        """
        material, subject, workspace = await self._verify_material_hierarchy(
            material_id, subject_id, org_id
        )
        await self._verify_workspace_access(
            user_id=requesting_user_id,
            workspace_id=workspace.workspace_id,
            is_org_admin=is_org_admin
        )

        is_assigned_teacher = await self.repo.is_user_subject_teacher(subject.subject_id, requesting_user_id)
        can_manage = is_org_admin or is_assigned_teacher

        if material.material_status == SubjectMaterialStatus.ARCHIVED and not can_manage:
            raise NotFoundException("Material not found.")

        return self._format_material_response(material)

    async def update_material(
        self,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        material_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        payload: MaterialUpdateRequest
    ) -> MaterialResponse:
        """
        Update course material metadata (title, description, category).
        """
        material, subject, workspace = await self._verify_material_hierarchy(
            material_id, subject_id, org_id
        )
        await self._verify_teacher_or_admin(
            user_id=requesting_user_id,
            org_id=org_id,
            subject_id=subject.subject_id,
            workspace_id=workspace.workspace_id,
            is_org_admin=is_org_admin
        )

        if material.material_status == SubjectMaterialStatus.ARCHIVED:
            raise ConflictException("Cannot edit an archived material.")

        updated = await self.repo.update_material(
            material=material,
            title=payload.title,
            description=payload.description,
            category=payload.category
        )

        return self._format_material_response(updated)

    async def archive_material(
        self,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        material_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool
    ) -> dict:
        """
        Soft archive course material.
        """
        material, subject, workspace = await self._verify_material_hierarchy(
            material_id, subject_id, org_id
        )
        await self._verify_teacher_or_admin(
            user_id=requesting_user_id,
            org_id=org_id,
            subject_id=subject.subject_id,
            workspace_id=workspace.workspace_id,
            is_org_admin=is_org_admin
        )

        await self.repo.archive_material(material)
        return {"message": "Material archived successfully"}

    async def get_download_url(
        self,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        material_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool
    ) -> MaterialDownloadUrlResponse:
        """
        Generate a short-lived presigned GET URL for downloading or browser-viewing.
        """
        material, subject, workspace = await self._verify_material_hierarchy(
            material_id, subject_id, org_id
        )
        await self._verify_workspace_access(
            user_id=requesting_user_id,
            workspace_id=workspace.workspace_id,
            is_org_admin=is_org_admin
        )

        is_assigned_teacher = await self.repo.is_user_subject_teacher(subject.subject_id, requesting_user_id)
        can_manage = is_org_admin or is_assigned_teacher

        if material.material_status == SubjectMaterialStatus.ARCHIVED and not can_manage:
            raise NotFoundException("Material not found.")

        url = self.storage.generate_download_url(
            key=material.material_s3_key,
            expires_in=900
        )

        return MaterialDownloadUrlResponse(
            download_url=url,
            expires_in=900,
            original_filename=material.material_original_filename,
            content_type=material.material_content_type
        )

    # ── Response Helpers ────────────────────────────────────────

    def _format_material_response(self, material: SubjectMaterial) -> MaterialResponse:
        uploader_summary = None
        if material.uploader:
            uploader_summary = MaterialUploaderSummary(
                user_id=material.uploader.user_id,
                email=material.uploader.user_email,
                first_name=material.uploader.user_first_name,
                last_name=material.uploader.user_last_name
            )

        return MaterialResponse(
            material_id=material.material_id,
            subject_id=material.material_subject_id,
            title=material.material_title,
            description=material.material_description,
            category=material.material_category,
            original_filename=material.material_original_filename,
            content_type=material.material_content_type,
            file_size=material.material_file_size,
            status=material.material_status.value if hasattr(material.material_status, "value") else str(material.material_status),
            s3_key=material.material_s3_key,
            uploaded_by=uploader_summary,
            created_at=material.material_created_at,
            updated_at=material.material_updated_at
        )
