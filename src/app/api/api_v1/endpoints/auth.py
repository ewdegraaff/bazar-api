from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from supabase import Client
from sqlalchemy.orm import Session
from typing import Optional

from src.app.api.auth_deps import CurrentUser
from src.app.db.session import SessionDep
from src.app.crud import crud_auth
from src.app.schemas import OnboardResponse, Token, RegisterRequest, UserMetadata
from src.app.services.auth_service import AuthService

router = APIRouter()


@router.post("/complete-onboarding")
async def complete_onboarding(
    db: SessionDep, current_user: CurrentUser, 
) -> OnboardResponse:
    """
    Complete the onboarding process for a newly registered user.
    This endpoint is called after email verification to create the user's account structure.
    """
    return crud_auth.complete_onboarding(db, current_user)


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Login endpoint that returns both access and refresh tokens.
    
    Args:
        form_data: OAuth2 password form containing username and password
        
    Returns:
        Token object containing access_token and refresh_token
        
    Raises:
        HTTPException: If credentials are invalid
    """
    auth_service = AuthService()
    response = auth_service.authenticate_user(form_data.username, form_data.password)
    if not response:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    return response


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str):
    """
    Refresh access token using a valid refresh token.
    
    Args:
        refresh_token: The refresh token from the X-Refresh-Token header
        
    Returns:
        New access and refresh tokens
        
    Raises:
        HTTPException: If refresh token is invalid or expired
    """
    auth_service = AuthService()
    try:
        new_tokens = auth_service.refresh_access_token(refresh_token)
        if not new_tokens:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        return new_tokens
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Failed to refresh token: {str(e)}")


@router.post("/register", response_model=UserMetadata)
async def register(
    register_data: RegisterRequest,
    db: SessionDep,
    email_confirm: bool = False
):
    """
    Register a new user with email and password.
    
    Args:
        register_data: Registration data containing email, password, and optional metadata
        db: Database session
        email_confirm: Whether to mark the email as verified (default: False)
        
    Returns:
        UserMetadata object containing user status information
        
    Raises:
        HTTPException: If registration fails or user already exists
    """
    try:
        register_data.validate_passwords()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    auth_service = AuthService()
    try:
        response = await auth_service.register_user(
            email=register_data.email,
            password=register_data.password,
            metadata=register_data.metadata,
            email_confirm=email_confirm,
            db=db
        )
        if not response:
            raise HTTPException(status_code=400, detail="Failed to register user")
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")