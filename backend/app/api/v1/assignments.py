import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.users.models import User
from app.modules.auth.dependencies import get_current_user
from app.modules.organizations.models import Organization
from app.modules.rbac.dependencies import get_current_organization, require_permission
from app.modules.rbac.constants import AssignmentPermission
from app.modules.assignments.models import AssignmentStatus
from app.modules.assignments.service import AssignmentService
from app.modules.assignments.schemas import (
    AssignmentCreateRequest,
    AssignmentUpdateRequest,
    AssignmentResponse,
    AttachmentUploadUrlRequest,
    AttachmentUploadUrlResponse,
    AttachmentConfirmRequest,
    AttachmentResponse,
    AttachmentDownloadUrlResponse,
    SubmissionResponse,
    SubmissionFileUploadUrlRequest,
    SubmissionFileUploadUrlResponse,
    StudentSubmitRequest,
    GradeSubmissionRequest,
    ReturnSubmissionRequest
)

router = APIRouter()


# ── Assignment Endpoints ────────────────────────────────────────

@router.get("", response_model=List[AssignmentResponse])
async def list_assignments(
    subject_id: Optional[uuid.UUID] = Query(None, description="Subject ID (optional for global view)"),
    workspace_id: Optional[uuid.UUID] = Query(None, description="Workspace ID (optional)"),
    status: Optional[AssignmentStatus] = Query(None, description="Filter assignments by status"),
    search: Optional[str] = Query(None, description="Search assignments by title, description, or subject name"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.READ))
):
    """List accessible assignments (subject-scoped or global across organization)."""
    service = AssignmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    return await service.list_assignments(
        org_id=org.organization_id,
        subject_id=subject_id,
        workspace_id=workspace_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        status_filter=status,
        search=search
    )


@router.post("", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    payload: AssignmentCreateRequest,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.CREATE))
):
    """Create a new assignment for a subject (Teachers/Admins only, starts as DRAFT)."""
    service = AssignmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.create_assignment(
        org_id=org.organization_id,
        created_by_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        payload=payload
    )
    await db.commit()
    return res


@router.get("/{assignment_id}", response_model=AssignmentResponse)
async def get_assignment(
    assignment_id: uuid.UUID,
    subject_id: Optional[uuid.UUID] = Query(None, description="Subject ID (optional)"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.READ))
):
    """Retrieve details of a single assignment."""
    service = AssignmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    return await service.get_assignment(
        org_id=org.organization_id,
        assignment_id=assignment_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        subject_id=subject_id
    )


@router.patch("/{assignment_id}", response_model=AssignmentResponse)
async def update_assignment(
    assignment_id: uuid.UUID,
    payload: AssignmentUpdateRequest,
    subject_id: Optional[uuid.UUID] = Query(None, description="Subject ID (optional)"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.UPDATE))
):
    """Update an assignment's title, description, or due date."""
    service = AssignmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.update_assignment(
        org_id=org.organization_id,
        assignment_id=assignment_id,
        payload=payload,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        subject_id=subject_id
    )
    await db.commit()
    return res


@router.post("/{assignment_id}/publish", response_model=AssignmentResponse)
async def publish_assignment(
    assignment_id: uuid.UUID,
    subject_id: Optional[uuid.UUID] = Query(None, description="Subject ID (optional)"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.UPDATE))
):
    """Publish a draft assignment (DRAFT -> PUBLISHED)."""
    service = AssignmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.publish_assignment(
        org_id=org.organization_id,
        assignment_id=assignment_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        subject_id=subject_id
    )
    await db.commit()
    return res


@router.post("/{assignment_id}/close", response_model=AssignmentResponse)
async def close_assignment(
    assignment_id: uuid.UUID,
    subject_id: Optional[uuid.UUID] = Query(None, description="Subject ID (optional)"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.UPDATE))
):
    """Close an active assignment (PUBLISHED -> CLOSED)."""
    service = AssignmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.close_assignment(
        org_id=org.organization_id,
        assignment_id=assignment_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        subject_id=subject_id
    )
    await db.commit()
    return res


@router.delete("/{assignment_id}")
@router.post("/{assignment_id}/archive")
async def delete_assignment(
    assignment_id: uuid.UUID,
    subject_id: Optional[uuid.UUID] = Query(None, description="Subject ID (optional)"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.DELETE))
):
    """Permanently delete an assignment, its reference files, and all student submissions."""
    service = AssignmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    await service.delete_assignment(
        org_id=org.organization_id,
        assignment_id=assignment_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        subject_id=subject_id
    )
    await db.commit()
    return {"message": "Assignment deleted successfully", "assignment_id": str(assignment_id)}


# ── Teacher Assignment Attachment Endpoints ─────────────────────

@router.post("/{assignment_id}/attachments/upload-url", response_model=AttachmentUploadUrlResponse)
async def request_attachment_upload_url(
    assignment_id: uuid.UUID,
    payload: AttachmentUploadUrlRequest,
    subject_id: Optional[uuid.UUID] = Query(None, description="Subject ID (optional)"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.UPDATE))
):
    """Request a short-lived presigned S3 upload URL for an assignment attachment."""
    service = AssignmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    return await service.request_attachment_upload_url(
        org_id=org.organization_id,
        assignment_id=assignment_id,
        payload=payload,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        subject_id=subject_id
    )


