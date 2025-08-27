import logging
import uuid
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import create_client

from src.app.core.config import settings
from src.app.models.core import User
from src.app.schemas.auth import AuthResponse, UserInfo, UserMetadata, SupabaseSession

class AuthService:
    def __init__(self):
        # Create Supabase client in the service
        self.supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        self.logger = logging.getLogger(__name__)

    async def create_anonymous_user(self, db: AsyncSession) -> User:
        """Create a temporary anonymous user for tracking activity before registration.
        
        Returns:
            User: Anonymous user object
            
        Raises:
            Exception: If anonymous user creation fails
        """
        try:
            self.logger.debug("Creating anonymous user")
            
            # Generate unique anonymous ID
            anonymous_id = f"anon_{uuid.uuid4().hex[:16]}"
            
            # Create anonymous user in our database
            anonymous_user = User(
                is_anonymous=True,
                anonymous_id=anonymous_id,
                email=None,
                name=None
            )
            
            db.add(anonymous_user)
            await db.flush()  # Get the user ID without committing
            
            # Assign default system role (user)
            from src.app.models.system_role import SystemRole
            from src.app.models.user_system_role import UserSystemRole
            
            stmt = select(SystemRole).where(SystemRole.name == "user")
            result = await db.execute(stmt)
            user_role = result.scalar_one_or_none()
            
            if not user_role:
                raise HTTPException(
                    status_code=500,
                    detail="Default system role not found"
                )
                
            # Create user system role relationship
            user_system_role = UserSystemRole(
                user_id=anonymous_user.id,
                system_role_id=user_role.id
            )
            db.add(user_system_role)
            
            await db.commit()
            
            self.logger.info(f"Created anonymous user with ID: {anonymous_user.id}")
            return anonymous_user
            
        except Exception as e:
            await db.rollback()
            self.logger.error(f"Failed to create anonymous user: {str(e)}")
            raise e

    async def convert_anonymous_to_verified(
        self, 
        anonymous_user: User, 
        email: str, 
        password: str, 
        metadata: UserMetadata | None = None,
        db: AsyncSession | None = None
    ) -> UserMetadata:
        """Convert an anonymous user to a verified user with email and password.
        
        Args:
            anonymous_user: The anonymous user to convert
            email: User's email address
            password: User's password
            metadata: Optional user metadata
            db: Database session
            
        Returns:
            UserMetadata: User status information
            
        Raises:
            Exception: If conversion fails
        """
        try:
            self.logger.debug(f"Converting anonymous user {anonymous_user.id} to verified user with email: {email}")
            
            # Check if email is already in use by another user
            if db:
                from sqlalchemy import select
                stmt = select(User).where(User.email == email, User.id != anonymous_user.id)
                result = await db.execute(stmt)
                existing_user = result.scalar_one_or_none()
                
                if existing_user:
                    raise HTTPException(
                        status_code=400,
                        detail="Email address is already in use by another user"
                    )
            
            # Create user in Supabase (this will send email verification)
            response = self.supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "user_id": str(anonymous_user.id),
                        "converted_from_anonymous": True,
                        "anonymous_id": anonymous_user.anonymous_id
                    }
                }
            })
            
            if not response or not response.user:
                raise Exception("Failed to create user in Supabase")
            
            # Update our database user record
            if db:
                anonymous_user.email = email
                anonymous_user.is_anonymous = False
                anonymous_user.converted_from_anonymous_id = anonymous_user.anonymous_id
                anonymous_user.anonymous_id = None  # Clear anonymous ID
                
                await db.commit()
                
                return UserMetadata(
                    email_verified=False,  # Will be verified when user clicks email link
                    onboarding_complete=True,  # Already completed during anonymous phase
                    user_role=metadata.user_role if metadata else "user"
                )
            else:
                return UserMetadata(
                    email_verified=False,
                    onboarding_complete=False,
                    user_role=metadata.user_role if metadata else "user"
                )
                
        except Exception as e:
            self.logger.error(f"Failed to convert anonymous user: {str(e)}")
            raise e

    async def get_anonymous_user_by_id(self, anonymous_id: str, db: AsyncSession) -> User | None:
        """Get an anonymous user by their anonymous ID.
        
        Args:
            anonymous_id: The anonymous ID to look up
            db: Database session
            
        Returns:
            User object if found, None otherwise
        """
        try:
            stmt = select(User).where(User.anonymous_id == anonymous_id, User.is_anonymous == True)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            self.logger.error(f"Failed to get anonymous user: {str(e)}")
            return None

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

    async def register_user(
        self,
        email: str,
        password: str,
        metadata: UserMetadata | None = None,
        db: AsyncSession | None = None
    ) -> UserMetadata | bool:
        """
        Register a new user with Supabase.
        
        Args:
            email: User's email address
            password: User's password
            metadata: Optional user metadata to be stored in Supabase
            db: Database session for business data operations
            
        Returns:
            UserMetadata if registration successful, False otherwise
            
        Raises:
            Exception: If registration fails
        """
        try:
            self.logger.debug(f"Attempting to register user: {email}")
            
            # Check if email is already in use by another user
            if db:
                from sqlalchemy import select
                stmt = select(User).where(User.email == email)
                result = await db.execute(stmt)
                existing_user = result.scalar_one_or_none()
                
                if existing_user:
                    raise HTTPException(
                        status_code=400,
                        detail="Email address is already in use by another user"
                    )
            
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
