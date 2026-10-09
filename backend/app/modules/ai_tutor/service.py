import uuid
import logging
from typing import Optional, List, Dict, Any, Set, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    NotFoundException,
    ForbiddenException,
    ValidationException,
)
from app.modules.subjects.models import Subject, SubjectStatus
from app.modules.organizations.models import Workspace, WorkspaceStatus
from app.modules.subjects.material_repository import SubjectMaterialRepository
from app.modules.rag.service import RagService
from app.modules.rag.schemas import RagSearchResultItem
from app.modules.ai_tutor.models import AiTutorConversation, AiTutorMessage
from app.modules.ai_tutor.repository import AiTutorRepository
from app.modules.ai_tutor.llm_client import AiTutorLlmClient
from app.modules.ai_tutor.prompt import (
    build_system_prompt,
    format_reference_context,
    format_user_query_turn,
)
from app.modules.ai_tutor.exceptions import (
    AiTutorException,
    ConversationNotFoundException,
)
from app.modules.ai_tutor.schemas import (
    AiTutorSourceItem,
    AiTutorMessageResponse,
    AiTutorConversationResponse,
    AiTutorConversationDetailResponse,
    AiTutorSendMessageResponse,
)

logger = logging.getLogger(__name__)


class AiTutorService:
    def __init__(
        self,
        db: AsyncSession,
        repo: Optional[AiTutorRepository] = None,
        rag_service: Optional[RagService] = None,
        llm_client: Optional[AiTutorLlmClient] = None,
    ):
        self.db = db
        self.repo = repo or AiTutorRepository(db)
        self.material_repo = SubjectMaterialRepository(db)
        self.rag_service = rag_service or RagService(db)
        self.llm_client = llm_client or AiTutorLlmClient()

    # ── Hierarchy and Access Validation ──────────────────────────

    async def _verify_subject_and_access(
        self,
        subject_id: uuid.UUID,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        is_org_admin: bool = False,
    ) -> Tuple[Subject, Workspace]:
        subject = await self.material_repo.get_subject(subject_id)
        if not subject or subject.subject_status == SubjectStatus.ARCHIVED:
            raise NotFoundException("Subject not found or archived.")

        workspace = await self.material_repo.get_workspace(subject.subject_workspace_id)
        if (
            not workspace
            or workspace.workspace_organization_id != org_id
            or workspace.workspace_status == WorkspaceStatus.ARCHIVED
        ):
            raise NotFoundException("Subject not found in current organization context.")

        if not is_org_admin:
            is_member = await self.material_repo.is_user_workspace_member(
                user_id, workspace.workspace_id
            )
            if not is_member:
                raise ForbiddenException("Access denied. You are not a member of this workspace.")

        return subject, workspace

    # ── Source Deduplication Helper ──────────────────────────────

    def _deduplicate_sources(
        self,
        results: List[RagSearchResultItem]
    ) -> List[AiTutorSourceItem]:
        deduped: List[AiTutorSourceItem] = []
        seen_keys: Set[Tuple[uuid.UUID, Optional[int], Optional[int]]] = set()

        for item in results:
            key = (item.material_id, item.page_number, item.slide_number)
            if key not in seen_keys:
                seen_keys.add(key)
                deduped.append(
                    AiTutorSourceItem(
                        material_id=item.material_id,
                        title=item.material_title,
                        filename=item.filename,
                        page_number=item.page_number,
                        slide_number=item.slide_number,
                    )
                )

        return deduped

    # ── Conversation Management ──────────────────────────────────

    async def create_conversation(
        self,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        user_id: uuid.UUID,
        title: Optional[str] = None,
        is_org_admin: bool = False,
    ) -> AiTutorConversationResponse:
        subject, workspace = await self._verify_subject_and_access(
            subject_id=subject_id,
            org_id=org_id,
            user_id=user_id,
            is_org_admin=is_org_admin,
        )

        conv_title = (title.strip() if title and title.strip() else "New Chat")[:255]

        conversation = await self.repo.create_conversation(
            org_id=org_id,
            workspace_id=workspace.workspace_id,
            subject_id=subject.subject_id,
            student_id=user_id,
            title=conv_title,
        )

        return AiTutorConversationResponse(
            conversation_id=conversation.conversation_id,
            subject_id=conversation.conversation_subject_id,
            title=conversation.conversation_title,
            created_at=conversation.conversation_created_at,
            updated_at=conversation.conversation_updated_at,
            message_count=0,
        )

    async def list_conversations(
        self,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        user_id: uuid.UUID,
        is_org_admin: bool = False,
    ) -> List[AiTutorConversationResponse]:
        subject, workspace = await self._verify_subject_and_access(
            subject_id=subject_id,
            org_id=org_id,
            user_id=user_id,
            is_org_admin=is_org_admin,
        )

        conv_pairs = await self.repo.list_conversations(
            org_id=org_id,
            workspace_id=workspace.workspace_id,
            subject_id=subject.subject_id,
            student_id=user_id,
        )

        return [
            AiTutorConversationResponse(
                conversation_id=conv.conversation_id,
                subject_id=conv.conversation_subject_id,
                title=conv.conversation_title,
                created_at=conv.conversation_created_at,
                updated_at=conv.conversation_updated_at,
                message_count=count,
            )
            for conv, count in conv_pairs
        ]

    async def get_conversation(
        self,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        is_org_admin: bool = False,
    ) -> AiTutorConversationDetailResponse:
        subject, workspace = await self._verify_subject_and_access(
            subject_id=subject_id,
            org_id=org_id,
            user_id=user_id,
            is_org_admin=is_org_admin,
        )

        conv = await self.repo.get_conversation(
            org_id=org_id,
            workspace_id=workspace.workspace_id,
            subject_id=subject.subject_id,
            student_id=user_id,
            conversation_id=conversation_id,
        )

        if not conv:
            raise ConversationNotFoundException()

        formatted_messages: List[AiTutorMessageResponse] = []
        for msg in conv.messages:
            sources_list = None
            if msg.message_sources:
                sources_list = [
                    AiTutorSourceItem(**s) if isinstance(s, dict) else s
                    for s in msg.message_sources
                ]

            formatted_messages.append(
                AiTutorMessageResponse(
                    message_id=msg.message_id,
                    conversation_id=msg.message_conversation_id,
                    role=msg.message_role,
                    content=msg.message_content,
                    sources=sources_list,
                    created_at=msg.message_created_at,
                )
            )

        return AiTutorConversationDetailResponse(
            conversation_id=conv.conversation_id,
            subject_id=conv.conversation_subject_id,
            title=conv.conversation_title,
            created_at=conv.conversation_created_at,
            updated_at=conv.conversation_updated_at,
            messages=formatted_messages,
        )

    async def delete_conversation(
        self,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        is_org_admin: bool = False,
    ) -> None:
        subject, workspace = await self._verify_subject_and_access(
            subject_id=subject_id,
            org_id=org_id,
            user_id=user_id,
            is_org_admin=is_org_admin,
        )

        conv = await self.repo.get_conversation(
            org_id=org_id,
            workspace_id=workspace.workspace_id,
            subject_id=subject.subject_id,
            student_id=user_id,
            conversation_id=conversation_id,
        )

        if not conv:
            raise ConversationNotFoundException()

        await self.repo.delete_conversation(conv)

    # ── Message Handling & Grounded Response Generation ──────────

    async def send_message(
        self,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        content: str,
        is_org_admin: bool = False,
    ) -> AiTutorSendMessageResponse:
        clean_content = content.strip()
        if not clean_content:
            raise ValidationException("Message content cannot be empty.")

        subject, workspace = await self._verify_subject_and_access(
            subject_id=subject_id,
            org_id=org_id,
            user_id=user_id,
            is_org_admin=is_org_admin,
        )

        # Verify conversation ownership
        conv = await self.repo.get_conversation(
            org_id=org_id,
            workspace_id=workspace.workspace_id,
            subject_id=subject.subject_id,
            student_id=user_id,
            conversation_id=conversation_id,
        )
        if not conv:
            raise ConversationNotFoundException()

        # Update title if default "New Chat" and this is first message
        if conv.conversation_title == "New Chat" or not conv.conversation_title:
            conv.conversation_title = clean_content[:60]

        # 1. Fetch recent history before saving current message
        recent_history_msgs = await self.repo.get_recent_messages(
            conversation_id=conversation_id,
            limit=settings.AI_TUTOR_MAX_HISTORY_MESSAGES,
        )

        history_payload = [
            {"role": m.message_role, "content": m.message_content}
            for m in recent_history_msgs
        ]

        # 2. Save student's user message
        user_msg = await self.repo.create_message(
            conversation_id=conversation_id,
            role="user",
            content=clean_content,
            sources=None,
        )

        # 3. Retrieve relevant chunks via RAG with strict tenant filtering
        rag_response = await self.rag_service.search(
            org_id=org_id,
            subject_id=subject.subject_id,
            query=clean_content,
            requesting_user_id=user_id,
            is_org_admin=is_org_admin,
            top_k=settings.AI_TUTOR_MAX_CONTEXT_CHUNKS,
        )

        # 4. Deduplicate sources
        deduped_sources = self._deduplicate_sources(rag_response.results)

        # 5. Build prompt and context
        system_prompt = build_system_prompt(subject.subject_name)
        formatted_context = format_reference_context(rag_response.results)
        user_query_turn = format_user_query_turn(clean_content, formatted_context)

        # 6. Call LLM generation
        tutor_answer = self.llm_client.generate_tutor_response(
            system_instruction=system_prompt,
            conversation_history=history_payload,
            current_query_with_context=user_query_turn,
        )

        # 7. Save assistant message
        sources_dicts = [s.model_dump(mode="json") for s in deduped_sources]
        assistant_msg = await self.repo.create_message(
            conversation_id=conversation_id,
            role="assistant",
            content=tutor_answer,
            sources=sources_dicts if sources_dicts else None,
        )

        # 8. Update conversation timestamp
        await self.repo.update_conversation_timestamp(conv)

        return AiTutorSendMessageResponse(
            user_message=AiTutorMessageResponse(
                message_id=user_msg.message_id,
                conversation_id=user_msg.message_conversation_id,
                role=user_msg.message_role,
                content=user_msg.message_content,
                sources=None,
                created_at=user_msg.message_created_at,
            ),
            assistant_message=AiTutorMessageResponse(
                message_id=assistant_msg.message_id,
                conversation_id=assistant_msg.message_conversation_id,
                role=assistant_msg.message_role,
                content=assistant_msg.message_content,
                sources=deduped_sources if deduped_sources else None,
                created_at=assistant_msg.message_created_at,
            ),
        )
