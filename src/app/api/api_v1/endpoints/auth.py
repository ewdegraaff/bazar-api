from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from src.app.api.auth_deps import CurrentUser, AnonymousUser
from src.app.db.session import SessionDep
from src.app.crud import crud_auth
from src.app.crud.crud_user import user as crud_user
from src.app.schemas import OnboardResponse, Token, RegisterRequest, UserMetadata, AnonymousUserResponse, AnonymousUserSessionResponse, ConvertedUserSessionResponse, MarkUserForDeletionRequest, MarkUserForDeletionResponse, ConvertAnonymousRequest
from src.app.services.auth_service import AuthService

router = APIRouter()


@router.post("/create-anonymous", response_model=AnonymousUserSessionResponse)
async def create_anonymous_user(db: SessionDep):
    """
    Create a temporary anonymous user for tracking activity before registration.
    This allows users to start using the app immediately without losing progress.
    Creates user in both Supabase and local database, returns session tokens.
    """
    auth_service = AuthService()
    try:
        result = await auth_service.create_anonymous_user(db)
        return AnonymousUserSessionResponse(
            user=result["user"],
            session=result["session"]
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


@router.post("/convert-anonymous", response_model=ConvertedUserSessionResponse)
async def convert_anonymous_to_verified(
    request: ConvertAnonymousRequest,
    db: SessionDep
):
    """
    Convert an anonymous user to a verified user with email and password.
    This preserves all the anonymous user's progress and settings.
    Uses the user ID since it remains the same after conversion.
    Returns session tokens for immediate authentication.
    """
    try:
        request.register_data.validate_passwords()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Find the anonymous user by ID
    from src.app.models.core import User
    from sqlalchemy import select
    
    stmt = select(User).where(User.id == request.user_id, User.is_anonymous == True)
    result = await db.execute(stmt)
    anonymous_user = result.scalar_one_or_none()
    
    if not anonymous_user:
        raise HTTPException(status_code=404, detail="Anonymous user not found")
    
    auth_service = AuthService()
    try:
        result = await auth_service.convert_anonymous_to_verified(
            anonymous_user=anonymous_user,
            email=request.register_data.email,
            password=request.register_data.password,
            name=request.name,
            previous_anonymous_id=request.register_data.previous_anonymous_id,
            metadata=request.register_data.metadata,
            db=db
        )
        return ConvertedUserSessionResponse(
            user=result["user"],
            session=result.get("session"),
            requires_email_confirmation=result.get("requires_email_confirmation", False),
            message=result.get("message")
        )
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


@router.post("/mark-for-deletion", response_model=MarkUserForDeletionResponse)
async def mark_user_for_deletion(
    request: MarkUserForDeletionRequest,
    db: SessionDep,
    current_user: CurrentUser
):
    """
    Mark a user for deletion by setting the marked_for_deletion flag.
    This only marks the user for deletion - actual deletion is a separate process.
    
    Rules:
    - Users can mark themselves for deletion
    - Users can mark anonymous users for deletion
    - Users CANNOT mark other verified users for deletion
    
    Args:
        request: Request containing the user ID to mark for deletion
        db: Database session
        current_user: Currently authenticated user
        
    Returns:
        Response confirming the user has been marked for deletion
        
    Raises:
        HTTPException: If user not found or operation fails
    """
    try:
        # Check if the user to be deleted exists
        from src.app.models.core import User
        from sqlalchemy import select
        
        stmt = select(User).where(User.id == request.user_id)
        result = await db.execute(stmt)
        user_to_delete = result.scalar_one_or_none()
        
        if not user_to_delete:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Users can only mark themselves for deletion, OR mark anonymous users for deletion
        # They cannot mark other verified users for deletion
        if not user_to_delete.is_anonymous and str(request.user_id) != str(current_user.id):
            raise HTTPException(status_code=403, detail="Users can only mark themselves or anonymous users for deletion")
        
        success = await crud_user.mark_for_deletion(db, user_id=str(request.user_id))
        
        if not success:
            raise HTTPException(status_code=404, detail="User not found or already marked for deletion")
        
        return MarkUserForDeletionResponse(
            success=True,
            user_id=request.user_id,
            marked_for_deletion=True,
            message="User marked for deletion successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to mark user for deletion: {str(e)}")


@router.get("/users-marked-for-deletion")
async def get_users_marked_for_deletion(
    db: SessionDep,
    current_user: CurrentUser
):
    """
    Get all users that are marked for deletion.
    This endpoint is useful for the separate deletion process.
    
    Args:
        db: Database session
        current_user: Currently authenticated user
        
    Returns:
        List of users marked for deletion
        
    Raises:
        HTTPException: If operation fails
    """
    try:
        users = await crud_user.get_users_marked_for_deletion(db)
        return {
            "success": True,
            "users": [
                {
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.name,
                    "is_anonymous": user.is_anonymous,
                    "anonymous_id": user.anonymous_id,
                    "marked_for_deletion": user.marked_for_deletion,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "updated_at": user.updated_at.isoformat() if user.updated_at else None
                }
                for user in users
            ],
            "count": len(users)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get users marked for deletion: {str(e)}")