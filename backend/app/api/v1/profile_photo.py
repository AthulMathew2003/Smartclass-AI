import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.profile_photo import ProfilePhotoService
from app.modules.organizations.member_schemas import (
    ProfilePhotoConfirmRequest,
    ProfilePhotoUploadRequest,
    ProfilePhotoUploadInfo,
)
from app.modules.users.schemas import UserInfo
from app.core.exceptions import NotFoundException
from app.modules.rbac.dependencies import require_permission
from app.modules.rbac.constants import MemberPermission

router = APIRouter()


async def _get_target_user(user_id: uuid.UUID, db: AsyncSession) -> User:
    """Fetch a user by ID or raise NotFoundException."""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise NotFoundException("User not found.")
    return user


@router.post(
    "/{user_id}/profile-photo/upload-url",
    response_model=ProfilePhotoUploadInfo,
)
async def request_profile_photo_upload_url(
    user_id: uuid.UUID,
    payload: ProfilePhotoUploadRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(MemberPermission.UPDATE)),
):
    """
    Generate a presigned S3 upload URL for a user's profile photo.
    Requires member.update permission (admin/owner only).
    """
    user = await _get_target_user(user_id, db)
    photo_service = ProfilePhotoService()
    upload_data = photo_service.request_upload(
        user_id=user.user_id,
        content_type=payload.content_type,
        file_size=payload.file_size,
    )
    return ProfilePhotoUploadInfo(
        key=upload_data["key"],
        upload_url=upload_data["upload_url"],
        expires_in=upload_data["expires_in"],
    )


@router.post("/{user_id}/profile-photo/confirm")
async def confirm_profile_photo_upload(
    user_id: uuid.UUID,
    payload: ProfilePhotoConfirmRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(MemberPermission.UPDATE)),
):
    """
    Confirm a profile photo upload by verifying the S3 object exists
    and saving the key to user_profile_image.
    Requires member.update permission.
    """
    user = await _get_target_user(user_id, db)
    photo_service = ProfilePhotoService()
    updated_user = await photo_service.confirm_upload(db, user, payload.key)
    await db.commit()

    return UserInfo(
        id=str(updated_user.user_id),
        email=updated_user.user_email,
        first_name=updated_user.user_first_name,
        last_name=updated_user.user_last_name,
        profile_image=updated_user.user_profile_image,
        profile_image_url=photo_service.resolve_photo_url(updated_user.user_profile_image),
    )


@router.delete("/{user_id}/profile-photo")
async def delete_profile_photo(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(MemberPermission.UPDATE)),
):
    """
    Remove a user's profile photo. Clears user_profile_image and deletes the S3 object.
    Requires member.update permission.
    """
    user = await _get_target_user(user_id, db)
    photo_service = ProfilePhotoService()
    updated_user = await photo_service.delete_photo(db, user)
    await db.commit()

    return UserInfo(
        id=str(updated_user.user_id),
        email=updated_user.user_email,
        first_name=updated_user.user_first_name,
        last_name=updated_user.user_last_name,
        profile_image=updated_user.user_profile_image,
        profile_image_url=None,
    )
