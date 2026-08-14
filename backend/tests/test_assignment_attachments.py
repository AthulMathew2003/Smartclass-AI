import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.modules.assignments.models import Assignment, AssignmentAttachment, AssignmentStatus
from app.modules.assignments.attachments import (
    sanitize_filename,
    validate_attachment_request,
    generate_attachment_s3_key,
    ALLOWED_ATTACHMENT_MIME_TYPES
)
from app.modules.subjects.models import Subject
from app.modules.organizations.models import Organization, Workspace
from app.modules.users.models import User
from app.core.exceptions import ValidationException


def test_sanitize_filename():
    assert sanitize_filename("test.pdf") == "test.pdf"
    assert sanitize_filename("../../../etc/passwd") == "passwd"
    assert sanitize_filename("C:\\Windows\\System32\\calc.exe") == "calc.exe"
    assert sanitize_filename("") == "attachment"
    assert sanitize_filename(None) == "attachment"
    assert len(sanitize_filename("a" * 300 + ".pdf")) == 255


def test_validate_attachment_request_allowed_types():
    for mime_type, expected_ext in ALLOWED_ATTACHMENT_MIME_TYPES.items():
        ext = validate_attachment_request(mime_type, 1024 * 1024, f"sample.{expected_ext}")
        assert ext == expected_ext


def test_validate_attachment_request_disallowed_types():
    with pytest.raises(ValidationException, match="not allowed"):
        validate_attachment_request("image/svg+xml", 1024, "icon.svg")

    with pytest.raises(ValidationException, match="not allowed"):
        validate_attachment_request("text/html", 1024, "page.html")

    with pytest.raises(ValidationException, match="not allowed"):
        validate_attachment_request("application/javascript", 1024, "script.js")

    with pytest.raises(ValidationException, match="Unsupported file type"):
        validate_attachment_request("application/x-zip-compressed", 1024, "archive.zip")


def test_validate_attachment_request_file_size():
    with pytest.raises(ValidationException, match="greater than zero"):
        validate_attachment_request("application/pdf", 0, "file.pdf")

    with pytest.raises(ValidationException, match="greater than zero"):
        validate_attachment_request("application/pdf", -10, "file.pdf")

    with pytest.raises(ValidationException, match="exceeds maximum limit"):
        validate_attachment_request("application/pdf", 11 * 1024 * 1024, "large.pdf")


def test_generate_attachment_s3_key():
    assign_id = uuid.uuid4()
    att_id = uuid.uuid4()
    key = generate_attachment_s3_key(assign_id, att_id, "application/pdf")
    assert key == f"assignments/{assign_id}/attachments/{att_id}.pdf"

    img_key = generate_attachment_s3_key(assign_id, att_id, "image/png")
    assert img_key == f"assignments/{assign_id}/attachments/{att_id}.png"


@pytest.mark.asyncio
async def test_assignment_attachment_cascade_and_creator_set_null(db_session: AsyncSession):
    # 1. Setup owner, creator user, org, workspace, subject, assignment
    owner = User(
        user_id=uuid.uuid4(),
        user_email=f"att_owner_{uuid.uuid4().hex[:6]}@test.com",
        user_password_hash="hash",
        user_first_name="Owner",
        user_last_name="User"
    )
    creator = User(
        user_id=uuid.uuid4(),
        user_email=f"att_creator_{uuid.uuid4().hex[:6]}@test.com",
        user_password_hash="hash",
        user_first_name="Creator",
        user_last_name="User"
    )
    db_session.add(owner)
    db_session.add(creator)
    await db_session.flush()

    org = Organization(
        organization_id=uuid.uuid4(),
        organization_name="Cascade Org",
        organization_slug=f"cascade-org-{uuid.uuid4().hex[:6]}",
        organization_owner_user_id=owner.user_id
    )
    db_session.add(org)
    await db_session.flush()

    ws = Workspace(
        workspace_id=uuid.uuid4(),
        workspace_organization_id=org.organization_id,
        workspace_name="Workspace 1",
        workspace_created_by=owner.user_id
    )
    db_session.add(ws)
    await db_session.flush()

    subj = Subject(
        subject_id=uuid.uuid4(),
        subject_workspace_id=ws.workspace_id,
        subject_name="Physics 101",
        subject_created_by=owner.user_id
    )
    db_session.add(subj)
    await db_session.flush()

    assignment = Assignment(
        assignment_id=uuid.uuid4(),
        assignment_subject_id=subj.subject_id,
        assignment_title="Lab 1",
        assignment_status=AssignmentStatus.DRAFT,
        assignment_created_by=creator.user_id
    )
    db_session.add(assignment)
    await db_session.flush()

    # 2. Add attachment created by creator
    att_id = uuid.uuid4()
    attachment = AssignmentAttachment(
        attachment_id=att_id,
        attachment_assignment_id=assignment.assignment_id,
        attachment_s3_key=f"assignments/{assignment.assignment_id}/attachments/{att_id}.pdf",
        attachment_original_filename="lab_manual.pdf",
        attachment_content_type="application/pdf",
        attachment_size=102400,
        attachment_created_by=creator.user_id
    )
    db_session.add(attachment)
    await db_session.commit()

    # Verify attachment created
    stmt = select(AssignmentAttachment).where(AssignmentAttachment.attachment_id == att_id)
    att_res = (await db_session.execute(stmt)).scalar_one_or_none()
    assert att_res is not None
    assert att_res.attachment_original_filename == "lab_manual.pdf"
    assert att_res.attachment_created_by == creator.user_id

    # 3. Test Creator deletion -> SET NULL on attachment_created_by
    await db_session.delete(creator)
    await db_session.commit()
    db_session.expire_all()

    att_after_user_del = (await db_session.execute(stmt)).scalar_one_or_none()
    assert att_after_user_del is not None
    assert att_after_user_del.attachment_created_by is None

    # 4. Test Assignment deletion -> CASCADE deletes attachment
    await db_session.delete(assignment)
    await db_session.commit()
    db_session.expire_all()

    att_after_assign_del = (await db_session.execute(stmt)).scalar_one_or_none()
    assert att_after_assign_del is None
