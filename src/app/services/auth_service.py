import logging
from supabase import create_client
from src.app.core.config import settings
from fastapi import HTTPException
from src.app.schemas.auth import AuthResponse, UserInfo, UserMetadata, SupabaseSession
from src.app.crud.crud_auth import auth
from src.app.models.core import User
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any

class AuthService:
    def __init__(self):
        # Create Supabase client in the service
        self.supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        self.admin_supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        self.logger = logging.getLogger(__name__)

    async def verify_token(
        self,
        token: str,
        db: AsyncSession | None = None,
        verify_email: bool = True,
    ) -> dict:
        """Verify a JWT token and return user information.
        
        Args:
            token: JWT token to verify
            db: Database session for business data operations
            
        Returns:
            dict: User information from the token
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            self.logger.debug("Attempting to verify token")
            
            # Get the user directly from the token - this is a sync operation but safe to use
            # as it's just JWT verification and doesn't involve database operations
            user = self.supabase.auth.get_user(token)
            
            if not user or not user.user:
                self.logger.warning("Token verification failed: No valid user found")
                raise HTTPException(status_code=401, detail="Invalid token")
                
            self.logger.info(f"Token verified successfully for user: {user.user.email}")
            
            # Convert datetime objects to ISO format strings
            created_at = user.user.created_at.isoformat() if user.user.created_at else None
            last_sign_in_at = user.user.last_sign_in_at.isoformat() if user.user.last_sign_in_at else None
            
            # Get user_id from metadata instead of Supabase user id
            user_id = user.user.user_metadata.get('user_id')
            if not user_id:
                self.logger.error("No user_id found in user metadata")
                raise HTTPException(status_code=401, detail="Invalid user metadata")
            
            return {
                "username": user.user.user_metadata.get('username', ''),
                "email": user.user.email,
                "id": user_id,  # Use user_id from metadata
                "created_at": created_at,
                "last_sign_in_at": last_sign_in_at
            }
            
        except Exception as e:
            error_str = str(e)
            self.logger.error(f"Token verification failed: {error_str}")
            if "token is expired" in error_str.lower():
                raise HTTPException(status_code=401, detail="Token has expired")
            raise HTTPException(status_code=401, detail="Invalid token")

    def authenticate_user(self, username: str, password: str) -> AuthResponse | bool:
        try:
            self.logger.debug(f"Attempting to authenticate user: {username}")
            response = self.supabase.auth.sign_in_with_password({
                "email": username,
                "password": password
            })
            if response and response.user:
                self.logger.info(f"User authenticated successfully: {username}")
                # Convert datetime objects to ISO format strings
                created_at = response.user.created_at.isoformat() if response.user.created_at else None
                last_sign_in_at = response.user.last_sign_in_at.isoformat() if response.user.last_sign_in_at else None
                
                # Get user_id from metadata instead of Supabase user id
                user_id = response.user.user_metadata.get('user_id')
                if not user_id:
                    self.logger.error("No user_id found in user metadata")
                    raise HTTPException(status_code=401, detail="Invalid user metadata")
                
                return AuthResponse(
                    session=SupabaseSession(
                        access_token=response.session.access_token,
                        refresh_token=response.session.refresh_token,
                        expires_in=response.session.expires_in,
                        expires_at=response.session.expires_at,
                        token_type="bearer"
                    ),
                    user=UserInfo(
                        username=response.user.user_metadata.get('username', ''),
                        email=response.user.email,
                        id=user_id,  # Use user_id from metadata
                        created_at=created_at,
                        last_sign_in_at=last_sign_in_at
                    )
                )
            self.logger.warning(f"Authentication failed for user: {username}")
            return False
        except Exception as e:
            self.logger.error(f"An error occurred during authentication for user: {username}, Error: {e}")
            raise HTTPException(status_code=500, detail="An error occurred during authentication")

    def refresh_access_token(self, refresh_token: str) -> SupabaseSession:
        """
        Refresh an access token using a refresh token.
        
        Args:
            refresh_token: The refresh token from a previous authentication
            
        Returns:
            SupabaseSession: New session with access and refresh tokens
            
        Raises:
            Exception: If token refresh fails
        """
        try:
            self.logger.debug("Attempting to refresh token")
            response = self.supabase.auth.refresh_session(refresh_token)
            
            if not response or not response.session:
                self.logger.warning("Token refresh failed: No valid session returned")
                return None
                
            self.logger.info("Token refreshed successfully")
            return SupabaseSession(
                access_token=response.session.access_token,
                refresh_token=response.session.refresh_token,
                expires_in=response.session.expires_in,
                expires_at=response.session.expires_at,
                token_type="bearer"
            )
            
        except Exception as e:
            self.logger.error(f"Token refresh failed: {str(e)}")
            raise Exception(f"Failed to refresh token: {str(e)}")
            

    def update_user_metadata(self, user_id: str, metadata: UserMetadata, access_token: str, refresh_token: str) -> None:
        """Update user metadata in Supabase auth.
        
        Args:
            user_id: ID of user to update
            metadata: Dictionary of metadata to update
            access_token: User's access token for session
            refresh_token: User's refresh token for session
            
        Raises:
            HTTPException: If metadata update fails
        """
        try:
            self.logger.debug(f"Updating user metadata for user: {user_id}")
            self.supabase.auth.set_session(access_token, refresh_token)
            self.supabase.auth.update_user(
                {
                    "data": metadata.model_dump(exclude_none=True)
                }
            )
        except Exception as e:
            self.logger.error(f"An error occurred while updating the user metadata: {e}")
            raise HTTPException(status_code=500, detail="An error occurred while updating the user metadata")

    async def register_user(
        self,
        email: str,
        password: str,
        metadata: UserMetadata | None = None,
        email_confirm: bool = False,
        db: AsyncSession | None = None
    ) -> UserMetadata | bool:
        """
        Register a new user with Supabase.
        
        Args:
            email: User's email address
            password: User's password
            metadata: Optional user metadata to be stored in Supabase
            email_confirm: Whether to mark the email as verified (default: False)
            db: Database session for business data operations
            
        Returns:
            UserMetadata if registration successful, False otherwise
            
        Raises:
            Exception: If registration fails
        """
        try:
            self.logger.debug(f"Attempting to register user: {email}")
            
            if email_confirm:
                # Use admin API to create user with email confirmed
                response = self.admin_supabase.auth.admin.create_user({
                    "email": email,
                    "password": password,
                    "email_confirm": True,
                    "user_metadata": metadata.model_dump() if metadata else {}
                })
                
                if not response or not response.user:
                    raise Exception("Failed to create user with admin API")
                
                # Create a User object from the response
                user = User(
                    id=response.user.id,
                    email=response.user.email,
                    name=response.user.user_metadata.get('name', '')
                )
                
                if db:
                    # Complete onboarding to create user account
                    onboarding_response = await auth.complete_onboarding(db, user)
                    
                    return UserMetadata(
                        email_verified=True,
                        onboarding_complete=True,
                        user_role=metadata.user_role if metadata else "user"
                    )
                else:
                    return UserMetadata(
                        email_verified=True,
                        onboarding_complete=False,
                        user_role=metadata.user_role if metadata else "user"
                    )
            else:
                # Use regular sign up for normal registration
                response = self.supabase.auth.sign_up({
                    "email": email,
                    "password": password,
                    "options": {
                        "data": metadata.model_dump() if metadata else {}
                    }
                })
                
                if not response or not response.user:
                    raise Exception("Failed to register user")
                    
                return UserMetadata(
                    email_verified=False,
                    onboarding_complete=metadata.onboarding_complete if metadata else False,
                    user_role=metadata.user_role if metadata else "user"
                )
        except Exception as e:
            self.logger.error(f"Failed to register user: {str(e)}")
            raise e
