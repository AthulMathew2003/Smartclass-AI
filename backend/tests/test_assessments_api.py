import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient

from app.modules.users.service import UserService
from app.modules.organizations.member_service import MemberService
from app.modules.organizations.models import Organization, Role
from app.modules.organizations.member_schemas import MemberCreateRequest
from sqlalchemy import select


async def setup_test_users_and_org(client: AsyncClient, db_session):
    """Helper to bootstrap users, organization, roles, workspace, and tokens."""
    user_service = UserService(db_session)
    owner = await user_service.create_user(email="api_owner@test.com", password="Password123!", first_name="Owner", last_name="User")
    teacher = await user_service.create_user(email="api_teacher@test.com", password="Password123!", first_name="Teacher", last_name="User")
    unassigned = await user_service.create_user(email="api_unassigned@test.com", password="Password123!", first_name="Unassigned", last_name="Teacher")
    student = await user_service.create_user(email="api_student@test.com", password="Password123!", first_name="Student", last_name="User")
    await db_session.commit()

    # Login owner
    login_res = await client.post("/api/v1/auth/login", json={"email": "api_owner@test.com", "password": "Password123!"})
    owner_token = login_res.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # Onboard Org
    onboard_payload = {
        "org_name": "Assessment API Academy",
        "org_slug": "assess-api-acad",
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

    org_res = await db_session.execute(select(Organization).where(Organization.organization_slug == "assess-api-acad"))
    org = org_res.scalars().first()
    owner_headers["X-Organization-Id"] = str(org.organization_id)

    roles_res = await db_session.execute(select(Role).where(Role.role_is_system == True))
    roles_by_name = {r.role_name: r.role_id for r in roles_res.scalars().all()}

    # Add members to Org
    member_service = MemberService(db_session)
    await member_service.create_member(org.organization_id, MemberCreateRequest(
        email="api_teacher@test.com", first_name="Teacher", last_name="User", role_id=roles_by_name["Teacher"], workspace_ids=[]
    ))
    await member_service.create_member(org.organization_id, MemberCreateRequest(
        email="api_unassigned@test.com", first_name="Unassigned", last_name="User", role_id=roles_by_name["Teacher"], workspace_ids=[]
    ))
    await member_service.create_member(org.organization_id, MemberCreateRequest(
        email="api_student@test.com", first_name="Student", last_name="User", role_id=roles_by_name["Student"], workspace_ids=[]
    ))
    await db_session.commit()

    # Logins
    login_t = await client.post("/api/v1/auth/login", json={"email": "api_teacher@test.com", "password": "Password123!"})
    teacher_headers = {"Authorization": f"Bearer {login_t.json()['access_token']}", "X-Organization-Id": str(org.organization_id)}

    login_u = await client.post("/api/v1/auth/login", json={"email": "api_unassigned@test.com", "password": "Password123!"})
    unassigned_headers = {"Authorization": f"Bearer {login_u.json()['access_token']}", "X-Organization-Id": str(org.organization_id)}

    login_s = await client.post("/api/v1/auth/login", json={"email": "api_student@test.com", "password": "Password123!"})
    student_headers = {"Authorization": f"Bearer {login_s.json()['access_token']}", "X-Organization-Id": str(org.organization_id)}

    return {
        "org": org,
        "roles": roles_by_name,
        "owner": {"user": owner, "headers": owner_headers},
        "teacher": {"user": teacher, "headers": teacher_headers},
        "unassigned": {"user": unassigned, "headers": unassigned_headers},
        "student": {"user": student, "headers": student_headers}
    }


@pytest.mark.asyncio
async def test_assessments_api_builder_and_question_bank_flow(client: AsyncClient, db_session):
    """Full API integration test: Question Bank CRUD, Assessment Builder, Snapshots, Student Sanitization, and RBAC."""
    data = await setup_test_users_and_org(client, db_session)
    owner = data["owner"]
    teacher = data["teacher"]
    unassigned = data["unassigned"]
    student = data["student"]

    # 1. Get Workspace
    ws_res = await client.get("/api/v1/workspaces", headers=owner["headers"])
    assert ws_res.status_code == 200
    workspace_id = uuid.UUID(ws_res.json()[0]["workspace_id"])

    # Add Teacher & Student to Workspace
    from app.modules.organizations.models import WorkspaceMember
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
        json={"workspace_id": str(workspace_id), "subject_name": "History 101"},
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

    # 3. Create Questions in Subject Question Bank
    bank_q1_res = await client.post(
        f"/api/v1/subjects/{subject_id}/questions",
        json={
            "type": "mcq_single",
            "text": "When did World War II end?",
            "default_marks": 5.0,
            "explanation": "WWII ended in 1945.",
            "options": [
                {"text": "1940", "order": 1, "is_correct": False},
                {"text": "1945", "order": 2, "is_correct": True},
                {"text": "1950", "order": 3, "is_correct": False}
            ]
        },
        headers=teacher["headers"]
    )
    assert bank_q1_res.status_code == 201
    bank_q1_id = bank_q1_res.json()["question_id"]

    bank_q2_res = await client.post(
        f"/api/v1/subjects/{subject_id}/questions",
        json={
            "type": "true_false",
            "text": "The Roman Empire fell in 476 AD.",
            "default_marks": 5.0,
            "options": [
                {"text": "True", "order": 1, "is_correct": True},
                {"text": "False", "order": 2, "is_correct": False}
            ]
        },
        headers=teacher["headers"]
    )
    assert bank_q2_res.status_code == 201
    bank_q2_id = bank_q2_res.json()["question_id"]
    await db_session.commit()

    # Unassigned teacher cannot create question in Subject Question Bank -> 403 Forbidden
    unassigned_q_res = await client.post(
        f"/api/v1/subjects/{subject_id}/questions",
        json={
            "type": "short_answer",
            "text": "Who was Napoleon?",
            "default_marks": 5.0
        },
        headers=unassigned["headers"]
    )
    assert unassigned_q_res.status_code == 403

    # 4. Create Draft Assessment
    now = datetime.now(timezone.utc)
    create_payload = {
        "subject_id": subject_id,
        "title": "History Quiz 1",
        "description": "Ancient civilizations and wars",
        "type": "quiz",
        "duration_minutes": 30,
        "start_at": (now + timedelta(hours=1)).isoformat(),
        "end_at": (now + timedelta(hours=2)).isoformat(),
        "passing_marks": 5.0,
        "attempt_limit": 1,
        "randomize_questions": True
    }
    create_res = await client.post("/api/v1/assessments", json=create_payload, headers=teacher["headers"])
    assert create_res.status_code == 201
    assessment_id = create_res.json()["assessment_id"]
    assert create_res.json()["assessment_status"] == "draft"

    # 5. Add Questions from Question Bank to Assessment
    add_q1_res = await client.post(
        f"/api/v1/assessments/{assessment_id}/questions/from-bank",
        json={"question_id": bank_q1_id, "marks": 5.0},
        headers=teacher["headers"]
    )
    assert add_q1_res.status_code == 201
    aq1_id = add_q1_res.json()["assessment_question_id"]
    assert add_q1_res.json()["assessment_question_order"] == 1

    add_q2_res = await client.post(
        f"/api/v1/assessments/{assessment_id}/questions/from-bank",
        json={"question_id": bank_q2_id, "marks": 5.0},
        headers=teacher["headers"]
    )
    assert add_q2_res.status_code == 201
    aq2_id = add_q2_res.json()["assessment_question_id"]
    assert add_q2_res.json()["assessment_question_order"] == 2
    await db_session.commit()

    # Verify total marks auto-calculated on Assessment
    get_assessment_res = await client.get(f"/api/v1/assessments/{assessment_id}", headers=teacher["headers"])
    assert get_assessment_res.status_code == 200
    assert float(get_assessment_res.json()["assessment_total_marks"]) == 10.0
    assert get_assessment_res.json()["total_questions"] == 2

    # 6. Reorder Questions in Assessment
    reorder_res = await client.post(
        f"/api/v1/assessments/{assessment_id}/questions/reorder",
        json={"question_ids": [str(aq2_id), str(aq1_id)]},
        headers=teacher["headers"]
    )
    assert reorder_res.status_code == 200
    assert reorder_res.json()[0]["assessment_question_id"] == str(aq2_id)
    assert reorder_res.json()[0]["assessment_question_order"] == 1
    assert reorder_res.json()[1]["assessment_question_id"] == str(aq1_id)
    assert reorder_res.json()[1]["assessment_question_order"] == 2
    await db_session.commit()

    # 7. Student access check before publish (Draft is hidden)
    student_get_draft = await client.get(f"/api/v1/assessments/{assessment_id}", headers=student["headers"])
    assert student_get_draft.status_code == 404

    # 8. Publish Assessment
    pub_res = await client.post(f"/api/v1/assessments/{assessment_id}/publish", headers=teacher["headers"])
    assert pub_res.status_code == 200
    assert pub_res.json()["assessment_status"] == "published"
    await db_session.commit()

    # 9. Student retrieves published assessment questions -> SANITIZED (no answer keys!)
    student_q_res = await client.get(f"/api/v1/assessments/{assessment_id}/questions", headers=student["headers"])
    assert student_q_res.status_code == 200
    student_questions = student_q_res.json()
    assert len(student_questions) == 2
    for q in student_questions:
        assert "question_explanation" not in q or q.get("question_explanation") is None
        for opt in q["options"]:
            assert "is_correct" not in opt
            assert "option_is_correct" not in opt

    # 10. Teacher receives full assessment questions with correct answers
    teacher_q_res = await client.get(f"/api/v1/assessments/{assessment_id}/questions", headers=teacher["headers"])
    assert teacher_q_res.status_code == 200
    teacher_questions = teacher_q_res.json()
    assert len(teacher_questions) == 2
    for q in teacher_questions:
        assert "options" in q
        for opt in q["options"]:
            assert "option_is_correct" in opt

    # 11. Close Assessment
    close_res = await client.post(f"/api/v1/assessments/{assessment_id}/close", headers=teacher["headers"])
    assert close_res.status_code == 200
    assert close_res.json()["assessment_status"] == "closed"
    await db_session.commit()

    # 12. Archive Assessment
    arch_res = await client.post(f"/api/v1/assessments/{assessment_id}/archive", headers=teacher["headers"])
    assert arch_res.status_code == 200
    assert arch_res.json()["assessment_status"] == "archived"
    await db_session.commit()
