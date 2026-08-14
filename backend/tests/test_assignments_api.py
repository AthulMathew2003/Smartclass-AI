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
async def test_assignment_crud_and_lifecycle_transitions(client: AsyncClient, db_session):
    user_service = UserService(db_session)
    owner_data = await _create_user_and_login(client, user_service, "lc_owner@test.com", "Owner")
    teacher_data = await _create_user_and_login(client, user_service, "lc_teacher@test.com", "Teacher")
    await db_session.commit()

    # 1. Onboard Organization
    onboard_payload = {
        "org_name": "Lifecycle Academy",
        "org_slug": "lifecycle-acad",
        "org_type": "School",
        "org_country": "US",
        "org_state": "CA",
        "org_city": "SF",
        "org_timezone": "America/Los_Angeles",
        "owner_first_name": "Owner",
        "owner_last_name": "User",
        "owner_phone": "1234567890",
        "workspace_name": "Grade 10"
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
        "email": "lc_teacher@test.com",
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
        "subject_name": "Data Structures",
        "subject_description": "Algorithms and data structures."
    }, headers=owner_data["headers"])
    assert sub_res.status_code == 201
    subject_id = sub_res.json()["subject_id"]

    # Assign Teacher to Subject
    assign_t_res = await client.post(
        f"/api/v1/subjects/{subject_id}/teachers?workspace_id={workspace_id}",
        json={"user_id": str(teacher_data["user"].user_id)},
        headers=owner_data["headers"]
    )
    assert assign_t_res.status_code == 201

    # 2. Create Assignment -> starts as DRAFT
    create_assign_payload = {
        "subject_id": subject_id,
        "title": "Binary Trees Assignment",
        "description": "Implement AVL and Red-Black tree rotations.",
        "due_at": "2026-09-01T23:59:00Z"
    }
    create_a_res = await client.post("/api/v1/assignments", json=create_assign_payload, headers=teacher_data["headers"])
    assert create_a_res.status_code == 201
    assignment_data = create_a_res.json()
    assert assignment_data["assignment_title"] == "Binary Trees Assignment"
    assert assignment_data["assignment_status"] == "draft"
    assignment_id = assignment_data["assignment_id"]

    # 3. Update Assignment Metadata
    update_res = await client.patch(
        f"/api/v1/assignments/{assignment_id}?subject_id={subject_id}",
        json={"title": "Self-Balancing Trees Assignment"},
        headers=teacher_data["headers"]
    )
    assert update_res.status_code == 200
    assert update_res.json()["assignment_title"] == "Self-Balancing Trees Assignment"

    # Cannot close a draft assignment -> 409
    bad_close = await client.post(f"/api/v1/assignments/{assignment_id}/close?subject_id={subject_id}", headers=teacher_data["headers"])
    assert bad_close.status_code == 409

    # 4. Publish Assignment (DRAFT -> PUBLISHED)
    pub_res = await client.post(f"/api/v1/assignments/{assignment_id}/publish?subject_id={subject_id}", headers=teacher_data["headers"])
    assert pub_res.status_code == 200
    assert pub_res.json()["assignment_status"] == "published"

    # Cannot re-publish already published assignment -> 409
    dup_pub = await client.post(f"/api/v1/assignments/{assignment_id}/publish?subject_id={subject_id}", headers=teacher_data["headers"])
    assert dup_pub.status_code == 409

    # 5. Close Assignment (PUBLISHED -> CLOSED)
    close_res = await client.post(f"/api/v1/assignments/{assignment_id}/close?subject_id={subject_id}", headers=teacher_data["headers"])
    assert close_res.status_code == 200
    assert close_res.json()["assignment_status"] == "closed"

    # Cannot re-close already closed assignment -> 409
    dup_close = await client.post(f"/api/v1/assignments/{assignment_id}/close?subject_id={subject_id}", headers=teacher_data["headers"])
    assert dup_close.status_code == 409

    # Cannot publish a closed assignment directly -> 409
    bad_pub = await client.post(f"/api/v1/assignments/{assignment_id}/publish?subject_id={subject_id}", headers=teacher_data["headers"])
    assert bad_pub.status_code == 409

    # 6. Archive Assignment (CLOSED -> ARCHIVED)
    archive_res = await client.delete(f"/api/v1/assignments/{assignment_id}?subject_id={subject_id}", headers=teacher_data["headers"])
    assert archive_res.status_code == 200
    assert archive_res.json()["assignment_status"] == "archived"

    # Cannot re-archive already archived assignment -> 409
    dup_archive = await client.delete(f"/api/v1/assignments/{assignment_id}?subject_id={subject_id}", headers=teacher_data["headers"])
    assert dup_archive.status_code == 409

    # Cannot mutate, publish, or close archived assignment -> 409
    assert (await client.patch(f"/api/v1/assignments/{assignment_id}?subject_id={subject_id}", json={"title": "Test"}, headers=teacher_data["headers"])).status_code == 409
    assert (await client.post(f"/api/v1/assignments/{assignment_id}/publish?subject_id={subject_id}", headers=teacher_data["headers"])).status_code == 409
    assert (await client.post(f"/api/v1/assignments/{assignment_id}/close?subject_id={subject_id}", headers=teacher_data["headers"])).status_code == 409


