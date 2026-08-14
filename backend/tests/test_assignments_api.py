import uuid
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


@pytest.mark.asyncio
async def test_assignment_crud_lifecycle_and_rbac(client: AsyncClient, db_session):
    user_service = UserService(db_session)
    owner_data = await _create_user_and_login(client, user_service, "assign_owner@test.com", "Owner")
    teacher_data = await _create_user_and_login(client, user_service, "assign_teacher@test.com", "Teacher")
    await db_session.commit()

    # 1. Onboard Organization
    onboard_payload = {
        "org_name": "Assignment High",
        "org_slug": "assignment-high",
        "org_type": "School",
        "org_country": "US",
        "org_state": "CA",
        "org_city": "SF",
        "org_timezone": "America/Los_Angeles",
        "owner_first_name": "Owner",
        "owner_last_name": "User",
        "owner_phone": "1234567890",
        "workspace_name": "Grade 11"
    }
    onboard_res = await client.post("/api/v1/organizations/onboarding", json=onboard_payload, headers=owner_data["headers"])
    assert onboard_res.status_code == 200
    await db_session.commit()

    org_res = await client.get("/api/v1/organizations/memberships", headers=owner_data["headers"])
    org_id = org_res.json()[0]["organization_id"]
    owner_data["headers"]["X-Organization-Id"] = org_id

    # Fetch workspace
    ws_res = await client.get("/api/v1/workspaces", headers=owner_data["headers"])
    workspace_id = ws_res.json()[0]["workspace_id"]

    # Fetch teacher role
    roles_res = await client.get("/api/v1/organizations/roles", headers=owner_data["headers"])
    roles_data = roles_res.json()
    teacher_role_id = next(r["role_id"] for r in roles_data if r["role_name"] == "Teacher")

    # Add Teacher to Organization & Workspace
    add_teacher_res = await client.post("/api/v1/organizations/members", json={
        "email": "assign_teacher@test.com",
        "first_name": "Teacher",
        "last_name": "User",
        "role_id": teacher_role_id,
        "workspace_ids": [workspace_id]
    }, headers=owner_data["headers"])
    assert add_teacher_res.status_code == 200
    teacher_data["headers"]["X-Organization-Id"] = org_id

    # Create Subject (Math)
    sub_res = await client.post("/api/v1/subjects", json={
        "workspace_id": workspace_id,
        "subject_name": "Calculus AB",
        "subject_description": "Advanced calculus course."
    }, headers=owner_data["headers"])
    assert sub_res.status_code == 201
    subject_id = sub_res.json()["subject_id"]

    # Assign Teacher to Subject (using user_id)
    assign_t_res = await client.post(
        f"/api/v1/subjects/{subject_id}/teachers?workspace_id={workspace_id}",
        json={"user_id": str(teacher_data["user"].user_id)},
        headers=owner_data["headers"]
    )
    assert assign_t_res.status_code == 201

    # 2. Teacher Creates Draft Assignment
    create_assign_payload = {
        "subject_id": subject_id,
        "title": "Limits & Continuity Worksheet",
        "description": "Solve exercises 1-20 from Chapter 2.",
        "status": "draft",
    }
    create_a_res = await client.post("/api/v1/assignments", json=create_assign_payload, headers=teacher_data["headers"])
    assert create_a_res.status_code == 201
    assignment_data = create_a_res.json()
    assert assignment_data["assignment_title"] == "Limits & Continuity Worksheet"
    assert assignment_data["assignment_status"] == "draft"
    assignment_id = assignment_data["assignment_id"]

    # 3. Teacher Lists Assignments
    list_res = await client.get(f"/api/v1/assignments?subject_id={subject_id}", headers=teacher_data["headers"])
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # 4. Teacher Updates Assignment (Publish)
    update_payload = {
        "title": "Limits & Continuity Problem Set",
        "status": "published"
    }
    update_res = await client.patch(
        f"/api/v1/assignments/{assignment_id}?subject_id={subject_id}",
        json=update_payload,
        headers=teacher_data["headers"]
    )
    assert update_res.status_code == 200
    assert update_res.json()["assignment_title"] == "Limits & Continuity Problem Set"
    assert update_res.json()["assignment_status"] == "published"

    # 5. Teacher Archives Assignment (DELETE soft delete)
    delete_res = await client.delete(
        f"/api/v1/assignments/{assignment_id}?subject_id={subject_id}",
        headers=teacher_data["headers"]
    )
    assert delete_res.status_code == 200
    assert delete_res.json()["assignment_status"] == "archived"

    # 6. Attempt to update an archived assignment -> 409 Conflict
    re_update_res = await client.patch(
        f"/api/v1/assignments/{assignment_id}?subject_id={subject_id}",
        json={"title": "Hacked Title"},
        headers=teacher_data["headers"]
    )
    assert re_update_res.status_code == 409


