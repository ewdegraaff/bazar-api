from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from typing import Annotated

from src.app.api.auth_deps import CurrentUser
from src.app.db.session import SessionDep
from src.app.core.pbac import require_permission
from src.app.schemas import User
from src.app.schemas.user import UserCreate, UserUpdate, UserResponse
from src.app.models.core import User as UserModel

router = APIRouter()


@router.post("", response_model=UserResponse)
async def create_user(
    user_in: UserCreate,
    db: SessionDep,
    current_user: Annotated[CurrentUser, Depends(require_permission("create", "users"))]
) -> User:
    """Create new user."""
    # Check if user with email exists
    stmt = select(UserModel).where(UserModel.email == user_in.email)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user = UserModel(**user_in.model_dump())
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("", response_model=list[User])
async def read_users(
    current_user: Annotated[CurrentUser, Depends(require_permission("read", "users"))],
    db: SessionDep,
    skip: int | None = None,
    limit: int | None = None,
) -> list[User]:
    """Get all users."""
    stmt = select(UserModel)
    if skip is not None:
        stmt = stmt.offset(skip)
    if limit is not None:
        stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/me", response_model=User)
async def read_user_me(
    current_user: Annotated[CurrentUser, Depends(require_permission("read", "users"))]
) -> User:
    """Get current user."""
    return current_user


@router.get("/{user_id}", response_model=User)
async def read_user(
    user_id: str,
    db: SessionDep,
    current_user: Annotated[CurrentUser, Depends(require_permission("read", "users"))]
) -> User:
    """Get a specific user."""
    stmt = select(UserModel).where(UserModel.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_in: UserUpdate,
    db: SessionDep,
    current_user: Annotated[CurrentUser, Depends(require_permission("update", "users"))]
) -> User:
    """Update user."""
    stmt = select(UserModel).where(UserModel.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user attributes
    for key, value in user_in.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", response_model=UserResponse)
async def delete_user(
    user_id: str,
    db: SessionDep,
    current_user: Annotated[CurrentUser, Depends(require_permission("delete", "users"))]
) -> User:
    """Delete user."""
    stmt = select(UserModel).where(UserModel.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.delete(user)
    await db.commit()
    return user
