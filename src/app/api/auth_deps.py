"""Authentication dependencies for FastAPI endpoints."""
from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import create_client, Client
from sqlalchemy import select
import logging
from uuid import UUID

from src.app.db.session import SessionDep
from src.app.models.core import User
from src.app.services.auth_service import AuthService
from src.app.core.config import settings

logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_supabase_client() -> Client:
    """Get a Supabase client instance."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

auth_service = AuthService()

async def get_current_user(
    db: SessionDep,
    token: str = Depends(oauth2_scheme),
) -> User:
    """Get the current authenticated user."""
    try:
        user_info = await auth_service.verify_token(token, db)
        logger.info(f"Token verified, looking for user with email: {user_info['email']}")
        
        # Look up user by email instead of ID
        stmt = select(User).where(User.email == user_info["email"])
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            logger.error(f"User authenticated in Supabase but not found in application database: {user_info['email']}")
            raise HTTPException(
                status_code=403,
                detail="User not registered in application. Please complete registration first."
            )
            
        return user
    except ValueError as e:
        logger.error(f"Invalid UUID format: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid user ID format")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        raise HTTPException(status_code=401, detail="Could not validate credentials")

async def get_anonymous_user(
    db: SessionDep,
    anonymous_id: str = Header(..., alias="X-Anonymous-ID"),
) -> User:
    """Get an anonymous user by their anonymous ID from header."""
    try:
        user = await auth_service.get_anonymous_user_by_id(anonymous_id, db)
        if not user:
            raise HTTPException(
                status_code=404,
                detail="Anonymous user not found"
            )
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting anonymous user: {str(e)}")
        raise HTTPException(status_code=401, detail="Could not validate anonymous user")

# Type aliases for dependencies
CurrentUser = Annotated[User, Depends(get_current_user)]
AnonymousUser = Annotated[User, Depends(get_anonymous_user)]
