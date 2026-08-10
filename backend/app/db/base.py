# Import all models here so Alembic can discover them for autogenerate
from app.db.base_class import Base  # noqa: F401
from app.modules.users.models import User  # noqa: F401
from app.modules.auth.models import OAuthAccount, RefreshToken  # noqa: F401
from app.modules.organizations.models import (  # noqa: F401
    Organization,
    Workspace,
    Role,
    OrganizationMember,
    WorkspaceMember
)
from app.modules.rbac.models import Permission, RolePermission  # noqa: F401