@pytest.mark.asyncio
async def test_teacher_authorization_and_unassigned_teacher(client: AsyncClient, db_session):
    user_service = UserService(db_session)
    owner_data = await _create_user_and_login(client, user_service, "auth_owner@test.com", "Owner")
    teacher1_data = await _create_user_and_login(client, user_service, "teacher_assigned@test.com", "Teacher1")
    teacher2_data = await _create_user_and_login(client, user_service, "teacher_unassigned@test.com", "Teacher2")
    await db_session.commit()

    # Onboard
    await client.post("/api/v1/organizations/onboarding", json={
        "org_name": "Auth Org", "org_slug": "auth-org", "org_type": "School", "org_country": "US", "org_state": "NY", "org_city": "NYC",
        "org_timezone": "UTC", "owner_first_name": "O", "owner_last_name": "O", "owner_phone": "1", "workspace_name": "Room 101"
    }, headers=owner_data["headers"])
    org_res = await client.get("/api/v1/organizations/memberships", headers=owner_data["headers"])
    org_id = org_res.json()[0]["organization_id"]
    owner_data["headers"]["X-Organization-Id"] = org_id
    teacher1_data["headers"]["X-Organization-Id"] = org_id
    teacher2_data["headers"]["X-Organization-Id"] = org_id

    ws_res = await client.get("/api/v1/workspaces", headers=owner_data["headers"])
    workspace_id = ws_res.json()[0]["workspace_id"]

    roles_res = await client.get("/api/v1/organizations/roles", headers=owner_data["headers"])
    teacher_role_id = next(r["role_id"] for r in roles_res.json() if r["role_name"] == "Teacher")

    # Add both teachers to org + workspace
    await client.post("/api/v1/organizations/members", json={
        "email": "teacher_assigned@test.com", "first_name": "T1", "last_name": "U", "role_id": teacher_role_id, "workspace_ids": [workspace_id]
    }, headers=owner_data["headers"])
    await client.post("/api/v1/organizations/members", json={
        "email": "teacher_unassigned@test.com", "first_name": "T2", "last_name": "U", "role_id": teacher_role_id, "workspace_ids": [workspace_id]
    }, headers=owner_data["headers"])

    # Create Subject
    sub_res = await client.post("/api/v1/subjects", json={
        "workspace_id": workspace_id, "subject_name": "Literature"
    }, headers=owner_data["headers"])
    subject_id = sub_res.json()["subject_id"]

    # Assign only Teacher 1 to Literature
    await client.post(
        f"/api/v1/subjects/{subject_id}/teachers?workspace_id={workspace_id}",
        json={"user_id": str(teacher1_data["user"].user_id)},
        headers=owner_data["headers"]
    )

    # Teacher 1 creates assignment -> 201
    t1_create_res = await client.post("/api/v1/assignments", json={
        "subject_id": subject_id, "title": "Essay 1", "status": "published"
    }, headers=teacher1_data["headers"])
    assert t1_create_res.status_code == 201
    assignment_id = t1_create_res.json()["assignment_id"]

    # Teacher 2 attempts to create assignment -> 403 Forbidden
    t2_create_res = await client.post("/api/v1/assignments", json={
        "subject_id": subject_id, "title": "Unauthorized Essay"
    }, headers=teacher2_data["headers"])
    assert t2_create_res.status_code == 403

    # Teacher 2 attempts to update assignment -> 403 Forbidden
    t2_update_res = await client.patch(
        f"/api/v1/assignments/{assignment_id}?subject_id={subject_id}",
        json={"title": "Hacked"},
        headers=teacher2_data["headers"]
    )
    assert t2_update_res.status_code == 403

    # Teacher 2 attempts to delete assignment -> 403 Forbidden
    t2_del_res = await client.delete(
        f"/api/v1/assignments/{assignment_id}?subject_id={subject_id}",
        headers=teacher2_data["headers"]
    )
    assert t2_del_res.status_code == 403


