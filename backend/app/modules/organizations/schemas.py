import uuid
from typing import Optional, List
from pydantic import BaseModel, Field


class OnboardingRequest(BaseModel):
    org_name: str = Field(..., min_length=2, max_length=255)
    org_slug: str = Field(..., min_length=2, max_length=255)
    org_type: str = Field(..., max_length=100)
    org_country: str = Field(..., max_length=100)
    org_state: str = Field(..., max_length=100)
    org_city: str = Field(..., max_length=100)
    org_timezone: str = Field(..., max_length=100)
    org_logo: Optional[str] = None
    org_description: Optional[str] = None

    # Owner details to update
    owner_first_name: str = Field(..., min_length=1, max_length=100)
    owner_last_name: str = Field(..., min_length=1, max_length=100)
    owner_phone: Optional[str] = Field(None, max_length=20)

    # First workspace details
    workspace_name: str = Field(..., min_length=2, max_length=255)


class OrganizationBrief(BaseModel):
    organization_id: uuid.UUID
    organization_name: str
    organization_slug: str
    role_name: str


class UserMembershipBrief(BaseModel):
    organization_id: uuid.UUID
    organization_name: str
    organization_slug: str
    role_name: str
    workspace_name: Optional[str] = None


class OrganizationStatusResponse(BaseModel):
    has_organization: bool
