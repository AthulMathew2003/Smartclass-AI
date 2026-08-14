from fastapi import APIRouter
from app.modules.auth.router import router as auth_router
from app.modules.organizations.router import router as org_router
from app.api.v1.workspaces import router as workspace_router
from app.modules.rbac.router import router as rbac_router
from app.api.v1.subjects import router as subject_router
from app.api.v1.profile_photo import router as profile_photo_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["Auth"])
router.include_router(org_router, prefix="/organizations", tags=["Organizations"])
router.include_router(workspace_router, prefix="/workspaces", tags=["Workspaces"])
router.include_router(subject_router, prefix="/subjects", tags=["Subjects"])
router.include_router(rbac_router, prefix="/roles", tags=["Roles & RBAC"])
router.include_router(profile_photo_router, prefix="/users", tags=["Profile Photos"])