@router.post("/{assignment_id}/attachments/confirm", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED)
async def confirm_attachment_upload(
    assignment_id: uuid.UUID,
    payload: AttachmentConfirmRequest,
    subject_id: Optional[uuid.UUID] = Query(None, description="Subject ID (optional)"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.UPDATE))
):
    """Confirm S3 upload and record attachment metadata in database."""
    service = AssignmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.confirm_attachment_upload(
        org_id=org.organization_id,
        assignment_id=assignment_id,
        payload=payload,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        subject_id=subject_id
    )
    await db.commit()
    return res


@router.get("/{assignment_id}/attachments", response_model=List[AttachmentResponse])
async def list_attachments(
    assignment_id: uuid.UUID,
    subject_id: Optional[uuid.UUID] = Query(None, description="Subject ID (optional)"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.READ))
):
    """List attachments for an assignment."""
    service = AssignmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    return await service.list_attachments(
        org_id=org.organization_id,
        assignment_id=assignment_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        subject_id=subject_id
    )


@router.get("/{assignment_id}/attachments/{attachment_id}/download-url", response_model=AttachmentDownloadUrlResponse)
async def get_attachment_download_url(
    assignment_id: uuid.UUID,
    attachment_id: uuid.UUID,
    subject_id: Optional[uuid.UUID] = Query(None, description="Subject ID (optional)"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.READ))
):
    """Get a short-lived presigned GET URL for downloading an attachment."""
    service = AssignmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    return await service.get_attachment_download_url(
        org_id=org.organization_id,
        assignment_id=assignment_id,
        attachment_id=attachment_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        subject_id=subject_id
    )


@router.delete("/{assignment_id}/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attachment(
    assignment_id: uuid.UUID,
    attachment_id: uuid.UUID,
    subject_id: Optional[uuid.UUID] = Query(None, description="Subject ID (optional)"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.UPDATE))
):
    """Delete an assignment attachment (S3 object and database row)."""
    service = AssignmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    await service.delete_attachment(
        org_id=org.organization_id,
        assignment_id=assignment_id,
        attachment_id=attachment_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        subject_id=subject_id
    )
    await db.commit()


# ── Student Submission & Resubmission Endpoints ─────────────────

@router.get("/{assignment_id}/submission", response_model=Optional[SubmissionResponse])
async def get_student_submission(
    assignment_id: uuid.UUID,
    student_id: Optional[uuid.UUID] = Query(None, description="Student ID (teachers/admins only)"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.READ))
):
    """
    Retrieve submission history and versions.
    - Students view their own submission.
    - Teachers/Admins can view a student's submission via student_id.
    """
    service = AssignmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    return await service.get_submission(
        org_id=org.organization_id,
        assignment_id=assignment_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        target_student_id=student_id
    )


@router.get("/{assignment_id}/submissions", response_model=List[SubmissionResponse])
async def list_assignment_submissions(
    assignment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.READ))
):
    """List all student submissions for an assignment (Teachers/Admins only)."""
    service = AssignmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    return await service.list_submissions_for_teacher(
        org_id=org.organization_id,
        assignment_id=assignment_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
    )


@router.post("/{assignment_id}/submit", response_model=SubmissionResponse)
async def submit_assignment(
    assignment_id: uuid.UUID,
    payload: StudentSubmitRequest,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.READ))
):
    """
    Submit or resubmit an assignment (Students only).
    - Creates a new submission version on every resubmission.
    """
    service = AssignmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.submit_assignment(
        org_id=org.organization_id,
        assignment_id=assignment_id,
        student_id=current_user.user_id,
        payload=payload,
        is_org_admin=is_org_admin
    )
    await db.commit()
    return res


@router.post("/{assignment_id}/submission/files/upload-url", response_model=SubmissionFileUploadUrlResponse)
async def request_submission_file_upload_url(
    assignment_id: uuid.UUID,
    payload: SubmissionFileUploadUrlRequest,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.READ))
):
    """Request a presigned S3 upload URL for a student submission file."""
    service = AssignmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    return await service.request_submission_file_upload_url(
        org_id=org.organization_id,
        assignment_id=assignment_id,
        student_id=current_user.user_id,
        payload=payload,
        is_org_admin=is_org_admin
    )


@router.get("/{assignment_id}/submission/files/{attachment_id}/download-url", response_model=AttachmentDownloadUrlResponse)
async def get_submission_attachment_download_url(
    assignment_id: uuid.UUID,
    attachment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.READ))
):
    """Get a short-lived presigned GET URL for downloading a student submission attachment."""
    service = AssignmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    return await service.get_submission_attachment_download_url(
        org_id=org.organization_id,
        assignment_id=assignment_id,
        attachment_id=attachment_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
    )


# ── Teacher Grading Endpoints ───────────────────────────────────

@router.post("/{assignment_id}/submissions/{submission_id}/grade", response_model=SubmissionResponse)
async def grade_submission(
    assignment_id: uuid.UUID,
    submission_id: uuid.UUID,
    payload: GradeSubmissionRequest,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.UPDATE))
):
    """Grade a student submission (Teachers & Org Admins only)."""
    service = AssignmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.grade_submission(
        org_id=org.organization_id,
        assignment_id=assignment_id,
        submission_id=submission_id,
        payload=payload,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
    )
    await db.commit()
    return res


@router.post("/{assignment_id}/submissions/{submission_id}/return", response_model=SubmissionResponse)
async def return_submission(
    assignment_id: uuid.UUID,
    submission_id: uuid.UUID,
    payload: ReturnSubmissionRequest,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.UPDATE))
):
    """Return a student submission (Teachers & Org Admins only)."""
    service = AssignmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.return_submission(
        org_id=org.organization_id,
        assignment_id=assignment_id,
        submission_id=submission_id,
        payload=payload,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
    )
    await db.commit()
    return res

