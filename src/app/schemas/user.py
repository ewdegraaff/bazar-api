from typing import ClassVar, Optional, List, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, ConfigDict

from .base import BaseSchema, TimestampSchema, IDSchema, BaseResponseSchema


# Base user schema
class User(BaseSchema):
    """User schema."""
    id: UUID
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    profile_image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    marked_for_deletion: bool


class UserPublic(BaseSchema):
    """Public user schema without sensitive fields."""
    id: UUID
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    profile_image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# request
# Properties to receive on object creation
# in
class UserBase(BaseSchema):
    """Base user schema."""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    profile_image_url: Optional[str] = None
    marked_for_deletion: bool = False


class UserCreate(UserBase):
    """Schema for creating a user."""
    marked_for_deletion: bool = False


# Properties to receive on User update
# in
class UserUpdate(BaseSchema):
    """Schema for updating a user."""
    name: Optional[str] = None
    profile_image_url: Optional[str] = None
    marked_for_deletion: Optional[bool] = None


class MarkUserForDeletionRequest(BaseSchema):
    """Schema for marking a user for deletion."""
    user_id: UUID


class MarkUserForDeletionResponse(BaseSchema):
    """Schema for marking user for deletion response."""
    success: bool
    user_id: UUID
    marked_for_deletion: bool
    message: str


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