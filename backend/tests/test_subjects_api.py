import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy import select
from app.modules.subjects.models import SubjectStatus
from tests.test_subjects import setup_org_and_users


@pytest.mark.asyncio
async def test_subject_api_crud_and_rbac(client: AsyncClient, db_session, setup_org_and_users):
    """
    Test API endpoints for subjects using the client.
    `setup_org_and_users` provides a dictionary with populated users, org, workspace.
    """
    data = setup_org_and_users
    org_id = str(data["org"].organization_id)
    ws_id = str(data["workspace"].workspace_id)

    # Login Owner
    login_owner = await client.post("/api/v1/auth/login", json={"email": "subj_owner@example.com", "password": "Password123!"})
    token_owner = login_owner.json()["access_token"]
    headers_owner = {"Authorization": f"Bearer {token_owner}", "X-Organization-Id": org_id}

    # Login Teacher 1
    login_t1 = await client.post("/api/v1/auth/login", json={"email": "subj_teacher1@example.com", "password": "Password123!"})
    token_t1 = login_t1.json()["access_token"]
    headers_t1 = {"Authorization": f"Bearer {token_t1}", "X-Organization-Id": org_id}

    # Login Student
    login_s = await client.post("/api/v1/auth/login", json={"email": "subj_student@example.com", "password": "Password123!"})
    token_s = login_s.json()["access_token"]
    headers_s = {"Authorization": f"Bearer {token_s}", "X-Organization-Id": org_id}

    # 1. Test POST /api/v1/subjects -> 201 (Owner has subject.create)
    payload = {
        "workspace_id": ws_id,
        "subject_name": "API AI 101",
        "subject_description": "API Test"
    }
    create_res = await client.post("/api/v1/subjects", json=payload, headers=headers_owner)
    if create_res.status_code != 201:
        print("CREATE FAIL:", create_res.text)
    assert create_res.status_code == 201
    subj_data = create_res.json()
    subj_id = subj_data["subject_id"]

    # 2. Test RBAC: Student cannot create subject -> 403
    payload2 = {
        "workspace_id": ws_id,
        "subject_name": "API DBMS 101"
    }
    create_res_student = await client.post("/api/v1/subjects", json=payload2, headers=headers_s)
    assert create_res_student.status_code == 403

    # 3. Test Teacher can create subject -> 201 (Teacher has subject.create)
    create_res_t1 = await client.post("/api/v1/subjects", json=payload2, headers=headers_t1)
    assert create_res_t1.status_code == 201
    subj2_id = create_res_t1.json()["subject_id"]

    # 4. Test GET /api/v1/subjects list visibility
    # Owner sees 2 (all subjects in workspace)
    res_list_owner = await client.get(f"/api/v1/subjects?workspace_id={ws_id}", headers=headers_owner)
    assert res_list_owner.status_code == 200
    assert len(res_list_owner.json()) == 2

    # Teacher 1 sees all 2 (workspace membership grants access to all subjects)
    res_list_t1 = await client.get(f"/api/v1/subjects?workspace_id={ws_id}", headers=headers_t1)
    assert res_list_t1.status_code == 200
    assert len(res_list_t1.json()) == 2

    # Student sees all 2 (workspace membership = automatic subject access)
    res_list_s = await client.get(f"/api/v1/subjects?workspace_id={ws_id}", headers=headers_s)
    assert res_list_s.status_code == 200
    assert len(res_list_s.json()) == 2

    # 5. Assign Teacher 1 to AI 101
    teacher_payload = {
        "user_id": str(data["teacher1"].user_id)
    }
    add_teacher_res = await client.post(f"/api/v1/subjects/{subj_id}/teachers?workspace_id={ws_id}", json=teacher_payload, headers=headers_owner)
    assert add_teacher_res.status_code == 201

    # 6. Teacher 1 can add Teacher 2 to AI 101 (because Teacher 1 is assigned)
    teacher2_payload = {
        "user_id": str(data["teacher2"].user_id)
    }
    add_t2_res = await client.post(f"/api/v1/subjects/{subj_id}/teachers?workspace_id={ws_id}", json=teacher2_payload, headers=headers_t1)
    assert add_t2_res.status_code == 201

    # Student cannot add teachers -> 403
    add_s_fail = await client.post(f"/api/v1/subjects/{subj_id}/teachers?workspace_id={ws_id}", json=teacher_payload, headers=headers_s)
    assert add_s_fail.status_code == 403

    # 7. Test GET /api/v1/subjects/{id} -> 200 (student can view since workspace member)
    get_subj = await client.get(f"/api/v1/subjects/{subj_id}?workspace_id={ws_id}", headers=headers_s)
    assert get_subj.status_code == 200

    # 8. Test PATCH /api/v1/subjects/{id} -> 200 (by assigned teacher)
    patch_payload = {"subject_name": "API AI 102"}
    patch_res = await client.patch(f"/api/v1/subjects/{subj_id}?workspace_id={ws_id}", json=patch_payload, headers=headers_t1)
    assert patch_res.status_code == 200
    assert patch_res.json()["subject_name"] == "API AI 102"

    # 9. Test Tenant Isolation
    headers_fake_org = {"Authorization": f"Bearer {token_owner}", "X-Organization-Id": str(uuid.uuid4())}
    fail_res = await client.get(f"/api/v1/subjects?workspace_id={ws_id}", headers=headers_fake_org)
    assert fail_res.status_code == 403  # Access denied to this organization

    # 10. Test DELETE /api/v1/subjects/{id} -> archived
    del_res = await client.delete(f"/api/v1/subjects/{subj_id}?workspace_id={ws_id}", headers=headers_owner)
    assert del_res.status_code == 200
    assert del_res.json()["subject_status"] == SubjectStatus.ARCHIVED.value

    # 11. Test GET /api/v1/subjects/{id}/teachers -> list teachers
    teachers_res = await client.get(f"/api/v1/subjects/{subj_id}/teachers?workspace_id={ws_id}", headers=headers_owner)
    assert teachers_res.status_code == 200
    assert len(teachers_res.json()) == 2  # Both teachers still assigned (archive preserves)

    # 12. Test DELETE teacher -> 204
    remove_res = await client.delete(f"/api/v1/subjects/{subj2_id}/teachers/{data['teacher1'].user_id}?workspace_id={ws_id}", headers=headers_owner)
    # subj2 has no teachers assigned, so this should 404
    assert remove_res.status_code == 404

    # Add teacher1 to subj2 then remove
    await client.post(f"/api/v1/subjects/{subj2_id}/teachers?workspace_id={ws_id}", json=teacher_payload, headers=headers_owner)
    remove_res2 = await client.delete(f"/api/v1/subjects/{subj2_id}/teachers/{data['teacher1'].user_id}?workspace_id={ws_id}", headers=headers_owner)
    assert remove_res2.status_code == 204


