import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, delete, func, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai_tutor.models import AiTutorConversation, AiTutorMessage


class AiTutorRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_conversation(
        self,
        org_id: uuid.UUID,
        workspace_id: uuid.UUID,
        subject_id: uuid.UUID,
        student_id: uuid.UUID,
        title: str,
    ) -> AiTutorConversation:
        conversation = AiTutorConversation(
            conversation_id=uuid.uuid4(),
            conversation_organization_id=org_id,
            conversation_workspace_id=workspace_id,
            conversation_subject_id=subject_id,
            conversation_student_id=student_id,
            conversation_title=title,
            conversation_created_at=datetime.now(timezone.utc),
            conversation_updated_at=datetime.now(timezone.utc),
        )
        self.db.add(conversation)
        await self.db.flush()
        return conversation

    async def list_conversations(
        self,
        org_id: uuid.UUID,
        workspace_id: uuid.UUID,
        subject_id: uuid.UUID,
        student_id: uuid.UUID,
    ) -> List[Tuple[AiTutorConversation, int]]:
        """
        List all conversations for a student in a subject along with message counts.
        """
        # Count subquery
        count_subq = (
            select(
                AiTutorMessage.message_conversation_id,
                func.count(AiTutorMessage.message_id).label("msg_count"),
            )
            .group_by(AiTutorMessage.message_conversation_id)
            .subquery()
        )

        query = (
            select(
                AiTutorConversation,
                func.coalesce(count_subq.c.msg_count, 0).label("message_count"),
            )
            .outerjoin(
                count_subq,
                AiTutorConversation.conversation_id == count_subq.c.message_conversation_id,
            )
            .where(
                AiTutorConversation.conversation_organization_id == org_id,
                AiTutorConversation.conversation_workspace_id == workspace_id,
                AiTutorConversation.conversation_subject_id == subject_id,
                AiTutorConversation.conversation_student_id == student_id,
            )
            .order_by(desc(AiTutorConversation.conversation_updated_at))
        )

        result = await self.db.execute(query)
        return [(row[0], row[1]) for row in result.all()]

    async def get_conversation(
        self,
        org_id: uuid.UUID,
        workspace_id: uuid.UUID,
        subject_id: uuid.UUID,
        student_id: uuid.UUID,
        conversation_id: uuid.UUID,
    ) -> Optional[AiTutorConversation]:
        """
        Fetch conversation ensuring strict tenant & ownership scoping with messages eagerly loaded.
        """
        query = (
            select(AiTutorConversation)
            .options(selectinload(AiTutorConversation.messages))
            .where(
                AiTutorConversation.conversation_id == conversation_id,
                AiTutorConversation.conversation_organization_id == org_id,
                AiTutorConversation.conversation_workspace_id == workspace_id,
                AiTutorConversation.conversation_subject_id == subject_id,
                AiTutorConversation.conversation_student_id == student_id,
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def delete_conversation(
        self,
        conversation: AiTutorConversation
    ) -> None:
        await self.db.delete(conversation)
        await self.db.flush()

    async def update_conversation_timestamp(
        self,
        conversation: AiTutorConversation
    ) -> None:
        conversation.conversation_updated_at = datetime.now(timezone.utc)
        await self.db.flush()

    async def create_message(
        self,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        sources: Optional[List[Dict[str, Any]]] = None,
    ) -> AiTutorMessage:
        message = AiTutorMessage(
            message_id=uuid.uuid4(),
            message_conversation_id=conversation_id,
            message_role=role,
            message_content=content,
            message_sources=sources,
            message_created_at=datetime.now(timezone.utc),
        )
        self.db.add(message)
        await self.db.flush()
        return message

    async def get_recent_messages(
        self,
        conversation_id: uuid.UUID,
        limit: int = 10,
    ) -> List[AiTutorMessage]:
        """
        Fetch the most recent N messages in chronological order.
        """
        subq = (
            select(AiTutorMessage)
            .where(AiTutorMessage.message_conversation_id == conversation_id)
            .order_by(desc(AiTutorMessage.message_created_at))
            .limit(limit)
            .subquery()
        )

        from sqlalchemy.orm import aliased
        aliased_msg = aliased(AiTutorMessage, subq)
        query = select(aliased_msg).order_by(aliased_msg.message_created_at)
        result = await self.db.execute(query)
        return list(result.scalars().all())
