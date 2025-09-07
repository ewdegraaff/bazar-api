from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from typing import Annotated

from src.app.api.auth_deps import CurrentUser
from src.app.db.session import SessionDep
from src.app.core.pbac import require_permission
from src.app.schemas import User
from src.app.schemas.user import UserCreate, UserUpdate, UserResponse, UserPublic
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


@router.get("", response_model=list[UserPublic])
async def read_users(
    current_user: Annotated[CurrentUser, Depends(require_permission("read", "users"))],
    db: SessionDep,
    skip: int | None = None,
    limit: int | None = None,
) -> list[UserPublic]:
    """Get all users."""
    stmt = select(UserModel)
    if skip is not None:
        stmt = stmt.offset(skip)
    if limit is not None:
        stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/me", response_model=UserPublic)
async def read_user_me(
    current_user: Annotated[CurrentUser, Depends(require_permission("read", "users"))]
) -> UserPublic:
    """Get current user."""
    return current_user


@router.get("/{user_id}", response_model=UserPublic)
async def read_user(
    user_id: str,
    db: SessionDep,
    current_user: Annotated[CurrentUser, Depends(require_permission("read", "users"))]
) -> UserPublic:
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
    
    # Check if user is trying to update their own account or has admin privileges
    # Load user with system roles to check for admin privileges
    from sqlalchemy.orm import selectinload
    stmt_with_roles = select(UserModel).options(selectinload(UserModel.system_roles)).where(UserModel.id == current_user.id)
    result_with_roles = await db.execute(stmt_with_roles)
    current_user_with_roles = result_with_roles.scalar_one_or_none()
    
    if not current_user_with_roles:
        raise HTTPException(status_code=403, detail="User not found")
    
    # Get user system roles
    user_system_roles = [role.name for role in current_user_with_roles.system_roles]
    
    # Allow update if user is updating their own account OR has admin/superadmin role
    is_self_update = str(user_id) == str(current_user.id)
    has_admin_role = any(role in user_system_roles for role in ["admin", "superadmin"])
    
    if not (is_self_update or has_admin_role):
        raise HTTPException(status_code=403, detail="Users can only update their own account")
    
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
