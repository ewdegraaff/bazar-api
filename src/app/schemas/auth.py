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
    metadata: UserMetadata | None = None

    def validate_passwords(self) -> None:
        """Validate that passwords match."""
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")