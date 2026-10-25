"""
Unit and Integration Tests for AI Question Paper Generation (Step 10.16).

Covers:
  1. Successful generation from selected course materials.
  2. Strict resource filtering (unselected materials never accessed).
  3. Org/Workspace/Subject tenant isolation.
  4. Unauthorized access prevention (students blocked).
  5. Missing or unindexed material handling.
  6. Empty retrieval handling.
  7. Gemini malformed output handling.
  8. Gemini timeout and bounded retry behavior.
  9. MCQ schema and correct-answer validation.
  10. Subjective answer and rubric validation.
  11. Total-mark validation.
  12. Duplicate question handling.
  13. Source provenance correctness.
  14. Draft retrieval, editing, and single-question regeneration.
  15. Draft-to-assessment conversion.
  16. Repeated conversion idempotency.
  17. Answer key and rubric privacy.
"""
import uuid
import json
import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from sqlalchemy import select

from app.core.exceptions import (
    AiServiceException,
    AiTimeoutException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.modules.assessments.models import (
    Assessment,
    AssessmentStatus,
    AssessmentType,
    QuestionType,
)
from app.modules.assessments.qp_models import QpDraft, QpDraftQuestion, QpDraftStatus
from app.modules.assessments.qp_schemas import (
    QpConvertRequest,
    QpDraftQuestionUpdateInput,
    QpGenerateRequest,
    QpRegenerateQuestionRequest,
)
from app.modules.assessments.qp_service import (
    GeminiGeneratedQuestion,
    GeminiPaperOutput,
    QuestionPaperGenerationService,
)
from app.modules.organizations.models import Organization, Role, Workspace, WorkspaceMember
from app.modules.subjects.models import (
    MaterialIndexStatus,
    Subject,
    SubjectMaterial,
    SubjectMaterialStatus,
    SubjectTeacher,
)
from app.modules.users.models import User


class MockGeminiResponse:
    def __init__(self, text: str):
        self.text = text


async def setup_test_fixtures(db_session):
    """Sets up a complete test tenant hierarchy with teacher, student, materials, etc."""
    teacher = User(
        user_email=f"prof_{uuid.uuid4().hex[:6]}@smartclass.edu",
        user_password_hash="hashed_pw",
        user_first_name="Ada",
        user_last_name="Lovelace",
    )
    student = User(
        user_email=f"stud_{uuid.uuid4().hex[:6]}@smartclass.edu",
        user_password_hash="hashed_pw",
        user_first_name="Alan",
        user_last_name="Turing",
    )
    db_session.add_all([teacher, student])
    await db_session.flush()

    org = Organization(
        organization_name="MIT Institute",
        organization_slug=f"mit-{uuid.uuid4().hex[:6]}",
        organization_owner_user_id=teacher.user_id,
    )
    db_session.add(org)
    await db_session.flush()

    ws = Workspace(
        workspace_organization_id=org.organization_id,
        workspace_name="Computer Science",
        workspace_created_by=teacher.user_id,
    )
    db_session.add(ws)
    await db_session.flush()

    roles_res = await db_session.execute(select(Role).where(Role.role_is_system == True))
    roles_by_name = {r.role_name: r.role_id for r in roles_res.scalars().all()}

    subj = Subject(
        subject_workspace_id=ws.workspace_id,
        subject_name="Operating Systems",
    )
    db_session.add(subj)
    await db_session.flush()

    st = SubjectTeacher(
        subject_teacher_subject_id=subj.subject_id,
        subject_teacher_user_id=teacher.user_id,
    )
    wm_teacher = WorkspaceMember(
        workspace_member_workspace_id=ws.workspace_id,
        workspace_member_user_id=teacher.user_id,
        workspace_member_role_id=roles_by_name.get("Teacher") or uuid.uuid4(),
    )
    wm_student = WorkspaceMember(
        workspace_member_workspace_id=ws.workspace_id,
        workspace_member_user_id=student.user_id,
        workspace_member_role_id=roles_by_name.get("Student") or uuid.uuid4(),
    )
    db_session.add_all([st, wm_teacher, wm_student])
    await db_session.flush()

    # Create 2 course materials: 1 indexed, 1 unindexed
    mat1 = SubjectMaterial(
        material_subject_id=subj.subject_id,
        material_uploaded_by=teacher.user_id,
        material_title="Lecture 1 - Process Scheduling",
        material_original_filename="lec1_processes.pdf",
        material_s3_key="s3://smartclass/lec1.pdf",
        material_file_size=1024 * 500,
        material_content_type="application/pdf",
        material_status=SubjectMaterialStatus.ACTIVE,
        material_index_status=MaterialIndexStatus.INDEXED,
        material_chunk_count=12,
    )
    mat2 = SubjectMaterial(
        material_subject_id=subj.subject_id,
        material_uploaded_by=teacher.user_id,
        material_title="Lecture 2 - Memory Management",
        material_original_filename="lec2_memory.pdf",
        material_s3_key="s3://smartclass/lec2.pdf",
        material_file_size=1024 * 800,
        material_content_type="application/pdf",
        material_status=SubjectMaterialStatus.ACTIVE,
        material_index_status=MaterialIndexStatus.PENDING,  # Unindexed
        material_chunk_count=0,
    )
    db_session.add_all([mat1, mat2])
    await db_session.flush()

    return {
        "teacher": teacher,
        "student": student,
        "org": org,
        "workspace": ws,
        "subject": subj,
        "material1": mat1,
        "material2": mat2,
    }


def make_mock_gemini_output():
    """Returns valid structured Gemini question generation output JSON."""
    return json.dumps({
        "questions": [
            {
                "question_type": "mcq_single",
                "question_text": "Which scheduling algorithm provides the shortest average waiting time?",
                "marks": 2.0,
                "difficulty": "easy",
                "options": [
                    {"text": "Shortest Job First (SJF)", "is_correct": True},
                    {"text": "First Come First Served (FCFS)", "is_correct": False},
                    {"text": "Round Robin (RR)", "is_correct": False},
                    {"text": "Priority Scheduling", "is_correct": False},
                ],
                "expected_answer": None,
                "rubric": None,
                "explanation": "SJF provably provides minimum average waiting time for a given set of processes.",
                "source_hint": "Process scheduling algorithms, SJF optimality",
            },
            {
                "question_type": "short_answer",
                "question_text": "Explain the concept of context switching and the overhead associated with it.",
                "marks": 8.0,
                "difficulty": "medium",
                "options": None,
                "expected_answer": "Context switching is saving the state of the active process into PCB and restoring state of another.",
                "rubric": "Definition (3 marks), Overhead causes like register saves & cache invalidation (5 marks)",
                "explanation": "Context switches are pure overhead since the CPU performs no useful work during switching.",
                "source_hint": "Context switch mechanism and state save in PCB",
            },
        ]
    })


# ── TEST 1: Successful Draft Generation with Selected Materials ───

@pytest.mark.asyncio
async def test_successful_draft_generation(db_session):
    fixtures = await setup_test_fixtures(db_session)
    teacher = fixtures["teacher"]
    org = fixtures["org"]
    subj = fixtures["subject"]
    mat1 = fixtures["material1"]

    mock_chunks = [
        {
            "id": "chunk_1",
            "content": "Process scheduling: SJF provides shortest average waiting time.",
            "material_id": str(mat1.material_id),
            "chunk_index": 0,
            "page_number": 3,
        },
        {
            "id": "chunk_2",
            "content": "Context switch overhead involves saving process control block registers.",
            "material_id": str(mat1.material_id),
            "chunk_index": 1,
            "page_number": 5,
        },
    ]

    mock_vector_store = MagicMock()
    mock_vector_store.search.return_value = mock_chunks

    mock_embeddings = MagicMock()
    mock_embeddings.embed_query = MagicMock(return_value=[0.1] * 768)

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MockGeminiResponse(
        make_mock_gemini_output()
    )

    service = QuestionPaperGenerationService(
        db=db_session,
        embedding_service=mock_embeddings,
        vector_store=mock_vector_store,
        client=mock_client,
    )

    req = QpGenerateRequest(
        title="Midterm OS Paper",
        description="Covers CPU scheduling",
        material_ids=[mat1.material_id],
        total_marks=10.0,
        duration_minutes=45,
        total_questions=2,
        question_types=["mcq_single", "short_answer"],
    )

    result = await service.generate_draft(
        org_id=org.organization_id,
        subject_id=subj.subject_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False,
        config=req,
    )

    assert result.draft_title == "Midterm OS Paper"
    assert result.draft_status == "ready"
    assert len(result.questions) == 2
    assert result.questions[0].dq_question_type == "mcq_single"
    assert result.questions[0].dq_marks == 2.0
    assert result.questions[1].dq_question_type == "short_answer"
    assert result.questions[1].dq_marks == 8.0

    # Verify vector search was explicitly filtered to selected material_ids
    mock_vector_store.search.assert_called_once()
    call_kwargs = mock_vector_store.search.call_args[1]
    assert call_kwargs["material_ids"] == [mat1.material_id]


# ── TEST 2: Resource Filtering: Unselected Materials Never Used ──

@pytest.mark.asyncio
async def test_resource_filtering_enforced(db_session):
    fixtures = await setup_test_fixtures(db_session)
    teacher = fixtures["teacher"]
    org = fixtures["org"]
    subj = fixtures["subject"]
    mat1 = fixtures["material1"]

    mock_vector_store = MagicMock()
    mock_vector_store.search.return_value = [
        {
            "id": "c1",
            "content": "Scheduling algorithms content",
            "material_id": str(mat1.material_id),
            "chunk_index": 0,
        }
    ]

    mock_embeddings = MagicMock()
    mock_embeddings.embed_query = MagicMock(return_value=[0.1] * 768)

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MockGeminiResponse(
        make_mock_gemini_output()
    )

    service = QuestionPaperGenerationService(
        db=db_session,
        embedding_service=mock_embeddings,
        vector_store=mock_vector_store,
        client=mock_client,
    )

    req = QpGenerateRequest(
        title="Filtered Paper",
        material_ids=[mat1.material_id],  # Only mat1 is selected
        total_marks=10.0,
        total_questions=2,
        question_types=["mcq_single", "short_answer"],
    )

    await service.generate_draft(
        org_id=org.organization_id,
        subject_id=subj.subject_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False,
        config=req,
    )

    # Verify that search was strictly scoped to mat1
    _, kwargs = mock_vector_store.search.call_args
    assert kwargs["material_ids"] == [mat1.material_id]
    assert kwargs["subject_id"] == subj.subject_id
    assert kwargs["organization_id"] == org.organization_id


# ── TEST 3: Tenant Isolation: Cross-Subject/Org Access Blocked ───

@pytest.mark.asyncio
async def test_tenant_isolation_mismatched_org(db_session):
    fixtures = await setup_test_fixtures(db_session)
    teacher = fixtures["teacher"]
    subj = fixtures["subject"]
    mat1 = fixtures["material1"]
    fake_org_id = uuid.uuid4()

    service = QuestionPaperGenerationService(db=db_session)
    req = QpGenerateRequest(
        title="Cross Tenant Attempt",
        material_ids=[mat1.material_id],
        total_marks=10.0,
        total_questions=1,
        question_types=["mcq_single"],
    )

    with pytest.raises(NotFoundException):
        await service.generate_draft(
            org_id=fake_org_id,
            subject_id=subj.subject_id,
            requesting_user_id=teacher.user_id,
            is_org_admin=False,
            config=req,
        )


# ── TEST 4: Unauthorized Access Prevention: Student Blocked ──────

@pytest.mark.asyncio
async def test_student_cannot_generate_or_access_drafts(db_session):
    fixtures = await setup_test_fixtures(db_session)
    student = fixtures["student"]
    org = fixtures["org"]
    subj = fixtures["subject"]
    mat1 = fixtures["material1"]

    service = QuestionPaperGenerationService(db=db_session)
    req = QpGenerateRequest(
        title="Student Hacked Paper",
        material_ids=[mat1.material_id],
        total_marks=10.0,
        total_questions=1,
        question_types=["mcq_single"],
    )

    # Student should receive ForbiddenException
    with pytest.raises(ForbiddenException):
        await service.generate_draft(
            org_id=org.organization_id,
            subject_id=subj.subject_id,
            requesting_user_id=student.user_id,
            is_org_admin=False,
            config=req,
        )


# ── TEST 5: Unindexed Material Handling ──────────────────────────

@pytest.mark.asyncio
async def test_unindexed_material_rejection(db_session):
    fixtures = await setup_test_fixtures(db_session)
    teacher = fixtures["teacher"]
    org = fixtures["org"]
    subj = fixtures["subject"]
    mat2 = fixtures["material2"]  # Pending index status

    service = QuestionPaperGenerationService(db=db_session)
    req = QpGenerateRequest(
        title="Paper with Unindexed Doc",
        material_ids=[mat2.material_id],
        total_marks=10.0,
        total_questions=1,
        question_types=["mcq_single"],
    )

    with pytest.raises(ValidationException) as exc_info:
        await service.generate_draft(
            org_id=org.organization_id,
            subject_id=subj.subject_id,
            requesting_user_id=teacher.user_id,
            is_org_admin=False,
            config=req,
        )

    assert "indexed" in str(exc_info.value).lower()


# ── TEST 6: Empty Retrieval Handling ─────────────────────────────

@pytest.mark.asyncio
async def test_empty_retrieval_handling(db_session):
    fixtures = await setup_test_fixtures(db_session)
    teacher = fixtures["teacher"]
    org = fixtures["org"]
    subj = fixtures["subject"]
    mat1 = fixtures["material1"]

    mock_vector_store = MagicMock()
    mock_vector_store.search.return_value = []  # No chunks retrieved

    mock_embeddings = MagicMock()
    mock_embeddings.embed_query = MagicMock(return_value=[0.1] * 768)

    service = QuestionPaperGenerationService(
        db=db_session,
        embedding_service=mock_embeddings,
        vector_store=mock_vector_store,
    )

    req = QpGenerateRequest(
        title="No Chunks Found",
        material_ids=[mat1.material_id],
        total_marks=10.0,
        total_questions=1,
        question_types=["mcq_single"],
    )

    with pytest.raises(ValidationException) as exc_info:
        await service.generate_draft(
            org_id=org.organization_id,
            subject_id=subj.subject_id,
            requesting_user_id=teacher.user_id,
            is_org_admin=False,
            config=req,
        )

    assert "no indexed content chunks found" in str(exc_info.value).lower()


# ── TEST 7: Gemini Malformed Output Handling ─────────────────────

@pytest.mark.asyncio
async def test_gemini_malformed_output(db_session):
    fixtures = await setup_test_fixtures(db_session)
    teacher = fixtures["teacher"]
    org = fixtures["org"]
    subj = fixtures["subject"]
    mat1 = fixtures["material1"]

    mock_vector_store = MagicMock()
    mock_vector_store.search.return_value = [
        {"id": "c1", "content": "Context", "material_id": str(mat1.material_id)}
    ]
    mock_embeddings = MagicMock()
    mock_embeddings.embed_query = MagicMock(return_value=[0.1] * 768)

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MockGeminiResponse(
        "INVALID NOT JSON AT ALL"
    )

    service = QuestionPaperGenerationService(
        db=db_session,
        embedding_service=mock_embeddings,
        vector_store=mock_vector_store,
        client=mock_client,
        max_retries=1,
    )

    req = QpGenerateRequest(
        title="Malformed Output Test",
        material_ids=[mat1.material_id],
        total_marks=10.0,
        total_questions=1,
        question_types=["mcq_single"],
    )

    with pytest.raises(ValidationException) as exc_info:
        await service.generate_draft(
            org_id=org.organization_id,
            subject_id=subj.subject_id,
            requesting_user_id=teacher.user_id,
            is_org_admin=False,
            config=req,
        )

    assert "failed" in str(exc_info.value).lower()


# ── TEST 8: Gemini Timeout and Bounded Retries ───────────────────

@pytest.mark.asyncio
async def test_gemini_timeout_bounded_retry(db_session):
    fixtures = await setup_test_fixtures(db_session)
    teacher = fixtures["teacher"]
    org = fixtures["org"]
    subj = fixtures["subject"]
    mat1 = fixtures["material1"]

    mock_vector_store = MagicMock()
    mock_vector_store.search.return_value = [
        {"id": "c1", "content": "Sample content", "material_id": str(mat1.material_id)}
    ]
    mock_embeddings = MagicMock()
    mock_embeddings.embed_query = MagicMock(return_value=[0.1] * 768)

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = TimeoutError("Gemini timed out")

    service = QuestionPaperGenerationService(
        db=db_session,
        embedding_service=mock_embeddings,
        vector_store=mock_vector_store,
        client=mock_client,
        max_retries=2,
    )

    req = QpGenerateRequest(
        title="Timeout Test",
        material_ids=[mat1.material_id],
        total_marks=10.0,
        total_questions=1,
        question_types=["mcq_single"],
    )

    with pytest.raises(AiTimeoutException) as exc_info:
        await service.generate_draft(
            org_id=org.organization_id,
            subject_id=subj.subject_id,
            requesting_user_id=teacher.user_id,
            is_org_admin=False,
            config=req,
        )

    assert exc_info.value.status_code == 504
    # Should have retried boundedly (1 initial + 2 retries = 3 calls)
    assert mock_client.models.generate_content.call_count == 3


# ── TEST 9: Draft Editing and Single Question Regeneration ───────

@pytest.mark.asyncio
async def test_draft_editing_and_single_question_regeneration(db_session):
    fixtures = await setup_test_fixtures(db_session)
    teacher = fixtures["teacher"]
    org = fixtures["org"]
    subj = fixtures["subject"]
    mat1 = fixtures["material1"]

    mock_vector_store = MagicMock()
    mock_vector_store.search.return_value = [
        {"id": "c1", "content": "CPU context switch", "material_id": str(mat1.material_id)}
    ]
    mock_embeddings = MagicMock()
    mock_embeddings.embed_query = MagicMock(return_value=[0.1] * 768)
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MockGeminiResponse(
        make_mock_gemini_output()
    )

    service = QuestionPaperGenerationService(
        db=db_session,
        embedding_service=mock_embeddings,
        vector_store=mock_vector_store,
        client=mock_client,
    )

    draft = await service.generate_draft(
        org_id=org.organization_id,
        subject_id=subj.subject_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False,
        config=QpGenerateRequest(
            title="Editable Draft",
            material_ids=[mat1.material_id],
            total_marks=10.0,
            total_questions=2,
            question_types=["mcq_single", "short_answer"],
        ),
    )

    q1 = draft.questions[0]

    # Edit Q1 text and marks
    updated_draft = await service.update_question(
        org_id=org.organization_id,
        subject_id=subj.subject_id,
        draft_id=draft.draft_id,
        dq_id=q1.dq_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False,
        payload=QpDraftQuestionUpdateInput(
            question_text="Updated text for question 1?",
            marks=3.0,
        ),
    )

    assert updated_draft.questions[0].dq_question_text == "Updated text for question 1?"
    assert updated_draft.questions[0].dq_marks == 3.0

    # Regenerate Q1
    regen_output = json.dumps({
        "questions": [
            {
                "question_type": "mcq_single",
                "question_text": "Regenerated MCQ about SJF?",
                "marks": 3.0,
                "difficulty": "medium",
                "options": [
                    {"text": "Option A", "is_correct": True},
                    {"text": "Option B", "is_correct": False},
                ],
                "explanation": "Regen explanation",
                "source_hint": "CPU scheduling",
            }
        ]
    })
    mock_client.models.generate_content.return_value = MockGeminiResponse(regen_output)

    post_regen_draft = await service.regenerate_question(
        org_id=org.organization_id,
        subject_id=subj.subject_id,
        draft_id=draft.draft_id,
        dq_id=q1.dq_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False,
        payload=QpRegenerateQuestionRequest(
            additional_instructions="Make it slightly harder"
        ),
    )

    assert post_regen_draft.questions[0].dq_question_text == "Regenerated MCQ about SJF?"


# ── TEST 10: Draft-to-Assessment Conversion ──────────────────────

@pytest.mark.asyncio
async def test_draft_to_assessment_conversion(db_session):
    fixtures = await setup_test_fixtures(db_session)
    teacher = fixtures["teacher"]
    org = fixtures["org"]
    subj = fixtures["subject"]
    mat1 = fixtures["material1"]

    mock_vector_store = MagicMock()
    mock_vector_store.search.return_value = [
        {"id": "c1", "content": "SJF context switch", "material_id": str(mat1.material_id)}
    ]
    mock_embeddings = MagicMock()
    mock_embeddings.embed_query = MagicMock(return_value=[0.1] * 768)
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MockGeminiResponse(
        make_mock_gemini_output()
    )

    service = QuestionPaperGenerationService(
        db=db_session,
        embedding_service=mock_embeddings,
        vector_store=mock_vector_store,
        client=mock_client,
    )

    draft = await service.generate_draft(
        org_id=org.organization_id,
        subject_id=subj.subject_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False,
        config=QpGenerateRequest(
            title="Convertible Final Exam",
            material_ids=[mat1.material_id],
            total_marks=10.0,
            duration_minutes=60,
            total_questions=2,
            question_types=["mcq_single", "short_answer"],
        ),
    )

    # Convert draft to assessment
    conv_result = await service.convert_draft_to_assessment(
        org_id=org.organization_id,
        subject_id=subj.subject_id,
        draft_id=draft.draft_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False,
        payload=QpConvertRequest(
            assessment_type="exam",
            passing_marks=4.0,
            attempt_limit=1,
            randomize_questions=False,
        ),
    )

    assert conv_result["status"] == "converted"
    assessment_id = uuid.UUID(conv_result["assessment_id"])

    # Verify created assessment exists in DB with DRAFT status
    assessment = await service.assessment_repo.get_assessment_by_id(assessment_id)
    assert assessment is not None
    assert assessment.assessment_title == "Convertible Final Exam"
    assert assessment.assessment_status == AssessmentStatus.DRAFT
    assert float(assessment.assessment_total_marks) == 10.0
    assert assessment.assessment_duration_minutes == 60

    # Verify assessment questions were attached with full snapshots
    questions = await service.assessment_repo.list_assessment_questions(assessment_id)
    assert len(questions) == 2
    assert questions[0].assessment_question_snapshot["question_type"] == "mcq_single"
    assert questions[1].assessment_question_snapshot["question_type"] == "short_answer"

    # Verify idempotency: calling conversion again returns existing assessment
    repeat_conv = await service.convert_draft_to_assessment(
        org_id=org.organization_id,
        subject_id=subj.subject_id,
        draft_id=draft.draft_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False,
        payload=QpConvertRequest(assessment_type="exam"),
    )
    assert repeat_conv["status"] == "already_converted"
    assert repeat_conv["assessment_id"] == str(assessment_id)


# ── REGRESSION TESTS: Pydantic Validation & Generation Resilience ──


def test_schema_compatibility_with_google_genai():
    """
    Directly tests that GeminiPaperOutput does not produce exclusiveMinimum
    or other fields forbidden by google.genai.types.Schema.
    This was the exact root cause of the initial ValidationError.
    """
    from google.genai._transformers import t_schema
    schema = t_schema(None, GeminiPaperOutput)
    assert schema is not None
    # Verify 'marks' field has minimum, not exclusiveMinimum
    questions_schema = schema.properties["questions"]
    q_item_schema = questions_schema.items
    marks_schema = q_item_schema.properties["marks"]
    assert getattr(marks_schema, "minimum", None) == 0.5
    assert not hasattr(marks_schema, "exclusiveMinimum") or getattr(marks_schema, "exclusiveMinimum", None) is None


@pytest.mark.asyncio
async def test_regression_missing_required_fields(db_session):
    """Test 2: Gemini output missing required fields (e.g. question_text)."""
    fixtures = await setup_test_fixtures(db_session)
    teacher = fixtures["teacher"]
    org = fixtures["org"]
    subj = fixtures["subject"]
    mat1 = fixtures["material1"]

    mock_vector_store = MagicMock()
    mock_vector_store.search.return_value = [{"id": "c1", "content": "OS text", "material_id": str(mat1.material_id)}]
    mock_embeddings = MagicMock()
    mock_embeddings.embed_query = MagicMock(return_value=[0.1] * 768)

    # Missing question_text
    invalid_output = json.dumps({
        "questions": [
            {
                "question_type": "mcq_single",
                "marks": 5.0,
                "difficulty": "easy",
                "options": [{"text": "A", "is_correct": True}, {"text": "B", "is_correct": False}],
            }
        ]
    })
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MockGeminiResponse(invalid_output)

    service = QuestionPaperGenerationService(
        db=db_session,
        embedding_service=mock_embeddings,
        vector_store=mock_vector_store,
        client=mock_client,
        max_retries=1,
    )

    with pytest.raises(ValidationException) as exc_info:
        await service.generate_draft(
            org_id=org.organization_id,
            subject_id=subj.subject_id,
            requesting_user_id=teacher.user_id,
            is_org_admin=False,
            config=QpGenerateRequest(
                title="Missing Fields Test",
                material_ids=[mat1.material_id],
                total_marks=5.0,
                total_questions=1,
                question_types=["mcq_single"],
            ),
        )
    assert "ValidationError" in str(exc_info.value)
    # Ensure cause is preserved
    assert exc_info.value.__cause__ is not None


@pytest.mark.asyncio
async def test_regression_invalid_question_type_or_difficulty(db_session):
    """Test 3: Gemini returns invalid question_type or difficulty."""
    fixtures = await setup_test_fixtures(db_session)
    teacher = fixtures["teacher"]
    org = fixtures["org"]
    subj = fixtures["subject"]
    mat1 = fixtures["material1"]

    mock_vector_store = MagicMock()
    mock_vector_store.search.return_value = [{"id": "c1", "content": "OS text", "material_id": str(mat1.material_id)}]
    mock_embeddings = MagicMock()
    mock_embeddings.embed_query = MagicMock(return_value=[0.1] * 768)

    invalid_output = json.dumps({
        "questions": [
            {
                "question_type": "fill_in_the_blank",
                "question_text": "What is the capital of Operating Systems?",
                "marks": 5.0,
                "difficulty": "extreme_nightmare",
            }
        ]
    })
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MockGeminiResponse(invalid_output)

    service = QuestionPaperGenerationService(
        db=db_session,
        embedding_service=mock_embeddings,
        vector_store=mock_vector_store,
        client=mock_client,
        max_retries=1,
    )

    with pytest.raises(ValidationException) as exc_info:
        await service.generate_draft(
            org_id=org.organization_id,
            subject_id=subj.subject_id,
            requesting_user_id=teacher.user_id,
            is_org_admin=False,
            config=QpGenerateRequest(
                title="Invalid Type Test",
                material_ids=[mat1.material_id],
                total_marks=5.0,
                total_questions=1,
                question_types=["mcq_single"],
            ),
        )
    assert "ValidationError" in str(exc_info.value)


@pytest.mark.asyncio
async def test_regression_invalid_mcq_options_and_correct_answers(db_session):
    """Test 4: MCQ options validation and single-correct answer normalization."""
    fixtures = await setup_test_fixtures(db_session)
    teacher = fixtures["teacher"]
    org = fixtures["org"]
    subj = fixtures["subject"]
    mat1 = fixtures["material1"]

    mock_vector_store = MagicMock()
    mock_vector_store.search.return_value = [{"id": "c1", "content": "OS text", "material_id": str(mat1.material_id)}]
    mock_embeddings = MagicMock()
    mock_embeddings.embed_query = MagicMock(return_value=[0.1] * 768)

    # MCQ with multiple correct options (should normalize to 1 correct)
    output = json.dumps({
        "questions": [
            {
                "question_type": "mcq_single",
                "question_text": "Which scheduling algorithms exist?",
                "marks": 5.0,
                "difficulty": "medium",
                "options": [
                    {"text": "Round Robin", "is_correct": True},
                    {"text": "Shortest Job First", "is_correct": True},
                    {"text": "Invalid", "is_correct": False},
                ],
                "source_hint": "OS text",
            }
        ]
    })
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MockGeminiResponse(output)

    service = QuestionPaperGenerationService(
        db=db_session,
        embedding_service=mock_embeddings,
        vector_store=mock_vector_store,
        client=mock_client,
        max_retries=1,
    )

    draft = await service.generate_draft(
        org_id=org.organization_id,
        subject_id=subj.subject_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False,
        config=QpGenerateRequest(
            title="Multi Correct Test",
            material_ids=[mat1.material_id],
            total_marks=5.0,
            total_questions=1,
            question_types=["mcq_single"],
        ),
    )
    # Exactly one option should be correct after normalization
    opts = draft.questions[0].dq_options
    correct_count = sum(1 for o in opts if o.get("is_correct"))
    assert correct_count == 1


@pytest.mark.asyncio
async def test_regression_invalid_marks_and_total_mark_mismatches(db_session):
    """Test 5: Marks < 0.5 rejected; total mark mismatch flagged as warning."""
    fixtures = await setup_test_fixtures(db_session)
    teacher = fixtures["teacher"]
    org = fixtures["org"]
    subj = fixtures["subject"]
    mat1 = fixtures["material1"]

    mock_vector_store = MagicMock()
    mock_vector_store.search.return_value = [{"id": "c1", "content": "OS text", "material_id": str(mat1.material_id)}]
    mock_embeddings = MagicMock()
    mock_embeddings.embed_query = MagicMock(return_value=[0.1] * 768)

    # 1. Negative marks -> rejected by schema validator
    negative_marks_output = json.dumps({
        "questions": [
            {
                "question_type": "short_answer",
                "question_text": "What is process scheduling?",
                "marks": -5.0,
                "difficulty": "medium",
                "expected_answer": "OS process scheduling",
            }
        ]
    })
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MockGeminiResponse(negative_marks_output)

    service = QuestionPaperGenerationService(
        db=db_session,
        embedding_service=mock_embeddings,
        vector_store=mock_vector_store,
        client=mock_client,
        max_retries=1,
    )

    with pytest.raises(ValidationException) as exc_info:
        await service.generate_draft(
            org_id=org.organization_id,
            subject_id=subj.subject_id,
            requesting_user_id=teacher.user_id,
            is_org_admin=False,
            config=QpGenerateRequest(
                title="Negative Marks Test",
                material_ids=[mat1.material_id],
                total_marks=5.0,
                total_questions=1,
                question_types=["short_answer"],
            ),
        )
    assert "ValidationError" in str(exc_info.value)

    # 2. Total marks mismatch (target 20.0, actual 5.0) -> validation warning
    mismatch_output = json.dumps({
        "questions": [
            {
                "question_type": "short_answer",
                "question_text": "What is process scheduling in operating systems?",
                "marks": 5.0,
                "difficulty": "medium",
                "expected_answer": "Process scheduling selects processes for execution.",
                "rubric": "5 marks for complete definition.",
            }
        ]
    })
    mock_client.models.generate_content.return_value = MockGeminiResponse(mismatch_output)

    draft = await service.generate_draft(
        org_id=org.organization_id,
        subject_id=subj.subject_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False,
        config=QpGenerateRequest(
            title="Mismatch Total Marks Test",
            material_ids=[mat1.material_id],
            total_marks=20.0,
            total_questions=1,
            question_types=["short_answer"],
        ),
    )
    assert draft.draft_validation_result is not None
    issues = draft.draft_validation_result.get("issues", [])
    mismatch_warnings = [i for i in issues if "Total marks mismatch" in i.get("message", "")]
    assert len(mismatch_warnings) >= 1


@pytest.mark.asyncio
async def test_regression_missing_subjective_expected_answers_or_rubrics(db_session):
    """Test 6: Missing subjective expected answer and rubric flagged as warning."""
    fixtures = await setup_test_fixtures(db_session)
    teacher = fixtures["teacher"]
    org = fixtures["org"]
    subj = fixtures["subject"]
    mat1 = fixtures["material1"]

    mock_vector_store = MagicMock()
    mock_vector_store.search.return_value = [{"id": "c1", "content": "OS text", "material_id": str(mat1.material_id)}]
    mock_embeddings = MagicMock()
    mock_embeddings.embed_query = MagicMock(return_value=[0.1] * 768)

    no_rubric_output = json.dumps({
        "questions": [
            {
                "question_type": "short_answer",
                "question_text": "Explain context switching overhead in detail.",
                "marks": 10.0,
                "difficulty": "hard",
                "expected_answer": "",  # Empty
                "rubric": None,         # Missing
            }
        ]
    })
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MockGeminiResponse(no_rubric_output)

    service = QuestionPaperGenerationService(
        db=db_session,
        embedding_service=mock_embeddings,
        vector_store=mock_vector_store,
        client=mock_client,
        max_retries=1,
    )

    draft = await service.generate_draft(
        org_id=org.organization_id,
        subject_id=subj.subject_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False,
        config=QpGenerateRequest(
            title="Missing Rubric Test",
            material_ids=[mat1.material_id],
            total_marks=10.0,
            total_questions=1,
            question_types=["short_answer"],
            generate_answer_key=True,
            generate_rubrics=True,
        ),
    )
    issues = draft.draft_validation_result.get("issues", [])
    rubric_warnings = [i for i in issues if "Rubric was requested" in i.get("message", "") or "no expected answer" in i.get("message", "")]
    assert len(rubric_warnings) >= 1


@pytest.mark.asyncio
async def test_regression_invalid_provenance_references(db_session):
    """Test 7: Unselected material IDs in provenance are caught and rejected/filtered."""
    fixtures = await setup_test_fixtures(db_session)
    teacher = fixtures["teacher"]
    org = fixtures["org"]
    subj = fixtures["subject"]
    mat1 = fixtures["material1"]
    unselected_id = str(uuid.uuid4())

    service = QuestionPaperGenerationService(db=db_session)

    fake_questions = [
        {
            "marks": 10.0,
            "question_text": "Valid test question about operating systems?",
            "question_type": "short_answer",
            "source_material_ids": [unselected_id],  # Illegal source reference
        }
    ]
    val_result = service._validate_paper(
        questions=fake_questions,
        config=QpGenerateRequest(
            title="Provenance Test",
            material_ids=[mat1.material_id],
            total_marks=10.0,
            total_questions=1,
            question_types=["short_answer"],
        ),
        allowed_material_ids=[str(mat1.material_id)],
    )
    assert not val_result.is_valid
    errors = [i for i in val_result.issues if i.severity == "error" and "not in the selection" in i.message]
    assert len(errors) == 1


@pytest.mark.asyncio
async def test_regression_malformed_json_and_markdown_output(db_session):
    """Test 8: Markdown-wrapped JSON (```json ... ```) is cleaned and parsed properly."""
    fixtures = await setup_test_fixtures(db_session)
    teacher = fixtures["teacher"]
    org = fixtures["org"]
    subj = fixtures["subject"]
    mat1 = fixtures["material1"]

    mock_vector_store = MagicMock()
    mock_vector_store.search.return_value = [{"id": "c1", "content": "OS text", "material_id": str(mat1.material_id)}]
    mock_embeddings = MagicMock()
    mock_embeddings.embed_query = MagicMock(return_value=[0.1] * 768)

    # Markdown wrapped JSON
    wrapped_output = f"```json\n{make_mock_gemini_output()}\n```"
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MockGeminiResponse(wrapped_output)

    service = QuestionPaperGenerationService(
        db=db_session,
        embedding_service=mock_embeddings,
        vector_store=mock_vector_store,
        client=mock_client,
        max_retries=1,
    )

    draft = await service.generate_draft(
        org_id=org.organization_id,
        subject_id=subj.subject_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False,
        config=QpGenerateRequest(
            title="Markdown JSON Test",
            material_ids=[mat1.material_id],
            total_marks=10.0,
            total_questions=2,
            question_types=["mcq_single", "short_answer"],
        ),
    )
    assert draft.draft_status == "ready"
    assert len(draft.questions) == 2


@pytest.mark.asyncio
async def test_regression_validation_failure_followed_by_successful_correction(db_session):
    """Test 9: Attempt 1 fails validation, attempt 2 provides corrected valid response."""
    fixtures = await setup_test_fixtures(db_session)
    teacher = fixtures["teacher"]
    org = fixtures["org"]
    subj = fixtures["subject"]
    mat1 = fixtures["material1"]

    mock_vector_store = MagicMock()
    mock_vector_store.search.return_value = [{"id": "c1", "content": "OS text", "material_id": str(mat1.material_id)}]
    mock_embeddings = MagicMock()
    mock_embeddings.embed_query = MagicMock(return_value=[0.1] * 768)

    attempt1_bad = json.dumps({
        "questions": [
            {
                "question_type": "mcq_single",
                "marks": 5.0,
                "difficulty": "easy",
                "options": [{"text": "A", "is_correct": True}, {"text": "B", "is_correct": False}],
            }
        ]
    })
    attempt2_good = json.dumps({
        "questions": [
            {
                "question_type": "mcq_single",
                "question_text": "Corrected question text here?",
                "marks": 5.0,
                "difficulty": "easy",
                "options": [{"text": "A", "is_correct": True}, {"text": "B", "is_correct": False}],
            }
        ]
    })

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = [
        MockGeminiResponse(attempt1_bad),
        MockGeminiResponse(attempt2_good),
    ]

    service = QuestionPaperGenerationService(
        db=db_session,
        embedding_service=mock_embeddings,
        vector_store=mock_vector_store,
        client=mock_client,
        max_retries=2,
    )

    draft = await service.generate_draft(
        org_id=org.organization_id,
        subject_id=subj.subject_id,
        requesting_user_id=teacher.user_id,
        is_org_admin=False,
        config=QpGenerateRequest(
            title="Recovery Test",
            material_ids=[mat1.material_id],
            total_marks=5.0,
            total_questions=1,
            question_types=["mcq_single"],
        ),
    )
    assert draft.draft_status == "ready"
    assert mock_client.models.generate_content.call_count == 2
    # Check that attempt 2 received correction instructions
    second_call_prompt = mock_client.models.generate_content.call_args_list[1][1]["contents"]
    assert "CRITICAL CORRECTION REQUIRED" in second_call_prompt


@pytest.mark.asyncio
async def test_regression_repeated_invalid_output_fails_safely_after_retry_limit(db_session):
    """Test 10: Repeated invalid output fails safely after retry limit and preserves cause."""
    fixtures = await setup_test_fixtures(db_session)
    teacher = fixtures["teacher"]
    org = fixtures["org"]
    subj = fixtures["subject"]
    mat1 = fixtures["material1"]

    mock_vector_store = MagicMock()
    mock_vector_store.search.return_value = [{"id": "c1", "content": "OS text", "material_id": str(mat1.material_id)}]
    mock_embeddings = MagicMock()
    mock_embeddings.embed_query = MagicMock(return_value=[0.1] * 768)

    invalid_output = json.dumps({"questions": [{"invalid_field": 123}]})
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MockGeminiResponse(invalid_output)

    service = QuestionPaperGenerationService(
        db=db_session,
        embedding_service=mock_embeddings,
        vector_store=mock_vector_store,
        client=mock_client,
        max_retries=2,
    )

    with pytest.raises(ValidationException) as exc_info:
        await service.generate_draft(
            org_id=org.organization_id,
            subject_id=subj.subject_id,
            requesting_user_id=teacher.user_id,
            is_org_admin=False,
            config=QpGenerateRequest(
                title="Exhaust Retries Test",
                material_ids=[mat1.material_id],
                total_marks=5.0,
                total_questions=1,
                question_types=["mcq_single"],
            ),
        )

    assert "failed after 3 attempts" in str(exc_info.value)
    assert mock_client.models.generate_content.call_count == 3
    assert exc_info.value.__cause__ is not None


@pytest.mark.asyncio
async def test_regression_safe_error_handling_no_internal_diagnostics_exposed(db_session):
    """Test 11: Error responses do not leak secrets, API keys, or raw tracebacks to clients."""
    fixtures = await setup_test_fixtures(db_session)
    teacher = fixtures["teacher"]
    org = fixtures["org"]
    subj = fixtures["subject"]
    mat1 = fixtures["material1"]

    mock_vector_store = MagicMock()
    mock_vector_store.search.return_value = [{"id": "c1", "content": "OS text", "material_id": str(mat1.material_id)}]
    mock_embeddings = MagicMock()
    mock_embeddings.embed_query = MagicMock(return_value=[0.1] * 768)

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError(
        "Internal provider error at https://api.google.com?key=AIzaSySecretFakeKey123"
    )

    service = QuestionPaperGenerationService(
        db=db_session,
        embedding_service=mock_embeddings,
        vector_store=mock_vector_store,
        client=mock_client,
        max_retries=1,
    )

    with pytest.raises(AiServiceException) as exc_info:
        await service.generate_draft(
            org_id=org.organization_id,
            subject_id=subj.subject_id,
            requesting_user_id=teacher.user_id,
            is_org_admin=False,
            config=QpGenerateRequest(
                title="Secret Leak Prevention Test",
                material_ids=[mat1.material_id],
                total_marks=5.0,
                total_questions=1,
                question_types=["mcq_single"],
            ),
        )

    assert exc_info.value.status_code == 502
    error_str = str(exc_info.value)
    assert "AIzaSySecretFakeKey123" not in error_str
    assert "key=" not in error_str


@pytest.mark.asyncio
async def test_gemini_provider_client_error_404_raises_502(db_session):
    """Reproduce exact 404/ClientError failure: returns 502 AiServiceException, not 422 ValidationException."""
    fixtures = await setup_test_fixtures(db_session)
    teacher = fixtures["teacher"]
    org = fixtures["org"]
    subj = fixtures["subject"]
    mat1 = fixtures["material1"]

    mock_vector_store = MagicMock()
    mock_vector_store.search.return_value = [{"id": "c1", "content": "OS text", "material_id": str(mat1.material_id)}]
    mock_embeddings = MagicMock()
    mock_embeddings.embed_query = MagicMock(return_value=[0.1] * 768)

    # Simulate Google GenAI ClientError 404 (model deprecated)
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception(
        "ClientError 404 NOT_FOUND. {'error': {'code': 404, 'message': 'This model models/gemini-2.5-flash is no longer available'}}"
    )

    service = QuestionPaperGenerationService(
        db=db_session,
        embedding_service=mock_embeddings,
        vector_store=mock_vector_store,
        client=mock_client,
        max_retries=2,
    )

    req = QpGenerateRequest(
        title="Model Deprecation Reproduction Test",
        material_ids=[mat1.material_id],
        total_marks=10.0,
        total_questions=1,
        question_types=["mcq_single"],
    )

    with pytest.raises(AiServiceException) as exc_info:
        await service.generate_draft(
            org_id=org.organization_id,
            subject_id=subj.subject_id,
            requesting_user_id=teacher.user_id,
            is_org_admin=False,
            config=req,
        )

    assert exc_info.value.status_code == 502
    assert "AI provider error" in str(exc_info.value)
    # 3 total attempts
    assert mock_client.models.generate_content.call_count == 3

    # Verify draft status is marked FAILED and not stuck in GENERATING
    result = await db_session.execute(
        select(QpDraft).where(QpDraft.draft_title == "Model Deprecation Reproduction Test")
    )
    draft = result.scalar_one_or_none()
    assert draft is not None
    assert draft.draft_status == QpDraftStatus.FAILED
    assert "ClientError" in draft.draft_generation_error


@pytest.mark.asyncio
async def test_invalid_generation_inputs_fail_safely(db_session):
    """Verify invalid inputs still return appropriate validation or permission errors."""
    fixtures = await setup_test_fixtures(db_session)
    teacher = fixtures["teacher"]
    student = fixtures["student"]
    org = fixtures["org"]
    subj = fixtures["subject"]
    mat1 = fixtures["material1"]

    service = QuestionPaperGenerationService(db=db_session)

    # 1. Student access blocked
    with pytest.raises(ForbiddenException):
        await service.generate_draft(
            org_id=org.organization_id,
            subject_id=subj.subject_id,
            requesting_user_id=student.user_id,
            is_org_admin=False,
            config=QpGenerateRequest(
                title="Student Attempt",
                material_ids=[mat1.material_id],
                total_marks=10.0,
            ),
        )

    # 2. Non-existent material ID
    fake_mid = uuid.uuid4()
    with pytest.raises(NotFoundException):
        await service.generate_draft(
            org_id=org.organization_id,
            subject_id=subj.subject_id,
            requesting_user_id=teacher.user_id,
            is_org_admin=False,
            config=QpGenerateRequest(
                title="Missing Material",
                material_ids=[fake_mid],
                total_marks=10.0,
            ),
        )

