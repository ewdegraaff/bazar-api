from typing import Optional
from fastapi import HTTPException
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.models.core import User
from src.app.models.system_role import SystemRole
from src.app.models.user_system_role import UserSystemRole
from src.app.schemas.auth import OnboardResponse
from src.app.crud.base import CRUDBase
from src.app.schemas.user import UserCreate, UserInDB


class CRUDAuth(CRUDBase[UserInDB, UserCreate, None, User]):
    """CRUD operations for authentication and user management."""
    
    async def complete_onboarding(self, db: AsyncSession, current_user: User) -> OnboardResponse:
        """
        Complete the onboarding process for a newly registered user.
        Creates the user's account structure in the database.
        
        Args:
            db: Database session
            current_user: Current authenticated user from Supabase
            
        Returns:
            OnboardResponse: Response indicating successful onboarding
            
        Raises:
            HTTPException: If user already exists or onboarding fails
        """
        # Check if user already exists in our database
        stmt = select(User).where(User.email == current_user.email)
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="User already exists in database"
            )
        
        try:
            # Create user in our database (no organization needed)
            user = User(
                id=current_user.id,
                name=current_user.name,
                email=current_user.email
            )
            db.add(user)
            await db.flush()  # Get the user ID without committing
            
            # Assign default system role (user)
            stmt = select(SystemRole).where(SystemRole.name == "user")
            result = await db.execute(stmt)
            user_role = result.scalar_one_or_none()
            
            if not user_role:
                raise HTTPException(
                    status_code=500,
                    detail="Default system role not found"
                )
                
            # Create user system role relationship using the model
            user_system_role = UserSystemRole(
                user_id=user.id,
                system_role_id=user_role.id
            )
            db.add(user_system_role)
            
            # Commit all changes
            await db.commit()
            
            return OnboardResponse(
                success=True,
                message="Onboarding completed successfully",
                user_id=str(user.id)
            )
            
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to complete onboarding: {str(e)}"
            )

    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[UserInDB]:
        """Get user by email."""
        stmt = select(self.sql_model).where(self.sql_model.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            return None
        return self.model.model_validate(user.__dict__)

    async def get_by_username(self, db: AsyncSession, *, username: str) -> Optional[UserInDB]:
        """Get user by username."""
        stmt = select(self.sql_model).where(self.sql_model.username == username)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            return None
        return self.model.model_validate(user.__dict__)


auth = CRUDAuth(UserInDB, User)