@pytest.mark.asyncio
async def test_teacher_lifecycle_rbac_and_unassigned_teacher(client: AsyncClient, db_session):
    user_service = UserService(db_session)
    owner_data = await _create_user_and_login(client, user_service, "t_owner@test.com", "Owner")
    teacher1_data = await _create_user_and_login(client, user_service, "t_assigned@test.com", "Teacher1")
    teacher2_data = await _create_user_and_login(client, user_service, "t_unassigned@test.com", "Teacher2")
    await db_session.commit()

    # Onboard
    await client.post("/api/v1/organizations/onboarding", json={
        "org_name": "RBAC Org", "org_slug": "rbac-org", "org_type": "School", "org_country": "US", "org_state": "NY", "org_city": "NYC",
        "org_timezone": "UTC", "owner_first_name": "O", "owner_last_name": "O", "owner_phone": "1", "workspace_name": "WS 1"
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

    # Add both teachers
    await client.post("/api/v1/organizations/members", json={
        "email": "t_assigned@test.com", "first_name": "T1", "last_name": "U", "role_id": teacher_role_id, "workspace_ids": [workspace_id]
    }, headers=owner_data["headers"])
    await client.post("/api/v1/organizations/members", json={
        "email": "t_unassigned@test.com", "first_name": "T2", "last_name": "U", "role_id": teacher_role_id, "workspace_ids": [workspace_id]
    }, headers=owner_data["headers"])

    # Create Subject & assign Teacher 1
    sub_res = await client.post("/api/v1/subjects", json={
        "workspace_id": workspace_id, "subject_name": "Operating Systems"
    }, headers=owner_data["headers"])
    subject_id = sub_res.json()["subject_id"]
    await client.post(
        f"/api/v1/subjects/{subject_id}/teachers?workspace_id={workspace_id}",
        json={"user_id": str(teacher1_data["user"].user_id)},
        headers=owner_data["headers"]
    )

    # Teacher 1 creates assignment
    create_res = await client.post("/api/v1/assignments", json={
        "subject_id": subject_id, "title": "Memory Management Lab"
    }, headers=teacher1_data["headers"])
    assert create_res.status_code == 201
    assignment_id = create_res.json()["assignment_id"]

    # Teacher 2 (unassigned) blocked on publish, close, archive
    assert (await client.post(f"/api/v1/assignments/{assignment_id}/publish?subject_id={subject_id}", headers=teacher2_data["headers"])).status_code == 403
    assert (await client.post(f"/api/v1/assignments/{assignment_id}/close?subject_id={subject_id}", headers=teacher2_data["headers"])).status_code == 403
    assert (await client.delete(f"/api/v1/assignments/{assignment_id}?subject_id={subject_id}", headers=teacher2_data["headers"])).status_code == 403

    # Owner can publish, close, archive
    assert (await client.post(f"/api/v1/assignments/{assignment_id}/publish?subject_id={subject_id}", headers=owner_data["headers"])).status_code == 200
    assert (await client.post(f"/api/v1/assignments/{assignment_id}/close?subject_id={subject_id}", headers=owner_data["headers"])).status_code == 200
    assert (await client.delete(f"/api/v1/assignments/{assignment_id}?subject_id={subject_id}", headers=owner_data["headers"])).status_code == 200


@pytest.mark.asyncio
async def test_student_visibility_and_status_filtering(client: AsyncClient, db_session):
    user_service = UserService(db_session)
    owner_data = await _create_user_and_login(client, user_service, "filt_owner@test.com", "Owner")
    teacher_data = await _create_user_and_login(client, user_service, "filt_teacher@test.com", "Teacher")
    student_data = await _create_user_and_login(client, user_service, "filt_student@test.com", "Student")
    await db_session.commit()

    # Onboard
    await client.post("/api/v1/organizations/onboarding", json={
        "org_name": "Filter Org", "org_slug": "filter-org", "org_type": "School", "org_country": "US", "org_state": "NY", "org_city": "NYC",
        "org_timezone": "UTC", "owner_first_name": "O", "owner_last_name": "O", "owner_phone": "1", "workspace_name": "Grade 12"
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
        "email": "filt_teacher@test.com", "first_name": "T", "last_name": "T", "role_id": teacher_role_id, "workspace_ids": [workspace_id]
    }, headers=owner_data["headers"])
    await client.post("/api/v1/organizations/members", json={
        "email": "filt_student@test.com", "first_name": "S", "last_name": "S", "role_id": student_role_id, "workspace_ids": [workspace_id]
    }, headers=owner_data["headers"])

    # Create Subject & assign teacher
    sub_res = await client.post("/api/v1/subjects", json={
        "workspace_id": workspace_id, "subject_name": "Database Systems"
    }, headers=owner_data["headers"])
    subject_id = sub_res.json()["subject_id"]
    await client.post(
        f"/api/v1/subjects/{subject_id}/teachers?workspace_id={workspace_id}",
        json={"user_id": str(teacher_data["user"].user_id)},
        headers=owner_data["headers"]
    )

    # Teacher creates:
    # 1. Draft assignment
    # 2. Published assignment
    # 3. Closed assignment
    # 4. Archived assignment
    d_res = await client.post("/api/v1/assignments", json={"subject_id": subject_id, "title": "Draft Lab"}, headers=teacher_data["headers"])
    d_id = d_res.json()["assignment_id"]

    p_res = await client.post("/api/v1/assignments", json={"subject_id": subject_id, "title": "SQL Queries"}, headers=teacher_data["headers"])
    p_id = p_res.json()["assignment_id"]
    await client.post(f"/api/v1/assignments/{p_id}/publish?subject_id={subject_id}", headers=teacher_data["headers"])

    c_res = await client.post("/api/v1/assignments", json={"subject_id": subject_id, "title": "ER Diagrams"}, headers=teacher_data["headers"])
    c_id = c_res.json()["assignment_id"]
    await client.post(f"/api/v1/assignments/{c_id}/publish?subject_id={subject_id}", headers=teacher_data["headers"])
    await client.post(f"/api/v1/assignments/{c_id}/close?subject_id={subject_id}", headers=teacher_data["headers"])

    a_res = await client.post("/api/v1/assignments", json={"subject_id": subject_id, "title": "Old Homework"}, headers=teacher_data["headers"])
    a_id = a_res.json()["assignment_id"]
    await client.delete(f"/api/v1/assignments/{a_id}?subject_id={subject_id}", headers=teacher_data["headers"])

    # ── Teacher View ──
    # Default list -> includes all 4
    t_all = (await client.get(f"/api/v1/assignments?subject_id={subject_id}", headers=teacher_data["headers"])).json()
    assert len(t_all) == 4

    # Teacher filter by draft -> 1
    t_drafts = (await client.get(f"/api/v1/assignments?subject_id={subject_id}&status=draft", headers=teacher_data["headers"])).json()
    assert len(t_drafts) == 1
    assert t_drafts[0]["assignment_id"] == d_id

    # Teacher filter by published -> 1
    t_pub = (await client.get(f"/api/v1/assignments?subject_id={subject_id}&status=published", headers=teacher_data["headers"])).json()
    assert len(t_pub) == 1
    assert t_pub[0]["assignment_id"] == p_id

    # ── Student View ──
    # Default list -> sees only published (1) and closed (1) = 2
    s_all = (await client.get(f"/api/v1/assignments?subject_id={subject_id}", headers=student_data["headers"])).json()
    assert len(s_all) == 2
    assert set(a["assignment_id"] for a in s_all) == {p_id, c_id}

    # Student requests drafts filter -> gets empty list []
    s_drafts = (await client.get(f"/api/v1/assignments?subject_id={subject_id}&status=draft", headers=student_data["headers"])).json()
    assert len(s_drafts) == 0

    # Student requests archived filter -> gets empty list []
    s_arch = (await client.get(f"/api/v1/assignments?subject_id={subject_id}&status=archived", headers=student_data["headers"])).json()
    assert len(s_arch) == 0

    # Student requests published filter -> gets 1
    s_pub = (await client.get(f"/api/v1/assignments?subject_id={subject_id}&status=published", headers=student_data["headers"])).json()
    assert len(s_pub) == 1
    assert s_pub[0]["assignment_id"] == p_id

    # Direct ID access
    assert (await client.get(f"/api/v1/assignments/{d_id}?subject_id={subject_id}", headers=student_data["headers"])).status_code == 404
    assert (await client.get(f"/api/v1/assignments/{a_id}?subject_id={subject_id}", headers=student_data["headers"])).status_code == 404
    assert (await client.get(f"/api/v1/assignments/{p_id}?subject_id={subject_id}", headers=student_data["headers"])).status_code == 200
    assert (await client.get(f"/api/v1/assignments/{c_id}?subject_id={subject_id}", headers=student_data["headers"])).status_code == 200


@pytest.mark.asyncio
async def test_idor_bola_tenant_workspace_isolation(client: AsyncClient, db_session):
    user_service = UserService(db_session)
    owner_a = await _create_user_and_login(client, user_service, "idor_a@test.com", "OwnerA")
    owner_b = await _create_user_and_login(client, user_service, "idor_b@test.com", "OwnerB")
    await db_session.commit()

    # Onboard Org A
    await client.post("/api/v1/organizations/onboarding", json={
        "org_name": "Org A", "org_slug": "org-a", "org_type": "School", "org_country": "US", "org_state": "CA", "org_city": "SF",
        "org_timezone": "UTC", "owner_first_name": "A", "owner_last_name": "A", "owner_phone": "1", "workspace_name": "WS A"
    }, headers=owner_a["headers"])
    org_a_id = (await client.get("/api/v1/organizations/memberships", headers=owner_a["headers"])).json()[0]["organization_id"]
    owner_a["headers"]["X-Organization-Id"] = org_a_id
    ws_a_id = (await client.get("/api/v1/workspaces", headers=owner_a["headers"])).json()[0]["workspace_id"]

    sub_a_res = await client.post("/api/v1/subjects", json={"workspace_id": ws_a_id, "subject_name": "Subject A"}, headers=owner_a["headers"])
    sub_a_id = sub_a_res.json()["subject_id"]

    assign_a_res = await client.post("/api/v1/assignments", json={"subject_id": sub_a_id, "title": "Assignment A"}, headers=owner_a["headers"])
    assign_a_id = assign_a_res.json()["assignment_id"]

    # Onboard Org B
    await client.post("/api/v1/organizations/onboarding", json={
        "org_name": "Org B", "org_slug": "org-b", "org_type": "School", "org_country": "US", "org_state": "CA", "org_city": "SF",
        "org_timezone": "UTC", "owner_first_name": "B", "owner_last_name": "B", "owner_phone": "1", "workspace_name": "WS B"
    }, headers=owner_b["headers"])
    org_b_id = (await client.get("/api/v1/organizations/memberships", headers=owner_b["headers"])).json()[0]["organization_id"]
    owner_b["headers"]["X-Organization-Id"] = org_b_id

    # 1. User from Org B attempts to access Assignment A -> 403 / 404
    assert (await client.get(f"/api/v1/assignments/{assign_a_id}?subject_id={sub_a_id}", headers=owner_b["headers"])).status_code in (403, 404)
    assert (await client.patch(f"/api/v1/assignments/{assign_a_id}?subject_id={sub_a_id}", json={"title": "Hacked"}, headers=owner_b["headers"])).status_code in (403, 404)
    assert (await client.post(f"/api/v1/assignments/{assign_a_id}/publish?subject_id={sub_a_id}", headers=owner_b["headers"])).status_code in (403, 404)
    assert (await client.delete(f"/api/v1/assignments/{assign_a_id}?subject_id={sub_a_id}", headers=owner_b["headers"])).status_code in (403, 404)

    # 2. Access Assignment A with mismatched / foreign subject_id -> 404
    random_sub_id = str(uuid.uuid4())
    assert (await client.get(f"/api/v1/assignments/{assign_a_id}?subject_id={random_sub_id}", headers=owner_a["headers"])).status_code == 404
