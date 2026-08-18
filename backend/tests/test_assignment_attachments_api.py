import uuid
from unittest.mock import patch, MagicMock
import pytest
from httpx import AsyncClient
from app.modules.users.service import UserService


async def _create_user_and_login(client: AsyncClient, user_service: UserService, email: str, name: str) -> dict:
    user = await user_service.create_user(
        email=email,
        password="Password123!",
        first_name=name,
        last_name="User"
    )
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = login_res.json()["access_token"]
    return {
        "user": user,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"}
    }


@pytest.fixture(autouse=True)
def mock_s3_storage():
    with patch("app.modules.assignments.service.S3StorageService") as mock_cls:
        instance = MagicMock()
        instance.generate_upload_url.return_value = "https://s3.ap-south-1.amazonaws.com/presigned-upload-url"
        instance.generate_download_url.return_value = "https://s3.ap-south-1.amazonaws.com/presigned-download-url"
        instance.object_exists.return_value = True
        instance.delete_object.return_value = None
        mock_cls.return_value = instance
        yield instance


@pytest.mark.asyncio
async def test_attachment_full_lifecycle_and_rbac(client: AsyncClient, db_session, mock_s3_storage):
    user_service = UserService(db_session)
    owner_data = await _create_user_and_login(client, user_service, "att_owner@test.com", "Owner")
    teacher1_data = await _create_user_and_login(client, user_service, "att_assigned@test.com", "Teacher1")
    teacher2_data = await _create_user_and_login(client, user_service, "att_unassigned@test.com", "Teacher2")
    student_data = await _create_user_and_login(client, user_service, "att_student@test.com", "Student")
    await db_session.commit()

    # 1. Onboard Org
    onboard_res = await client.post("/api/v1/organizations/onboarding", json={
        "org_name": "Attachment Org", "org_slug": "attachment-org", "org_type": "School", "org_country": "US", "org_state": "CA", "org_city": "SF",
        "org_timezone": "UTC", "owner_first_name": "O", "owner_last_name": "O", "owner_phone": "1", "workspace_name": "Class 10"
    }, headers=owner_data["headers"])
    assert onboard_res.status_code == 200

    org_res = await client.get("/api/v1/organizations/memberships", headers=owner_data["headers"])
    org_id = org_res.json()[0]["organization_id"]
    owner_data["headers"]["X-Organization-Id"] = org_id
    teacher1_data["headers"]["X-Organization-Id"] = org_id
    teacher2_data["headers"]["X-Organization-Id"] = org_id
    student_data["headers"]["X-Organization-Id"] = org_id

    ws_res = await client.get("/api/v1/workspaces", headers=owner_data["headers"])
    workspace_id = ws_res.json()[0]["workspace_id"]

    roles_res = await client.get("/api/v1/organizations/roles", headers=owner_data["headers"])
    roles = roles_res.json()
    teacher_role_id = next(r["role_id"] for r in roles if r["role_name"] == "Teacher")
    student_role_id = next(r["role_id"] for r in roles if r["role_name"] == "Student")

    # Add members
    await client.post("/api/v1/organizations/members", json={
        "email": "att_assigned@test.com", "first_name": "T1", "last_name": "U", "role_id": teacher_role_id, "workspace_ids": [workspace_id]
    }, headers=owner_data["headers"])
    await client.post("/api/v1/organizations/members", json={
        "email": "att_unassigned@test.com", "first_name": "T2", "last_name": "U", "role_id": teacher_role_id, "workspace_ids": [workspace_id]
    }, headers=owner_data["headers"])
    await client.post("/api/v1/organizations/members", json={
        "email": "att_student@test.com", "first_name": "S", "last_name": "U", "role_id": student_role_id, "workspace_ids": [workspace_id]
    }, headers=owner_data["headers"])

    # Create Subject & assign Teacher 1
    sub_res = await client.post("/api/v1/subjects", json={
        "workspace_id": workspace_id, "subject_name": "Chemistry"
    }, headers=owner_data["headers"])
    subject_id = sub_res.json()["subject_id"]
    await client.post(
        f"/api/v1/subjects/{subject_id}/teachers?workspace_id={workspace_id}",
        json={"user_id": str(teacher1_data["user"].user_id)},
        headers=owner_data["headers"]
    )

    # 2. Teacher 1 creates assignment
    assign_res = await client.post("/api/v1/assignments", json={
        "subject_id": subject_id, "title": "Organic Chemistry Lab"
    }, headers=teacher1_data["headers"])
    assert assign_res.status_code == 201
    assignment_id = assign_res.json()["assignment_id"]

    # 3. RBAC on Upload URL Request
    # Student blocked -> 403
    student_req = await client.post(
        f"/api/v1/assignments/{assignment_id}/attachments/upload-url?subject_id={subject_id}",
        json={"filename": "lab.pdf", "content_type": "application/pdf", "file_size": 1024},
        headers=student_data["headers"]
    )
    assert student_req.status_code == 403

    # Unassigned Teacher blocked -> 403
    unassigned_req = await client.post(
        f"/api/v1/assignments/{assignment_id}/attachments/upload-url?subject_id={subject_id}",
        json={"filename": "lab.pdf", "content_type": "application/pdf", "file_size": 1024},
        headers=teacher2_data["headers"]
    )
    assert unassigned_req.status_code == 403

    # Teacher 1 (assigned) requests upload URL -> 200
    upload_req = await client.post(
        f"/api/v1/assignments/{assignment_id}/attachments/upload-url?subject_id={subject_id}",
        json={"filename": "lab_notes.pdf", "content_type": "application/pdf", "file_size": 2048},
        headers=teacher1_data["headers"]
    )
    assert upload_req.status_code == 200
    upload_data = upload_req.json()
    assert "attachment_id" in upload_data
    assert upload_data["s3_key"].startswith(f"assignments/{assignment_id}/attachments/")
    assert "upload_url" in upload_data
    attachment_id = upload_data["attachment_id"]
    s3_key = upload_data["s3_key"]

    # 4. Confirm Upload
    # Student cannot confirm -> 403
    bad_confirm = await client.post(
        f"/api/v1/assignments/{assignment_id}/attachments/confirm?subject_id={subject_id}",
        json={"attachment_id": attachment_id, "s3_key": s3_key, "filename": "lab_notes.pdf", "content_type": "application/pdf", "file_size": 2048},
        headers=student_data["headers"]
    )
    assert bad_confirm.status_code == 403

    # Invalid S3 Key prefix rejection -> 422/400
    bad_key_confirm = await client.post(
        f"/api/v1/assignments/{assignment_id}/attachments/confirm?subject_id={subject_id}",
        json={"attachment_id": attachment_id, "s3_key": f"assignments/{uuid.uuid4()}/attachments/bad.pdf", "filename": "lab_notes.pdf", "content_type": "application/pdf", "file_size": 2048},
        headers=teacher1_data["headers"]
    )
    assert bad_key_confirm.status_code in (400, 422)

    # Valid confirmation by assigned teacher -> 201
    confirm_res = await client.post(
        f"/api/v1/assignments/{assignment_id}/attachments/confirm?subject_id={subject_id}",
        json={"attachment_id": attachment_id, "s3_key": s3_key, "filename": "lab_notes.pdf", "content_type": "application/pdf", "file_size": 2048},
        headers=teacher1_data["headers"]
    )
    assert confirm_res.status_code == 201
    att_saved = confirm_res.json()
    assert att_saved["attachment_id"] == attachment_id
    assert att_saved["original_filename"] == "lab_notes.pdf"
    assert att_saved["size"] == 2048

    # 5. List Attachments on DRAFT assignment
    # Teacher sees 1 attachment
    t_list = await client.get(f"/api/v1/assignments/{assignment_id}/attachments?subject_id={subject_id}", headers=teacher1_data["headers"])
    assert t_list.status_code == 200
    assert len(t_list.json()) == 1

    # Student cannot see draft assignment attachments -> 404
    s_list_draft = await client.get(f"/api/v1/assignments/{assignment_id}/attachments?subject_id={subject_id}", headers=student_data["headers"])
    assert s_list_draft.status_code == 404

    # 6. Publish Assignment
    await client.post(f"/api/v1/assignments/{assignment_id}/publish?subject_id={subject_id}", headers=teacher1_data["headers"])

    # Student can now list attachments -> 200
    s_list_pub = await client.get(f"/api/v1/assignments/{assignment_id}/attachments?subject_id={subject_id}", headers=student_data["headers"])
    assert s_list_pub.status_code == 200
    assert len(s_list_pub.json()) == 1

    # 7. Download Presigned URL
    # Student can get download URL on published assignment
    s_dl = await client.get(
        f"/api/v1/assignments/{assignment_id}/attachments/{attachment_id}/download-url?subject_id={subject_id}",
        headers=student_data["headers"]
    )
    assert s_dl.status_code == 200
    assert "download_url" in s_dl.json()
    assert s_dl.json()["original_filename"] == "lab_notes.pdf"

    # 8. Delete Attachment
    # Student cannot delete attachment -> 403
    s_del = await client.delete(
        f"/api/v1/assignments/{assignment_id}/attachments/{attachment_id}?subject_id={subject_id}",
        headers=student_data["headers"]
    )
    assert s_del.status_code == 403

    # Unassigned Teacher cannot delete -> 403
    u_del = await client.delete(
        f"/api/v1/assignments/{assignment_id}/attachments/{attachment_id}?subject_id={subject_id}",
        headers=teacher2_data["headers"]
    )
    assert u_del.status_code == 403

    # Owner / Admin / Assigned Teacher can delete -> 204
    t_del = await client.delete(
        f"/api/v1/assignments/{assignment_id}/attachments/{attachment_id}?subject_id={subject_id}",
        headers=teacher1_data["headers"]
    )
    assert t_del.status_code == 204

    # After deletion, list is empty
    t_list_empty = await client.get(f"/api/v1/assignments/{assignment_id}/attachments?subject_id={subject_id}", headers=teacher1_data["headers"])
    assert len(t_list_empty.json()) == 0


