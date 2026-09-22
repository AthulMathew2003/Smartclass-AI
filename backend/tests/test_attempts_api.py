import pytest
import uuid
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy import select

from app.modules.users.service import UserService
from app.modules.organizations.member_service import MemberService
from app.modules.organizations.models import Organization, Role, WorkspaceMember
from app.modules.organizations.member_schemas import MemberCreateRequest


async def setup_test_users_and_org(client: AsyncClient, db_session):
    """Helper to bootstrap users, organization, roles, workspace, and tokens."""
    user_service = UserService(db_session)
    owner = await user_service.create_user(email="api_att_owner@test.com", password="Password123!", first_name="Owner", last_name="User")
    teacher = await user_service.create_user(email="api_att_teacher@test.com", password="Password123!", first_name="Teacher", last_name="User")
    student = await user_service.create_user(email="api_att_student@test.com", password="Password123!", first_name="Student", last_name="User")
    await db_session.commit()

    # Login owner
    login_res = await client.post("/api/v1/auth/login", json={"email": "api_att_owner@test.com", "password": "Password123!"})
    owner_token = login_res.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # Onboard Org
    onboard_payload = {
        "org_name": "Attempt API Academy",
        "org_slug": "attempt-api-acad",
        "org_type": "School",
        "org_country": "USA",
        "org_state": "CA",
        "org_city": "SF",
        "org_timezone": "America/Los_Angeles",
        "owner_first_name": "Owner",
        "owner_last_name": "User",
        "owner_phone": "1234567890",
        "workspace_name": "Main WS"
    }
    await client.post("/api/v1/organizations/onboarding", json=onboard_payload, headers=owner_headers)
    await db_session.commit()

    org_res = await db_session.execute(select(Organization).where(Organization.organization_slug == "attempt-api-acad"))
    org = org_res.scalars().first()
    owner_headers["X-Organization-Id"] = str(org.organization_id)

    roles_res = await db_session.execute(select(Role).where(Role.role_is_system == True))
    roles_by_name = {r.role_name: r.role_id for r in roles_res.scalars().all()}

    # Add members to Org
    member_service = MemberService(db_session)
    await member_service.create_member(org.organization_id, MemberCreateRequest(
        email="api_att_teacher@test.com", first_name="Teacher", last_name="User", role_id=roles_by_name["Teacher"], workspace_ids=[]
    ))
    await member_service.create_member(org.organization_id, MemberCreateRequest(
        email="api_att_student@test.com", first_name="Student", last_name="User", role_id=roles_by_name["Student"], workspace_ids=[]
    ))
    await db_session.commit()

    login_t = await client.post("/api/v1/auth/login", json={"email": "api_att_teacher@test.com", "password": "Password123!"})
    teacher_headers = {"Authorization": f"Bearer {login_t.json()['access_token']}", "X-Organization-Id": str(org.organization_id)}

    login_s = await client.post("/api/v1/auth/login", json={"email": "api_att_student@test.com", "password": "Password123!"})
    student_headers = {"Authorization": f"Bearer {login_s.json()['access_token']}", "X-Organization-Id": str(org.organization_id)}

    return {
        "org": org,
        "roles": roles_by_name,
        "owner": {"user": owner, "headers": owner_headers},
        "teacher": {"user": teacher, "headers": teacher_headers},
        "student": {"user": student, "headers": student_headers}
    }


