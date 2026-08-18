import uuid
from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient
from app.modules.users.service import UserService
from app.modules.assignments.service import AssignmentService
from app.modules.assignments.models import AssignmentStatus, SubmissionStatus


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


@pytest.mark.asyncio
async def test_student_submission_resubmission_and_grading_flow(client: AsyncClient, db_session, monkeypatch):
    user_service = UserService(db_session)
    owner_data = await _create_user_and_login(client, user_service, "sub_owner@test.com", "Owner")
    teacher_data = await _create_user_and_login(client, user_service, "sub_teacher@test.com", "Teacher")
    student_data = await _create_user_and_login(client, user_service, "sub_student@test.com", "Student")
    student2_data = await _create_user_and_login(client, user_service, "sub_student2@test.com", "Student2")
    await db_session.commit()

    # 1. Onboard Organization
    await client.post("/api/v1/organizations/onboarding", json={
        "org_name": "Submission Academy",
        "org_slug": "sub-academy",
        "org_type": "School",
        "org_country": "US",
        "org_state": "CA",
        "org_city": "SF",
        "org_timezone": "America/Los_Angeles",
        "owner_first_name": "Owner",
        "owner_last_name": "User",
        "owner_phone": "1234567890",
        "workspace_name": "Grade 11"
    }, headers=owner_data["headers"])
    await db_session.commit()

    org_res = await client.get("/api/v1/organizations/memberships", headers=owner_data["headers"])
    org_id = org_res.json()[0]["organization_id"]
    owner_data["headers"]["X-Organization-Id"] = org_id
    teacher_data["headers"]["X-Organization-Id"] = org_id
    student_data["headers"]["X-Organization-Id"] = org_id
    student2_data["headers"]["X-Organization-Id"] = org_id

    # Fetch workspace
    ws_res = await client.get("/api/v1/workspaces", headers=owner_data["headers"])
    workspace_id = ws_res.json()[0]["workspace_id"]

    # Fetch roles
    roles_res = await client.get("/api/v1/organizations/roles", headers=owner_data["headers"])
    roles_data = roles_res.json()
    teacher_role_id = next(r["role_id"] for r in roles_data if r["role_name"] == "Teacher")
    student_role_id = next(r["role_id"] for r in roles_data if r["role_name"] == "Student")

    # Add teacher and students to org & workspace
    await client.post("/api/v1/organizations/members", json={
        "email": "sub_teacher@test.com",
        "first_name": "Teacher",
        "last_name": "User",
        "role_id": teacher_role_id,
        "workspace_ids": [workspace_id]
    }, headers=owner_data["headers"])
    await client.post("/api/v1/organizations/members", json={
        "email": "sub_student@test.com",
        "first_name": "Student",
        "last_name": "User",
        "role_id": student_role_id,
        "workspace_ids": [workspace_id]
    }, headers=owner_data["headers"])
    await client.post("/api/v1/organizations/members", json={
        "email": "sub_student2@test.com",
        "first_name": "Student2",
        "last_name": "User",
        "role_id": student_role_id,
        "workspace_ids": [workspace_id]
    }, headers=owner_data["headers"])

    # Create Subject & assign teacher
    sub_res = await client.post("/api/v1/subjects", json={
        "workspace_id": workspace_id,
        "subject_name": "Calculus",
        "subject_description": "Differential & Integral Calculus."
    }, headers=owner_data["headers"])
    subject_id = sub_res.json()["subject_id"]

    await client.post(
        f"/api/v1/subjects/{subject_id}/teachers?workspace_id={workspace_id}",
        json={"user_id": str(teacher_data["user"].user_id)},
        headers=owner_data["headers"]
    )

    # 2. Teacher creates assignment (DRAFT)
    create_res = await client.post("/api/v1/assignments", json={
        "subject_id": subject_id,
        "title": "Integration by Parts",
        "description": "Complete problems 1 through 10.",
        "due_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    }, headers=teacher_data["headers"])
    assert create_res.status_code == 201
    assignment_id = create_res.json()["assignment_id"]

    # Student cannot submit to DRAFT assignment -> 404
    bad_sub = await client.post(f"/api/v1/assignments/{assignment_id}/submit", json={"files": []}, headers=student_data["headers"])
    assert bad_sub.status_code == 404

    # 3. Publish Assignment
    pub_res = await client.post(f"/api/v1/assignments/{assignment_id}/publish?subject_id={subject_id}", headers=teacher_data["headers"])
    assert pub_res.status_code == 200

    # 4. Student requests presigned upload URL for submission file
    file_req_res = await client.post(
        f"/api/v1/assignments/{assignment_id}/submission/files/upload-url",
        json={
            "filename": "my_homework.pdf",
            "content_type": "application/pdf",
            "file_size": 1024 * 500  # 500 KB
        },
        headers=student_data["headers"]
    )
    assert file_req_res.status_code == 200
    file_upload_data = file_req_res.json()
    assert "upload_url" in file_upload_data
    assert "s3_key" in file_upload_data
    assert "submissions/" in file_upload_data["s3_key"]
    assert str(assignment_id) in file_upload_data["s3_key"]

    att_id = file_upload_data["attachment_id"]
    s3_key = file_upload_data["s3_key"]

    # Mock S3 object_exists for confirming upload
    monkeypatch.setattr("app.core.storage.S3StorageService.object_exists", lambda self, key: True)
    monkeypatch.setattr("app.core.storage.S3StorageService.generate_download_url", lambda self, key, expires_in=900: f"https://mock-s3.example.com/download/{key}")

    deleted_keys = []
    monkeypatch.setattr("app.core.storage.S3StorageService.delete_object", lambda self, key: deleted_keys.append(key))

    # 5. Student submits assignment
    submit_res = await client.post(
        f"/api/v1/assignments/{assignment_id}/submit",
        json={
            "files": [{
                "attachment_id": att_id,
                "s3_key": s3_key,
                "original_filename": "my_homework.pdf",
                "content_type": "application/pdf",
                "file_size": 1024 * 500
            }]
        },
        headers=student_data["headers"]
    )
    assert submit_res.status_code == 200
    sub_data = submit_res.json()
    assert sub_data["submission_status"] == "submitted"
    assert len(sub_data["attachments"]) == 1
    assert sub_data["attachments"][0]["original_filename"] == "my_homework.pdf"
    submission_id = sub_data["submission_id"]
    att_file_id = sub_data["attachments"][0]["attachment_id"]

    # 6. Student downloads their submission attachment
    dl_res = await client.get(
        f"/api/v1/assignments/{assignment_id}/submission/files/{att_file_id}/download-url",
        headers=student_data["headers"]
    )
    assert dl_res.status_code == 200
    assert "https://mock-s3.example.com/download/" in dl_res.json()["download_url"]

    # 7. Student 2 cannot download Student 1's submission file -> 403 / 404
    bad_dl = await client.get(
        f"/api/v1/assignments/{assignment_id}/submission/files/{att_file_id}/download-url",
        headers=student2_data["headers"]
    )
    assert bad_dl.status_code in (403, 404)

    # 8. Teacher views student submission & grades it
    teacher_sub_res = await client.get(
        f"/api/v1/assignments/{assignment_id}/submission?student_id={student_data['user'].user_id}",
        headers=teacher_data["headers"]
    )
    assert teacher_sub_res.status_code == 200
    assert teacher_sub_res.json()["submission_id"] == submission_id

    # Teacher grades submission
    grade_res = await client.post(
        f"/api/v1/assignments/{assignment_id}/submissions/{submission_id}/grade",
        json={
            "grade": 85.5,
            "feedback": "Good job, but check problem 4."
        },
        headers=teacher_data["headers"]
    )
    assert grade_res.status_code == 200
    graded_data = grade_res.json()
    assert graded_data["submission_grade"] == 85.5
    assert graded_data["submission_status"] == "graded"

    # 9. Student resubmits (Direct file replacement)
    # Student requests another file upload URL
    file2_req_res = await client.post(
        f"/api/v1/assignments/{assignment_id}/submission/files/upload-url",
        json={
            "filename": "my_homework_v2.pdf",
            "content_type": "application/pdf",
            "file_size": 1024 * 550
        },
        headers=student_data["headers"]
    )
    assert file2_req_res.status_code == 200
    file2_upload_data = file2_req_res.json()
    att2_id = file2_upload_data["attachment_id"]
    s3_key2 = file2_upload_data["s3_key"]

    # Attempting to submit with an invalid S3 key (wrong prefix or path traversal) -> 400 / 422
    bad_s3_res = await client.post(
        f"/api/v1/assignments/{assignment_id}/submit",
        json={
            "files": [{
                "attachment_id": str(uuid.uuid4()),
                "s3_key": "submissions/arbitrary/path/hack.pdf",
                "original_filename": "hack.pdf",
                "content_type": "application/pdf",
                "file_size": 1024
            }]
        },
        headers=student_data["headers"]
    )
    assert bad_s3_res.status_code in (400, 422)

    resubmit_res = await client.post(
        f"/api/v1/assignments/{assignment_id}/submit",
        json={
            "files": [{
                "attachment_id": att2_id,
                "s3_key": s3_key2,
                "original_filename": "my_homework_v2.pdf",
                "content_type": "application/pdf",
                "file_size": 1024 * 550
            }]
        },
        headers=student_data["headers"]
    )
    assert resubmit_res.status_code == 200
    resub_data = resubmit_res.json()
    assert resub_data["submission_status"] == "submitted"
    # Active submission grade reset to None
    assert resub_data["submission_grade"] is None
    assert resub_data["submission_feedback"] is None
    # Old file replaced with new file
    assert len(resub_data["attachments"]) == 1
    assert resub_data["attachments"][0]["original_filename"] == "my_homework_v2.pdf"
    # Verify old S3 key was deleted
    assert s3_key in deleted_keys

    # 10. Teacher lists all submissions
    all_subs_res = await client.get(
        f"/api/v1/assignments/{assignment_id}/submissions",
        headers=teacher_data["headers"]
    )
    assert all_subs_res.status_code == 200
    all_subs = all_subs_res.json()
    assert len(all_subs) == 1
    assert len(all_subs[0]["attachments"]) == 1
    assert all_subs[0]["attachments"][0]["original_filename"] == "my_homework_v2.pdf"

    # Teacher re-grades the updated submission
    regrade_res = await client.post(
        f"/api/v1/assignments/{assignment_id}/submissions/{submission_id}/grade",
        json={
            "grade": 98.0,
            "feedback": "Perfect fixes on problem 4!"
        },
        headers=teacher_data["headers"]
    )
    assert regrade_res.status_code == 200
    assert regrade_res.json()["submission_grade"] == 98.0
    assert regrade_res.json()["submission_status"] == "graded"

    # 11. Teacher returns submission
    return_res = await client.post(
        f"/api/v1/assignments/{assignment_id}/submissions/{submission_id}/return",
        json={"feedback": "Returned for optional revision."},
        headers=teacher_data["headers"]
    )
    assert return_res.status_code == 200
    return_data = return_res.json()
    assert return_data["submission_status"] == "returned"
    assert return_data["submission_grade"] == 98.0
    assert return_data["submission_feedback"] == "Returned for optional revision."

    # Student cannot grade or return
    bad_grade_student = await client.post(
        f"/api/v1/assignments/{assignment_id}/submissions/{submission_id}/grade",
        json={"grade": 100.0},
        headers=student_data["headers"]
    )
    assert bad_grade_student.status_code == 403

    # Grade validation tests (out of bounds)
    bad_grade_high = await client.post(
        f"/api/v1/assignments/{assignment_id}/submissions/{submission_id}/grade",
        json={"grade": 105.0},
        headers=teacher_data["headers"]
    )
    assert bad_grade_high.status_code in (400, 422)

    bad_grade_low = await client.post(
        f"/api/v1/assignments/{assignment_id}/submissions/{submission_id}/grade",
        json={"grade": -5.0},
        headers=teacher_data["headers"]
    )
    assert bad_grade_low.status_code in (400, 422)

    # 12. Security & IDOR checks
    # Random submission ID -> 404
    fake_sub_id = uuid.uuid4()
    not_found_grade = await client.post(
        f"/api/v1/assignments/{assignment_id}/submissions/{fake_sub_id}/grade",
        json={"grade": 90.0},
        headers=teacher_data["headers"]
    )
    assert not_found_grade.status_code == 404

    # Fake attachment download -> 404
    fake_att_id = uuid.uuid4()
    not_found_dl = await client.get(
        f"/api/v1/assignments/{assignment_id}/submission/files/{fake_att_id}/download-url",
        headers=student_data["headers"]
    )
    assert not_found_dl.status_code == 404

    # 13. Teacher closes assignment
    await client.post(f"/api/v1/assignments/{assignment_id}/close?subject_id={subject_id}", headers=teacher_data["headers"])

    # Student cannot submit to closed assignment -> 409
    closed_sub = await client.post(
        f"/api/v1/assignments/{assignment_id}/submit",
        json={"files": []},
        headers=student_data["headers"]
    )
    assert closed_sub.status_code == 409


@pytest.mark.asyncio
async def test_late_submission_status(client: AsyncClient, db_session, monkeypatch):
    user_service = UserService(db_session)
    owner_data = await _create_user_and_login(client, user_service, "late_owner@test.com", "Owner")
    teacher_data = await _create_user_and_login(client, user_service, "late_teacher@test.com", "Teacher")
    student_data = await _create_user_and_login(client, user_service, "late_student@test.com", "Student")
    await db_session.commit()

    # Onboard
    await client.post("/api/v1/organizations/onboarding", json={
        "org_name": "Late Academy",
        "org_slug": "late-academy",
        "org_type": "School",
        "org_country": "US",
        "org_state": "CA",
        "org_city": "SF",
        "org_timezone": "America/Los_Angeles",
        "owner_first_name": "Owner",
        "owner_last_name": "User",
        "owner_phone": "1234567890",
        "workspace_name": "Grade 12"
    }, headers=owner_data["headers"])
    await db_session.commit()

    org_res = await client.get("/api/v1/organizations/memberships", headers=owner_data["headers"])
    org_id = org_res.json()[0]["organization_id"]
    owner_data["headers"]["X-Organization-Id"] = org_id
    teacher_data["headers"]["X-Organization-Id"] = org_id
    student_data["headers"]["X-Organization-Id"] = org_id

    ws_res = await client.get("/api/v1/workspaces", headers=owner_data["headers"])
    workspace_id = ws_res.json()[0]["workspace_id"]

    roles_res = await client.get("/api/v1/organizations/roles", headers=owner_data["headers"])
    roles_data = roles_res.json()
    teacher_role_id = next(r["role_id"] for r in roles_data if r["role_name"] == "Teacher")
    student_role_id = next(r["role_id"] for r in roles_data if r["role_name"] == "Student")

    await client.post("/api/v1/organizations/members", json={
        "email": "late_teacher@test.com",
        "first_name": "Teacher",
        "last_name": "User",
        "role_id": teacher_role_id,
        "workspace_ids": [workspace_id]
    }, headers=owner_data["headers"])
    await client.post("/api/v1/organizations/members", json={
        "email": "late_student@test.com",
        "first_name": "Student",
        "last_name": "User",
        "role_id": student_role_id,
        "workspace_ids": [workspace_id]
    }, headers=owner_data["headers"])

    sub_res = await client.post("/api/v1/subjects", json={
        "workspace_id": workspace_id,
        "subject_name": "Physics",
        "subject_description": "Mechanics."
    }, headers=owner_data["headers"])
    subject_id = sub_res.json()["subject_id"]

    await client.post(
        f"/api/v1/subjects/{subject_id}/teachers?workspace_id={workspace_id}",
        json={"user_id": str(teacher_data["user"].user_id)},
        headers=owner_data["headers"]
    )

    # Create assignment with valid future due date
    future_due = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    create_res = await client.post("/api/v1/assignments", json={
        "subject_id": subject_id,
        "title": "Lab Report 1",
        "description": "Due tomorrow.",
        "due_at": future_due
    }, headers=teacher_data["headers"])
    assert create_res.status_code == 201
    assignment_id = create_res.json()["assignment_id"]

    await client.post(f"/api/v1/assignments/{assignment_id}/publish?subject_id={subject_id}", headers=teacher_data["headers"])

    # Simulate past due date in DB
    from app.modules.assignments.models import Assignment
    assign_obj = await db_session.get(Assignment, uuid.UUID(assignment_id))
    assign_obj.assignment_due_at = datetime.now(timezone.utc) - timedelta(hours=2)
    db_session.add(assign_obj)
    await db_session.commit()

    # Student submits after due date -> status should be 'late'
    submit_res = await client.post(
        f"/api/v1/assignments/{assignment_id}/submit",
        json={"files": []},
        headers=student_data["headers"]
    )
    assert submit_res.status_code == 200
    assert submit_res.json()["submission_status"] == "late"
