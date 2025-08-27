from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from src.app.api.auth_deps import CurrentUser, AnonymousUser
from src.app.db.session import SessionDep
from src.app.crud import crud_auth
from src.app.schemas import OnboardResponse, Token, RegisterRequest, UserMetadata, AnonymousUserResponse
from src.app.services.auth_service import AuthService

router = APIRouter()


@router.post("/create-anonymous", response_model=AnonymousUserResponse)
async def create_anonymous_user(db: SessionDep):
    """
    Create a temporary anonymous user for tracking activity before registration.
    This allows users to start using the app immediately without losing progress.
    """
    auth_service = AuthService()
    try:
        anonymous_user = await auth_service.create_anonymous_user(db)
        return AnonymousUserResponse(
            success=True,
            anonymous_user_id=str(anonymous_user.id),
            anonymous_id=anonymous_user.anonymous_id,
            message="Anonymous user created successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create anonymous user: {str(e)}")


@router.get("/anonymous-profile")
async def get_anonymous_profile(anonymous_user: AnonymousUser):
    """
    Get profile information for an anonymous user.
    This allows anonymous users to access their profile data.
    """
    return {
        "id": str(anonymous_user.id),
        "anonymous_id": anonymous_user.anonymous_id,
        "is_anonymous": anonymous_user.is_anonymous,
        "created_at": anonymous_user.created_at.isoformat() if anonymous_user.created_at else None
    }


@router.post("/convert-anonymous")
async def convert_anonymous_to_verified(
    anonymous_id: str,
    register_data: RegisterRequest,
    db: SessionDep
):
    """
    Convert an anonymous user to a verified user with email and password.
    This preserves all the anonymous user's progress and settings.
    """
    try:
        register_data.validate_passwords()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Find the anonymous user
    from src.app.models.core import User
    from sqlalchemy import select
    
    stmt = select(User).where(User.anonymous_id == anonymous_id, User.is_anonymous == True)
    result = await db.execute(stmt)
    anonymous_user = result.scalar_one_or_none()
    
    if not anonymous_user:
        raise HTTPException(status_code=404, detail="Anonymous user not found")
    
    auth_service = AuthService()
    try:
        response = await auth_service.convert_anonymous_to_verified(
            anonymous_user=anonymous_user,
            email=register_data.email,
            password=register_data.password,
            metadata=register_data.metadata,
            db=db
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to convert anonymous user: {str(e)}")


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
    db: SessionDep
):
    """
    Register a new user with email and password.
    
    Args:
        register_data: Registration data containing email, password, and optional metadata
        db: Database session
        
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
            db=db
        )
        if not response:
            raise HTTPException(status_code=400, detail="Failed to register user")
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")