@pytest.mark.asyncio
async def test_assessment_attempts_api_flow(client: AsyncClient, db_session):
    """End-to-end API route tests for assessment attempts, answer saves, and submit."""
    data = await setup_test_users_and_org(client, db_session)
    owner = data["owner"]
    teacher = data["teacher"]
    student = data["student"]

    # 1. Get Workspace
    ws_res = await client.get("/api/v1/workspaces", headers=owner["headers"])
    assert ws_res.status_code == 200
    workspace_id = uuid.UUID(ws_res.json()[0]["workspace_id"])

    # Add Teacher & Student to Workspace
    db_session.add(WorkspaceMember(
        workspace_member_workspace_id=workspace_id,
        workspace_member_user_id=teacher["user"].user_id,
        workspace_member_role_id=data["roles"]["Teacher"]
    ))
    db_session.add(WorkspaceMember(
        workspace_member_workspace_id=workspace_id,
        workspace_member_user_id=student["user"].user_id,
        workspace_member_role_id=data["roles"]["Student"]
    ))
    await db_session.commit()

    # 2. Create Subject & Assign Teacher
    subj_res = await client.post(
        "/api/v1/subjects",
        json={"workspace_id": str(workspace_id), "subject_name": "Computer Science"},
        headers=owner["headers"]
    )
    assert subj_res.status_code == 201
    subject_id = subj_res.json()["subject_id"]
    await db_session.commit()

    assign_res = await client.post(
        f"/api/v1/subjects/{subject_id}/teachers?workspace_id={workspace_id}",
        json={"user_id": str(teacher["user"].user_id)},
        headers=owner["headers"]
    )
    assert assign_res.status_code == 201
    await db_session.commit()

    # 3. Teacher creates Question in Question Bank & Assessment
    q_res = await client.post(
        f"/api/v1/subjects/{subject_id}/questions",
        json={
            "question_type": "mcq_single",
            "question_text": "What does CPU stand for?",
            "default_marks": 5.0,
            "question_explanation": "Central Processing Unit",
            "options": [
                {"option_text": "Central Processing Unit", "option_order": 1, "is_correct": True},
                {"option_text": "Computer Power Unit", "option_order": 2, "is_correct": False},
            ]
        },
        headers=teacher["headers"]
    )
    assert q_res.status_code == 201
    q_id = q_res.json()["question_id"]

    asm_res = await client.post(
        "/api/v1/assessments",
        json={
            "subject_id": subject_id,
            "title": "Hardware Quiz",
            "type": "quiz",
            "attempt_limit": 1
        },
        headers=teacher["headers"]
    )
    assert asm_res.status_code == 201
    asm_id = asm_res.json()["assessment_id"]

    # Add question to assessment
    add_q_res = await client.post(
        f"/api/v1/assessments/{asm_id}/questions",
        json={"question_id": q_id, "marks": 5.0, "order": 1},
        headers=teacher["headers"]
    )
    assert add_q_res.status_code == 201
    aq_id = add_q_res.json()["assessment_question_id"]

    # Publish assessment
    pub_res = await client.post(f"/api/v1/assessments/{asm_id}/publish", headers=teacher["headers"])
    assert pub_res.status_code == 200

    # 4. Student starts Attempt
    start_res = await client.post(f"/api/v1/assessments/{asm_id}/start", headers=student["headers"])
    assert start_res.status_code == 200
    att_data = start_res.json()
    attempt_id = att_data["attempt_id"]
    assert att_data["attempt_number"] == 1
    assert att_data["attempt_status"] == "in_progress"
    assert len(att_data["questions"]) == 1

    # Verify options are sanitized
    opt_id = att_data["questions"][0]["options"][0]["option_id"]
    assert "option_is_correct" not in att_data["questions"][0]["options"][0]

    # 5. Student lists attempts
    list_att_res = await client.get(f"/api/v1/assessments/{asm_id}/attempts", headers=student["headers"])
    assert list_att_res.status_code == 200
    assert len(list_att_res.json()) == 1
    assert list_att_res.json()[0]["attempt_status"] == "in_progress"

    # 6. Student saves answer
    ans_res = await client.put(
        f"/api/v1/assessments/{asm_id}/attempts/{attempt_id}/answers/{aq_id}",
        json={"selected_option_id": opt_id},
        headers=student["headers"]
    )
    assert ans_res.status_code == 200
    assert ans_res.json()["status"] == "saved"

    # 7. Student retrieves attempt
    get_att_res = await client.get(
        f"/api/v1/assessments/{asm_id}/attempts/{attempt_id}",
        headers=student["headers"]
    )
    assert get_att_res.status_code == 200
    assert str(aq_id) in get_att_res.json()["answers"]

    # 8. Student submits attempt
    sub_res = await client.post(
        f"/api/v1/assessments/{asm_id}/attempts/{attempt_id}/submit",
        headers=student["headers"]
    )
    assert sub_res.status_code == 200
    assert sub_res.json()["attempt_status"] == "submitted"
    assert sub_res.json()["attempt_submitted_at"] is not None

    # 9. Second start fails due to attempt limit = 1
    second_start = await client.post(f"/api/v1/assessments/{asm_id}/start", headers=student["headers"])
    assert second_start.status_code == 409

    # 10. Student retrieves evaluation result
    res_res = await client.get(
        f"/api/v1/assessments/{asm_id}/attempts/{attempt_id}/result",
        headers=student["headers"]
    )
    assert res_res.status_code == 200
    res_data = res_res.json()
    assert float(res_data["total_marks"]) == 5.0
    assert float(res_data["obtained_marks"]) == 5.0
    assert float(res_data["percentage"]) == 100.0
    assert res_data["status"] == "completed"
    assert res_data["passed"] is True
    assert len(res_data["questions"]) == 1
    assert res_data["questions"][0]["correctness"] == "correct"

    # 11. Teacher lists all assessment results
    t_results_res = await client.get(
        f"/api/v1/assessments/{asm_id}/results",
        headers=teacher["headers"]
    )
    assert t_results_res.status_code == 200
    t_results = t_results_res.json()
    assert len(t_results) == 1
    assert t_results[0]["attempt_id"] == attempt_id
    assert float(t_results[0]["obtained_marks"]) == 5.0

    # 12. Teacher manual grading API
    grade_res = await client.put(
        f"/api/v1/assessments/{asm_id}/attempts/{attempt_id}/questions/{aq_id}/grade",
        json={"marks_awarded": 3.5, "feedback": "Partially credited manually"},
        headers=teacher["headers"]
    )
    assert grade_res.status_code == 200
    recalculated = grade_res.json()
    assert float(recalculated["obtained_marks"]) == 3.5
    assert float(recalculated["percentage"]) == 70.0

