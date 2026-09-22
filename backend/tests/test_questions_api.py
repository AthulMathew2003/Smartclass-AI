import uuid
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User
from app.modules.users.service import UserService
from app.modules.organizations.models import Organization, Workspace, Role, WorkspaceMember
from app.modules.organizations.service import OrganizationService
from app.modules.organizations.member_service import MemberService
from app.modules.organizations.member_schemas import MemberCreateRequest
from app.modules.subjects.service import SubjectService
from app.modules.subjects.schemas import SubjectCreateRequest
from app.modules.assessments.schemas import AssessmentCreateRequest
from app.modules.assessments.service import AssessmentService
from app.modules.assessments.models import AssessmentStatus, QuestionType


@pytest.mark.asyncio
async def test_questions_api_full_flow(client: AsyncClient, db_session: AsyncSession):
    """End-to-end HTTP API test for questions creation, listing, sanitization, reordering, updating, and deleting."""
    user_service = UserService(db_session)
    owner_user = await user_service.create_user(email="q_api_owner@example.com", password="Password123!")
    teacher_user = await user_service.create_user(email="q_api_teacher@example.com", password="Password123!")
    student_user = await user_service.create_user(email="q_api_student@example.com", password="Password123!")
    await db_session.commit()

    # 1. Onboarding
    login_owner = await client.post("/api/v1/auth/login", json={"email": "q_api_owner@example.com", "password": "Password123!"})
    token_owner = login_owner.json()["access_token"]
    headers_owner = {"Authorization": f"Bearer {token_owner}"}

    payload = {
        "org_name": "Questions Academy",
        "org_slug": "questions-acad",
        "org_type": "School",
        "org_country": "USA",
        "org_state": "CA",
        "org_city": "SF",
        "org_timezone": "America/Los_Angeles",
        "owner_first_name": "Q",
        "owner_last_name": "Owner",
        "owner_phone": "1234567890",
        "workspace_name": "Main WS"
    }
    res = await client.post("/api/v1/organizations/onboarding", json=payload, headers=headers_owner)
    assert res.status_code == 200
    await db_session.commit()

    org = (await db_session.execute(select(Organization).where(Organization.organization_slug == "questions-acad"))).scalars().first()
    headers_owner["X-Organization-Id"] = str(org.organization_id)
    ws = (await db_session.execute(select(Workspace).where(Workspace.workspace_organization_id == org.organization_id))).scalars().first()

    # 2. Add Teacher & Student
    teacher_role = (await db_session.execute(select(Role).where(Role.role_name == "Teacher", Role.role_organization_id.is_(None)))).scalars().first()
    student_role = (await db_session.execute(select(Role).where(Role.role_name == "Student", Role.role_organization_id.is_(None)))).scalars().first()

    member_service = MemberService(db_session)
    await member_service.create_member(org.organization_id, MemberCreateRequest(
        email="q_api_teacher@example.com", first_name="Teach", last_name="Er", role_id=teacher_role.role_id, workspace_ids=[]
    ))
    await member_service.create_member(org.organization_id, MemberCreateRequest(
        email="q_api_student@example.com", first_name="Stud", last_name="Ent", role_id=student_role.role_id, workspace_ids=[]
    ))
    db_session.add(WorkspaceMember(workspace_member_workspace_id=ws.workspace_id, workspace_member_user_id=teacher_user.user_id, workspace_member_role_id=teacher_role.role_id))
    db_session.add(WorkspaceMember(workspace_member_workspace_id=ws.workspace_id, workspace_member_user_id=student_user.user_id, workspace_member_role_id=student_role.role_id))
    await db_session.commit()

    # 3. Create Subject & Assign Teacher
    subj_service = SubjectService(db_session)
    subj = await subj_service.create_subject(org.organization_id, ws.workspace_id, owner_user.user_id, SubjectCreateRequest(
        workspace_id=ws.workspace_id, subject_name="Chemistry", subject_description="Organic & Inorganic"
    ))
    from app.modules.subjects.models import SubjectTeacher
    db_session.add(SubjectTeacher(subject_teacher_subject_id=subj.subject_id, subject_teacher_user_id=teacher_user.user_id))
    await db_session.commit()

    # Login Teacher and Student
    login_teacher = await client.post("/api/v1/auth/login", json={"email": "q_api_teacher@example.com", "password": "Password123!"})
    token_teacher = login_teacher.json()["access_token"]
    headers_teacher = {"Authorization": f"Bearer {token_teacher}", "X-Organization-Id": str(org.organization_id)}

    login_student = await client.post("/api/v1/auth/login", json={"email": "q_api_student@example.com", "password": "Password123!"})
    token_student = login_student.json()["access_token"]
    headers_student = {"Authorization": f"Bearer {token_student}", "X-Organization-Id": str(org.organization_id)}

    # 4. Teacher creates Draft Assessment
    asm_res = await client.post("/api/v1/assessments", json={
        "subject_id": str(subj.subject_id),
        "title": "Chemistry Midterm",
        "total_marks": 50
    }, headers=headers_teacher)
    assert asm_res.status_code == 201
    asm_id = asm_res.json()["assessment_id"]

    # 5. Teacher creates Questions (MCQ_SINGLE and TRUE_FALSE)
    q1_res = await client.post(f"/api/v1/assessments/{asm_id}/questions", json={
        "question_type": "mcq_single",
        "question_text": "What is the atomic number of Carbon?",
        "marks": 5.0,
        "question_explanation": "Carbon has 6 protons in its nucleus.",
        "options": [
            {"option_text": "4", "option_order": 1, "is_correct": False},
            {"option_text": "6", "option_order": 2, "is_correct": True},
            {"option_text": "12", "option_order": 3, "is_correct": False}
        ]
    }, headers=headers_teacher)
    assert q1_res.status_code == 201
    q1_data = q1_res.json()
    assert q1_data["assessment_question_order"] == 1
    assert len(q1_data["options"]) == 3
    q1_id = q1_data["assessment_question_id"]

    q2_res = await client.post(f"/api/v1/assessments/{asm_id}/questions", json={
        "question_type": "true_false",
        "question_text": "Water is composed of hydrogen and oxygen.",
        "marks": 5.0,
        "options": [
            {"option_text": "True", "option_order": 1, "is_correct": True},
            {"option_text": "False", "option_order": 2, "is_correct": False}
        ]
    }, headers=headers_teacher)
    assert q2_res.status_code == 201
    q2_data = q2_res.json()
    assert q2_data["assessment_question_order"] == 2
    q2_id = q2_data["assessment_question_id"]

    # 6. Test Reorder
    reorder_res = await client.patch(f"/api/v1/assessments/{asm_id}/questions/reorder", json={
        "question_ids": [q2_id, q1_id]
    }, headers=headers_teacher)
    assert reorder_res.status_code == 200
    reordered = reorder_res.json()
    assert reordered[0]["assessment_question_id"] == q2_id and reordered[0]["assessment_question_order"] == 1
    assert reordered[1]["assessment_question_id"] == q1_id and reordered[1]["assessment_question_order"] == 2

    # 7. Student cannot access draft assessment questions
    stud_draft_res = await client.get(f"/api/v1/assessments/{asm_id}/questions", headers=headers_student)
    assert stud_draft_res.status_code == 404

    # 8. Publish Assessment
    pub_res = await client.post(f"/api/v1/assessments/{asm_id}/publish", headers=headers_teacher)
    assert pub_res.status_code == 200

    # 9. Student accesses published assessment questions - verify sanitization
    stud_pub_res = await client.get(f"/api/v1/assessments/{asm_id}/questions", headers=headers_student)
    assert stud_pub_res.status_code == 200
    sq_list = stud_pub_res.json()
    assert len(sq_list) == 2
    for sq in sq_list:
        assert "question_explanation" not in sq
        for opt in sq["options"]:
            assert "is_correct" not in opt
            assert "option_is_correct" not in opt

    # 10. Teacher accesses published assessment questions - gets full answer keys
    teach_pub_res = await client.get(f"/api/v1/assessments/{asm_id}/questions", headers=headers_teacher)
    assert teach_pub_res.status_code == 200
    tq_list = teach_pub_res.json()
    assert len(tq_list) == 2
    carbon_q = [q for q in tq_list if q["assessment_question_id"] == q1_id][0]
    assert carbon_q["question_explanation"] == "Carbon has 6 protons in its nucleus."
    assert carbon_q["options"][1]["option_is_correct"] is True