@pytest.mark.asyncio
async def test_student_visibility_and_restrictions(client: AsyncClient, db_session):
    user_service = UserService(db_session)
    owner_data = await _create_user_and_login(client, user_service, "stud_owner@test.com", "Owner")
    teacher_data = await _create_user_and_login(client, user_service, "stud_teacher@test.com", "Teacher")
    student_data = await _create_user_and_login(client, user_service, "stud_student@test.com", "Student")
    await db_session.commit()

    # Onboard
    await client.post("/api/v1/organizations/onboarding", json={
        "org_name": "Student Org", "org_slug": "student-org", "org_type": "School", "org_country": "US", "org_state": "NY", "org_city": "NYC",
        "org_timezone": "UTC", "owner_first_name": "O", "owner_last_name": "O", "owner_phone": "1", "workspace_name": "Grade 9"
    }, headers=owner_data["headers"])
    org_res = await client.get("/api/v1/organizations/memberships", headers=owner_data["headers"])
    org_id = org_res.json()[0]["organization_id"]
    owner_data["headers"]["X-Organization-Id"] = org_id
    teacher_data["headers"]["X-Organization-Id"] = org_id
    student_data["headers"]["X-Organization-Id"] = org_id

    ws_res = await client.get("/api/v1/workspaces", headers=owner_data["headers"])
    workspace_id = ws_res.json()[0]["workspace_id"]

    roles_res = await client.get("/api/v1/organizations/roles", headers=owner_data["headers"])
    teacher_role_id = next(r["role_id"] for r in roles_res.json() if r["role_name"] == "Teacher")
    student_role_id = next(r["role_id"] for r in roles_res.json() if r["role_name"] == "Student")

    # Add teacher and student
    await client.post("/api/v1/organizations/members", json={
        "email": "stud_teacher@test.com", "first_name": "T", "last_name": "T", "role_id": teacher_role_id, "workspace_ids": [workspace_id]
    }, headers=owner_data["headers"])
    await client.post("/api/v1/organizations/members", json={
        "email": "stud_student@test.com", "first_name": "S", "last_name": "S", "role_id": student_role_id, "workspace_ids": [workspace_id]
    }, headers=owner_data["headers"])

    # Create Subject & assign teacher
    sub_res = await client.post("/api/v1/subjects", json={
        "workspace_id": workspace_id, "subject_name": "World History"
    }, headers=owner_data["headers"])
    subject_id = sub_res.json()["subject_id"]
    await client.post(
        f"/api/v1/subjects/{subject_id}/teachers?workspace_id={workspace_id}",
        json={"user_id": str(teacher_data["user"].user_id)},
        headers=owner_data["headers"]
    )

    # Teacher creates 1 draft and 1 published assignment
    draft_res = await client.post("/api/v1/assignments", json={
        "subject_id": subject_id, "title": "Draft Quiz", "status": "draft"
    }, headers=teacher_data["headers"])
    draft_id = draft_res.json()["assignment_id"]

    pub_res = await client.post("/api/v1/assignments", json={
        "subject_id": subject_id, "title": "Ancient Egypt Essay", "status": "published"
    }, headers=teacher_data["headers"])
    pub_id = pub_res.json()["assignment_id"]

    # Student lists assignments -> only sees published assignment
    stud_list_res = await client.get(f"/api/v1/assignments?subject_id={subject_id}", headers=student_data["headers"])
    assert stud_list_res.status_code == 200
    stud_assignments = stud_list_res.json()
    assert len(stud_assignments) == 1
    assert stud_assignments[0]["assignment_title"] == "Ancient Egypt Essay"

    # Student gets draft assignment by ID -> 404 Not Found
    stud_draft_res = await client.get(f"/api/v1/assignments/{draft_id}?subject_id={subject_id}", headers=student_data["headers"])
    assert stud_draft_res.status_code == 404

    # Student gets published assignment by ID -> 200 OK
    stud_pub_res = await client.get(f"/api/v1/assignments/{pub_id}?subject_id={subject_id}", headers=student_data["headers"])
    assert stud_pub_res.status_code == 200
    assert stud_pub_res.json()["assignment_title"] == "Ancient Egypt Essay"

    # Student attempts to create assignment -> 403 Forbidden
    stud_create_res = await client.post("/api/v1/assignments", json={
        "subject_id": subject_id, "title": "Student Created"
    }, headers=student_data["headers"])
    assert stud_create_res.status_code == 403