@pytest.mark.asyncio
async def test_teacher_subject_assignment_permissions(client: AsyncClient, db_session, setup_org_and_users):
    """
    Test teacher assignment RBAC and boundary enforcement:
    1. Assigned teacher can add another teacher to their subject.
    2. Non-assigned teacher cannot add to a subject they don't teach.
    3. Student cannot add/remove teachers.
    4. Admin/Owner can add/remove teachers freely.
    5. Teacher assignment on archived subject rejected.
    6. Teacher must be a workspace member.
    7. Cross-organization manipulation rejected.
    8. Verify Teacher role has subject.teacher.add & subject.teacher.remove.
    """
    data = setup_org_and_users
    org_id = str(data["org"].organization_id)
    ws_id = str(data["workspace"].workspace_id)
    org_obj = data["org"]

    from app.modules.users.service import UserService
    from app.modules.organizations.member_service import MemberService
    from app.modules.organizations.member_schemas import MemberCreateRequest
    from app.modules.organizations.repository import OrganizationRepository
    from app.modules.rbac.constants import SystemRole
    from app.modules.organizations.models import Role
    from app.modules.rbac.models import Permission, RolePermission

    user_svc = UserService(db_session)
    admin_user = await user_svc.create_user(email="subj_admin_step7@example.com", password="Password123!")
    await db_session.commit()

    roles = (await db_session.execute(select(Role).where(Role.role_organization_id.is_(None)))).scalars().all()
    admin_role = next(r for r in roles if r.role_name == SystemRole.ADMIN)

    member_svc = MemberService(db_session)
    await member_svc.create_member(org_obj.organization_id, MemberCreateRequest(
        email=admin_user.user_email, first_name="Admin", last_name="User", role_id=admin_role.role_id, workspace_ids=[]
    ))
    org_repo = OrganizationRepository(db_session)
    await org_repo.create_workspace_member(data["workspace"].workspace_id, admin_user.user_id, admin_role.role_id)
    await db_session.commit()

    # Logins
    login_owner = await client.post("/api/v1/auth/login", json={"email": "subj_owner@example.com", "password": "Password123!"})
    token_owner = login_owner.json()["access_token"]
    headers_owner = {"Authorization": f"Bearer {token_owner}", "X-Organization-Id": org_id}

    login_admin = await client.post("/api/v1/auth/login", json={"email": "subj_admin_step7@example.com", "password": "Password123!"})
    token_admin = login_admin.json()["access_token"]
    headers_admin = {"Authorization": f"Bearer {token_admin}", "X-Organization-Id": org_id}

    login_t1 = await client.post("/api/v1/auth/login", json={"email": "subj_teacher1@example.com", "password": "Password123!"})
    token_t1 = login_t1.json()["access_token"]
    headers_t1 = {"Authorization": f"Bearer {token_t1}", "X-Organization-Id": org_id}

    login_t2 = await client.post("/api/v1/auth/login", json={"email": "subj_teacher2@example.com", "password": "Password123!"})
    token_t2 = login_t2.json()["access_token"]
    headers_t2 = {"Authorization": f"Bearer {token_t2}", "X-Organization-Id": org_id}

    login_s = await client.post("/api/v1/auth/login", json={"email": "subj_student@example.com", "password": "Password123!"})
    token_s = login_s.json()["access_token"]
    headers_s = {"Authorization": f"Bearer {token_s}", "X-Organization-Id": org_id}

    # Setup Subjects A and B
    res_a = await client.post("/api/v1/subjects", json={"workspace_id": ws_id, "subject_name": "Subject A"}, headers=headers_owner)
    assert res_a.status_code == 201
    subj_a_id = res_a.json()["subject_id"]

    res_b = await client.post("/api/v1/subjects", json={"workspace_id": ws_id, "subject_name": "Subject B"}, headers=headers_owner)
    assert res_b.status_code == 201
    subj_b_id = res_b.json()["subject_id"]

    # Assign Teacher 1 to Subject A
    add_t1 = await client.post(
        f"/api/v1/subjects/{subj_a_id}/teachers?workspace_id={ws_id}",
        json={"user_id": str(data["teacher1"].user_id)},
        headers=headers_owner
    )
    assert add_t1.status_code == 201

    # 1. Teacher 1 (assigned to Subject A) adds Teacher 2 to Subject A -> 201
    res_t1_add_a = await client.post(
        f"/api/v1/subjects/{subj_a_id}/teachers?workspace_id={ws_id}",
        json={"user_id": str(data["teacher2"].user_id)},
        headers=headers_t1
    )
    assert res_t1_add_a.status_code == 201

    # 2. Teacher 1 attempts to add a teacher to Subject B (not assigned to B) -> 403
    res_t1_add_b = await client.post(
        f"/api/v1/subjects/{subj_b_id}/teachers?workspace_id={ws_id}",
        json={"user_id": str(data["teacher2"].user_id)},
        headers=headers_t1
    )
    assert res_t1_add_b.status_code == 403

    # 3. Student cannot add/remove teachers -> 403
    res_s_add = await client.post(
        f"/api/v1/subjects/{subj_a_id}/teachers?workspace_id={ws_id}",
        json={"user_id": str(data["teacher2"].user_id)},
        headers=headers_s
    )
    assert res_s_add.status_code == 403

    res_s_rem = await client.delete(
        f"/api/v1/subjects/{subj_a_id}/teachers/{data['teacher2'].user_id}?workspace_id={ws_id}",
        headers=headers_s
    )
    assert res_s_rem.status_code == 403

    # 4. Admin adds/removes teacher
    res_admin_rem = await client.delete(
        f"/api/v1/subjects/{subj_a_id}/teachers/{data['teacher2'].user_id}?workspace_id={ws_id}",
        headers=headers_admin
    )
    assert res_admin_rem.status_code == 204

    res_admin_add = await client.post(
        f"/api/v1/subjects/{subj_a_id}/teachers?workspace_id={ws_id}",
        json={"user_id": str(data["teacher2"].user_id)},
        headers=headers_admin
    )
    assert res_admin_add.status_code == 201

    # Owner removes
    res_owner_rem = await client.delete(
        f"/api/v1/subjects/{subj_a_id}/teachers/{data['teacher2'].user_id}?workspace_id={ws_id}",
        headers=headers_owner
    )
    assert res_owner_rem.status_code == 204

    # 5. Archive Subject A -> teacher assignment should fail
    await client.delete(f"/api/v1/subjects/{subj_a_id}?workspace_id={ws_id}", headers=headers_owner)
    res_t1_add_archived = await client.post(
        f"/api/v1/subjects/{subj_a_id}/teachers?workspace_id={ws_id}",
        json={"user_id": str(data["teacher2"].user_id)},
        headers=headers_owner
    )
    assert res_t1_add_archived.status_code == 403

    # 6. Non-workspace-member teacher assignment -> 403
    res_non_ws = await client.post(
        f"/api/v1/subjects/{subj_b_id}/teachers?workspace_id={ws_id}",
        json={"user_id": str(data["non_member"].user_id)},
        headers=headers_owner
    )
    assert res_non_ws.status_code == 403

    # 7. Cross-organization manipulation rejected
    fake_org_headers = {"Authorization": f"Bearer {token_t2}", "X-Organization-Id": str(uuid.uuid4())}
    res_cross_org = await client.post(
        f"/api/v1/subjects/{subj_b_id}/teachers?workspace_id={ws_id}",
        json={"user_id": str(data["teacher1"].user_id)},
        headers=fake_org_headers
    )
    assert res_cross_org.status_code == 403

    # 8. Verify Teacher permission mapping exists for subject.teacher.add & subject.teacher.remove
    teacher_role_obj = next(r for r in roles if r.role_name == SystemRole.TEACHER)
    stmt = (
        select(Permission.permission_name)
        .join(RolePermission, Permission.permission_id == RolePermission.permission_id)
        .where(RolePermission.role_id == teacher_role_obj.role_id)
    )
    t_perms = (await db_session.execute(stmt)).scalars().all()
    assert t_perms.count("subject.teacher.add") == 1
    assert t_perms.count("subject.teacher.remove") == 1
