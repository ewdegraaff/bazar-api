from typing import ClassVar, Optional, List, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, ConfigDict

from .base import BaseSchema, TimestampSchema, IDSchema, BaseResponseSchema


# Base user schema
class User(BaseSchema):
    """User schema."""
    id: UUID
    name: str
    email: EmailStr
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None


# request
# Properties to receive on object creation
# in
class UserBase(BaseSchema):
    """Base user schema."""
    name: str
    email: EmailStr


class UserCreate(UserBase):
    """Schema for creating a user."""
    pass


# Properties to receive on User update
# in
class UserUpdate(BaseSchema):
    """Schema for updating a user."""
    name: Optional[str] = None
    email: Optional[str] = None


# Properties to return to client
# curd model
# out
class UserResponse(UserBase, BaseResponseSchema):
    """Schema for user response."""
    model_config = ConfigDict(from_attributes=True)


# Properties properties stored in DB
class UserInDB(UserBase, BaseResponseSchema):
    """Schema for user in database."""
    table_name: ClassVar[str] = "users"


class CurrentUser(User):
    """Schema for current authenticated user."""
    pass