@pytest.mark.asyncio
async def test_archived_workspace_and_subject_protection(client: AsyncClient, db_session):
    user_service = UserService(db_session)
    owner_data = await _create_user_and_login(client, user_service, "arch_owner@test.com", "Owner")
    await db_session.commit()

    # Onboard
    await client.post("/api/v1/organizations/onboarding", json={
        "org_name": "Archived Test Org", "org_slug": "arch-test-org", "org_type": "School", "org_country": "US", "org_state": "NY", "org_city": "NYC",
        "org_timezone": "UTC", "owner_first_name": "O", "owner_last_name": "O", "owner_phone": "1", "workspace_name": "WS Arch"
    }, headers=owner_data["headers"])
    org_res = await client.get("/api/v1/organizations/memberships", headers=owner_data["headers"])
    org_id = org_res.json()[0]["organization_id"]
    owner_data["headers"]["X-Organization-Id"] = org_id

    ws_res = await client.get("/api/v1/workspaces", headers=owner_data["headers"])
    workspace_id = ws_res.json()[0]["workspace_id"]

    sub_res = await client.post("/api/v1/subjects", json={
        "workspace_id": workspace_id, "subject_name": "Music"
    }, headers=owner_data["headers"])
    subject_id = sub_res.json()["subject_id"]

    # 1. Archive Subject -> assignment creation blocked (409)
    await client.delete(f"/api/v1/subjects/{subject_id}?workspace_id={workspace_id}", headers=owner_data["headers"])
    arch_sub_assign_res = await client.post("/api/v1/assignments", json={
        "subject_id": subject_id, "title": "Piano Exam"
    }, headers=owner_data["headers"])
    assert arch_sub_assign_res.status_code == 409

    # 2. Archive Workspace -> assignment creation blocked (409)
    # Create new subject in active workspace
    sub2_res = await client.post("/api/v1/subjects", json={
        "workspace_id": workspace_id, "subject_name": "Art"
    }, headers=owner_data["headers"])
    subject2_id = sub2_res.json()["subject_id"]

    # Archive workspace
    await client.delete(f"/api/v1/workspaces/{workspace_id}", headers=owner_data["headers"])
    arch_ws_assign_res = await client.post("/api/v1/assignments", json={
        "subject_id": subject2_id, "title": "Painting Project"
    }, headers=owner_data["headers"])
    assert arch_ws_assign_res.status_code == 409
