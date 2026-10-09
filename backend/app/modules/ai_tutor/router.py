import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.users.models import User
from app.modules.auth.dependencies import get_current_user
from app.modules.organizations.models import Organization
from app.modules.rbac.dependencies import get_current_organization, require_permission
from app.modules.rbac.constants import SubjectPermission
from app.modules.ai_tutor.service import AiTutorService
from app.modules.ai_tutor.schemas import (
    AiTutorCreateConversationRequest,
    AiTutorConversationResponse,
    AiTutorConversationDetailResponse,
    AiTutorSendMessageRequest,
    AiTutorSendMessageResponse,
)

router = APIRouter()


@router.post(
    "/subjects/{subject_id}/conversations",
    response_model=AiTutorConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    subject_id: uuid.UUID,
    payload: AiTutorCreateConversationRequest = AiTutorCreateConversationRequest(),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(SubjectPermission.READ)),
):
    """
    Create a new private AI Tutor conversation thread for a subject.
    """
    service = AiTutorService(db)
    is_org_admin = await service.material_repo.is_user_org_admin(
        current_user.user_id, org.organization_id
    )
    res = await service.create_conversation(
        org_id=org.organization_id,
        subject_id=subject_id,
        user_id=current_user.user_id,
        title=payload.title,
        is_org_admin=is_org_admin,
    )
    await db.commit()
    return res


@router.get(
    "/subjects/{subject_id}/conversations",
    response_model=List[AiTutorConversationResponse],
)
async def list_conversations(
    subject_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(SubjectPermission.READ)),
):
    """
    List all AI Tutor conversations owned by the current student for this subject.
    """
    service = AiTutorService(db)
    is_org_admin = await service.material_repo.is_user_org_admin(
        current_user.user_id, org.organization_id
    )
    return await service.list_conversations(
        org_id=org.organization_id,
        subject_id=subject_id,
        user_id=current_user.user_id,
        is_org_admin=is_org_admin,
    )


@router.get(
    "/subjects/{subject_id}/conversations/{conversation_id}",
    response_model=AiTutorConversationDetailResponse,
)
async def get_conversation(
    subject_id: uuid.UUID,
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(SubjectPermission.READ)),
):
    """
    Fetch details and message history for an AI Tutor conversation.
    """
    service = AiTutorService(db)
    is_org_admin = await service.material_repo.is_user_org_admin(
        current_user.user_id, org.organization_id
    )
    return await service.get_conversation(
        org_id=org.organization_id,
        subject_id=subject_id,
        conversation_id=conversation_id,
        user_id=current_user.user_id,
        is_org_admin=is_org_admin,
    )


@router.delete(
    "/subjects/{subject_id}/conversations/{conversation_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_conversation(
    subject_id: uuid.UUID,
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(SubjectPermission.READ)),
):
    """
    Delete an AI Tutor conversation thread and all its messages.
    """
    service = AiTutorService(db)
    is_org_admin = await service.material_repo.is_user_org_admin(
        current_user.user_id, org.organization_id
    )
    await service.delete_conversation(
        org_id=org.organization_id,
        subject_id=subject_id,
        conversation_id=conversation_id,
        user_id=current_user.user_id,
        is_org_admin=is_org_admin,
    )
    await db.commit()
    return {"message": "Conversation deleted successfully."}


@router.post(
    "/subjects/{subject_id}/conversations/{conversation_id}/messages",
    response_model=AiTutorSendMessageResponse,
)
async def send_message(
    subject_id: uuid.UUID,
    conversation_id: uuid.UUID,
    payload: AiTutorSendMessageRequest,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(SubjectPermission.READ)),
):
    """
    Send a message in an AI Tutor conversation, perform grounded RAG retrieval over subject materials,
    and generate an AI response with source citations.
    """
    service = AiTutorService(db)
    is_org_admin = await service.material_repo.is_user_org_admin(
        current_user.user_id, org.organization_id
    )
    res = await service.send_message(
        org_id=org.organization_id,
        subject_id=subject_id,
        conversation_id=conversation_id,
        user_id=current_user.user_id,
        content=payload.content,
        is_org_admin=is_org_admin,
    )
    await db.commit()
    return res
