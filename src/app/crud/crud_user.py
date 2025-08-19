from supabase import Client
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.session import SessionDep
from src.app.crud.base import CRUDBase
from src.app.schemas import User, UserCreate, UserUpdate
from src.app.models.core import User as UserModel


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate, UserModel]):
    """CRUD operations for user management."""
    
    async def get_by_email(self, db: AsyncSession, *, email: str) -> User | None:
        """Get a user by email."""
        stmt = select(UserModel).where(UserModel.email == email)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(self, db: AsyncSession, *, username: str) -> User | None:
        """Get a user by username."""
        stmt = select(UserModel).where(UserModel.username == username)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> list[User]:
        """Get multiple users."""
        stmt = select(UserModel).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def create(self, db: Client, *, obj_in: UserCreate) -> User:
        return await super().create(db, obj_in=obj_in)

    async def get(self, db: Client, *, id: str) -> User | None:
        return await super().get(db, id=id)

    async def get_all(self, db: Client) -> list[User]:
        return await super().get_all(db)

    async def update(self, db: Client, *, obj_in: UserUpdate) -> User:
        return await super().update(db, obj_in=obj_in)

    async def delete(self, db: Client, *, id: str) -> User:
        return await super().delete(db, id=id)


user = CRUDUser(User, UserModel)