@pytest.mark.asyncio
async def test_closed_and_archived_attachment_protections(client: AsyncClient, db_session, mock_s3_storage):
    user_service = UserService(db_session)
    owner_data = await _create_user_and_login(client, user_service, "prot_owner@test.com", "Owner")
    teacher_data = await _create_user_and_login(client, user_service, "prot_teacher@test.com", "Teacher")
    await db_session.commit()

    # Onboard
    await client.post("/api/v1/organizations/onboarding", json={
        "org_name": "Prot Org", "org_slug": "prot-org", "org_type": "School", "org_country": "US", "org_state": "CA", "org_city": "SF",
        "org_timezone": "UTC", "owner_first_name": "O", "owner_last_name": "O", "owner_phone": "1", "workspace_name": "WS 1"
    }, headers=owner_data["headers"])
    org_id = (await client.get("/api/v1/organizations/memberships", headers=owner_data["headers"])).json()[0]["organization_id"]
    owner_data["headers"]["X-Organization-Id"] = org_id
    teacher_data["headers"]["X-Organization-Id"] = org_id
    ws_id = (await client.get("/api/v1/workspaces", headers=owner_data["headers"])).json()[0]["workspace_id"]

    roles = (await client.get("/api/v1/organizations/roles", headers=owner_data["headers"])).json()
    teacher_role_id = next(r["role_id"] for r in roles if r["role_name"] == "Teacher")

    await client.post("/api/v1/organizations/members", json={
        "email": "prot_teacher@test.com", "first_name": "T", "last_name": "U", "role_id": teacher_role_id, "workspace_ids": [ws_id]
    }, headers=owner_data["headers"])

    sub_res = await client.post("/api/v1/subjects", json={"workspace_id": ws_id, "subject_name": "Biology"}, headers=owner_data["headers"])
    subject_id = sub_res.json()["subject_id"]
    await client.post(
        f"/api/v1/subjects/{subject_id}/teachers?workspace_id={ws_id}",
        json={"user_id": str(teacher_data["user"].user_id)},
        headers=owner_data["headers"]
    )

    # Create & publish assignment
    assign_res = await client.post("/api/v1/assignments", json={"subject_id": subject_id, "title": "Genetics"}, headers=teacher_data["headers"])
    assignment_id = assign_res.json()["assignment_id"]
    await client.post(f"/api/v1/assignments/{assignment_id}/publish?subject_id={subject_id}", headers=teacher_data["headers"])

    # Upload 1 attachment while published
    u_res = await client.post(
        f"/api/v1/assignments/{assignment_id}/attachments/upload-url?subject_id={subject_id}",
        json={"filename": "paper.pdf", "content_type": "application/pdf", "file_size": 1024},
        headers=teacher_data["headers"]
    )
    att_id = u_res.json()["attachment_id"]
    s3_key = u_res.json()["s3_key"]
    await client.post(
        f"/api/v1/assignments/{assignment_id}/attachments/confirm?subject_id={subject_id}",
        json={"attachment_id": att_id, "s3_key": s3_key, "filename": "paper.pdf", "content_type": "application/pdf", "file_size": 1024},
        headers=teacher_data["headers"]
    )

    # 1. Close Assignment
    await client.post(f"/api/v1/assignments/{assignment_id}/close?subject_id={subject_id}", headers=teacher_data["headers"])

    # Adding new attachments to CLOSED assignment is rejected -> 409
    assert (await client.post(
        f"/api/v1/assignments/{assignment_id}/attachments/upload-url?subject_id={subject_id}",
        json={"filename": "new.pdf", "content_type": "application/pdf", "file_size": 1024},
        headers=teacher_data["headers"]
    )).status_code == 409

    # Deleting attachments on CLOSED assignment is rejected -> 409
    assert (await client.delete(
        f"/api/v1/assignments/{assignment_id}/attachments/{att_id}?subject_id={subject_id}",
        headers=teacher_data["headers"]
    )).status_code == 409

    # 2. Delete Assignment (Hard Delete)
    await client.delete(f"/api/v1/assignments/{assignment_id}?subject_id={subject_id}", headers=teacher_data["headers"])

    # Adding attachments to DELETED assignment returns -> 404 Not Found
    assert (await client.post(
        f"/api/v1/assignments/{assignment_id}/attachments/upload-url?subject_id={subject_id}",
        json={"filename": "new.pdf", "content_type": "application/pdf", "file_size": 1024},
        headers=teacher_data["headers"]
    )).status_code == 404


