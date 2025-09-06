from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr

from .base import BaseSchema


class Token(BaseModel):
    """Token schema for authentication."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserAttributes(BaseModel):
    """User attributes for authentication."""
    email: str
    password: str


class SupabaseSession(BaseModel):
    """Supabase session information."""
    access_token: str
    refresh_token: str
    expires_in: int
    expires_at: int
    token_type: str


class OnboardResponse(BaseModel):
    """Response schema for onboarding completion."""
    success: bool
    message: str
    user_id: str


class UserInfo(BaseModel):
    """User information returned during authentication."""
    username: str
    email: str
    id: str
    created_at: str
    last_sign_in_at: Optional[str] = None


class AnonymousUserInfo(BaseModel):
    """User information for anonymous users."""
    id: str
    email: Optional[str] = None
    isAnonymous: bool = True
    emailConfirmed: bool = False
    email_confirmed_at: Optional[str] = None
    created_at: str
    last_sign_in_at: Optional[str] = None


class VerifiedUserInfo(BaseModel):
    """User information for verified users."""
    id: str
    email: str
    isAnonymous: bool = False
    emailConfirmed: bool = True
    email_confirmed_at: Optional[str] = None
    created_at: str
    last_sign_in_at: Optional[str] = None


class AuthResponse(BaseModel):
    """Complete authentication response including tokens and user info."""
    session: SupabaseSession
    user: UserInfo


class UserMetadata(BaseModel):
    """User metadata to be updated in Supabase auth."""
    email_verified: bool | None = None
    onboarding_complete: bool | None = None
    user_role: str | None = None


class RegisterRequest(BaseModel):
    """Request schema for user registration."""
    email: EmailStr
    password: str
    confirm_password: str
    previous_anonymous_id: str | None = None
    metadata: UserMetadata | None = None

    def validate_passwords(self) -> None:
        """Validate that passwords match."""
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")


class AnonymousUserResponse(BaseModel):
    """Response schema for anonymous user creation."""
    success: bool
    anonymous_user_id: str
    anonymous_id: str
    message: str


class AnonymousUserSessionResponse(BaseModel):
    """Response schema for anonymous user creation with session data."""
    user: AnonymousUserInfo
    session: SupabaseSession


class ConvertedUserSessionResponse(BaseModel):
    """Response schema for converted user with session data."""
    user: VerifiedUserInfo
    session: Optional[SupabaseSession] = None
    requires_email_confirmation: Optional[bool] = False
    message: Optional[str] = None


class ConvertAnonymousRequest(BaseModel):
    """Request schema for converting anonymous user to verified user."""
    user_id: str
    name: str
    register_data: RegisterRequest