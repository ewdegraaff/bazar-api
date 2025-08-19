from typing import ClassVar, Optional
from datetime import datetime
from pydantic import BaseModel
from uuid import UUID

from .base import BaseSchema, BaseResponseSchema


class SystemRoleBase(BaseSchema):
    """Base schema for system role."""
    name: str  # superadmin, admin, user


class SystemRoleCreate(SystemRoleBase):
    """Schema for creating a system role."""
    pass


class SystemRoleUpdate(BaseModel):
    """Schema for updating a system role."""
    name: Optional[str] = None


class SystemRoleResponse(SystemRoleBase):
    """Schema for system role response."""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SystemRoleInDB(SystemRoleBase, BaseResponseSchema):
    """Schema for system role in database."""
    table_name: ClassVar[str] = "system_roles"
    id: UUID
    created_at: datetime
    updated_at: datetime 