@pytest.mark.asyncio
async def test_attachment_tenant_isolation_and_idor(client: AsyncClient, db_session, mock_s3_storage):
    user_service = UserService(db_session)
    owner_a = await _create_user_and_login(client, user_service, "att_a@test.com", "OwnerA")
    owner_b = await _create_user_and_login(client, user_service, "att_b@test.com", "OwnerB")
    await db_session.commit()

    # Org A
    await client.post("/api/v1/organizations/onboarding", json={
        "org_name": "Org A", "org_slug": "org-a-att", "org_type": "School", "org_country": "US", "org_state": "CA", "org_city": "SF",
        "org_timezone": "UTC", "owner_first_name": "A", "owner_last_name": "A", "owner_phone": "1", "workspace_name": "WS A"
    }, headers=owner_a["headers"])
    org_a_id = (await client.get("/api/v1/organizations/memberships", headers=owner_a["headers"])).json()[0]["organization_id"]
    owner_a["headers"]["X-Organization-Id"] = org_a_id
    ws_a_id = (await client.get("/api/v1/workspaces", headers=owner_a["headers"])).json()[0]["workspace_id"]
    sub_a_res = await client.post("/api/v1/subjects", json={"workspace_id": ws_a_id, "subject_name": "Math A"}, headers=owner_a["headers"])
    sub_a_id = sub_a_res.json()["subject_id"]
    assign_a_res = await client.post("/api/v1/assignments", json={"subject_id": sub_a_id, "title": "Calculus"}, headers=owner_a["headers"])
    assign_a_id = assign_a_res.json()["assignment_id"]

    # Add attachment on Org A
    u_res = await client.post(
        f"/api/v1/assignments/{assign_a_id}/attachments/upload-url?subject_id={sub_a_id}",
        json={"filename": "calc.pdf", "content_type": "application/pdf", "file_size": 1024},
        headers=owner_a["headers"]
    )
    att_id = u_res.json()["attachment_id"]
    s3_key = u_res.json()["s3_key"]
    await client.post(
        f"/api/v1/assignments/{assign_a_id}/attachments/confirm?subject_id={sub_a_id}",
        json={"attachment_id": att_id, "s3_key": s3_key, "filename": "calc.pdf", "content_type": "application/pdf", "file_size": 1024},
        headers=owner_a["headers"]
    )

    # Org B
    await client.post("/api/v1/organizations/onboarding", json={
        "org_name": "Org B", "org_slug": "org-b-att", "org_type": "School", "org_country": "US", "org_state": "CA", "org_city": "SF",
        "org_timezone": "UTC", "owner_first_name": "B", "owner_last_name": "B", "owner_phone": "1", "workspace_name": "WS B"
    }, headers=owner_b["headers"])
    org_b_id = (await client.get("/api/v1/organizations/memberships", headers=owner_b["headers"])).json()[0]["organization_id"]
    owner_b["headers"]["X-Organization-Id"] = org_b_id

    # Org B attempts to access Org A attachments -> 403 or 404
    assert (await client.get(f"/api/v1/assignments/{assign_a_id}/attachments?subject_id={sub_a_id}", headers=owner_b["headers"])).status_code in (403, 404)
    assert (await client.get(f"/api/v1/assignments/{assign_a_id}/attachments/{att_id}/download-url?subject_id={sub_a_id}", headers=owner_b["headers"])).status_code in (403, 404)
    assert (await client.delete(f"/api/v1/assignments/{assign_a_id}/attachments/{att_id}?subject_id={sub_a_id}", headers=owner_b["headers"])).status_code in (403, 404)
